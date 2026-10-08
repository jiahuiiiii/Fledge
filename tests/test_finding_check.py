"""Evidence-review contract only; no real model calls or semantic claims."""
from copy import deepcopy
from uuid import uuid4
import json
import pytest
from thesis.research import finding_check as C, sentiment as S
from thesis.providers import ledger
from thesis.db import transaction
from test_sentiment_context import with_context
from test_sentiment import provider


def case(owner):
    iid, _, _, _ = with_context(owner)
    with transaction(owner) as c:packet=S.prepare(c,iid)
    candidate=S.render(dict(response_body=provider()(S.request_for(packet))),packet)
    return packet,candidate,C.sentiment_units(candidate)


def response(units):
    return dict(id=str(uuid4()),response_body=dict(status='completed',output=[dict(type='message',content=[dict(type='output_text',text=json.dumps(dict(decisions=[dict(key=u['key'],reason='Authored boundary test only.',verdict='supported') for u in units])))])]))


def test_original_context_is_separate_from_selected_evidence_and_has_no_private_metadata(owner):
    packet,candidate,units=case(owner)
    before=deepcopy((packet,candidate,units))
    wire=json.loads(C.request_for(packet,units)['input'][1]['content'])
    child=next(s for s in wire['source_context'] if s.get('conversation'))
    unit=next(u for u in wire['findings'] if u['contexts'])
    assert child['scope']=='hackernews'
    assert set(unit['contexts'][0])=={'source_id','parent_type','citations'}
    assert set(child['conversation'])=={'parent_key','parent_type','published_at','passages'}
    assert 'author_hash' not in json.dumps(wire) and 'result_id' not in json.dumps(wire)
    assert len(wire['source_context'])==len(packet['sources'])+len(packet['comparison_sources'])
    assert (packet,candidate,units)==before
    assert ledger.estimate(C.request_for(packet,units))>0


@pytest.mark.parametrize('fault',['quote','foreign','parent_quote','parent_detached','parent_type','duplicate_unit','empty'])
def test_invalid_evidence_is_rejected_before_dispatch(owner,fault):
    packet,_,units=case(owner)
    unit=next(u for u in units if u['contexts'])
    if fault=='quote':unit['citations'][0]['quote']='Invented quote.'
    elif fault=='foreign':unit['citations'][0]['source_id']=str(uuid4())
    elif fault=='parent_quote':unit['contexts'][0]['citations'][0]['quote']='Invented parent.'
    elif fault=='parent_detached':unit['contexts'][0]['source_id']=str(uuid4())
    elif fault=='parent_type':unit['contexts'][0]['parent_type']='wrong-type'
    elif fault=='duplicate_unit':units.append(deepcopy(units[0]))
    elif fault=='empty':units=[]
    with pytest.raises(ValueError):C.request_for(packet,units)


@pytest.mark.parametrize('fault',['missing','duplicate','foreign','incomplete','blank','extra'])
def test_complete_verdict_coverage_and_closed_output_contract(owner,fault):
    _,_,units=case(owner);call=response(units)
    raw=call['response_body'];data=json.loads(raw['output'][0]['content'][0]['text'])
    if fault=='missing':data['decisions'].pop()
    elif fault=='duplicate':data['decisions'].append(deepcopy(data['decisions'][0]))
    elif fault=='foreign':data['decisions'][0]['key']='other'
    elif fault=='incomplete':raw['status']='incomplete'
    elif fault=='blank':data['decisions'][0]['reason']=' '
    elif fault=='extra':data['decisions'][0]['replacement']='Do not rewrite prose.'
    raw['output'][0]['content'][0]['text']=json.dumps(data)
    with pytest.raises(ValueError):C.read(call,units)


def test_review_does_not_rewrite_and_identity_pins_owner_content_and_policy(owner,monkeypatch):
    packet,candidate,units=case(owner);before=deepcopy((packet,candidate,units))
    result=C.read(response(units),units)
    assert len(result['decisions'])==len(units)
    assert (packet,candidate,units)==before
    base=C.identity(packet,units,owner=owner)
    assert C.identity(packet,units,owner=str(uuid4()))!=base
    changed=deepcopy(units);changed[0]['text']='A different material claim.'
    assert C.identity(packet,changed,owner=owner)!=base
    monkeypatch.setattr(C,'POLICY','test-policy')
    assert C.identity(packet,units,owner=owner)!=base


def test_higher_effort_preserves_evidence_and_has_distinct_priced_identity(owner):
    packet,_,units=case(owner)
    medium=C.request_for(packet,units);high=C.request_for(packet,units,effort='high')
    assert high['max_output_tokens']==9000 and medium['max_output_tokens']==6000
    assert high['reasoning']=={'effort':'high'}
    assert high | {k:medium[k] for k in ('max_output_tokens','reasoning')} == medium
    assert ledger.request_profile(high).version==ledger.FINDING_CHECK_PRICE_VERSION
    assert ledger.estimate(high)>ledger.estimate(medium)
    assert C.identity(packet,units,owner=owner,effort='high')!=C.identity(packet,units,owner=owner)
    with pytest.raises(ValueError):C.request_for(packet,units,effort='xhigh')
