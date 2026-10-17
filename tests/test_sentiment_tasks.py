"""Prepared task contracts: invented outputs, no dispatch or network."""
from copy import deepcopy
import json
import pytest
from thesis.research import sentiment_tasks as T, sentiment as S
from thesis.providers import ledger
from experiments.sentiment_batching.controls import packet as controls


def packet():
    p=controls();p['sources']=p['sources'][:4];return p


def call(value):
    return dict(response_body=dict(status='completed',output=[dict(type='message',
        content=[dict(type='output_text',text=json.dumps(value))])]))


def tones(p):
    return [dict(id=s['label'],relevance='relevant',sentiment='neutral',statement='opinion',
                 topic='general',passages=['p1'],previous_passages=[],context_passages=[],
                 price_claims=[],basis='descriptive') for s in p['sources']]


def events(p):
    return [dict(id=s['label'],reporting=dict(kind='reported_event',impact='not_stated',passages=['p1']),
                 importance=dict(level='high',category='deal',form='event',passages=['p1']))
            for s in p['sources'] if s['channel']=='news']


def test_instructions_and_shared_schemas_are_small_and_requests_keep_ledger_bounds(monkeypatch):
    monkeypatch.setattr(ledger,'execute',lambda *a,**k:pytest.fail('Contract dispatched a paid call'))
    p=packet()
    for task in ('tone','event'):
        body=T.request_for(task,p)
        assert len(body['input'][0]['content'])<=6000
        assert len(ledger.canonical(body['text']['format']['schema']))<6000
        assert ledger.request_profile(body).max_output==12000
        assert len(ledger.canonical(body).encode())<=48000
    assert len(T.DUPLICATE_INSTRUCTION)<=6000
    event_input=json.loads(T.request_for('event',p)['input'][1]['content'])
    assert all(s['channel']=='news' for s in event_input['sources'])
    with pytest.raises(ValueError,match='candidates'):T.request_for('duplicate',p)
    with pytest.raises(ValueError):T.request_for('invented',p)


def test_tone_completeness_and_citations_checked_before_following_tasks():
    p=packet();items=tones(p)
    assert len(T.tone_labels(call(dict(items=items)),p))==4
    with pytest.raises(ValueError,match='exactly one'):
        T.tone_labels(call(dict(items=items[:-1])),p)
    items[0]['passages']=['invented']
    with pytest.raises(ValueError,match='evidence'):
        T.tone_labels(call(dict(items=items)),p)


@pytest.mark.parametrize('category,form,title',[
    ('analyst_opinion','event','Ordinary headline'),
    ('market_commentary','event','Ordinary headline'),
    ('deal','opinion','Ordinary headline'),
    ('deal','comparison','Ordinary headline'),
    ('deal','price_recap','Ordinary headline'),
    ('deal','event','Lumen vs rival: Which stock to buy?'),
    ('deal','event','Why Lumen stock fell today'),
])
def test_opinions_comparisons_and_price_recaps_are_low_even_if_model_says_high(category,form,title):
    p=packet();p['sources'][0]['title']=title;items=events(p)
    items[0]['importance'].update(category=category,form=form)
    value=T.event_labels(call(dict(items=items)),p,tones(p))['item_1']['importance']
    assert value['level']=='low' and value['proposed_level']=='high' and value['low_by_rule']


def test_importance_requires_same_source_evidence_and_complete_news_labels():
    p=packet();items=events(p)
    value=T.event_labels(call(dict(items=items)),p,tones(p))['item_1']['importance']
    assert value['level']=='high' and value['citations'][0]['source_id']==p['sources'][0]['id']
    for passages in ([],['invented'],['p1','p1']):
        bad=deepcopy(items);bad[0]['importance']['passages']=passages
        with pytest.raises(ValueError):T.event_labels(call(dict(items=bad)),p,tones(p))
    with pytest.raises(ValueError,match='exactly one'):
        T.event_labels(call(dict(items=items*2)),p,tones(p))


def test_duplicate_candidates_need_specific_headline_overlap_and_earlier_reference():
    p=packet();p['sources']=[p['sources'][0],p['sources'][2]]
    p['sources'][0]['title']='Lumen signs Cedar supply contract for factory chips'
    p['sources'][1]['title']='Lumen signs Cedar supply contract for new factory chips'
    pairs=T.candidates(p,tones(p))
    assert pairs==[dict(item_id='item_3',reference_id='item_1')]
    body=T.request_for('duplicate',p,pairs=pairs)
    assert len(body['input'][0]['content'])<6000 and ledger.estimate(body)>0
    assert T.duplicate_labels(call(dict(coverage_links=[])),p,[],pairs)==[]
    bad=dict(item_id='item_1',reference_id='item_3',relation='repeats',explanation='Invented later comparison',
             item_passages=['p1'],reference_passages=['p1'])
    with pytest.raises(ValueError,match='outside'):
        T.duplicate_labels(call(dict(coverage_links=[bad])),p,[],pairs)
    values=tones(p);values[1]['relevance']='unrelated'
    assert T.candidates(p,values)==[]
    p['sources'][1]['title']='Lumen stock today market share company'
    assert T.candidates(p,tones(p))==[]


def test_parentless_task_schema_forbids_parent_claims_and_binds_supplied_labels():
    p=packet();p['sources']=[p['sources'][0]]
    body=T.request_for('tone',p);properties=body['text']['format']['schema']['$defs']['ToneItem']['properties']
    assert properties['context_passages']['maxItems']==0
    assert properties['id']['enum']==[p['sources'][0]['label']]
    assert properties['previous_passages']['maxItems']==0 and properties['price_claims']['maxItems']==0
    assert set(properties['passages']['items']['enum'])=={x['id'] for x in p['sources'][0]['passages']}
    assert len(T.INSTRUCTIONS['tone'])<=6000 and len(ledger.canonical(body).encode())<=48000


def test_supplied_parents_keep_their_actual_context_ids_and_mixed_runtime_guards():
    p=controls();p['sources']=[p['sources'][5]]
    body=T.request_for('tone',p);properties=body['text']['format']['schema']['$defs']['ToneItem']['properties']
    assert properties['context_passages']['maxItems']==2
    assert properties['context_passages']['items']['enum']==['p1']
    raw=tones(p);raw[0]['context_passages']=['invented-parent']
    with pytest.raises(ValueError):T.tone_labels(call(dict(items=raw)),p)


def test_schema_revision_changes_reading_identity_without_changing_source_text(monkeypatch):
    from thesis.research import sentiment_task_runner as R
    p=packet();new=R.identity(p)
    monkeypatch.setattr(T,'SCHEMA_POLICY','authored-previous-schema')
    assert R.identity(p)!=new
