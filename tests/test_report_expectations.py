"""User-owned reporting expectations, period matching and durable deadline history."""

from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4
import json
import pytest
from pydantic import ValidationError
from thesis import service, review_export, review_digest
from thesis.db import transaction, one
from thesis.config import INSTRUMENT
from thesis.models import SaveIdea, Condition
from thesis.monitoring.evaluator import (
    evaluate,
    manifest_conditions,
    REPORT_VERSION,
    LEGACY_VERSION,
)
from thesis.monitoring.report_expectations import expectation, states
from thesis.providers import ledger
from thesis.research import proposals
from test_integration import payload, drain
from test_reporting_age import finish_all
from test_sec_fundamentals import bundle, apply
from thesis.research.sec.service import add_company


def with_expectation(
    end="2025-09-30", due="2025-08-30", revision=0, iid=INSTRUMENT, **changes
):
    body = payload(revision=revision).model_dump()
    body["instrument_id"] = iid
    body["conditions"] = body["conditions"][:1]
    body["conditions"][0].update(
        expected_period_end=end, expected_report_by=due, **changes
    )
    return SaveIdea(**body)


@pytest.mark.parametrize(
    "end,due",
    [
        (None, "2026-10-31"),
        ("2026-09-30", None),
        ("2026-10-31", "2026-10-30"),
        ("2026-02-30", "2026-03-31"),
        ("2026-09-30", "9999-12-31"),
        ("2026-09-30", "2037-09-30"),
    ],
)
def test_paired_real_calendar_dates_are_required(end, due):
    with pytest.raises(ValidationError):
        with_expectation(end, due)


def fact(end="2025-06-30", period_type="quarter", value="18", **kw):
    return (
        dict(
            id=str(uuid4()),
            metric="revenue_growth",
            period="Chosen period",
            unit="percent",
            basis="reported",
            period_type=period_type,
            period_end=end,
            value=value,
        )
        | kw
    )


def definition(**kw):
    return with_expectation("2025-09-30", "2025-10-30", **kw).conditions[0].model_dump()


def test_inclusive_utc_boundary_and_early_availability():
    c = definition()
    o = fact()
    assert expectation(c, o, "2025-10-30T23:59:59.999999Z")["state"] == "waiting"
    assert expectation(c, o, "2025-10-31T08:00:00+08:00")["state"] == "overdue"
    assert (
        expectation(c, fact("2025-09-30"), "2025-10-01T00:00:00Z")["state"]
        == "available"
    )
    assert (
        expectation(c, fact("2025-12-31"), "2026-01-31T00:00:00Z")["state"]
        == "available"
    )


@pytest.mark.parametrize("role,early", [("required", "met"), ("risk", "not_met")])
def test_last_value_kept_but_cannot_satisfy_overdue_scope(role, early):
    c = definition(role=role)
    o = fact()
    assert evaluate([c], [o], "Chosen period", "2025-10-30T12:00:00Z")[0] == early
    outcome, results = evaluate([c], [o], "Chosen period", "2025-10-31T00:00:00Z")
    assert (
        outcome == "unknown"
        and results[0]["observation_id"] == o["id"]
        and results[0]["observed_value"] == "18"
    )
    assert "does not prove the company filed late" in results[0]["explanation"]
    assert (
        evaluate([c], [fact("2025-09-30")], "Chosen period", "2025-10-31T00:00:00Z")[0]
        == early
    )


def test_scope_conflict_missing_end_and_age_are_independent():
    c = definition()
    clock = "2025-10-31T00:00:00Z"
    for item in [
        fact("2025-09-30", "annual"),
        fact(None),
        fact("2025-09-30", basis="adjusted"),
    ]:
        assert evaluate([c], [item], "Chosen period", clock)[0] == "unknown"
    a = fact("2025-09-30")
    b = fact("2025-09-30", value="21")
    result = evaluate([c], [a, b], "Chosen period", clock)
    assert result[0] == "unknown" and result[1][0]["disagreement"]
    assert states([c], [a, b], "Chosen period", clock)[0]["state"] == "conflicting"
    c["max_report_age_days"] = 1
    assert states([c], [a], "Chosen period", clock)[0]["state"] == "available"
    assert (
        "Too old to assess"
        in evaluate([c], [a], "Chosen period", clock)[1][0]["explanation"]
    )


def test_default_definitions_and_signatures_remain_legacy(owner):
    service.save_idea(owner, payload())
    drain(owner)
    e = service.state(owner)["versions"][0]["evaluations"][0]
    assert (
        "report_expectations" not in e["manifest"]
        and e["manifest"]["evaluator"] == LEGACY_VERSION
    )
    assert all(
        "expected_period_end" not in c and "expected_report_by" not in c
        for c in e["manifest"]["conditions"]
    )
    assert manifest_conditions(
        [
            dict(
                role="required",
                expected_period_end=None,
                expected_report_by=None,
                metric="revenue_growth",
            )
        ]
    ) == [dict(metric="revenue_growth")]


def test_clock_only_missing_interval_then_new_period_recovers(owner):
    # Northstar Q2 is available July24; Q3 arrives Oct24. The chosen target is
    # deliberately June30+1 day rather than an invented official filing date.
    saved = service.save_idea(owner, with_expectation("2025-07-01", "2025-08-30"))
    drain(owner)
    before = service.state(owner)
    first = before["versions"][0]["evaluations"][0]
    assert (
        first["outcome"] == "met"
        and first["manifest"]["report_expectations"][0]["state"] == "waiting"
    )
    budget = ledger.snapshot()
    service.advance(owner, 0)
    service.advance(owner, 1)
    finish_all(owner)
    after = service.state(owner)
    history = list(reversed(after["versions"][0]["evaluations"]))
    overdue = [
        e
        for e in history
        if e["manifest"]["report_expectations"][0]["state"] == "overdue"
    ]
    assert (
        len(overdue) >= 1
        and overdue[0]["manifest"]["assessed_at"] == "2025-08-31T00:00:00+00:00"
    )
    assert (
        overdue[0]["outcome"] == "unknown"
        and overdue[0]["manifest"]["cutoff"] == first["manifest"]["cutoff"]
    )
    assert (
        overdue[0]["results"][0]["observation_id"]
        == first["results"][0]["observation_id"]
    )
    assert history[-1]["manifest"]["report_expectations"][0]["state"] == "available"
    assert history[0] == first and ledger.snapshot() == budget
    changes = [c for c in after["changes"] if c["kind"] == "reporting"]
    assert len(changes) == 2
    assert {c["details"]["affected_reports"][0]["state"] for c in changes} == {
        "available",
        "overdue",
    }
    assert history[-1]["manifest"]["evaluator"] == REPORT_VERSION
    drain(owner)
    assert service.state(owner)["versions"] == after["versions"]
    _, html = review_export.download(
        owner, saved["version_id"], evaluation_id=overdue[0]["id"]
    )
    assert "Expected figures are missing" in html and "2025-08-30" in html
    _, digest = review_digest.download(owner)
    assert (
        "Expected figures are missing" in digest
        and "Required quarter figures are available" in digest
    )


def test_clearing_an_expectation_creates_a_new_revision(owner):
    service.save_idea(owner, with_expectation("2025-12-31", "2026-01-31"))
    drain(owner)
    for stage in range(4):
        service.advance(owner, stage)
    drain(owner)
    prior = service.state(owner)["versions"][0]["evaluations"][0]
    assert prior["manifest"]["report_expectations"][0]["state"] == "waiting"
    # Use SEC wall-clock mode for a clock beyond the recorded sample below;
    # this recorded sample remains at its fixture date, as designed.
    revised = with_expectation(None, None, revision=1)
    service.save_idea(owner, revised)
    drain(owner)
    current = service.state(owner)["versions"]
    assert (
        current[1]["evaluations"][0] == prior
        and "report_expectations" not in current[0]["evaluations"][0]["manifest"]
    )


def test_sec_clock_deadline_restatement_archive_and_permissions(owner):
    iid = add_company("MSFT")["instrument_id"]
    apply(iid, bundle())
    today = datetime.now(timezone.utc).date()
    # Put the deadline beyond the independent 24-hour source-freshness boundary.
    # Using today made the +1h repeat cross that boundary before 01:00 UTC,
    # correctly creating a new assessment unrelated to deadline deduplication.
    due = today + timedelta(days=1)
    sv = service.save_idea(
        owner, with_expectation("2025-12-31", due.isoformat(), iid=iid)
    )
    drain(owner)
    baseline = service.state(owner, iid)
    first = baseline["versions"][0]["evaluations"][0]
    clock = datetime.combine(
        due + timedelta(days=1), datetime.min.time(), timezone.utc
    )
    before = ledger.snapshot()
    service.queue_current(owner, now=clock)
    finish_all(owner)
    after = service.state(owner, iid)
    last = after["versions"][0]["evaluations"][0]
    assert last['freshness'] == 'stale'
    assert (
        last["outcome"] == "unknown"
        and last["manifest"]["report_expectations"][0]["state"] == "overdue"
    )
    assert (
        after["documents"] == baseline["documents"]
        and after["source_checks"] == baseline["source_checks"]
        and ledger.snapshot() == before
    )
    service.queue_current(owner, now=clock + timedelta(hours=1))
    finish_all(owner)
    assert service.state(owner, iid)["versions"] == after["versions"]
    apply(iid, bundle(revenue=130))
    service.queue_current(owner, now=clock + timedelta(hours=2))
    finish_all(owner)
    current = service.state(owner, iid)["versions"][0]["evaluations"][0]
    assert current["manifest"]["report_expectations"][0]["state"] == "overdue"
    other = str(uuid4())
    with transaction(admin=True) as c:
        c.execute("INSERT INTO accounts VALUES(%s,%s)", (other, "Other test"))
    assert service.state(other, iid)["versions"] == []
    archived = with_expectation(
        "2025-12-31", today.isoformat(), revision=1, iid=iid
    ).model_dump()
    archived["status"] = "archived"
    service.save_idea(owner, SaveIdea(**archived))
    service.queue_current(owner, now=clock + timedelta(days=2))
    finish_all(owner)
    assert service.state(owner, iid)["versions"][1]["evaluations"][0] == current


def test_pending_numeric_suggestion_preserves_explicit_dates(owner):
    saved = service.save_idea(owner, with_expectation("2025-09-30", "2025-10-30"))
    drain(owner)
    with transaction(owner) as c:
        base = proposals.base_definition(c, owner, INSTRUMENT, saved["version_id"])
    old = base["conditions"][0]
    new = {
        k: v
        for k, v in old.items()
        if k not in ("condition_id", "expected_period_end", "expected_report_by")
    }
    new["threshold"] = "30"
    candidate = proposals.apply_change(
        base,
        dict(
            id=str(uuid4()),
            kind="numeric",
            operation="update",
            target_condition_id=old["condition_id"],
            proposed=dict(definition=new),
        ),
    )
    assert (
        candidate["conditions"][0]["expected_period_end"] == "2025-09-30"
        and candidate["conditions"][0]["expected_report_by"] == "2025-10-30"
    )
    SaveIdea(**candidate)


def test_source_withdrawal_withholds_new_reporting_metadata(owner):
    sv = service.save_idea(owner, with_expectation("2025-06-30", "2025-07-30"))
    drain(owner)
    before = service.state(owner)
    assert (
        before["versions"][0]["evaluations"][0]["manifest"]["report_expectations"][0][
            "state"
        ]
        == "available"
    )
    with transaction(admin=True) as c:
        originals = c.execute("SELECT id,entitlement FROM sources").fetchall()
        original_check = one(
            c,
            "SELECT pg_get_constraintdef(oid) definition FROM pg_constraint WHERE conrelid='sources'::regclass AND conname='sources_entitlement_check'",
        )["definition"]
        c.execute("ALTER TABLE sources DROP CONSTRAINT sources_entitlement_check")
        c.execute("UPDATE sources SET entitlement='restricted'")
    try:
        e = service.state(owner)["versions"][0]["evaluations"][0]
        assert (
            e["manifest"]["report_expectations"][0]["state"] == "withheld"
            and e["manifest"]["report_expectations"][0]["observed_period_end"] is None
        )
        _, html = review_export.download(owner, sv["version_id"], evaluation_id=e["id"])
        assert "Required quarter figures are available" not in html
    finally:
        with transaction(admin=True) as c:
            for source in originals:
                c.execute(
                    "UPDATE sources SET entitlement=%s WHERE id=%s",
                    (source["entitlement"], source["id"]),
                )
            c.execute(
                "ALTER TABLE sources ADD CONSTRAINT sources_entitlement_check "
                + original_check
            )
    assert (
        service.state(owner)["versions"][0]["evaluations"][0]["manifest"][
            "report_expectations"
        ][0]["state"]
        == "available"
    )
