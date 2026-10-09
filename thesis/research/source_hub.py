"""Bounded Deus-style news fan-in with independent, visible provider outcomes."""
import json
import re
from threading import Lock
from urllib.parse import urljoin, urlsplit
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from uuid import uuid4
from xml.etree import ElementTree as ET
import httpx
from thesis.db import transaction, one, rows
from thesis.providers.settings import settings
from thesis.config import DATA, ROOT
from thesis.service import Conflict
from .catalogue import mentions
from .market import safe_url, provider_text, commit_news
from .social import plain_summary
from .sec.service import collection_lock

# Publisher endpoints from the pinned Deus settings. Only these endpoints are
# fetched; article links are retained for the reader, never followed by ingestion.
FEEDS = {
 'cnbc': ('CNBC', 'https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114', 30),
 'yahoo_news': ('Yahoo Finance', 'https://finance.yahoo.com/news/rssindex', 30),
 'wsj_markets': ('Wall Street Journal · Markets', 'https://feeds.content.dowjones.io/public/rss/RSSMarketsMain', 30),
 'wsj_business': ('Wall Street Journal · Business', 'https://feeds.content.dowjones.io/public/rss/WSJcomUSBusiness', 20),
 'wsj_tech': ('Wall Street Journal · Technology', 'https://feeds.content.dowjones.io/public/rss/RSSWSJD', 20),
 'marketwatch': ('MarketWatch', 'https://feeds.content.dowjones.io/public/rss/mw_topstories', 20),
 'nyt_business': ('New York Times · Business', 'https://rss.nytimes.com/services/xml/rss/nyt/Business.xml', 20),
 'google_business': ('Google News · Business', 'https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pWVXlnQVAB', 30),
 'fed_press': ('Federal Reserve', 'https://www.federalreserve.gov/feeds/press_all.xml', 15),
 'korea_economy': ('Korea Times · Economy', 'https://feed.koreatimes.co.kr/k/economy.xml', 25),
 'korea_business': ('Korea Times · Business', 'https://feed.koreatimes.co.kr/k/business.xml', 25),
}
FEED_LOCKS = {provider: Lock() for provider in FEEDS}
LABELS = {key: val[0] for key,val in FEEDS.items()} | {'alpha_vantage':'Alpha Vantage', 'x':'X / Twitter'}
RECENT_CHECK = 'This source was checked recently; saved data is retained.'


class SourceDeferred(Conflict):
    """No request was sent because the shared refresh interval has not elapsed."""


def configuration(provider):
    if DATA != ROOT / '.local':
        return 'Live extra sources are disabled in this isolated workspace.'
    values=settings()
    if values.get('THESIS_LIVE_DATA_ENABLED')!='true':
        return 'Source loading is switched off.'
    if provider=='alpha_vantage' and not values.get('ALPHA_VANTAGE_API_KEY'):
        return 'Add an Alpha Vantage key with access to NEWS_SENTIMENT, a Premium news endpoint.'
    if provider=='x' and (not values.get('X_BEARER_TOKEN') or values.get('THESIS_X_ENABLED')!='true'):
        return 'Add an X API token and enable X source requests; X charges separately for data.'
    return None


def reserve(provider, *, daily_limit=None):
    now=datetime.now(timezone.utc)
    with transaction(source=True) as c:
        c.execute('INSERT INTO provider_clocks(provider) VALUES(%s) ON CONFLICT DO NOTHING',(provider,))
        row=one(c,'SELECT * FROM provider_clocks WHERE provider=%s FOR UPDATE',(provider,))
        if row['denied']:
            raise ValueError('Access was denied. This source needs a supported connection before retrying.')
        if row['blocked_until'] and row['blocked_until']>now:
            raise Conflict('This source is cooling down after a provider limit.')
        if row['requests'] and row['next_at']>now:
            raise SourceDeferred(RECENT_CHECK)
        used=row['requests'] if row['usage_date']==now.date() else 0
        if daily_limit and used>=daily_limit:
            raise Conflict('The local daily request limit for this source has been reached.')
        delay=900 if provider in FEEDS else 60
        c.execute('UPDATE provider_clocks SET next_at=%s,usage_date=%s,requests=%s WHERE provider=%s',
                  (now+timedelta(seconds=delay),now.date(),used+1,provider))


def get(provider, url, *, params=None, headers=None, transport=None):
    allowed={key: value[1] for key,value in FEEDS.items()} | {'alpha_vantage':'https://www.alphavantage.co/query','x':'https://api.x.com/2/tweets/search/recent'}
    if allowed.get(provider) != url:
        raise ValueError('Unsupported source endpoint.')
    reserve(provider,daily_limit=25 if provider=='alpha_vantage' else 20 if provider=='x' else None)
    try:
        with httpx.Client(timeout=httpx.Timeout(20,connect=6),follow_redirects=False,transport=transport,
                          headers={'User-Agent':'ThesisResearchPrototype/0.1', **(headers or {})}) as client:
            endpoint = url
            for redirect in range(3):
                with client.stream('GET',endpoint,params=params) as response:
                    if provider in FEEDS and response.status_code in (301,302,307,308):
                        target=urljoin(endpoint,response.headers.get('Location',''))
                        destination=urlsplit(target)
                        if (redirect>=2 or not response.headers.get('Location') or
                            destination.scheme!='https' or destination.netloc!=urlsplit(url).netloc or
                            destination.username or destination.password):
                            raise ValueError(f'{LABELS[provider]} redirected outside its supported feed endpoint.')
                        endpoint=target
                        continue
                    if response.status_code in (401,403,429):
                        now=datetime.now(timezone.utc)
                        retry=response.headers.get('Retry-After','')
                        seconds=3600
                        try:
                            seconds=max(seconds,int(retry) if retry.isdigit() else (parsedate_to_datetime(retry)-now).total_seconds())
                        except (ValueError,TypeError,OverflowError):pass
                        with transaction(source=True) as c:
                            c.execute('UPDATE provider_clocks SET denied=%s,blocked_until=%s WHERE provider=%s',
                                      (response.status_code in (401,403),now+timedelta(seconds=min(seconds,86400)),provider))
                        raise ValueError(f'{LABELS[provider]} returned HTTP {response.status_code}; no retry was made.')
                    if response.status_code!=200:
                        raise ValueError(f'{LABELS[provider]} did not return a usable feed (HTTP {response.status_code}).')
                    body=bytearray()
                    for chunk in response.iter_bytes():
                        body.extend(chunk)
                        if len(body)>2_000_000:raise ValueError('Source response exceeded the supported size.')
                    return bytes(body)
    except httpx.HTTPError:
        # Never expose request URLs containing API keys in UI/history/errors.
        raise ValueError(f'{LABELS[provider]} could not be reached. Saved data is retained.') from None


def feed_bytes(provider, *, transport=None):
    # Concurrent company jobs share the first completed feed read in this process.
    # The persistent request clock still bounds other processes and restarts.
    with FEED_LOCKS[provider]:
        return _feed_bytes(provider, transport=transport)


def _feed_bytes(provider, *, transport=None):
    now=datetime.now(timezone.utc)
    with transaction(source=True) as c:
        row=one(c,'SELECT * FROM public_feed_cache WHERE provider=%s',(provider,))
    if row and now-row['retrieved_at']<timedelta(minutes=15):
        return bytes(row['body']),True
    body=get(provider,FEEDS[provider][1],transport=transport)
    # Validate XML before sharing a response between company jobs.
    xml_root(body)
    # Start the cache lifetime after retrieval. Starting before reservation made
    # it expire before the shared clock, causing an unnecessary deferred check.
    now=datetime.now(timezone.utc)
    with transaction(source=True) as c:
        c.execute('INSERT INTO public_feed_cache VALUES(%s,%s,%s) ON CONFLICT(provider) DO UPDATE SET body=excluded.body,retrieved_at=excluded.retrieved_at',(provider,body,now))
    return body,False


def xml_root(body):
    if len(body)>2_000_000 or b'<!DOCTYPE' in body.upper() or b'<!ENTITY' in body.upper():
        raise ValueError('Unsupported feed size or XML declaration.')
    try:root=ET.fromstring(body)
    except ET.ParseError:raise ValueError('The source did not return a readable RSS/Atom feed.') from None
    if root.tag not in ('rss','{http://www.w3.org/2005/Atom}feed'):
        raise ValueError('The source did not return an RSS/Atom feed.')
    return root


def parse_feed(provider, body, company, now):
    root=xml_root(body); atom='{http://www.w3.org/2005/Atom}'
    entries=root.findall('./channel/item') if root.tag=='rss' else root.findall(atom+'entry')
    output={};rejected=0
    for entry in entries[:FEEDS[provider][2]]:
        try:
            prefix=atom if root.tag!= 'rss' else ''
            title=provider_text(plain_summary(entry.findtext(prefix+'title') or ''),600)
            summary=provider_text(plain_summary(entry.findtext(prefix+'description') or entry.findtext(prefix+'summary') or entry.findtext(prefix+'content') or ''),6000,allow_empty=True)
            link=entry.findtext('link') if not prefix else next((l.get('href') for l in entry.findall(atom+'link') if l.get('rel','alternate')=='alternate'),'')
            url=safe_url(link)
            date=entry.findtext('pubDate') if not prefix else entry.findtext(atom+'published') or entry.findtext(atom+'updated')
            if not date:raise ValueError('Missing publication time')
            published=datetime.fromisoformat(date.replace('Z','+00:00')) if prefix else parsedate_to_datetime(date)
            if published.tzinfo is None or not now-timedelta(days=7)<=published<=now:
                raise ValueError('Outside news window')
            if not mentions(title+' '+summary,company['symbol'],company['name']):
                continue
            output[url]=dict(url=url,headline=title,body=summary,publisher=LABELS[provider],published_at=published,provider_id='')
        except (ValueError,TypeError,OverflowError):rejected+=1
    return sorted(output.values(),key=lambda x:(x['published_at'],x['url']),reverse=True),len(entries),rejected


def alpha_error(body):
    """Translate known provider errors without persisting echoed keys or URLs.

    Rate-limit notices often advertise premium plans. That advertisement alone
    must not be mistaken for an endpoint-access rejection.
    """
    if not isinstance(body, dict):
        return 'Alpha Vantage returned no readable response; saved news is unchanged.'
    messages = [body[k] for k in ('Note', 'Information', 'Error Message') if k in body]
    if not messages:
        return None
    text = ' '.join(m for m in messages if isinstance(m, str)).lower()
    text = re.sub(r'\s+', ' ', text)
    if re.search(r'(?:invalid|missing) (?:api ?key)|api ?key.{0,30}(?:invalid|missing)', text):
        return 'Alpha Vantage rejected the API key as invalid or missing. Check ALPHA_VANTAGE_API_KEY in the private .env; saved news is unchanged.'
    if re.search(r'rate limit|call frequency|request limit|(?:requests?|calls?) per (?:day|minute|second)', text):
        return 'Alpha Vantage reported a request limit. Wait for the provider allowance to reset and check other apps using this key. A rate-limit notice alone does not establish a plan restriction; saved news is unchanged.'
    if re.search(r'premium (?:api )?(?:endpoint|function)|(?:requires?|requiring).{0,30}premium|premium.{0,30}(?:required|only)', text):
        return 'Alpha Vantage requires Premium access for NEWS_SENTIMENT. A free API key does not unlock this endpoint; waiting will not change the plan. Confirm endpoint access with Alpha Vantage or use the other news sources. Saved news is unchanged.'
    if re.search(r'invalid (?:api call|request|parameter|function)', text):
        return 'Alpha Vantage rejected the request parameters. The integration needs checking; replacing the key or buying a plan is not an established fix. Saved news is unchanged.'
    return 'Alpha Vantage returned an unrecognised service message. Fledge could not determine whether it concerns the key, usage or endpoint access. NEWS_SENTIMENT is documented as Premium; check access with Alpha Vantage. Saved news is unchanged.'


def alpha_pause(conn, now):
    clock = one(conn, "SELECT blocked_until FROM provider_clocks WHERE provider='alpha_vantage'")
    if clock and clock['blocked_until'] and clock['blocked_until'] > now:
        until = clock['blocked_until'].astimezone(timezone.utc).strftime('%d %b %Y, %H:%M UTC')
        return f'Fledge has paused requests until {until}. This is the app’s cooldown, not a confirmed provider reset time.'
    return None


def parse_alpha(body, company, now):
    if message := alpha_error(body):
        raise ValueError(message)
    if not isinstance(body.get('feed'),list):raise ValueError('Alpha Vantage returned no readable feed.')
    output={};rejected=0
    for item in body['feed'][:50]:
        try:
            if not any(isinstance(t,dict) and t.get('ticker')==company['symbol'] for t in item.get('ticker_sentiment',[])):continue
            title=provider_text(item.get('title'),600);summary=provider_text(item.get('summary',''),6000,allow_empty=True)
            url=safe_url(item.get('url'));publisher=provider_text(item.get('source'),180)
            published=datetime.strptime(item['time_published'],'%Y%m%dT%H%M%S').replace(tzinfo=timezone.utc)
            if not now-timedelta(days=7)<=published<=now:raise ValueError('Outside news window')
            output[url]=dict(url=url,headline=title,body=summary,publisher=publisher,published_at=published,provider_id='')
        except (ValueError,TypeError,KeyError,AttributeError):rejected+=1
    # Provider sentiment scores are intentionally not imported as our labels.
    return list(output.values()),len(body['feed']),rejected


def begin(iid,provider):
    now=datetime.now(timezone.utc);token=uuid4()
    with transaction(source=True) as c:
        company=one(c,'SELECT i.symbol,i.name FROM instruments i JOIN sec_companies s ON s.instrument_id=i.id WHERE i.id=%s',(iid,))
        if not company:raise ValueError('Choose a registered company.')
        c.execute('INSERT INTO provider_checks(instrument_id,provider) VALUES(%s,%s) ON CONFLICT DO NOTHING',(iid,provider))
        old=one(c,'SELECT * FROM provider_checks WHERE instrument_id=%s AND provider=%s FOR UPDATE',(iid,provider))
        if old['lease_until'] and old['lease_until']>now:raise Conflict('This source is already being checked.')
        if old['last_attempt_at'] and now-old['last_attempt_at']<timedelta(minutes=15):raise Conflict('This source was checked recently; wait 15 minutes.')
        c.execute('UPDATE provider_checks SET attempt_id=%s,lease_until=%s,last_attempt_at=%s WHERE instrument_id=%s AND provider=%s',(token,now+timedelta(minutes=3),now,iid,provider))
    return company,token


def finish(iid,provider,token,outcome,message,fetched=0,matched=0,articles=None,rejected=0):
    now=datetime.now(timezone.utc)
    with transaction(source=True) as c:
        collection_lock(c)
        now=datetime.now(timezone.utc)
        state=one(c,'SELECT * FROM provider_checks WHERE instrument_id=%s AND provider=%s FOR UPDATE',(iid,provider))
        if state['attempt_id']!=token or not state['lease_until'] or state['lease_until']<now:
            raise Conflict('A newer source check replaced this attempt.')
        if articles is not None:
            commit_news(c,iid,articles,rejected,now,source_id='news-'+provider,source_name=LABELS[provider],entitlement='public-news')
        c.execute('UPDATE provider_checks SET completed_at=%s,lease_until=NULL,outcome=%s,message=%s,fetched=%s,matched=%s WHERE instrument_id=%s AND provider=%s',
                  (now,outcome,message,fetched,matched,iid,provider))
    return dict(status=outcome,message=message,fetched=fetched,matched=matched)


def refresh(iid,provider,*,transport=None,fetcher=None):
    if provider not in FEEDS and provider!='alpha_vantage':raise ValueError('Unsupported news provider.')
    if not fetcher and (message:=configuration(provider)):
        return dict(status='blocked',message=message)
    if provider=='alpha_vantage' and not fetcher:
        with transaction(source=True) as c:
            if pause := alpha_pause(c, datetime.now(timezone.utc)):
                # Keep the original diagnostic/check time while cooling down.
                return dict(status='blocked',message=pause)
    company,token=begin(iid,provider);now=datetime.now(timezone.utc)
    try:
        cached=False
        if provider in FEEDS:
            raw,cached=(fetcher(provider),False) if fetcher else feed_bytes(provider,transport=transport)
            articles,total,rejected=parse_feed(provider,raw,company,now)
        else:
            raw=fetcher(provider) if fetcher else json.loads(get(provider,'https://www.alphavantage.co/query',
                params=dict(function='NEWS_SENTIMENT',tickers=company['symbol'],time_from=(now-timedelta(days=7)).strftime('%Y%m%dT%H%M'),sort='LATEST',limit=50,apikey=settings()['ALPHA_VANTAGE_API_KEY']),transport=transport))
            if isinstance(raw,dict) and any(k in raw for k in ('Note','Information','Error Message')) and not fetcher:
                with transaction(source=True) as c:
                    c.execute('UPDATE provider_clocks SET blocked_until=%s WHERE provider=%s',
                              (now+timedelta(days=1),provider))
            articles,total,rejected=parse_alpha(raw,company,now)
        considered=min(total,FEEDS[provider][2] if provider in FEEDS else 50)
        message=f'{len(articles)} matching reports from {considered} of {total} feed items examined; {rejected} outside the window or unusable' + (' · reused recent feed cache.' if cached else '.')
        return finish(iid,provider,token,'ready',message,total,len(articles),articles,rejected)
    except SourceDeferred as exc:
        # A skipped request must not erase a previous real failure or success.
        with transaction(source=True) as c:
            state=one(c,'SELECT * FROM provider_checks WHERE instrument_id=%s AND provider=%s FOR UPDATE',(iid,provider))
            if state['attempt_id']!=token or not state['lease_until'] or state['lease_until']<datetime.now(timezone.utc):
                raise Conflict('A newer source check replaced this attempt.')
            c.execute('UPDATE provider_checks SET lease_until=NULL WHERE instrument_id=%s AND provider=%s',(iid,provider))
            if not state['outcome'] or state['outcome']=='deferred' or state['message']==RECENT_CHECK:
                c.execute("UPDATE provider_checks SET outcome='deferred',message=%s WHERE instrument_id=%s AND provider=%s",(str(exc),iid,provider))
        return dict(status='cached',message=str(exc),deferred=True)
    except (ValueError,Conflict) as exc:
        return finish(iid,provider,token,'failed',str(exc))


def refresh_rss(iid,*,fetcher=None):
    def run(provider):
        try:return refresh(iid,provider,fetcher=fetcher)
        except Conflict as exc:return dict(status='cached',message=str(exc))
    with ThreadPoolExecutor(max_workers=3) as pool:
        results=list(pool.map(run,FEEDS))
    matched=sum(r.get('matched',0) for r in results)
    failed=sum(r['status']=='failed' for r in results)
    waiting=sum(r['status']=='cached' for r in results)
    blocked=all(r['status']=='blocked' for r in results)
    checked=sum(r['status']=='ready' for r in results)
    return dict(status='blocked' if blocked else 'partial' if failed else 'cached' if waiting==len(results) else 'ready',
                message=results[0]['message'] if blocked else rss_sample_message(matched,checked,failed,waiting))


def rss_sample_message(matched, checked, failed, waiting):
    if checked is None:
        # Older journals did not retain the successful-feed count. Do not
        # reconstruct it from today's potentially different feed catalogue.
        parts = [f'{matched} report matches in that publisher-feed sample (7 days).']
    else:
        parts = [f'{matched} report matches across {checked} checked publisher feeds in the 7-day sample.' if checked else 'No publisher feeds were checked in this attempt.']
    if failed: parts.append(f'{failed} failed checks.')
    if waiting: parts.append(f'{waiting} checks deferred by the refresh schedule.')
    parts.append('General headline feeds are a limited sample; saved company news is separate.')
    return ' '.join(parts)


def status(conn,iid):
    saved={r['provider']:r for r in rows(conn,'SELECT * FROM provider_checks WHERE instrument_id=%s',(iid,))}
    clocks={r['provider']:r for r in rows(conn,'SELECT * FROM provider_clocks')}
    now=datetime.now(timezone.utc)
    result=[]
    for provider,label in LABELS.items():
        item=saved.get(provider,{})
        missing=configuration(provider)
        message=missing or item.get('message') or 'Included in Refresh research.'
        outcome='blocked' if missing else item.get('outcome') or 'not_loaded'
        # Correct only the exact historical app-timer diagnostic at read time;
        # do not rewrite records or imply an unperformed successful check.
        if not missing and (outcome=='deferred' or (outcome=='failed' and item.get('message')==RECENT_CHECK)):
            outcome='deferred'
            message='The shared refresh interval deferred this company check; no request was sent. Saved news is unchanged.'
        if provider=='x' and missing and settings().get('THESIS_X_ENABLED')!='true':
            outcome='disabled'
            message='Optional X / Twitter source is off.'
        clock=clocks.get(provider,{})
        dates=[clock.get('next_at'),clock.get('blocked_until')]
        if item.get('last_attempt_at'):dates.append(item['last_attempt_at']+timedelta(minutes=15))
        next_check=max((date for date in dates if date and date>now),default=None)
        if clock.get('denied'):
            # Elapsed pacing cannot grant a denied connection permission.
            next_check=None
        if provider=='alpha_vantage' and not missing:
            if message == 'Alpha Vantage returned an access or usage-limit message; no news was replaced.':
                message='The earlier check did not retain a specific failure reason. NEWS_SENTIMENT is documented as Premium; confirm that this key includes endpoint access. The old response does not prove a key, quota or plan problem.'
            if pause := alpha_pause(conn, datetime.now(timezone.utc)):
                message += ' ' + pause
        result.append(dict(provider=provider,label=label,channel='social' if provider=='x' else 'news',
                           status=outcome,
                           message=message,
                           checked_at=None if outcome=='deferred' else item.get('completed_at'),
                           last_attempt_at=item.get('last_attempt_at'),next_check_at=next_check,
                           matched=item.get('matched',0)))
    return result
