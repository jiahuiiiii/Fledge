"""Freeze and explicitly evaluate saved news for the file-only routing replay.

Only the selected OpenAI models, ledger calls and private output files are used.
No source collection, app publications, settings, automatic retry or Telegram.
"""
import argparse
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from thesis.db import transaction,one,rows  # noqa:E402
from thesis.providers import ledger,settings  # noqa:E402
from thesis.research import (sentiment as S,sentiment_tasks as T,sentiment_task_runner as TR,
    sentiment_batching as B,relevance_prefilter as P,reporting_basis,coverage)  # noqa:E402
from experiments.soclaas_replay import news_noise_replay as E  # noqa:E402
N=E.N
POLICY='news-noise-campaign-1'
PREFIX='experiment:news-noise-v1:'


def contract():
    from thesis.monitoring import news_watch,alert_routing,telegram_stories,telegram_message,daily_telegram
    modules=(S,T,TR,B,P,reporting_basis,coverage,E,N,news_watch,alert_routing,telegram_stories,telegram_message,daily_telegram)
    return dict(models=list(settings._models()),schema_policy=T.SCHEMA_POLICY,
        runner=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        modules={m.__name__:hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest() for m in modules})


def freeze(capture,records):
    N.validate(capture);reused={};wanted=capture['sources']
    for record in records:
        packet=record['packet'];sources={s['id']:s for s in packet.get('sources',[])}
        for item in record['result'].get('items',[]):
            sid=item.get('source_id');source=sources.get(sid);target=wanted.get(sid)
            if (not source or not target or str(packet.get('instrument_id'))!=target['instrument_id']
                    or N.model_source(source)['passages']!=source['passages']
                    or N.sentiment_reuse.content_key(source)!=N.sentiment_reuse.content_key(target)
                    or not N.candidate(record,source,item)):
                continue
            at=N.instant(record['created_at']).isoformat()
            if sid in reused and N.instant(reused[sid]['created_at'])<=N.instant(at):continue
            metadata={k:record['result'].get(k) for k in ('prompt_version','summary_policy','guard_policy','prefilter','model')}
            reused[sid]=dict(analysis_id=str(record['id']),call_id=str(record['call_id']),created_at=at,
                source=deepcopy(source),item=deepcopy(item),packet={k:packet.get(k) for k in N.POLICIES},result=metadata)
    core=dict(policy=POLICY,contract=contract(),capture=capture,reused=reused)
    return dict(core,fingerprint=N.digest(core))


def validate(plan):
    if (plan.get('policy')!=POLICY or N.digest({k:v for k,v in plan.items() if k!='fingerprint'})!=plan.get('fingerprint')
            or plan.get('contract')!=contract()):
        raise ValueError('The frozen news plan or its production contracts changed.')
    N.validate(plan['capture'])
    if plan['contract']['models']!=['openai',settings.OPENAI_MODEL,settings.OPENAI_REASONING_MODEL]:
        raise ValueError('Keep the selected OpenAI quick and bulk pair.')
    for sid,saved in plan['reused'].items():
        source=plan['capture']['sources'].get(sid)
        record=dict(packet=saved['packet'],result=saved['result'])
        if (not source or source['id']!=saved['source']['id']
                or N.sentiment_reuse.content_key(source)!=N.sentiment_reuse.content_key(saved['source'])
                or not N.candidate(record,saved['source'],saved['item'])):
            raise ValueError('An inherited tone no longer matches the frozen evidence/policy.')
    child=plan;depth=0
    while child.get('previous_plan'):
        parent=child['previous_plan'];depth+=1
        if depth>3 or N.digest({k:v for k,v in parent.items() if k!='fingerprint'})!=parent.get('fingerprint'):
            raise ValueError('An earlier frozen news plan changed.')
        if (child['capture']!=parent['capture'] or child['reused']!=parent['reused']
                or child['contract']['models']!=parent['contract']['models']
                or any(v!=parent['contract']['modules'].get(k) for k,v in child['contract']['modules'].items() if k!=T.__name__)):
            raise ValueError('A news schema revision cannot change sources, tones, models or other production contracts.')
        child=parent
    if len(set(plan.get('retry_hashes',[])))!=len(plan.get('retry_hashes',[])):
        raise ValueError('Repeated retry authorization.')
    return plan['capture']


def revised_plan(previous,retry_hashes):
    if N.digest({k:v for k,v in previous.items() if k!='fingerprint'})!=previous.get('fingerprint'):
        raise ValueError('The original frozen news plan changed.')
    core={k:deepcopy(v) for k,v in previous.items() if k not in {'fingerprint','previous_plan','retry_hashes'}}
    core.update(contract=contract(),previous_plan=deepcopy(previous),retry_hashes=sorted(set(retry_hashes)))
    plan=dict(core,fingerprint=N.digest(core));validate(plan);return plan


def without_schema(body):
    body=deepcopy(body);body['text']['format'].pop('schema');return body


def packet_for(company,sources,cutoff):
    return dict(N.POLICIES,company={k:company[k] for k in ('symbol','name')},
        instrument_id=company['instrument_id'],cutoff=N.instant(cutoff).isoformat(),
        sources=deepcopy(sources),comparison_sources=[])


def estimate(plan):
    capture=validate(plan);event_bodies=[];missing=set()
    for frame in capture['frames']:
        company=next(c for c in capture['companies'] if c['instrument_id']==frame['instrument_id'])
        sources=E.canonical_sources(capture,company,frame['source_ids']+frame['comparison_source_ids'])
        packet=packet_for(company,sources,frame['cutoff'])
        missing.update(s['id'] for s in sources if s['id'] not in plan['reused'])
        if frame['initial_baseline']:continue
        selected=[s for s in sources if s['id'] in frame['source_ids']
            and not plan['reused'].get(s['id'],{}).get('item',{}).get('prefilter')]
        event_bodies.extend(T.request_for('event',part) for part in TR.plan('event',packet,selected))
    return dict(fingerprint=plan['fingerprint'],source_versions=len(capture['sources']),
        reused_tone_versions=len(plan['reused']),missing_tone_versions=len(missing),
        event_requests_before_new_quick_skips=len(event_bodies),
        event_independent_reservation_sum_usd=str(Decimal(sum(ledger.estimate(b) for b in event_bodies))/ledger.NANO),
        duplicate_requests='Depend on actual relevance, wording candidates and cached negative pair checks.',
        expected_total_usd='2–5',proposed_combined_cap_usd='6',paid_calls=0,app_writes=0)


def collect(conn,capture):
    if conn.execute('SHOW transaction_read_only').fetchone()['transaction_read_only']!='on':
        raise ValueError('Freeze inputs only in a database-enforced read-only transaction.')
    return freeze(capture,conn.execute('SELECT id,call_id,created_at,packet,result FROM sentiment_analyses '
        'WHERE instrument_id=ANY(%s::uuid[]) AND created_at>=%s ORDER BY created_at,id',
        ([c['instrument_id'] for c in capture['companies']],N.instant(capture['window_start'])-E.timedelta(days=7))))


def saved_calls():
    with transaction(consistent=True) as conn:
        return rows(conn,'SELECT * FROM model_calls WHERE starts_with(request_key,%s) ORDER BY created_at,id',(PREFIX,))


def spend(calls):
    return (sum(c['charged_nano_usd'] or 0 for c in calls if c['status']=='settled'),
        sum(c['reserved_nano_usd'] for c in calls if c['status']!='settled'))


def access(packet):
    with transaction(consistent=True) as conn:B.check_access(conn,packet)


class Stopped(Exception):pass


def run(plan,output,cap,*,approved_plan,transport=None,remaining_after=None,revised_after=None,saved_only=False):
    capture=validate(plan)
    if approved_plan!=plan['fingerprint']:raise ValueError('Execution needs the exact frozen plan binding.')
    if not isinstance(cap,Decimal) or not cap.is_finite() or not 0<cap<=8:
        raise ValueError('Choose an explicit combined cap from above zero to US$8.')
    if remaining_after is not None and revised_after is not None:raise ValueError('Choose one explicit continuation mode.')
    if not saved_only and transport is None and os.environ.get('THESIS_TEST_OFFLINE')=='true':
        raise ValueError('Offline tests cannot dispatch a provider request.')
    output=Path(output)
    if output.exists():raise ValueError('Choose a new output path; retained evidence is immutable.')
    with transaction(consistent=True) as lock:
        if not one(lock,"SELECT pg_try_advisory_xact_lock(hashtextextended('experiment:news-noise-v1',0)) locked")['locked']:
            raise ValueError('A news-noise campaign is already running.')
        old=saved_calls()
        if old and remaining_after is None and revised_after is None:raise ValueError('A prior campaign exists; explicit same-plan continuation is required.')
        if remaining_after is not None:
            prior=Path(remaining_after)
            if json.loads((prior/'plan.json').read_text())!=plan:
                raise ValueError('A continuation must retain the identical frozen plan.')
        if revised_after is not None:
            prior=Path(revised_after)
            if json.loads((prior/'plan.json').read_text())!=plan.get('previous_plan'):
                raise ValueError('A revised campaign must retain the exact original plan.')
            before=json.loads((prior/'campaign.json').read_text())
            failed={c['request_hash'] for c in before['calls'] if not c['passed']}
            if before['fingerprint']!=plan['previous_plan']['fingerprint'] or not set(plan.get('retry_hashes',[]))<=failed:
                raise ValueError('Only explicitly named failed requests may receive a revised attempt.')
        output.mkdir(parents=True)
        (output/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n')
        report=dict(fingerprint=plan['fingerprint'],completed=False,attempted=0,calls=[],frames_completed=0,
            paid_usd='0',unresolved_maximum_usd='0',cap_usd=str(cap),automatic_retries=0,app_writes=0,telegram_http_calls=0)
        def save():
            paid,pending=spend(saved_calls());report.update(paid_usd=str(Decimal(paid)/ledger.NANO),
                unresolved_maximum_usd=str(Decimal(pending)/ledger.NANO))
            (output/'campaign.json').write_text(json.dumps(report,indent=2)+'\n')
        save()
        if any(c['status']!='settled' or ledger.REDISPATCH in c['request_key'] for c in old):
            report['stopped']='prior_unsettled_or_redispatched_attempt';save();return report
        inherited={N.digest(without_schema(c['request_body'])):c for c in old} if plan.get('previous_plan') else {}
        companies={c['instrument_id']:c for c in capture['companies']}
        state={};link_state={}
        for sid,saved in plan['reused'].items():
            item=deepcopy(saved['item']);item.pop('importance',None);item.pop('duplicate_candidates_checked',None)
            item.setdefault('model',(saved['result'].get('prefilter') or {}).get('model') if item.get('prefilter') else saved['result'].get('model'))
            item.setdefault('prompt_version',saved['result']['prompt_version'])
            if item.get('prefilter'):item.setdefault('call_ids',(saved['result'].get('prefilter') or {}).get('call_ids',[]))
            else:item['call_id']=item.get('call_id') or saved['call_id']
            state[sid]=item
        evaluated=dict(input_fingerprint=capture['fingerprint'],campaign_fingerprint=plan['fingerprint'],baselines={},frames={})

        def call(task,packet,body,parse):
            access(packet);key=PREFIX+N.digest(body);calls=saved_calls()
            prior=next((c for c in calls if c['request_key']==key),None)
            inherited_schema=False;retested=None
            if prior is None and inherited:
                candidate=inherited.get(N.digest(without_schema(body)))
                if candidate:
                    if candidate['request_hash'] in plan.get('retry_hashes',[]):retested=str(candidate['id'])
                    else:prior=candidate;inherited_schema=True
                elif any(c['request_body']['input'][1]==body['input'][1] for c in old):
                    report['stopped']='request_changed_beyond_schema';raise Stopped()
            if prior is not None and (prior['status']!='settled' or (not inherited_schema and prior['request_hash']!=N.digest(body))):
                report['stopped']='prior_attempt_unsettled_or_changed';raise Stopped()
            if any(c['request_key'].startswith(key) and c['request_key']!=key for c in calls):
                report['stopped']='prior_redispatch_refused';raise Stopped()
            if prior is None:
                if saved_only:report['stopped']='new_request_needed_saved_only';raise Stopped()
                paid,pending=spend(calls)
                if paid+pending+ledger.estimate(body)>int(cap*ledger.NANO):
                    report['stopped']='combined_cap_before_dispatch';raise Stopped()
                report['attempted']+=1;save()
                try:prior=ledger.execute(key,'sentiment:'+P.POLICY if task=='quick' else T.PROMPT+':'+task,body,transport=transport)
                except Exception:
                    report['stopped']='paid_request_failed_no_retry';save();raise Stopped() from None
            save()  # Keep cost even if local response/validator work fails.
            filename=output/(N.digest(body)+'.response.json')
            if filename.exists():
                if json.loads(filename.read_text())!=prior['response_body']:raise ValueError('Retained raw response changed.')
            else:filename.write_text(json.dumps(prior['response_body'],ensure_ascii=False,indent=2)+'\n')
            row=dict(task=task,request_hash=prior['request_hash'],planned_request_hash=N.digest(body),
                inherited_schema=inherited_schema,retested_call_id=retested,call_id=str(prior['id']),passed=False)
            report['calls'].append(row)
            try:result=parse(prior)
            except (ValueError,KeyError,TypeError) as error:
                report['stopped']='validator_failure_no_retry';row['failure']=B.failure_details(prior,error);save();raise Stopped() from None
            row['passed']=True;save();return result,prior

        def evaluate(packet,*,new=(),quiet=False):
            access(packet);sources=packet['sources'];fresh=[s for s in sources if s['id'] not in state]
            selected=dict(packet,sources=fresh)
            for body in P.plan(selected) if fresh else []:
                def parse_quick(answer):
                    value=P.labels(answer,body)
                    if value is None:raise ValueError('The quick relevance result is invalid; no later task was sent.')
                    return value
                values,origin=call('quick',selected,body,parse_quick)
                for source in fresh:
                    if values.get(source['label'])=='unrelated':
                        state[source['id']]=dict(P.skipped_item(source),model=origin['model'],call_ids=[str(origin['id'])],prompt_version=P.POLICY)
            fresh=[s for s in fresh if s['id'] not in state]
            for part in TR.plan('tone',packet,fresh):
                def parse_tone(answer):
                    raw=T.tone_labels(answer,part)
                    return S.render(TR.response(raw),dict(part,reporting_policy=None))['items']
                items,origin=call('tone',part,T.request_for('tone',part),parse_tone)
                for item in items:state[item['source_id']]=dict(item,model=origin['model'],call_id=str(origin['id']),prompt_version=T.PROMPT)
            for source in sources:state[source['id']]['id']=source['label']
            targets=[s for s in sources if s['id'] in new and not state[s['id']].get('prefilter')]
            if not quiet:
                for part in TR.plan('event',packet,targets):
                    tones=[state[s['id']] for s in sources]
                    values,origin=call('event',part,T.request_for('event',part),lambda answer:T.event_labels(answer,part,tones))
                    for source in part['sources']:
                        item=state[source['id']];value=values[source['label']]
                        item['reporting_basis']=reporting_basis.render(reporting_basis.Evidence.model_validate(value['reporting']),
                            source,item['relevance'],repairs=[])
                        item['importance']=dict(value['importance'],model=origin['model'],call_id=str(origin['id']))
                        if value['importance'].get('event_repair'):
                            repair=item.setdefault('repair',dict(policy=S.sentiment_reliability.POLICY,
                                reasons=[],original=dict(reporting=value['reporting']),component='reporting'))
                            repair['reasons']=list(dict.fromkeys(repair['reasons']+value['importance']['event_repair']))
                            repair['reporting_original']=deepcopy(value['reporting'])
                            repair['reporting_call_id']=str(origin['id'])
            # Use the live candidate selection, bounded per-pair requests and
            # negative-pair cache. Old/future comparison links were not inherited.
            current=[s for s in sources if not state[s['id']].get('prefilter')]
            comparison=dict(packet,sources=current)
            pairs=T.candidates(comparison,[state[s['id']] for s in current])
            def pair_part(values):
                targets={p['item_id'] for p in values};refs={p['reference_id'] for p in values}
                lookup={s['label']:s for s in current}
                return dict(packet,sources=[lookup[k] for k in sorted(targets)],
                    comparison_sources=[lookup[k] for k in sorted(refs-targets)])
            parts=[];pending=[]
            for pair in pairs:
                trial=pending+[pair]
                try:T.request_for('duplicate',pair_part(trial),pairs=trial)
                except ValueError:
                    if not pending:raise
                    parts.append(pending);pending=[pair];T.request_for('duplicate',pair_part(pending),pairs=pending)
                else:pending=trial
            if pending:parts.append(pending)
            raw=[]
            for values in parts:
                part=pair_part(values)
                links,origin=call('duplicate',part,T.request_for('duplicate',part,pairs=values),
                    lambda answer:T.duplicate_labels(answer,comparison,[state[s['id']] for s in current],values))
                raw+=links
                for pair in values:
                    item=next(state[s['id']] for s in current if s['label']==pair['item_id'])
                    item['duplicate_candidates_checked']=sorted(set(item.get('duplicate_candidates_checked',[]))|{T.pair_key(comparison,pair)})
            for link in coverage.render([coverage.Link.model_validate(l) for l in raw],comparison,[state[s['id']] for s in current]):
                link_state[link['source_id']]=link
            visible={s['id'] for s in sources}
            links=[deepcopy(l) for l in link_state.values() if l['source_id'] in visible and l['reference_source_id'] in visible]
            items=[deepcopy(state[s['id']]) for s in sources]
            result=dict(items=items,coverage_links=links,summary=S.summarize(items,sources,links,[]),
                prompt_version=T.PROMPT,summary_policy=S.POLICY,guard_policy=packet['guard_policy'],model=T.REASONING_MODEL,
                batching=dict(policy=T.POLICY),prefilter=dict(policy=P.POLICY),repairs=S.sentiment_reliability.counts(items))
            return dict(packet=packet,result=result)

        try:
            # All current source permissions are checked before any payment.
            for iid,company in companies.items():
                all_sources=[s for s in capture['sources'].values() if s['instrument_id']==iid]
                access(packet_for(company,all_sources,capture['window_end']))
            for iid,company in companies.items():
                if capture['baseline_counts'].get(company['symbol'],0):
                    packet=packet_for(company,E.baseline_sources(capture,company),capture['window_start'])
                    value=evaluate(packet,quiet=True)
                    E.check_reading(value,capture,company,N.instant(capture['window_start']),expected_sources=packet['sources'])
                    evaluated['baselines'][iid]=value
            for frame in capture['frames']:
                company=companies[frame['instrument_id']]
                packet=packet_for(company,E.canonical_sources(capture,company,frame['source_ids']+frame['comparison_source_ids']),frame['cutoff'])
                value=evaluate(packet,new=frame['source_ids'],quiet=frame['initial_baseline'])
                E.check_reading(value,capture,company,N.instant(frame['cutoff']),new=() if frame['initial_baseline'] else frame['source_ids'],expected_sources=packet['sources'])
                evaluated['frames'][E.frame_key(frame)]=value
                report['frames_completed']+=1;save()
            replay=E.replay(capture,evaluated)
            (output/'evaluated.json').write_text(json.dumps(evaluated,ensure_ascii=False,indent=2)+'\n')
            (output/'replay.json').write_text(json.dumps(replay,ensure_ascii=False,indent=2)+'\n')
            report.update(completed=True,replay_fingerprint=replay['fingerprint'],replay_counts=replay['counts'],
                noise_gate='pending_independent_review')
        except Stopped:pass
        except (ValueError,KeyError,TypeError):report['stopped']='source_or_replay_validation_failed_no_retry'
        save();return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan',type=Path);parser.add_argument('--execute',action='store_true')
    parser.add_argument('--capture',type=Path,help='Freeze current permitted-label candidates read-only, without AI calls.')
    parser.add_argument('--output',type=Path);parser.add_argument('--cap-usd',type=Decimal)
    parser.add_argument('--approved-plan');parser.add_argument('--remaining-after',type=Path)
    parser.add_argument('--revised-after',type=Path);parser.add_argument('--saved-only',action='store_true')
    args=parser.parse_args()
    if args.capture:
        if args.execute or args.plan.exists():parser.error('Freeze to a new plan path without --execute.')
        import psycopg
        from psycopg.rows import dict_row
        from thesis.config import dsn
        capture=N.validate(json.loads(args.capture.read_text()))
        with psycopg.connect(dsn('thesis_local'),row_factory=dict_row,options='-c default_transaction_read_only=on') as conn:
            conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            plan=collect(conn,capture)
        with args.plan.open('x') as output:output.write(json.dumps(plan,ensure_ascii=False,indent=2)+'\n')
    else:plan=json.loads(args.plan.read_text())
    if args.execute:
        if args.output is None or args.cap_usd is None:parser.error('Choose a new output and explicit combined cap.')
        result=run(plan,args.output,args.cap_usd,approved_plan=args.approved_plan,remaining_after=args.remaining_after,
            revised_after=args.revised_after,saved_only=args.saved_only)
        print(json.dumps({k:v for k,v in result.items() if k!='calls'},indent=2))
    else:print(json.dumps(estimate(plan),indent=2))
