"""Opt-in split pipeline with invented output and the real disposable ledger."""
from copy import deepcopy
import json
from uuid import uuid4
from unittest.mock import patch
import pytest
from thesis.providers import ledger
from thesis.research import sentiment as S,sentiment_batching as B,sentiment_tasks as T
from thesis.research import sentiment_task_runner as R
from test_model_budget import clean_model_ledger,response  # noqa: F401
from test_sentiment_tasks import packet,tones,events


def provider(seen, *, fail=None):
    def send(body):
        data=json.loads(body['input'][1]['content'])
        instruction=body['input'][0]['content']
        if instruction.startswith('Label whether'):
            task='quick';result=dict(items=[dict(label=s['label'],relevance='unrelated') for s in data['sources']])
        elif 'candidate_pairs' in data:
            task='duplicate';result=dict(coverage_links=[])
        elif instruction==T.EVENT_INSTRUCTION:
            task='event';result=dict(items=events(dict(sources=data['sources'])))
        else:
            task='tone';result=dict(items=tones(dict(sources=data['sources'])))
        seen.append(task)
        if task==fail:
            if fail=='tone':result['items'][0]['passages']=['invented']
            else:result['items']=[]
        return response()|dict(model=body['model'],id='resp_'+str(uuid4()),
            output=[dict(type='message',content=[dict(type='output_text',text=json.dumps(result))])])
    return send


def reuse(result):
    return {item['source_id']:dict(item=deepcopy(item),links=[],analysis_id='authored-analysis',
        call_id=item.get('call_id') or str(uuid4())) for item in result['items']}


def test_default_off_and_explicit_pipeline_change_identity(monkeypatch):
    p=packet();old=B.plan_identity(p)
    assert not R.enabled()
    monkeypatch.setenv('THESIS_SENTIMENT_TASKS','true')
    assert B.plan_identity(p)!=old and B.plan_identity(p)==R.identity(p)
    p['cutoff']='2026-10-09T00:00:00+00:00'
    assert B.plan_identity(p)==R.identity(p)


def test_tone_and_event_are_separate_and_saved_calls_are_reused(monkeypatch):
    monkeypatch.setenv('THESIS_SENTIMENT_TASKS','true');p=packet();seen=[]
    with patch.object(B,'check_access'):
        result,calls=B.run(p,transport=provider(seen),prefilter=False)
        assert seen==['tone','event'] and len(calls)==2
        assert len(result['items'])==4 and result['prompt_version']==T.PROMPT
        assert [i['importance']['level'] for i in result['items'] if i['channel']=='news']==['high','high']
        assert all(i['call_id'] and i['model']==T.SENTIMENT_MODEL for i in result['items'])
        again,old_calls=B.run(p,transport=lambda _:pytest.fail('Repeated paid request'),prefilter=False)
        assert [i['sentiment'] for i in again['items']]==[i['sentiment'] for i in result['items']]
        assert [c['id'] for c in old_calls]==[c['id'] for c in calls]
        assert B.fully_saved(p,prefilter=False)


def test_saved_old_tones_are_not_reread_but_missing_importance_is_filled():
    p=packet();old=S.render(R.response([dict(item,**({'reporting':dict(kind='not_applicable',passages=[],impact='not_stated')} if s['channel']=='news' else {}))
        for item,s in zip(tones(p),p['sources'])]),p)
    for item in old['items']:item.update(model='original-priced-model',call_id='original-call',prompt_version=S.PROMPT)
    saved=reuse(old);seen=[]
    with patch.object(B,'check_access'):
        result,calls=R.run(p,saved,transport=provider(seen),prefilter=False)
    assert seen==['event'] and len(calls)==1
    assert result['source_reuse']['reused']==4
    assert all(i['model']=='original-priced-model' and i['call_id']=='original-call' and i['prompt_version']==S.PROMPT for i in result['items'])
    assert all(i['importance']['call_id']!=i['call_id'] for i in result['items'] if i['channel']=='news')
    assert all('importance' not in i for i in old['items'])
    with patch.object(B,'check_access'):
        same,calls=R.run(p,reuse(result),transport=lambda _:pytest.fail('All labels saved'),prefilter=False)
    assert not calls and same['items']==result['items']


def test_importance_backfill_preserves_both_old_tone_and_new_event_repair_reasons():
    p=packet();raw=tones(p);raw[0].update(sentiment='negative',basis='descriptive')
    old=S.render(R.response([dict(item,**({'reporting':dict(kind='not_applicable',passages=[],impact='not_stated')}
        if s['channel']=='news' else {})) for item,s in zip(raw,p['sources'])]),p)
    before=deepcopy(old);seen=[];normal=provider(seen)
    def backfill(body):
        result=normal(body)
        content=json.loads(result['output'][0]['content'][0]['text'])
        content['items'][0]['reporting'].update(kind='opinion_only')
        result['output'][0]['content'][0]['text']=json.dumps(content)
        return result
    with patch.object(B,'check_access'):
        result,_=R.run(p,reuse(old),transport=backfill,prefilter=False)
    repaired=result['items'][0]
    assert seen==['event'] and old==before
    assert set(repaired['repair']['reasons'])=={'tone_basis_disagree','event_fields_inconsistent'}
    assert repaired['repair']['reporting_original']['kind']=='opinion_only'
    assert repaired['repair']['reporting_call_id']==repaired['importance']['call_id']
    assert repaired['importance']['level']=='low' and not repaired['reporting_basis']['eligible']


@pytest.mark.parametrize('task',['tone','event'])
def test_first_invalid_task_stops_and_is_not_automatically_retried(task):
    p=packet();seen=[]
    with patch.object(B,'check_access'):
        with pytest.raises(ValueError):R.run(p,transport=provider(seen,fail=task),prefilter=False)
        count=len(seen)
        with pytest.raises(ValueError):R.run(p,transport=lambda _:pytest.fail('Automatic retry'),prefilter=False)
    assert len(seen)==count and ledger.snapshot()['calls']==count


def test_quick_unrelated_sources_are_saved_without_tone_or_event_calls():
    p=packet();seen=[]
    with patch.object(B,'check_access'):
        result,calls=R.run(p,transport=provider(seen),prefilter=True)
    assert seen==['quick'] and len(calls)==1 and len(result['items'])==4
    assert all(i['prefilter'] and i['relevance']=='unrelated' for i in result['items'])
    assert result['prefilter']['skipped']==4
    with patch.object(B,'check_access'):
        again,calls=R.run(p,reuse(result),transport=lambda _:pytest.fail('Reused quick check'),prefilter=True)
    assert not calls and again['items']==result['items']


def test_access_cancel_and_saved_only_never_dispatch():
    p=packet()
    with patch.object(B,'check_access',side_effect=ValueError('Source access changed')):
        with pytest.raises(ValueError,match='access'):R.run(p,transport=lambda _:pytest.fail('Withdrawn source'),prefilter=False)
    with patch.object(B,'check_access'):
        with pytest.raises(ValueError):R.run(p,transport=lambda _:pytest.fail('Saved-only dispatched'),prefilter=False,saved_only=True)
    assert ledger.snapshot()['calls']==0


def test_whole_source_plans_split_by_count_and_size_without_losing_context():
    p=packet();p['sources']*=3
    for n,source in enumerate(p['sources']):
        p['sources'][n]=dict(source,id=f'authored-{n}',label=f'item_{n}')
    parts=R.plan('tone',p,p['sources'])
    assert [len(part['sources']) for part in parts]==[8,4]
    assert {s['id'] for part in parts for s in part['sources']}=={s['id'] for s in p['sources']}
    p['sources'][0]['text']='x'*50000;p['sources'][0]['passages']=[dict(id='p1',quote='x'*50000)]
    with pytest.raises(ValueError,match='complete source'):R.plan('tone',p,p['sources'])


def test_explicit_retry_then_terminal_split_preserves_paid_results_and_cannot_repeat():
    # The explicit recovery path, with the automatic half-split switched off.
    p=packet();seen=[];bad=provider(seen,fail='tone');manual=dict(auto_split=False)
    with patch.object(B,'check_access'):
        with pytest.raises(ValueError):R.run(p,transport=bad,prefilter=False,**manual)
        with pytest.raises(ValueError):R.run(p,transport=bad,prefilter=False,retry_failed=True,**manual)
        assert seen==['tone','tone']
        with pytest.raises(ValueError):R.run(p,transport=lambda _:pytest.fail('Unapproved split'),prefilter=False,**manual)
        result,calls=R.run(p,transport=provider(seen),prefilter=False,split_failed=True,**manual)
        assert seen==['tone','tone','tone','tone','event']
        assert len(result['items'])==4 and len(calls)==3 and result['tasks']['recovery']
        again,calls=R.run(p,transport=lambda _:pytest.fail('Automatic repeated recovery'),prefilter=False,**manual)
        assert again['summary']==result['summary'] and len(calls)==3
    assert ledger.snapshot()['calls']==5


def test_a_failed_terminal_child_cannot_retry_or_split_again():
    p=packet();seen=[];bad=provider(seen,fail='tone')
    with patch.object(B,'check_access'):
        for options in ({},{'retry_failed':True},{'split_failed':True}):
            with pytest.raises(ValueError):R.run(p,transport=bad,prefilter=False,**options)
        count=len(seen)
        for options in ({},{'retry_failed':True},{'split_failed':True}):
            with pytest.raises(ValueError):R.run(p,transport=lambda _:pytest.fail('Terminal child resent'),prefilter=False,**options)
    assert len(seen)==count==3


def test_real_generation_bridges_old_prompt_without_rereading_tones(owner,monkeypatch):
    from test_market import prepare
    from test_sentiment import provider as legacy_provider
    from thesis.db import transaction,one
    iid=prepare(owner)
    old=S.generate(iid,transport=legacy_provider('neutral'))
    with transaction() as conn:
        before=one(conn,'SELECT result FROM sentiment_analyses WHERE id=%s',(old['id'],))['result']
    monkeypatch.setenv('THESIS_SENTIMENT_TASKS','true');seen=[]
    new=S.generate(iid,transport=provider(seen))
    assert 'tone' not in seen and new['source_reuse']['reused']==len(old['items'])
    assert not new['earlier_method'] and new['prompt_version']==T.PROMPT
    assert all(i['call_id'] in {x['call_id'] for x in old['items']} for i in new['items'])
    with transaction() as conn:
        assert one(conn,'SELECT result FROM sentiment_analyses WHERE id=%s',(old['id'],))['result']==before
    repeat=S.generate(iid,transport=lambda _:pytest.fail('Unchanged whole reading'))
    assert repeat['id']==new['id']


@pytest.mark.parametrize('old_prompt',['thesis-source-sentiment-tasks-1','thesis-source-sentiment-tasks-2'])
def test_rubric_revision_preserves_old_task_labels_and_their_actual_provenance(owner,monkeypatch,old_prompt):
    from test_market import prepare
    from thesis.db import transaction,one
    iid=prepare(owner)
    monkeypatch.setenv('THESIS_SENTIMENT_TASKS','true')
    with monkeypatch.context() as earlier:
        earlier.setattr(T,'PROMPT',old_prompt)
        earlier.setattr(T,'INSTRUCTIONS',dict(T.INSTRUCTIONS,tone='Authored earlier tone instructions'))
        before=S.generate(iid,transport=provider([]))
    with transaction() as conn:
        original=deepcopy(one(conn,'SELECT result FROM sentiment_analyses WHERE id=%s',(before['id'],))['result'])
    after=S.generate(iid,transport=lambda _:pytest.fail('Prompt revision forced a paid reread'))
    assert after['prompt_version']==T.PROMPT!=old_prompt
    assert after['source_reuse']['reused']==len(before['items'])
    for prior,current in zip(before['items'],after['items']):
        for field in ('sentiment','model','call_id','prompt_version'):
            assert current[field]==prior[field]
        assert current['prompt_version']==old_prompt
    with transaction() as conn:
        assert one(conn,'SELECT result FROM sentiment_analyses WHERE id=%s',(before['id'],))['result']==original


def test_duplicate_comparisons_run_only_for_candidates_and_save_negative_checks():
    p=packet();p['sources']=[p['sources'][0],p['sources'][2]]
    p['sources'][0]['title']='Lumen signs Cedar supply contract for factory chips'
    p['sources'][1]['title']='Lumen signs Cedar supply contract for new factory chips'
    seen=[]
    with patch.object(B,'check_access'):
        result,calls=R.run(p,transport=provider(seen),prefilter=False)
        assert seen==['tone','event','duplicate']
        assert result['items'][1]['duplicate_candidates_checked'] and result['coverage_links']==[]
        repeated,calls=R.run(p,reuse(result),transport=lambda _:pytest.fail('Candidate already checked'),prefilter=False)
    assert not calls and repeated['items']==result['items']


def test_unresolved_task_is_never_resent_even_by_explicit_retry():
    seen=[]
    def timeout(body):seen.append(True);raise TimeoutError('Invented timeout')
    with patch.object(B,'check_access'):
        with pytest.raises(ledger.BudgetBlocked):R.run(packet(),transport=timeout,prefilter=False)
        for options in ({},{'retry_failed':True},{'split_failed':True}):
            with pytest.raises(ledger.BudgetBlocked):
                R.run(packet(),transport=lambda _:pytest.fail('Uncertain charge resent'),prefilter=False,**options)
    assert seen==[True] and ledger.snapshot()['unresolved']==1


def test_duplicate_ids_or_labels_block_before_any_paid_task():
    p=packet();p['sources'].append(deepcopy(p['sources'][0]))
    with pytest.raises(ValueError,match='distinct'):
        R.run(p,transport=lambda _:pytest.fail('Duplicate source dispatched'),prefilter=False)


def test_switch_bridge_is_whitelisted_and_rollback_does_not_reuse_new_prompt(monkeypatch):
    from thesis.research import sentiment_reuse as U
    p=packet();record=dict(packet=p,result=dict(prompt_version=S.PROMPT,model=T.SENTIMENT_MODEL,
        summary_policy=S.POLICY,guard_policy=p.get('guard_policy')))
    assert U.compatible(record,p)
    monkeypatch.setenv('THESIS_SENTIMENT_TASKS','true')
    assert U.compatible(record,p)
    record['result']['prompt_version']=T.PROMPT
    assert U.compatible(record,p)
    monkeypatch.setenv('THESIS_SENTIMENT_RELIABILITY','false')
    assert U.compatible(record,p)  # exact new prompt remains reusable
    record['result']['prompt_version']=S.PROMPT
    assert not U.compatible(record,p)  # cross-prompt bridge is part of phase1
    monkeypatch.setenv('THESIS_SENTIMENT_TASKS','false')
    record['result']['prompt_version']=T.PROMPT
    assert not U.compatible(record,p)



def sized(seen, *, fail_sizes):
    """Tone answers fail only for batches of the given sizes; everything else passes."""
    good=provider([])
    def send(body):
        data=json.loads(body['input'][1]['content'])
        is_tone=body['input'][0]['content'] not in (T.EVENT_INSTRUCTION,) and 'candidate_pairs' not in data
        seen.append(('tone' if is_tone else 'event',len(data['sources'])))
        reply=good(body)
        if is_tone and len(data['sources']) in fail_sizes:
            text=json.loads(reply['output'][0]['content'][0]['text']);text['items'][0]['passages']=['invented']
            reply['output'][0]['content'][0]['text']=json.dumps(text)
        return reply
    return send


def test_failed_batch_is_retried_once_as_two_halves_and_the_reading_completes():
    p=packet();seen=[]
    with patch.object(B,'check_access'):
        result,calls=R.run(p,transport=sized(seen,fail_sizes={4}),prefilter=False,auto_split=True)
        assert seen[0]==('tone',4) and sorted(seen[1:3])==[('tone',2),('tone',2)]
        assert len(result['items'])==4
        [recovery]=result['tasks']['recovery']
        assert recovery['automatic'] and recovery['task']=='tone' and len(recovery['child_keys'])==2
        # The next reading reuses the halves; nothing is resent.
        again,_=R.run(p,transport=lambda _:pytest.fail('Repeated paid request'),prefilter=False,auto_split=True)
        assert again['summary']==result['summary']
    assert ledger.snapshot()['calls']==len(seen)


def test_a_failed_half_stops_and_is_never_retried_again():
    p=packet();seen=[]
    with patch.object(B,'check_access'):
        with pytest.raises(ValueError):R.run(p,transport=sized(seen,fail_sizes={4,2}),prefilter=False,auto_split=True)
        sent=list(seen)
        assert sent[0]==('tone',4) and all(size==2 for _,size in sent[1:]) and 2<=len(sent)<=3
        # Later automatic readings stay stopped: no second automatic retry is sent.
        for _ in range(2):
            with pytest.raises(ValueError):
                R.run(p,transport=lambda _:pytest.fail('Second automatic retry'),prefilter=False,auto_split=True)
        assert ledger.snapshot()['calls']==len(sent)
        # An explicit owner retry remains available, as before.
        with pytest.raises(ValueError):R.run(p,transport=sized(seen,fail_sizes={4,2}),prefilter=False,retry_failed=True,auto_split=True)
        assert len(seen)>len(sent)


def test_a_single_source_batch_is_not_split():
    p=packet();p['sources']=p['sources'][:1];seen=[]
    with patch.object(B,'check_access'):
        with pytest.raises(ValueError):R.run(p,transport=sized(seen,fail_sizes={1}),prefilter=False,auto_split=True)
    assert seen==[('tone',1)]


def test_automatic_split_can_be_switched_off(monkeypatch):
    monkeypatch.setenv('THESIS_SENTIMENT_AUTO_SPLIT','false')
    assert not R.auto_split_enabled()
    p=packet();seen=[]
    with patch.object(B,'check_access'):
        with pytest.raises(ValueError):R.run(p,transport=sized(seen,fail_sizes={4}),prefilter=False)
    assert seen==[('tone',4)]
    monkeypatch.delenv('THESIS_SENTIMENT_AUTO_SPLIT')
    assert R.auto_split_enabled()
