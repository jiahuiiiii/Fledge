"""Opt-in replays of real saved SEC responses. Never fetches or calls a model.

Run with THESIS_REAL_CORPUS pointing to the exported public response directory.
Acquisition/restart timing and thresholds are authored test conditions, not a
prospective market backtest or customer investment advice.
"""

import json
import os
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4
import pytest
from thesis import service
from thesis.db import transaction, one
from thesis.models import SaveIdea
from thesis.research.sec.service import add_company, commit_bundle
from thesis.research.sec.normalize import normalize
from thesis.monitoring.evaluator import evaluate
from test_integration import drain

CORPUS = os.environ.get("THESIS_REAL_CORPUS")
pytestmark = pytest.mark.skipif(
    not CORPUS,
    reason="Opt-in saved real SEC corpus not configured; no automatic fetching",
)
EXPECTED = {
    "MSFT": dict(
        cik=789019,
        period_type="annual",
        growth="17.78868679984665843165651490",
        margin="46.78081840892722073053498835",
        end="2026-06-30",
    ),
    "AAPL": dict(
        cik=320193,
        period_type="quarter",
        growth="16.35650176528138159853673060",
        margin="32.62290137729968834824570222",
        end="2026-06-27",
    ),
    "GOOGL": dict(
        cik=1652044,
        period_type="quarter",
        growth="24.23362508814867051064006310",
        margin="34.03285585495342081538615647",
        end="2026-06-30",
    ),
}


def source(symbol):
    return json.loads((Path(CORPUS) / (symbol + ".json")).read_text())


def load(symbol):
    data = source(symbol)
    iid = add_company(symbol)["instrument_id"]
    now = datetime.now(timezone.utc)
    with transaction(source=True) as conn:
        commit_bundle(conn, iid, data["payload"], now)
    return iid, data


def condition(metric, threshold, period_type, **kw):
    return dict(
        condition_id=str(uuid4()),
        metric=metric,
        operator=">=",
        threshold=threshold,
        unit="percent",
        basis="reported",
        period_type=period_type,
        **kw
    )


@pytest.mark.parametrize("symbol", EXPECTED)
def test_real_sec_normalization_matches_independently_checked_filing(symbol):
    data = source(symbol)
    expected = EXPECTED[symbol]
    parsed = normalize(
        data["payload"]["companyfacts"],
        data["payload"]["submissions"],
        expected["cik"],
        datetime.fromisoformat(data["retrieved_at"]),
    )
    assert parsed["period_type"] == expected["period_type"]
    assert str(parsed["period_end"]) == expected["end"]
    assert [Decimal(c["value"]) for c in parsed["calculations"]] == [
        Decimal(expected["growth"]),
        Decimal(expected["margin"]),
    ]
    for c in parsed["calculations"]:
        assert all(x["accession"] == parsed["accession"] for x in c["inputs"])


@pytest.mark.parametrize("symbol", EXPECTED)
def test_real_replay_full_monitoring_and_repeat_has_no_spurious_update(owner, symbol):
    iid, data = load(symbol)
    expected = EXPECTED[symbol]
    conditions = [
        condition("revenue_growth", "15", expected["period_type"]),
        condition("revenue_growth", "20", expected["period_type"]),
        condition("operating_margin", "33", expected["period_type"]),
        condition("operating_margin", "45", expected["period_type"]),
    ]
    saved = service.save_idea(
        owner,
        SaveIdea(
            instrument_id=iid,
            expected_revision=0,
            question="Real evidence replay test",
            reasoning="Authored test reasoning; inspect growth and margin.",
            status="monitoring",
            conditions=conditions,
        ),
    )
    drain(owner)
    state = service.state(owner, iid)
    evaluation = state["versions"][0]["evaluations"][0]
    outcomes = {str(r["condition_id"]): r["outcome"] for r in evaluation["results"]}
    for c in conditions:
        value = Decimal(
            expected["growth"]
            if c["metric"] == "revenue_growth"
            else expected["margin"]
        )
        assert outcomes[c["condition_id"]] == (
            "met" if value >= Decimal(c["threshold"]) else "not_met"
        )
    with transaction(source=True) as conn:
        repeat = commit_bundle(conn, iid, data["payload"], datetime.now(timezone.utc))
    drain(owner)
    again = service.state(owner, iid)
    assert len(again["versions"][0]["evaluations"]) == 1
    assert not [
        c for c in again["changes"] if str(c["version_id"]) == saved["version_id"]
    ]
    assert (
        evaluation["manifest"]["observation_ids"]
        == again["versions"][0]["evaluations"][0]["manifest"]["observation_ids"]
    )


@pytest.mark.parametrize("symbol", EXPECTED)
def test_real_fiscal_scope_and_age_boundaries_are_not_guessed(owner, symbol):
    iid, _ = load(symbol)
    state = service.state(owner, iid)
    expected = EXPECTED[symbol]
    facts = state["observations"]
    period = state["demo"]["period"]
    scope = expected["period_type"]
    wrong = "quarter" if scope == "annual" else "annual"
    assert (
        evaluate([condition("revenue_growth", 0, wrong)], facts, period)[0] == "unknown"
    )
    end = datetime.fromisoformat(expected["end"]).replace(tzinfo=timezone.utc)
    c = condition("revenue_growth", 0, scope, max_report_age_days=90)
    assert (
        evaluate(
            [c],
            facts,
            period,
            (end + timedelta(days=90, hours=23, minutes=59)).isoformat(),
        )[0]
        == "met"
    )
    outcome, results = evaluate(
        [c], facts, period, (end + timedelta(days=91)).isoformat()
    )
    assert outcome == "unknown" and results[0]["observed_value"] == Decimal(
        expected["growth"]
    )


@pytest.mark.parametrize("symbol", EXPECTED)
def test_real_payload_reordering_and_unrelated_field_noise_have_no_financial_effect(
    symbol,
):
    data = source(symbol)
    expected = EXPECTED[symbol]
    bundle = deepcopy(data["payload"])
    now = datetime.fromisoformat(data["retrieved_at"])
    original = normalize(
        bundle["companyfacts"], bundle["submissions"], expected["cik"], now
    )
    for concept in bundle["companyfacts"]["facts"].get("us-gaap", {}).values():
        for unit, facts in concept.get("units", {}).items():
            facts.reverse()
    bundle["companyfacts"][
        "irrelevant_test_metadata"
    ] = "Synthetic fault: ignored extra field"
    altered = normalize(
        bundle["companyfacts"], bundle["submissions"], expected["cik"], now
    )
    assert original["calculations"] == altered["calculations"]


@pytest.mark.parametrize("symbol", EXPECTED)
def test_real_payload_wrong_company_is_rejected_before_ingestion(symbol):
    data = source(symbol)
    wrong = 320193 if symbol != "AAPL" else 789019
    with pytest.raises(ValueError):
        normalize(
            data["payload"]["companyfacts"],
            data["payload"]["submissions"],
            wrong,
            datetime.fromisoformat(data["retrieved_at"]),
        )
