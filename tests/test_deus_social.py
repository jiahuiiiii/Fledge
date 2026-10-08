"""Authored source controls, real PostgreSQL roles, mocked transports only."""
from datetime import datetime, timezone, timedelta
from copy import deepcopy
import httpx
import pytest
from thesis.db import transaction, one, rows
from thesis.research import reddit_research as reddit, social, hackernews as hn, sentiment
from test_market import prepare
from test_sentiment import feed, provider
from test_hackernews import item


def thread(post, now):
    return [dict(data=dict(children=[dict(kind='t3',data=dict(name=post['post_key'],subreddit='stocks',title=post['title'],selftext=post['body'],created_utc=post['published_at'].timestamp()))])),
            dict(data=dict(children=[dict(kind='t1',data=dict(name='t1_reply1',parent_id=post['post_key'],body='I disagree with that optimistic outlook.',author='reader',created_utc=now.timestamp()-5))]))]


def reddit_transport(now, *, denial=False):
    def get(kind,post=None):
        if kind=='search':
            return feed(date=(now-timedelta(minutes=1)).isoformat())
        if denial:
            raise httpx.HTTPStatusError('denied',request=httpx.Request('GET','https://www.reddit.com'),response=httpx.Response(429))
        return thread(post,now)
    return get


def test_company_collection_keeps_replies_and_parent_separate(owner):
    iid=prepare(owner);now=datetime.now(timezone.utc)
    result=reddit.refresh(iid,fetcher=reddit_transport(now),now=now)
    assert result['posts']==1 and result['comments']==1 and not result['failures']
    with transaction() as c:
        sources=social.documents(c,iid,now)
        assert len(sources)==2
        child=next(p for p in sources if p['social_kind']=='comment')
        assert child['title']=='Reddit comment' and child['match_basis']=='thread'
        packet=sentiment.prepare(c,iid,now)
        child=next(p for p in packet['sources'] if p.get('social_kind')=='comment')
        assert child['conversation']['title'] != child['title']
        assert child['conversation']['body'] not in child['text']
    result=sentiment.generate(iid,now=now,transport=provider())
    assert result['summary']['social_platforms']['reddit']['selected']==2
    with pytest.raises(Exception,match='recently'):
        reddit.refresh(iid,fetcher=lambda *_:pytest.fail('Repeated collection'),now=now)


def test_denial_preserves_discovered_posts_and_stops_enrichment(owner):
    iid=prepare(owner); now=datetime.now(timezone.utc)
    result=reddit.refresh(iid,fetcher=reddit_transport(now,denial=True),now=now)
    assert result['failures']==1 and result['comments']==0
    with transaction() as c:
        assert len(social.documents(c,iid,now))==1
        status=social.status(c,iid)[0]
        assert '429' in status['error'] and status['matched_count']==1


def test_thread_identity_and_immediate_parent_required():
    now=datetime.now(timezone.utc)
    post=social.parse_feed(feed(), 'stocks',now)[0][0]
    raw=thread(post,now)
    raw[0]['data']['children'][0]['data']['name']='t3_wrong'
    with pytest.raises(ValueError,match='identity'):
        reddit.replies(raw,post,now,7)
    raw=thread(post,now)
    raw[1]['data']['children'][0]['data']['parent_id']='t3_elsewhere'
    assert reddit.replies(raw,post,now,7)==([],[])


def test_removed_parent_withholds_reply_and_saved_reading(owner):
    iid=prepare(owner);now=datetime.now(timezone.utc)
    reddit.refresh(iid,fetcher=reddit_transport(now),now=now)
    sentiment.generate(iid,now=now,transport=provider())
    with transaction(source=True) as c:
        c.execute("INSERT INTO social_withdrawals VALUES('t3_abc123',%s)",(now,))
    with transaction() as c:
        assert social.documents(c,iid,now)==[]
        assert sentiment.latest(c,iid)['withheld']


def test_thread_only_reply_without_parent_is_not_sent_to_model(owner):
    iid=prepare(owner);now=datetime.now(timezone.utc)
    reddit.refresh(iid,fetcher=reddit_transport(now),now=now)
    with transaction(source=True) as c:
        c.execute('UPDATE social_conversation_state SET latest_result_id=NULL')
    with transaction() as c:
        packet=sentiment.prepare(c,iid,now)
        assert not any(s.get('discovery_match')=='thread' for s in packet['sources'])


def test_thread_diversity_and_exact_whitespace_duplicates():
    posts=[dict(platform='reddit',title='Comment',body=f'Opinion {i}',post_key=str(i),thread_key='one') for i in range(5)]
    posts += [dict(platform='reddit',title='Comment',body='Other view',post_key='6',thread_key='two'),
              dict(platform='reddit',title='Comment',body='Other   view',post_key='7',thread_key='three')]
    assert len(social.balanced(posts))==3


def test_hn_thread_replies_verified_without_attributing_title(owner):
    iid=prepare(owner);now=datetime.now(timezone.utc)
    calls=[]
    story=dict(id=99,type='story',title='Microsoft earnings outlook',time=int((now-timedelta(hours=1)).timestamp()),kids=[123,124])
    def get(kind,value,clock):
        calls.append((kind,value))
        if kind=='search':return dict(hits=[])
        if kind=='stories':return dict(hits=[dict(objectID='99')])
        if str(value)=='99':return story
        return item(str(value),'I disagree with the growth prediction.',now)
    result=hn.refresh(iid,fetcher=get,now=now,include_threads=True)
    assert not result['failures']
    with transaction() as c:
        posts=social.documents(c,iid,now)
        assert len(posts)==2 and all(p['title']=='Hacker News comment' for p in posts)
        packet=sentiment.prepare(c,iid,now)
        assert len(packet['sources'])==2
        assert all(s['conversation']['title']==story['title'] for s in packet['sources'] if s['channel']=='social')


def test_hn_unrelated_story_cannot_admit_reply(owner):
    iid=prepare(owner);now=datetime.now(timezone.utc)
    def get(kind,value,clock):
        if kind=='search':return dict(hits=[])
        if kind=='stories':return dict(hits=[dict(objectID='99')])
        assert str(value)=='99'
        return dict(id=99,type='story',title='A broadcasting show',time=int(now.timestamp()),kids=[123])
    hn.refresh(iid,fetcher=get,now=now,include_threads=True)
    with transaction() as c:assert not social.documents(c,iid,now)


def test_hn_search_uses_exact_company_and_no_typo_expansion(owner,monkeypatch):
    prepare(owner)
    requests=[]
    def handler(request):
        requests.append(request)
        return httpx.Response(200,json=dict(hits=[]))
    real=httpx.Client
    monkeypatch.setattr(httpx,'Client',lambda **kwargs: real(transport=httpx.MockTransport(handler),**kwargs))
    hn.fetch('search','MSFT',datetime.now(timezone.utc))
    params=requests[0].url.params
    assert params['query']=='"Microsoft"' and params['typoTolerance']=='false' and params['queryType']=='prefixNone'


def test_reddit_rate_limit_stops_other_requests(owner,monkeypatch):
    prepare(owner)
    with transaction(source=True) as c:
        c.execute('UPDATE reddit_request_clock SET next_at=now(),blocked_until=NULL')
    calls=[]
    def handler(request):
        calls.append(request)
        return httpx.Response(429,headers={'Retry-After':'3600'})
    real=httpx.Client
    monkeypatch.setattr(httpx,'Client',lambda **kwargs: real(transport=httpx.MockTransport(handler),**kwargs))
    with pytest.raises(httpx.HTTPStatusError):reddit.request('https://www.reddit.com/r/stocks/search.rss',atom=True)
    with pytest.raises(Exception,match='cooling down'):reddit.request('https://www.reddit.com/r/investing/search.rss',atom=True)
    assert len(calls)==1
    with transaction(source=True) as c:c.execute('UPDATE reddit_request_clock SET blocked_until=NULL,next_at=now()')


def test_reddit_rejects_untrusted_destination():
    with pytest.raises(ValueError,match='Unsupported'):
        reddit.request('https://example.com/r/stocks/search.rss',atom=True)


def test_reddit_access_denial_stays_blocked_after_cooldown(owner,monkeypatch):
    prepare(owner)
    with transaction(source=True) as c:
        c.execute("UPDATE reddit_request_clock SET next_at=now(),blocked_until=now()-interval '1 day',reason='Reddit returned HTTP 403.'")
    monkeypatch.setattr(httpx,'Client',lambda **kwargs:pytest.fail('Access denial must not be retried'))
    try:
        with pytest.raises(ValueError,match='approved Reddit connection'):
            reddit.request('https://www.reddit.com/r/stocks/search.rss',atom=True)
    finally:
        with transaction(source=True) as c:
            c.execute('UPDATE reddit_request_clock SET blocked_until=NULL,next_at=now(),reason=NULL')


def test_hn_direct_reply_acquires_immediate_context(owner):
    iid=prepare(owner);now=datetime.now(timezone.utc)
    def get(kind,value,clock):
        if kind=='search':return dict(hits=[dict(objectID='123')])
        if kind=='stories':return dict(hits=[])
        if str(value)=='123':return item('123','Microsoft has an agreement with them.',now)
        assert str(value)=='99'
        return dict(id=99,type='comment',text='Do they work with the company?',time=int((now-timedelta(hours=1)).timestamp()),parent=98)
    hn.refresh(iid,fetcher=get,now=now,include_threads=True)
    with transaction() as c:
        source=next(s for s in sentiment.prepare(c,iid,now)['sources'] if s['channel']=='social')
        assert source['conversation']['parent_key']=='hn:99'
        assert source['conversation']['body']=='Do they work with the company?'
        assert source['discovery_match']=='direct'
