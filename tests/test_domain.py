from uuid import uuid4
from decimal import Decimal
import pytest
from pydantic import ValidationError
from thesis.models import SaveIdea, Condition
from thesis.monitoring.evaluator import evaluate
from thesis.research.pipeline import normalize_article, validate_claim
from thesis.fixtures import dt


def c(**kw):
    return dict(
        condition_id=str(uuid4()),
        metric="revenue_growth",
        operator=">=",
        threshold="15",
        unit="percent",
        basis="reported",
        **kw
    )


def fact(value="18", **kw):
    return dict(
        id=str(uuid4()),
        metric="revenue_growth",
        value=value,
        period="2025-Q2",
        unit="percent",
        basis="reported",
        **kw
    )


@pytest.mark.parametrize(
    "value,expected", [("18", "met"), ("15", "met"), ("14.999999", "not_met")]
)
def test_decimal_threshold(value, expected):
    assert evaluate([c()], [fact(value)], "2025-Q2")[0] == expected


@pytest.mark.parametrize(
    "field,value", [("unit", "USD"), ("basis", "adjusted"), ("period", "2025-YTD")]
)
def test_incompatible_scope_is_unknown(field, value):
    f = fact()
    f[field] = value
    assert evaluate([c()], [f], "2025-Q2")[0] == "unknown"


def test_conflict_and_restatement():
    old = fact("12")
    new = fact("13")
    assert evaluate([c()], [old, new], "2025-Q2")[0] == "unknown"
    new["supersedes_id"] = old["id"]
    assert evaluate([c()], [old, new], "2025-Q2")[1][0]["observed_value"] == "13"


def test_no_vacuous_pass_and_all_failure_dominates_unknown():
    with pytest.raises(ValueError):
        evaluate([], [], "2025-Q2")
    second = c()
    second["metric"] = "operating_margin"
    assert evaluate([c(), second], [fact("12")], "2025-Q2")[0] == "not_met"


@pytest.mark.parametrize("threshold", ["NaN", "Infinity", "-101", "1001"])
def test_invalid_thresholds_rejected(threshold):
    data = c()
    data["threshold"] = threshold
    with pytest.raises(ValidationError):
        Condition(**data)


def test_condition_scope_rejects_currency_and_unknown_operator():
    for field, value in [
        ("unit", "USD"),
        ("operator", "contains"),
        ("period_type", "year"),
    ]:
        data = c()
        data[field] = value
        with pytest.raises(ValidationError):
            Condition(**data)


def test_quote_validation_wrong_company_and_fabrication():
    doc = dict(
        instrument_id="A",
        body="The company did not confirm renewal values.",
        available_at=dt("2025-10-18T14:05:00+00:00"),
    )
    claim = dict(
        instrument_id="A", quote="did not confirm", available_at=doc["available_at"]
    )
    validate_claim(claim, doc)  # Negation remains in exact source; no entailment claim.
    with pytest.raises(ValueError):
        validate_claim(dict(claim, quote="confirmed renewals"), doc)
    with pytest.raises(ValueError):
        validate_claim(dict(claim, instrument_id="B"), doc)
    with pytest.raises(ValueError):
        validate_claim(dict(claim, available_at=dt("2025-10-17T00:00:00+00:00")), doc)
