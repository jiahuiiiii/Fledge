"""Ledger-backed campaign with invented sources and transport, never network."""
from copy import deepcopy
from decimal import Decimal
import json
import pytest
from experiments.soclaas_replay import news_noise_campaign as C
from test_news_noise_replay import dataset
from test_sentiment_task_runner import provider
from test_model_budget import clean_model_ledger  # noqa:F401


def inputs(*,missing=False,baseline=True):
    capture,evaluated=dataset(baseline=baseline)
    records=[]
    for index,value in enumerate([*evaluated['baselines'].values(),*evaluated['frames'].values()]):
        value=deepcopy(value)
        if missing:
            value['packet']['sources']=[s for s in value['packet']['sources'] if s['id']!='source-7']
            value['result']['items']=[i for i in value['result']['items'] if i['source_id']!='source-7']
        records.append(dict(value,id='analysis-'+str(index),call_id='original-'+str(index),created_at=value['packet']['cutoff']))
    return capture,records,C.freeze(capture,records)


@pytest.fixture
def access(monkeypatch):
    checked=[]
    def verify(packet):checked.append(packet['instrument_id'])
    monkeypatch.setattr(C,'access',verify)
    return checked


def run(plan,path,transport,**kwargs):
    return C.run(plan,path,Decimal('6'),approved_plan=plan['fingerprint'],transport=transport,**kwargs)


def next_purpose(plan,monkeypatch):
    monkeypatch.setattr(C.T,'EVENT_POLICY','authored-next-purpose')
    monkeypatch.setattr(C.T,'EVENT_INSTRUCTION',C.T.EVENT_INSTRUCTION+'\nAuthored next purpose.')
    monkeypatch.setitem(C.T.INSTRUCTIONS,'event',C.T.EVENT_INSTRUCTION)
    core=dict(policy=C.POLICY,contract=C.contract(),capture=deepcopy(plan['capture']),reused=deepcopy(plan['reused']))
    return dict(core,fingerprint=C.N.digest(core))


def test_new_purpose_requires_completed_prior_plan_and_saved_only_never_pays(tmp_path,access,monkeypatch):
    _,_,plan=inputs();first=run(plan,tmp_path/'first',provider([]));assert first['completed']
    new=next_purpose(plan,monkeypatch)
    free=run(new,tmp_path/'free',lambda _:pytest.fail('Saved-only paid'),after_completed=tmp_path/'first',saved_only=True)
    assert free['attempted']==0 and free['stopped']=='new_request_needed_saved_only'
    assert free['paid_usd']==first['paid_usd'] and free['after_completed_fingerprint']==plan['fingerprint']
    paid=run(new,tmp_path/'next',provider([]),after_completed=tmp_path/'first')
    assert paid['completed'] and Decimal(paid['paid_usd'])>Decimal(first['paid_usd'])
    assert not paid['automatic_retries']


def test_new_purpose_cannot_change_sources_tones_or_ignore_an_unfinished_run(tmp_path,access,monkeypatch):
    _,_,plan=inputs();run(plan,tmp_path/'first',provider([]))
    with pytest.raises(ValueError,match='identical purpose'):run(plan,tmp_path/'identical',provider([]),after_completed=tmp_path/'first')
    new=next_purpose(plan,monkeypatch)
    changed=deepcopy(new);sid=next(iter(changed['reused']));changed['reused'][sid]['analysis_id']='another-origin'
    changed['fingerprint']=C.N.digest({k:v for k,v in changed.items() if k!='fingerprint'})
    with pytest.raises(ValueError,match='exact sources'):run(changed,tmp_path/'changed',provider([]),after_completed=tmp_path/'first')
    report_path=tmp_path/'first/campaign.json';report=json.loads(report_path.read_text());report['completed']=False;report_path.write_text(json.dumps(report))
    with pytest.raises(ValueError,match='completed prior'):run(new,tmp_path/'unfinished',provider([]),after_completed=tmp_path/'first')


def test_frozen_plan_keeps_exact_old_tones_and_contracts_without_dispatch():
    capture,records,plan=inputs();before=deepcopy(records)
    report=C.estimate(plan)
    assert report['reused_tone_versions']==8 and report['missing_tone_versions']==0
    assert report['event_requests_before_new_quick_skips']==7 and report['paid_calls']==0
    assert C.ledger.snapshot()['calls']==0 and records==before
    changed=deepcopy(plan);changed['contract']['schema_policy']='changed'
    changed['fingerprint']=C.N.digest({k:v for k,v in changed.items() if k!='fingerprint'})
    with pytest.raises(ValueError,match='contracts changed'):C.validate(changed)


def test_full_mocked_campaign_reuses_tones_and_only_persists_ledger_and_private_replay(tmp_path,access):
    _,_,plan=inputs();seen=[];report=run(plan,tmp_path/'once',provider(seen))
    assert report['completed'] and report['frames_completed']==7
    assert 'tone' not in seen and 'quick' not in seen and seen.count('event')==7
    assert report['automatic_retries']==report['telegram_http_calls']==report['app_writes']==0
    assert report['noise_gate']=='pending_independent_review' and len(access)>7
    replay=json.loads((tmp_path/'once/replay.json').read_text())
    assert replay['completed_input_days']==7 and replay['counts']['immediate']==7
    assert Decimal(report['paid_usd'])>0 and report['unresolved_maximum_usd']=='0'
    with pytest.raises(ValueError,match='explicit'):run(plan,tmp_path/'other-folder',provider(seen))


def test_missing_tone_uses_selected_quick_check_and_skips_event_when_unrelated(tmp_path,access):
    _,_,plan=inputs(missing=True);seen=[];report=run(plan,tmp_path/'missing',provider(seen))
    assert report['completed'] and seen.count('quick')==1 and 'tone' not in seen
    assert seen.count('event')==6


def test_first_observed_sample_without_baseline_needs_no_importance_or_publication(tmp_path,access):
    _,_,plan=inputs(baseline=False);seen=[];report=run(plan,tmp_path/'quiet',provider(seen))
    assert report['completed'] and seen.count('event')==6
    replay=json.loads((tmp_path/'quiet/replay.json').read_text())
    assert replay['counts']['immediate']==6


def test_missing_relevant_source_gets_tone_then_event_with_separate_calls(tmp_path,access):
    _,_,plan=inputs(missing=True);seen=[];normal=provider(seen)
    def output(body):
        response=normal(body)
        if body['input'][0]['content'].startswith('Label whether'):
            data=json.loads(response['output'][0]['content'][0]['text'])
            for item in data['items']:item['relevance']='relevant'
            response['output'][0]['content'][0]['text']=json.dumps(data)
        return response
    report=run(plan,tmp_path/'fresh',output)
    assert report['completed'] and seen.count('tone')==seen.count('quick')==1 and seen.count('event')==7
    evaluated=json.loads((tmp_path/'fresh/evaluated.json').read_text())
    item=next(i for r in evaluated['frames'].values() for i in r['result']['items'] if i['source_id']=='source-7')
    assert item['call_id']!=item['importance']['call_id'] and item['prompt_version']==C.T.PROMPT


@pytest.mark.parametrize('failure',['invalid','timeout'])
def test_first_paid_failure_stops_and_another_folder_cannot_retry(tmp_path,access,failure):
    _,_,plan=inputs();seen=[];normal=provider(seen,fail='event')
    def output(body):
        if failure=='timeout':seen.append('timeout');raise TimeoutError('Authored transport failure')
        return normal(body)
    first=run(plan,tmp_path/'first',output)
    assert not first['completed'] and first['attempted']==len(seen)==1
    if failure=='timeout':assert Decimal(first['unresolved_maximum_usd'])>0
    else:assert Decimal(first['paid_usd'])>0
    with pytest.raises(ValueError):run(plan,tmp_path/'new',provider(seen))
    continued=run(plan,tmp_path/'continued',provider(seen),remaining_after=tmp_path/'first')
    assert continued['attempted']==0 and not continued['completed'] and len(seen)==1


def test_explicit_free_validator_recheck_continues_only_with_never_attempted_calls(tmp_path,access,monkeypatch):
    _,_,plan=inputs();seen=[];parse=C.T.event_labels
    def invalid(*args):raise ValueError('Authored temporary validator stop')
    monkeypatch.setattr(C.T,'event_labels',invalid)
    first=run(plan,tmp_path/'first',provider(seen));assert not first['completed'] and len(seen)==1
    monkeypatch.setattr(C.T,'event_labels',parse)
    report=run(plan,tmp_path/'remaining',provider(seen),remaining_after=tmp_path/'first')
    assert report['completed'] and report['attempted']==len(seen)-1
    assert len({call['request_hash'] for call in C.saved_calls()})==len(seen)


@pytest.mark.parametrize('cap',[Decimal('0'),Decimal('NaN'),Decimal('Infinity'),Decimal('9')])
def test_invalid_cap_cannot_create_an_output_or_dispatch(tmp_path,access,cap):
    _,_,plan=inputs()
    with pytest.raises(ValueError):C.run(plan,tmp_path/'invalid',cap,approved_plan=plan['fingerprint'],transport=lambda _:pytest.fail('dispatch'))
    assert not (tmp_path/'invalid').exists() and C.ledger.snapshot()['calls']==0


def test_combined_reservation_cap_is_checked_before_the_first_dispatch(tmp_path,access):
    _,_,plan=inputs();report=C.run(plan,tmp_path/'cap',Decimal('.000001'),approved_plan=plan['fingerprint'],
        transport=lambda _:pytest.fail('dispatch'))
    assert report['attempted']==0 and report['stopped']=='combined_cap_before_dispatch'
    assert report['paid_usd']=='0' and C.ledger.snapshot()['calls']==0


def test_all_source_permissions_are_checked_before_any_payment(tmp_path,monkeypatch):
    _,_,plan=inputs()
    def revoked(packet):raise ValueError('Authored source withdrawal')
    monkeypatch.setattr(C,'access',revoked)
    report=run(plan,tmp_path/'revoked',lambda _:pytest.fail('dispatch'))
    assert report['attempted']==0 and not report['completed'] and C.ledger.snapshot()['calls']==0


def test_continuation_cannot_change_inputs_or_erase_previous_costs(tmp_path,access,monkeypatch):
    _,_,plan=inputs();seen=[];normal=provider(seen);parse=C.T.event_labels
    monkeypatch.setattr(C.T,'event_labels',lambda *args:(_ for _ in ()).throw(ValueError('Authored stop')))
    first=run(plan,tmp_path/'first',normal)
    monkeypatch.setattr(C.T,'event_labels',parse)
    changed=deepcopy(plan);changed['capture']['companies'][0]['name']='Different company'
    with pytest.raises(ValueError):run(changed,tmp_path/'changed',normal,remaining_after=tmp_path/'first')
    cap=Decimal(first['paid_usd'])
    result=C.run(plan,tmp_path/'cap',cap,approved_plan=plan['fingerprint'],transport=normal,remaining_after=tmp_path/'first')
    assert not result['completed'] and result['attempted']==0 and len(seen)==1
    assert result['paid_usd']==first['paid_usd']


def test_read_write_snapshot_is_rejected_before_loading_frozen_candidates():
    capture,_,_=inputs()
    class Writable:
        def execute(self,sql):assert sql=='SHOW transaction_read_only';return self
        def fetchone(self):return dict(transaction_read_only='off')
    with pytest.raises(ValueError,match='read-only'):C.collect(Writable(),capture)


def old_schema_run(tmp_path,monkeypatch,access):
    current=C.T.bounded_schema;seen=[];normal=provider(seen)
    def old_schema(task,sources):
        if task!='event':return current(task,sources)
        schema=C.T.strict_schema(C.T.EventResult)
        schema['$defs']['EventItem']['properties']['id']['enum']=[s['label'] for s in sources]
        return schema
    def invalid_third(body):
        answer=normal(body)
        if len(seen)==3:
            value=json.loads(answer['output'][0]['content'][0]['text'])
            value['items'][0]['reporting']['passages']=['A headline is not a passage ID']
            answer['output'][0]['content'][0]['text']=json.dumps(value)
        return answer
    with monkeypatch.context() as old:
        old.setattr(C.T,'bounded_schema',old_schema);old.setattr(C.T,'SCHEMA_POLICY','authored-schema-2')
        _,_,plan=inputs();report=run(plan,tmp_path/'old',invalid_third)
    assert len(seen)==3 and sum(c['passed'] for c in report['calls'])==2
    return plan,report,seen,normal


def test_revised_news_schema_reuses_valid_answers_and_retests_only_explicit_failed_request(tmp_path,access,monkeypatch):
    old,first,seen,normal=old_schema_run(tmp_path,monkeypatch,access)
    failed=first['calls'][-1]['request_hash'];revised=C.revised_plan(old,[failed])
    report=run(revised,tmp_path/'revision',normal,revised_after=tmp_path/'old')
    assert report['completed'] and report['attempted']==len(seen)-3
    assert sum(c['inherited_schema'] for c in report['calls'])>=1
    assert sum(bool(c['retested_call_id']) for c in report['calls'])==1
    assert Decimal(report['paid_usd'])==Decimal(C.spend(C.saved_calls())[0])/C.ledger.NANO
    assert Decimal(report['paid_usd'])>Decimal(first['paid_usd'])


def test_saved_only_revision_never_dispatches_even_with_a_large_cap(tmp_path,access,monkeypatch):
    old,first,seen,normal=old_schema_run(tmp_path,monkeypatch,access)
    revised=C.revised_plan(old,[first['calls'][-1]['request_hash']])
    report=run(revised,tmp_path/'free',lambda _:pytest.fail('Saved-only execution dispatched'),
        revised_after=tmp_path/'old',saved_only=True)
    assert not report['completed'] and report['attempted']==0 and len(seen)==3
    assert report['stopped']=='new_request_needed_saved_only' and report['paid_usd']==first['paid_usd']
    assert sum(c['passed'] for c in report['calls'])==2


def test_schema_revision_without_failed_case_authorization_cannot_redispatch_it(tmp_path,access,monkeypatch):
    old,first,seen,normal=old_schema_run(tmp_path,monkeypatch,access)
    revised=C.revised_plan(old,[])
    report=run(revised,tmp_path/'not-approved',normal,revised_after=tmp_path/'old')
    assert report['attempted']==0 and not report['completed'] and len(seen)==3
    assert report['stopped']=='validator_failure_no_retry'
    valid=C.revised_plan(old,[first['calls'][0]['request_hash']])
    with pytest.raises(ValueError,match='explicitly named failed'):
        run(valid,tmp_path/'valid-cannot-retry',normal,revised_after=tmp_path/'old')


def test_schema_revision_keeps_original_failed_charge_in_budget(tmp_path,access,monkeypatch):
    old,first,seen,normal=old_schema_run(tmp_path,monkeypatch,access)
    revised=C.revised_plan(old,[first['calls'][-1]['request_hash']])
    result=C.run(revised,tmp_path/'bounded-revision',Decimal(first['paid_usd']),approved_plan=revised['fingerprint'],
        transport=normal,revised_after=tmp_path/'old')
    assert result['attempted']==0 and result['stopped']=='combined_cap_before_dispatch' and len(seen)==3
    assert result['paid_usd']==first['paid_usd']
    changed=deepcopy(revised);changed['capture']['companies'][0]['name']='Changed'
    changed['fingerprint']=C.N.digest({k:v for k,v in changed.items() if k!='fingerprint'})
    with pytest.raises(ValueError):C.validate(changed)
