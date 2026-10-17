"""Read-only three-day latency/provider-denial report; never changes the app.

Capture at least 24 hours with THESIS_SOURCE_METRICS on before enabling lanes.
Supply that baseline start and the confirmed lane-rollout time. Unknown or
partial observations cannot pass. No account or company identities are emitted.
"""
import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
from pathlib import Path
from statistics import median
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from thesis.config import dsn  # noqa: E402


def assess(baseline_since, since, as_of, checks, observations, *, deployment_confirmed=False):
    for clock in (baseline_since,since,as_of):
        if clock.tzinfo is None:raise ValueError('Observation clocks need a timezone')
    if not baseline_since < since <= as_of:raise ValueError('Observation windows are out of order')
    until=min(as_of,since+timedelta(days=3))
    hours=(until-since).total_seconds()/3600
    baseline_hours=(since-baseline_since).total_seconds()/3600
    before,after=Counter(),Counter()
    baseline_responses=0
    providers=set()
    for row in observations:
        at=row['observed_at'];provider=row['provider']
        if not baseline_since<=at<until:continue
        providers.add(provider)
        baseline_responses+=at<since
        if row['http_status'] in (401,403,429):
            (before if at<since else after)[provider]+=1
    full=hours>=72
    provider_rows=[dict(provider=p,baseline_denials=before[p],rollout_denials=after[p],
                        baseline_per_day=round(before[p]*24/baseline_hours,4),
                        rollout_per_day=round(after[p]*24/hours,4) if hours else None)
                   for p in sorted(providers)]
    stable=all(Decimal(after[p])*Decimal(str(baseline_hours))<=Decimal(before[p])*Decimal(str(hours)) for p in providers)
    lanes={}
    for lane,maximum in (('fast',60),('slow',180)):
        selected=[c for c in checks if c['lane']==lane and since<=c['started_at']<until]
        finished=[c for c in selected if c['status']=='completed' and c.get('completed_at') and c['completed_at']<=until]
        durations=[max(0,(c['completed_at']-c['started_at']).total_seconds()) for c in finished]
        middle=median(durations) if durations else None
        lanes[lane]=dict(attempts=len(selected),completed=len(finished),median_seconds=middle,
                         target_seconds=maximum,
                         status='pending' if not full else 'passed' if middle is not None and middle<=maximum else 'failed')
    total=sum(l['attempts'] for l in lanes.values())
    completed=sum(l['completed'] for l in lanes.values())
    completion=100*completed/total if total else None
    gates=dict(deployment='passed' if deployment_confirmed else 'pending',
               fast=lanes['fast']['status'],slow=lanes['slow']['status'],
               completion='pending' if not full else 'passed' if total and completed*100>=total*97 else 'failed',
               provider_denials=('pending' if not full or baseline_hours<24 or not baseline_responses else
                                'passed' if stable else 'failed'))
    return dict(since=since.isoformat(),measured_until=until.isoformat(),elapsed_hours=hours,
                baseline_hours=baseline_hours,baseline_http_responses=baseline_responses,
                lanes=lanes,completion_percent=completion,providers=provider_rows,
                gates=gates,passed=all(g=='passed' for g in gates.values()),
                limitations=['Recorded attempts only; missing scheduled slots are not reconstructed.',
                             'Provider denials are HTTP 401/403/429 responses per day, not local cooldowns.',
                             'A separate baseline with metrics enabled and lanes disabled is required.'])


def report(baseline_since,since,*,as_of=None,deployment_confirmed=False):
    import psycopg
    from psycopg.rows import dict_row
    as_of=as_of or datetime.now(timezone.utc)
    if as_of>datetime.now(timezone.utc):raise ValueError('Observation end is in the future')
    until=min(as_of,since+timedelta(days=3))
    with psycopg.connect(dsn('thesis_local'),row_factory=dict_row,
                         options='-c default_transaction_read_only=on') as conn:
        conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        checks=conn.execute("SELECT c.lane,c.started_at,r.completed_at,r.status FROM watch_checks c "
                            "LEFT JOIN watch_check_results r ON r.check_id=c.id "
                            "WHERE c.lane IN ('fast','slow') AND c.started_at>=%s AND c.started_at<%s",(since,until)).fetchall()
        observations=conn.execute('SELECT provider,observed_at,http_status FROM source_request_events WHERE observed_at>=%s AND observed_at<%s',
                                  (baseline_since,until)).fetchall()
    return assess(baseline_since,since,as_of,checks,observations,deployment_confirmed=deployment_confirmed)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-since',type=datetime.fromisoformat,required=True)
    parser.add_argument('--since',type=datetime.fromisoformat,required=True)
    parser.add_argument('--deployment-confirmed',action='store_true')
    args=parser.parse_args()
    print(json.dumps(report(args.baseline_since,args.since,deployment_confirmed=args.deployment_confirmed),indent=2))
