"""Finite recurring event windows, quiet clocks and historical-only late checks."""

from copy import deepcopy
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import json
import pytest
from pydantic import ValidationError
from thesis import service, review_export
from thesis.db import transaction, one
from thesis.models import EventCondition, EventReviewRequest, SaveIdea
from thesis.monitoring.event_windows import windows, current
from thesis.monitoring.events import assess, boundaries
from thesis.research import event_review as E, proposals
from thesis.providers import ledger
from test_event_conditions import event, wire, save, packet
from test_integration import payload, drain
from test_market import prepare, commit, news
from test_event_occurrence import result as dated_result


def recurring(**kw):
    return event(
        window_start="2026-01-31",
        deadline="2026-01-31",
        repeat_months=1,
        repeat_count=4,
        **kw,
    )


def test_month_end_is_anchored_and_does_not_drift():
    e = recurring()
    assert [w["window_start"] for w in windows(e)] == [
        "2026-01-31",
        "2026-02-28",
        "2026-03-31",
        "2026-04-30",
    ]
    assert current(e, "2026-02-27T23:59:59Z")["index"] == 1
    assert current(e, "2026-02-28T00:00:00Z")["index"] == 2
    e = event(
        window_start="2024-02-29",
        deadline="2024-02-29",
        repeat_months=12,
        repeat_count=5,
    )
    assert [w["deadline"] for w in windows(e)] == [
        "2024-02-29",
        "2025-02-28",
        "2026-02-28",
        "2027-02-28",
        "2028-02-29",
    ]


@pytest.mark.parametrize(
    "changes",
    [
        dict(repeat_months=2),
        dict(repeat_months=True),
        dict(repeat_count=1),
        dict(repeat_count=13),
        dict(repeat_months=0),
        dict(deadline="2026-02-28"),
        dict(repeat_months=12, repeat_count=12),
    ],
)
def test_invalid_overlapping_or_unbounded_schedules_rejected(changes):
    with pytest.raises(ValidationError):
        EventCondition(**(recurring() | changes))


def test_boundaries_and_results_reset_independently_of_network():
    e = event(
        window_start="2026-01-01",
        deadline="2026-03-31",
        repeat_months=3,
        repeat_count=4,
    )
    assert [x.isoformat()[:10] for x in boundaries([e])] == [
        "2026-01-01",
        "2026-04-01",
        "2026-07-01",
        "2026-10-01",
        "2027-01-01",
    ]
    # Original-anchor day 31 clamps June; March31+6 months is September30.
    review = dict(
        id=str(uuid4()),
        result=dict(
            events=[
                dict(
                    condition_id=e["condition_id"],
                    window=windows(e)[0],
                    status="confirmed",
                    explanation="Authored report",
                    citations=[],
                )
            ]
        ),
    )
    assert assess([e], review, "2026-03-31T23:59:59Z")[0]["outcome"] == "met"
    next_period = assess([e], review, "2026-04-01T00:00:00Z")[0]
    assert (
        next_period["outcome"] == "unknown"
        and next_period["review_id"] is None
        and next_period["citations"] == []
        and next_period["window"]["index"] == 2
    )
    assert current(e, "2028-01-01T00:00:00Z")["index"] == 4


def setup(owner, *, occurrence=False):
    iid = prepare(owner)
    today = datetime.now(timezone.utc).date()
    first = today.replace(day=1)
    e = event(
        window_start=first.isoformat(),
        deadline=today.isoformat(),
        repeat_months=1,
        repeat_count=3,
        date_basis="event_occurrence" if occurrence else "report_publication",
    )
    if occurrence:
        commit(
            iid,
            [
                news(
                    headline="Completed launch",
                    summary=f"The product launched on {today.isoformat()}.",
                )
            ],
        )
    sv = service.save_idea(
        owner,
        SaveIdea(
            **(
                payload(conditions=False).model_dump()
                | dict(instrument_id=iid, events=[e])
            )
        ),
    )
    drain(owner)
    return iid, sv, e


def prepare_for(owner, sv, iid, **kw):
    with transaction(owner) as c:
        return E.prepare(
            c, owner, sv["version_id"], service.state(owner, iid)["snapshot_id"], **kw
        )


def test_clock_rollover_creates_reviewable_unknown_without_paid_call(owner):
    iid, sv, e = setup(owner)
    p = prepare_for(owner, sv, iid)
    E.generate(
        owner,
        sv["version_id"],
        p["snapshot_id"],
        transport=lambda _: wire(p, "confirmed"),
    )
    drain(owner)
    v = service.state(owner, iid)["versions"][0]
    old = v["evaluations"][0]
    assert old["outcome"] == "met" and old["event_results"][0]["window"]["index"] == 1
    clock = datetime.fromisoformat(windows(e)[1]["window_start"] + "T00:00:00+00:00")
    before = ledger.snapshot()
    service.queue_current(owner, now=clock)
    drain(owner)
    state = service.state(owner, iid)
    new = state["versions"][0]["evaluations"][0]
    assert (
        new["outcome"] == "unknown"
        and new["event_results"][0]["window"]["index"] == 2
        and new["manifest"]["event_review_id"] is None
    )
    assert ledger.snapshot() == before
    assert (
        next(x for x in state["versions"][0]["evaluations"] if x["id"] == old["id"])
        == old
    )
    assert any(
        c["details"].get("affected_events", [{}])[0].get("window", {}).get("index") == 2
        for c in state["changes"]
        if c["details"].get("affected_events")
    )
    service.queue_current(owner, now=clock)
    drain(owner)
    assert (
        service.state(owner, iid)["versions"][0]["evaluations"]
        == state["versions"][0]["evaluations"]
    )
    _, html = review_export.download(owner, sv["version_id"], evaluation_id=new["id"])
    assert "Checked window 2 of 3" in html


def test_same_snapshot_reuse_cannot_cross_periods_or_private_owners(owner):
    iid, sv, e = setup(owner, occurrence=True)
    p = prepare_for(owner, sv, iid)
    today = datetime.now(timezone.utc).date().isoformat()
    out = E.generate(
        owner,
        sv["version_id"],
        p["snapshot_id"],
        transport=lambda _: dated_result(p, today),
    )
    drain(owner)
    later = windows(e)[1]["window_start"] + "T00:00:00+00:00"
    with transaction(owner) as c:
        later_packet = E.prepare(
            c, owner, sv["version_id"], p["snapshot_id"], clock=later
        )
        assert E.reusable(
            c, owner, sv["version_id"], p["snapshot_id"], clock=later
        ) == (None, None)
    assert E.identity(owner, p) != E.identity(
        owner, later_packet
    ) and E.scope_signature(p) != E.scope_signature(later_packet)
    assert E.identity(owner, p) != E.identity(str(uuid4()), p)
    assert out["events"][0]["window"]["index"] == 1


def test_past_window_check_retained_but_cannot_replace_current_period(owner):
    iid, sv, e = setup(owner, occurrence=True)
    sid = service.state(owner, iid)["snapshot_id"]
    later = windows(e)[1]["window_start"] + "T00:00:00+00:00"
    service.queue_current(owner, now=later)
    drain(owner)
    before = service.state(owner, iid)["versions"][0]["evaluations"][0]
    with transaction(owner) as c:
        p = E.prepare(
            c,
            owner,
            sv["version_id"],
            sid,
            clock=later,
            event_periods={e["condition_id"]: 1},
        )
    assert p["historical_windows"]
    today = datetime.now(timezone.utc).date().isoformat()
    out = E.generate(
        owner,
        sv["version_id"],
        sid,
        clock=later,
        event_periods={e["condition_id"]: 1},
        transport=lambda _: dated_result(p, today),
    )
    drain(owner)
    assert out["historical_window_check"] and not out["applied_to_monitoring"]
    assert service.state(owner, iid)["versions"][0]["evaluations"][0] == before
    _, html = review_export.download(owner, sv["version_id"], event_review_id=out["id"])
    assert "Checked window 1 of 3" in html and "earlier-window check" in html
    before_budget = ledger.snapshot()
    again = E.generate(
        owner,
        sv["version_id"],
        sid,
        clock=later,
        event_periods={e["condition_id"]: 1},
        transport=lambda _: pytest.fail("already checked"),
    )
    assert again["id"] == out["id"] and ledger.snapshot() == before_budget


def test_invalid_or_future_period_rejected_before_dispatch(owner):
    iid, sv, e = setup(owner)
    sid = service.state(owner, iid)["snapshot_id"]
    before = ledger.snapshot()
    for selected in (
        {e["condition_id"]: 2},
        {e["condition_id"]: 20},
        {str(uuid4()): 1},
    ):
        with pytest.raises(ValueError):
            E.generate(
                owner,
                sv["version_id"],
                sid,
                event_periods=selected,
                transport=lambda _: pytest.fail("must not dispatch"),
            )
    assert ledger.snapshot() == before
    for bad in (True, 0, 13, "1"):
        with pytest.raises(ValidationError):
            EventReviewRequest(snapshot_id=sid, event_periods={e["condition_id"]: bad})


def test_complete_schedule_and_original_approval_survive_suggestion_update(owner):
    sv = save(
        owner,
        events=[
            event(
                window_start="2025-10-01",
                deadline="2025-10-10",
                repeat_months=3,
                repeat_count=4,
            )
        ],
    )
    with transaction(owner) as c:
        base = proposals.base_definition(
            c, owner, "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", sv["version_id"]
        )
    old = base["events"][0]
    definition = {
        k: v
        for k, v in old.items()
        if k not in ("condition_id", "repeat_months", "repeat_count")
    }
    proposed = dict(
        id=str(uuid4()),
        kind="event",
        operation="update",
        target_condition_id=old["condition_id"],
        proposed=dict(definition=definition),
    )
    new = proposals.apply_change(base, proposed)["events"][0]
    assert new["repeat_months"] == 3 and new["repeat_count"] == 4


def test_wrong_window_selected_quote_does_not_inherit_previous_confirmation():
    e = recurring()
    review = dict(
        id=str(uuid4()),
        result=dict(
            events=[
                dict(
                    condition_id=e["condition_id"],
                    status="confirmed",
                    window=windows(e)[0],
                    explanation="Old report",
                    citations=[dict(source_id="old", quote="Old report")],
                )
            ]
        ),
    )
    current_point = assess([e], review, "2026-02-28T00:00:00Z")[0]
    assert (
        current_point["outcome"] == "unknown"
        and current_point["citations"] == []
        and current_point["review_id"] is None
    )


def test_delayed_response_at_rollover_is_history_only(owner, monkeypatch):
    iid, sv, e = setup(owner, occurrence=True)
    p = prepare_for(owner, sv, iid)
    initial = service.state(owner, iid)["versions"][0]["evaluations"][0]
    later = datetime.fromisoformat(windows(e)[1]["window_start"] + "T00:00:00+00:00")
    real_datetime = E.datetime

    class Later(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return later

    def send(_):
        monkeypatch.setattr(E, "datetime", Later)
        return dated_result(p, datetime.now(timezone.utc).date().isoformat())

    result = E.generate(owner, sv["version_id"], p["snapshot_id"], transport=send)
    assert result["period_elapsed"] and not result["applied_to_monitoring"]
    drain(owner)
    assert service.state(owner, iid)["versions"][0]["evaluations"][0] == initial


def test_clock_catchup_preserves_each_window_and_default_manifest_shape(owner):
    iid, sv, e = setup(owner)
    p = prepare_for(owner, sv, iid)
    before = ledger.snapshot()
    last = windows(e)[-1]["deadline"] + "T23:59:59+00:00"
    service.queue_current(owner, now=last)
    drain(owner)
    versions = service.state(owner, iid)["versions"]
    indices = {
        x["event_results"][0]["window"]["index"] for x in versions[0]["evaluations"]
    }
    assert indices == {1, 2, 3} and ledger.snapshot() == before
    ordinary = save(owner)
    drain(owner)
    with transaction(owner) as c:
        manifest = service.manifest_for(c, owner, ordinary["version_id"])
    assert (
        "repeat_months" not in manifest["events"][0]
        and "repeat_count" not in manifest["events"][0]
    )
    assert "window" not in manifest["event_windows"][0]


def test_api_period_override_uses_membership_validation_without_paid_work(
    owner, monkeypatch
):
    from fastapi.testclient import TestClient
    from thesis import app as app_module

    iid, sv, e = setup(owner)
    monkeypatch.setattr(app_module, "OWNER", owner)
    sid = service.state(owner, iid)["snapshot_id"]
    before = ledger.snapshot()
    with TestClient(app_module.app) as client:
        client.get("/api/v1/session")
        response = client.post(
            f'/api/v1/ideas/versions/{sv["version_id"]}/event-review',
            headers={"x-thesis-request": "local-ui"},
            json=dict(snapshot_id=sid, event_periods={str(uuid4()): 1}),
        )
    assert (
        response.status_code == 422
        and "recurring condition" in response.text
        and ledger.snapshot() == before
    )


def test_fiscal_quarter_end_stays_at_month_end():
    e = event(
        window_start="2026-07-01",
        deadline="2026-09-30",
        repeat_months=3,
        repeat_count=4,
    )
    assert [x["deadline"] for x in windows(e)] == [
        "2026-09-30",
        "2026-12-31",
        "2027-03-31",
        "2027-06-30",
    ]
    e = event(
        window_start="2026-01-30",
        deadline="2026-01-30",
        repeat_months=1,
        repeat_count=3,
    )
    assert [x["deadline"] for x in windows(e)] == [
        "2026-01-30",
        "2026-02-28",
        "2026-03-30",
    ]
