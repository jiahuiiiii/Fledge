"""Company-directed Reddit discovery and reply enrichment adapted from Deus.

Uses the same public Reddit host throughout; denials stop enrichment. No mirror,
cookie, proxy or user-agent disguise. Parent and reply authors stay separate.
"""
import hashlib
import re
import time
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from uuid import uuid4, uuid5, NAMESPACE_URL
import httpx
from thesis.db import transaction, one, rows
from thesis.service import Conflict
from . import social
from .catalogue import company_alias, mentions
from .social_threads import save


def request(url, params=None, *, atom=False, html_page=False):
    pattern = (r'https://www\.reddit\.com/r/[A-Za-z0-9_+]+/(?:search/|comments/[a-z0-9]+/[A-Za-z0-9_-]+/)'
               if html_page else r'https://www\.reddit\.com/(?:r/[A-Za-z0-9_+]+/(?:search\.rss|new/\.rss|comments/[a-z0-9]+\.json))')
    if (atom and html_page) or not re.fullmatch(pattern, url):
        raise ValueError('Unsupported Reddit endpoint.')
    if atom and datetime.now(timezone.utc).date().isoformat() >= '2026-11-13':
        raise ValueError('Reddit RSS support has ended; a supported connection is needed.')
    with transaction(source=True) as c:
        state = one(c,'SELECT * FROM reddit_request_clock WHERE singleton FOR UPDATE')
        now = datetime.now(timezone.utc)
        if state['reason'] in {'Reddit returned HTTP 401.','Reddit returned HTTP 403.'}:
            raise ValueError('Reddit denied access. A supported, approved Reddit connection is needed before collection can resume.')
        if state['blocked_until'] and state['blocked_until'] > now:
            raise Conflict('Reddit is cooling down after a provider rejection. Next check after ' + state['blocked_until'].strftime('%H:%M UTC') + '.')
        start = max(now,state['next_at'])
        c.execute('UPDATE reddit_request_clock SET next_at=%s WHERE singleton',(start+timedelta(seconds=3),))
    time.sleep(max(0,(start-datetime.now(timezone.utc)).total_seconds()))
    # A different worker may have received a denial while this request was queued.
    with transaction(source=True) as c:
        state=one(c,'SELECT blocked_until,reason FROM reddit_request_clock WHERE singleton')
        if state['reason'] in {'Reddit returned HTTP 401.','Reddit returned HTTP 403.'}:
            raise ValueError('Reddit denied access. A supported, approved Reddit connection is needed before collection can resume.')
        if state['blocked_until'] and state['blocked_until'] > datetime.now(timezone.utc):
            raise Conflict('Reddit is cooling down after a provider rejection.')
    with httpx.Client(timeout=httpx.Timeout(20,connect=6),follow_redirects=False,
                      headers={'User-Agent':'ThesisResearchPrototype/0.1 (local company research)',
                               'Accept':'text/html' if html_page else 'application/atom+xml' if atom else 'application/json'}) as client:
        with client.stream('GET',url,params=params) as response:
            if response.status_code in (401,403,429):
                now=datetime.now(timezone.utc)
                seconds=900 if response.status_code==429 else 3600
                retry=response.headers.get('Retry-After','')
                try:
                    wait=int(retry) if retry.isdigit() else (parsedate_to_datetime(retry)-now).total_seconds()
                    seconds=max(seconds,wait)
                except (ValueError,TypeError,OverflowError):
                    pass
                until=now+timedelta(seconds=min(seconds,86400))
                with transaction(source=True) as c:
                    c.execute('UPDATE reddit_request_clock SET blocked_until=GREATEST(blocked_until,%s),reason=%s WHERE singleton',
                              (until,f'Reddit returned HTTP {response.status_code}.'))
            response.raise_for_status()
            if html_page and (response.status_code != 200 or 'text/html' not in response.headers.get('Content-Type','').lower()):
                raise ValueError('Reddit HTML returned a redirect, login challenge, or unsupported page. No alternate route was attempted.')
            data=bytearray()
            for chunk in response.iter_bytes():
                data.extend(chunk)
                if len(data)>2000000:
                    raise ValueError('Reddit response exceeded size limit.')
    return bytes(data)


def fetch(kind, company, days, post=None, feeds=social.FEEDS):
    if kind=='search':
        alias=company_alias(company['name'])
        query=f'"{company["symbol"]}"' + (f' OR "{alias}"' if alias else '')
        return request('https://www.reddit.com/r/' + '+'.join(feeds) + '/search.rss',
                       dict(q=query,restrict_sr='on',sort='new',t={1:'day',7:'week',30:'month'}[days],limit=50),atom=True)
    if kind=='comments' and post:
        key=post['post_key'].removeprefix('t3_')
        if not re.fullmatch('[a-z0-9]+',key) or post['feed'] not in social.FEEDS:
            raise ValueError('Unsupported Reddit thread identity.')
        import json
        return json.loads(request(f'https://www.reddit.com/r/{post["feed"]}/comments/{key}.json',dict(limit=12,depth=1,sort='top',raw_json=1)))
    raise ValueError('Unsupported Reddit collection step.')


def search_posts(content, now, days, enabled):
    # Parsing and cleaning are the existing Deus-derived normalization boundary.
    parsed, excluded=social.parse_feed(content,social.FEEDS[0],now,days)
    result=[]
    for post in parsed:
        match=re.fullmatch(r'https://(?:www\.)?reddit\.com/r/([A-Za-z0-9_]+)/comments/([a-z0-9]+)/[^?#\s]*',post['url'])
        if not match or match[1].lower() not in enabled or post['post_key'] != 't3_'+match[2]:
            excluded+=1
            continue
        post['feed']=match[1].lower()
        result.append(post)
    return result,excluded


def replies(raw, post, now, days):
    if not isinstance(raw,list) or len(raw)!=2:
        raise ValueError('Reddit did not return a thread.')
    try:
        parent=raw[0]['data']['children'][0]['data']
        children=raw[1]['data']['children']
    except (KeyError,IndexError,TypeError):
        raise ValueError('Reddit thread is incomplete.')
    if not isinstance(parent,dict) or parent.get('name')!=post['post_key'] or str(parent.get('subreddit','')).lower()!=post['feed']:
        raise ValueError('Reddit thread identity does not match the post.')
    if parent.get('removed_by_category') or parent.get('selftext') in ('[removed]','[deleted]'):
        return [],[post['post_key']]
    # A changed title/body needs a new discovery version, not context silently
    # attached to an older source. Use the already dated RSS body as the parent.
    if social.plain_summary(parent.get('title','')) != post['title']:
        raise ValueError('The Reddit thread changed since discovery; refresh to read its new version.')
    if type(parent.get('created_utc')) not in (int,float) or abs(parent['created_utc']-post['published_at'].timestamp()) > 1:
        raise ValueError('Reddit parent publication time could not be verified.')
    context=dict(parent_key=post['post_key'],parent_type='story',title=post['title'],
                 body=social.plain_summary(parent.get('selftext') or ''),url=post['url'],published_at=post['published_at'])
    if len(context['body'])>6000 or not isinstance(children,list):
        raise ValueError('Reddit thread context exceeds the reading limit.')
    result,removed=[],[]
    for entry in children[:12]:
        if not isinstance(entry,dict) or entry.get('kind')!='t1':
            continue
        child=entry.get('data') or {}
        key=child.get('name','')
        if not re.fullmatch(r't1_[a-z0-9]+',key) or child.get('parent_id')!=post['post_key'] or child.get('link_id',post['post_key'])!=post['post_key']:
            continue
        if child.get('body') in ('[removed]','[deleted]'):
            removed.append(key)
            continue
        if type(child.get('created_utc')) not in (int,float) or not isinstance(child.get('body'),str):
            continue
        try:
            published=datetime.fromtimestamp(child['created_utc'],timezone.utc)
        except (ValueError,OverflowError,OSError):
            continue
        body=child['body'].strip()
        if not body or len(body)>12000 or not max(now-timedelta(days=days),post['published_at'])<=published<=now or child.get('author')=='AutoModerator':
            continue
        title='Reddit comment'
        result.append(dict(post_key=key,feed=post['feed'],title=title,body=body,
                           url=post['url'].rstrip('/')+'/'+key[3:]+'/',published_at=published,
                           author_hash=hashlib.sha256(('reddit:'+str(child.get('author','unknown'))).encode()).hexdigest() if child.get('author') else None,
                           content_hash=hashlib.sha256((title+'\n'+body).encode()).hexdigest(),parent=context))
    return result,removed


def refresh(iid, *, lookback_days=7, fetcher=None, now=None, collector=None):
    from thesis.providers.settings import settings
    from . import reddit_html, reddit_rss
    collector = collector or ('public' if fetcher else 'html' if settings().get('THESIS_REDDIT_HTML_ENABLED') == 'true' else 'rss')
    if collector not in ('public', 'html', 'rss'):
        raise ValueError('Choose the RSS, public feed or public HTML collector.')
    adapter = reddit_html if collector == 'html' else None
    if type(lookback_days) is not int or lookback_days not in (1,7,30):
        raise ValueError('Choose a discussion window of 1, 7 or 30 days.')
    supplied=now
    now=now or datetime.now(timezone.utc)
    token=uuid4()
    cache_only=False
    with transaction(source=True) as c:
        company=one(c,'SELECT i.symbol,i.name FROM instruments i JOIN sec_companies s ON s.instrument_id=i.id WHERE i.id=%s',(iid,))
        if not company:
            raise ValueError('Choose a registered company.')
        enabled=social.company_feeds(company['symbol'], [r['feed'] for r in rows(c,'SELECT feed FROM social_feeds WHERE enabled')])
        if not enabled:
            return dict(checked=[],failures=0,matched=0)
        c.execute('INSERT INTO reddit_company_checks(instrument_id) VALUES(%s) ON CONFLICT DO NOTHING',(iid,))
        state=one(c,'SELECT * FROM reddit_company_checks WHERE instrument_id=%s FOR UPDATE',(iid,))
        if state['lease_until'] and state['lease_until']>now:
            raise Conflict('Reddit company discussions are already being checked.')
        if state['last_attempt_at'] and now-state['last_attempt_at']<timedelta(minutes=15):
            if collector != 'rss' or fetcher:
                raise Conflict('Reddit company discussions were checked recently; wait 15 minutes.')
            cache_only=True
        # Four RSS requests can each wait for a reported reset (up to a minute)
        # and use a bounded HTTP timeout. Keep room for that paced acquisition.
        lease_minutes = 6 if collector == 'rss' else 4
        c.execute('UPDATE reddit_company_checks SET attempt_id=%s,lease_until=%s,last_attempt_at=%s WHERE instrument_id=%s',(token,now+timedelta(minutes=lease_minutes),state['last_attempt_at'] if cache_only else now,iid))
    get=fetcher or (lambda kind,post=None:(adapter.fetch if adapter else fetch)(kind,company,lookback_days,post,enabled))
    posts,comments,removed=[],[],[]
    excluded=0
    error=None
    discovered=0
    rss_result=None
    try:
        if collector == 'rss':
            rss_result=reddit_rss.collect(company,lookback_days,enabled,now,fetcher,cache_only=cache_only)
            posts,comments,removed=[rss_result[k] for k in ('posts','comments','removed')]
            excluded,discovered,error=[rss_result[k] for k in ('excluded','discovered','error')]
        else:
            candidates,excluded=(adapter.search_posts if adapter else search_posts)(get('search'),now,lookback_days,enabled)
            discovered=len(candidates)
            posts=[p for p in candidates if social.mentions(p,company['symbol'],company['name'])]
            excluded+=len(candidates)-len(posts)
            for post in posts[:3]:
                reply,withdrawn=(adapter.replies if adapter else replies)(get('comments',post),post,now,lookback_days)
                comments.extend(reply)
                removed.extend(withdrawn)
    except httpx.HTTPStatusError as exc:
        error=f'Reddit returned HTTP {exc.response.status_code}. Collection stopped; no alternate host or automatic retry was used.'
    except Conflict as exc:
        error=str(exc)
    except ValueError as exc:
        error=str(exc) if str(exc).startswith(('Reddit denied access.','Reddit RSS support has ended','Reddit HTML')) else 'Some Reddit discussions or replies could not be verified. Saved sources are retained.'
    except (TypeError,OverflowError,httpx.HTTPError) as exc:
        error='Some Reddit discussions or replies could not be verified. Saved sources are retained.'
    if adapter and error:
        error='Public HTML collector: ' + error
    done=supplied or datetime.now(timezone.utc)
    with transaction(source=True) as c:
        from .sec.service import collection_lock
        collection_lock(c)
        state=one(c,'SELECT * FROM reddit_company_checks WHERE instrument_id=%s FOR UPDATE',(iid,))
        if state['attempt_id']!=token or state['lease_until'] is None or state['lease_until']<done:
            raise Conflict('This Reddit collection expired or was replaced.')
        enabled_now={r['feed'] for r in rows(c,'SELECT feed FROM social_feeds WHERE enabled')}
        posts=[p for p in posts if p['feed'] in enabled_now and p['post_key'] not in removed]
        comments=[p for p in comments if p['feed'] in enabled_now and p['post_key'] not in removed and p.get('thread_key') not in removed]
        for key in removed:
            c.execute('INSERT INTO social_withdrawals VALUES(%s,%s) ON CONFLICT DO NOTHING',(key,done))
        retained=0
        for post in posts+comments:
            parent=post.get('parent')
            if post['feed'] not in enabled_now or post['post_key'] in removed or (parent and parent['parent_key'] in removed):
                continue
            pid=uuid5(NAMESPACE_URL,str(iid)+':reddit:'+post['post_key']+':'+post['content_hash'])
            c.execute("INSERT INTO social_posts VALUES(%s,%s,'reddit',%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                      (pid,iid,post['feed'],post['post_key'],post['author_hash'],post['content_hash'],post['title'],post['body'],post['url'],post['published_at'],done))
            save(c,pid,post.get('thread_key') or (parent['parent_key'] if parent else post['post_key']),post.get('kind') or ('comment' if parent else 'post'),
                 'direct' if social.mentions(post,company['symbol'],company['name']) else 'thread',done,parent,
                 method=post.get('method') or (reddit_rss.METHOD if collector == 'rss' else adapter.METHOD if adapter else None))
            retained+=1
        if rss_result:
            for kind,check in rss_result['checks'].items():
                check['matched']=len(posts if kind=='posts' else comments)
                message=(f'{check["matched"]} company posts retained from ticker/name search and any saved hot feeds.' if kind=='posts' else
                        f'{check["matched"]} company-matched comments retained. RSS supplies update times; immediate reply parents are unavailable.' if posts else 'No matching posts in this feed sample; no comment requests were made.')
                if check['errors']:
                    message += ' ' + ' '.join(dict.fromkeys(check['errors']))
                if cache_only:
                    message='Reused saved feeds; no new source request. ' + message
                elif check.get('cached'):
                    message='Includes previously saved feeds. ' + message
                outcome='partial' if check['errors'] and check['matched'] else 'failed' if check['errors'] else 'ready'
                c.execute('INSERT INTO provider_checks(instrument_id,provider,last_attempt_at,completed_at,outcome,message,fetched,matched) VALUES(%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(instrument_id,provider) DO UPDATE SET last_attempt_at=excluded.last_attempt_at,completed_at=excluded.completed_at,outcome=excluded.outcome,message=excluded.message,fetched=excluded.fetched,matched=excluded.matched',
                          (iid,'reddit_rss_'+kind,now,done,outcome,message,check['fetched'],check['matched']))
        c.execute('UPDATE reddit_company_checks SET lease_until=NULL,completed_at=%s,lookback_days=%s,post_count=%s,matched_count=%s,excluded_count=%s,error=%s WHERE instrument_id=%s',
                  (done,lookback_days,discovered,retained,excluded,error,iid))
    result=dict(checked=['reddit'],failures=int(bool(error)),matched=retained,posts=len(posts),comments=len(comments),
                collector=collector,message=error or f'{len(posts)} company posts and {len(comments)} replies collected through {"public HTML" if adapter else "company RSS search" if collector == "rss" else "public feeds"}.')
    if collector == 'rss':
        result['status']='partial' if error and retained else 'blocked' if error else 'cached' if cache_only else 'ready'
        return result
    if error and ('Reddit denied access.' in error or 'HTTP 403' in error or 'HTTP 401' in error or 'switched off' in error):
        result['status']='blocked'
    return result
