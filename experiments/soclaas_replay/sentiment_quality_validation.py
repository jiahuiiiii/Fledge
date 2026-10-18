"""Freeze, estimate and explicitly execute one bounded quality campaign.

No app research/settings writes, model switch or automatic paid retries. The
owner's blind answers are never read here. Responses stay in private output.
"""
import argparse
from copy import deepcopy
from datetime import datetime
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
from thesis.research import sentiment,sentiment_tasks as T,sentiment_batching as B,reddit_thread_context as threads,sentiment_context,social  # noqa:E402
from thesis.research.citations import model_source,source_passages  # noqa:E402
from experiments.soclaas_replay import owner_quality_set as Q  # noqa:E402

POLICY='sentiment-quality-validation-1'
HARD_TONES=('negative','unclear','negative','mixed','negative','neutral')
HARD_REFERENCES=((4,'item_195'),(3,'item_187'),(8,'item_203'),(8,'item_200'),(8,'item_10'),(6,'item_5'))
PREFIX='experiment:sentiment-quality-v1:'


def digest(value):return hashlib.sha256(ledger.canonical(value).encode()).hexdigest()


# 'review' reproduces the blind page (topic + reply only). 'thread' also sends the
# other saved messages of the same discussion, as the live app does, so a short
# reply is read with its conversation. 'parents' keeps the reviewed topic + reply
# and adds each reply's verified immediate parent from Reddit's context feed, as
# the live app now does; unordered siblings are not sent. Hard cases keep their
# fixed benchmark.
THREAD_CONTEXTS=('review','thread','parents')


def iso(value):return datetime.fromisoformat(str(value)).isoformat()


def with_parent(packet,check):
    """Attach one privately checked parent exactly as sentiment_context.attach would."""
    packet=deepcopy(packet);source=packet['sources'][0];parent=check['parent']
    if check.get('outcome')!='available' or check.get('source_id')!=source['id'] or source.get('platform')!='reddit':
        raise ValueError('A parent check must be an available parent of this exact Reddit reply.')
    passages,omitted=source_passages(parent['title'],parent['body'])
    if parent['parent_type']=='comment':passages=[p for p in passages if p['id']!='p0']
    if not passages or len(ledger.canonical(passages).encode())>sentiment_context.MAX_PARENT_BYTES:return packet
    context=dict(private_check=True,post_id=source['id'],parent_key=parent['parent_key'],parent_type=parent['parent_type'],
        title=parent['title'],body=parent['body'],url=parent['url'],published_at=iso(parent['published_at']),
        checked_at=iso(check['fetched_at']),passages=passages,omitted_fragment_count=omitted)
    context['content_key']=digest(sentiment_context.wire(context))
    # Evidence records need an identity; it is not on the model wire.
    context['result_id']='private-check:'+digest(check)
    source.update(conversation=context,context_status='included')
    if source.get('timestamp_basis')=='feed_updated':source['source_note']=social.FEED_NOTE_WITH_PARENT
    for thread in packet.get('reddit_thread_context',[]):
        for message in thread['messages']:
            if message['source_id']==source['id']:message['parent_key']=parent['parent_key']
    return packet


def selected(packet,source_id,*,thread_extras=False):
    packet=deepcopy(packet)
    sources=[s for s in packet['sources'] if s['id']==source_id]
    if len(sources)!=1:raise ValueError('A frozen quality case needs its one exact source.')
    packet.update(sources=sources,thread_extras=thread_extras,comparison_sources=[])
    if model_source(sources[0])['passages']!=sources[0]['passages']:
        raise ValueError('Model-visible passages differ from the reviewed passages.')
    return packet


def wire_evidence(payload,label):
    """One original benchmark source and its required parent/topic passages."""
    source=next(s for s in payload['sources'] if s['label']==label)
    fields=('id','title','passages','channel','platform','published_at','available_at','social_kind','discovery_match','conversation')
    context=[]
    if source.get('conversation'):
        context.append(dict(label='Saved parent context',passages=source['conversation']['passages']))
    for thread in payload.get('reddit_threads',[]):
        target=next((m for m in thread['messages'] if m.get('source_label')==label),None)
        if not target:continue
        for message in thread['messages']:
            if message is target:continue
            if message['role']!='topic' and message['message_key']!=target.get('parent_key'):continue
            passages=message.get('passages')
            if passages is None:
                passages=next(s['passages'] for s in payload['sources'] if s['label']==message['source_label'])
            context.append(dict(label='Saved discussion context · '+message['role'],passages=passages))
    return dict(company=payload['company'],source={k:source.get(k) for k in fields},context=context)


def packet_evidence(packet):
    body=T.request_for('tone',packet)
    payload=json.loads(body['input'][1]['content'])
    return wire_evidence(payload,packet['sources'][0]['label'])


def hard_case(body,packet,index):
    batch,label=HARD_REFERENCES[index]
    expected=wire_evidence(json.loads(body['input'][1]['content']),label)
    p=selected(packet,expected['source']['id'])
    if packet_evidence(p)!=expected:raise ValueError('The hard-case source/context differs from its original benchmark.')
    return dict(id=f'hard-{index+1:02d}',source_id=p['sources'][0]['id'],packet=p,expected_tone=HARD_TONES[index],
        benchmark=dict(batch=batch,label=label,request_hash=digest(body),evidence=expected))


def make_plan(manifest,owner_packets,hard_cases,*,thread_context='review',parents=None):
    if thread_context not in THREAD_CONTEXTS:raise ValueError('Unknown thread-context option.')
    if (thread_context=='parents')!=(parents is not None):raise ValueError('Parent checks belong only to the parents option.')
    Q.validate_manifest(manifest)
    expected={c['id'] for c in manifest['cases']}
    if set(owner_packets)!=expected or len(hard_cases)!=6:
        raise ValueError('Use all fifty owner cases and the six fixed hard cases.')
    requests=[]
    for case in manifest['cases']:
        packet=selected(owner_packets[case['id']],case['source_id'],thread_extras=thread_context=='thread')
        if Q.case_evidence(packet,packet['sources'][0])!={k:v for k,v in case.items() if k!='id'}:
            raise ValueError('A quality source or review context changed.')
        if thread_context=='parents':
            reviewed=packet
            packet=with_parent(reviewed,parents[case['id']]) if case['id'] in parents else reviewed
            requests.append(dict(scope='owner50',id=case['id'],packet=packet,reviewed_packet=reviewed))
            continue
        requests.append(dict(scope='owner50',id=case['id'],packet=packet))
    for index,case in enumerate(hard_cases):
        if case['id']!=f'hard-{index+1:02d}' or case['expected_tone']!=HARD_TONES[index]:
            raise ValueError('The six fixed interpretation expectations cannot change.')
        packet=selected(case['packet'],case['source_id'])
        reference=case.get('benchmark',{})
        if ((reference.get('batch'),reference.get('label'))!=HARD_REFERENCES[index]
                or packet_evidence(packet)!=reference.get('evidence')
                or not isinstance(reference.get('request_hash'),str) or len(reference['request_hash'])!=64):
            raise ValueError('Hard cases must preserve their fixed benchmark evidence and reference.')
        requests.append(dict(scope='hard6',id=case['id'],packet=packet,expected_tone=case['expected_tone'],benchmark=reference))
    for case in requests:
        case['body']=T.request_for('tone',case['packet'])
        # The configured sentiment model: GPT-5.4 by default, or the owner's Luna choice.
        if case['body']['model']!=settings.SENTIMENT_MODEL:
            raise ValueError('Quality evaluation retains the selected GPT-5.4 bulk model.')
    plan=dict(policy=POLICY,owner_fingerprint=manifest['fingerprint'],model=settings.SENTIMENT_MODEL,requests=requests)
    if thread_context!='review':plan['thread_context']=thread_context  # earlier plans keep their exact fingerprint
    if parents is not None:
        if not set(parents)<=expected:raise ValueError('Unknown parent-check case.')
        plan['parents']=parents
    return dict(plan,fingerprint=digest(plan))


def validate(plan,manifest):
    Q.validate_manifest(manifest)
    core={k:v for k,v in plan.items() if k!='fingerprint'}
    if plan.get('policy')!=POLICY or digest(core)!=plan.get('fingerprint') or plan.get('owner_fingerprint')!=manifest['fingerprint']:
        raise ValueError('The frozen evaluation plan changed.')
    owner={};hard=[]
    for case in plan['requests']:
        if case['scope']=='owner50':
            if case['id'] in owner:raise ValueError('Repeated owner case.')
            owner[case['id']]=case.get('reviewed_packet',case['packet'])
        elif case['scope']=='hard6':
            hard.append(dict(case,source_id=case['packet']['sources'][0]['id']))
        else:raise ValueError('Unknown evaluation scope.')
    rebuilt=make_plan(manifest,owner,hard,thread_context=plan.get('thread_context','review'),parents=plan.get('parents'))
    supplied={k:v for k,v in plan.items() if k not in {'fingerprint','previous_plan','retry_cases'}}
    if {k:v for k,v in rebuilt.items() if k!='fingerprint'}!=supplied:
        raise ValueError('The plan no longer matches the production task contract.')
    if plan.get('previous_plan'):
        previous=plan['previous_plan']
        for parent in ancestors(plan):
            if digest({k:v for k,v in parent.items() if k!='fingerprint'})!=parent.get('fingerprint'):
                raise ValueError('An earlier frozen plan changed.')
        chain=[plan]+ancestors(plan)
        for child,parent in zip(chain,chain[1:]):equivalent(child,parent)
        identities={c['scope']+':'+c['id'] for c in plan['requests']}
        if not set(plan.get('retry_cases',[]))<=identities:raise ValueError('Unknown explicitly retried case.')
    return plan['requests']


def ancestors(plan):
    result=[];parent=plan.get('previous_plan')
    while parent:
        result.append(parent)
        if len(result)>3:raise ValueError('Too many quality-plan revisions; review the experiment separately.')
        parent=parent.get('previous_plan')
    return result


def narrows(new,old):
    if isinstance(old,dict):
        if not isinstance(new,dict) or not set(old)<=set(new):return False
        if not (set(new)-set(old))<={'enum','maxItems','minItems'}:return False
        for k,v in old.items():
            if k=='enum':
                if not set(new[k])<=set(v):return False
            elif k=='maxItems':
                if new[k]>v:return False
            elif k=='minItems':
                if new[k]<v:return False
            elif not narrows(new[k],v):return False
        return True
    return new==old


def equivalent(plan,previous):
    if plan['owner_fingerprint']!=previous['owner_fingerprint'] or plan['model']!=previous['model']:
        raise ValueError('A schema revision cannot change the sample or model.')
    if len(plan['requests'])!=len(previous['requests']):raise ValueError('A schema revision cannot change the cases.')
    changed=False
    for new,old in zip(plan['requests'],previous['requests']):
        if {k:v for k,v in new.items() if k!='body'}!={k:v for k,v in old.items() if k!='body'}:
            raise ValueError('A schema revision cannot change source text, context or expectations.')
        a,b=deepcopy(new['body']),deepcopy(old['body'])
        sa=a['text']['format'].pop('schema');sb=b['text']['format'].pop('schema')
        if a!=b or not narrows(sa,sb):raise ValueError('Only stricter output constraints may change.')
        changed=changed or sa!=sb
    if not changed:raise ValueError('Identical paid requests cannot be retried as a schema revision.')


def revised_plan(previous,manifest,retry_cases):
    if digest({k:v for k,v in previous.items() if k!='fingerprint'})!=previous['fingerprint']:
        raise ValueError('The earlier frozen plan changed.')
    owner={c['id']:c['packet'] for c in previous['requests'] if c['scope']=='owner50'}
    hard=[dict(c,source_id=c['packet']['sources'][0]['id']) for c in previous['requests'] if c['scope']=='hard6']
    plan=make_plan(manifest,owner,hard,thread_context=previous.get('thread_context','review'))
    equivalent(plan,previous)
    core={k:v for k,v in plan.items() if k!='fingerprint'}
    core.update(previous_plan=previous,retry_cases=sorted(set(retry_cases)))
    result=dict(core,fingerprint=digest(core));validate(result,manifest)
    return result


def thread_plan(previous,manifest):
    """Same 50 owner cases and 6 hard cases, re-frozen with full saved thread context.

    A separate development comparison, not a continuation: no earlier answer is reused.
    """
    if digest({k:v for k,v in previous.items() if k!='fingerprint'})!=previous['fingerprint']:
        raise ValueError('The earlier frozen plan changed.')
    owner={c['id']:c['packet'] for c in previous['requests'] if c['scope']=='owner50'}
    hard=[dict(c,source_id=c['packet']['sources'][0]['id']) for c in previous['requests'] if c['scope']=='hard6']
    plan=make_plan(manifest,owner,hard,thread_context='thread');validate(plan,manifest)
    return plan


def parents_plan(previous,manifest,checks):
    """Same reviewed cases, re-frozen with each reply's verified immediate parent.

    Only available checks are used; removed, changed or unverified parents stay absent.
    A separate development comparison: no earlier answer is reused.
    """
    if digest({k:v for k,v in previous.items() if k!='fingerprint'})!=previous['fingerprint']:
        raise ValueError('The earlier frozen plan changed.')
    owner={c['id']:c.get('reviewed_packet',c['packet']) for c in previous['requests'] if c['scope']=='owner50'}
    hard=[dict(c,source_id=c['packet']['sources'][0]['id']) for c in previous['requests'] if c['scope']=='hard6']
    available={k:v for k,v in checks.items() if v.get('outcome')=='available'}
    plan=make_plan(manifest,owner,hard,thread_context='parents',parents=available);validate(plan,manifest)
    return plan


def fits_schema(call,body):
    properties=body['text']['format']['schema']['$defs']['ToneItem']['properties']
    items=T.ToneResult.model_validate_json(sentiment.response_text(call)).model_dump()['items']
    for item in items:
        for field in ('id','passages','previous_passages','context_passages','price_claims'):
            rule=properties[field];value=item[field]
            if 'enum' in rule and value not in rule['enum']:return False
            if isinstance(value,list):
                if len(value)>rule.get('maxItems',len(value)):return False
                allowed=rule.get('items',{}).get('enum')
                if allowed is not None and not set(value)<=set(allowed):return False
    return True


def estimate(plan,manifest):
    prepared=validate(plan,manifest)
    values={digest(c['body']):ledger.estimate(c['body']) for c in prepared}
    return dict(fingerprint=plan['fingerprint'],owner_cases=50,hard_cases=6,requests=len(values),
        model=plan['model'],summed_reservation_maximum_usd=str(Decimal(sum(values.values()))/ledger.NANO),
        largest_reservation_usd=str(Decimal(max(values.values()))/ledger.NANO),paid_calls=0,app_research_writes=0)


def consumed(packet):
    """Permission checks cover exactly the target and required wire context."""
    used=deepcopy(packet);used['comparison_sources']=[]
    for source in used['sources']:
        # A privately checked parent has no live result row; withdrawal is checked separately.
        if (source.get('conversation') or {}).get('private_check'):source.pop('conversation')
    wire=threads.wire(packet,packet['sources'],extras=packet.get('thread_extras',False))
    wanted={c['thread_key']:{m['message_key'] for m in c['messages']} for c in wire}
    used['reddit_thread_context']=[dict(c,messages=[m for m in c['messages'] if m['message_key'] in wanted[c['thread_key']]])
        for c in packet.get('reddit_thread_context',[]) if c['thread_key'] in wanted]
    return used


def verify_access(conn,packet):
    B.check_access(conn,consumed(packet))
    private=[s['conversation']['parent_key'] for s in packet['sources'] if (s.get('conversation') or {}).get('private_check')]
    if private and one(conn,'SELECT 1 FROM social_withdrawals WHERE post_key=ANY(%s)',(private,)):
        raise ValueError('A privately checked parent was withdrawn.')


def saved_calls(prepared):
    keys={PREFIX+digest(c['body']) for c in prepared}
    with transaction(consistent=True) as conn:
        # Also detect a legacy ledger redispatch suffix; this runner never makes one.
        calls=rows(conn,'SELECT * FROM model_calls WHERE request_key=ANY(%s) OR '
            "EXISTS(SELECT 1 FROM unnest(%s::text[]) base WHERE starts_with(request_key,base||':redispatch:'))",(list(keys),list(keys)))
    return calls


def costs(calls):
    paid=sum(c['charged_nano_usd'] or 0 for c in calls if c['status']=='settled')
    pending=sum(c['reserved_nano_usd'] for c in calls if c['status']!='settled')
    return paid,pending


def parse(call,packet):
    # Validate the same task response and then score the rendered/repaired label,
    # rather than silently scoring the provider's pre-repair raw object.
    items=T.tone_labels(call,packet)
    checked=dict(response_body=dict(status='completed',output=[dict(type='message',content=[
        dict(type='output_text',text=json.dumps(dict(items=items,coverage_links=[])))])]))
    result=sentiment.render(checked,dict(packet,reporting_policy=None))
    item=result['items'][0]
    return dict(relevance=item['relevance'],sentiment=item['sentiment']),result['repairs']['repaired']


def run(plan,manifest,output,cap,*,approved_plan,transport=None,remaining_after=None,revised_after=None,reuse_settled=False):
    prepared=validate(plan,manifest)
    funding=prepared+[c for parent in ancestors(plan) for c in parent['requests']]
    if remaining_after is not None and revised_after is not None:raise ValueError('Choose one explicit continuation mode.')
    if approved_plan!=plan['fingerprint']:raise ValueError('Execution needs approval for this exact frozen plan.')
    if not isinstance(cap,Decimal) or not cap.is_finite() or not 0<cap<=Decimal('2'):
        raise ValueError('Use an explicit positive combined campaign cap of at most US$2.')
    if transport is None and os.environ.get('THESIS_TEST_OFFLINE')=='true':
        raise ValueError('Offline tests cannot dispatch an AI request.')
    if settings._models()!=('openai',settings.OPENAI_MODEL,settings.OPENAI_REASONING_MODEL):
        raise ValueError('Keep the selected OpenAI bulk and quick pair unchanged.')
    with transaction(consistent=True) as lock:
        if not one(lock,"SELECT pg_try_advisory_xact_lock(hashtextextended('experiment:sentiment-quality-v1',0)) locked")['locked']:
            raise ValueError('A quality campaign is already running.')
        existing=saved_calls(funding)
        # reuse_settled lets a new frozen plan read settled answers to byte-identical
        # requests for free. Unsettled, failed or redispatched requests still stop below.
        if existing and remaining_after is None and revised_after is None and not reuse_settled:
            raise ValueError('A campaign request was already attempted; use an explicitly approved continuation.')
        if remaining_after is not None:
            previous=Path(remaining_after)
            if json.loads((previous/'plan.json').read_text())!=plan:
                raise ValueError('A continuation must retain the identical frozen plan.')
            prior=json.loads((previous/'validation.json').read_text())
            if prior['fingerprint']!=plan['fingerprint']:raise ValueError('The prior campaign identity changed.')
        if revised_after is not None:
            previous=Path(revised_after)
            if json.loads((previous/'plan.json').read_text())!=plan.get('previous_plan'):
                raise ValueError('A revised continuation must retain the exact earlier plan.')
            prior=json.loads((previous/'validation.json').read_text())
            failed={r['scope']+':'+r['id'] for r in prior['results'] if not r['passed']}
            if prior['fingerprint']!=plan['previous_plan']['fingerprint'] or not set(plan['retry_cases'])<=failed:
                raise ValueError('Only explicitly named failed cases may receive a revised paid attempt.')
        output=Path(output);output.mkdir(parents=True,exist_ok=False)
        report=dict(fingerprint=plan['fingerprint'],owner_fingerprint=manifest['fingerprint'],planned=56,
            cap_usd=str(cap),paid_usd='0',unresolved_maximum_usd='0',attempted=0,results=[],completed=False,
            automatic_retries=0,app_research_writes=0,owner_labels_read=0)
        (output/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n')
        def save():
            paid,pending=costs(saved_calls(funding))
            report.update(paid_usd=str(Decimal(paid)/ledger.NANO),unresolved_maximum_usd=str(Decimal(pending)/ledger.NANO))
            (output/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
        save()
        if any(c['status']!='settled' for c in existing):
            report['stopped']='prior_attempt_unsettled_or_changed';save();return report
        if any(ledger.REDISPATCH in c['request_key'] for c in existing):
            report['stopped']='prior_redispatch_refused';save();return report
        try:
            with transaction(consistent=True) as conn:
                for case in prepared:verify_access(conn,case['packet'])
        except (ValueError,KeyError):
            report['stopped']='source_access_or_context_changed';save();return report
        for case in prepared:
            key=PREFIX+digest(case['body']);filename=case['scope']+'-'+case['id']
            calls=saved_calls(funding);matching=[c for c in calls if c['request_key']==key]
            if any(c['request_key'].startswith(key) and c['request_key']!=key for c in calls):
                report['stopped']='prior_redispatch_refused';break
            old=matching[0] if matching else None
            inherited=False;retested=None
            if old is None:
                for parent in ancestors(plan):
                    previous_case=next(c for c in parent['requests'] if (c['scope'],c['id'])==(case['scope'],case['id']))
                    prior_key=PREFIX+digest(previous_case['body'])
                    prior_call=next((c for c in calls if c['request_key']==prior_key),None)
                    if prior_call is None:continue
                    if prior_call['request_hash']!=digest(previous_case['body']):
                        report['stopped']='prior_attempt_unsettled_or_changed';save();return report
                    try:
                        parse(prior_call,case['packet'])
                        valid=fits_schema(prior_call,case['body'])
                    except (ValueError,KeyError,TypeError):valid=False
                    if valid:old=prior_call;inherited=True
                    elif case['scope']+':'+case['id'] in plan.get('retry_cases',[]):retested=str(prior_call['id'])
                    else:
                        report['stopped']='prior_saved_answer_invalid_no_retry';save();return report
                    break
            if old and ((not inherited and old['request_hash']!=digest(case['body'])) or old['status']!='settled'):
                report['stopped']='prior_attempt_unsettled_or_changed';break
            try:
                with transaction(consistent=True) as conn:verify_access(conn,case['packet'])
            except (ValueError,KeyError):
                report['stopped']='source_access_or_context_changed';break
            paid,pending=costs(calls)
            if paid+pending+(0 if old else ledger.estimate(case['body']))>cap*ledger.NANO:
                report['stopped']='combined_cap_before_dispatch';break
            if old:call=old
            else:
                (output/(filename+'.request.json')).write_text(json.dumps(case['body'],ensure_ascii=False,indent=2)+'\n')
                report['attempted']+=1;save()
                try:call=ledger.execute(key,POLICY,case['body'],transport=transport)
                except Exception:
                    report['stopped']='paid_request_failed_no_retry';save();break
            save()  # Record settled cost before any response-file or validator work.
            (output/(filename+'.response.json')).write_text(json.dumps(call['response_body'],ensure_ascii=False,indent=2)+'\n')
            row=dict(scope=case['scope'],id=case['id'],call_id=str(call['id']),reused=old is not None,passed=False,
                inherited_schema=inherited,retested_call_id=retested,request_hash=call['request_hash'])
            try:prediction,repaired=parse(call,case['packet'])
            except (ValueError,KeyError,TypeError):
                report['results'].append(row);report['stopped']='validator_failure_no_retry';save();break
            row.update(passed=True,prediction=prediction,repaired=repaired)
            if case['scope']=='hard6':row['expected_tone_match']=prediction['sentiment']==case['expected_tone']
            report['results'].append(row);save()
        report['completed']=len(report['results'])==56 and all(r['passed'] for r in report['results'])
        owner={r['id']:r['prediction'] for r in report['results'] if r['passed'] and r['scope']=='owner50'}
        hard=[r for r in report['results'] if r['scope']=='hard6']
        report['hard_correct']=sum(r.get('expected_tone_match',False) for r in hard)
        report['hard_gate_passed']=len(hard)==6 and all(r['passed'] for r in hard) and report['hard_correct']>=4
        if len(owner)==50:
            (output/'owner-predictions.json').write_text(json.dumps(dict(fingerprint=manifest['fingerprint'],predictions=owner),indent=2)+'\n')
        save();return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan',type=Path);parser.add_argument('manifest',type=Path)
    parser.add_argument('--execute',action='store_true');parser.add_argument('--output',type=Path)
    parser.add_argument('--cap-usd',type=Decimal);parser.add_argument('--approved-plan')
    parser.add_argument('--remaining-after',type=Path)
    parser.add_argument('--revised-after',type=Path)
    parser.add_argument('--reuse-settled',action='store_true',help='Read settled answers to identical requests free; never re-send one.')
    parser.add_argument('--thread-variant',type=Path,help='Write a full-thread-context plan built from PLAN to this new file.')
    parser.add_argument('--parents-variant',type=Path,help='Write a verified-parent plan built from PLAN to this new file.')
    parser.add_argument('--parent-checks',type=Path,help='Private reply-chain results used by --parents-variant.')
    args=parser.parse_args();plan=json.loads(args.plan.read_text());manifest=json.loads(args.manifest.read_text())
    if args.thread_variant:
        if args.thread_variant.exists():parser.error('Choose a new file for the thread-context plan.')
        variant=thread_plan(plan,manifest)
        args.thread_variant.write_text(json.dumps(variant,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(estimate(variant,manifest),indent=2));sys.exit()
    if args.parents_variant:
        if args.parents_variant.exists() or args.parent_checks is None:parser.error('Choose a new plan file and the parent-check results.')
        variant=parents_plan(plan,manifest,json.loads(args.parent_checks.read_text()))
        args.parents_variant.write_text(json.dumps(variant,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(estimate(variant,manifest),indent=2));sys.exit()
    if args.execute:
        if args.output is None or args.cap_usd is None:parser.error('Execution requires a new output folder and explicit cap.')
        result=run(plan,manifest,args.output,args.cap_usd,approved_plan=args.approved_plan,remaining_after=args.remaining_after,revised_after=args.revised_after,reuse_settled=args.reuse_settled)
        print(json.dumps({k:v for k,v in result.items() if k!='results'},indent=2))
    else:print(json.dumps(estimate(plan,manifest),indent=2))
