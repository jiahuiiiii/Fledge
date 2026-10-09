"""RSS acquisition controls; all HTTP here is simulated and DB disposable."""
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import httpx
import pytest
from thesis.db import transaction, one, rows
from thesis.research import reddit_rss as rss, reddit_research, social, sentiment
from thesis.service import Conflict
from test_market import prepare
from test_sentiment import feed
from thesis.research.citations import model_source


def comments_feed(post, now, body='Microsoft margins concern me.', key='t1_comment1'):
    from xml.sax.saxutils import escape
    root=rss.xml(feed(date=post['published_at'].isoformat()))
    root.insert(0,rss.ET.Element(rss.ATOM+'link',rel='self',href=rss.endpoint('comments',post)))
    entry=rss.ET.SubElement(root,rss.ATOM+'entry')
    for field,value in [('id',key),('content',body),('updated',(now-timedelta(seconds=10)).isoformat())]:
        rss.ET.SubElement(entry,rss.ATOM+field).text=value
    rss.ET.SubElement(entry,rss.ATOM+'link',href=post['url']+key.removeprefix('t1_')+'/')
    author=rss.ET.SubElement(entry,rss.ATOM+'author')
    rss.ET.SubElement(author,rss.ATOM+'name').text='/u/test-reader'
    return rss.ET.tostring(root)


@pytest.fixture(autouse=True)
def clocks(db, monkeypatch):
    with transaction(admin=True) as c:
        c.execute("DELETE FROM provider_clocks WHERE provider LIKE 'reddit-rss:%%'")
        c.execute("DELETE FROM public_feed_cache WHERE provider LIKE 'reddit-rss:%%'")
    monkeypatch.setattr(rss.time, 'sleep', lambda _: None)


def transport(calls, status=200, body=None, headers=None):
    def handle(request):
        calls.append(request)
        return httpx.Response(status, content=body or feed(), headers=headers or {'Content-Type':'application/atom+xml'})
    return httpx.MockTransport(handle)


@pytest.mark.parametrize('change', ['wrong_id', 'wrong_feed', 'missing_published', 'future', 'old'])
def test_original_identity_and_publication_required(change):
    now=datetime.now(timezone.utc)
    raw=feed()
    if change=='wrong_id':raw=raw.replace(b't3_abc123',b't3_otherr')
    if change=='wrong_feed':raw=raw.replace(b'/r/stocks/',b'/r/investing/')
    if change=='missing_published':raw=raw.replace(b'published>',b'updated>')
    if change=='future':raw=feed(date=(now+timedelta(days=1)).isoformat())
    if change=='old':raw=feed(date=(now-timedelta(days=8)).isoformat())
    assert rss.posts(raw,'stocks',now,7)==([],1)


def test_parse_original_post_and_bounded_window():
    now=datetime.now(timezone.utc)
    raw=feed(date=(now-timedelta(days=8)).isoformat())
    p=rss.posts(raw,'stocks',now,30)[0][0]
    assert p['post_key']==p['thread_key']=='t3_abc123'
    assert p['body'].startswith('I am concerned') and p['kind']=='post'
    assert len(p['author_hash'])==64


@pytest.mark.parametrize('raw',[b'<html>Login</html>',b'bad xml',b'<!DOCTYPE feed><feed/>',b'x'*2_000_001])
def test_pages_and_unsafe_xml_are_not_empty_success(raw):
    with pytest.raises(ValueError):rss.xml(raw)


def test_concurrent_companies_share_cache_and_honest_identity(owner):
    prepare(owner);calls=[]
    mock=transport(calls)
    with ThreadPoolExecutor(max_workers=4) as pool:
        values=list(pool.map(lambda _:rss.read('posts','stocks',transport=mock), range(4)))
    assert len(calls)==1 and len(set(values))==1
    assert calls[0].headers['User-Agent']==rss.UA
    assert str(calls[0].url)=='https://www.reddit.com/r/stocks/hot/.rss'


def test_cooldown_allows_cached_bodies_but_never_a_new_request(owner):
    prepare(owner);calls=[];mock=transport(calls)
    original=rss.read('posts','stocks',transport=mock)
    with transaction(source=True) as c:
        c.execute("UPDATE provider_clocks SET blocked_until=now()+interval '1 hour' WHERE provider='reddit-rss:all'")
    assert rss.read('posts','stocks',transport=mock,cache_only=True)==original
    with pytest.raises(Conflict,match='No recent saved'):
        rss.read('posts','investing',transport=mock,cache_only=True)
    assert len(calls)==1
    with transaction(source=True) as c:
        c.execute("UPDATE provider_clocks SET denied=true WHERE provider='reddit-rss:posts'")
    with pytest.raises(ValueError,match='denied'):
        rss.read('posts','stocks',transport=mock,cache_only=True)
    assert len(calls)==1


def test_recent_company_refresh_only_reads_cache_without_extending_live_cooldown(owner,monkeypatch):
    iid=prepare(owner);calls=[];now=datetime.now(timezone.utc)
    def read(kind,value,**kwargs):
        calls.append(kwargs.get('cache_only',False))
        if kind=='search':return feed()
        if kind=='posts':return feed() if value=='stocks' else b'<feed xmlns="http://www.w3.org/2005/Atom"/>'
        return comments_feed(value,now)
    monkeypatch.setattr(rss,'read',read)
    first=reddit_research.refresh(iid,now=now)
    mark=len(calls)
    second=reddit_research.refresh(iid,now=now+timedelta(seconds=30))
    assert first['comments']==second['comments']==1
    assert all(calls[mark:]) and second['status']=='cached'
    with transaction() as c:
        state=one(c,'SELECT * FROM reddit_company_checks WHERE instrument_id=%s',(iid,))
        assert state['last_attempt_at']==now
        assert len(social.documents(c,iid,now+timedelta(seconds=30)))==2


@pytest.mark.parametrize('status',[301,302,401,403,429])
def test_redirect_denial_and_cooldown_stop_repeated_requests(owner,status):
    prepare(owner);calls=[]
    mock=transport(calls,status,headers={'Retry-After':'7200','Location':'https://old.reddit.com/'})
    with pytest.raises(ValueError,match=f'HTTP {status}'):rss.read('posts','stocks',transport=mock)
    with pytest.raises((ValueError,Conflict)):
        rss.read('posts','stocks',transport=mock)
    assert len(calls)==1
    if status==429:
        with transaction() as c:
            clock=one(c,"SELECT * FROM provider_clocks WHERE provider='reddit-rss:all'")
        assert clock['blocked_until']>datetime.now(timezone.utc)+timedelta(minutes=119)
        with pytest.raises(Exception,match='cooling down'):
            rss.read('posts','investing',transport=mock)
        assert len(calls)==1


def test_legacy_denial_is_preserved_and_rss_is_independent(owner):
    prepare(owner);calls=[]
    with transaction(source=True) as c:
        old=one(c,'SELECT * FROM reddit_request_clock WHERE singleton')
        c.execute("UPDATE reddit_request_clock SET reason='Reddit returned HTTP 403.' WHERE singleton")
    try:
        rss.read('posts','stocks',transport=transport(calls))
        with transaction() as c:assert one(c,'SELECT reason FROM reddit_request_clock WHERE singleton')['reason']=='Reddit returned HTTP 403.'
    finally:
        with transaction(source=True) as c:c.execute('UPDATE reddit_request_clock SET reason=%s WHERE singleton',(old['reason'],))
    assert len(calls)==1


def test_feed_permission_revoked_during_collection_blocks_storage(owner):
    iid=prepare(owner)
    def get(kind,value):
        if kind=='search':
            with transaction(admin=True) as c:c.execute("UPDATE social_feeds SET enabled=false WHERE feed='stocks'")
            return feed()
        if kind=='comments':raise ValueError('Reddit RSS comments returned HTTP 429.')
        return b'<feed xmlns="http://www.w3.org/2005/Atom"/>'
    try:
        reddit_research.refresh(iid,collector='rss',fetcher=get)
        with transaction() as c:assert not rows(c,'SELECT * FROM social_posts WHERE instrument_id=%s',(iid,))
    finally:
        with transaction(admin=True) as c:c.execute("UPDATE social_feeds SET enabled=true WHERE feed='stocks'")


def test_posts_reach_analysis_even_when_comments_fail(owner):
    iid=prepare(owner)
    def get(kind,value):
        if kind=='search':
            return feed()
        raise ValueError('Reddit RSS comments returned HTTP 429. Collection stopped.')
    result=reddit_research.refresh(iid,collector='rss',fetcher=get)
    assert result['posts']==1 and result['comments']==0 and result['status']=='partial'
    with transaction() as c:
        checks={s['kind']:s for s in social.status(c,iid) if s.get('kind')}
        assert checks['posts']['outcome']=='ready'
        assert '429' in checks['comments']['error']
        packet=sentiment.prepare(c,iid,datetime.now(timezone.utc))
        assert len([s for s in packet['sources'] if s['channel']=='social'])==1


def test_no_match_does_not_request_comments(owner):
    iid=prepare(owner);calls=[]
    def get(kind,value):
        calls.append(kind)
        assert kind=='search'
        return b'<feed xmlns="http://www.w3.org/2005/Atom"/>'
    result=reddit_research.refresh(iid,collector='rss',fetcher=get)
    assert not result['failures'] and not result['matched']
    with transaction() as c:
        status=next(s for s in social.status(c,iid) if s.get('kind')=='comments')
        assert 'no comment requests' in status['notice']


def test_recorded_actual_hot_feed_when_available():
    path=Path('.local/live-tests/reddit-rss-integration-20261008/probe-20261008T072415Z/posts.body')
    if not path.exists():pytest.skip('Optional private actual-source evidence')
    found,excluded=rss.posts(path.read_bytes(),'stocks',datetime(2026,10,8,7,24,15,tzinfo=timezone.utc),7)
    assert len(found)==24 and excluded==1
    assert any(p['post_key']=='t3_1wze2hd' for p in found)


def test_comments_preserve_missing_parent_and_feed_date_basis(owner):
    iid=prepare(owner);now=datetime.now(timezone.utc)
    def get(kind,value):
        if kind=='search':return feed()
        return comments_feed(value,now)
    result=reddit_research.refresh(iid,collector='rss',fetcher=get,now=now)
    assert result['comments']==1 and result['status']=='ready'
    with transaction() as c:
        sources=social.documents(c,iid,now)
        child=next(s for s in sources if s['social_kind']=='comment')
        assert child['thread_key']=='t3_abc123' and child['timestamp_basis']=='feed_updated'
        assert not rows(c,'SELECT * FROM social_conversation_results WHERE post_id=%s',(child['id'],))
        packet=sentiment.prepare(c,iid,now)
        source=next(s for s in packet['sources'] if s.get('social_kind')=='comment')
        assert 'conversation' not in source
        assert model_source(source)['timestamp_basis']=='feed_updated'
        assert 'immediate reply parent is unavailable' in model_source(source)['source_note']
        from thesis.research import conversation
        context=conversation.present(c,child['id'])
        assert not context['can_refresh'] and context['result'] is None
        assert 'does not identify the immediate reply parent' in context['unavailable_reason']


def test_thread_title_does_not_make_contextless_reply_eligible(owner):
    iid=prepare(owner);now=datetime.now(timezone.utc)
    def get(kind,value):
        if kind=='search':return feed()
        return comments_feed(value,now,body='This! They are completely wrong.')
    result=reddit_research.refresh(iid,collector='rss',fetcher=get,now=now)
    assert result['comments']==0
    with transaction() as c:assert len(social.documents(c,iid,now))==1


@pytest.mark.parametrize('mutation',['thread','comment_link','date','future','deleted','missing_original'])
def test_comment_identity_dates_and_withdrawals(mutation):
    now=datetime.now(timezone.utc);post=rss.posts(feed(),'stocks',now,7)[0][0]
    raw=comments_feed(post,now)
    if mutation=='thread':raw=raw.replace(b'comments/abc123',b'comments/other')
    if mutation=='comment_link':raw=raw.replace(b'discussion/comment1/',b'discussion/other/')
    if mutation=='date':raw=raw.replace(b'updated>',b'undated>')
    if mutation=='future':raw=comments_feed(post,now+timedelta(days=1))
    if mutation=='deleted':raw=comments_feed(post,now,body='[deleted]')
    if mutation=='missing_original':raw=raw.replace(b't3_abc123',b't3_other')
    if mutation in ('thread','missing_original'):
        with pytest.raises(ValueError):rss.replies(raw,post,now,7)
    else:
        found,removed=rss.replies(raw,post,now,7)
        assert not found
        assert removed==(['t1_comment1'] if mutation=='deleted' else [])


def test_recorded_actual_comments_when_available():
    base=Path('.local/live-tests/reddit-rss-integration-20261008')
    path=base/'comments-20261008T073945Z/comments.body'
    if not path.exists():pytest.skip('Optional private actual-source evidence')
    now=datetime(2026,10,8,7,40,tzinfo=timezone.utc)
    original=rss.posts((base/'probe-20261008T072415Z/posts.body').read_bytes(),'stocks',now,7)[0]
    post=next(p for p in original if p['post_key']=='t3_1wze2hd')
    found,removed=rss.replies(path.read_bytes(),post,now,7)
    assert len(found)==50 and not removed
    assert all('parent' not in p and p['kind']=='comment' for p in found)
    assert found[0]['post_key']=='t1_peauk23'
    assert found[0]['body']=='It demonstrates they think NVDA is undervalued and a good investment.'


def search_value(**changes):
    return dict(dict(symbol='AVGO',name='Broadcom Inc.',feeds=['stocks','investing'],days=7),**changes)


def test_search_uses_both_ticker_and_name_with_stable_permission_scoped_url():
    from urllib.parse import urlparse,parse_qs
    value=search_value()
    url=rss.endpoint('search',value)
    assert url==rss.endpoint('search',search_value(feeds=['investing','stocks','stocks']))
    parsed=urlparse(url)
    assert parsed.netloc=='www.reddit.com' and parsed.path=='/r/investing+stocks/search.rss'
    assert parse_qs(parsed.query)==dict(q=['"AVGO" OR "Broadcom"'],restrict_sr=['on'],sort=['new'],t=['week'],limit=['50'])
    assert rss.endpoint('search',search_value(days=30))!=url
    assert rss.endpoint('search',search_value(feeds=['stocks']))!=url


@pytest.mark.parametrize('changes',[dict(symbol='AVGO/elsewhere'),dict(feeds=['stocks','private']),dict(feeds=[]),dict(days=True),dict(days=8)])
def test_search_rejects_unsupported_destinations(changes):
    with pytest.raises(ValueError):rss.endpoint('search',search_value(**changes))


@pytest.mark.parametrize('first',['search','posts'])
def test_search_and_hot_feeds_share_denial_scope(owner,first):
    prepare(owner);calls=[]
    args=dict(search=search_value(),posts='stocks')
    with pytest.raises(ValueError,match='HTTP 403'):
        rss.read(first,args[first],transport=transport(calls,403))
    other='posts' if first=='search' else 'search'
    with pytest.raises(ValueError,match='denied'):
        rss.read(other,args[other],transport=transport(calls))
    assert len(calls)==1


def test_search_cache_separates_company_window_and_enabled_feeds(owner):
    prepare(owner);calls=[];mock=transport(calls)
    first=rss.read('search',search_value(),transport=mock)
    assert rss.read('search',search_value(feeds=['investing','stocks']),transport=mock)==first
    for changes in [dict(symbol='NVDA',name='NVIDIA'),dict(days=30),dict(feeds=['stocks'])]:
        # This fixture skips sleeps; model the previous request slot elapsing.
        with transaction(source=True) as c:c.execute("UPDATE provider_clocks SET next_at=now() WHERE provider='reddit-rss:all'")
        rss.read('search',search_value(**changes),transport=mock)
    assert len(calls)==4


def test_search_discovery_keeps_feed_identity_original_dates_and_bounds():
    now=datetime.now(timezone.utc)
    root=rss.xml(feed(title='AVGO is in my portfolio',body='My position.'))
    root.append(rss.xml(feed(key='second')).find(rss.ATOM+'entry'))
    raw=rss.ET.tostring(root).replace(b'/r/stocks/comments/second/',b'/r/investing/comments/second/')
    parsed,excluded=rss.posts(raw,['stocks'],now,7,search=True)
    assert excluded==1 and len(parsed)==1
    assert parsed[0]['feed']=='stocks' and parsed[0]['method']==rss.SEARCH_METHOD
    assert social.mentions(parsed[0],'AVGO','Broadcom Inc.')
    parsed,excluded=rss.posts(raw,['stocks','investing'],now,7,search=True)
    assert len(parsed)==2 and excluded==0 and parsed[1]['feed']=='investing'
    undated=raw.replace(b'published>',b'updated>')
    assert rss.posts(undated,['stocks','investing'],now,7,search=True)==([],2)
    root=rss.xml(b'<feed xmlns="http://www.w3.org/2005/Atom"/>')
    for i in range(60):root.append(rss.xml(feed(key=f'p{i}')).find(rss.ATOM+'entry'))
    assert len(rss.posts(rss.ET.tostring(root),['stocks'],now,7,search=True)[0])==50


def test_search_and_saved_hot_feed_deduplicate_before_comment_requests(owner,monkeypatch):
    prepare(owner);calls=[];now=datetime.now(timezone.utc)
    def read(kind,value,**kwargs):
        calls.append((kind,kwargs.get('cache_only',False)))
        if kind=='search':return feed()
        if kind=='posts':
            assert kwargs['cache_only']
            return feed() if value=='stocks' else b'<feed xmlns="http://www.w3.org/2005/Atom"/>'
        return comments_feed(value,now)
    monkeypatch.setattr(rss,'read',read)
    result=rss.collect(dict(symbol='MSFT',name='Microsoft'),7,['stocks','investing'],now)
    assert len(result['posts'])==len(result['comments'])==1
    assert [kind for kind,cached in calls if not cached]==['search','comments']
    assert result['posts'][0]['method']==rss.SEARCH_METHOD


def test_failed_search_uses_saved_hot_and_comment_bodies_without_extra_network(owner,monkeypatch):
    prepare(owner);calls=[];now=datetime.now(timezone.utc)
    def read(kind,value,**kwargs):
        calls.append((kind,kwargs.get('cache_only',False)))
        if kind=='search':raise ValueError('Reddit RSS search returned HTTP 429.')
        assert kwargs['cache_only']
        if kind=='posts':return feed()
        return comments_feed(value,now)
    monkeypatch.setattr(rss,'read',read)
    result=rss.collect(dict(symbol='MSFT',name='Microsoft'),7,['stocks'],now)
    assert len(result['posts'])==len(result['comments'])==1
    assert result['error'] and all(cached for _,cached in calls[1:])


def test_actual_avgo_search_when_available():
    path=Path('.local/live-tests/reddit-rss-integration-20261008/avgo-search-20261008T082647Z/search.body')
    if not path.exists():pytest.skip('Optional private actual-source evidence')
    parsed,excluded=rss.posts(path.read_bytes(),social.FEEDS,datetime(2026,10,8,8,27,tzinfo=timezone.utc),7,search=True)
    matches=[p for p in parsed if social.mentions(p,'AVGO','Broadcom Inc.')]
    assert len(parsed)==3 and excluded==0 and len(matches)==2
    assert {p['post_key'] for p in matches}=={'t3_1wz7g0s','t3_1wvtm6k'}
    assert all(p['method']==rss.SEARCH_METHOD for p in matches)


@pytest.mark.parametrize('symbol,dedicated',[('AVGO','broadcomstock'),('NVDA','nvda_stock'),('MSFT',None)])
def test_company_communities_include_only_relevant_enabled_dedicated_feed(symbol,dedicated):
    selected=social.company_feeds(symbol,social.FEEDS)
    assert set(selected)==set(social.GENERAL_FEEDS) | ({dedicated} if dedicated else set())
    assert social.company_feeds(symbol,['stocks','private'])==['stocks']
    assert social.company_feeds(symbol,[])==[]


def test_expanded_community_is_stored_once_with_same_search_request_count(owner):
    iid=prepare(owner);calls=[];now=datetime.now(timezone.utc)
    def get(kind,value):
        calls.append(kind)
        if kind=='search':
            assert set(value['feeds'])==set(social.GENERAL_FEEDS)
            assert 'nvda_stock' not in value['feeds'] and 'broadcomstock' not in value['feeds']
            return feed().replace(b'/r/stocks/',b'/r/stockmarket/')
        return comments_feed(value,now).replace(b'/r/stocks/',b'/r/stockmarket/')
    result=reddit_research.refresh(iid,collector='rss',fetcher=get,now=now)
    assert result['posts']==1 and result['comments']==1 and calls==['search','comments']
    with transaction() as c:
        sources=social.documents(c,iid,now)
        assert len(sources)==2 and all(s['feed']=='stockmarket' for s in sources)
        status=next(s for s in social.status(c,iid) if s.get('kind')=='posts')
        assert status['communities']==list(social.GENERAL_FEEDS)
        assert 'r/securityanalysis' in status['sample_notice']
        assert not rows(c,'SELECT * FROM news_watches')


def test_new_community_disabled_during_fetch_is_not_saved(owner):
    iid=prepare(owner)
    def get(kind,value):
        if kind=='search':
            with transaction(admin=True) as c:c.execute("UPDATE social_feeds SET enabled=false WHERE feed='valueinvesting'")
            return feed().replace(b'/r/stocks/',b'/r/valueinvesting/')
        raise ValueError('No comment response in this authored case.')
    try:
        reddit_research.refresh(iid,collector='rss',fetcher=get)
        with transaction() as c:assert not social.documents(c,iid,datetime.now(timezone.utc))
    finally:
        with transaction(admin=True) as c:c.execute("UPDATE social_feeds SET enabled=true WHERE feed='valueinvesting'")


def test_provider_rejection_includes_the_next_check_time(owner):
    prepare(owner);calls=[]
    with pytest.raises(ValueError,match=r'HTTP 429.*Next check after .* UTC'):
        rss.read('search',search_value(),transport=transport(calls,429))
    assert len(calls)==1


def test_successful_response_records_exhausted_provider_window(owner,monkeypatch):
    prepare(owner);calls=[]
    headers={'Content-Type':'application/atom+xml','X-Ratelimit-Remaining':'0.0','X-Ratelimit-Reset':'53'}
    rss.read('search',search_value(),transport=transport(calls,headers=headers))
    with transaction() as c:
        quota=one(c,"SELECT next_at FROM provider_clocks WHERE provider='reddit-rss:quota'")['next_at']
    assert quota > datetime.now(timezone.utc)+timedelta(seconds=52)
    waits=[]
    def elapsed(seconds):
        waits.append(seconds)
        # Simulate actual elapsed time without sleeping in the test suite.
        with transaction(source=True) as c:c.execute("UPDATE provider_clocks SET next_at=now() WHERE provider='reddit-rss:quota'")
    monkeypatch.setattr(rss.time,'sleep',elapsed)
    rss.read('posts','stocks',transport=transport(calls))
    assert len(calls)==2 and 52 < waits[0] <= 55


def test_long_server_window_defers_without_counting_or_sending_a_request(owner):
    prepare(owner);calls=[]
    rss.remember_reset(httpx.Headers({'X-Ratelimit-Remaining':'0','X-Ratelimit-Reset':'180'}),datetime.now(timezone.utc))
    with pytest.raises(Conflict,match='request window'):
        rss.read('search',search_value(),transport=transport(calls))
    assert not calls
    with transaction() as c:
        clock=one(c,"SELECT requests FROM provider_clocks WHERE provider='reddit-rss:all'")
        assert clock is None or clock['requests']==0


def test_window_extended_by_another_worker_stops_queued_dispatch(owner,monkeypatch):
    prepare(owner);calls=[]
    monkeypatch.setattr(rss.time,'sleep',lambda _:rss.remember_reset(httpx.Headers({'X-Ratelimit-Remaining':'0','X-Ratelimit-Reset':'45'}),datetime.now(timezone.utc)))
    with pytest.raises(Conflict,match='request window'):
        rss.read('search',search_value(),transport=transport(calls))
    assert not calls


@pytest.mark.parametrize('remaining,reset',[('1','50'),('0','bad'),('0','-1'),('NaN','50'),('0','inf')])
def test_invalid_or_unexhausted_headers_do_not_create_a_pause(owner,remaining,reset):
    prepare(owner)
    rss.remember_reset(httpx.Headers({'X-Ratelimit-Remaining':remaining,'X-Ratelimit-Reset':reset}),datetime.now(timezone.utc))
    with transaction() as c:assert not one(c,"SELECT * FROM provider_clocks WHERE provider='reddit-rss:quota'")


def test_shorter_header_never_clears_a_later_window_or_429_pause(owner):
    prepare(owner);now=datetime.now(timezone.utc)
    with transaction(source=True) as c:
        c.execute("INSERT INTO provider_clocks(provider,blocked_until) VALUES('reddit-rss:all',%s)",(now+timedelta(minutes=15),))
    for seconds in [100,20]:rss.remember_reset(httpx.Headers({'X-Ratelimit-Remaining':'0','X-Ratelimit-Reset':str(seconds)}),now)
    with transaction() as c:
        assert one(c,"SELECT next_at FROM provider_clocks WHERE provider='reddit-rss:quota'")['next_at']==now+timedelta(seconds=101)
        assert one(c,"SELECT blocked_until FROM provider_clocks WHERE provider='reddit-rss:all'")['blocked_until']==now+timedelta(minutes=15)


def test_paced_rss_lease_still_rejects_expired_collection(owner):
    iid=prepare(owner);now=datetime.now(timezone.utc)
    def get(kind,value):
        if kind=='search':
            with transaction(source=True) as c:
                check=one(c,'SELECT lease_until FROM reddit_company_checks WHERE instrument_id=%s',(iid,))
                assert check['lease_until']==now+timedelta(minutes=6)
                c.execute('UPDATE reddit_company_checks SET lease_until=%s WHERE instrument_id=%s',(now-timedelta(seconds=1),iid))
            return feed()
        return comments_feed(value,now)
    with pytest.raises(Conflict,match='expired'):
        reddit_research.refresh(iid,collector='rss',fetcher=get,now=now)
    with transaction() as c:assert not social.documents(c,iid,now)
