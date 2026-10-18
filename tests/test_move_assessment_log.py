"""Passive price audit uses saved authored quotes; no source or AI requests."""
from copy import deepcopy
from datetime import timedelta
from uuid import uuid4
import psycopg
import pytest
from thesis.db import transaction,one,rows
from thesis.monitoring import move_watch as W,move_assessment_log as L,news_watch
from thesis.providers import settings
from thesis.research.sec.service import add_company
from test_move_alerts import setup
from test_price_moves import NOW
from test_model_budget import clean_model_ledger  # noqa:F401


def activate(monkeypatch):
    monkeypatch.setenv('THESIS_MOVE_ALERTS','true')
    monkeypatch.setattr(settings,'EXPLAINER_MODEL',None)


def claimed(owner):
    token=uuid4()
    with transaction(owner) as conn:
        conn.execute('INSERT INTO move_watch_state(owner_id,next_check_at,claim_token,lease_until) VALUES(%s,%s,%s,%s) '
            'ON CONFLICT(owner_id) DO UPDATE SET claim_token=excluded.claim_token,lease_until=excluded.lease_until',
            (owner,NOW,token,NOW+timedelta(minutes=15)))
    return token


def test_audit_records_both_triggers_and_context_before_publication_and_keeps_repeats(owner,monkeypatch):
    setup(owner,grouping=True);activate(monkeypatch)
    with transaction(owner,consistent=True) as c:preferences=rows(c,'SELECT * FROM news_watches ORDER BY instrument_id')
    assert W.run_once(owner,now=NOW,refresh=lambda *a:None)
    assert W.run_once(owner,now=NOW+timedelta(minutes=15),refresh=lambda *a:None)
    with transaction(owner,consistent=True) as c:
        values=rows(c,'SELECT * FROM move_assessments ORDER BY observed_at,instrument_id')
        assert len(values)==8 and sum(r['qualifies'] for r in values)==4
        assert sum(r['already_claimed'] for r in values)==2
        assert all(r['status']=='measured' and r['preview'] and r['policy']=='price-move-rules-2' for r in values)
        assert all(r['payload']['thresholds']==dict(session='3',relative='2',two_sessions='5') for r in values)
        assert len(rows(c,'SELECT * FROM move_events'))==1
        assert rows(c,'SELECT * FROM news_watches ORDER BY instrument_id')==preferences
        assert one(c,'SELECT count(*) n FROM model_calls')['n']==0


def test_non_triggering_prices_and_stale_quotes_are_retained_as_distinct_outcomes(owner,monkeypatch):
    setup(owner);activate(monkeypatch);monkeypatch.setenv('THESIS_MOVE_SESSION_PERCENT','4')
    assert W.run_once(owner,now=NOW,refresh=lambda *a:None)
    assert W.run_once(owner,now=NOW+timedelta(minutes=31),refresh=lambda *a:None)
    with transaction(owner,consistent=True) as c:
        values=rows(c,'SELECT * FROM move_assessments ORDER BY observed_at')
        assert [r['status'] for r in values]==['measured','invalid_quote']
        assert not any(r['qualifies'] for r in values)
        assert values[0]['payload']['measure']['reasons']==[]
        assert values[1]['payload']['measure'] is None and values[1]['quote_id']
        assert not rows(c,'SELECT * FROM move_events')


def test_missing_quotes_and_withheld_reference_access_are_not_counted_as_no_move(owner,monkeypatch):
    setup(owner);activate(monkeypatch)
    iid=add_company('AAPL')['instrument_id'];news_watch.configure(owner,iid,True,now=NOW)
    assert W.run_once(owner,now=NOW,refresh=lambda *a:None)
    monkeypatch.setattr(W.reference_prices,'allowed',lambda *a:False)
    assert W.run_once(owner,now=NOW+timedelta(minutes=15),refresh=lambda *a:None)
    with transaction(owner,consistent=True) as c:
        values=rows(c,'SELECT * FROM move_assessments ORDER BY observed_at')
        assert len(values)==4
        assert any(str(r['instrument_id'])==str(iid) and r['status']=='no_quote' and r['quote_id'] is None for r in values)
        assert sum(r['status']=='references_withheld' for r in values)==2


def test_log_failure_does_not_stop_detection_and_marks_the_coverage_gap(owner,monkeypatch):
    setup(owner);activate(monkeypatch)
    def unavailable(*args,**kwargs):raise ValueError('Authored private audit diagnostic')
    monkeypatch.setattr(L,'record',unavailable)
    assert W.run_once(owner,now=NOW,refresh=lambda *a:None)
    with transaction(owner,consistent=True) as c:
        assert len(rows(c,'SELECT * FROM move_events'))==1
        run=one(c,'SELECT * FROM move_watch_runs')
        assert run['status']=='completed' and run['error']=='Price assessment log unavailable; detection continued.'
        assert not rows(c,'SELECT * FROM move_assessments')
        assert one(c,'SELECT count(*) n FROM model_calls')['n']==0


def test_assessments_survive_a_later_publication_failure_without_inventing_an_alert(owner,monkeypatch):
    setup(owner);activate(monkeypatch)
    def failed(*args,**kwargs):raise ValueError('Authored publication failure')
    monkeypatch.setattr(W.move_alerts,'record',failed)
    assert W.run_once(owner,now=NOW,refresh=lambda *a:None)
    with transaction(owner,consistent=True) as c:
        assert one(c,'SELECT qualifies FROM move_assessments')['qualifies']
        assert one(c,'SELECT status FROM move_watch_runs')['status']=='failed'
        assert not rows(c,'SELECT * FROM move_events')


def test_private_immutable_audit_and_worker_membership(owner,monkeypatch):
    setup(owner);activate(monkeypatch)
    assert W.run_once(owner,now=NOW,refresh=lambda *a:None)
    with transaction(owner,consistent=True) as c:row=one(c,'SELECT * FROM move_assessments')
    with transaction(str(uuid4()),consistent=True) as c:assert not rows(c,'SELECT * FROM move_assessments')
    for command in ('UPDATE move_assessments SET preview=false WHERE id=%s','DELETE FROM move_assessments WHERE id=%s'):
        with pytest.raises(psycopg.errors.RaiseException):
            with transaction(admin=True) as c:c.execute(command,(row['id'],))
    with transaction(owner,consistent=True) as c:
        observations=[];W.snapshot(c,owner,NOW,observations=observations)
    # The worker has finished and its lease is no longer active.
    with pytest.raises(psycopg.errors.RaiseException,match='active worker'):
        with transaction(owner) as c:L.record(c,owner,row['run_id'],observations,at=NOW,preview=True)


def test_wrong_company_quote_and_duplicate_worker_observation_are_rejected(owner):
    setup(owner,grouping=True);token=claimed(owner)
    with transaction(owner,consistent=True) as c:
        observations=[];W.snapshot(c,owner,NOW,observations=observations)
    wrong=deepcopy(observations[0]);wrong['quote_id']=observations[-1]['quote_id']
    with pytest.raises(psycopg.errors.RaiseException,match='another company'):
        with transaction(owner) as c:L.record(c,owner,token,[wrong],at=NOW,preview=True)
    with transaction(owner) as c:L.record(c,owner,token,observations,at=NOW,preview=True)
    with pytest.raises(psycopg.errors.UniqueViolation):
        with transaction(owner) as c:L.record(c,owner,token,observations,at=NOW,preview=True)


def test_pure_saved_snapshot_never_persists_or_fetches(owner):
    setup(owner)
    with transaction(owner,consistent=True) as c:
        observations=[];measured=W.snapshot(c,owner,NOW,observations=observations)
        assert len(measured)==len(observations)==1
        assert not rows(c,'SELECT * FROM move_assessments')
