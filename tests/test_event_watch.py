"""Opt-in approved events, shared acquisition and immutable reuse; mocked providers."""

from datetime import datetime, timezone, timedelta
from copy import deepcopy
from uuid import uuid4
import json
import pytest
import psycopg
from fastapi.testclient import TestClient
from thesis import service, review_export
from thesis.db import transaction, one, rows
from thesis.models import SaveIdea
from thesis.providers import ledger
from thesis.monitoring import news_watch, event_watch, watch_history
from thesis.research import event_review, sentiment
from test_event_conditions import event, wire
from test_integration import payload, drain
from test_market import prepare, commit, news
from test_sentiment import provider


def setup(owner, *, role="required", status="monitoring", **event_fields):
    iid = prepare(owner)
    article = news(
        headline="Microsoft announces the product is generally available.",
        summary="Authored fixture: Microsoft says this product launch is complete.",
    )
    commit(iid, [article])
    p = payload(conditions=False, status=status).model_dump() | dict(
        instrument_id=iid, events=[event(role=role, **event_fields)]
    )
    saved = service.save_idea(owner, SaveIdea(**p))
    drain(owner)
    news_watch.configure(
        owner, iid, True, now=datetime.now(timezone.utc) - timedelta(minutes=61)
    )
    return iid, saved, article


def select(owner, iid, saved):
    return event_watch.configure(owner, iid, saved["version_id"])


def due(owner, iid):
    with transaction(owner) as c:
        c.execute(
            "UPDATE news_watches SET next_check_at=now()-interval '1 minute' WHERE owner_id=%s AND instrument_id=%s",
            (owner, iid),
        )


def model(owner, saved, status="confirmed", before=None):
    def transport(_):
        with transaction(owner) as c:
            sid = one(
                c,
                "SELECT max(id) id FROM research_snapshots WHERE instrument_id=(SELECT instrument_id FROM theses WHERE id=(SELECT thesis_id FROM thesis_versions WHERE id=%s))",
                (saved["version_id"],),
            )["id"]
            packet = event_review.prepare(c, owner, saved["version_id"], sid)
        if before:
            before()
        return wire(packet, status)

    return transport


def run(owner, iid, saved, *, status="confirmed", before=None, transport=None):
    return news_watch.run_once(
        owner,
        market_refresh=lambda _: None,
        social_refresh=lambda: None,
        analyzer=lambda i: sentiment.generate(i, transport=provider()),
        event_analyzer=lambda o, i, v, t: event_watch.run(
            o, i, v, t, transport=transport or model(owner, saved, status, before)
        ),
    )


def event_calls(owner):
    with transaction(owner) as c:
        return one(
            c,
            "SELECT count(*) n FROM model_calls WHERE owner_id=%s AND purpose=%s",
            (owner, event_review.PROMPT),
        )["n"]


@pytest.mark.parametrize(
    "role,status,outcome",
    [
        ("required", "confirmed", "met"),
        ("risk", "confirmed", "not_met"),
        ("risk", "denied_report", "unknown"),
        ("required", "uncertain", "unknown"),
    ],
)
def test_scheduled_event_check_reaches_exact_condition_and_updates(
    owner, role, status, outcome
):
    iid, saved, _ = setup(owner, role=role)
    select(owner, iid, saved)
    assert run(owner, iid, saved, status=status)
    drain(owner)
    state = service.state(owner, iid)
    e = state["versions"][0]["evaluations"][0]
    assert e["outcome"] == outcome and e["event_results"][0]["review_id"]
    assert state["versions"][0]["event_reviews"][0]["applied_to_monitoring"]
    check = watch_history.history(owner, iid)["items"][0]
    assert (
        check["event_version_id"] == saved["version_id"]
        and check["details"]["events"] == "checked"
    )
    assert event_calls(owner) == 1
    if outcome != "unknown":
        assert any(c["kind"] == "event" for c in state["changes"])
    _, html = review_export.download(owner, saved["version_id"], evaluation_id=e["id"])
    assert e["event_results"][0]["citations"][0]["quote"] in html


def test_unchanged_snapshot_reuses_exact_inputs_no_new_charge_or_alert(owner):
    iid, saved, article = setup(owner)
    select(owner, iid, saved)
    run(owner, iid, saved)
    drain(owner)
    old = service.state(owner, iid)
    original = old["versions"][0]["evaluations"][0]
    count = len(old["changes"])
    commit(iid, [article])
    new_sid = service.state(owner, iid)["snapshot_id"]
    assert new_sid != original["manifest"]["snapshot_id"]
    with transaction(owner) as c:
        manifest = service.manifest_for(c, owner, saved["version_id"])
    assert manifest["event_review_id"] == original["manifest"]["event_review_id"]
    assert (
        manifest["event_review_reuse"]["original_snapshot_id"]
        == original["manifest"]["snapshot_id"]
    )
    due(owner, iid)
    assert run(
        owner,
        iid,
        saved,
        transport=lambda _: pytest.fail("Identical event inputs dispatched"),
    )
    drain(owner)
    current = service.state(owner, iid)
    assert event_calls(owner) == 1 and len(current["changes"]) == count
    assert current["versions"][0]["evaluations"][0]["outcome"] == "met"
    assert (
        watch_history.history(owner, iid)["items"][0]["details"]["events"] == "reused"
    )
    assert (
        next(
            e
            for e in current["versions"][0]["evaluations"]
            if e["id"] == original["id"]
        )
        == original
    )


def test_changed_source_requires_new_check_and_stores_new_original_quotes(owner):
    iid, saved, article = setup(owner)
    select(owner, iid, saved)
    run(owner, iid, saved)
    drain(owner)
    commit(
        iid,
        [
            article
            | dict(
                summary="Authored correction: the product is a preview; general availability is planned."
            )
        ],
    )
    with transaction(owner) as c:
        assert (
            service.manifest_for(c, owner, saved["version_id"])["event_review_id"]
            is None
        )
    due(owner, iid)
    run(owner, iid, saved, status="uncertain")
    drain(owner)
    assert event_calls(owner) == 2
    version = service.state(owner, iid)["versions"][0]
    assert (
        version["evaluations"][0]["outcome"] == "unknown"
        and len(version["event_reviews"]) == 2
    )


@pytest.mark.parametrize(
    "change", ["stop_events", "stop_watch", "edit", "new_snapshot", "expired"]
)
def test_late_automatic_result_is_historical_and_never_applied(owner, change):
    iid, saved, article = setup(owner)
    select(owner, iid, saved)

    def alter():
        if change == "stop_events":
            event_watch.configure(owner, iid, None)
        if change == "stop_watch":
            news_watch.configure(owner, iid, False)
        if change == "edit":
            p = payload(revision=1, conditions=False).model_dump() | dict(
                instrument_id=iid, events=[event(role="risk")]
            )
            service.save_idea(owner, SaveIdea(**p))
        if change == "new_snapshot":
            commit(iid, [article])
        if change == "expired":
            with transaction(owner) as c:
                c.execute(
                    "UPDATE news_watches SET lease_until=now()-interval '1 second' WHERE owner_id=%s AND instrument_id=%s",
                    (owner, iid),
                )

    run(owner, iid, saved, before=alter)
    drain(owner)
    with transaction(owner) as c:
        review = one(
            c, "SELECT * FROM event_evidence_reviews WHERE owner_id=%s", (owner,)
        )
        assert review["automatic"]
        assert (
            one(
                c,
                "SELECT count(*) n FROM event_review_activations WHERE owner_id=%s",
                (owner,),
            )["n"]
            == 0
        )
    state = service.state(owner, iid)
    assert state["versions"][0]["evaluations"][0]["outcome"] == "unknown"
    old = next(v for v in state["versions"] if str(v["id"]) == saved["version_id"])
    assert not old["event_reviews"][0]["applied_to_monitoring"]
    assert not any(
        e["manifest"]["event_review_id"] == str(review["id"])
        for v in state["versions"]
        for e in v["evaluations"]
    )


def test_manual_request_can_apply_completed_stopped_result_without_repaying(owner):
    iid, saved, _ = setup(owner)
    select(owner, iid, saved)
    run(owner, iid, saved, before=lambda: event_watch.configure(owner, iid, None))
    with transaction(owner) as c:
        row = one(c, "SELECT * FROM event_evidence_reviews WHERE owner_id=%s", (owner,))
    before = ledger.snapshot()
    record = event_review.generate(
        owner,
        saved["version_id"],
        row["snapshot_id"],
        transport=lambda _: pytest.fail("Cached result dispatched"),
    )
    drain(owner)
    assert record["applied_to_monitoring"] and ledger.snapshot() == before
    assert (
        service.state(owner, iid)["versions"][0]["evaluations"][0]["outcome"] == "met"
    )


def test_no_eligible_window_and_changed_approval_do_not_dispatch(owner):
    iid, saved, _ = setup(owner, window_start="2040-01-01", deadline="2040-12-31")
    select(owner, iid, saved)
    run(owner, iid, saved, transport=lambda _: pytest.fail("No eligible source"))
    assert (
        watch_history.history(owner, iid)["items"][0]["details"]["events"]
        == "no_eligible_evidence"
    )
    p = payload(revision=1, conditions=False).model_dump() | dict(
        instrument_id=iid, events=[event()]
    )
    newer = service.save_idea(owner, SaveIdea(**p))
    due(owner, iid)
    run(
        owner,
        iid,
        newer,
        transport=lambda _: pytest.fail("Changed approval dispatched"),
    )
    assert (
        watch_history.history(owner, iid)["items"][0]["details"]["events"]
        == "approval_changed"
    )
    assert event_calls(owner) == 0


def test_failed_model_is_recorded_not_silently_retried(owner):
    iid, saved, _ = setup(owner)
    select(owner, iid, saved)
    run(
        owner,
        iid,
        saved,
        transport=lambda _: dict(
            status="incomplete", output=[], usage=dict(input_tokens=10, output_tokens=1)
        ),
    )
    h = watch_history.history(owner, iid)["items"][0]
    assert (
        h["status"] == "failed"
        and h["details"]["failed_stage"] == "approved event analysis"
    )
    assert not news_watch.run_once(owner)
    assert not service.state(owner, iid)["versions"][0]["event_reviews"]


def test_optin_validation_owner_and_immutable_activation(owner, monkeypatch):
    iid, saved, _ = setup(owner, status="draft")
    with pytest.raises(service.Conflict):
        select(owner, iid, saved)
    p = payload(revision=1, conditions=False).model_dump() | dict(
        instrument_id=iid, events=[event()]
    )
    approved = service.save_idea(owner, SaveIdea(**p))
    select(owner, iid, approved)
    from thesis import app as web

    monkeypatch.setattr(web, "OWNER", owner)
    client = TestClient(web.app)
    url = f"/api/v1/companies/{iid}/event-watch"
    assert (
        client.post(url, json=dict(version_id=approved["version_id"])).status_code
        == 401
    )
    client.get("/api/v1/session")
    assert (
        client.post(url, json=dict(version_id=approved["version_id"])).status_code
        == 403
    )
    h = {"x-thesis-request": "local-ui"}
    assert (
        client.post(
            url, headers=h, json=dict(version_id=saved["version_id"])
        ).status_code
        == 409
    )
    assert (
        client.post(
            url, headers=h, json=dict(version_id=approved["version_id"], owner_id=owner)
        ).status_code
        == 422
    )
    assert (
        client.post(
            url, headers=h, json=dict(version_id=approved["version_id"])
        ).status_code
        == 200
    )
    run(owner, iid, approved)
    with transaction(str(uuid4())) as c:
        assert one(c, "SELECT count(*) n FROM event_review_activations")["n"] == 0
    with pytest.raises(psycopg.Error):
        with transaction(owner) as c:
            c.execute("DELETE FROM event_review_activations")
    with pytest.raises(psycopg.Error):
        with transaction(source=True) as c:
            c.execute("SELECT * FROM event_review_activations")


def test_reuse_proof_rejects_definition_source_and_snapshot_changes(owner):
    iid, saved, article = setup(owner)
    select(owner, iid, saved)
    run(owner, iid, saved)
    commit(iid, [article])
    with transaction(owner) as c:
        m = service.manifest_for(c, owner, saved["version_id"])
        row = one(c, "SELECT * FROM event_evidence_reviews WHERE owner_id=%s", (owner,))
        proof = m["event_review_reuse"]
        assert event_review.validate_reuse(c, owner, row, m["snapshot_id"], proof)
        assert not event_review.validate_reuse(
            c, owner, row, m["snapshot_id"], proof | dict(input_signature="wrong")
        )
        for field in ("description", "evidence_requirement", "deadline", "role"):
            packet = deepcopy(row["packet"])
            packet["events"][0][field] = "changed"
            assert event_review.scope_signature(packet) != proof["input_signature"]
        packet = deepcopy(row["packet"])
        packet["sources"][0]["text"] += " Changed text."
        assert event_review.scope_signature(packet) != proof["input_signature"]
