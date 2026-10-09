"""Company discovery and honest check summaries; authored data only."""
from copy import deepcopy
from datetime import datetime, timezone
from urllib.parse import urlsplit, parse_qs
import pytest
from thesis.db import transaction, one
from thesis.research import catalogue, loading, reddit_rss, reddit_research, hackernews, source_hub, market
from test_market import prepare
from test_multi_sources import rss
from test_sentiment import feed


@pytest.mark.parametrize('symbol,name,search,text', [
    ('QCOM','QUALCOMM INC/DE','QUALCOMM','Qualcomm announced a new chip.'),
    ('AMD','ADVANCED MICRO DEVICES INC','AMD','AMD released a processor.'),
    ('MRVL','Marvell Technology, Inc.','Marvell','Marvell raised its outlook.'),
    ('MU','MICRON TECHNOLOGY INC','Micron','Micron plans a new factory.'),
    ('AAPL','Apple','Apple','Apple reports its results.'),
    ('FN','Fabrinet','Fabrinet','Fabrinet reports revenue.'),
])
def test_search_and_original_matching_share_company_names(symbol,name,search,text):
    assert catalogue.company_search_name(symbol,name)==search
    assert catalogue.mentions(text,symbol,name)
    url=reddit_rss.endpoint('search',dict(symbol=symbol,name=name,days=7,feeds=['stocks']))
    query=parse_qs(urlsplit(url).query)['q'][0]
    assert query==f'"{symbol}"'+(f' OR "{search}"' if search!=symbol else '')
    assert 'INC DE' not in query


@pytest.mark.parametrize('name,expected',[
    ('QUALCOMM INC/DE','QUALCOMM'),('Example Corporation /CA/','Example'),
    ('Example INC DE','Example INC DE'),('Example/Global Inc.','Example Global'),
    ('Example/US','Example US'),
])
def test_only_explicit_issuer_annotations_are_removed(name,expected):
    assert catalogue.company_alias(name)==expected


@pytest.mark.parametrize('text,symbol,name',[
    ('A five micron process.','MU','MICRON TECHNOLOGY INC'),
    ('amd is a lowercase fragment.','AMD','ADVANCED MICRO DEVICES INC'),
    ('Marvellous work.','MRVL','Marvell Technology, Inc.'),
    ('Qualcommish','QCOM','QUALCOMM INC/DE'),
    ('Marvell','MRVL','Unrelated Issuer Inc.'),
    ('Micron','MU','Unrelated Issuer Inc.'),
    ('It is all on the table.','ALL','Allstate Corp'),
])
def test_ambiguous_words_and_wrong_identities_remain_excluded(text,symbol,name):
    assert not catalogue.mentions(text,symbol,name)


def test_qualcomm_publisher_and_reddit_originals_are_not_dropped():
    now=datetime.now(timezone.utc)
    company=dict(symbol='QCOM',name='QUALCOMM INC/DE')
    assert len(source_hub.parse_feed('cnbc',rss(title='Qualcomm reports results.',summary='Its business grew.'),company,now)[0])==1
    raw=feed(title='Qualcomm reports results.').replace(b'Microsoft',b'Qualcomm')
    result=reddit_rss.collect(company,7,['stocks'],now,fetcher=lambda kind,value: raw if kind=='search' else b'<feed xmlns="http://www.w3.org/2005/Atom"/>')
    assert len(result['posts'])==1


def test_no_reddit_posts_does_not_claim_replies_were_checked(owner):
    iid=prepare(owner)
    result=reddit_research.refresh(iid,collector='rss',fetcher=lambda *_:b'<feed xmlns="http://www.w3.org/2005/Atom"/>')
    assert result['status']=='ready'
    assert 'Comments were not checked' in result['message']
    assert '7-day sample' in result['message']


def test_cached_reddit_message_does_not_claim_new_collection():
    message=reddit_research.reddit_sample_message(3,4,30,True)
    assert 'no new source request' in message and '30-day feed sample' in message


def test_legacy_publisher_message_does_not_invent_successful_feed_count():
    message=source_hub.rss_sample_message(2,None,1,3)
    assert '2 report matches' in message
    assert 'across' not in message and 'No publisher feeds' not in message


def test_publisher_summary_separates_matches_waits_and_failures(monkeypatch):
    monkeypatch.setattr(source_hub,'FEEDS',dict(a=(),b=(),c=()))
    monkeypatch.setattr(source_hub,'refresh',lambda iid,p,**kw: {'a':dict(status='ready',matched=2),'b':dict(status='cached'),'c':dict(status='failed')}[p])
    result=source_hub.refresh_rss('unused')
    assert result['status']=='partial'
    assert '2 report matches across 1 checked' in result['message']
    assert '1 failed checks' in result['message'] and '1 checks deferred' in result['message']


def test_legacy_summary_is_read_only_and_does_not_project_unrelated_failure(owner):
    iid=prepare(owner)
    run=loading.start(owner,iid)
    result=deepcopy(run)
    result['steps']=[
        dict(key='reddit',status='cached',message='0 company posts and 0 replies collected through company RSS search.'),
        dict(key='rss',status='cached',message='0 matching publisher reports; 0 failed checks; 11 checks deferred by the refresh schedule. Open source coverage for details.'),
        dict(key='hackernews',status='ready',message='0 company-related comments verified across direct mentions and discussions.'),
        dict(key='market',status='ready',message='Source check complete'),
        dict(key='reddit',status='failed',message='Unrelated failure.'),
    ]
    original=deepcopy(result)
    with transaction(owner,consistent=True) as c:
        visible=loading.explain_source_counts(c,result)
        unchanged=one(c,'SELECT steps FROM research_loads WHERE id=%s',(run['id'],))['steps']
    assert result==original and unchanged==run['steps']
    assert 'no new source request' in visible['steps'][0]['message']
    assert 'No publisher feeds were checked' in visible['steps'][1]['message']
    assert 'limited sample' in visible['steps'][2]['message']
    assert visible['steps'][-1]['message']=='Unrelated failure.'
    assert 'saved_coverage' in visible and 'saved_coverage' not in result


def test_saved_coverage_respects_current_permissions(owner):
    iid=prepare(owner)
    source_hub.refresh(iid,'cnbc',fetcher=lambda _:rss())
    run=loading.start(owner,iid)
    before=loading.latest(owner,iid)['saved_coverage']
    assert before['news']>0
    with transaction(admin=True) as c:
        c.execute("UPDATE sources SET entitlement='local-yahoo-history' WHERE id='news-cnbc'")
    try:
        assert loading.latest(owner,iid)['saved_coverage']['news']==before['news']-1
    finally:
        with transaction(admin=True) as c:
            c.execute("UPDATE sources SET entitlement='public-news' WHERE id='news-cnbc'")


def test_hn_uses_short_search_but_keeps_original_verification(owner,monkeypatch):
    import httpx
    prepare(owner)
    calls=[]
    client=httpx.Client
    def response(request):
        calls.append(request)
        return httpx.Response(200,json=dict(hits=[]))
    monkeypatch.setattr(hackernews.httpx,'Client',lambda **kw:client(**kw,transport=httpx.MockTransport(response)))
    hackernews.fetch('search','QCOM',datetime.now(timezone.utc),company_name='QUALCOMM INC/DE')
    assert calls[0].url.params['query']=='"QUALCOMM"'
    assert calls[0].url.params['restrictSearchableAttributes']=='comment_text'
    assert 'created_at_i>' in calls[0].url.params['numericFilters']


def test_switched_off_discussions_are_not_successful_empty_checks(owner):
    iid=prepare(owner)
    with transaction(admin=True) as c:
        c.execute('UPDATE social_feeds SET enabled=false')
    try:
        for collector in (reddit_research,hackernews):
            result=collector.refresh(iid,fetcher=lambda *_:pytest.fail('Source is off'))
            assert result['status']=='blocked' and 'no discussion check' in result['message']
    finally:
        with transaction(admin=True) as c:
            c.execute('UPDATE social_feeds SET enabled=true')
