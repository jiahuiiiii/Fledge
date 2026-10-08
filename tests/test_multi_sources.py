"""Public-source boundary checks with authored fixtures and mocked transports."""
from datetime import datetime, timezone, timedelta
from email.utils import format_datetime
from copy import deepcopy
from uuid import uuid4
import json
import httpx
import pytest
from thesis.db import transaction, one, rows
from thesis import service
from thesis.research import source_hub as hub, x_source, sentiment, social, market_brief, sentiment_inputs, discussion_themes
from thesis.research.sec.service import add_company
from thesis.service import Conflict
from test_market import prepare

NOW=datetime.now(timezone.utc)
COMPANY={'symbol':'MSFT','name':'Microsoft'}


def rss(title='Microsoft reports a new product.', date=None, url='https://example.test/public-news', summary='The Microsoft product is under development.'):
    return f'<rss><channel><item><title>{title}</title><description>{summary}</description><link>{url}</link><pubDate>{date if date is not None else format_datetime(NOW-timedelta(hours=1))}</pubDate></item></channel></rss>'.encode()


def alpha(**overrides):
    return {'feed':[{'title':'Microsoft announces a product.', 'summary':'Microsoft says the product is in development.', 'source':'Example publisher', 'url':'https://example.test/alpha', 'time_published':(NOW-timedelta(hours=1)).strftime('%Y%m%dT%H%M%S'), 'ticker_sentiment':[{'ticker':'MSFT','ticker_sentiment_score':'0.99','ticker_sentiment_label':'Bullish'}], **overrides}]}


def xdata(**overrides):
    return {'data':[{'id':'123456','text':'Microsoft has a great product.', 'author_id':'34567','created_at':(NOW-timedelta(hours=1)).isoformat(),**overrides}]}


@pytest.fixture
def clocks(owner):
    with transaction(admin=True) as c:
        c.execute('TRUNCATE provider_clocks,public_feed_cache')
    return owner


def test_rss_and_atom_preserve_dates_and_source_text():
    items,total,rejected=hub.parse_feed('wsj_markets',rss(),COMPANY,NOW)
    assert (len(items),total,rejected)==(1,1,0)
    assert items[0]['publisher']=='Wall Street Journal · Markets'
    raw=b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Microsoft product launch</title><summary>Microsoft shared a plan.</summary><link href="https://example.test/atom"/><updated>'+NOW.isoformat().encode()+b'</updated></entry></feed>'
    assert hub.parse_feed('cnbc',raw,COMPANY,NOW)[0][0]['url'].endswith('/atom')


@pytest.mark.parametrize('date',['','undated','Sun, 01 Jan 2000 10:00:00 GMT',format_datetime(NOW+timedelta(days=1))])
def test_bad_or_missing_dates_do_not_become_fresh_news(date):
    items,total,rejected=hub.parse_feed('cnbc',rss(date=date),COMPANY,NOW)
    assert items==[] and rejected==1


@pytest.mark.parametrize('raw',[b'<html/>',b'<rss>',b'<!DOCTYPE rss [<!ENTITY x "bad">]><rss/>',b'x'*2_000_001])
def test_xml_is_bounded_and_rejects_entity_documents(raw):
    with pytest.raises(ValueError):hub.xml_root(raw)


def test_company_filter_unsafe_urls_and_scores():
    assert hub.parse_feed('cnbc',rss(title='A story elsewhere.',summary='No company mentioned.'),COMPANY,NOW)[0]==[]
    assert hub.parse_feed('cnbc',rss(url='javascript:alert(1)'),COMPANY,NOW)[0]==[]
    result,total,rejected=hub.parse_alpha(alpha(),COMPANY,NOW)
    assert len(result)==1 and 'sentiment' not in json.dumps(result,default=str)
    assert hub.parse_alpha(alpha(ticker_sentiment=[{'ticker':'AAPL'}]),COMPANY,NOW)[0]==[]
    with pytest.raises(ValueError):hub.parse_alpha({'Information':'secret quota message'},COMPANY,NOW)


def test_one_cached_feed_serves_multiple_company_checks(clocks):
    calls=[]
    transport=httpx.MockTransport(lambda req:calls.append(req) or httpx.Response(200,content=rss()))
    first,cached=hub.feed_bytes('cnbc',transport=transport)
    second,reused=hub.feed_bytes('cnbc',transport=transport)
    assert first==second and not cached and reused and len(calls)==1
    assert hub.parse_feed('cnbc',second,{'symbol':'AAPL','name':'Apple'},NOW)[0]==[]


@pytest.mark.parametrize('status',[401,403,429])
def test_rejection_suppresses_further_requests(clocks,status):
    calls=[]
    transport=httpx.MockTransport(lambda req:calls.append(req) or httpx.Response(status,headers={'Retry-After':'7200'}))
    for _ in range(2):
        with pytest.raises((ValueError,Conflict)):hub.get('cnbc',hub.FEEDS['cnbc'][1],transport=transport)
    assert len(calls)==1
    with transaction() as c:
        state=one(c,"SELECT * FROM provider_clocks WHERE provider='cnbc'")
    assert state['denied']==(status in (401,403)) and state['blocked_until']>NOW+timedelta(minutes=59)


def test_daily_caps_and_request_errors_do_not_disclose_keys(clocks):
    with transaction(admin=True) as c:
        c.execute("INSERT INTO provider_clocks(provider,requests) VALUES('alpha_vantage',25)")
    with pytest.raises(Conflict,match='daily'):hub.reserve('alpha_vantage',daily_limit=25)
    def fail(req):raise httpx.ConnectError('request with SECRETKEY',request=req)
    with pytest.raises(ValueError) as exc:
        hub.get('x','https://api.x.com/2/tweets/search/recent',params={'token':'SECRETKEY'},transport=httpx.MockTransport(fail))
    assert 'SECRETKEY' not in str(exc.value)
    with pytest.raises(ValueError,match='endpoint'):hub.get('x',hub.FEEDS['cnbc'][1])


def test_registered_sources_enter_analysis_and_respect_current_access(owner):
    iid=prepare(owner)
    result=hub.refresh(iid,'wsj_markets',fetcher=lambda _:rss())
    assert result['status']=='ready' and result['matched']==1
    with transaction() as c:
        packet=sentiment.prepare(c,iid)
        saved=[s for s in packet['sources'] if s['publisher'].startswith('Wall Street')]
        assert len(saved)==1 and saved[0]['channel']=='news'
    with transaction(admin=True) as c:
        c.execute("UPDATE sources SET entitlement='local-yahoo-history' WHERE id='news-wsj_markets'")
    with transaction() as c:
        assert all(s['id']!=saved[0]['id'] for s in sentiment.prepare(c,iid)['sources'])


def test_source_failures_and_zero_matches_remain_distinct(owner):
    iid=prepare(owner)
    failed=hub.refresh(iid,'cnbc',fetcher=lambda _:b'<html/>')
    quiet=hub.refresh(iid,'wsj_markets',fetcher=lambda _:rss(title='Another business story',summary='Unrelated company.'))
    assert failed['status']=='failed' and quiet['status']=='ready' and quiet['matched']==0
    with transaction() as c:
        assert len(rows(c,'SELECT * FROM provider_checks WHERE instrument_id=%s',(iid,)))==2


def test_cross_feed_duplicates_are_one_news_candidate(owner):
    iid=prepare(owner)
    hub.refresh(iid,'cnbc',fetcher=lambda _:rss(url='https://www.wsj.com/tech/shared?mod=business_feed'))
    hub.refresh(iid,'wsj_markets',fetcher=lambda _:rss(url='https://www.wsj.com/tech/shared?mod=technology_feed'))
    with transaction() as c:
        selected=sentiment.prepare(c,iid)
        assert len([s for s in selected['sources'] if '/shared' in s['url']])==1
        assert one(c,"SELECT count(*) n FROM documents WHERE url LIKE %s",('https://www.wsj.com/tech/shared%',))['n']==2


def test_late_collection_cannot_overwrite_new_check(owner):
    iid=prepare(owner); company,token=hub.begin(iid,'cnbc')
    with transaction(admin=True) as c:
        c.execute("UPDATE provider_checks SET attempt_id=%s WHERE instrument_id=%s",(uuid4(),iid))
    with pytest.raises(Conflict):hub.finish(iid,'cnbc',token,'ready','old result',articles=[])


def test_disabled_connections_never_make_requests(owner):
    iid=prepare(owner)
    assert hub.refresh(iid,'alpha_vantage')['status']=='blocked'
    assert x_source.refresh(iid)['status']=='blocked'
    assert hub.refresh_rss(iid)['status']=='blocked'


@pytest.mark.parametrize('patch',[
 {'referenced_tweets':[{'type':'quoted','id':'2345'}]}, {'id':'unsafe/id'},
 {'created_at':(NOW+timedelta(hours=1)).isoformat()}, {'text':'A completely unrelated post.'}])
def test_x_excludes_unresolved_context_unsafe_ids_and_wrong_target(patch):
    assert x_source.parse(xdata(**patch),COMPANY,NOW)[0]==[]


def test_x_remains_a_separate_original_source_and_can_be_withdrawn(owner):
    iid=prepare(owner)
    result=x_source.refresh(iid,fetcher=lambda _:xdata())
    assert result['status']=='ready' and result['matched']==1
    with transaction() as c:
        post=next(p for p in social.documents(c,iid,datetime.now(timezone.utc)) if p['platform']=='x')
        assert post['author_hash']!='34567' and social.publisher(post)=='X · public posts'
        current=sentiment_inputs.current(c,iid)
        assert current['scopes']['x']['selected']==1
    with transaction(admin=True) as c:
        c.execute("UPDATE social_feeds SET enabled=false WHERE feed='x'")
    with transaction() as c:
        assert not any(p['platform']=='x' for p in social.documents(c,iid,datetime.now(timezone.utc)))
    with transaction(admin=True) as c:c.execute("UPDATE social_feeds SET enabled=true WHERE feed='x'")


def test_x_window_is_applied_even_if_provider_returns_older_post(owner):
    iid=prepare(owner)
    result=x_source.refresh(iid,lookback_days=1,fetcher=lambda _:xdata(created_at=(NOW-timedelta(days=2)).isoformat()))
    assert result['matched']==0


def test_x_themes_do_not_use_generic_title_as_evidence():
    source=dict(id='x:1234',label='item_1',channel='social',platform='x',title='X post',text='Microsoft has a great product.',publisher='X',published_at=NOW.isoformat())
    request=discussion_themes.request_for({'sources':[source],'company':COMPANY})
    supplied=json.loads(request['input'][1]['content'])['sources'][0]
    assert supplied['scope']=='x' and all(p['id']!='p0' for p in supplied['passages'])


def test_public_feed_allows_only_bounded_same_host_redirects(clocks):
    calls=[]
    def respond(request):
        calls.append(str(request.url))
        return httpx.Response(302,headers={'Location':'/rss/localized?hl=en'}) if len(calls)==1 else httpx.Response(200,content=rss())
    body=hub.get('google_business',hub.FEEDS['google_business'][1],transport=httpx.MockTransport(respond))
    assert body==rss() and len(calls)==2
    calls=[]
    def wrong(request):
        calls.append(str(request.url));return httpx.Response(302,headers={'Location':'https://other.test/feed'})
    with pytest.raises(ValueError,match='redirected'):
        hub.get('cnbc',hub.FEEDS['cnbc'][1],transport=httpx.MockTransport(wrong))
    assert len(calls)==1


def test_concurrent_company_reads_share_one_feed_request(clocks):
    from concurrent.futures import ThreadPoolExecutor
    calls=[]
    transport=httpx.MockTransport(lambda request: calls.append(request) or httpx.Response(200,content=rss()))
    with ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(lambda _:hub.feed_bytes("cnbc",transport=transport),range(4)))
    assert len(calls)==1 and sum(cached for _,cached in results)==3


def test_x_requires_verified_empty_result():
    with pytest.raises(ValueError):x_source.parse({},COMPANY,NOW)
    assert x_source.parse({"meta":{"result_count":0}},COMPANY,NOW)==([],0)
