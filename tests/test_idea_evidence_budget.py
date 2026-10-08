"""The richer private answer route has its own finite, fully reserved allowance."""

from copy import deepcopy
import pytest
from thesis.providers import ledger
from test_model_budget import (
    reasoning_body,
    reasoning_response,
    sentiment_body,
    finding_check_body,
)


def body():
    value = reasoning_body()
    value["max_output_tokens"] = ledger.IDEA_EVIDENCE_MAX_OUTPUT
    value["text"]["format"]["name"] = "idea_answer_evidence"
    return value


def test_private_evidence_profile_preserves_historical_profiles_and_full_reservation(
    db,
):
    value = body()
    old = deepcopy(value)
    old["max_output_tokens"] = 6000
    assert ledger.request_profile(value).version == ledger.IDEA_EVIDENCE_PRICE_VERSION
    assert ledger.request_profile(old).version == ledger.REASONING_PRICE_VERSION
    assert (
        ledger.request_profile(sentiment_body()).version
        == ledger.SENTIMENT_PRICE_VERSION
    )
    assert (
        ledger.request_profile(finding_check_body()).version
        == ledger.FINDING_CHECK_PRICE_VERSION
    )
    assert ledger.estimate(value) - ledger.estimate(old) == 3000 * 15000
    call, fresh = ledger.reserve("bounded-private-answer-evidence", "test", value)
    assert fresh and call["reserved_nano_usd"] == ledger.estimate(value)
    settled = ledger.settle(
        call,
        reasoning_response(
            usage=dict(
                input_tokens=100,
                output_tokens=8700,
                input_tokens_details=dict(cached_tokens=10),
                output_tokens_details=dict(reasoning_tokens=6000),
            )
        ),
    )
    assert settled["charged_nano_usd"] == 90 * 2500 + 10 * 250 + 8700 * 15000
    assert ledger.snapshot()["unresolved"] == 0


@pytest.mark.parametrize(
    "change",
    [
        dict(max_output_tokens=9001),
        dict(reasoning={"effort": "high"}),
        dict(service_tier="priority"),
        dict(model=ledger.MODEL),
    ],
)
def test_private_evidence_profile_rejects_unpriced_variants(change):
    with pytest.raises(ValueError):
        ledger.estimate(body() | change)


def test_question_format_cannot_silently_use_private_evidence_allowance():
    value = body()
    value["text"]["format"]["name"] = "idea_source_relevance"
    with pytest.raises(ValueError):
        ledger.estimate(value)
