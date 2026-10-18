"""Deployment evidence and restart observations; no app or provider is started."""
import json
import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
import pytest

from thesis import runtime_status as R
from thesis.config import ROOT, dsn


def tree(tmp_path):
    (tmp_path/'thesis').mkdir()
    (tmp_path/'migrations').mkdir()
    (tmp_path/'run.py').write_text('authored launcher\n')
    (tmp_path/'thesis/worker.py').write_text('POLICY="authored-1"\n')
    (tmp_path/'migrations/001_authored.sql').write_text('-- authored\n')
    return tmp_path


def test_startup_record_is_private_and_excludes_secrets(tmp_path, monkeypatch):
    root=tree(tmp_path);data=tmp_path/'data'
    monkeypatch.setenv('OPENAI_API_KEY','authored-secret-never-export')
    monkeypatch.setattr(R,'process_start',lambda pid:'authored process start')
    manifest=R.record_start(root=root,data=data)
    assert manifest['pid']==os.getpid()
    assert (data/'runtime.json').stat().st_mode & 0o777 == 0o600
    assert 'authored-secret-never-export' not in (data/'runtime.json').read_text()
    assert R.deployment(root=root,data=data,pid=os.getpid())['source_changed_since_start'] is False
    assert list(data.glob('*.tmp'))==[]


@pytest.mark.parametrize('changed',['thesis/worker.py','run.py','migrations/001_authored.sql'])
def test_later_edits_are_not_claimed_live(tmp_path, monkeypatch, changed):
    root=tree(tmp_path);data=tmp_path/'data'
    monkeypatch.setattr(R,'process_start',lambda pid:'authored start')
    before=R.record_start(root=root,data=data)
    (root/changed).write_text('authored changed source\n')
    result=R.deployment(root=root,data=data,pid=os.getpid())
    assert result['startup_manifest']==before
    assert result['source_changed_since_start'] is True


def test_user_css_and_private_files_do_not_change_backend_identity(tmp_path):
    root=tree(tmp_path);before=R.source_fingerprint(root)
    (root/'.env').write_text('AUTHORED_SECRET=private\n')
    (root/'frontend').mkdir();(root/'frontend/app.css').write_text('authored CSS\n')
    assert R.source_fingerprint(root)==before


@pytest.mark.parametrize('content',[None,'{broken','[]','{}'])
def test_missing_or_malformed_manifest_is_unknown_not_current(tmp_path, content):
    root=tree(tmp_path);data=tmp_path/'data';data.mkdir()
    if content is not None:(data/'runtime.json').write_text(content)
    result=R.deployment(root=root,data=data,pid=123)
    assert result['startup_manifest'] is None
    assert result['source_changed_since_start'] is None
    assert 'unknown' in result['status']


def test_old_or_reused_process_id_is_not_accepted(tmp_path, monkeypatch):
    root=tree(tmp_path);data=tmp_path/'data'
    monkeypatch.setattr(R,'process_start',lambda pid:'authored old start')
    R.record_start(root=root,data=data)
    assert R.deployment(root=root,data=data,pid=os.getpid()+1)['startup_manifest'] is None
    monkeypatch.setattr(R,'process_start',lambda pid:'authored newer start')
    assert R.deployment(root=root,data=data,pid=os.getpid())['startup_manifest'] is None


def test_modes_use_actual_start_gate_and_never_enable_settings(monkeypatch):
    flags=('THESIS_MOVE_ALERTS','THESIS_SENTIMENT_LANES','THESIS_ALERT_ROUTING_LIVE',
           'THESIS_ALERT_ROUTING_PREVIEW','THESIS_SENTIMENT_TASKS','THESIS_DAILY_REPORTS',
           'THESIS_MOVE_TELEGRAM_ENABLED')
    for key in flags:monkeypatch.delenv(key,raising=False)
    assert R.operating_mode()['name']=='Combined research checks'
    monkeypatch.setenv('THESIS_MOVE_ALERTS','true')
    assert R.operating_mode()['name']=='Price previews'
    monkeypatch.setenv('THESIS_SENTIMENT_LANES','true')
    assert R.operating_mode()['name']=='Fast price previews'
    assert R.operating_mode()['features']['source_metrics']
    monkeypatch.setenv('THESIS_ALERT_ROUTING_LIVE','true')
    monkeypatch.setenv('THESIS_ALERT_ROUTING_LIVE_STARTED_AT','not a time')
    value=R.operating_mode()
    assert value['name']=='Custom delivery configuration'
    assert value['features']['severity_requested'] and not value['features']['severity_routing']
    assert os.environ['THESIS_ALERT_ROUTING_LIVE_STARTED_AT']=='not a time'


def readonly():
    return psycopg.connect(dsn('thesis_local'),row_factory=dict_row,
                          options='-c default_transaction_read_only=on')


def test_schema_report_is_read_only_and_detects_missing_checkout_files(db,tmp_path):
    with readonly() as conn:
        current=R.schema_status(conn)
        assert current['applied']==len(list((ROOT/'migrations').glob('*.sql')))
        assert current['pending']==[] and current['mismatched_or_missing']==[]
        (tmp_path/'migrations').mkdir()
        wrong=R.schema_status(conn,root=tmp_path)
        assert len(wrong['mismatched_or_missing'])==current['applied']
        assert conn.execute('SHOW transaction_read_only').fetchone()['transaction_read_only']=='on'
        with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
            conn.execute('DELETE FROM schema_migrations')


def test_due_checks_and_leases_are_real_restart_blockers(owner):
    from thesis.db import transaction
    from test_move_alerts import setup
    setup(owner)
    mode=dict(features=dict(fast_lanes=False,price_detection=False,daily_records=False))
    with transaction(owner) as conn:
        conn.execute("UPDATE news_watches SET next_check_at=now()+interval '60 seconds' WHERE owner_id=%s",(owner,))
    with readonly() as conn:
        assert R.restart_blockers(conn,mode=mode)['news_due_90s']>=1
    with transaction(owner) as conn:
        conn.execute("UPDATE news_watches SET next_check_at=now()+interval '180 seconds',lease_until=now()+interval '60 seconds' WHERE owner_id=%s",(owner,))
    with readonly() as conn:
        blockers=R.restart_blockers(conn,mode=mode)
        assert blockers['news_due_90s']==0 and blockers['news_leases']>=1
        assert 'fast_due_90s' not in blockers
        mode['features']['fast_lanes']=True
        assert R.restart_blockers(conn,mode=mode)['fast_due_90s']>=1


def test_manifest_write_failure_does_not_take_app_down(monkeypatch,caplog):
    import asyncio
    from types import SimpleNamespace
    from thesis import app
    from thesis.research import loading
    closed=[]
    def failed():raise OSError('authored private filesystem detail')
    monkeypatch.setattr(R,'record_start',failed)
    monkeypatch.setattr(app.threading,'Thread',lambda **kw:SimpleNamespace(
        start=lambda:None,join=lambda **kw:None))
    monkeypatch.setattr(loading,'WorkerLease',lambda *a:SimpleNamespace(close=lambda:closed.append(True)))
    async def check():
        async with app.lifespan(app.app):
            assert 'running version is unverified' in caplog.text
            assert 'authored private filesystem detail' not in caplog.text
    asyncio.run(check())
    assert closed==[True]


def test_old_ledger_records_are_not_mistaken_for_active_calls(db):
    from uuid import uuid4
    from hashlib import sha256
    from psycopg.types.json import Jsonb
    from thesis.db import transaction
    from thesis.providers import ledger
    from test_model_budget import body
    mode=dict(features=dict(fast_lanes=False,price_detection=False,daily_records=False))
    request=body();profile=ledger.request_profile(request);old=uuid4()
    with readonly() as conn:
        before=conn.execute('SELECT * FROM model_activity()').fetchone()
    with transaction(admin=True) as conn:
        conn.execute("""INSERT INTO model_calls(id,request_key,request_hash,purpose,model,price_version,
          request_body,reserved_nano_usd,status,created_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,'dispatched',now()-interval '2 days')""",
          (old,'authored-old-'+str(old),sha256(ledger.canonical(request).encode()).hexdigest(),
           'authored',profile.model,profile.version,Jsonb(request),ledger.estimate(request)))
    with readonly() as conn:
        assert R.restart_blockers(conn,mode=mode)['ai_requests']==before['running']
        assert conn.execute('SELECT needs_attention FROM model_activity()').fetchone()['needs_attention']==before['needs_attention']+1
    recent,_=ledger.reserve('authored-active-'+str(uuid4()),'authored',request)
    with readonly() as conn:
        assert R.restart_blockers(conn,mode=mode)['ai_requests']==before['running']+1
        # Observation neither settles old calls nor redispatches them.
        assert conn.execute("SELECT count(*) n FROM model_calls WHERE id=ANY(%s::uuid[]) AND status='dispatched'",
                            ([old,recent['id']],)).fetchone()['n']==2
