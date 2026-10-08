from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4
import json
import pytest
import psycopg
from pydantic import ValidationError
from thesis import service, review_export
from thesis.db import transaction, one
from thesis.models import SaveIdea, EventCondition
from thesis.monitoring.events import assess, boundaries, window_state
from thesis.research import event_review
from thesis.providers import ledger
from test_integration import payload, drain
from test_model_budget import response


def event(**kw):
    return (
        dict(
            condition_id=str(uuid4()),
            description="The product becomes available",
            evidence_requirement="A report explicitly confirms a completed launch, not a plan.",
            role="required",
            window_start="2025-01-01",
            deadline="2026-12-31",
        )
        | kw
    )


def save(owner, events=None, revision=0, **kw):
    p = (
        payload(revision=revision, conditions=False).model_dump()
        | dict(events=events or [event()])
        | kw
    )
    return service.save_idea(owner, SaveIdea(**p))


def packet(owner, saved):
    sid = service.state(owner)["snapshot_id"]
    with transaction(owner) as conn:
        return event_review.prepare(conn, owner, saved["version_id"], sid)


def wire(packet, status="uncertain", **kw):
    findings = []
    for e in packet["events"]:
        source = next(
            (s for s in packet["sources"] if s["id"] in e["eligible_source_ids"]), None
        )
        citations = (
            [dict(source_id=source["id"], passage_id=source["passages"][0]["id"])]
            if source
            else []
        )
        findings.append(
            dict(
                condition_id=e["condition_id"],
                status=status,
                explanation="Authored mocked interpretation; not real event verification.",
                citations=citations,
            )
        )
    return (
        response()
        | dict(
            model=event_review.REASONING_MODEL,
            output=[
                dict(
                    type="message",
                    content=[
                        dict(type="output_text", text=json.dumps(dict(events=findings)))
                    ],
                )
            ],
        )
        | kw
    )


@pytest.mark.parametrize(
    "role,status,outcome,state",
    [
        ("required", "confirmed", "met", "confirmed"),
        ("risk", "confirmed", "not_met", "risk_reported"),
        ("risk", "denied_report", "unknown", "denied_report"),
        ("required", "uncertain", "unknown", "uncertain"),
        ("required", "conflicting", "unknown", "conflicting"),
    ],
)
def test_event_evidence_never_turns_denial_or_silence_into_safety(
    role, status, outcome, state
):
    e = event(role=role)
    r = dict(
        id=uuid4(),
        result=dict(
            events=[
                dict(
                    condition_id=e["condition_id"],
                    status=status,
                    explanation="Test",
                    citations=[],
                )
            ]
        ),
    )
    actual = assess([e], r, "2026-02-01T00:00:00Z")[0]
    assert (actual["outcome"], actual["state"]) == (outcome, state)
    if status != "confirmed":
        after = assess([e], r, "2027-01-01T00:00:00Z")[0]
        assert (
            after["outcome"] == "unknown" and after["state"] == "deadline_unconfirmed"
        )


def test_inclusive_utc_window_and_no_review():
    e = event(window_start="2026-02-01", deadline="2026-02-02")
    assert window_state(e, "2026-01-31T23:59:59.999999Z") == "not_started"
    assert window_state(e, "2026-02-02T23:59:59.999999Z") == "within_window"
    assert window_state(e, "2026-02-03T00:00:00Z") == "deadline_unconfirmed"
    assert [d.isoformat() for d in boundaries([e])] == [
        "2026-02-01T00:00:00+00:00",
        "2026-02-03T00:00:00+00:00",
    ]
    assert assess([e], None, "2026-02-03T00:00:00Z")[0]["outcome"] == "unknown"


@pytest.mark.parametrize(
    "changes",
    [
        dict(deadline="2024-01-01"),
        dict(description="   "),
        dict(role="buy"),
        dict(deadline="2090-01-01"),
    ],
)
def test_invalid_definition_rejected(changes):
    with pytest.raises(ValidationError):
        EventCondition(**event(**changes))


def test_event_only_approval_complete_immutable_history(owner):
    s = save(owner)
    drain(owner)
    before = service.state(owner)["versions"][0]
    assert (
        len(before["events"]) == 1
        and len(before["evaluations"][0]["event_results"]) == 1
    )
    assert (
        before["evaluations"][0]["results"] == []
        and before["evaluations"][0]["outcome"] == "unknown"
    )
    with pytest.raises(psycopg.errors.RaiseException):
        with transaction(owner) as c:
            c.execute(
                "INSERT INTO version_events SELECT owner_id,version_id,%s,description,evidence_requirement,role,window_start,deadline FROM version_events WHERE version_id=%s",
                (uuid4(), s["version_id"]),
            )
    save(owner, revision=1, events=[event(role="risk")])
    drain(owner)
    assert service.state(owner)["versions"][1] == before
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with transaction(owner) as c:
            c.execute("DELETE FROM version_events")


def test_window_excludes_sources_before_spending(owner):
    s = save(owner, events=[event(window_start="2040-01-01", deadline="2040-12-31")])
    before = ledger.snapshot()
    with pytest.raises(ValueError, match="No eligible reports"):
        event_review.generate(
            owner,
            s["version_id"],
            service.state(owner)["snapshot_id"],
            transport=lambda _: pytest.fail("must not dispatch"),
        )
    assert ledger.snapshot() == before


def test_mocked_event_review_cache_private_scope_and_export(owner):
    s = save(owner)
    p = packet(owner, s)
    out = event_review.generate(
        owner,
        s["version_id"],
        p["snapshot_id"],
        transport=lambda _: wire(p, "confirmed"),
    )
    drain(owner)
    v = service.state(owner)["versions"][0]
    e = v["evaluations"][0]
    assert e["event_results"][0]["state"] == "confirmed" and e["outcome"] == "met"
    assert out["id"] == e["manifest"]["event_review_id"]
    before = ledger.snapshot()
    assert (
        event_review.generate(
            owner,
            s["version_id"],
            p["snapshot_id"],
            transport=lambda _: pytest.fail("cache"),
        )
        == out
    )
    assert ledger.snapshot() == before
    _, html = review_export.download(owner, s["version_id"], evaluation_id=e["id"])
    assert (
        "Event evidence" in html
        and "completed launch" in html
        and out["events"][0]["citations"][0]["quote"] in html
    )
    _, standalone = review_export.download(
        owner, s["version_id"], event_review_id=out["id"]
    )
    assert "Saved event evidence check" in standalone
    with transaction(str(uuid4())) as c:
        assert one(c, "SELECT count(*) n FROM event_evidence_reviews")["n"] == 0
    with pytest.raises(service.Missing):
        review_export.download(str(uuid4()), s["version_id"], event_review_id=out["id"])


def test_missing_duplicate_wrong_window_and_wrong_passage_findings_rejected(owner):
    s = save(
        owner, events=[event(), event(window_start="2040-01-01", deadline="2040-12-31")]
    )
    p = packet(owner, s)

    def call(points):
        r = wire(p)
        r["output"][0]["content"][0]["text"] = json.dumps(dict(events=points))
        return dict(response_body=r, model="mock", purpose="mock")

    points = json.loads(wire(p)["output"][0]["content"][0]["text"])["events"]
    for bad in [points[:1], [points[0], points[0]]]:
        with pytest.raises(ValueError, match="each saved condition"):
            event_review.render(call(bad), p)
    eligible = next(x for x in points if x["citations"])
    future = next(x for x in points if not x["citations"])
    bad = deepcopy(points)
    next(x for x in bad if x["condition_id"] == future["condition_id"])["citations"] = (
        eligible["citations"]
    )
    with pytest.raises(ValueError, match="outside"):
        event_review.render(call(bad), p)
    bad = deepcopy(points)
    next(x for x in bad if x["citations"])["citations"][0]["passage_id"] = "invented"
    with pytest.raises(ValueError, match="original passage"):
        event_review.render(call(bad), p)
    bad = deepcopy(points)
    bad[0]["status"] = "confirmed"
    bad[0]["citations"] = []
    with pytest.raises(ValueError, match="requires supporting"):
        event_review.render(call(bad), p)


def test_late_result_stays_on_original_revision(owner):
    s = save(owner)
    p = packet(owner, s)

    def transport(_):
        save(owner, revision=1, events=[event(role="risk")])
        return wire(p, "confirmed")

    result = event_review.generate(
        owner, s["version_id"], p["snapshot_id"], transport=transport
    )
    drain(owner)
    versions = service.state(owner)["versions"]
    assert (
        versions[0]["event_reviews"] == []
        and versions[0]["evaluations"][0]["outcome"] == "unknown"
    )
    assert versions[1]["event_reviews"][0]["id"] == result["id"]


def test_new_snapshot_needs_explicit_check_and_deadline_catches_up(owner):
    # Recorded clock begins 2025-10-24 and then advances past this report window.
    info = service.state(owner)["demo"]
    start = info["as_of"][:10]
    from datetime import date, timedelta

    end = (date.fromisoformat(start) + timedelta(days=1)).isoformat()
    s = save(owner, events=[event(window_start=start, deadline=end)])
    drain(owner)
    before = service.state(owner)
    service.advance(owner, 0)
    drain(owner)
    after = service.state(owner)
    assert any(
        r["state"] == "deadline_unconfirmed"
        for e in after["versions"][0]["evaluations"]
        for r in e["event_results"]
    )
    assert any(c["kind"] == "event" for c in after["changes"])
    drain(owner)
    assert service.state(owner)["versions"] == after["versions"]


def test_scoped_event_interpretation_hides_revoked_quotes():
    point = dict(
        condition_id="a",
        status="confirmed",
        explanation="Sensitive interpretation",
        citations=[dict(source_id="x", quote="Sensitive quote")],
    )
    scoped = event_review.scoped_point(point, set())
    assert (
        scoped["outcome"] == "unknown"
        and scoped["withheld"]
        and scoped["citations"] == []
    )
    assert "Sensitive" not in str(scoped)


def test_new_evidence_does_not_inherit_confirmation(owner):
    s = save(owner)
    p = packet(owner, s)
    event_review.generate(
        owner,
        s["version_id"],
        p["snapshot_id"],
        transport=lambda _: wire(p, "confirmed"),
    )
    drain(owner)
    before = service.state(owner)["versions"][0]["evaluations"][0]
    assert before["outcome"] == "met"
    service.advance(owner, 0)
    drain(owner)
    after = service.state(owner)["versions"][0]
    assert after["evaluations"][0]["outcome"] == "unknown"
    assert after["evaluations"][0]["manifest"]["event_review_id"] is None
    assert next(e for e in after["evaluations"] if e["id"] == before["id"]) == before


def test_mixed_conditions_require_complete_results(owner):
    p = payload().model_dump() | dict(events=[event(role="risk")])
    s = service.save_idea(owner, SaveIdea(**p))
    drain(owner)
    v = service.state(owner)["versions"][0]
    assert len(v["evaluations"][0]["results"]) == 2
    assert len(v["evaluations"][0]["event_results"]) == 1
    assert v["evaluations"][0]["outcome"] == "unknown"
    p = packet(owner, s)
    event_review.generate(
        owner,
        s["version_id"],
        p["snapshot_id"],
        transport=lambda _: wire(p, "confirmed"),
    )
    drain(owner)
    e = service.state(owner)["versions"][0]["evaluations"][0]
    assert all(r["outcome"] == "met" for r in e["results"])
    assert (
        e["outcome"] == "not_met" and e["event_results"][0]["state"] == "risk_reported"
    )


def test_revoked_source_hides_event_interpretation_and_overall_status(
    owner, monkeypatch
):
    s = save(owner)
    p = packet(owner, s)
    review = event_review.generate(
        owner,
        s["version_id"],
        p["snapshot_id"],
        transport=lambda _: wire(p, "confirmed"),
    )
    drain(owner)
    cited = review["events"][0]["citations"][0]["source_id"]
    original = service.permitted_documents
    monkeypatch.setattr(
        service,
        "permitted_documents",
        lambda *a, **kw: [d for d in original(*a, **kw) if str(d["id"]) != cited],
    )
    data = service.state(owner)
    v = data["versions"][0]
    e = v["evaluations"][0]
    assert e["outcome"] == "unknown" and e["event_results"][0]["withheld"]
    assert v["event_reviews"][0]["events"][0]["citations"] == []
    _, html = review_export.download(owner, s["version_id"], evaluation_id=e["id"])
    assert "Historical interpretation withheld" in html


def test_max_date_does_not_overflow_scheduler():
    with pytest.raises(ValidationError):
        EventCondition(**event(window_start="9999-01-01", deadline="9999-12-31"))
