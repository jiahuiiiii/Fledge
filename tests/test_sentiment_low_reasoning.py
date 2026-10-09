"""Owner-authorized effort/output tuning, retaining the flagship and old ledger."""
from copy import deepcopy
import pytest
from thesis.db import transaction, one
from thesis.providers import ledger
from thesis.providers.settings import REASONING_MODEL
from thesis.research import sentiment as S
from test_model_budget import (
    clean_model_ledger, reasoning_body, reasoning_response, sentiment_body,
    sentiment_depth_body, finding_check_body,
)
from test_sentiment_batching import packet


def tuned_body():
    return S.request_for(packet())


def test_request_retains_flagship_and_only_changes_effort_and_output_bound():
    body = tuned_body()
    assert body['model'] == REASONING_MODEL == 'gpt-5.4-2026-03-05'
    assert body['reasoning'] == {'effort': 'low'} and body['max_output_tokens'] == 12000
    assert body['text']['format']['strict'] is True
    profile = ledger.request_profile(body)
    assert profile.version == ledger.SENTIMENT_LOW_PRICE_VERSION and profile.effort == 'low'
    # Historical reservations keep their exact caps, rates and effort.
    assert ledger.request_profile(sentiment_body()).max_output == 9000
    assert ledger.request_profile(sentiment_body()).effort == 'medium'
    assert ledger.request_profile(reasoning_body()).max_output == 6000
    assert ledger.request_profile(sentiment_depth_body()).effort == 'high'
    assert ledger.request_profile(finding_check_body()).effort == 'high'


def test_new_profile_reserves_full_maximum_and_settles_usage_once(owner):
    body = tuned_body()
    expected = (len(ledger.canonical(body).encode()) + 8192) * 2500 + 12000 * 15000
    call, fresh = ledger.reserve('low-effort-bounded-classification', S.PROMPT, body)
    assert fresh and call['reserved_nano_usd'] == expected
    reply = reasoning_response(usage=dict(input_tokens=1000, output_tokens=11000,
        input_tokens_details={'cached_tokens': 100},
        output_tokens_details={'reasoning_tokens': 9000}))
    settled = ledger.settle(call, reply)
    assert settled['charged_nano_usd'] == 900*2500 + 100*250 + 11000*15000
    reused = ledger.execute(call['request_key'], S.PROMPT, body,
        transport=lambda _: pytest.fail('cached result resent'))
    assert reused['id'] == call['id'] and ledger.snapshot()['calls'] == 1


def test_new_profile_does_not_rewrite_a_historical_settlement(owner):
    call, _ = ledger.reserve('old-medium-request', 'thesis-source-sentiment-20', sentiment_body())
    assert call['price_version'] == ledger.SENTIMENT_PRICE_VERSION
    settled = ledger.settle(call, reasoning_response(usage=dict(input_tokens=100, output_tokens=9000,
        input_tokens_details={'cached_tokens': 0}, output_tokens_details={'reasoning_tokens': 8086})))
    with transaction() as conn:
        stored = one(conn, 'SELECT * FROM model_calls WHERE id=%s', (call['id'],))
    assert stored == settled and stored['charged_nano_usd'] == 135250000
    assert stored['request_body']['max_output_tokens'] == 9000
    assert stored['request_body']['reasoning'] == {'effort': 'medium'}


@pytest.mark.parametrize('change', [
    dict(max_output_tokens=12001), dict(max_output_tokens=9000),
    dict(reasoning={'effort': 'medium'}), dict(reasoning={'effort': 'none'}),
    dict(reasoning={'effort': 'high'}), dict(service_tier='priority'), dict(store=True),
])
def test_unpriced_variants_cannot_reserve_a_call(owner, change):
    with pytest.raises(ValueError):
        ledger.reserve('unsupported-classification', S.PROMPT, tuned_body() | change)
    assert ledger.snapshot()['calls'] == 0


@pytest.mark.parametrize('name', ['private_relevance', 'finding_evidence_check', 'source_sentiment_reasoning_eval', 'idea_answer_evidence'])
def test_tuned_allowance_is_restricted_to_sentiment(owner, name):
    body = deepcopy(tuned_body()); body['text']['format']['name'] = name
    with pytest.raises(ValueError):
        ledger.reserve('other-route', 'test', body)
    assert ledger.snapshot()['calls'] == 0
