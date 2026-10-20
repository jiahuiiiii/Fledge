"""Local deployment evidence and read-only operating status; no control switches.

The startup manifest identifies source on disk at startup, not every lazily
imported module. A changed tree is therefore reported as needing a deliberate
restart, never described as the version currently running.
"""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
from uuid import uuid4

from .config import DATA, ROOT, dsn


def source_fingerprint(root=ROOT):
    files = [root / 'run.py', root / 'requirements.txt']
    files += sorted((root / 'thesis').rglob('*.py'))
    files += sorted((root / 'migrations').glob('*.sql'))
    digest = sha256()
    for path in files:
        if path.is_file():
            digest.update(str(path.relative_to(root)).encode() + b'\0')
            digest.update(path.read_bytes() + b'\0')
    return digest.hexdigest()


def process_start(pid):
    return subprocess.run(['ps', '-p', str(pid), '-o', 'lstart='],
                          capture_output=True, text=True, check=False).stdout.strip()


def operating_mode():
    # Use the production gates, including explicit start times, rather than
    # pretending a requested flag alone means a feature is active.
    from .monitoring import move_watch as M, watch_lanes as W, alert_routing as R
    from .monitoring import daily_updates as D, daily_telegram as DT
    from .research.source_observations import enabled as metrics_enabled
    from .research.sentiment_task_runner import enabled as tasks_enabled
    now = datetime.now(timezone.utc)
    features = dict(fast_lanes=W.enabled(), source_metrics=metrics_enabled(), price_detection=M.enabled(),
                    smaller_tasks=tasks_enabled(), severity_routing=R.live_active(now),
                    severity_requested=R.live_requested(), routing_previews=R.enabled(),
                    daily_records=D.enabled(), digest_delivery=DT.enabled('digest', now=now),
                    cost_delivery=DT.enabled('cost', now=now),
                    move_delivery_requested=str(M.option('THESIS_MOVE_TELEGRAM_ENABLED') or '').lower()
                    in {'true', '1', 'on'})
    new_delivery = any(features[k] for k in ('severity_requested', 'digest_delivery',
                                            'cost_delivery', 'move_delivery_requested'))
    if new_delivery:
        name = 'Custom delivery configuration'
    elif features['price_detection']:
        name = 'Fast price previews' if features['fast_lanes'] else 'Price previews'
    else:
        name = 'Fast research checks' if features['fast_lanes'] else 'Combined research checks'
    return dict(name=name, features=features,
                note='Named summaries describe existing gates. Account preferences and delivery safety still apply; no setting is changed.')


def record_start(*, root=ROOT, data=DATA):
    """Called only inside the real app lifespan, before background work starts."""
    manifest = dict(pid=os.getpid(), process_start=process_start(os.getpid()),
                    recorded_at=datetime.now(timezone.utc).isoformat(),
                    source_fingerprint=source_fingerprint(root), mode_at_start=operating_mode())
    data.mkdir(parents=True, exist_ok=True)
    temporary = data / ('runtime-' + uuid4().hex + '.tmp')
    try:
        with temporary.open('x', encoding='utf-8') as output:
            os.chmod(temporary, 0o600)
            json.dump(manifest, output, indent=2)
            output.write('\n')
        os.replace(temporary, data / 'runtime.json')
    finally:
        temporary.unlink(missing_ok=True)
    return manifest


def deployment(*, root=ROOT, data=DATA, pid=None):
    path = data / 'runtime.json'
    current = source_fingerprint(root)
    manifest = None
    if path.exists():
        try:
            value = json.loads(path.read_text())
            if (isinstance(value, dict) and type(value.get('pid')) is int and value['pid'] == pid
                    and value.get('process_start') and process_start(pid) == value['process_start']
                    and isinstance(value.get('source_fingerprint'), str)):
                manifest = value
        except (ValueError, TypeError, OSError):
            pass
    changed = current != manifest['source_fingerprint'] if manifest else None
    return dict(startup_manifest=manifest, source_on_disk=current, source_changed_since_start=changed,
                status=('Running startup source matches disk.' if changed is False else
                        'Source changed after startup; restart deliberately.' if changed else
                        'Running source is unknown: no matching startup manifest.'))


def schema_status(conn, *, root=ROOT):
    applied = conn.execute('SELECT version,filename,checksum FROM schema_migrations ORDER BY version').fetchall()
    files = {int(p.name[:3]): p for p in (root / 'migrations').glob('[0-9][0-9][0-9]_*.sql')}
    bad = [r['version'] for r in applied if r['version'] not in files
           or files[r['version']].name != r['filename']
           or sha256(files[r['version']].read_bytes()).hexdigest() != r['checksum']]
    versions = {r['version'] for r in applied}
    return dict(applied=max(versions) if versions else 0, mismatched_or_missing=bad,
                pending=[p.name for v, p in sorted(files.items()) if v not in versions],
                startup_behavior='All pending migrations apply automatically. Feature gates are separate.')


def restart_blockers(conn, *, mode):
    queries = dict(
        data_updates='SELECT count(*) n FROM research_loads WHERE active',
        ai_requests='SELECT running n FROM model_activity()',
        news_leases='SELECT count(*) n FROM news_watches WHERE lease_until>now()',
        fast_leases='SELECT count(*) n FROM fast_watch_state WHERE lease_until>now()',
        filing_leases='SELECT count(*) n FROM filing_watches WHERE lease_until>now()',
        move_leases='SELECT count(*) n FROM move_watch_state WHERE lease_until>now()',
        evaluations="SELECT count(*) n FROM jobs WHERE status IN ('pending','running')",
        sends="SELECT count(*) n FROM telegram_deliveries WHERE status='sending'",
        news_due_90s="SELECT count(*) n FROM news_watches WHERE enabled AND next_check_at<=now()+interval '90 seconds'",
        filings_due_90s="SELECT count(*) n FROM filing_watches WHERE enabled AND next_check_at<=now()+interval '90 seconds'",
        # A review waiting out its hour after a failure is not about to run.
        reviews_due_90s="""SELECT count(*) n FROM review_schedules WHERE enabled AND next_due_at<=now()+interval '90 seconds'
          AND (retry_after IS NULL OR retry_after<=now()+interval '90 seconds')""",
        active_actions="""SELECT count(*) n FROM pg_locks l JOIN pg_stat_activity a ON a.pid=l.pid
          WHERE l.locktype='advisory' AND l.granted AND l.pid<>pg_backend_pid()
          AND NOT (l.classid::bigint=((hashtextextended('research-loading-worker-process',0)>>32)&4294967295)
          AND l.objid::bigint=(hashtextextended('research-loading-worker-process',0)&4294967295)
          AND l.objsubid=1 AND a.state='idle')
          -- Millisecond transaction locks (the 1.5-second Telegram rating poll)
          -- are not an action; real work holds its lock far longer.
          AND NOT (a.xact_start IS NOT NULL AND now()-a.xact_start<interval '5 seconds')""")
    if mode['features']['fast_lanes']:
        queries['fast_due_90s'] = """SELECT count(*) n FROM news_watches w LEFT JOIN fast_watch_state f
          USING(owner_id,instrument_id) WHERE w.enabled AND (f.next_check_at IS NULL
          OR f.next_check_at<=now()+interval '90 seconds')"""
    from .monitoring.move_watch import regular_session
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    if mode['features']['price_detection'] and any(regular_session(t) for t in (now, now+timedelta(seconds=90))):
        queries['moves_due_90s'] = """SELECT count(DISTINCT w.owner_id) n FROM news_watches w
          LEFT JOIN move_watch_state s USING(owner_id) WHERE w.enabled
          AND (s.next_check_at IS NULL OR s.next_check_at<=now()+interval '90 seconds')"""
    return {name: conn.execute(query).fetchone()['n'] for name, query in queries.items()}


def routine_timers(conn, *, mode):
    """Shown but never blocking: daily records re-check about every minute, so one
    is always due. Their local transactions roll back cleanly; sends are counted
    separately as restart blockers."""
    if not mode['features']['daily_records']:
        return {}
    return dict(daily_due_90s=conn.execute("""SELECT count(*) n FROM daily_updates_state
          WHERE next_check_at<=now()+interval '90 seconds'""").fetchone()['n'])


def report(*, root=ROOT, data=DATA, port=8841):
    import psycopg
    from psycopg.rows import dict_row
    pids = subprocess.run(['lsof', '-nP', f'-iTCP:{port}', '-sTCP:LISTEN', '-t'],
                          capture_output=True, text=True, check=False).stdout.split()
    pid = int(pids[0]) if len(pids) == 1 else None
    mode = operating_mode()
    with psycopg.connect(dsn('thesis_local'), row_factory=dict_row,
                         options='-c default_transaction_read_only=on') as conn:
        conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        schema = schema_status(conn, root=root)
        blockers = restart_blockers(conn, mode=mode)
        routine = routine_timers(conn, mode=mode)
        attention = conn.execute('SELECT needs_attention FROM model_activity()').fetchone()['needs_attention']
    return dict(as_of=datetime.now(timezone.utc).isoformat(), app_pid=pid,
                app_process_start=process_start(pid) if pid else None,
                deployment=deployment(root=root, data=data, pid=pid), configured_mode=mode,
                schema=schema, restart_blockers=blockers, routine_timers=routine,
                historical_ai_records_needing_attention=attention,
                idle_at_observation=bool(pid) and not any(blockers.values()) and not schema['mismatched_or_missing'],
                restart_note='Read-only observation, not a reservation. Recheck immediately before a Terminal restart.',
                source_calls=0, model_calls=0, data_writes=0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8841)
    print(json.dumps(report(port=parser.parse_args().port), indent=2))
