"""Typed risk suggestions use the existing explicit review and numeric evaluator."""
from copy import deepcopy
from uuid import uuid4
import pytest
from psycopg.types.json import Jsonb
from thesis import service
from thesis.db import transaction, one
from thesis.models import SaveIdea
from thesis.providers import ledger
from thesis.research import proposals as P
from test_integration import payload, drain
from test_numerical_roles import risk_payload
from test_proposals import provider, request, complete


def suggestion(role='risk', threshold='15', operation='add', target=None):
    return dict(kind='numeric', operation=operation, target_condition_id=target,
        definition=None if operation=='remove' else dict(role=role, metric='revenue_growth',
            operator='<=', threshold=threshold, period_type='quarter', max_report_age_days=None))


def generate(owner, saved, item):
    return P.generate(owner,request(owner,saved),transport=provider(lambda _: [item]))['proposals'][0]


def test_risk_add_requires_user_threshold_then_exact_approval_and_crossing(owner):
    saved=service.save_idea(owner,payload(status='draft',conditions=False))
    before=deepcopy(service.state(owner)['versions'])
    p=generate(owner,saved,suggestion(threshold=None))
    assert service.state(owner)['versions']==before and p['status']=='pending'
    assert p['candidate']['conditions'][0]['role']=='risk'
    with pytest.raises(ValueError):complete(p)
    candidate=deepcopy(p['candidate']);candidate['conditions'][0]['threshold']='15';candidate['status']='monitoring'
    definition=SaveIdea(**candidate)
    approved=P.decide(owner,p['id'],definition=definition);drain(owner)
    state=service.state(owner);assert state['versions'][0]['conditions'][0]['role']=='risk'
    assert state['versions'][0]['evaluations'][0]['results'][0]['outcome']=='met'
    assert P.decide(owner,p['id'],definition=definition)==approved
    for stage in (0,1):service.advance(owner,stage);drain(owner)
    after=service.state(owner)
    result=after['versions'][0]['evaluations'][0]['results'][0]
    assert result['role']=='risk' and result['outcome']=='not_met'
    assert after['versions'][1]==before[0]
    with pytest.raises(service.Conflict):
        P.decide(owner,p['id'],definition=definition.model_copy(update={'conditions':[definition.conditions[0].model_copy(update={'role':'required'})]}))


@pytest.mark.parametrize('operation',['update','remove'])
def test_existing_risk_changes_are_pending_and_preserve_original_revision(owner,operation):
    saved=service.save_idea(owner,risk_payload(status='draft'))
    before=deepcopy(service.state(owner)['versions'][0]);target=str(before['conditions'][0]['condition_id'])
    p=generate(owner,saved,suggestion(threshold='12',operation=operation,target=target))
    assert service.state(owner)['versions'][0]==before
    if operation=='update':
        assert p['candidate']['conditions'][0]['role']=='risk'
        assert p['candidate']['conditions'][0]['condition_id']==target
    P.decide(owner,p['id'],definition=complete(p,status='draft'))
    versions=service.state(owner)['versions'];assert versions[1]==before
    assert len(versions[0]['conditions'])==(1 if operation=='update' else 0)
    if operation=='update':assert versions[0]['conditions'][0]['role']=='risk'


def test_explicit_purpose_change_needs_review_and_changes_no_original_values(owner):
    saved=service.save_idea(owner,risk_payload(status='draft'))
    before=deepcopy(service.state(owner)['versions'][0]);original=before['conditions'][0]
    p=generate(owner,saved,suggestion(role='required',threshold=str(original['threshold']),operation='update',target=str(original['condition_id'])))
    assert p['base']['conditions'][0]['role']=='risk'
    assert p['proposed']['definition']['role']=='required'
    assert service.state(owner)['versions'][0]==before
    P.decide(owner,p['id'],definition=complete(p,status='draft'))
    after=service.state(owner)['versions'];assert after[1]==before
    assert after[0]['conditions'][0]['role']=='required'
    assert after[0]['conditions'][0]['operator']==original['operator']
    assert after[0]['conditions'][0]['threshold']==original['threshold']


@pytest.mark.parametrize('role',[None,'safe','bullish'])
def test_invalid_role_cannot_publish_any_pending_suggestion(owner,role):
    saved=service.save_idea(owner,payload(status='draft',conditions=False))
    before=service.state(owner)['versions']
    with pytest.raises(ValueError):generate(owner,saved,suggestion(role=role))
    state=service.state(owner)
    assert state['proposals']==[] and state['versions']==before


def test_legacy_pending_required_suggestion_remains_readable_and_approvable(owner):
    saved=service.save_idea(owner,payload(status='draft',conditions=False))
    p=generate(owner,saved,suggestion(role='required'))
    # Recreate a historical required-only record without mutating the original.
    with transaction(owner) as c:
        row=one(c,'SELECT * FROM idea_proposals WHERE id=%s',(p['id'],))
        old=deepcopy(row['proposed']);old['definition'].pop('role');pid=uuid4()
        c.execute('''INSERT INTO idea_proposals
            SELECT %s,owner_id,instrument_id,base_version_id,snapshot_id,call_id,
            request_key||'-legacy',ordinal,kind,operation,target_condition_id,%s,rationale,citations,packet,created_at
            FROM idea_proposals WHERE id=%s''',(pid,Jsonb(old),p['id']))
        legacy=P.present(c,owner,one(c,'SELECT * FROM idea_proposals WHERE id=%s',(pid,)))
    definition=complete(legacy,status='draft')
    assert definition.conditions[0].role=='required'
    P.decide(owner,pid,definition=definition)
    assert service.state(owner)['versions'][0]['conditions'][0]['role']=='required'


def test_generation_identity_separates_new_role_schema_from_old_method(owner):
    saved=service.save_idea(owner,risk_payload(status='draft'))
    with transaction(owner) as c:packet=P.prepare(c,owner,request(owner,saved))
    body=P.request_for(packet)
    definition=body['text']['format']['schema']['$defs']['NumericDefinition']
    assert 'role' in definition['required']
    assert definition['properties']['role']['enum']==['required','risk']
    assert P.PROMPT=='thesis-condition-proposals-4'
    assert ledger.estimate(body)>0
