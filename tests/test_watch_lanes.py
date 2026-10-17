"""Independent source lanes, clocks, permissions and rollback; no network."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Event
from uuid import uuid4

import pytest
import psycopg
from thesis.db import transaction, one, rows
from thesis.monitoring import news_watch as W, watch_history, watch_context, watch_lanes as lanes
from thesis.monitoring.us_session import fast_interval, next_fast_check
from thesis.research import sentiment
from thesis.providers import ledger
from test_market import prepare
from test_sentiment import provider


def due(owner):
    iid=prepare(owner)
    now=datetime.now(timezone.utc)
    W.configure(owner,iid,True,now=now-timedelta(minutes=61))
    return iid,now


def analyze(now):
    return lambda iid:sentiment.generate(iid,now=now,transport=provider())


@pytest.mark.parametrize('stamp,want', [
    ('2026-10-16T12:29:59+00:00',60),('2026-10-16T12:30:00+00:00',15),
    ('2026-10-16T21:00:00+00:00',60),('2026-11-02T13:30:00+00:00',15),
    ('2026-11-26T16:00:00+00:00',60),('2026-11-27T18:59:59+00:00',15),
    ('2026-11-27T19:00:00+00:00',60),('2026-10-17T16:00:00+00:00',60),
    ('2027-07-05T16:00:00+00:00',60),('2028-07-03T17:59:59+00:00',15),
    ('2029-10-17T16:00:00+00:00',60),
])
def test_market_window_dst_holidays_early_close_and_unknown_year(stamp,want):
    assert fast_interval(datetime.fromisoformat(stamp)) == want


def test_hourly_check_does_not_skip_start_of_fast_window():
    now=datetime.fromisoformat('2026-10-16T12:10:00+00:00')
    assert next_fast_check(now)==datetime.fromisoformat('2026-10-16T12:30:00+00:00')
    with pytest.raises(ValueError):fast_interval(now.replace(tzinfo=None))


def test_off_by_default_never_creates_fast_runtime_state(owner,monkeypatch):
    iid,now=due(owner)
    monkeypatch.delenv('THESIS_SENTIMENT_LANES',raising=False)
    assert not lanes.enabled()
    assert not W.run_once(owner,now=now,lane='fast')
    with transaction(owner) as c:
        assert not rows(c,'SELECT * FROM fast_watch_state')


def test_fast_check_does_not_fetch_social_or_change_slow_runtime(owner,monkeypatch):
    iid,now=due(owner);monkeypatch.setenv('THESIS_SENTIMENT_LANES','true')
    slow_token=uuid4()
    with transaction(owner) as c:
        c.execute("UPDATE news_watches SET claim_token=%s,lease_until=%s,error='Authored slow failure' WHERE owner_id=%s AND instrument_id=%s",
                  (slow_token,now+timedelta(minutes=10),owner,iid))
        before=one(c,'SELECT * FROM news_watches WHERE owner_id=%s AND instrument_id=%s',(owner,iid))
    market=[]
    assert W.run_once(owner,now=now,lane='fast',market_refresh=lambda i:market.append(i),
                      social_refresh=lambda:pytest.fail('Fast check reached social'),analyzer=analyze(now))
    with transaction(owner) as c:
        after=one(c,'SELECT * FROM news_watches WHERE owner_id=%s AND instrument_id=%s',(owner,iid))
    for key in ('claim_token','lease_until','error','next_check_at','interval_minutes','last_check_at'):
        assert before[key] == after[key]
    assert market == [iid]
    check=watch_history.history(owner,iid)['items'][0]
    assert check['status']=='completed' and check['lane']=='fast'
    assert check['interval_minutes']==fast_interval(now)
    assert check['details']['social']=='separate_slow_lane'
    with transaction(owner,consistent=True) as c:
        status=lanes.present(c,owner,iid)
        assert status['lanes_enabled'] and status['fast_check']['last_check_at']==now
        assert status['error']=='Authored slow failure'
    with transaction(str(uuid4()),consistent=True) as c:assert lanes.present(c,owner,iid) is None


def test_slow_check_skips_news_collection(owner,monkeypatch):
    iid,now=due(owner);monkeypatch.setenv('THESIS_SENTIMENT_LANES','true')
    social=[]
    assert W.run_once(owner,now=now,market_refresh=lambda _:pytest.fail('Slow check reached news'),
                      social_refresh=lambda:social.append(True),analyzer=analyze(now))
    check=watch_history.history(owner,iid)['items'][0]
    assert social == [True] and check['lane']=='slow' and check['status']=='completed'
    assert check['details']['market']=='separate_fast_lane'


def test_same_company_fast_check_finishes_while_slow_source_is_waiting(owner,monkeypatch):
    iid,now=due(owner);monkeypatch.setenv('THESIS_SENTIMENT_LANES','true')
    record=sentiment.generate(iid,now=now,transport=provider())
    before=ledger.snapshot()['calls']
    waiting,release=Event(),Event()
    def slow_source():
        waiting.set()
        assert release.wait(10)
    with ThreadPoolExecutor(max_workers=2) as pool:
        slow=pool.submit(W.run_once,owner,now=now,social_refresh=slow_source,analyzer=lambda _:record)
        try:
            assert waiting.wait(5)
            fast=pool.submit(W.run_once,owner,now=now,lane='fast',market_refresh=lambda _:None,
                             social_refresh=lambda:pytest.fail('Fast waited on social'),analyzer=lambda _:record)
            assert fast.result(timeout=5)
        finally:
            release.set()
        assert slow.result(timeout=5)
    checks=watch_history.history(owner,iid)['items']
    assert {c['lane'] for c in checks}=={'fast','slow'}
    assert all(c['status']=='completed' for c in checks)
    assert ledger.snapshot()['calls']==before


def test_owner_edit_stops_fast_work_before_analysis(owner,monkeypatch):
    iid,now=due(owner);monkeypatch.setenv('THESIS_SENTIMENT_LANES','true')
    def stop(_):W.configure(owner,iid,False,now=now)
    assert W.run_once(owner,now=now,lane='fast',market_refresh=stop,
                      analyzer=lambda _:pytest.fail('Stopped watch reached model'))
    check=watch_history.history(owner,iid)['items'][0]
    assert check['status']=='stopped'
    with transaction(owner) as c:assert not rows(c,'SELECT * FROM fast_watch_state')


def test_fast_renewal_readonly_history_and_owner_isolation(owner,monkeypatch):
    iid,now=due(owner);monkeypatch.setenv('THESIS_SENTIMENT_LANES','true')
    token=uuid4()
    with transaction(owner) as c:
        watch=lanes.claim_fast(c,owner,now,token)
        watch_history.start(c,owner,watch,token,now,now+timedelta(minutes=15))
    watch_context.require_active(owner,iid,token,now+timedelta(minutes=14),renew=True)
    with transaction(owner,consistent=True) as c:
        check=one(c,'SELECT * FROM watch_checks WHERE id=%s',(token,))
        assert watch_history.present(c,owner,check,None,now+timedelta(minutes=16))['status']=='running'
        assert one(c,'SELECT lease_until FROM news_watches WHERE owner_id=%s AND instrument_id=%s',(owner,iid))['lease_until'] is None
    other=str(uuid4())
    with transaction(other) as c:assert not rows(c,'SELECT * FROM fast_watch_state')
    with pytest.raises(W.WatchStopped):watch_context.require_active(owner,iid,uuid4(),now,renew=True)
    monkeypatch.setenv('THESIS_SENTIMENT_LANES','false')
    with pytest.raises(W.WatchStopped):watch_context.require_active(owner,iid,token,now)


def test_new_history_interval_constraint_is_lane_specific(owner):
    iid,now=due(owner)
    with transaction(owner) as c:
        watch=one(c,'SELECT * FROM news_watches WHERE owner_id=%s AND instrument_id=%s',(owner,iid))
    with pytest.raises(psycopg.errors.CheckViolation):
        with transaction(owner) as c:
            watch_history.start(c,owner,dict(watch,lane='slow',interval_minutes=15),uuid4(),now,now+timedelta(minutes=15))
