"""Read-only outcome evidence. Never installs, rolls back, sends or pays.

The observation clock starts at an explicitly confirmed actual-delivery rollout,
not a preview install. Ten complete regular US sessions are required. External
quality and independent noise reviews remain separate gates, never inferred.
"""
import argparse
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
from math import ceil
from pathlib import Path
from statistics import median
import sys
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from thesis.monitoring import us_session
from experiments.soclaas_replay.phase2_readiness import aware, NANO


def sessions(since):
    """First ten whole sessions after rollout; a mid-session install starts tomorrow."""
    result=[];day=since.astimezone(us_session.NEW_YORK).date()
    while len(result)<10:
        if day.year not in us_session.CLOSED:
            raise ValueError('Outcome window exceeds the verified US calendar')
        value=us_session.bounds(day)
        if value and value[0]>=since:result.append(value)
        day+=timedelta(days=1)
    return result


def gate(value, ok, full):
    return dict(value=value,status='pending' if value is None or not full else 'passed' if ok else 'failed')


def assess(since,as_of,data,*,actual_delivery_confirmed=False,no_model_switch_confirmed=False):
    since,as_of=aware(since),aware(as_of)
    if as_of<since:raise ValueError('Observation end precedes its start')
    calendar=sessions(since);start=aware(calendar[0][0])
    # Finish the final 24h spending bucket as well as the tenth session.
    end=start+timedelta(days=ceil((aware(calendar[-1][1])-start).total_seconds()/86400))
    until=min(as_of,end);full=as_of>=end and actual_delivery_confirmed
    missing=set(data.get('missing_tables',[]))
    checks=[c for c in data.get('checks',[]) if start<=c['started_at']<until]
    finished=lambda c: c.get('completed_at') is not None and c['completed_at']<=until
    good=lambda c: finished(c) and c['status']=='completed'
    count=len(checks);completed=sum(good(c) for c in checks)
    percent=lambda n,d:round(100*n/d,4) if d else None
    metrics={'completion':gate(percent(completed,count),bool(count) and completed/count>=.97,full)}
    lanes={}
    for lane,limit in (('fast',60),('slow',180)):
        durations=[(c['completed_at']-c['started_at']).total_seconds() for c in checks if c['lane']==lane and good(c)]
        value=median(durations) if durations else None
        lanes[lane]=gate(value,value is not None and value<=limit,full)
    metrics['duration_seconds']=lanes
    # A failure opens an outage episode; only a later successful attempt closes
    # it. Retain the preceding attempt per company/lane at the left boundary.
    histories=defaultdict(list)
    for c in data.get('checks',[]):
        if c['started_at']<until:histories[(c['instrument_id'],c['lane'])].append(c)
    stuck=set()
    for key,history in histories.items():
        opened=None
        for c in sorted(history,key=lambda c:c['started_at']):
            if good(c):
                if opened is not None and (min(c['completed_at'],until)-max(opened,start)).total_seconds()>7200:stuck.add(key[0])
                opened=None
            elif opened is None:opened=c['started_at']
        if opened is not None and (until-max(opened,start)).total_seconds()>7200:stuck.add(key[0])
    metrics['stuck_companies']=gate(len(stuck) if count else None,not stuck,full)
    repairs={c['analysis_id']:c.get('repairs') for c in checks if good(c) and c.get('analysis_id')}
    valid=[r for r in repairs.values() if isinstance(r,dict) and isinstance(r.get('total'),int)
           and isinstance(r.get('repaired'),int) and 0<=r['repaired']<=r['total']]
    total=sum(r['total'] for r in valid);lost=sum(r['repaired'] for r in valid)
    repair_value=percent(lost,total) if len(valid)==len(repairs) else None
    metrics['repair_percent']=gate(repair_value,repair_value is not None and repair_value<=5,full)
    # Full 24-hour installation-cost windows, including weekends and explainers.
    # Experiment charges are displayed separately, never silently discarded.
    days=[];cursor=start;experiment=experiment_holds=0
    while cursor<until:
        right=cursor+timedelta(days=1);charged=maximum=holds=0
        for call in data.get('calls',[]):
            if not cursor<=call['created_at']<min(right,until):continue
            settled=call['status']=='settled' and call.get('finished_at') is not None and call['finished_at']<=until
            amount=call['charged_nano_usd'] if settled else 0
            if call['experiment']:
                experiment+=amount
                if not settled:experiment_holds+=call['reserved_nano_usd']
                continue
            charged+=amount;maximum+=amount if settled else call['reserved_nano_usd'];holds+=not settled
        days.append(dict(start=cursor.isoformat(),complete=right<=until,confirmed_usd=str(Decimal(charged)/NANO),
                         maximum_usd=str(Decimal(maximum)/NANO),unsettled=holds))
        cursor=right
    metrics['daily_cost_usd']=gate(max((d['maximum_usd'] for d in days),key=Decimal,default=None),
        bool(days) and all(Decimal(d['maximum_usd'])<=3 and not d['unsettled'] for d in days),
        full and all(d['complete'] for d in days))
    closed=[d for d in days if d['complete']]
    if any(d['unsettled'] for d in days):metrics['daily_cost_usd']['status']='pending'
    if actual_delivery_confirmed and any(Decimal(d['confirmed_usd'])>3 for d in days):
        metrics['daily_cost_usd']['status']='failed'
    if 'model_calls' in missing:metrics['daily_cost_usd']=gate(None,False,full)
    metrics['switch_cost_usd']=gate('0' if no_model_switch_confirmed else None,no_model_switch_confirmed,actual_delivery_confirmed)
    sent=[d for d in data.get('deliveries',[]) if d['status']=='sent' and d.get('sent_at') and d['sent_at']<=until]
    window_sent=[d for d in sent if start<=d['sent_at']<until and d['kind'] in ('company','idea','condition','move','digest')]
    # Half-open rolling 24h story identity, per account (capture is owner-scoped).
    claims=defaultdict(set)
    for c in data.get('claims',[]):claims[(c['delivery_id'],c['attempt'])].add(c['story_key'])
    previous={};duplicates=0;unverifiable=0;ambiguous=0
    for d in sorted(sent,key=lambda d:(d['sent_at'],str(d['id']))):
        if d['kind'] not in ('company','idea','condition','move','digest'):continue
        keys=claims[(d['id'],d['attempts'])]
        inside=start<=d['sent_at']<until
        if inside:
            unverifiable+=not bool(keys)
            overlap={k for k in keys if k in previous and d['sent_at']-previous[k]<timedelta(days=1)}
            # A material update claims its URL to block later old copies, but
            # intentionally doesn't use that URL to suppress its own send.
            # Flat claims cannot associate each URL with an update inside a
            # mixed recap. Do not turn that ambiguity into a false duplicate.
            update=any(k.startswith('update:') for k in keys)
            certain={k for k in overlap if not update or not k.startswith('url:')}
            duplicates+=bool(certain)
            ambiguous+=bool(overlap and not certain)
        for k in keys:previous[k]=d['sent_at']
    metrics['duplicate_deliveries']=gate(duplicates if window_sent and not unverifiable and not ambiguous and 'telegram_story_claims' not in missing else None,duplicates==0,full)
    latest={}
    for r in sorted(data.get('feedback',[]),key=lambda r:(r['created_at'],str(r['id']))):
        if start<=r['created_at']<until:latest[(r['kind'],r['event_id'])]=r['value']
    useful=sum(v=='useful' for v in latest.values());rated=len(latest)
    metrics['useful_percent']=gate(percent(useful,rated),bool(rated) and useful/rated>=.7,full)
    # Denominator is first qualifying saved observation per company/session/
    # direction/policy. Context members and already-claimed repeats add no move.
    episodes={};invalid=0;run_ids=set()
    for a in sorted(data.get('assessments',[]),key=lambda a:a['observed_at']):
        if a['preview'] or not start<=a['observed_at']<until:continue
        run_ids.add(a['run_id'])
        if a['status']!='measured':invalid+=1;continue
        if not a['qualifies']:continue
        m=a['payload']['measure'];key=(a['instrument_id'],m['session'],m.get('trigger_direction',m['direction']),a['policy'])
        if key not in episodes:episodes[key]=a
    gaps=sum(r['id'] not in run_ids or bool(r.get('error')) for r in data.get('move_runs',[]) if start<=r['started_at']<until)
    orphan=len(run_ids-{r['id'] for r in data.get('move_runs',[])})
    coverage=bool(run_ids) and not invalid and not gaps and not orphan and 'move_assessments' not in missing
    event_sends={d['event_id']:d['sent_at'] for d in sorted(sent,key=lambda d:d['sent_at'],reverse=True) if d['kind']=='move'}
    matches={}
    for event in data.get('move_members',[]):
        if event['preview'] or not event['triggered'] or event['event_id'] not in event_sends:continue
        m=event['payload'];key=(event['instrument_id'],str(event['session_date']),m.get('trigger_direction',m['direction']),event['policy'])
        if key not in episodes:continue
        observed=episodes[key];sent_at=event_sends[event['event_id']]
        if event['created_at']>=observed['observed_at'] and sent_at>=event['created_at']:
            matches[key]=min(matches.get(key,sent_at),sent_at)
    recall=percent(len(matches),len(episodes)) if coverage else None
    metrics['moves_alerted_percent']=gate(recall,recall is not None and recall>=90,full)
    delays=[]
    for key,sent_at in matches.items():
        a=episodes[key];quoted=datetime.fromisoformat(a['payload']['measure']['quoted_at'])
        session=us_session.bounds(quoted.astimezone(us_session.NEW_YORK).date())
        if session and session[0]<=quoted<=session[1]:delays.append((sent_at-quoted).total_seconds()/60)
    delay=median(delays) if delays and coverage else None
    metrics['move_latency_minutes']=gate(delay,delay is not None and delay<=20,full)
    # Deliberately external: predictions cannot label their own accuracy/noise.
    metrics['low_value_percent']=gate(None,False,full)
    metrics['label_quality_percent']=gate(None,False,full)
    bad_days=[]
    for day in closed:
        left=datetime.fromisoformat(day['start']);right=left+timedelta(days=1)
        chosen=[c for c in checks if left<=c['started_at']<right]
        if chosen and sum(good(c) for c in chosen)/len(chosen)<.9:bad_days.append(day['start'])
    rollback=dict(completion_below_90=bool(bad_days),cost_above_6_two_days=sum(Decimal(d['confirmed_usd'])>6 for d in closed)>=2,
        moves_below_70=bool(coverage and episodes and recall<70 and full),
        ratings_majority_not_useful=bool(until-start>=timedelta(days=7) and rated and rated-useful>useful))
    return dict(since=since.isoformat(),measured_until=until.isoformat(),actual_delivery_confirmed=actual_delivery_confirmed,
        complete_sessions=sum(aware(s[1])<=as_of for s in calendar),required_sessions=10,
        window_complete=full,metrics=metrics,checks=dict(total=count,completed=completed),
        moves=dict(qualifying=len(episodes),sent=len(matches),invalid_assessments=invalid,run_gaps=gaps,orphan_runs=orphan,coverage_complete=coverage),
        ratings=dict(total=rated,useful=useful),duplicate_evidence=dict(confirmed=duplicates,missing_claims=unverifiable,ambiguous_updates=ambiguous),
        daily_windows=days,experiment_confirmed_usd=str(Decimal(experiment)/NANO),experiment_unresolved_maximum_usd=str(Decimal(experiment_holds)/NANO),
        rollback=rollback,rollback_required=actual_delivery_confirmed and any(rollback.values()),missing_tables=sorted(missing),
        limitations=['Saved observations do not reconstruct unsampled intraday moves or missed watch schedule slots.',
            'Move latency is wall time from the first qualifying saved quote; overnight waits remain counted.',
            'Story keys cover displayed exact content, URLs and verified repeats; semantic paraphrases remain unproven.',
            'Daily installation costs include normal explainers and all accounts; experiments are separate.',
            'Independent noise review and owner 50-source/hard-case quality results must accompany this report.',
            'Rollback flags request operator action; this read-only report never changes the app.'])


def collect(conn,owner,since,until):
    """Host-only read; private rows scoped explicitly, cost ledger installation-wide."""
    found={r['name'] for r in conn.execute("SELECT tablename name FROM pg_tables WHERE schemaname='public'")}
    result={'missing_tables':[]}
    def read(key,table,sql,params):
        if table not in found:result['missing_tables'].append(table);result[key]=[]
        else:result[key]=conn.execute(sql,params).fetchall()
    # Keep prior history to resolve an outage spanning the left boundary.
    read('checks','watch_checks',"SELECT c.instrument_id,c.lane,c.started_at,r.completed_at,r.status,r.analysis_id,a.result->'repairs' repairs "
         "FROM watch_checks c LEFT JOIN watch_check_results r ON r.check_id=c.id LEFT JOIN sentiment_analyses a ON a.id=r.analysis_id "
         "WHERE c.owner_id=%s AND c.started_at<%s",(owner,until))
    read('calls','model_calls',"SELECT created_at,finished_at,status,charged_nano_usd,reserved_nano_usd,request_key LIKE 'experiment:%%' experiment "
         "FROM model_calls WHERE created_at>=%s AND created_at<%s",(since,until))
    for key,table,clock in (('deliveries','telegram_deliveries','created_at'),('claims','telegram_story_claims','created_at'),
                           ('feedback','alert_feedback','created_at'),('assessments','move_assessments','observed_at'),
                           ('move_runs','move_watch_runs','started_at')):
        read(key,table,f'SELECT * FROM {table} WHERE owner_id=%s AND {clock}<%s',(owner,until))
    read('move_members','move_event_members',"SELECT m.*,e.created_at,e.session_date,e.preview,e.policy FROM move_event_members m "
         "JOIN move_events e ON e.id=m.event_id AND e.owner_id=m.owner_id WHERE m.owner_id=%s AND e.created_at<%s",(owner,until))
    return result


def report(owner,since,*,as_of=None,actual_delivery_confirmed=False,no_model_switch_confirmed=False):
    import psycopg
    from psycopg.rows import dict_row
    from thesis.config import dsn
    since=aware(since);as_of=aware(as_of or datetime.now(timezone.utc))
    if as_of>datetime.now(timezone.utc) or as_of<since:raise ValueError('Choose a real observation window')
    calendar=sessions(since);start=aware(calendar[0][0])
    end=start+timedelta(days=ceil((aware(calendar[-1][1])-start).total_seconds()/86400))
    until=min(as_of,end)
    with psycopg.connect(dsn('thesis_local'),row_factory=dict_row,options='-c default_transaction_read_only=on') as conn:
        conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        data=collect(conn,owner,since,until)
    return assess(since,as_of,data,actual_delivery_confirmed=actual_delivery_confirmed,no_model_switch_confirmed=no_model_switch_confirmed)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--owner',type=UUID,required=True)
    p.add_argument('--since',type=datetime.fromisoformat,required=True)
    p.add_argument('--as-of',type=datetime.fromisoformat)
    p.add_argument('--actual-delivery-confirmed',action='store_true')
    p.add_argument('--no-model-switch-confirmed',action='store_true')
    a=p.parse_args()
    print(json.dumps(report(a.owner,a.since,as_of=a.as_of,actual_delivery_confirmed=a.actual_delivery_confirmed,
                            no_model_switch_confirmed=a.no_model_switch_confirmed),indent=2))
