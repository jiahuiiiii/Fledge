"""Daily membership and spending use disposable storage and mocked AI only."""
from contextlib import contextmanager
from datetime import datetime,date,timedelta,timezone
from decimal import Decimal
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import pytest
import psycopg
from psycopg.types.json import Jsonb
from fastapi.testclient import TestClient
from thesis.db import transaction,one,rows
from thesis import service,review_digest
from thesis.monitoring import daily_updates as D,alert_routing as R
from thesis.providers import ledger
from test_model_budget import clean_model_ledger  # noqa:F401

NOW=datetime(2026,10,18,0,0,tzinfo=timezone.utc)


def enable(monkeypatch,*,since='2026-10-17T00:00:00Z'):
    monkeypatch.setenv('THESIS_DAILY_REPORTS','true')
    monkeypatch.setenv('THESIS_DAILY_REPORTS_STARTED_AT',since)


def medium(owner,monkeypatch):
    from test_idea_alerts import setup,provider
    from thesis.research import idea_alerts
    iid,_,reading=setup(owner)
    idea_alerts.generate(owner,iid,reading['id'],transport=provider('risk'))
    event=review_digest.prepare(owner)['records'][0]
    now=datetime.now(timezone.utc)
    with transaction(owner) as conn:R.save(conn,owner,event,now=now)
    enable(monkeypatch,since=(now-timedelta(minutes=1)).isoformat())
    end=D.occurrence(now.astimezone(D.SGT).date()+timedelta(days=1),420,D.SGT)
    return event,now,end


def model_call(*,created,charged=None,reserved=10_000_000_000,finished=None,owner=None,key=None):
    identity=uuid4()
    with transaction(admin=True) as conn:
        conn.execute('INSERT INTO model_calls(id,request_key,request_hash,purpose,model,price_version,request_body,'
            'reserved_nano_usd,status,charged_nano_usd,created_at,finished_at,owner_id) '
            'VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
            (identity,key or 'authored:'+str(identity),'0'*64,'Authored cost fixture',ledger.MODEL,ledger.PRICE_VERSION,
             Jsonb(dict(authored=True)),reserved,'settled' if charged is not None else 'unresolved',charged,created,finished,owner))
    return identity


def test_off_or_missing_start_never_creates_records_or_uses_a_provider(owner,monkeypatch):
    monkeypatch.setattr(ledger,'execute',lambda *_a,**_k:pytest.fail('Daily report called AI'))
    assert not D.enabled() and D.run_once(owner,now=NOW)==0
    assert not D.history(owner)['enabled']
    monkeypatch.setenv('THESIS_DAILY_REPORTS','true')
    assert D.run_once(owner,now=NOW)==0 and D.cost_threshold() is None
    with transaction(owner) as c:assert not rows(c,'SELECT * FROM daily_digests')


def test_frozen_medium_membership_is_private_and_opening_does_not_review_or_pay(owner,monkeypatch):
    event,now,end=medium(owner,monkeypatch);before=ledger.snapshot()
    assert D.run_once(owner,now=end)==1 and D.run_once(owner,now=end)==0
    history=D.history(owner,now=end);assert len(history['digests'])==1
    digest=history['digests'][0];assert digest['total']==1 and digest['preview']
    read=D.read(owner,digest['id']);assert read['total']==1 and read['records'][0]['id']==event['id']
    assert not read['records'][0]['review_action'] and ledger.snapshot()==before
    with transaction(owner) as c:
        assert not rows(c,'SELECT * FROM idea_alert_reviews')
        assert not rows(c,'SELECT * FROM telegram_deliveries')
    other=uuid4()
    with transaction(admin=True) as c:c.execute("INSERT INTO accounts VALUES(%s,'Authored other account')",(other,))
    assert not D.history(other,now=end)['digests'] and D.history(other,now=end)['today_spend'] is None
    with pytest.raises(service.Missing):D.read(other,digest['id'])
    with pytest.raises(psycopg.errors.RaiseException):
        with transaction(admin=True) as c:c.execute("DELETE FROM daily_digest_members WHERE digest_id=%s",(digest['id'],))


def test_membership_rejects_wrong_publication_and_saved_rows_cannot_be_edited(owner,monkeypatch):
    event,now,end=medium(owner,monkeypatch)
    with transaction(owner) as c:
        route=one(c,'SELECT * FROM alert_routing_decisions')
        digest=D.make_digest(c,owner,now-timedelta(minutes=1),end,end)
    with pytest.raises(psycopg.errors.RaiseException):
        with transaction(owner) as c:
            c.execute('INSERT INTO daily_digest_members VALUES(%s,%s,1,%s,%s,%s)',
                (owner,digest,route['id'],'move',event['id']))
    with pytest.raises(psycopg.errors.RaiseException):
        with transaction(admin=True) as c:c.execute('UPDATE daily_digests SET window_end=window_start')


def test_source_withdrawal_withholds_digest_details_without_changing_frozen_membership(owner,monkeypatch):
    _,_,end=medium(owner,monkeypatch);D.run_once(owner,now=end)
    digest=D.history(owner,now=end)['digests'][0]
    with transaction(admin=True) as c:
        c.execute("UPDATE sources SET entitlement='local-stockanalysis-targets' WHERE id='finnhub-news'")
    value=D.read(owner,digest['id']);assert value['total']==1
    assert value['records'][0]['detail']['withheld'] and not value['records'][0]['detail']['items']


def test_daily_schedule_catches_up_one_window_at_a_time_and_keeps_boundary_routes_in_next_day(owner,monkeypatch):
    event,now,end=medium(owner,monkeypatch)
    with transaction(owner) as c:
        first=D.next_digest(c,owner,now,end)
        assert first and first[0]==now and first[1]==end
        assert D.next_digest(c,owner,now,end-timedelta(microseconds=1)) is None
    assert D.run_once(owner,now=end+timedelta(days=2))==1
    assert D.run_once(owner,now=end+timedelta(days=2,minutes=1))==1
    with transaction(owner) as c:
        ds=rows(c,'SELECT * FROM daily_digests ORDER BY window_end')
        assert len(ds)==2 and ds[0]['window_end']==ds[1]['window_start']
        assert one(c,'SELECT count(*) n FROM daily_digest_members')['n']==1


def test_latest_route_policy_and_unique_publication_prevent_daily_duplicates(owner,monkeypatch):
    event,now,end=medium(owner,monkeypatch)
    with transaction(owner) as c:
        r=one(c,'SELECT * FROM alert_routing_decisions')
        c.execute('INSERT INTO alert_routing_decisions VALUES(%s,%s,%s,%s,%s,%s,%s,true,%s,%s,%s)',
            (uuid4(),owner,r['kind'],r['event_id'],'authored-new-policy','medium','digest','Authored reroute',Jsonb({}),now+timedelta(seconds=1)))
    assert D.run_once(owner,now=end)==1
    digest=D.history(owner,now=end)['digests'][0]
    assert D.read(owner,digest['id'])['total']==1


def test_confirmed_spend_includes_shared_private_and_experiment_charges_but_separates_holds(owner,monkeypatch):
    monkeypatch.setattr(D,'OWNER',owner)
    created=datetime(2026,10,17,1,tzinfo=timezone.utc)
    model_call(created=created,charged=2_000_000_000,finished=created,owner=owner)
    model_call(created=created,charged=3_000_000_000,finished=created,key='experiment:authored-cost')
    other=uuid4()
    with transaction(admin=True) as c:c.execute("INSERT INTO accounts VALUES(%s,'Authored other account')",(other,))
    model_call(created=created,charged=500_000_000,finished=created,owner=other)
    model_call(created=created,reserved=700_000_000)
    value=D.spend(owner,date(2026,10,17),now=NOW)
    assert value['charged_usd']=='5.5' and value['pending_max_usd']=='0.7'
    assert value['experiment_charged_usd']=='3' and value['settled_calls']==3 and value['pending_calls']==1
    assert 'owner_id' not in value and D.spend(uuid4(),date(2026,10,17),now=NOW) is None


def test_singapore_midnight_uses_half_open_dispatch_day_and_future_settlement_is_still_pending(owner,monkeypatch):
    monkeypatch.setattr(D,'OWNER',owner);start,end=D.day_bounds(date(2026,10,17))
    model_call(created=start,charged=100,finished=start)
    model_call(created=end,charged=200,finished=end)
    model_call(created=start+timedelta(hours=1),charged=300,reserved=400,finished=NOW+timedelta(seconds=1))
    value=D.spend(owner,date(2026,10,17),now=NOW)
    assert value['charged_nano_usd']==100 and value['pending_max_nano_usd']==400
    assert start.hour==16 and end-start==timedelta(days=1)


def test_strict_cost_boundary_and_late_settlement_create_one_notice_without_rewriting_report(owner,monkeypatch):
    enable(monkeypatch);monkeypatch.setattr(D,'OWNER',owner);monkeypatch.setenv('THESIS_DAILY_COST_ALERT_USD','5')
    created=datetime(2026,10,17,1,tzinfo=timezone.utc)
    model_call(created=created,charged=5_000_000_000,finished=created)
    pending=model_call(created=created,reserved=1)
    D.run_once(owner,now=NOW)
    with transaction(owner) as c:
        assert not rows(c,'SELECT * FROM daily_cost_notices')
        frozen=one(c,'SELECT * FROM daily_spend_reports')
        assert frozen['charged_nano_usd']==5_000_000_000 and frozen['pending_max_nano_usd']==1
    later=NOW+timedelta(minutes=2)
    with transaction(admin=True) as c:
        c.execute("UPDATE model_calls SET status='settled',charged_nano_usd=1,finished_at=%s WHERE id=%s",(later,pending))
    D.run_once(owner,now=later);D.run_once(owner,now=later+timedelta(minutes=1))
    with transaction(owner) as c:
        assert one(c,'SELECT count(*) n FROM daily_cost_notices')['n']==1
        assert one(c,'SELECT * FROM daily_spend_reports WHERE id=%s',(frozen['id'],))==frozen
    value=D.history(owner,now=later)
    current=next(v for v in value['spending'] if v['day']==date(2026,10,17))['current']
    assert current['charged_usd']=='5.000000001' and current['pending_max_usd']=='0'


@pytest.mark.parametrize('value',['NaN','Infinity','0','-5','0.000001','5.001','1000001','not a number'])
def test_invalid_cost_level_is_rejected(value,monkeypatch):
    monkeypatch.setenv('THESIS_DAILY_COST_ALERT_USD',value)
    with pytest.raises(ValueError):D.cost_threshold()


def test_full_installation_costs_are_database_read_only(owner,monkeypatch):
    from thesis import db
    monkeypatch.setattr(D,'OWNER',owner);original=D.transaction;observed=[]
    @contextmanager
    def checked(*args,**kwargs):
        assert kwargs==dict(admin=True,consistent=True)
        with original(*args,**kwargs) as c:
            observed.append(one(c,'SHOW transaction_read_only')['transaction_read_only']);yield c
    monkeypatch.setattr(D,'transaction',checked)
    D.spend(owner,date(2026,10,17),now=NOW);assert observed==['on']


def test_endpoints_require_auth_and_foreign_daily_id_is_unavailable(owner,monkeypatch):
    import thesis.app as module
    monkeypatch.setattr(module,'OWNER',owner)
    client=TestClient(module.app,base_url='http://127.0.0.1')
    assert client.get('/api/v1/daily-updates').status_code==401
    client.get('/api/v1/session')
    assert client.get('/api/v1/daily-updates').json()['result']['enabled'] is False
    enable(monkeypatch)
    assert client.get('/api/v1/daily-updates/'+str(uuid4())).status_code==404
    assert client.get('/api/v1/daily-updates/not-a-uuid').status_code==422


def test_preparation_failure_is_sanitized_and_cannot_propagate_into_delivery(owner,monkeypatch,caplog):
    monkeypatch.setattr(D,'run_once',lambda *_:(_ for _ in ()).throw(ValueError('Private source detail')))
    assert D.poll(owner)==0
    assert 'existing alerts and delivery continue' in caplog.text and 'Private source detail' not in caplog.text


def test_high_route_and_foreign_owner_cannot_be_added_to_a_daily_digest(owner,monkeypatch):
    event,now,end=medium(owner,monkeypatch)
    high=uuid4();other=uuid4()
    with transaction(owner) as c:
        c.execute("INSERT INTO alert_routing_decisions VALUES(%s,%s,'idea',%s,'authored-high','high','telegram',true,'High',%s,%s)",
            (high,owner,event['id'],Jsonb({}),now+timedelta(seconds=1)))
        digest=D.make_digest(c,owner,now-timedelta(minutes=1),end,end)
        assert one(c,'SELECT count(*) n FROM daily_digest_members')['n']==0
    with pytest.raises(psycopg.errors.RaiseException):
        with transaction(owner) as c:
            c.execute("INSERT INTO daily_digest_members VALUES(%s,%s,0,%s,'idea',%s)",(owner,digest,high,event['id']))
    with transaction(admin=True) as c:c.execute("INSERT INTO accounts VALUES(%s,'Authored other account')",(other,))
    with pytest.raises(psycopg.errors.RaiseException):
        with transaction(other) as c:
            c.execute("INSERT INTO daily_digest_members VALUES(%s,%s,0,%s,'idea',%s)",(other,digest,high,event['id']))


def test_exact_boundary_route_is_captured_in_the_following_window(owner,monkeypatch):
    event,now,end=medium(owner,monkeypatch)
    with transaction(owner) as c:
        c.execute("INSERT INTO alert_routing_decisions VALUES(%s,%s,'idea',%s,'authored-boundary','medium','digest',true,'Medium',%s,%s)",
            (uuid4(),owner,event['id'],Jsonb({}),end))
        first=D.make_digest(c,owner,now-timedelta(minutes=1),end,end)
        second=D.make_digest(c,owner,end,end+timedelta(days=1),end+timedelta(days=1))
    assert D.read(owner,first)['total']==0 and D.read(owner,second)['total']==1


def test_pagination_returns_every_frozen_member_once(owner,monkeypatch):
    from test_idea_alerts import setup,provider
    from thesis.research import idea_alerts
    from thesis.models import SaveIdea
    iid,_,reading=setup(owner)
    for revision in range(23):
        if revision:
            service.save_idea(owner,SaveIdea(instrument_id=iid,expected_revision=revision,
                question='Authored question '+str(revision),reasoning='Authored reasoning '+str(revision),status='draft',conditions=[]))
        idea_alerts.generate(owner,iid,reading['id'],transport=provider('risk'))
    report=review_digest.prepare(owner,exporting=True);assert report['total']==23
    now=datetime.now(timezone.utc)
    with transaction(owner) as c:
        for event in report['records']:R.save(c,owner,event,now=now)
    enable(monkeypatch,since=(now-timedelta(minutes=1)).isoformat())
    end=D.occurrence(now.astimezone(D.SGT).date()+timedelta(days=1),420,D.SGT)
    D.run_once(owner,now=end)
    digest=D.history(owner,now=end)['digests'][0]
    first,second=D.read(owner,digest['id']),D.read(owner,digest['id'],page=1)
    assert first['total']==second['total']==23 and len(first['records'])==20 and len(second['records'])==3
    assert len({r['id'] for r in first['records']+second['records']})==23


def test_concurrent_workers_prepare_one_digest_without_blocking_the_other_worker(owner,monkeypatch):
    _,_,end=medium(owner,monkeypatch);entered,release=Event(),Event();original=D.make_digest
    def slow(*args,**kwargs):
        entered.set();assert release.wait(10)
        return original(*args,**kwargs)
    monkeypatch.setattr(D,'make_digest',slow)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first=pool.submit(D.run_once,owner,now=end)
        assert entered.wait(10)
        assert pool.submit(D.run_once,owner,now=end).result(timeout=3)==0
        release.set();assert first.result(timeout=10)==1
    with transaction(owner) as c:assert one(c,'SELECT count(*) n FROM daily_digests')['n']==1


def test_oversized_digest_is_rejected_before_any_partial_record_is_written(owner,monkeypatch):
    _,now,end=medium(owner,monkeypatch)
    monkeypatch.setattr(D,'rows',lambda *_a,**_k:[{}]*1001)
    with pytest.raises(ValueError,match='no partial'):
        with transaction(owner) as c:D.make_digest(c,owner,now-timedelta(minutes=1),end,end)
    with transaction(owner) as c:assert not rows(c,'SELECT * FROM daily_digests')


def test_failed_preparation_has_a_visible_safe_status_and_backs_off_without_blocking_alerts(owner,monkeypatch):
    enable(monkeypatch);monkeypatch.setattr(D,'clock',lambda:NOW);calls=[];original=D.make_digest
    def broken(*args,**kwargs):calls.append(True);raise ValueError('Authored private evidence must not appear')
    monkeypatch.setattr(D,'make_digest',broken)
    assert D.poll(owner)==0 and D.run_once(owner,now=NOW+timedelta(minutes=1))==0
    assert calls==[True]
    status=D.history(owner,now=NOW)['preparation']
    assert status['error']=='preparation_failed' and 'private evidence' not in status['error_message']
    assert status['next_check_at']==NOW+timedelta(hours=1)
    monkeypatch.setattr(D,'make_digest',original)
    assert D.run_once(owner,now=NOW+timedelta(hours=1))==1
    assert D.history(owner,now=NOW+timedelta(hours=1))['preparation']['error'] is None


def test_late_settlement_is_not_skipped_after_failed_poll_backoff(owner,monkeypatch):
    enable(monkeypatch);monkeypatch.setattr(D,'OWNER',owner);monkeypatch.setenv('THESIS_DAILY_COST_ALERT_USD','5')
    created=NOW-timedelta(days=1)
    model_call(created=created,charged=5_000_000_000,finished=created)
    pending=model_call(created=created,reserved=1)
    assert D.run_once(owner,now=NOW)==2
    failed_at=NOW+timedelta(minutes=2)
    original=D.next_digest
    monkeypatch.setattr(D,'clock',lambda:failed_at)
    monkeypatch.setattr(D,'next_digest',lambda *_:(_ for _ in ()).throw(ValueError('Authored temporary error')))
    assert D.poll(owner)==0
    settled_at=failed_at+timedelta(minutes=1)
    with transaction(admin=True) as c:
        c.execute("UPDATE model_calls SET status='settled',charged_nano_usd=1,finished_at=%s WHERE id=%s",(settled_at,pending))
    monkeypatch.setattr(D,'next_digest',original)
    D.run_once(owner,now=failed_at+timedelta(hours=1))
    with transaction(owner) as c:
        assert one(c,'SELECT count(*) n FROM daily_cost_notices')['n']==1
        assert one(c,'SELECT last_success_at FROM daily_updates_state')['last_success_at']==failed_at+timedelta(hours=1)
