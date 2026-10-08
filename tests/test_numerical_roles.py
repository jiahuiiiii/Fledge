"""Requirements vs explicit risk thresholds. Offline; real inputs are saved replays."""

from copy import deepcopy
from decimal import Decimal
from uuid import uuid4
import os
import pytest
from pydantic import ValidationError
import psycopg
from thesis import service, review_export, review_digest
from thesis.db import transaction, one
from thesis.models import Condition, SaveIdea
from thesis.monitoring.evaluator import (
    evaluate,
    VERSION,
    LEGACY_VERSION,
    manifest_conditions,
)
from thesis.monitoring.events import combined_outcome
from test_domain import c, fact
from test_integration import payload, drain


@pytest.mark.parametrize(
    "operator,value,matched",
    [
        (">=", "15", True),
        (">=", "15.000000000000000001", True),
        (">=", "14.999999999999999999", False),
        ("<=", "15", True),
        ("<=", "14.999999999999999999", True),
        ("<=", "15.000000000000000001", False),
    ],
)
@pytest.mark.parametrize("role", ["required", "risk"])
def test_decimal_boundary_and_explicit_role(operator, value, matched, role):
    rule = c()
    rule.update(operator=operator, role=role)
    result = evaluate([rule], [fact(value)], "2025-Q2")[1][0]
    assert result["outcome"] == (
        "met" if matched == (role == "required") else "not_met"
    )
    assert result["observed_value"] == value
    if role == "risk":
        assert ("was reached" if matched else "was not reached") in result[
            "explanation"
        ]


@pytest.mark.parametrize(
    "fault",
    ["missing", "conflict", "period", "basis", "unit", "expired", "missing_end"],
)
def test_risk_abstains_instead_of_claiming_safety(fault):
    rule = c(role="risk")
    observations = [fact("12", period_end="2025-06-30")]
    if fault == "missing":
        observations = []
    if fault == "conflict":
        observations.append(fact("18"))
    if fault in ("period", "basis", "unit"):
        observations[0][fault] = "incompatible"
    if fault in ("expired", "missing_end"):
        rule["max_report_age_days"] = 1
        if fault == "missing_end":
            observations[0].pop("period_end")
    outcome, results = evaluate(
        [rule], observations, "2025-Q2", "2025-10-01T00:00:00+00:00"
    )
    assert outcome == "unknown"
    assert "was not reached" not in results[0]["explanation"]
    assert combined_outcome(results + [{"outcome": "not_met"}]) == "not_met"


def risk_payload(revision=0, role="risk", status="monitoring"):
    p = payload(revision=revision, status=status).model_dump()
    p["conditions"] = p["conditions"][:1]
    p["conditions"][0].update(role=role, operator="<=", threshold=Decimal("15"))
    return SaveIdea(**p)


def test_contract_and_legacy_meaning():
    assert Condition(**c()).role == "required"
    for role in ("invalid", None, True):
        with pytest.raises(ValidationError):
            Condition(**c(role=role))
    with pytest.raises(ValueError):
        evaluate([c(role="invalid")], [fact()], "2025-Q2")


def test_legacy_manifest_identity_pending_job_and_repeat(owner):
    saved = service.save_idea(owner, payload())
    with transaction(owner) as conn:
        job = one(conn, "SELECT * FROM jobs WHERE id=%s", (saved["job"]["id"],))
        assert all("role" not in c for c in job["manifest"]["conditions"])
        assert job["manifest"]["evaluator"] == LEGACY_VERSION
        generated = service.manifest_for(conn, owner, saved["version_id"])
        assert service.material_signature(generated) == job["input_signature"]
    drain(owner)
    first = service.state(owner)["versions"][0]["evaluations"][0]
    assert (
        first["manifest"] == job["manifest"]
        and first["fingerprint"] == job["fingerprint"]
    )
    drain(owner)
    assert service.state(owner)["versions"][0]["evaluations"] == [first]
    assert not service.state(owner)["changes"]


def test_risk_change_review_history_export_and_access(owner):
    saved = service.save_idea(owner, risk_payload())
    drain(owner)
    baseline = service.state(owner)["versions"][0]["evaluations"][0]
    assert baseline["outcome"] == "met"
    assert baseline["manifest"]["evaluator"] == VERSION
    assert baseline["manifest"]["conditions"][0]["role"] == "risk"
    assert baseline["results"][0]["role"] == "risk"
    service.advance(owner, 0)
    service.advance(owner, 1)
    drain(owner)
    state = service.state(owner)
    e = state["versions"][0]["evaluations"][0]
    assert e["outcome"] == "not_met" and e["results"][0]["observed_value"] == Decimal(
        "12"
    )
    changed = next(c for c in state["changes"] if c["details"]["affected_conditions"])
    affected = changed["details"]["affected_conditions"][0]
    assert (
        affected["role"] == "risk"
        and affected["before_outcome"] == "met"
        and affected["outcome"] == "not_met"
    )
    _, html = review_export.download(owner, saved["version_id"], evaluation_id=e["id"])
    assert (
        "Risk threshold reached" in html
        and "Risk to watch" in html
        and "At most 15%" in html
    )
    _, html = review_export.download(
        owner, saved["version_id"], evaluation_id=baseline["id"]
    )
    assert "Risk threshold not reached" in html and "18.00%" in html
    service.review(owner, e["id"], "reviewed")
    assert service.state(owner)["versions"][0]["evaluations"][0]["outcome"] == "not_met"
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with transaction(owner) as conn:
            conn.execute(
                "UPDATE version_conditions SET role='required' WHERE version_id=%s",
                (saved["version_id"],),
            )
    with pytest.raises(service.Missing):
        review_export.prepare(str(uuid4()), saved["version_id"])
    with transaction(admin=True) as conn:
        conn.execute(
            "UPDATE sources SET entitlement='local-yahoo-history' WHERE id=(SELECT source_id FROM documents WHERE id=(SELECT document_id FROM document_versions WHERE id=(SELECT document_version_id FROM observations WHERE id=%s)))",
            (e["results"][0]["observation_id"],),
        )
    _, html = review_export.download(owner, saved["version_id"], evaluation_id=e["id"])
    assert "Risk threshold reached" not in html


def test_role_edit_preserves_pending_older_revision(owner):
    original = risk_payload(role="required")
    old = service.save_idea(owner, original)
    claimed = service.claim_job(owner)
    replacement = original.model_dump()
    replacement["expected_revision"] = 1
    replacement["conditions"][0]["role"] = "risk"
    new = service.save_idea(owner, SaveIdea(**replacement))
    service.finish_job(owner, claimed)
    drain(owner)
    versions = service.state(owner)["versions"]
    assert (
        str(versions[0]["id"]) == new["version_id"]
        and versions[0]["evaluations"][0]["outcome"] == "met"
    )
    assert (
        str(versions[1]["id"]) == old["version_id"]
        and versions[1]["evaluations"][0]["outcome"] == "not_met"
    )
    assert (
        versions[0]["conditions"][0]["condition_id"]
        == versions[1]["conditions"][0]["condition_id"]
    )
    assert versions[1]["conditions"][0]["role"] == "required"


@pytest.mark.skipif(
    not os.environ.get("THESIS_REAL_CORPUS"),
    reason="Saved real SEC corpus required; no network",
)
@pytest.mark.parametrize("symbol", ["MSFT", "AAPL", "GOOGL"])
def test_saved_real_filings_with_authored_risk_rules(owner, symbol):
    from test_real_case_replay import load, EXPECTED

    iid, _ = load(symbol)
    known = EXPECTED[symbol]
    rules = []
    for metric, threshold, operator in [
        ("revenue_growth", "20", "<="),
        ("operating_margin", "33", "<="),
    ]:
        rule = c(role="risk")
        rule.update(
            metric=metric,
            threshold=threshold,
            operator=operator,
            period_type=known["period_type"],
        )
        rules.append(rule)
    service.save_idea(
        owner,
        SaveIdea(
            instrument_id=iid,
            expected_revision=0,
            question="Saved real-data role replay",
            reasoning="Authored thresholds for a software test, not investment advice.",
            status="monitoring",
            conditions=rules,
        ),
    )
    drain(owner)
    evaluation = service.state(owner, iid)["versions"][0]["evaluations"][0]
    by_metric = {r["metric"]: r for r in evaluation["results"]}
    assert by_metric["revenue_growth"]["outcome"] == (
        "not_met" if symbol in ("MSFT", "AAPL") else "met"
    )
    assert by_metric["operating_margin"]["outcome"] == (
        "not_met" if symbol == "AAPL" else "met"
    )
    assert all(r["observation_id"] for r in evaluation["results"])
    before = deepcopy(evaluation)
    drain(owner)
    assert service.state(owner, iid)["versions"][0]["evaluations"][0] == before


def test_reasoning_suggestions_preserve_risk_and_implicit_numeric_role_is_rejected(owner):
    from thesis.research import proposals
    from test_proposals import request, provider, complete

    saved = service.save_idea(owner, risk_payload(status="draft"))

    def reasoning(packet):
        return [
            dict(
                kind="reasoning",
                operation="update",
                question=packet["base"]["question"],
                reasoning="Authored revised research question without changing the saved risk.",
            )
        ]

    p = proposals.generate(owner, request(owner, saved), transport=provider(reasoning))[
        "proposals"
    ][0]
    assert p["candidate"]["conditions"][0]["role"] == "risk"
    approved = proposals.decide(owner, p["id"], definition=complete(p, status="draft"))
    assert (
        proposals.decide(owner, p["id"], definition=complete(p, status="draft"))
        == approved
    )
    assert service.state(owner)["versions"][0]["conditions"][0]["role"] == "risk"

    # A new generated update must explicitly state its role; an old-shaped
    # model response cannot silently turn the existing risk into a requirement.
    def numeric(packet):
        return [
            dict(
                kind="numeric",
                operation="update",
                target_condition_id=packet["base"]["conditions"][0]["condition_id"],
                definition=dict(
                    metric="revenue_growth",
                    operator="<=",
                    threshold="12",
                    period_type="quarter",
                    max_report_age_days=None,
                ),
            )
        ]

    current = {"version_id": str(service.state(owner)["versions"][0]["id"])}
    with pytest.raises(ValueError, match="role"):
        proposals.generate(owner, request(owner, current), transport=provider(numeric))
