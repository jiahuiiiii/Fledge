"""Independent private-comparison probes; all provider responses are mocked."""

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from threading import Event
from uuid import uuid4

import psycopg
import pytest

from thesis import service
from thesis.config import INSTRUMENT
from thesis.db import one, rows, transaction
from thesis.providers import ledger
from thesis.providers.settings import MODEL
from thesis.research import idea_review
from test_integration import drain, payload
from test_model_budget import body, response


@pytest.fixture(autouse=True)
def isolated_model_records(db):
    with transaction(admin=True) as conn:
        conn.execute(
            "TRUNCATE discussion_theme_reviews,expectation_reviews,watch_check_results,watch_checks,research_answers,idea_alert_reviews,idea_alert_publications,idea_alert_checks,idea_watch_seen,idea_watch_state,research_alert_reviews,research_alerts,watch_seen_sources,news_watches,sentiment_analyses,proposal_decisions,idea_proposals,event_review_activations,event_results,event_evidence_reviews,model_accounting_decisions,idea_evidence_reviews,model_dispatches,model_calls"
        )
    yield
    with transaction(admin=True) as conn:
        conn.execute(
            "TRUNCATE discussion_theme_reviews,expectation_reviews,watch_check_results,watch_checks,research_answers,idea_alert_reviews,idea_alert_publications,idea_alert_checks,idea_watch_seen,idea_watch_state,research_alert_reviews,research_alerts,watch_seen_sources,news_watches,sentiment_analyses,proposal_decisions,idea_proposals,event_review_activations,event_results,event_evidence_reviews,model_accounting_decisions,idea_evidence_reviews,model_dispatches,model_calls"
        )


def another_account():
    other = str(uuid4())
    with transaction(admin=True) as conn:
        conn.execute(
            "INSERT INTO accounts VALUES(%s,'Second fictional account')", (other,)
        )
    return other


def review_response(request):
    packet = json.loads(request["input"][1]["content"])
    source = packet["sources"][0]
    result = dict(
        points=[
            dict(
                relation="unclear",
                reasoning_segment_id=packet["reasoning_segments"][0]["id"],
                text="The supplied source alone does not establish this belief.",
                citations=[
                    dict(source_id=source["id"], passage_id=source["passages"][0]["id"])
                ],
            )
        ]
    )
    return response() | dict(
        model=request["model"],
        id="resp_mock_" + str(uuid4()),
        output=[
            dict(
                type="message",
                content=[dict(type="output_text", text=json.dumps(result))],
            )
        ],
    )


def test_private_call_and_dispatch_rows_are_hidden_but_totals_are_global(owner):
    other = another_account()
    request = body()
    request["input"][1]["content"] = "Private fictional reasoning from first account"
    call, dispatch = ledger.reserve("private-test", "test", request, owner=owner)
    assert dispatch
    ledger.authorize_dispatch(call["id"], request, owner=owner)
    ledger.settle(call, response(), owner=owner)

    with transaction(owner) as conn:
        assert one(
            conn,
            "SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user",
        ) == dict(rolsuper=False, rolbypassrls=False)
        assert (
            one(
                conn, "SELECT request_body FROM model_calls WHERE id=%s", (call["id"],)
            )["request_body"]
            == request
        )
        assert one(conn, "SELECT count(*) n FROM model_dispatches")["n"] == 1
        expected = ledger.snapshot(conn)
    for identity in (None, other):
        with transaction(identity) as conn:
            assert rows(conn, "SELECT * FROM model_calls") == []
            assert rows(conn, "SELECT * FROM model_dispatches") == []
            assert ledger.snapshot(conn) == expected
    with pytest.raises(ledger.BudgetBlocked, match="matching unused reservation"):
        ledger.authorize_dispatch(call["id"], request, owner=other)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with transaction(source=True) as conn:
            one(conn, "SELECT * FROM model_global_totals()")
    assert expected["calls"] == 1 and float(expected["spent_usd"]) > 0


def test_private_pending_request_blocks_other_owner_and_shared_dispatch(owner):
    other = another_account()
    entered, release = Event(), Event()

    def provider(request):
        entered.set()
        assert release.wait(8)
        return response()

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(
            ledger.execute,
            "private-running",
            "test",
            body(),
            owner=owner,
            transport=provider,
        )
        try:
            assert entered.wait(8)
            for identity in (other, None):
                with pytest.raises(ledger.BudgetBlocked, match="reconciliation"):
                    ledger.execute(
                        "blocked-" + str(identity),
                        "test",
                        body(),
                        owner=identity,
                        transport=lambda _: pytest.fail(
                            "Cross-owner duplicate dispatch"
                        ),
                    )
                with transaction(identity) as conn:
                    assert rows(conn, "SELECT * FROM model_calls") == []
                    assert ledger.snapshot(conn)["unresolved"] == 1
        finally:
            release.set()
        first.result(timeout=8)
    assert ledger.snapshot()["unresolved"] == 0 and ledger.snapshot()["calls"] == 1


def test_hidden_private_charge_still_enforces_shared_cap(owner):
    other = another_account()
    with transaction(admin=True) as conn:
        spent = one(conn, "SELECT cap_nano_usd FROM model_budget WHERE singleton")["cap_nano_usd"] - 1
        conn.execute(
            """INSERT INTO model_calls(id,request_key,request_hash,purpose,model,price_version,
          request_body,reserved_nano_usd,status,charged_nano_usd,owner_id)
          VALUES(%s,'hidden-earlier-work','x','test',%s,'test','{}',%s,'settled',%s,%s)""",
            (uuid4(), MODEL, spent, spent, owner),
        )
    with transaction(other) as conn:
        assert rows(conn, "SELECT * FROM model_calls") == []
        assert ledger.snapshot(conn)["remaining_usd"] == "1e-09"
    with pytest.raises(ledger.BudgetBlocked, match="allowance"):
        ledger.execute(
            "other-over-cap",
            "test",
            body(),
            owner=other,
            transport=lambda _: pytest.fail("Hidden charge bypassed budget"),
        )


def test_late_private_review_stays_on_original_revision_and_snapshot(owner):
    other = another_account()
    saved = service.save_idea(owner, payload())
    drain(owner)
    initial = service.state(owner)
    evaluation = initial["versions"][0]["evaluations"][0]
    snapshot_id = evaluation["manifest"]["snapshot_id"]
    entered, release = Event(), Event()
    seen = []

    def provider(request):
        seen.append(json.loads(request["input"][1]["content"]))
        entered.set()
        assert release.wait(8)
        return review_response(request)

    with ThreadPoolExecutor(max_workers=2) as pool:
        pending = pool.submit(
            idea_review.generate,
            owner,
            saved["version_id"],
            snapshot_id,
            str(evaluation["id"]),
            transport=provider,
        )
        try:
            assert entered.wait(8)
            # The network call holds no private/source transaction open.
            service.advance(owner, 0)
            replacement = payload(revision=1)
            replacement.reasoning = (
                "The saved claim changed while the comparison was running."
            )
            revised = service.save_idea(owner, replacement)
            drain(owner)
        finally:
            release.set()
        result = pending.result(timeout=8)
    final = service.state(owner)
    assert result["version_id"] == saved["version_id"]
    assert result["snapshot_id"] == snapshot_id and result["evaluation_id"] == str(
        evaluation["id"]
    )
    assert str(final["versions"][0]["id"]) == revised["version_id"]
    assert final["versions"][0]["evidence_reviews"] == []
    assert final["versions"][1]["evidence_reviews"] == [result]
    assert seen[0]["reasoning"] == initial["versions"][0]["reasoning"]
    assert seen[0]["cutoff"] == evaluation["manifest"]["cutoff"]
    assert {s["id"] for s in seen[0]["sources"]} <= set(
        evaluation["manifest"]["document_ids"]
    )
    assert (
        idea_review.generate(
            owner,
            saved["version_id"],
            snapshot_id,
            str(evaluation["id"]),
            transport=lambda _: pytest.fail("Duplicate private comparison"),
        )
        == result
    )
    assert ledger.snapshot()["calls"] == 1
    for identity in (None, other):
        with transaction(identity) as conn:
            assert rows(conn, "SELECT * FROM idea_evidence_reviews") == []
            assert rows(conn, "SELECT * FROM model_calls") == []
    with transaction(owner) as conn:
        stored = one(
            conn, "SELECT * FROM idea_evidence_reviews WHERE id=%s", (result["id"],)
        )
        assert (
            json.loads(idea_review.request_for(stored["packet"])["input"][1]["content"])
            == seen[0]
        )
        assert all("text" in source for source in stored["packet"]["sources"])
        assert all("text" not in source for source in seen[0]["sources"])
    assert service.state(other, INSTRUMENT)["versions"] == []


def test_expiry_review_uses_assessment_freshness_without_borrowing_new_sources(owner):
    from test_reporting_age import finish_all, with_limits
    from test_sec_fundamentals import apply, bundle
    from thesis.monitoring.age import instant
    from thesis.research.sec.service import add_company

    iid = add_company("MSFT")["instrument_id"]
    apply(iid, bundle())
    age = (datetime.now(timezone.utc).date() - date(2025, 9, 30)).days
    saved = service.save_idea(owner, with_limits(age + 1, age + 3, instrument=iid))
    finish_all(owner)
    initial = service.state(owner, iid)["versions"][0]["evaluations"][0]
    due = min(instant(a["expires_at"]) for a in initial["manifest"]["expiry"])
    service.queue_current(owner, now=due)
    finish_all(owner)
    expired = service.state(owner, iid)["versions"][0]["evaluations"][0]
    assert expired["manifest"]["snapshot_id"] == initial["manifest"]["snapshot_id"]
    assert expired["manifest"]["source_states"] == {"sec-companyfacts": "stale"}
    with transaction(owner) as conn:
        packet = idea_review.prepare(
            conn,
            owner,
            saved["version_id"],
            expired["manifest"]["snapshot_id"],
            str(expired["id"]),
        )
        snapshot = one(
            conn,
            "SELECT payload FROM research_snapshots WHERE id=%s",
            (expired["manifest"]["snapshot_id"],),
        )["payload"]
    assert snapshot["source_states"] == {"sec-companyfacts": "fresh"}
    assert packet["cutoff"] == snapshot["cutoff"]
    assert packet["assessed_at"] == expired["manifest"]["assessed_at"]
    assert packet["source_states"] == expired["manifest"]["source_states"]
    assert packet["freshness"] == expired["freshness"] == "stale"
    assert packet["numerical_assessment"]["outcome"] == expired["outcome"] == "unknown"
    assert {s["id"] for s in packet["sources"]} <= set(snapshot["document_ids"])


def test_workspace_snapshot_matches_displayed_evidence_during_refresh(
    owner, monkeypatch
):
    service.save_idea(owner, payload())
    drain(owner)
    initial = service.state(owner)
    read, release = Event(), Event()
    original = service.permitted_documents

    def paused_documents(*args, **kwargs):
        documents = original(*args, **kwargs)
        if not read.is_set():
            read.set()
            assert release.wait(8)
        return documents

    monkeypatch.setattr(service, "permitted_documents", paused_documents)
    with ThreadPoolExecutor(max_workers=2) as pool:
        pending = pool.submit(service.state, owner)
        try:
            assert read.wait(8)
            # Commit a new source snapshot after the response read its documents
            # but before it reads latest_snapshot. Refresh must remain unblocked.
            service.advance(owner, 0)
        finally:
            release.set()
        coherent = pending.result(timeout=8)
    assert coherent["documents"] == initial["documents"]
    assert coherent["snapshot_id"] == initial["snapshot_id"]
    refreshed = service.state(owner)
    assert refreshed["snapshot_id"] > coherent["snapshot_id"]
    assert refreshed["documents"] != coherent["documents"]
