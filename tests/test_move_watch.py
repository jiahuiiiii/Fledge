"""Independent price-preview worker; every source/model action is mocked."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event
from uuid import uuid4
from psycopg.types.json import Jsonb
import pytest
from thesis.db import transaction, one, rows
from thesis.monitoring import move_watch as W, news_watch
from thesis.providers import settings
from test_move_alerts import setup
from test_price_moves import NOW


def test_default_off_never_creates_state_or_fetches(owner,monkeypatch):
    monkeypatch.delenv('THESIS_MOVE_ALERTS',raising=False)
    setup(owner)
    assert not W.run_once(owner,now=NOW,refresh=lambda *a:pytest.fail('Disabled worker fetched'))
    with transaction(owner,consistent=True) as c:assert not rows(c,'SELECT * FROM move_watch_state')


def test_enabled_worker_groups_saved_prices_and_never_calls_unselected_explainer(owner,monkeypatch):
    setup(owner,grouping=True)
    monkeypatch.setenv('THESIS_MOVE_ALERTS','true')
    monkeypatch.setattr(settings,'EXPLAINER_MODEL',None)
    refreshes=[]
    assert W.run_once(owner,now=NOW,refresh=lambda companies,now:refreshes.append(companies))
    assert not W.run_once(owner,now=NOW+timedelta(minutes=1),refresh=lambda *a:pytest.fail('Early source request'))
    assert W.run_once(owner,now=NOW+timedelta(minutes=15),refresh=lambda *a:None)
    with transaction(owner,consistent=True) as c:
        events=rows(c,'SELECT * FROM move_events')
        assert len(events)==1 and events[0]['preview'] and events[0]['event_type']=='market'
        assert len(rows(c,'SELECT * FROM move_trigger_claims'))==2
        assert not rows(c,'SELECT * FROM move_explainer_attempts')
        runs=rows(c,'SELECT * FROM move_watch_runs ORDER BY started_at')
        assert [r['events_created'] for r in runs]==[1,0]
        assert all(r['status']=='completed' for r in runs)
    assert len(refreshes)==1


def test_two_session_rebound_uses_decline_claim_and_does_not_repeat(owner,monkeypatch):
    from test_price_moves import quote,history
    _,ids=setup(owner);iid=ids['MSFT'];at=NOW+timedelta(seconds=1)
    qid,rid,hid=uuid4(),uuid4(),uuid4();saved=history();saved['bars'][0]['close']='107'
    with transaction(admin=True) as c:
        c.execute("INSERT INTO sources VALUES('yahoo-price-history','Authored daily prices','local-yahoo-history') ON CONFLICT DO NOTHING")
    with transaction(source=True) as c:
        c.execute('INSERT INTO market_quotes VALUES(%s,%s,%s,%s)',(qid,iid,Jsonb(quote('101',stamp=at)),at))
        c.execute('INSERT INTO reference_price_snapshots VALUES(%s,%s,%s,%s,%s,%s,%s)',
                  (rid,'QQQ','quote',Jsonb({}),Jsonb(quote('101',stamp=at)),'1'*64,at))
        c.execute("UPDATE reference_refresh_state SET current_id=%s WHERE symbol='QQQ' AND resource='quote'",(rid,))
        c.execute('INSERT INTO price_history_snapshots VALUES(%s,%s,%s,%s,%s,%s,%s)',
                  (hid,iid,'MSFT',Jsonb({}),Jsonb(saved),'2'*64,NOW))
        c.execute('INSERT INTO price_history_state(instrument_id,current_id) VALUES(%s,%s)',(iid,hid))
    monkeypatch.setenv('THESIS_MOVE_ALERTS','true');monkeypatch.setattr(settings,'EXPLAINER_MODEL',None)
    assert W.run_once(owner,now=at,refresh=lambda *a:None)
    assert W.run_once(owner,now=at+timedelta(minutes=15),refresh=lambda *a:None)
    with transaction(owner,consistent=True) as c:
        events=rows(c,'SELECT * FROM move_events')
        assert len(events)==1 and events[0]['direction']=='down'
        assert events[0]['payload']['members'][0]['direction']=='up'
        assert one(c,'SELECT direction FROM move_trigger_claims')['direction']=='down'
        assert [r['events_created'] for r in rows(c,'SELECT * FROM move_watch_runs ORDER BY started_at')]==[1,0]


def test_workers_do_not_queue_behind_same_owner_lease(owner,monkeypatch):
    setup(owner);monkeypatch.setenv('THESIS_MOVE_ALERTS','true')
    waiting,release=Event(),Event()
    def pause(*a):waiting.set();assert release.wait(10)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first=pool.submit(W.run_once,owner,now=NOW,refresh=pause)
        try:
            assert waiting.wait(5)
            assert not W.run_once(owner,now=NOW,refresh=lambda *a:pytest.fail('Duplicate source request'))
        finally:release.set()
        assert first.result(timeout=5)


@pytest.mark.parametrize('how',['disable','replace','expire','stop_watch'])
def test_cancelled_expired_or_replaced_work_cannot_publish(owner,monkeypatch,how):
    event,ids=setup(owner);monkeypatch.setenv('THESIS_MOVE_ALERTS','true')
    def change(*a):
        if how=='disable':monkeypatch.setenv('THESIS_MOVE_ALERTS','false')
        elif how=='stop_watch':news_watch.configure(owner,ids['MSFT'],False,now=NOW)
        else:
            with transaction(owner) as c:
                if how=='replace':c.execute('UPDATE move_watch_state SET claim_token=%s WHERE owner_id=%s',(uuid4(),owner))
                else:c.execute('UPDATE move_watch_state SET lease_until=%s WHERE owner_id=%s',(NOW-timedelta(seconds=1),owner))
    assert W.run_once(owner,now=NOW,refresh=change,explainer=lambda *a:pytest.fail('Stopped worker called AI'))
    with transaction(owner,consistent=True) as c:assert not rows(c,'SELECT * FROM move_events')


def test_source_failure_and_explainer_failure_do_not_retry_or_break_later_events(owner,monkeypatch):
    setup(owner);monkeypatch.setenv('THESIS_MOVE_ALERTS','true')
    def failure(*a):raise ValueError('Authored private provider diagnostic')
    assert W.run_once(owner,now=NOW,refresh=failure)
    with transaction(owner,consistent=True) as c:
        record=one(c,'SELECT * FROM move_watch_runs')
        assert record['status']=='failed' and 'private provider diagnostic' not in record['error']
    assert W.run_once(owner,now=NOW+timedelta(minutes=15),refresh=lambda *a:None,explainer=failure)
    with transaction(owner,consistent=True) as c:
        assert len(rows(c,'SELECT * FROM move_events'))==1
        assert one(c,'SELECT * FROM move_watch_runs ORDER BY started_at DESC LIMIT 1')['status']=='completed'


def test_market_hours_stale_quotes_and_explicit_thresholds(owner,monkeypatch):
    setup(owner);monkeypatch.setenv('THESIS_MOVE_ALERTS','true')
    assert not W.run_once(owner,now=NOW+timedelta(days=2),refresh=lambda *a:pytest.fail('Weekend source request'))
    with pytest.raises(ValueError):W.run_once(owner,now=NOW.replace(tzinfo=None))
    monkeypatch.setenv('THESIS_MOVE_SESSION_PERCENT','4')
    assert W.run_once(owner,now=NOW,refresh=lambda *a:None)
    with transaction(owner,consistent=True) as c:assert not rows(c,'SELECT * FROM move_events')
    monkeypatch.setenv('THESIS_MOVE_SESSION_PERCENT','3')
    assert W.run_once(owner,now=NOW+timedelta(minutes=31),refresh=lambda *a:None)
    with transaction(owner,consistent=True) as c:assert not rows(c,'SELECT * FROM move_events')
