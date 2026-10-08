"""Occurrence timing cannot borrow publication dates or bypass source scope."""

from copy import deepcopy
from datetime import date
from uuid import uuid4
import json
import pytest
from pydantic import ValidationError
from thesis import service, review_export
from thesis.db import transaction, one
from thesis.models import EventCondition, SaveIdea
from thesis.research import event_review as E, event_dates, proposals
from thesis.research.citations import source_passages
from thesis.providers import ledger
from test_event_conditions import event, save, packet
from test_integration import drain, payload
from test_model_budget import response
from test_market import prepare, commit, news


@pytest.mark.parametrize(
    "text,expected",
    [
        ("2024-02-29", "2024-02-29"),
        ("September 3, 2026", "2026-09-03"),
        ("3 September 2026", "2026-09-03"),
        ("Sept. 3rd, 2026", "2026-09-03"),
        ("2025-02-29", None),
        ("09/03/2026", None),
        ("September 2026", None),
        ("yesterday", None),
        ("September 3", None),
        ("2026", None),
        ("October 32, 2026", None),
        ("September 3, 2026 to October 3, 2026", None),
    ],
)
def test_exact_calendar_date_only(text, expected):
    actual = event_dates.exact_day(text)
    assert (actual.isoformat() if actual else None) == expected


def pure_packet(date_text="September 3, 2026", **fields):
    text = f"Microsoft reports that the named product became generally available on {date_text}."
    source = dict(
        id="own-source",
        title="Original company report",
        text=text,
        published_at="2026-10-02T01:00:00+00:00",
    )
    source["passages"] = source_passages(source["title"], text)[0]
    return dict(
        events=[
            event(
                condition_id="event",
                date_basis="event_occurrence",
                window_start="2026-09-01",
                deadline="2026-09-30",
                eligible_source_ids=["own-source"],
                **fields,
            )
        ],
        sources=[source],
    )


def result(packet, date_text="September 3, 2026", status="confirmed"):
    points = []
    for definition in packet["events"]:
        source = (
            next(
                s
                for s in packet["sources"]
                if s["id"] in definition["eligible_source_ids"]
                and date_text in s["text"]
            )
            if date_text
            else packet["sources"][0]
        )
        passage = (
            next(p for p in source["passages"] if date_text in p["quote"])
            if date_text
            else source["passages"][0]
        )
        cite = dict(source_id=source["id"], passage_id=passage["id"])
        points.append(
            dict(
                condition_id=definition["condition_id"],
                status=status,
                explanation="Mocked source interpretation.",
                citations=[cite],
                occurrence_dates=(
                    [dict(cite, date_text=date_text)]
                    if date_text and definition.get("date_basis") == "event_occurrence"
                    else []
                ),
            )
        )
    return response() | dict(
        model=E.REASONING_MODEL,
        output=[
            dict(
                type="message",
                content=[
                    dict(type="output_text", text=json.dumps(dict(events=points)))
                ],
            )
        ],
    )


def render(p, r):
    return E.render(dict(response_body=r, model="mock", purpose=E.OCCURRENCE_PROMPT), p)


@pytest.mark.parametrize(
    "stated,status,expected",
    [
        ("September 3, 2026", "confirmed", "confirmed"),
        ("August 3, 2026", "confirmed", "uncertain"),
        ("October 3, 2026", "confirmed", "uncertain"),
        ("September 2026", "confirmed", "uncertain"),
        ("yesterday", "confirmed", "uncertain"),
        ("September 3, 2026", "uncertain", "uncertain"),
        ("September 3, 2026", "conflicting", "conflicting"),
        ("September 3, 2026", "denied_report", "denied_report"),
    ],
)
def test_code_window_and_missing_dates_never_convert_plan_or_denial(
    stated, status, expected
):
    p = pure_packet(stated)
    out = render(p, result(p, stated, status))["events"][0]
    assert out["status"] == expected
    assert out["citations"][0]["quote"] == p["sources"][0]["text"]
    if status == "confirmed" and expected == "uncertain":
        assert "publication date is not substituted" in out["explanation"]


def test_date_missing_or_borrowed_from_other_source_is_not_confirmation():
    p = pure_packet()
    assert render(p, result(p, None))["events"][0]["status"] == "uncertain"
    raw = result(p)
    data = json.loads(raw["output"][0]["content"][0]["text"])
    data["events"][0]["occurrence_dates"][0]["source_id"] = "other-source"
    raw["output"][0]["content"][0]["text"] = json.dumps(data)
    with pytest.raises(ValueError, match="own cited passage"):
        render(p, raw)


def test_reject_invalid_basis_and_report_only_date_attachment():
    with pytest.raises(ValidationError):
        EventCondition(**event(date_basis="date_guessed"))
    p = pure_packet()
    p["events"].append(
        dict(p["events"][0], condition_id="report", date_basis="report_publication")
    )
    r = result(p)
    data = json.loads(r["output"][0]["content"][0]["text"])
    data["events"][1]["occurrence_dates"] = data["events"][0]["occurrence_dates"]
    r["output"][0]["content"][0]["text"] = json.dumps(data)
    with pytest.raises(ValueError, match="cannot acquire occurrence"):
        render(p, r)


def test_later_report_qualifies_for_earlier_event_and_preserves_history(owner):
    iid = prepare(owner)
    article = news(
        headline="Microsoft launch completed",
        summary="The named product became generally available on September 3, 2026.",
    )
    commit(iid, [article])
    ev = event(
        date_basis="event_occurrence", window_start="2026-09-01", deadline="2026-09-30"
    )
    sv = service.save_idea(
        owner,
        SaveIdea(
            **(
                payload(conditions=False).model_dump()
                | dict(instrument_id=iid, events=[ev])
            )
        ),
    )
    drain(owner)
    before = service.state(owner, iid)["versions"][0]["evaluations"][0]
    with transaction(owner) as c:
        p = E.prepare(
            c, owner, sv["version_id"], service.state(owner, iid)["snapshot_id"]
        )
    assert p["events"][0]["date_basis"] == "event_occurrence"
    review = E.generate(
        owner, sv["version_id"], p["snapshot_id"], transport=lambda _: result(p)
    )
    drain(owner)
    v = service.state(owner, iid)["versions"][0]
    assessment = v["evaluations"][0]
    assert (
        assessment["outcome"] == "met"
        and assessment["event_results"][0]["citations"][0]["occurrence_dates"][0][
            "date"
        ]
        == "2026-09-03"
    )
    assert next(e for e in v["evaluations"] if e["id"] == before["id"]) == before
    budget = ledger.snapshot()
    assert (
        E.generate(
            owner,
            sv["version_id"],
            p["snapshot_id"],
            transport=lambda _: pytest.fail("cached"),
        )["id"]
        == review["id"]
    )
    assert ledger.snapshot() == budget
    for options in (
        dict(evaluation_id=assessment["id"]),
        dict(event_review_id=review["id"]),
    ):
        _, html = review_export.download(owner, sv["version_id"], **options)
        assert (
            "Event happened 2026-09-01" in html
            and "Selected event date: September 3, 2026" in html
        )
    old = deepcopy(v["events"][0])
    updated = {
        k: old[k]
        for k in (
            "condition_id",
            "description",
            "evidence_requirement",
            "role",
            "window_start",
            "deadline",
        )
    }
    sv2 = service.save_idea(
        owner,
        SaveIdea(
            **(
                payload(revision=1, conditions=False).model_dump()
                | dict(instrument_id=iid, events=[updated])
            )
        ),
    )
    drain(owner)
    with transaction(owner) as c:
        with pytest.raises(E.NoEligibleEvidence):
            E.prepare(c, owner, sv2["version_id"], p["snapshot_id"])
    assert service.state(owner, iid)["versions"][1] == v


def test_default_meaning_does_not_change_legacy_manifest_or_request(owner):
    sv = save(owner)
    p = packet(owner, sv)
    assert "date_basis" not in p["events"][0] and E.method(p) == E.PROMPT
    with transaction(owner) as c:
        manifest = service.manifest_for(c, owner, sv["version_id"])
    assert "date_basis" not in manifest["events"][0]
    drain(owner)
    before = service.state(owner)["versions"][0]["evaluations"]
    service.queue_current(owner)
    drain(owner)
    assert service.state(owner)["versions"][0]["evaluations"] == before


def test_source_withdrawal_clears_selected_date(owner):
    p = pure_packet()
    point = render(p, result(p))["events"][0]
    out = E.scoped_point(point, set())
    assert (
        out["withheld"]
        and out["citations"] == []
        and "September" not in str(out)
        and "2026-09-03" not in str(out)
    )


def test_suggestion_update_preserves_occurrence_meaning(owner):
    sv = save(owner, events=[event(date_basis="event_occurrence")])
    with transaction(owner) as c:
        base = proposals.base_definition(
            c, owner, "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", sv["version_id"]
        )
    original = base["events"][0]
    definition = {
        k: v for k, v in original.items() if k not in ("condition_id", "date_basis")
    }
    definition["description"] = "A refined completed event criterion"
    proposed = dict(
        id=str(uuid4()),
        kind="event",
        operation="update",
        target_condition_id=original["condition_id"],
        proposed=dict(definition=definition),
    )
    candidate = proposals.apply_change(base, proposed)
    assert candidate["events"][0]["date_basis"] == "event_occurrence"
    assert base["events"][0] == original


@pytest.mark.parametrize("role,expected", [("required", "met"), ("risk", "not_met")])
def test_occurrence_watch_applies_exact_dates_and_reuses_without_new_charge(
    owner, role, expected
):
    from test_event_watch import setup, select, run, due

    iid, sv, article = setup(
        owner,
        role=role,
        date_basis="event_occurrence",
        window_start="2026-09-01",
        deadline="2026-09-30",
    )
    article["summary"] = (
        "The named product became generally available on September 3, 2026."
    )
    commit(iid, [article])
    select(owner, iid, sv)

    def transport(_):
        with transaction(owner) as c:
            p = E.prepare(
                c, owner, sv["version_id"], service.state(owner, iid)["snapshot_id"]
            )
        return result(p)

    run(owner, iid, sv, transport=transport)
    drain(owner)
    state = service.state(owner, iid)
    v = state["versions"][0]
    assert v["evaluations"][0]["outcome"] == expected
    assert (
        v["event_reviews"][0]["automatic"]
        and v["event_reviews"][0]["applied_to_monitoring"]
    )
    before = ledger.snapshot()
    due(owner, iid)
    run(owner, iid, sv, transport=lambda _: pytest.fail("same event inputs"))
    drain(owner)
    assert (
        ledger.snapshot() == before
        and service.state(owner, iid)["versions"][0]["evaluations"] == v["evaluations"]
    )


def test_same_snapshot_with_new_dates_does_not_reuse_another_revision(owner):
    sv = save(owner, events=[event(date_basis="event_occurrence")])
    p = packet(owner, sv)
    assert E.method(p) == E.OCCURRENCE_PROMPT and "occurrence_dates" in json.dumps(
        E.request_for(p)["text"]["format"]["schema"]
    )
    other = deepcopy(p)
    other["events"][0]["deadline"] = "2026-11-30"
    assert E.scope_signature(other) != E.scope_signature(p) and E.identity(
        owner, p
    ) != E.identity(owner, other)
    assert E.identity(owner, p) != E.identity(str(uuid4()), p)


def test_mixed_report_and_event_conditions_keep_independent_rules():
    p = pure_packet()
    p["events"].append(
        dict(p["events"][0], condition_id="report", date_basis="report_publication")
    )
    raw = result(p)
    findings = render(p, raw)["events"]
    assert [f["status"] for f in findings] == ["confirmed", "confirmed"]
    assert (
        "occurrence_dates" in findings[0]["citations"][0]
        and "occurrence_dates" not in findings[1]["citations"][0]
    )
