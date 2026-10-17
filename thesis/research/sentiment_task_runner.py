"""Opt-in smaller sentiment tasks with durable results and no automatic retry.

An unchanged saved tone is carried forward across the explicit version bridge;
only missing event/importance or candidate comparisons need their own task.
Old readings and original paid responses are never rewritten.
"""
from copy import deepcopy
import hashlib
import json
import os
import threading

from thesis.db import transaction, one
from thesis.providers import ledger
from . import sentiment, sentiment_tasks as T, sentiment_reuse, reporting_basis
from . import relevance_prefilter, sentiment_reliability, coverage, reddit_thread_context


def enabled():
    value = os.environ.get('THESIS_SENTIMENT_TASKS')
    if value is None and os.environ.get('THESIS_TEST_OFFLINE') != 'true':
        from thesis.providers.settings import settings
        value = settings().get('THESIS_SENTIMENT_TASKS')
    return str(value or 'false').lower() in {'true', '1', 'on'}


def identity(packet):
    value = dict(policy=T.POLICY, instructions=T.INSTRUCTIONS, model=T.REASONING_MODEL,
                 company=packet['company'], sources=[sentiment_reuse.content_key(s) for s in packet['sources']],
                 comparisons=[sentiment_reuse.content_key(s) for s in packet.get('comparison_sources',[])],
                 policies={key:packet.get(key) for key in ('reporting_policy','context_policy','reddit_thread_policy','guard_policy')},
                 reread_token=packet.get('reread_token'))
    return 'sentiment-tasks:'+hashlib.sha256(ledger.canonical(value).encode()).hexdigest()


def key_for(task, body, packet):
    value = dict(policy=T.POLICY, task=task, request=body, reread_token=packet.get('reread_token'))
    return 'sentiment-task:'+hashlib.sha256(ledger.canonical(value).encode()).hexdigest()


def pair_key(packet, pair):
    return T.pair_key(packet,pair)


def part_for(packet, sources):
    return dict(packet, sources=sources, comparison_sources=[])


def plan(task, packet, sources):
    """Bound whole sources and required parents; only optional siblings may drop."""
    result=[]; selected=[]
    def fit(values):
        part=part_for(packet,values)
        try:T.request_for(task,part)
        except ValueError:
            part['thread_extras']=False
            try:T.request_for(task,part)
            except ValueError:return None
        return part
    for source in reddit_thread_context.ordered(sources):
        trial=selected+[source]
        if fit(trial) is None:
            if selected:result.append(fit(selected))
            selected=[source]
            if fit(selected) is None:
                raise ValueError('One complete source and required context exceed the task limit. No task was sent.')
        else:selected=trial
    if selected:
        result.append(fit(selected))
    return result


def response(items, links=()):
    return dict(response_body=dict(status='completed',output=[dict(type='message',
        content=[dict(type='output_text',text=json.dumps(dict(items=items,coverage_links=list(links))))])]))


def run(packet, reused=None, *, transport=None, progress=None, prefilter=None, saved_only=False,
        retry_failed=False, split_failed=False):
    from . import sentiment_batching as B, parallel
    reused=deepcopy(reused or {})
    supplied=packet['sources']+packet.get('comparison_sources',[])
    if (len({s['id'] for s in supplied})!=len(supplied)
            or len({s['label'] for s in supplied})!=len(supplied)):
        raise ValueError('Sentiment tasks need distinct source IDs and labels.')
    calls=[]; checked={}; tones={}; origins={}; events={}; links=[]; trace=[]
    recovery=[];parse_lock=threading.RLock()
    skipped={sid:dict(saved['item'],id=next(s['label'] for s in packet['sources'] if s['id']==sid))
             for sid,saved in reused.items() if saved['item'].get('prefilter')}
    quick_record=None
    def access():
        with transaction() as conn:B.check_access(conn,packet)
    def report(message, failure=None):
        if progress:progress(dict(completed=len(calls),total=len(calls)+(1 if failure else 0),source_counts=[],
                                  failed=1 if failure else None,message=message,**({'failure':failure} if failure else {})))
    def load(task, part, body):
        report('Reading '+{'tone':'tone and evidence','event':'news importance','duplicate':'possible repeated stories'}[task])
        access(); key=part.get('_task_key') or key_for(task,body,packet)
        with transaction() as conn:
            saved=ledger.find(conn,key)
            attempted=one(conn,'SELECT id FROM model_calls WHERE request_key=%s OR starts_with(request_key,%s) LIMIT 1',
                          (key,key+ledger.REDISPATCH))
        if saved:return saved
        if attempted:raise ledger.BudgetBlocked('An earlier sentiment task has no settled response. No automatic paid retry.')
        if saved_only:raise ValueError('This reading has an unsent task.')
        return ledger.execute(key,T.PROMPT+':'+task,body,transport=transport)
    def stage(task, parts, parse):
        jobs=[]
        def body_for(part):return T.request_for(task,part,pairs=part.get('_candidate_pairs'))
        def parse_result(call,part):
            with parse_lock:return parse(call,part)
        def invalid(part,call,error,attempt):
            details=B.failure_details(call,error)
            length=len(part.get('_candidate_pairs',part['sources']))
            if attempt==1 and length>1 and not part.get('_terminal'):
                details['split_available']=True
            report('A saved '+task+' task needs attention. No automatic paid retry.',details)
            raise ValueError('A saved '+task+' task did not pass its evidence checks. No automatic paid retry.') from None
        def resolve(part):
            body=body_for(part);base=part.get('_task_key') or key_for(task,body,packet)
            previous=None;bad=None
            for attempt in ([0] if part.get('_terminal') else [1,0]):
                key=base+(':retry:1' if attempt else '')
                with transaction() as conn:saved=ledger.find(conn,key)
                if saved:
                    try:parse_result(saved,part)
                    except ValueError as error:
                        if previous is None:previous=(saved,attempt);bad=error
                    else:calls.append(saved);return
                elif B.has_attempt(key):
                    raise ledger.BudgetBlocked('An earlier sentiment task may have been sent. No automatic paid retry; review its charge.')
            if previous:
                call,attempt=previous
                if not part.get('_terminal') and attempt==0 and retry_failed:
                    child=dict(part,_task_key=base+':retry:1')
                    jobs.append((child,body));return
                length=len(part.get('_candidate_pairs',part['sources']))
                if not part.get('_terminal') and attempt==1 and length>1:
                    children=[];middle=(length+1)//2
                    selected=part.get('_candidate_pairs',part['sources'])
                    for index,values in enumerate((selected[:middle],selected[middle:])):
                        child=pair_part(values) if task=='duplicate' else part_for(packet,values)
                        if task=='duplicate':child['_candidate_pairs']=values
                        child['_terminal']=True
                        child_body=body_for(child)
                        child['_task_key']=key_for(task,child_body,packet)+':split:'+hashlib.sha256(base.encode()).hexdigest()+':'+str(index)
                        children.append(child)
                    if split_failed or any(B.has_attempt(c['_task_key']) for c in children):
                        recovery.append(dict(task=task,parent_key=base,child_keys=[c['_task_key'] for c in children]))
                        for child in children:resolve(child)
                        return
                invalid(part,call,bad,attempt)
            if part.get('_terminal') and not split_failed:
                raise ledger.BudgetBlocked('Smaller-task recovery is unfinished. Continue it explicitly; no automatic paid call.')
            if split_failed and not part.get('_terminal') and not recovery:
                raise ValueError('No saved failed task is ready for smaller-batch recovery. No new task was sent.')
            jobs.append((part,body))
        # Revalidate saved results before dispatching any new task in this stage.
        for part in parts:
            resolve(part)
        def work(part,body):
            call=load(task,part,body)
            try:result=parse_result(call,part)
            except ValueError as error:raise B.BatchFailed(0,call,error) from None
            return call,result
        results,errors=parallel.run_all([lambda part=p,body=b:work(part,body) for p,b in jobs])
        if errors:
            error=errors[min(errors)]
            if not isinstance(error,B.BatchFailed):raise error
            report('The '+task+' task stopped. Its paid response is saved; no automatic retry.',B.failure_details(error.call,error.error))
            raise ValueError('The '+task+' task stopped. Paid results remain saved; no combined reading or automatic retry.') from None
        for result in results:
            call,_=result;calls.append(call)
        trace.append(dict(task=task,batches=len(parts),new_calls=len(jobs)))
    access()
    fresh=[s for s in packet['sources'] if s['id'] not in reused]
    if prefilter is None:prefilter=relevance_prefilter.enabled()
    if prefilter and fresh:
        # Preflight both possible stages before spending on the mini-model pass.
        plan('tone',packet,fresh)
        plan('event',packet,[s for s in fresh if s['channel']=='news'])
        sub=part_for(packet,fresh)
        if saved_only or split_failed:
            by_label={s['label']:s for s in fresh};skip=set();quick=[]
            for body in relevance_prefilter.plan(sub):
                with transaction() as conn:call=ledger.find(conn,relevance_prefilter.request_key(body))
                if not call:raise ValueError('The quick relevance check is not saved.')
                quick.append(call);found=relevance_prefilter.labels(call,body) or {}
                skip|={by_label[label]['id'] for label,value in found.items() if value=='unrelated'}
            quick_record=dict(policy=relevance_prefilter.POLICY,model=relevance_prefilter.MODEL,checked=len(fresh),
                              skipped=len(skip),call_ids=[str(c['id']) for c in quick])
        else:
            report('Quick relevance check · '+str(len(fresh))+' new sources')
            _,skip,quick_record,quick=relevance_prefilter.run(sub,transport=transport)
            skip=set(skip)
        calls+=quick
        for source in fresh:
            if source['id'] in skip:
                skipped[source['id']]=dict(relevance_prefilter.skipped_item(source),
                    model=quick_record['model'],call_ids=quick_record['call_ids'])
        fresh=[s for s in fresh if s['id'] not in skip]
    for source in packet['sources']:
        saved=reused.get(source['id'])
        if saved and source['id'] not in skipped:
            item=dict(saved['item'],id=source['label'])
            checked[source['label']]=item
            tones[source['label']]={key:item[key] for key in T.ToneItem.model_fields}
            tones[source['label']]['id']=source['label']
            links.extend(deepcopy(link) for link in saved['links']
                         if link['reference_source_id'] in {s['id'] for s in packet['sources']})
    def tone_result(call,part):
        for item in T.tone_labels(call,part):
            tones[item['id']]=item
            origins[item['id']]=dict(model=call['model'],call_id=str(call['id']),prompt_version=T.PROMPT)
    if fresh:stage('tone',plan('tone',packet,fresh),tone_result)
    news=[s for s in packet['sources'] if s['channel']=='news' and s['id'] not in skipped]
    missing_events=[s for s in news if (checked.get(s['label'],{}).get('importance') or {}).get('policy')!=T.POLICY]
    def event_result(call,part):
        for label,value in T.event_labels(call,part,list(tones.values())).items():
            value['importance'].update(model=call['model'],call_id=str(call['id']))
            events[label]=value
    if missing_events:stage('event',plan('event',packet,missing_events),event_result)
    # New tone outputs are validated with reporting before duplicate work is paid.
    for part in plan('tone',packet,fresh) if fresh else []:
        raw=[]
        for source in part['sources']:
            item=deepcopy(tones[source['label']])
            if source['channel']=='news' and packet.get('reporting_policy')==reporting_basis.POLICY:
                item['reporting']=events[source['label']]['reporting']
            raw.append(item)
        rendered=sentiment.render(response(raw),part)
        for item in rendered['items']:
            item.update(origins[item['id']]);checked[item['id']]=item
    for source in missing_events:
        label=source['label']; event=events[label];item=checked[label]
        item['reporting_basis']=reporting_basis.render(reporting_basis.Evidence.model_validate(event['reporting']),
                                                    source,item['relevance'],repairs=[] if sentiment_reliability.enabled() else None)
        item['importance']=event['importance']
        if event['importance'].get('event_repair'):
            repair=item.setdefault('repair',dict(policy=sentiment_reliability.POLICY,
                reasons=[],original=dict(reporting=event['reporting']),component='reporting'))
            repair['reasons']=list(dict.fromkeys(repair['reasons']+event['importance']['event_repair']))
            repair['reporting_original']=deepcopy(event['reporting'])
            item['repair']['reporting_call_id']=event['importance']['call_id']
    current=[s for s in packet['sources'] if s['id'] not in skipped]
    comparison_packet=dict(packet,sources=current)
    pairs=T.candidates(comparison_packet,list(checked.values()))
    pairs=[p for p in pairs if pair_key(packet,p) not in checked[p['item_id']].get('duplicate_candidates_checked',[])]
    # A request is bounded by its actual complete pair inputs, not just item count.
    pending=[];pair_parts=[]
    def pair_part(selected):
        targets={p['item_id'] for p in selected};references={p['reference_id'] for p in selected}
        by_label={s['label']:s for s in current+packet.get('comparison_sources',[])}
        return dict(packet,sources=[by_label[k] for k in sorted(targets)],
                    comparison_sources=[by_label[k] for k in sorted(references-targets)])
    for pair in pairs:
        trial=pending+[pair]
        try:T.request_for('duplicate',pair_part(trial),pairs=trial)
        except ValueError:
            if not pending:raise
            pair_parts.append(pending);pending=[pair]
            T.request_for('duplicate',pair_part(pending),pairs=pending)
        else:pending=trial
    if pending:pair_parts.append(pending)
    raw_links=[];link_origins={}
    def duplicate_result(call,part):
        selected=part['_candidate_pairs']
        values=T.duplicate_labels(call,comparison_packet,list(checked.values()),selected)
        raw_links.extend(values)
        for link in values:link_origins[link['item_id']]=dict(model=call['model'],call_id=str(call['id']))
        for pair in selected:
            item=checked[pair['item_id']]
            item['duplicate_candidates_checked']=sorted(set(item.get('duplicate_candidates_checked',[]))|{pair_key(packet,pair)})
    if pair_parts:
        stage('duplicate',[dict(pair_part(selected),_candidate_pairs=selected) for selected in pair_parts],duplicate_result)
    ignored=[]
    fresh_links=coverage.render([coverage.Link.model_validate(link) for link in raw_links],
                                comparison_packet,list(checked.values()),ignored)
    by_source={s['id']:s['label'] for s in current}
    for link in fresh_links:link.update(link_origins[by_source[link['source_id']]])
    # A new comparison for a current report supersedes its prior optional link.
    replaced={link['source_id'] for link in fresh_links}
    links=[link for link in links if link['source_id'] not in replaced]+fresh_links
    # Recheck optional saved links against the current combination of reused
    # labels too. In particular, an unrelated reference cannot suppress a story.
    source_map={s['id']:s for s in current+packet.get('comparison_sources',[])}
    restored=[];old_origins={}
    for link in links:
        own=source_map.get(link['source_id']);prior=source_map.get(link['reference_source_id'])
        if not own or not prior:continue
        restored.append(coverage.Link(item_id=own['label'],reference_id=prior['label'],relation=link['relation'],
            explanation='Saved source-pair comparison',item_passages=[q['passage_id'] for q in link['citations']],
            reference_passages=[q['passage_id'] for q in link['reference_citations']]))
        old_origins[link['source_id']]={key:link[key] for key in ('model','call_id') if key in link}
    links=coverage.render(restored,comparison_packet,list(checked.values()),ignored)
    for link in links:link.update(old_origins[link['source_id']])
    items=[deepcopy(skipped[s['id']]) if s['id'] in skipped else checked[s['label']] for s in packet['sources']]
    if [item['source_id'] for item in items]!=[s['id'] for s in packet['sources']]:
        raise ValueError('Every source must be read or reused exactly once.')
    result=dict(items=items,coverage_links=links,summary=sentiment.summarize(items,packet['sources'],links,packet.get('comparison_sources',[])),
                summary_policy=sentiment.POLICY,prompt_version=T.PROMPT,model=T.REASONING_MODEL,
                guard_policy=packet.get('guard_policy'),tasks=dict(policy=T.POLICY,stages=trace,duplicate_batches=len(pair_parts),recovery=recovery),
                batching=dict(policy=T.POLICY,completed=len(calls),total=len(calls),source_counts=[],comparison_limit=T.MAX_PAIRS,
                              comparison_context_bounded=bool(pairs)),
                source_reuse=dict(policy=sentiment_reuse.POLICY,reused=len(reused),new=len(packet['sources'])-len(reused),
                                  analysis_ids=sorted({s['analysis_id'] for s in reused.values()})),
                repairs=sentiment_reliability.counts(items))
    if quick_record or skipped:
        result['prefilter']=dict(quick_record or {},policy=relevance_prefilter.POLICY,
            model=relevance_prefilter.MODEL,checked_now=(quick_record or {}).get('checked',0),
            skipped_now=(quick_record or {}).get('skipped',0),skipped=len(skipped),
            call_ids=sorted({cid for item in items if item.get('prefilter') for cid in item.get('call_ids',[])}))
    if ignored:result['ignored_coverage_links']=ignored
    access();report('Reading complete · '+str(len(reused))+' saved labels reused')
    unique={str(call['id']):call for call in calls}
    return result,list(unique.values())
