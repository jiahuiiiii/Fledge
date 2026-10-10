"""Title/parent namespace recovery preserves evidence and paid request identity."""
from copy import deepcopy
import json
import pytest
from thesis.db import transaction, one
from thesis.providers import ledger
from thesis.research import discussion_themes as D, discussion_theme_check as C, theme_batching as B
from test_discussion_themes import setup, packet_for, response, check_response
from test_theme_context import context_case


def title_alias(result, wire):
    for theme in result['themes']:
        if theme['scope'] != 'news':
            continue
        for claim in theme['reading']['claims']:
            claim['context_passages'] = ['p0']


def test_title_alias_keeps_exact_claims_and_evidence_without_a_parent(owner):
    iid, aid = setup(owner)
    packet = packet_for(iid, aid)
    body = D.request_for(packet)
    raw = response(body, title_alias)
    original = deepcopy(raw)
    candidate = D.render({'response_body': raw}, packet)
    assert raw == original
    claim = next(t for t in candidate['themes'] if t['scope'] == 'news')['reading']['claims'][0]
    source = next(s for s in packet['sources'] if s['id'] == claim['source_id'])
    assert 'conversation' not in claim
    assert claim['citations'][0] == dict(source_id=source['id'], passage_id='p0', quote=source['title'], role='source_title')
    parsed = json.loads(raw['output'][0]['content'][0]['text'])
    assert claim['text'] == parsed['themes'][0]['reading']['claims'][0]['text']
    assert len(candidate['citation_normalization']['title_references']) == 1
    checking = C.request_for(packet, candidate, compact=True)
    checked = C.apply({'id': 'mock-check', 'response_body': check_response(checking)}, candidate)
    assert checked['citation_normalization'] == candidate['citation_normalization']


@pytest.mark.parametrize('refs', [['p1'], ['p0','p1'], ['p0','p0'], ['p999']])
def test_other_absent_parent_references_are_never_repaired(owner, refs):
    iid, aid = setup(owner)
    packet = packet_for(iid, aid)
    def corrupt(result, wire):
        result['themes'][0]['reading']['claims'][0]['context_passages'] = refs
    with pytest.raises(ValueError, match='No conversation context'):
        D.render({'response_body':response(D.request_for(packet), corrupt)}, packet)


def test_generic_social_title_is_never_treated_as_parent(owner):
    iid, aid = setup(owner)
    packet = packet_for(iid, aid)
    def corrupt(result, wire):
        next(t for t in result['themes'] if t['scope']=='hackernews')['reading']['claims'][0]['context_passages']=['p0']
    with pytest.raises(ValueError, match='No conversation context'):
        D.render({'response_body':response(D.request_for(packet), corrupt)}, packet)


def test_absent_title_cannot_supply_missing_parent_evidence(owner):
    iid, aid = setup(owner)
    packet = packet_for(iid, aid)
    for source in packet['sources']:
        if source['channel'] == 'news':
            source['title'] = ''
    with pytest.raises(ValueError, match='No conversation context'):
        D.render({'response_body':response(D.request_for(packet), title_alias)}, packet)


def test_schema_binds_each_source_to_its_own_parent_passage_set(owner):
    iid, _, _, _, reading = context_case(owner)
    packet = packet_for(iid, reading['id'])
    schema = D.request_for(packet)['text']['format']['schema']['$defs']['Claim']
    variants = schema.get('anyOf', [schema])
    for source in packet['sources']:
        matches = [v for v in variants if source['label'] in v['properties']['item_id']['enum']]
        assert len(matches) == 1
        definition = matches[0]
        context = definition['properties']['context_passages']
        assert 'context_passages' in definition['required']
        if source.get('conversation'):
            assert context['minItems'] == 1 and context['maxItems'] == 2
            assert context['items']['enum'] == [p['id'] for p in source['conversation']['passages']]
        else:
            assert context['minItems'] == context['maxItems'] == 0


def test_paid_legacy_batch_reused_without_redrafting_then_all_steps_checked(owner, monkeypatch):
    iid, aid = setup(owner)
    packet = packet_for(iid, aid)
    monkeypatch.setattr(B, 'MAX_SOURCES', 1)
    old_parts = B.plan(dict(packet, theme_legacy_request=True))
    first = old_parts[0]
    paid = ledger.execute(D.identity(first), D.LEGACY_PROMPT, D.request_for(first), transport=lambda b: response(b, title_alias))
    paid_original = deepcopy(paid)
    before = ledger.snapshot()
    parts = B.available_plan(packet)
    assert D.identity(parts[0]) == D.identity(first)
    assert parts[0]['sources'] == first['sources']
    assert all(not p.get('theme_legacy_request') for p in parts[1:])
    plan = B.preflight(parts)
    assert plan['saved_drafts'] == plan['normalized_title_references'] == 1
    assert ledger.snapshot() == before
    dispatched=[]
    def provider(body):
        dispatched.append(deepcopy(body))
        assert body != paid['request_body'], 'Already paid draft must not be regenerated'
        return response(body)
    result = D.generate(iid, aid, transport=provider)
    assert len(dispatched) == 2 * len(parts) - 1
    assert dispatched[0]['text']['format']['name'] == 'discussion_theme_evidence_check'
    assert result['result']['batching']['parts'][0]['synthesis_call_id'] == str(paid['id'])
    assert result['result']['batching']['parts'][0]['citation_normalization']['title_references']
    with transaction() as c:
        assert one(c, 'SELECT * FROM model_calls WHERE id=%s', (paid['id'],)) == paid_original
    assert D.generate(iid, aid, transport=lambda _: pytest.fail('No repeats'))['id'] == result['id']


def test_legacy_invalid_parent_stops_entire_plan_before_new_dispatch(owner, monkeypatch):
    iid, aid = setup(owner)
    monkeypatch.setattr(B, 'MAX_SOURCES', 1)
    parts = B.plan(dict(packet_for(iid, aid), theme_legacy_request=True))
    def wrong(result, wire):
        result['themes'][0]['reading']['claims'][0]['context_passages']=['p999']
    ledger.execute(D.identity(parts[0]), D.LEGACY_PROMPT, D.request_for(parts[0]), transport=lambda b: response(b, wrong))
    before=ledger.snapshot()
    with pytest.raises(ValueError, match='No conversation context'):
        D.generate(iid, aid, transport=lambda _: pytest.fail('No paid work'))
    assert ledger.snapshot() == before
    assert D.history(iid, aid)['current'] is None


def test_current_schema_changes_never_bypass_unresolved_legacy_charge(owner, monkeypatch):
    iid, aid = setup(owner)
    monkeypatch.setattr(B, 'MAX_SOURCES', 1)
    first=B.plan(dict(packet_for(iid, aid), theme_legacy_request=True))[0]
    def failed(_):
        raise TimeoutError('authored unresolved provider call')
    with pytest.raises(Exception):
        ledger.execute(D.identity(first), D.LEGACY_PROMPT, D.request_for(first), transport=failed)
    before=ledger.snapshot()
    with pytest.raises(ledger.BudgetBlocked, match='charge review'):
        B.available_plan(packet_for(iid, aid))
    assert ledger.snapshot() == before
