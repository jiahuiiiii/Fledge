"""Changed-feed reuse and daily original checks; mocked sources only."""
from datetime import datetime, timedelta, timezone
import pytest
from thesis.db import transaction, one, rows
from thesis.research import reddit_rss as rss, reddit_research as reddit, hackernews as hn
from test_market import prepare
from test_sentiment import feed
from test_reddit_rss import comments_feed
from test_hackernews import item


@pytest.fixture(autouse=True)
def clean_cache(db):
    with transaction(admin=True) as c:
        c.execute('DELETE FROM reddit_thread_checks')
        c.execute("DELETE FROM provider_clocks WHERE provider LIKE 'reddit-rss:%%'")


def post_feed(published,updated):
    raw=feed(date=published.isoformat())
    if updated is not None:
        raw=raw.replace(b'</entry>', ('<updated>'+updated.isoformat()+'</updated></entry>').encode())
    return raw


def collect(iid,published,updated,now,calls,**kw):
    def get(kind,value):
        if kind=='search':return post_feed(published,updated)
        if kind=='comments':
            calls.append(kind)
            return comments_feed(value,now)
        raise AssertionError('Unexpected live community fetch')
    return reddit.refresh(iid,now=now,collector='rss',fetcher=get,incremental=True,**kw)


def test_unchanged_known_thread_reuses_exact_comments_then_changed_update_fetches(owner):
    iid=prepare(owner);now=datetime.now(timezone.utc)
    published=now-timedelta(hours=1);updated=now-timedelta(minutes=1);calls=[]
    first=collect(iid,published,updated,now,calls)
    second=collect(iid,published,updated,now+timedelta(hours=1),calls)
    assert calls==['comments'] and first['comments']==second['comments']==1
    collect(iid,published,now+timedelta(minutes=30),now+timedelta(hours=2),calls)
    assert calls==['comments','comments']


def test_unknown_update_does_not_claim_thread_unchanged(owner):
    iid=prepare(owner);now=datetime.now(timezone.utc);calls=[]
    for offset in (0,1):collect(iid,now-timedelta(hours=1),None,now+timedelta(hours=offset),calls)
    assert len(calls)==2
    with transaction() as c:assert not rows(c,'SELECT * FROM reddit_thread_checks')


def test_denied_comments_cannot_return_retained_body(owner):
    iid=prepare(owner);now=datetime.now(timezone.utc);calls=[]
    published=now-timedelta(hours=1);updated=now-timedelta(minutes=1)
    collect(iid,published,updated,now,calls)
    with transaction(source=True) as c:
        c.execute("INSERT INTO provider_clocks(provider,denied) VALUES('reddit-rss:comments',true)")
    value=collect(iid,published,updated,now+timedelta(hours=1),calls)
    assert value['comments']==0 and value['failures']==1 and len(calls)==1


def test_invalid_comment_response_never_advances_thread_checkpoint(owner):
    iid=prepare(owner);now=datetime.now(timezone.utc)
    def get(kind,value):return post_feed(now-timedelta(hours=1),now-timedelta(minutes=1)) if kind=='search' else b'broken'
    assert reddit.refresh(iid,now=now,collector='rss',fetcher=get,incremental=True)['failures']==1
    with transaction() as c:assert not rows(c,'SELECT * FROM reddit_thread_checks')


def test_hn_seen_comments_skip_for_24_hours_new_comments_still_fetch_and_withdrawals_apply(owner):
    iid=prepare(owner);now=datetime.now(timezone.utc);calls=[];keys=['123']
    def get(kind,value,clock):
        if kind=='search':return dict(hits=[dict(objectID=k) for k in keys])
        calls.append(str(value))
        return item(str(value),now=now) if clock<now+timedelta(days=1) else dict(id=int(value),deleted=True)
    hn.refresh(iid,fetcher=get,now=now,incremental=True)
    keys.append('124')
    hn.refresh(iid,fetcher=get,now=now+timedelta(hours=1),incremental=True)
    assert calls==['123','124']
    hn.refresh(iid,fetcher=get,now=now+timedelta(days=1,minutes=1),incremental=True)
    assert calls==['123','124','123']
    with transaction() as c:
        assert one(c,"SELECT post_key FROM hn_withdrawals WHERE post_key='hn:123'")


def test_hn_daily_recheck_rotates_retained_sample_instead_of_starving_old_comments(owner):
    iid=prepare(owner);now=datetime.now(timezone.utc);keys=[str(k) for k in range(100,120)];calls=[]
    def get(kind,value,clock):
        if kind=='search':return dict(hits=[dict(objectID=k) for k in keys])
        calls.append(str(value));return item(str(value),now=now)
    hn.refresh(iid,fetcher=get,now=now,incremental=True)
    # Discover more than the eight retained-check slots in two samples.
    hn.refresh(iid,fetcher=get,now=now+timedelta(hours=1),incremental=True)
    keys.clear();calls.clear()
    hn.refresh(iid,fetcher=get,now=now+timedelta(days=1,hours=2),incremental=True)
    first=set(calls);calls.clear()
    hn.refresh(iid,fetcher=get,now=now+timedelta(days=1,hours=3),incremental=True)
    assert len(first)==8 and calls and not first.intersection(calls)
