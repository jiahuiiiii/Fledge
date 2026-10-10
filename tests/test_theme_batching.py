"""Complete discussion coverage, request-size bounds and no partial publication."""
from copy import deepcopy
import json
from uuid import uuid4
import pytest
from thesis.db import transaction, one
from thesis.providers import ledger
from thesis.research import discussion_themes as D, discussion_theme_check as C, theme_batching as B
from test_discussion_themes import setup, packet_for, response, check_response


def test_large_pool_partitions_whole_sources_and_bounds_both_steps(owner):
    iid, aid = setup(owner)
    packet = packet_for(iid, aid)
    base = packet['sources'][0]
    packet['sources'] = [dict(deepcopy(base), id=str(uuid4()), label=f'item_{i}',
                              text=(f'Microsoft source {i} reports a distinct software development. ' * 35)) for i in range(65)]
    original = deepcopy(packet)
    assert B.wire_size(D.request_for(packet)) > ledger.MAX_REQUEST_BYTES
    parts = B.plan(packet)
    assert len(parts) > 1
    assert [s for p in parts for s in p['sources']] == packet['sources']
    for part in parts:
        draft, envelope = B.bounds(part)
        assert B.wire_size(draft) <= B.MAX_BYTES
        assert B.wire_size(envelope) <= ledger.MAX_REQUEST_BYTES
        ledger.estimate(draft); ledger.estimate(envelope)
        candidate = D.render({'response_body': response(draft)}, part)
        check = C.request_for(part, candidate, compact=True)
        assert B.wire_size(check) <= B.wire_size(envelope)
        wire = json.loads(check['input'][1]['content'])
        assert len(wire['source_context']) == len(part['sources'])
        claim = wire['themes'][0]['reading']['claims'][0]
        assert 'text' not in wire['themes'][0]['reading']
        assert all('quote' not in citation for citation in claim['citations'])
        source = next(s for s in wire['source_context'] if s['id'] == claim['source_id'])
        assert set(c['passage_id'] for c in claim['citations']) <= {p['id'] for p in source['passages']}
    assert packet == original


def test_one_oversized_whole_source_stops_before_any_paid_call(owner):
    iid, aid = setup(owner)
    packet = packet_for(iid, aid)
    packet['sources'][0]['text'] = 'A' * 70000 + '.'
    before = ledger.snapshot()
    with pytest.raises(ValueError, match='One complete source'):
        B.plan(packet)
    assert ledger.snapshot() == before


def test_full_plan_budget_check_before_first_dispatch(owner, monkeypatch):
    iid, aid = setup(owner)
    before = ledger.snapshot()
    monkeypatch.setattr(B, 'MAX_SOURCES', 1)
    monkeypatch.setattr(ledger, 'snapshot', lambda: dict(before, remaining_usd='0'))
    with pytest.raises(ledger.BudgetBlocked, match='complete discussion summary'):
        D.generate(iid, aid, transport=lambda _: pytest.fail('preflight must not dispatch'))
    with transaction() as conn:
        assert one(conn, 'SELECT count(*) n FROM model_calls')['n'] == before['calls']
    assert D.history(iid, aid)['generation']['blocked_reason']


def test_batches_publish_once_after_all_checks_with_exact_sources_and_cache(owner, monkeypatch):
    iid, aid = setup(owner)
    packet = packet_for(iid, aid)
    monkeypatch.setattr(B, 'MAX_SOURCES', 1)
    before = ledger.snapshot()['calls']
    result = D.generate(iid, aid, transport=response)
    batching = result['result']['batching']
    assert batching['completed'] == len(packet['sources'])
    assert batching['sources'] == len(packet['sources'])
    assert {i for p in batching['parts'] for i in p['source_ids']} == {s['id'] for s in packet['sources']}
    assert ledger.snapshot()['calls'] == before + 2 * len(packet['sources'])
    assert {t['scope'] for t in result['result']['themes']} == {'news','reddit','hackernews'}
    assert {t['batch'] for t in result['result']['themes']} == set(range(1, 1 + len(packet['sources'])))
    assert len(result['result']['evidence_check']['call_ids']) == len(packet['sources'])
    assert D.generate(iid, aid, transport=lambda _: pytest.fail('cached'))['id'] == result['id']
    assert D.history(iid, aid)['generation']['cached']
    assert 'within each batch' in D.download(iid, result['id'])[1]


def test_failed_later_check_never_publishes_or_retries_completed_or_failed_calls(owner, monkeypatch):
    iid, aid = setup(owner)
    monkeypatch.setattr(B, 'MAX_SOURCES', 1)
    calls = []
    def provider(body):
        calls.append(body)
        out = response(body)
        if len(calls) == 4:
            out['status'] = 'incomplete'
        return out
    with pytest.raises(ValueError, match='batch 2.*No combined summary'):
        D.generate(iid, aid, transport=provider)
    assert len(calls) == 4
    assert D.history(iid, aid)['current'] is None
    before = ledger.snapshot()
    with pytest.raises(ValueError, match='incomplete'):
        D.generate(iid, aid, transport=lambda _: pytest.fail('never retry'))
    assert ledger.snapshot() == before


def test_withdrawal_between_batches_prevents_next_paid_request(owner, monkeypatch):
    iid, aid = setup(owner)
    monkeypatch.setattr(B, 'MAX_SOURCES', 1)
    calls = []
    def provider(body):
        calls.append(body)
        if len(calls) == 2:
            with transaction(admin=True) as conn:
                conn.execute('UPDATE social_feeds SET enabled=false')
        return response(body)
    with pytest.raises(ValueError, match='Source access changed'):
        D.generate(iid, aid, transport=provider)
    assert len(calls) == 2
    assert D.history(iid, aid)['current'] is None


def test_checker_accepts_eight_decisions_for_four_scopes_and_retains_quote_identity(owner):
    iid, aid = setup(owner)
    packet = packet_for(iid, aid)
    candidate = D.render({'response_body': response(D.request_for(packet))}, packet)
    candidate['themes'] = [deepcopy(candidate['themes'][0]) for _ in range(8)]
    body = C.request_for(packet, candidate)
    reviewed = C.apply({'id':'mock', 'response_body':check_response(body)}, candidate)
    assert len(reviewed['themes']) == 8
    corrupt = deepcopy(candidate)
    corrupt['themes'][0]['reading']['claims'][0]['citations'][0]['quote'] = 'Unselected wording'
    with pytest.raises(ValueError, match='exact own-source'):
        C.request_for(packet, corrupt, compact=True)


def test_concurrent_same_company_summary_cannot_dispatch(owner):
    iid, aid = setup(owner)
    before = ledger.snapshot()
    with B.reading_lock(iid):
        with pytest.raises(ValueError, match='already running'):
            D.generate(iid, aid, transport=lambda _: pytest.fail('locked'))
    assert ledger.snapshot() == before
