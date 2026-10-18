"""Outcome evidence is offline and cannot turn missing data into acceptance."""
from datetime import datetime,timedelta,timezone
from decimal import Decimal
import json
from uuid import uuid4
import pytest
from experiments.soclaas_replay import redesign_outcomes as O
from thesis.db import transaction
from test_move_alerts import setup
from test_price_moves import NOW

START=datetime(2026,10,19,13,30,tzinfo=timezone.utc)
END=START+timedelta(days=12)


def check(at=START,*,status='completed',seconds=30,lane='fast',company='a',analysis='a'):
    return dict(instrument_id=company,lane=lane,started_at=at,status=status,
        completed_at=at+timedelta(seconds=seconds) if status else None,
        analysis_id=analysis,repairs=dict(total=20,repaired=1))


def assessment(at=START,*,company='a',direction='down',qualifies=True,preview=False,status='measured',run='r'):
    m=dict(session='2026-10-19',direction=direction,trigger_direction=direction,quoted_at=at.isoformat())
    return dict(instrument_id=company,observed_at=at,preview=preview,status=status,qualifies=qualifies,
        run_id=run,policy='p',already_claimed=False,payload=dict(measure=m if status=='measured' else None))


def delivery(event='e',at=START+timedelta(minutes=10),*,kind='move',status='sent',ident='d',attempt=1):
    return dict(id=ident,event_id=event,sent_at=at,status=status,kind=kind,attempts=attempt)


def member(company='a',event='e',*,triggered=True,direction='down',preview=False):
    return dict(event_id=event,instrument_id=company,created_at=START,session_date='2026-10-19',
        preview=preview,policy='p',triggered=triggered,payload=dict(direction=direction,trigger_direction=direction))


def data():
    return dict(checks=[check(),check(lane='slow',analysis='b')],calls=[],
        assessments=[assessment()],move_runs=[dict(id='r',started_at=START,error=None)],
        deliveries=[delivery()],claims=[dict(delivery_id='d',attempt=1,story_key='article')],
        move_members=[member()],feedback=[dict(id='f',kind='move',event_id='e',value='useful',created_at=START)])


def assess(d=None,*,at=END,live=True,switch=True):
    return O.assess(START,at,d if d is not None else data(),actual_delivery_confirmed=live,no_model_switch_confirmed=switch)


def test_ten_complete_sessions_and_external_gates_stay_separate():
    r=assess()
    assert r['window_complete'] and r['complete_sessions']==10
    for key in ('completion','repair_percent','stuck_companies','daily_cost_usd','switch_cost_usd',
                'useful_percent','duplicate_deliveries','moves_alerted_percent','move_latency_minutes'):
        assert r['metrics'][key]['status']=='passed',key
    assert all(m['status']=='passed' for m in r['metrics']['duration_seconds'].values())
    assert r['metrics']['low_value_percent']['status']==r['metrics']['label_quality_percent']['status']=='pending'
    assert not r['rollback_required']


def test_previews_partial_windows_and_absent_data_never_pass():
    for r in (assess(live=False),assess(at=START+timedelta(days=1))):
        assert not r['window_complete']
        assert r['metrics']['completion']['status']=='pending'
        assert not r['rollback_required']
    r=assess({})
    for key in ('completion','repair_percent','stuck_companies','useful_percent','duplicate_deliveries',
                'moves_alerted_percent','move_latency_minutes'):
        assert r['metrics'][key]['value'] is None
        assert r['metrics'][key]['status']=='pending'


def test_calendar_weekend_mid_session_early_close_and_unknown_year():
    assert len(O.sessions(START))==10
    assert O.sessions(START+timedelta(seconds=1))[0][0].day==20
    assert O.sessions(START-timedelta(days=2))[0][0].day==19
    early=datetime(2026,11,27,14,30,tzinfo=timezone.utc)
    assert O.sessions(early)[0][1].hour==13
    with pytest.raises(ValueError,match='verified'):O.sessions(datetime(2029,1,1,tzinfo=timezone.utc))
    with pytest.raises(ValueError,match='timezone'):O.assess(START.replace(tzinfo=None),END,{})
    with pytest.raises(ValueError,match='precedes'):O.assess(START,START-timedelta(seconds=1),{})


def test_completion_includes_failed_stopped_and_later_results():
    d=data();d['checks']=[check() for _ in range(97)]+[check(status=s) for s in ('failed','stopped',None)]
    assert assess(d)['metrics']['completion']['value']==97
    d['checks'][0]['completed_at']=END+timedelta(days=1)
    r=assess(d)
    assert r['metrics']['completion']==dict(value=96.0,status='failed')
    assert r['checks']['completed']==96


def test_stuck_failure_chain_boundary_and_recovery():
    d=data();d['checks']=[check(START-timedelta(hours=3),status='failed'),
        check(START+timedelta(hours=2),status='failed'),check(START+timedelta(hours=3))]
    assert assess(d)['metrics']['stuck_companies']['value']==1
    d['checks']=[check(status='failed'),check(START+timedelta(hours=1))]
    assert assess(d)['metrics']['stuck_companies']['value']==0
    d['checks']=[check(status=None)]
    assert assess(d)['metrics']['stuck_companies']['value']==1


def test_reused_analysis_is_counted_once_and_unknown_repairs_stay_unknown():
    d=data();d['checks']=[check(),check(START+timedelta(hours=1))]
    d['checks'][1]['repairs']=dict(total=20,repaired=2)
    assert assess(d)['metrics']['repair_percent']==dict(value=10.0,status='failed')
    d['checks'][1]['repairs']=None
    assert assess(d)['metrics']['repair_percent']['value'] is None


def call(day=0,usd='3',*,experiment=False,settled=True):
    return dict(created_at=START+timedelta(days=day),finished_at=START+timedelta(days=day,seconds=1) if settled else None,
        status='settled' if settled else 'unresolved',charged_nano_usd=int(Decimal(usd)*O.NANO) if settled else None,
        reserved_nano_usd=int(Decimal(usd)*O.NANO),experiment=experiment)


def test_costs_include_explainers_holds_late_settlement_and_exclude_tests_explicitly():
    d=data();d['calls']=[call(),call(usd='99',experiment=True),call(1,usd='.01',settled=False),
        call(usd='.5',experiment=True,settled=False)]
    r=assess(d)
    assert r['experiment_confirmed_usd']=='99'
    assert r['experiment_unresolved_maximum_usd']=='0.5'
    assert r['daily_windows'][0]['confirmed_usd']=='3'
    assert r['metrics']['daily_cost_usd']['status']=='pending'
    d['calls'].extend([call(1,usd='7'),call(2,usd='7')])
    r=assess(d)
    assert r['metrics']['daily_cost_usd']['status']=='failed' and r['rollback']['cost_above_6_two_days']
    d['calls']=[call()];d['calls'][0]['finished_at']=END+timedelta(days=1)
    assert assess(d)['daily_windows'][0]['confirmed_usd']=='0'
    assert assess(switch=False)['metrics']['switch_cost_usd']['status']=='pending'
    d['missing_tables']=['model_calls'];d['calls']=[]
    assert assess(d)['metrics']['daily_cost_usd']==dict(value=None,status='pending')


def test_grouped_market_event_covers_only_triggering_members_and_repeats_add_nothing():
    d=data();d['assessments'] += [assessment(company='b'),assessment(company='c',qualifies=False),assessment(START+timedelta(minutes=15))]
    d['assessments'][-1]['already_claimed']=True
    d['move_members'] += [member(company='b'),member(company='c',triggered=False)]
    r=assess(d)
    assert r['moves']['qualifying']==r['moves']['sent']==2
    assert r['metrics']['moves_alerted_percent']['value']==100
    d['move_members'][1]['triggered']=False
    assert assess(d)['metrics']['moves_alerted_percent']['value']==50
    assert assess(d)['rollback']['moves_below_70']


@pytest.mark.parametrize('change',['preview','unsent','wrong_direction','wrong_policy','prior_event'])
def test_unconfirmed_or_nonmatching_events_do_not_cover_moves(change):
    d=data()
    if change=='preview':d['move_members'][0]['preview']=True
    elif change=='unsent':d['deliveries'][0]['status']='uncertain'
    elif change=='wrong_direction':d['move_members'][0]['payload']['trigger_direction']='up'
    elif change=='wrong_policy':d['move_members'][0]['policy']='old'
    else:d['move_members'][0]['created_at']=START-timedelta(minutes=1)
    assert assess(d)['metrics']['moves_alerted_percent']['value']==0


@pytest.mark.parametrize('change',['absent','invalid','audit_error','orphan','preview'])
def test_gaps_never_turn_into_zero_missed_moves(change):
    d=data()
    if change=='absent':d['missing_tables']=['move_assessments'];d['assessments']=[]
    elif change=='invalid':d['assessments'].append(assessment(company='b',status='invalid_quote'))
    elif change=='audit_error':d['move_runs'][0]['error']='Price assessment log unavailable; detection continued.'
    elif change=='orphan':d['move_runs']=[]
    else:d['assessments'][0]['preview']=True
    r=assess(d)
    assert r['metrics']['moves_alerted_percent']['value'] is None
    assert not r['moves']['coverage_complete']


def test_alert_latency_counts_overnight_wait_and_first_qualifying_quote():
    d=data();d['deliveries'][0]['sent_at']=START+timedelta(hours=20)
    r=assess(d)
    assert r['metrics']['move_latency_minutes']==dict(value=1200.0,status='failed')
    d['assessments'].append(assessment(START+timedelta(minutes=15)))
    assert assess(d)['metrics']['move_latency_minutes']['value']==1200


def test_story_duplicates_half_open_24h_attempts_and_missing_claims():
    d=data();d['deliveries'].append(delivery(ident='d2',at=START+timedelta(minutes=20)))
    d['claims'].extend([dict(delivery_id='d2',attempt=1,story_key='article'),dict(delivery_id='d2',attempt=1,story_key='extra')])
    assert assess(d)['metrics']['duplicate_deliveries']==dict(value=1,status='failed')
    d['deliveries'][1]['sent_at']=d['deliveries'][0]['sent_at']+timedelta(days=1)
    assert assess(d)['metrics']['duplicate_deliveries']['value']==0
    d['deliveries'][1]['attempts']=2
    assert assess(d)['metrics']['duplicate_deliveries']['value'] is None


def test_material_update_url_overlap_is_unknown_not_a_false_duplicate():
    d=data();d['claims'][0]['story_key']='url:old'
    d['deliveries'].append(delivery(ident='d2',at=START+timedelta(minutes=20)))
    d['claims'].extend([dict(delivery_id='d2',attempt=1,story_key='url:old'),
        dict(delivery_id='d2',attempt=1,story_key='update:new')])
    r=assess(d)
    assert r['duplicate_evidence']==dict(confirmed=0,missing_claims=0,ambiguous_updates=1)
    assert r['metrics']['duplicate_deliveries']['status']=='pending'


def test_feedback_uses_latest_vote_per_event_and_weekly_rollback():
    d=data();d['feedback'].extend([dict(d['feedback'][0],id='f2',created_at=START+timedelta(hours=1),value='not_useful'),
        dict(d['feedback'][0],id='f3',created_at=END+timedelta(days=1))])
    r=assess(d)
    assert r['ratings']==dict(total=1,useful=0)
    assert r['rollback']['ratings_majority_not_useful'] and r['rollback_required']
    assert not assess(d,at=START+timedelta(days=6))['rollback']['ratings_majority_not_useful']


def test_collection_is_read_only_private_and_missing_migrations_are_pending(owner):
    setup(owner)
    with transaction(admin=True,consistent=True) as conn:
        frozen=O.collect(conn,owner,NOW-timedelta(days=1),NOW+timedelta(days=1))
        assert conn.execute('SHOW transaction_read_only').fetchone()['transaction_read_only']=='on'
        assert frozen['missing_tables']==[]
        assert not O.collect(conn,uuid4(),NOW-timedelta(days=1),NOW+timedelta(days=1))['checks']
        r=O.assess(NOW,NOW,frozen)
        assert str(owner) not in json.dumps(r)
        assert not r['actual_delivery_confirmed'] and not r['window_complete']
