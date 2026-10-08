from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
from decimal import Decimal
import pytest
from thesis import service
from thesis.models import SaveIdea, ResearchAction
from thesis.config import INSTRUMENT
from thesis.db import transaction, one
from thesis.fixtures import dt, STAGES, uid
from thesis.research.recorded import AURORA, recorded_batch
from thesis.research.acquisition import (
    Batch,
    Check,
    Document,
    ingest_batch,
    latest_coverage,
)
from test_integration import payload, drain, saved


def aurora_payload(**kw):
    p = payload(**kw).model_dump()
    p["instrument_id"] = AURORA
    p["conditions"][0]["threshold"] = Decimal("5")
    p["conditions"][1]["threshold"] = Decimal("10")
    p["reasoning"] = "Aurora sensor demand might grow; costs could weaken margin."
    return SaveIdea(**p)


def poll(instrument=INSTRUMENT, delta=1, outcome="success", checks=True):
    with transaction() as conn:
        info = service.stage_info(conn, instrument)
    cutoff = dt(info["as_of"]) + timedelta(hours=delta)
    sources = (
        ["company", "wire"]
        if instrument == INSTRUMENT
        else ["aurora-company", "aurora-wire"]
    )
    return Batch(
        instrument_id=instrument,
        cutoff=cutoff,
        period=info["period"],
        sequence=info["stage"],
        label="Source check",
        documents=[],
        checks=(
            [
                Check(
                    id=uuid4(),
                    source_id=s,
                    checked_at=cutoff,
                    outcome=outcome,
                    cursor="new" if outcome == "success" else None,
                    covered_through=cutoff if outcome == "success" else None,
                )
                for s in sources
            ]
            if checks
            else []
        ),
    )


def apply(batch):
    with transaction(admin=True) as conn:
        ingest_batch(conn, batch)


def test_two_company_ideas_and_updates_are_separate(owner):
    saved(owner)
    service.save_idea(owner, aurora_payload())
    drain(owner)
    before = service.state(owner, AURORA)
    assert [str(f["value"]) for f in before["fundamentals"]] == ["8", "14"]
    service.advance(owner, 0)
    drain(owner)
    n = service.state(owner)
    a = service.state(owner, AURORA)
    assert a["versions"] == before["versions"] and a["demo"]["stage"] == 0
    assert n["demo"]["stage"] == 1 and len(n["versions"][0]["evaluations"]) == 2
    assert (
        len(n["changes"]) == 1 and str(n["changes"][0]["instrument_id"]) == INSTRUMENT
    )
    assert all(str(j["version_id"]) == str(a["versions"][0]["id"]) for j in a["jobs"])
    service.research_action(
        owner,
        ResearchAction(
            instrument_id=AURORA, question="Launch timing?", action="unresolved"
        ),
    )
    assert service.state(owner)["research_action"] is None
    assert (
        service.state(owner, AURORA)["research_action"]["question"] == "Launch timing?"
    )


def test_same_company_batch_reaches_each_private_owner(owner):
    other = str(uuid4())
    with transaction(admin=True) as conn:
        conn.execute("INSERT INTO accounts VALUES(%s,%s)", (other, "Second local test"))
    saved(owner)
    saved(other)
    drain(owner)
    drain(other)
    service.advance(owner, 0)
    drain(owner)
    drain(other)
    assert len(service.state(other)["changes"]) == 1
    assert all(str(c["owner_id"]) == other for c in service.state(other)["changes"])
    service.review(
        owner, service.state(owner)["changes"][0]["evaluation_id"], "reviewed"
    )
    assert service.state(other)["changes"][0]["review_action"] is None


def test_successful_empty_poll_updates_coverage_without_review_noise(owner):
    saved(owner)
    drain(owner)
    before = service.state(owner)
    apply(poll())
    drain(owner)
    after = service.state(owner)
    assert after["versions"] == before["versions"]
    assert len(after["jobs"]) == len(before["jobs"]) and after["changes"] == []
    assert (
        after["source_checks"][0]["checked_at"]
        > before["source_checks"][0]["checked_at"]
    )


def test_latest_coverage_recovers_and_ages_without_new_documents(owner):
    saved(owner)
    drain(owner)
    apply(poll(outcome="denied"))
    drain(owner)
    denied = service.state(owner)
    assert denied["coverage"] == "stale" and all(
        c["state"] == "denied" for c in denied["source_checks"]
    )
    apply(poll())
    drain(owner)
    recovered = service.state(owner)
    assert recovered["coverage"] == "fresh" and len(recovered["changes"]) == 2
    apply(poll(delta=25, checks=False))
    drain(owner)
    stale = service.state(owner)
    assert stale["coverage"] == "stale" and all(
        c["state"] == "stale" for c in stale["source_checks"]
    )
    assert len(stale["changes"]) == 3


def test_copied_story_retains_provenance_without_an_extra_alert(owner):
    saved(owner)
    drain(owner)
    batch = poll()
    original = recorded_batch(INSTRUMENT, 0).documents[0]
    copy = original.model_copy(deep=True)
    copy.id = uuid4()
    copy.version_id = uuid4()
    copy.source_id = "wire"
    copy.url = "fixture://syndicated/q2"
    copy.headline = "Wire republishes Northstar Q2 release"
    copy.available_at = batch.cutoff
    copy.facts = []
    for claim in copy.claims:
        claim.id = uuid4()
    batch.documents = [copy]
    apply(batch)
    drain(owner)
    data = service.state(owner)
    assert (
        len(data["documents"]) == 2
        and len(data["versions"][0]["evaluations"]) == 1
        and data["changes"] == []
    )
    assert len(data["claims"]) == 2
    assert all(
        len(c["origin_keys"]) == 1 and len(c["source_version_ids"]) == 2
        for c in data["claims"]
    )


def test_failed_batch_does_not_advance_source_cursor(owner):
    saved(owner)
    before = service.state(owner)
    batch = poll()
    original = recorded_batch(INSTRUMENT, 0).documents[0].model_copy(deep=True)
    original.id = uuid4()
    original.version_id = uuid4()
    original.url = "fixture://bad/quote"
    original.available_at = batch.cutoff
    for f in original.facts:
        f.id = uuid4()
    for c in original.claims:
        c.id = uuid4()
    original.claims[0].quote = "Fabricated quote not in the original"
    batch.documents = [original]
    with pytest.raises(ValueError, match="absent"):
        apply(batch)
    after = service.state(owner)
    assert (
        after["demo"] == before["demo"]
        and after["documents"] == before["documents"]
        and after["source_checks"] == before["source_checks"]
    )


def test_wrong_company_sources_and_unsupported_company_rejected(owner):
    bad = recorded_batch(AURORA, 1).model_copy(update={"instrument_id": INSTRUMENT})
    with pytest.raises(ValueError, match="permitted"):
        apply(bad)
    with pytest.raises(service.Missing):
        service.state(owner, str(uuid4()))
    p = aurora_payload().model_copy(update={"instrument_id": uuid4()})
    with pytest.raises(service.Missing):
        service.save_idea(owner, p)


def test_concurrent_queue_is_idempotent_and_same_revision_jobs_are_ordered(owner):
    saved(owner)
    first = service.claim_job(owner)
    apply(recorded_batch(INSTRUMENT, 1))
    with ThreadPoolExecutor(2) as pool:
        list(pool.map(lambda _: service.queue_current(owner), range(2)))
    assert service.claim_job(owner) is None
    service.finish_job(owner, first)
    second = service.claim_job(owner)
    assert second is not None
    service.finish_job(owner, second)
    assert len(service.state(owner)["changes"]) == 1


def test_legacy_completed_input_does_not_create_an_upgrade_alert(owner):
    result = saved(owner)
    drain(owner)
    with transaction(owner) as conn:
        conn.execute(
            "UPDATE jobs SET input_signature=NULL WHERE version_id=%s",
            (result["version_id"],),
        )
    before = service.state(owner)
    drain(owner)
    after = service.state(owner)
    assert before["versions"] == after["versions"] and after["changes"] == []


def test_restart_replays_every_coverage_transition_in_order(owner):
    saved(owner)
    drain(owner)
    for outcome in ("denied", "success", "denied"):
        apply(poll(outcome=outcome))
    # Worker is deliberately absent until all three shared batches committed.
    service.queue_current(owner)
    observed = []
    while job := service.claim_job(owner):
        observed.append(job["manifest"]["freshness"])
        service.finish_job(owner, job)
    assert observed == ["stale", "fresh", "stale"]
    data = service.state(owner)
    assert len(data["changes"]) == 3
    drain(owner)
    assert len(service.state(owner)["changes"]) == 3


def test_equal_cutoff_changes_compare_to_exact_previous_assessment(owner):
    saved(owner)
    drain(owner)
    for outcome in ("denied", "success"):
        apply(poll(delta=0, outcome=outcome))
    drain(owner)
    events = list(reversed(service.state(owner)["changes"]))
    assert len(events) == 2
    assert events[1]["previous_evaluation_id"] == events[0]["evaluation_id"]
    assert events[1]["details"]["coverage_before"] == "stale"
    assert events[1]["details"]["coverage_after"] == "fresh"


def test_concurrent_advance_accepts_expected_sequence_once(owner):
    def attempt(_):
        try:
            service.advance(owner, 0)
            return "advanced"
        except service.Conflict:
            return "conflict"

    with ThreadPoolExecutor(2) as pool:
        assert sorted(pool.map(attempt, range(2))) == ["advanced", "conflict"]
    assert service.state(owner)["demo"]["stage"] == 1


def test_period_boundaries_and_future_report_are_rejected(owner):
    from pydantic import ValidationError

    data = recorded_batch(INSTRUMENT, 0).model_dump()
    data["documents"][0]["facts"][0]["period_start"] = "2025-04-02"
    with pytest.raises(ValidationError, match="boundaries"):
        Batch(**data)
    data = recorded_batch(INSTRUMENT, 0).model_dump()
    fact = data["documents"][0]["facts"][0]
    fact.update(period="2026-Q2", period_start="2026-04-01", period_end="2026-06-30")
    with pytest.raises(ValidationError, match="after source publication"):
        Batch(**data)
    data = recorded_batch(INSTRUMENT, 0).model_dump()
    data["documents"][0]["published_at"] = dt("2025-06-29T12:00:00Z")
    with pytest.raises(ValidationError, match="after source publication"):
        Batch(**data)


@pytest.mark.parametrize(
    "field,value",
    [
        ("headline", "Changed title"),
        ("origin_key", "different origin"),
        ("available_at", "later"),
    ],
)
def test_source_version_metadata_cannot_change_on_replay(owner, field, value):
    batch = recorded_batch(INSTRUMENT, 0).model_copy(deep=True)
    if value == "later":
        value = batch.cutoff + timedelta(seconds=1)
        batch.cutoff = value
    setattr(batch.documents[0], field, value)
    with pytest.raises(ValueError, match="Immutable source"):
        apply(batch)


def test_observations_claims_and_check_identity_cannot_change_on_replay(owner):
    for target in ("facts", "claims", "checks"):
        batch = recorded_batch(INSTRUMENT, 0).model_copy(deep=True)
        if target == "facts":
            batch.documents[0].facts[0].value += 1
        elif target == "claims":
            batch.documents[0].claims[0].body = "Rewritten interpretation"
        else:
            batch.checks[0].cursor = "changed-cursor"
        with pytest.raises(ValueError, match="[Ii]mmutable"):
            apply(batch)
    # A genuine replay is a no-op and remains supported.
    before = service.state(owner)
    apply(recorded_batch(INSTRUMENT, 0))
    assert service.state(owner)["documents"] == before["documents"]


def test_method_change_reassesses_without_manufacturing_source_update(
    owner, monkeypatch
):
    saved(owner)
    drain(owner)
    monkeypatch.setattr(service, "LEGACY_VERSION", "new-test-method")
    drain(owner)
    data = service.state(owner)
    assert len(data["versions"][0]["evaluations"]) == 2
    assert data["changes"] == []


def test_other_company_pending_work_is_visible(owner):
    service.save_idea(owner, aurora_payload())
    assert service.state(owner)["jobs"] == []
    assert service.state(owner)["pending_work"] is True
    drain(owner)
    assert service.state(owner)["pending_work"] is False
