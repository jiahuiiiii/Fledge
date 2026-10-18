"""Frozen quality execution uses invented inputs and the disposable model ledger."""
from copy import deepcopy
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import hashlib,json
from uuid import uuid4
import pytest
from thesis.db import transaction,one
from thesis.providers import ledger
from thesis.research.citations import source_passages
from experiments.sentiment_batching.controls import packet as controls
from experiments.soclaas_replay import owner_quality_set as Q,sentiment_quality_validation as V
from test_model_budget import clean_model_ledger,response  # noqa:F401


def hard_input(packet,index):
    body=V.T.request_for('tone',packet)
    value=json.loads(body['input'][1]['content'])
    value['sources'][0]['label']=V.HARD_REFERENCES[index][1]
    body['input'][1]['content']=ledger.canonical(value)
    return V.hard_case(body,packet,index)


def fixtures():
    packets=[]
    for symbol in ('EXA','EXB'):
        p=controls();p['company']=dict(symbol=symbol,name=symbol+' Example');p['sources']=[]
        for channel in ('news','social'):
            for index in range(26):
                title=f'Authored {symbol} {channel} {index}'
                text=f'{symbol} described its service in this authored example.'
                passages,_=source_passages(title,text)
                p['sources'].append(dict(id=f'{symbol}-{channel}-{index}',label=f'item_{len(p["sources"])+1}',
                    channel=channel,platform='reddit' if channel=='social' else None,title=title,text=text,passages=passages,
                    published_at='2026-10-07T12:00:00+00:00',available_at='2026-10-07T12:00:00+00:00',
                    url='https://example.invalid/'+title.replace(' ','-'),content_hash=hashlib.sha256(title.encode()).hexdigest()))
        packets.append(p)
    manifest=Q.build(packets)
    by_symbol={p['company']['symbol']:p for p in packets}
    owner={c['id']:by_symbol[c['company']] for c in manifest['cases']}
    hard=[]
    for index,tone in enumerate(V.HARD_TONES):
        p=deepcopy(packets[0]);s=deepcopy(p['sources'][0]);s['id']=f'hard-source-{index+1}'
        p['sources']=[s]
        hard.append(hard_input(p,index))
    return manifest,V.make_plan(manifest,owner,hard)


def provider(seen,*,failure=None):
    def send(body):
        seen.append(body)
        if failure=='timeout':raise TimeoutError('Authored private transport failure')
        payload=json.loads(body['input'][1]['content']);s=payload['sources'][0]
        tone=V.HARD_TONES[int(s['id'].split('-')[-1])-1] if s['id'].startswith('hard-source-') else 'neutral'
        item=dict(id=s['label'],relevance='relevant',sentiment=tone,statement='opinion',topic='general',
            passages=['p1'],previous_passages=[],context_passages=[],price_claims=[],
            basis='unclear' if tone=='unclear' else 'descriptive' if tone=='neutral' else 'expressed_evaluation')
        return response()|dict(id='resp_'+str(uuid4()),model=body['model'],
            output=[dict(type='message',content=[dict(type='output_text',text=json.dumps(dict(items=[] if failure=='invalid' else [item])))])])
    return send


@pytest.fixture
def access(monkeypatch):
    seen=[]
    def verify(conn,packet):
        assert conn.execute('SHOW transaction_read_only').fetchone()['transaction_read_only']=='on'
        seen.append(packet['sources'][0]['id'])
    monkeypatch.setattr(V,'verify_access',verify)
    return seen


def execute(manifest,plan,path,transport,**kwargs):
    return V.run(plan,manifest,path,Decimal('2'),approved_plan=plan['fingerprint'],transport=transport,**kwargs)


def test_default_estimate_has_no_calls_or_owner_answers():
    m,p=fixtures();before=ledger.snapshot()['calls'];result=V.estimate(p,m)
    assert result['owner_cases']==50 and result['hard_cases']==6 and result['requests']==56
    assert result['paid_calls']==0 and ledger.snapshot()['calls']==before
    assert Decimal(result['largest_reservation_usd'])>0
    assert all(c['body']['input'][0]['content']==V.T.TONE_INSTRUCTION for c in p['requests'])


def test_plan_refuses_changed_review_context_model_body_and_denominators():
    m,p=fixtures()
    for change in ('context','body','model','count'):
        bad=deepcopy(p)
        if change=='context':bad['requests'][0]['packet']['sources'][0]['title']='Another title'
        elif change=='body':bad['requests'][0]['body']['input'][1]['content']='{}'
        elif change=='model':bad['model']='another-model'
        else:bad['requests'].pop()
        bad['fingerprint']=V.digest({k:v for k,v in bad.items() if k!='fingerprint'})
        with pytest.raises(ValueError):V.validate(bad,m)


def test_fifty_plus_six_mocked_requests_record_only_ledger_calls_and_private_results(tmp_path,access):
    m,p=fixtures();seen=[]
    result=execute(m,p,tmp_path/'once',provider(seen))
    assert result['completed'] and result['attempted']==len(seen)==56
    assert result['hard_correct']==6 and result['hard_gate_passed']
    assert result['automatic_retries']==result['app_research_writes']==result['owner_labels_read']==0
    assert len(access)==112 and ledger.snapshot()['calls']==56
    predictions=json.loads((tmp_path/'once/owner-predictions.json').read_text())
    assert len(predictions['predictions'])==50 and predictions['fingerprint']==m['fingerprint']
    assert Decimal(result['paid_usd'])>0 and result['unresolved_maximum_usd']=='0'
    with pytest.raises(ValueError,match='already attempted'):execute(m,p,tmp_path/'different-folder',provider(seen))
    assert len(seen)==56


@pytest.mark.parametrize('failure',['timeout','invalid'])
def test_paid_failure_stops_once_and_another_output_path_cannot_retry(tmp_path,access,failure):
    m,p=fixtures();seen=[]
    result=execute(m,p,tmp_path/'first',provider(seen,failure=failure))
    assert result['attempted']==len(seen)==1 and not result['completed']
    if failure=='timeout':assert Decimal(result['unresolved_maximum_usd'])>0
    else:assert Decimal(result['paid_usd'])>0
    with pytest.raises(ValueError,match='already attempted'):execute(m,p,tmp_path/'new',provider(seen))
    assert len(seen)==1 and not (tmp_path/'new').exists()


def test_unresolved_continuation_never_dispatches_a_remaining_request(tmp_path,access):
    m,p=fixtures();seen=[]
    execute(m,p,tmp_path/'first',provider(seen,failure='timeout'))
    result=execute(m,p,tmp_path/'continued',provider(seen),remaining_after=tmp_path/'first')
    assert result['attempted']==0 and result['stopped']=='prior_attempt_unsettled_or_changed' and len(seen)==1


def test_explicit_continuation_rechecks_paid_answers_free_and_sends_only_unattempted_cases(tmp_path,access,monkeypatch):
    m,p=fixtures();seen=[];parse=V.parse;checked=[]
    def initial(call,packet):
        checked.append(True)
        if len(checked)==2:raise ValueError('Authored validator issue')
        return parse(call,packet)
    monkeypatch.setattr(V,'parse',initial)
    first=execute(m,p,tmp_path/'first',provider(seen));assert first['attempted']==len(seen)==2
    monkeypatch.setattr(V,'parse',parse)
    final=execute(m,p,tmp_path/'continued',provider(seen),remaining_after=tmp_path/'first')
    assert final['completed'] and final['attempted']==54 and len(seen)==56
    assert sum(r['reused'] for r in final['results'])==2
    assert len({V.digest(b) for b in seen})==56
    assert Decimal(final['paid_usd'])==sum(Decimal(r['charged_nano_usd'])/ledger.NANO for r in V.saved_calls(p['requests']))


@pytest.mark.parametrize('cap',[Decimal('NaN'),Decimal('Infinity'),Decimal('0'),Decimal('3')])
def test_invalid_or_unapproved_caps_never_dispatch(tmp_path,access,cap):
    m,p=fixtures()
    with pytest.raises(ValueError):V.run(p,m,tmp_path/'no',cap,approved_plan=p['fingerprint'],transport=lambda _:pytest.fail('dispatch'))
    with pytest.raises(ValueError):V.run(p,m,tmp_path/'no',Decimal('2'),approved_plan='another-plan',transport=lambda _:pytest.fail('dispatch'))
    assert ledger.snapshot()['calls']==0


def test_combined_cap_is_checked_before_any_dispatch(tmp_path,access):
    m,p=fixtures()
    result=V.run(p,m,tmp_path/'cap',Decimal('.000001'),approved_plan=p['fingerprint'],transport=lambda _:pytest.fail('dispatch'))
    assert result['attempted']==0 and result['stopped']=='combined_cap_before_dispatch'
    assert ledger.snapshot()['calls']==0


def test_all_source_access_is_preflighted_before_any_paid_call(tmp_path,monkeypatch):
    m,p=fixtures();checked=[]
    def revoked(conn,packet):
        checked.append(True)
        if len(checked)==8:raise ValueError('Authored withdrawal')
    monkeypatch.setattr(V,'verify_access',revoked)
    result=execute(m,p,tmp_path/'refused',lambda _:pytest.fail('dispatch'))
    assert result['attempted']==0 and result['stopped']=='source_access_or_context_changed'
    assert ledger.snapshot()['calls']==0


def test_same_frozen_request_is_reused_for_a_hard_case_without_another_charge(tmp_path,access):
    m,p=fixtures();hard=[deepcopy(c) for c in p['requests'] if c['scope']=='hard6']
    hard[0]['packet']=deepcopy(p['requests'][0]['packet'])
    hard[0]=hard_input(hard[0]['packet'],0)
    hard=[dict(c,source_id=c['packet']['sources'][0]['id']) for c in hard]
    p=V.make_plan(m,{c['id']:c['packet'] for c in p['requests'] if c['scope']=='owner50'},hard)
    seen=[];result=execute(m,p,tmp_path/'dedup',provider(seen))
    assert result['completed'] and len(seen)==55 and sum(r['reused'] for r in result['results'])==1


def test_campaign_lock_blocks_another_runner_before_its_first_request(tmp_path,access):
    m,p=fixtures();entered,release=Event(),Event();seen=[];normal=provider(seen)
    def pause(body):
        if not seen:entered.set();assert release.wait(10)
        return normal(body)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first=pool.submit(execute,m,p,tmp_path/'first',pause);assert entered.wait(10)
        with pytest.raises(ValueError,match='already running'):execute(m,p,tmp_path/'other',normal)
        release.set();assert first.result(timeout=30)['completed']
    assert len(seen)==56 and not (tmp_path/'other').exists()


def test_current_source_permissions_are_enforced_with_read_only_real_storage(owner):
    from test_market import prepare
    from thesis.research import sentiment
    iid=prepare(owner)
    with transaction(owner,consistent=True) as conn:packet=sentiment.prepare(conn,iid)
    with transaction(owner,consistent=True) as conn:V.verify_access(conn,packet)
    with transaction(admin=True) as conn:conn.execute("UPDATE sources SET entitlement='local-stockanalysis-targets' WHERE id='finnhub-news'")
    with transaction(owner,consistent=True) as conn:
        with pytest.raises(ValueError):V.verify_access(conn,packet)


@pytest.mark.parametrize('wrong,expected',[(2,True),(3,False)])
def test_hard_case_gate_keeps_its_exact_four_of_six_boundary(tmp_path,access,wrong,expected):
    m,p=fixtures();seen=[];normal=provider(seen)
    def changed(body):
        result=normal(body);payload=json.loads(body['input'][1]['content'])
        source=payload['sources'][0]
        if source['id'].startswith('hard-source-') and int(source['id'].split('-')[-1])<=wrong:
            value=json.loads(result['output'][0]['content'][0]['text'])
            value['items'][0].update(sentiment='neutral',basis='descriptive')
            result['output'][0]['content'][0]['text']=json.dumps(value)
        return result
    result=execute(m,p,tmp_path/'hard',changed)
    assert result['completed'] and result['hard_correct']==6-wrong and result['hard_gate_passed']==expected


def test_continuation_cap_includes_earlier_settled_charges(tmp_path,access,monkeypatch):
    m,p=fixtures();seen=[];parse=V.parse
    monkeypatch.setattr(V,'parse',lambda *_:(_ for _ in ()).throw(ValueError('Authored validator stop')))
    first=execute(m,p,tmp_path/'first',provider(seen));assert first['attempted']==1
    monkeypatch.setattr(V,'parse',parse)
    cap=Decimal(first['paid_usd'])+Decimal(ledger.estimate(p['requests'][1]['body']))/ledger.NANO/2
    result=V.run(p,m,tmp_path/'continued',cap,approved_plan=p['fingerprint'],transport=provider(seen),remaining_after=tmp_path/'first')
    assert result['attempted']==0 and len(seen)==1 and result['stopped']=='combined_cap_before_dispatch'


def test_quality_prediction_uses_the_repaired_label_without_modifying_raw_output():
    m,p=fixtures();case=p['requests'][0];raw=provider([])(case['body'])
    value=json.loads(raw['output'][0]['content'][0]['text'])
    value['items'][0].update(relevance='unrelated',sentiment='negative',basis='expressed_evaluation')
    raw['output'][0]['content'][0]['text']=json.dumps(value)
    before=deepcopy(raw)
    label,repaired=V.parse(dict(response_body=raw),case['packet'])
    assert label==dict(relevance='unrelated',sentiment='unclear') and repaired==1 and raw==before


def legacy_plan(monkeypatch):
    with monkeypatch.context() as old:
        old.setattr(V.T,'bounded_schema',lambda task,sources:V.T.strict_schema(V.T.MODELS[task]))
        return fixtures()


def test_revised_schema_requires_explicit_named_retry_and_reuses_valid_paid_answers(tmp_path,access,monkeypatch):
    m,old=legacy_plan(monkeypatch);seen=[];normal=provider(seen)
    def bad_parent(body):
        raw=normal(body)
        if len(seen)==3:
            value=json.loads(raw['output'][0]['content'][0]['text']);value['items'][0]['context_passages']=['p1']
            raw['output'][0]['content'][0]['text']=json.dumps(value)
        return raw
    with monkeypatch.context() as previous:
        previous.setattr(V.T,'bounded_schema',lambda task,sources:V.T.strict_schema(V.T.MODELS[task]))
        first=execute(m,old,tmp_path/'old',bad_parent)
    assert first['attempted']==3 and len(seen)==3
    bad=first['results'][-1];identity=bad['scope']+':'+bad['id']
    revised=V.revised_plan(old,m,[identity])
    with pytest.raises(ValueError,match='already attempted'):
        execute(m,revised,tmp_path/'missing-mode',normal)
    result=execute(m,revised,tmp_path/'revised',normal,revised_after=tmp_path/'old')
    assert result['completed'] and result['attempted']==54 and len(seen)==57
    assert sum(r['inherited_schema'] for r in result['results'])==2
    assert sum(bool(r['retested_call_id']) for r in result['results'])==1
    assert Decimal(result['paid_usd'])>Decimal(first['paid_usd'])
    funding=revised['requests']+old['requests']
    assert Decimal(result['paid_usd'])==sum(Decimal(c['charged_nano_usd'])/ledger.NANO for c in V.saved_calls(funding))


def test_schema_revision_without_retry_permission_stops_before_new_paid_work(tmp_path,access,monkeypatch):
    m,old=legacy_plan(monkeypatch);seen=[];normal=provider(seen)
    def invalid(body):
        raw=normal(body);value=json.loads(raw['output'][0]['content'][0]['text'])
        value['items'][0]['context_passages']=['p1'];raw['output'][0]['content'][0]['text']=json.dumps(value)
        return raw
    with monkeypatch.context() as previous:
        previous.setattr(V.T,'bounded_schema',lambda task,sources:V.T.strict_schema(V.T.MODELS[task]))
        execute(m,old,tmp_path/'old',invalid)
    revised=V.revised_plan(old,m,[])
    result=execute(m,revised,tmp_path/'no-retry',normal,revised_after=tmp_path/'old')
    assert result['attempted']==0 and result['stopped']=='prior_saved_answer_invalid_no_retry' and len(seen)==1


def test_schema_revision_cannot_change_inputs_expectations_or_weaken_constraints(monkeypatch):
    m,old=legacy_plan(monkeypatch)
    revised=V.revised_plan(old,m,[])
    changed=deepcopy(revised);changed['requests'][0]['body']['input'][1]['content']='{}'
    with pytest.raises(ValueError):V.equivalent(changed,old)
    assert not V.narrows({'maxItems':3},{'maxItems':2})
    assert not V.narrows({'enum':['a','b']},{'enum':['a']})
    assert V.narrows({'maxItems':0},{'maxItems':2})
    with pytest.raises(ValueError,match='Identical'):V.equivalent(revised,revised)


def test_revised_cap_retains_original_paid_failures_before_another_dispatch(tmp_path,access,monkeypatch):
    m,old=legacy_plan(monkeypatch);seen=[];normal=provider(seen)
    def bad(body):
        raw=normal(body);value=json.loads(raw['output'][0]['content'][0]['text'])
        value['items'][0]['context_passages']=['p1'];raw['output'][0]['content'][0]['text']=json.dumps(value)
        return raw
    with monkeypatch.context() as previous:
        previous.setattr(V.T,'bounded_schema',lambda task,sources:V.T.strict_schema(V.T.MODELS[task]))
        first=execute(m,old,tmp_path/'old',bad)
    case=old['requests'][0];retry=case['scope']+':'+case['id']
    revised=V.revised_plan(old,m,[retry])
    cap=Decimal(first['paid_usd'])+Decimal(ledger.estimate(revised['requests'][0]['body']))/ledger.NANO/2
    result=V.run(revised,m,tmp_path/'bounded',cap,approved_plan=revised['fingerprint'],transport=normal,revised_after=tmp_path/'old')
    assert result['attempted']==0 and result['stopped']=='combined_cap_before_dispatch' and len(seen)==1
    assert result['paid_usd']==first['paid_usd']


def test_revised_plan_cannot_pay_again_for_a_previously_valid_case(tmp_path,access,monkeypatch):
    m,old=legacy_plan(monkeypatch);seen=[];normal=provider(seen);parse=V.parse;checked=[]
    def stop_second(call,packet):
        checked.append(True)
        if len(checked)==2:raise ValueError('Authored validator stop')
        return parse(call,packet)
    with monkeypatch.context() as previous:
        previous.setattr(V.T,'bounded_schema',lambda task,sources:V.T.strict_schema(V.T.MODELS[task]))
        previous.setattr(V,'parse',stop_second)
        execute(m,old,tmp_path/'old',normal)
    valid=old['requests'][0];revised=V.revised_plan(old,m,[valid['scope']+':'+valid['id']])
    with pytest.raises(ValueError,match='explicitly named failed'):
        execute(m,revised,tmp_path/'invalid-retry',normal,revised_after=tmp_path/'old')
    assert len(seen)==2 and not (tmp_path/'invalid-retry').exists()


def threaded_packet():
    """An authored Reddit reply inside a saved four-message discussion."""
    p=controls();p['company']=dict(symbol='EXA',name='EXA Example')
    def message(key,role,text,minute):
        passages,_=source_passages('Reddit comment' if role=='comment' else 'Authored EXA topic',text)
        return dict(source_id='src-'+key,message_key=key,role=role,parent_key=None,author_key='author-'+key,
            passages=passages,published_at=f'2026-10-07T12:{minute:02}:00+00:00',
            available_at=f'2026-10-07T12:{minute:02}:00+00:00',url='https://example.invalid/'+key)
    topic=message('t3_abc','topic','EXA results are out. Holding for years.',0)
    earlier=message('t1_one','comment','EXA guidance looked strong to me.',1)
    sibling=message('t1_two','comment','Same view, holding too.',2)
    target=message('t1_tgt','comment','Same here.',3)
    source=dict(id='src-t1_tgt',label='item_1',channel='social',platform='reddit',social_kind='comment',
        thread_key='t3_abc',post_key='t1_tgt',title='Reddit comment',text='Same here.',passages=target['passages'],
        published_at=target['published_at'],available_at=target['available_at'],url=target['url'],
        content_hash=hashlib.sha256(b'tgt').hexdigest(),author_hash='author-t1_tgt')
    p['sources']=[source];p['reddit_thread_context']=[dict(thread_key='t3_abc',messages=[topic,earlier,sibling,target])]
    return p


def supplied_messages(packet):
    payload=json.loads(V.T.request_for('tone',packet)['input'][1]['content'])
    return [m['message_key'] for m in payload['reddit_threads'][0]['messages']]


def test_thread_context_sends_saved_discussion_but_keeps_review_page_evidence():
    base=threaded_packet()
    review=V.selected(base,'src-t1_tgt')
    thread=V.selected(base,'src-t1_tgt',thread_extras=True)
    assert supplied_messages(review)==['t3_abc','t1_tgt']
    assert supplied_messages(thread)==['t3_abc','t1_one','t1_two','t1_tgt']
    # The blind review projection is the same in both modes, so owner labels stay comparable.
    assert Q.case_evidence(review,review['sources'][0])==Q.case_evidence(thread,thread['sources'][0])
    # Permission checks cover every message actually sent.
    keys=lambda p:[m['message_key'] for m in V.consumed(p)['reddit_thread_context'][0]['messages']]
    assert keys(review)==['t3_abc','t1_tgt'] and keys(thread)==['t3_abc','t1_one','t1_two','t1_tgt']


def test_thread_plan_is_a_separate_frozen_plan_and_review_plans_keep_their_identity():
    m,p=fixtures()
    assert 'thread_context' not in p
    variant=V.thread_plan(p,m)
    assert variant['thread_context']=='thread' and variant['fingerprint']!=p['fingerprint']
    assert V.validate(variant,m) and V.estimate(variant,m)['requests']==56
    assert all(c['packet']['thread_extras'] is (c['scope']=='owner50') for c in variant['requests'])
    tampered=deepcopy(variant);tampered['thread_context']='review'
    with pytest.raises(ValueError):V.validate(tampered,m)
    with pytest.raises(ValueError):V.make_plan(m,{},[],thread_context='everything')
