from datetime import datetime, timedelta, timezone
from uuid import uuid4
import httpx
import psycopg
import pytest
from thesis.db import transaction, rows
from thesis.monitoring import news_watch, watch_history
from thesis.research import source_observations as metrics, market, source_hub
from experiments.soclaas_replay.lane_readiness import assess, report
from test_market import prepare
from test_multi_sources import rss

START=datetime(2026,10,17,tzinfo=timezone.utc)


def sample(lane,seconds):
    return dict(lane=lane,started_at=START,completed_at=START+timedelta(seconds=seconds),status='completed')


def event(hours,status=200):
    return dict(provider='finnhub',observed_at=START+timedelta(hours=hours),http_status=status)


def assessment(checks=None,events=None,hours=72,confirmed=True,baseline=24):
    return assess(START-timedelta(hours=baseline),START,START+timedelta(hours=hours),
                  checks if checks is not None else [sample('fast',60),sample('slow',180)],
                  events if events is not None else [event(-1),event(1)],deployment_confirmed=confirmed)


def test_exact_boundaries_and_partial_unknown_baseline_cannot_pass():
    assert assessment()['passed']
    assert not assessment(hours=71.99)['passed']
    assert not assessment(confirmed=False)['passed']
    assert not assessment(baseline=23.99)['passed']
    assert not assessment(events=[])['passed']
    assert not assessment(checks=[])['passed']


def test_slow_or_fast_excess_and_missing_completions_fail():
    assert assessment([sample('fast',60.01),sample('slow',180)])['gates']['fast']=='failed'
    assert assessment([sample('fast',60),sample('slow',181)])['gates']['slow']=='failed'
    unfinished=sample('fast',1);unfinished['status']=None
    assert assessment([sample('fast',60),sample('slow',180),unfinished])['gates']['completion']=='failed'


def test_denial_comparison_uses_each_provider_and_equal_day_rates():
    events=[event(-1,429),event(1,429),event(25,403),event(49,401)]
    assert assessment(events=events)['gates']['provider_denials']=='passed'
    assert assessment(events=events+[event(50,429)])['gates']['provider_denials']=='failed'
    assert assessment(events=[event(-1),event(1,429)])['gates']['provider_denials']=='failed'
    assert assessment(events=[event(-1),event(1,503)])['gates']['provider_denials']=='passed'


def test_metrics_are_off_until_requested_and_http_denials_record_no_body_or_keys(owner,monkeypatch):
    prepare(owner)
    monkeypatch.setenv('THESIS_SENTIMENT_LANES','false')
    monkeypatch.setenv('THESIS_SOURCE_METRICS','false')
    before=0
    with transaction(admin=True) as c:before=len(rows(c,'SELECT * FROM source_request_events'))
    metrics.record('finnhub',200)
    with transaction(admin=True) as c:assert len(rows(c,'SELECT * FROM source_request_events'))==before
    monkeypatch.setenv('THESIS_SOURCE_METRICS','true')
    monkeypatch.setattr(market,'key',lambda:'authored-secret')
    monkeypatch.setattr(market,'reserve_request',lambda:None)
    with pytest.raises(ValueError,match='denied'):
        market.fetch('quote',{'symbol':'MSFT'},transport=httpx.MockTransport(lambda _:httpx.Response(429,text='must-not-save')))
    with transaction(admin=True) as c:
        event=rows(c,'SELECT * FROM source_request_events ORDER BY observed_at DESC LIMIT 1')[0]
        assert event['http_status']==429 and event['provider']=='finnhub'
        assert 'must-not-save' not in str(event) and 'authored-secret' not in str(event)
    with pytest.raises(psycopg.Error):
        with transaction(admin=True) as c:c.execute('UPDATE source_request_events SET http_status=200 WHERE id=%s',(event['id'],))


def test_request_observations_inherit_thread_context_and_do_not_leak_watch_ids(owner,monkeypatch):
    iid=prepare(owner);now=datetime.now(timezone.utc);token=uuid4()
    news_watch.configure(owner,iid,True,now=now)
    with transaction(owner) as c:
        watch=rows(c,'SELECT * FROM news_watches WHERE owner_id=%s',(owner,))[0]
        watch_history.start(c,owner,watch,token,now,now+timedelta(minutes=15))
    monkeypatch.setenv('THESIS_SOURCE_METRICS','true')
    marker=metrics.CHECK.set(token)
    try:
        def get(_):
            assert metrics.CHECK.get()==token
            metrics.record('cnbc',200)
            return rss()
        source_hub.refresh_rss(iid,fetcher=get)
    finally:metrics.CHECK.reset(marker)
    with transaction(owner) as c:assert rows(c,'SELECT check_id FROM source_request_events WHERE check_id=%s',(token,))
    with transaction(str(uuid4())) as c:assert not rows(c,'SELECT check_id FROM source_request_events WHERE check_id=%s',(token,))
    since=now+timedelta(seconds=.001)
    # Read-only CLI query path against the disposable DB, never the app DB.
    value=report(now-timedelta(days=1),since,as_of=datetime.now(timezone.utc))
    assert not value['passed'] and str(owner) not in str(value) and str(token) not in str(value)
