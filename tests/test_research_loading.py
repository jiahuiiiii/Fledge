"""Isolated queue and source-window checks; no live provider traffic."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import pytest
from thesis.db import transaction, one
from thesis.research import loading, catalogue, social, sentiment, hackernews
from thesis.providers import ledger
from thesis.monitoring import news_watch
from test_market import prepare
from test_sentiment import feed, provider
from test_model_budget import body, clean_model_ledger


def test_first_open_is_idempotent_and_never_queues_paid_work(owner):
    iid=prepare(owner)
    with ThreadPoolExecutor(max_workers=3) as pool:
        runs=list(pool.map(lambda _: loading.start(owner,iid,initial=True),range(3)))
    assert len({r['id'] for r in runs})==1
    assert len(runs[0]['steps'])==10
    assert 'analysis' not in {s['key'] for s in runs[0]['steps']}
    seen=[]
    while loading.work_once(owner,lambda run,key: seen.append(key) or {}): pass
    assert set(seen)==set(loading.LABELS)-{'analysis'}
    assert not loading.latest(owner,iid)['active']
    assert loading.start(owner,iid,initial=True)['id']==runs[0]['id']
    assert ledger.snapshot()['calls']==0


def test_independent_steps_are_concurrent_and_committed_once(owner):
    iid=prepare(owner); loading.start(owner,iid)
    gate=Barrier(4); seen=[]
    def execute(run,key):
        seen.append(key); gate.wait(timeout=10)
        return {'failures':1} if key=='reddit' else {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        result=list(pool.map(lambda _: loading.work_once(owner,execute),range(4)))
    assert all(result) and len(set(seen))==4
    run=loading.latest(owner,iid)
    assert len([s for s in run['steps'] if s['status']=='ready'])==3
    assert next(s for s in run['steps'] if s['key']=='reddit')['status']=='partial'


def test_analysis_waits_for_sources_and_ledger_then_runs(owner):
    iid=prepare(owner); loading.start(owner,iid,analyze=True,lookback_days=30)
    selected=[]
    for _ in range(6): loading.work_once(owner,lambda run,key:selected.append(key) or {})
    call,_=ledger.reserve('queued-test','test',body())
    assert ledger.snapshot()['running']==1 and ledger.snapshot()['needs_attention']==0
    assert not loading.work_once(owner,lambda run,key: selected.append(key))
    assert loading.latest(owner,iid)['steps'][-1]['status']=='queued'
    ledger.unresolved(call,'authored_transport_failure')
    assert ledger.snapshot()['running']==0 and ledger.snapshot()['needs_attention']==1
    loading.work_once(owner,lambda run,key:selected.append(key))
    run=loading.latest(owner,iid)
    assert not run['active'] and run['steps'][-1]['status']=='blocked'
    assert 'analysis' not in selected


def test_restart_never_replays_an_inflight_step(owner):
    iid=prepare(owner); loading.start(owner,iid,analyze=True)
    for _ in range(6): loading.work_once(owner,lambda *_:{})
    run,index=loading.claim(owner)
    assert run['steps'][index]['key']=='analysis'
    loading.recover(owner)
    assert not loading.work_once(owner,lambda *_:pytest.fail('must not repeat AI'))
    assert loading.latest(owner,iid)['steps'][-1]['status']=='interrupted'


def test_load_scope_and_input_validation(owner):
    iid=prepare(owner); run=loading.start(owner,iid)
    from thesis.config import OWNER
    assert loading.latest(OWNER,iid) is None
    with transaction() as conn:
        assert one(conn,'SELECT count(*) n FROM research_loads')['n']==0
    with pytest.raises(ValueError): loading.start(owner,iid,lookback_days=365)
    with pytest.raises(ValueError): loading.start(owner,str(uuid4()))


@pytest.mark.parametrize('text,symbol,name,expected',[
    ('Broadcom pricing has changed.','AVGO','Broadcom Inc.',True),
    ('Broadcomish is a made-up word.','AVGO','Broadcom Inc.',False),
    ('We are on target for tomorrow.','TGT','Target Corp',False),
    ('$TGT stock is expensive.','TGT','Target Corp',True),
    ('It is all on the table.','ALL','Allstate Corp',False),
    ('Allstate raised its prices.','ALL','Allstate Corp',True),
    ('The Amazon river is high.','AMZN','Amazon',False),
])
def test_company_name_matching_preserves_boundaries(text,symbol,name,expected):
    assert catalogue.mentions(text,symbol,name)==expected


def test_window_changes_collection_selection_identity_and_permissions(owner):
    iid=prepare(owner)
    now=datetime.now(timezone.utc)
    old=feed(date=(now-timedelta(days=20)).isoformat())
    assert social.parse_feed(old,'stocks',now)[0]==[]
    assert len(social.parse_feed(old,'stocks',now,30)[0])==1
    with transaction(source=True) as conn:
        conn.execute("UPDATE social_refresh_lock SET last_attempt_at=NULL,lease_until=NULL WHERE singleton")
    social.refresh(fetcher=lambda _:old,now=now,lookback_days=30)
    with transaction() as conn:
        seven=sentiment.prepare(conn,iid,now)
        month=sentiment.prepare(conn,iid,now,lookback_days=30)
        assert seven['available_social_count']==0
        assert month['available_social_count']>0
        assert sentiment.identity(seven)!=sentiment.identity(month)
    result=sentiment.generate(iid,now=now,lookback_days=30,transport=provider())
    assert not result['withheld'] and result['social_lookback_days']==30
    assert any(s['kind']=='social' for s in result['sources'])
    news_watch.configure(owner,iid,True,60)
    assert news_watch.publish(owner,iid,result['id'])==0


def test_window_identity_separates_saved_scope_but_reuses_identical_model_input(owner):
    iid=prepare(owner)
    with transaction() as c:
        seven=sentiment.prepare(c,iid); month=sentiment.prepare(c,iid,lookback_days=30)
    assert sentiment.model_identity(seven)==sentiment.model_identity(month)
    assert sentiment.identity(seven)!=sentiment.identity(month)


def test_hn_registered_name_and_window():
    now=datetime.now(timezone.utc)
    item=dict(id=123,type='comment',text='Broadcom pricing is expensive.',time=int((now-timedelta(days=20)).timestamp()))
    assert hackernews.parse_item(item,'123','AVGO',now,company_name='Broadcom Inc.')[0] is None
    assert hackernews.parse_item(item,'123','AVGO',now,company_name='Broadcom Inc.',lookback_days=30)[0]['body']==item['text']


def test_only_one_app_process_can_recover_the_queue(db):
    first=loading.worker_lease()
    assert first is not None
    try:
        assert loading.worker_lease() is None
    finally:
        first.close()
    second=loading.worker_lease()
    assert second is not None
    second.close()


def test_interrupted_worker_cannot_overwrite_recovery(owner):
    iid=prepare(owner); loading.start(owner,iid)
    def execute(run,key):
        loading.recover(owner)
        return {}
    loading.work_once(owner,execute)
    assert loading.latest(owner,iid)['steps'][0]['status']=='interrupted'
