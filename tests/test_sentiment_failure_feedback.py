"""Actual output-limit shape, durable progress and read-only legacy diagnosis."""
from copy import deepcopy
from unittest.mock import patch
import json
import pytest
from thesis.db import transaction, one
from thesis.providers import ledger
from thesis.research import sentiment as S, sentiment_batching as B, loading
from test_market import prepare
from test_sentiment import provider
from test_sentiment_batching import packet
from test_model_budget import clean_model_ledger


def cut_short(body):
    result = provider('neutral')(body)
    result.update(status='incomplete', incomplete_details={'reason': 'max_output_tokens'},
                  output=[{'type': 'reasoning'}, {'type': 'message', 'content': [
                      {'type': 'output_text', 'text': '{"items":[{"id":"item_9"'}]}])
    limit = body['max_output_tokens']
    result['usage'].update(output_tokens=limit, output_tokens_details={'reasoning_tokens': limit-914})
    return result


def test_limit_reports_exact_cause_charge_and_saved_work_without_retry(owner):
    p = packet(); seen = []; progress = []
    def transport(body):
        seen.append(body)
        return cut_short(body) if len(seen) == 2 else provider('neutral')(body)
    with patch.object(B, 'check_access'):
        with pytest.raises(ValueError, match='12,000-token response limit') as error:
            B.run(p, transport=transport, progress=progress.append)
        assert len(seen) == 2 and progress[-1]['completed'] == 1
        assert progress[-1]['failure']['code'] == 'output_limit'
        assert '1 completed batch is saved' in str(error.value)
        assert 'US$0.180' in str(error.value) and 'no automatic retry' in str(error.value)
        assert 'No combined reading was published' in str(error.value)
        assert progress[-1]['message'] == str(error.value)
        before = ledger.snapshot()
        with pytest.raises(ValueError, match='saved batch.*12,000-token response limit'):
            B.run(p, transport=lambda _: pytest.fail('automatic retry'))
        assert ledger.snapshot() == before


def test_later_batches_are_not_called_after_limit(owner):
    p = packet(); p['sources'] = p['sources'][:3]
    progress = []
    with patch.object(B, 'plan', return_value=[B.part_for(p, [s]) for s in p['sources']]), patch.object(B, 'check_access'):
        with pytest.raises(ValueError, match='2 later batches were not sent in this run'):
            B.run(p, transport=cut_short, progress=progress.append)
    assert ledger.snapshot()['calls'] == 1 and progress[-1]['completed'] == 0


def test_invalid_format_does_not_expose_model_text_or_claim_a_limit():
    call = {'response_body': {'status': 'completed', 'output': [
        {'type': 'message', 'content': [{'type': 'output_text', 'text': 'PRIVATE UNTRUSTED CONTENT'}]}]}}
    with pytest.raises(ValueError) as error:
        B.raw(call)
    details = B.failure_details(call, error.value)
    assert details['code'] == 'invalid_format'
    assert 'PRIVATE' not in json.dumps(details) and 'token' not in details['reason']
    missing = B.failure_details({'response_body': {'status': 'incomplete', 'output': []}}, ValueError())
    assert missing['code'] == 'incomplete_response' and 'token' not in missing['reason']


def test_unknown_charge_retains_billing_review_instead_of_validation_feedback(owner):
    progress = []
    def timeout(_):
        raise TimeoutError('private transport URL')
    with patch.object(B, 'check_access'):
        with pytest.raises(ledger.BudgetBlocked, match='charge needs reconciliation') as error:
            B.run(packet(), transport=timeout, progress=progress.append)
    assert progress[-1]['message'] == str(error.value)
    assert 'failure' not in progress[-1] and 'private transport' not in str(error.value)


def legacy_failure(owner, *, prompt='thesis-source-sentiment-20', limit=9000, effort='medium'):
    iid = prepare(owner)
    loading.start(owner, iid, analyze=True)
    for _ in range(6):
        loading.work_once(owner, lambda *_: {})
    p = packet(); p['company'] = {'symbol': 'MSFT', 'name': 'Microsoft Corp'}
    p['sources'] = p['sources'][:1]
    def execute(run, key):
        assert key == 'analysis'
        loading.analysis_progress(run, dict(completed=1, total=15, failed=2,
            source_counts=[1] * 15, message='Batch 2 could not finish; 1 completed batches are saved.'))
        historical = S.request_for(p) | dict(max_output_tokens=limit, reasoning={'effort': effort})
        ledger.execute('legacy-output-limit', prompt, historical, transport=cut_short)
        raise ValueError('Batch 2 of 15 did not pass validation. Completed batches are saved; no automatic retry was made.')
    loading.work_once(owner, execute)
    return iid


@pytest.mark.parametrize('prompt,limit,effort', [
    ('thesis-source-sentiment-20', 9000, 'medium'),
    ('thesis-source-sentiment-21', 12000, 'low'),
])
def test_old_generic_failure_is_explained_on_read_with_immutable_journal(owner, prompt, limit, effort):
    iid = legacy_failure(owner, prompt=prompt, limit=limit, effort=effort)
    with transaction(owner) as conn:
        before = one(conn, 'SELECT * FROM research_loads WHERE instrument_id=%s', (iid,))
    budget = ledger.snapshot()
    result = loading.latest(owner, iid)
    step = result['steps'][-1]
    assert f'{limit:,}-token response limit' in step['message']
    assert '13 later batches were not sent in this run' in step['message']
    assert step['batches']['message'] == step['message']
    assert step['batches']['failure']['code'] == 'output_limit'
    assert '1 completed batch is saved' in step['message']
    with transaction(owner) as conn:
        assert one(conn, 'SELECT * FROM research_loads WHERE id=%s', (before['id'],)) == before
    assert ledger.snapshot() == budget
    from thesis.config import OWNER
    assert loading.latest(OWNER, iid) is None


def test_legacy_diagnosis_cannot_use_different_company_or_later_call(owner):
    iid = legacy_failure(owner)
    with transaction(owner) as conn:
        original = one(conn, 'SELECT * FROM research_loads WHERE instrument_id=%s', (iid,))
        modified = deepcopy(original)
        other = one(conn, "SELECT id FROM instruments WHERE symbol<>'MSFT' ORDER BY id LIMIT 1")
        assert other
        modified['instrument_id'] = other['id']
        assert loading.explain_saved_failure(conn, modified) == modified
        modified = deepcopy(original)
        # No completed call existed before the analysis started.
        modified['steps'][-1]['finished_at'] = modified['steps'][-1]['started_at']
        assert loading.explain_saved_failure(conn, modified) == modified


def test_new_failure_progress_is_not_replaced_by_legacy_diagnostic(owner):
    iid = legacy_failure(owner)
    with transaction(owner) as conn:
        run = one(conn, 'SELECT * FROM research_loads WHERE instrument_id=%s', (iid,))
        run['steps'][-1]['batches']['failure'] = {'code': 'authored_diagnostic'}
        assert loading.explain_saved_failure(conn, run) == run
