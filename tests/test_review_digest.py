"""Periodic reviews preserve scope, chronology and private evidence without calls."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from thesis import service, review_digest
from thesis.db import transaction, one
from thesis.providers import ledger
from thesis.research import idea_alerts
from thesis.monitoring import news_watch
from thesis.models import SaveIdea
from test_idea_alerts import setup, provider, newer
from test_integration import payload, drain
from test_market import commit, news
from test_sentiment import provider as sentiment_provider
from thesis.research import sentiment


def test_period_counts_separate_older_pending_quiet_and_current_review(
    owner, monkeypatch
):
    iid, saved, analysis = setup(owner)
    end = datetime.now(timezone.utc)
    alert = idea_alerts.generate(owner, iid, analysis["id"], transport=provider("risk"))
    changed = newer(iid)
    idea_alerts.generate(owner, iid, changed["id"], transport=provider("context"))
    monkeypatch.setattr(
        ledger, "execute", lambda *a, **k: pytest.fail("read called AI")
    )
    r = review_digest.prepare(owner)
    assert r["total"] == 1 and r["totals"]["new_count"] == 1
    assert r["totals"]["pending_count"] == 1 and r["totals"]["quiet_checks"] == 1
    assert r["records"][0]["kind"] == "idea"
    assert r["records"][0]["detail"]["items"][0]["relation"] == "risk"
    future = datetime.now(timezone.utc) + timedelta(days=10)
    older = review_digest.prepare(owner, now=future)
    assert older["total"] == 0 and older["totals"]["older_pending_count"] == 1
    assert older["totals"]["pending_count"] == 1
    # The record window is historical; acknowledgement state is explicitly current.
    idea_alerts.review(owner, alert["id"], "unresolved")
    reviewed = review_digest.prepare(owner, review="unresolved")
    assert reviewed["total"] == 1 and reviewed["totals"]["pending_count"] == 0
    assert reviewed["totals"]["unresolved_count"] == 1
    assert review_digest.prepare(owner, cutoff=end)["total"] == 0


def test_all_alert_kinds_are_in_one_review_and_source_withdrawal_withholds(owner):
    iid, saved, analysis = setup(owner, True)
    news_watch.configure(owner, iid, True)
    commit(
        iid,
        [
            news(
                id=900,
                url="https://example.test/cost-warning",
                headline="Microsoft reports a cost warning",
                summary="Microsoft reports cost pressure, with demand still uncertain.",
            )
        ],
    )
    change = sentiment.generate(iid, transport=sentiment_provider("negative"))
    news_watch.publish(owner, iid, change["id"])
    idea_alerts.generate(owner, iid, analysis["id"], transport=provider("risk"))
    # Explicitly checking an older sample remains historical, not published.
    assert review_digest.prepare(owner)["total"] == 1
    live = idea_alerts.generate(owner, iid, change["id"], transport=provider("risk"))
    service.save_idea(owner, payload())
    drain(owner)
    service.advance(owner, 0)
    drain(owner)
    report = review_digest.prepare(owner)
    assert {"condition", "company", "idea"} == {r["kind"] for r in report["records"]}
    with transaction(admin=True) as c:
        entitlements = c.execute("SELECT id,entitlement FROM sources").fetchall()
        definition = c.execute("SELECT pg_get_constraintdef(oid) definition FROM pg_constraint WHERE conrelid='sources'::regclass AND conname='sources_entitlement_check'").fetchone()["definition"]
        c.execute("ALTER TABLE sources DROP CONSTRAINT sources_entitlement_check")
        c.execute("UPDATE sources SET entitlement='restricted'")
    try:
        report = review_digest.prepare(owner)
        assert all(r["detail"]["withheld"] for r in report["records"])
        _, html = review_digest.download(owner)
        assert "figures and source excerpts are withheld" in html
        assert "The supplied report may challenge" not in html
        assert "18%" not in html
    finally:
        with transaction(admin=True) as c:
            for source in entitlements:
                c.execute(
                    "UPDATE sources SET entitlement=%s WHERE id=%s",
                    (source["entitlement"], source["id"]),
                )
            c.execute(
                "ALTER TABLE sources ADD CONSTRAINT sources_entitlement_check " + definition
            )


def test_owner_scope_and_empty_review(owner):
    iid, saved, analysis = setup(owner)
    idea_alerts.generate(owner, iid, analysis["id"], transport=provider("risk"))
    other = str(uuid4())
    report = review_digest.prepare(other)
    assert report["total"] == 0 and report["companies"] == []
    with pytest.raises(service.Missing):
        review_digest.prepare(other, instrument_id=iid)
    _, html = review_digest.download(other)
    assert "durable operating margins" not in html


def test_coverage_failure_and_watch_off_are_not_reported_as_quiet_safety(owner):
    iid, saved, analysis = setup(owner)
    report = review_digest.prepare(owner)
    company = report["companies"][0]
    assert not company["coverage"]["watch"]
    assert any("not been checked" in x for x in company["coverage"]["concerns"])
    with transaction(admin=True) as c:
        c.execute(
            "INSERT INTO social_refresh_state(feed,completed_at,error) VALUES('stocks',now(),'HTTP 429') ON CONFLICT(feed) DO UPDATE SET error='HTTP 429'"
        )
    report = review_digest.prepare(owner)
    assert any(
        "r/stocks could not" in x
        for x in report["companies"][0]["coverage"]["concerns"]
    )
    assert "quiet list does not establish" in report["limitation"]


def test_pagination_does_not_truncate_counts_or_full_export(owner):
    iid, saved, analysis = setup(owner)
    for revision in range(23):
        if revision:
            service.save_idea(
                owner,
                SaveIdea(
                    instrument_id=iid,
                    expected_revision=revision,
                    question=f"Question {revision}",
                    reasoning=f"I expect demand to support margins in case {revision}.",
                    status="draft",
                    conditions=[],
                ),
            )
        idea_alerts.generate(owner, iid, analysis["id"], transport=provider("risk"))
    first = review_digest.prepare(owner)
    second = review_digest.prepare(owner, cutoff=first["cutoff"], page=1)
    assert first["total"] == second["total"] == 23
    assert len(first["records"]) == 20 and len(second["records"]) == 3
    assert len({str(x["id"]) for x in first["records"] + second["records"]}) == 23
    before = ledger.snapshot()
    _, html = review_digest.download(owner, cutoff=first["cutoff"])
    assert html.count("<section>") == 23 and ledger.snapshot() == before


@pytest.mark.parametrize(
    "args",
    [
        {"days": 2},
        {"page": -1},
        {"review": "secret"},
        {"cutoff": "2026-01-01"},
        {"cutoff": datetime.now(timezone.utc) + timedelta(days=1)},
    ],
)
def test_invalid_period_inputs_are_rejected(owner, args):
    with pytest.raises(ValueError):
        review_digest.prepare(owner, **args)


def test_export_is_inert_private_and_preserves_window_after_edit(owner):
    iid, saved, analysis = setup(owner)
    service.save_idea(
        owner,
        SaveIdea(
            instrument_id=iid,
            expected_revision=1,
            question="Private <script> question",
            reasoning="I expect <script>growth</script> to support margins.",
            status="draft",
            conditions=[],
        ),
    )
    idea_alerts.generate(owner, iid, analysis["id"], transport=provider("risk"))
    cutoff = review_digest.prepare(owner)["cutoff"]
    service.save_idea(
        owner,
        SaveIdea(
            instrument_id=iid,
            expected_revision=2,
            question="Later question",
            reasoning="Later reasoning.",
            status="archived",
            conditions=[],
        ),
    )
    filename, html = review_digest.download(owner, cutoff=cutoff)
    assert filename.endswith(".html") and "Private research record" in html
    assert (
        "<script>" not in html
        and "&lt;script&gt;" in html
        and "Content-Security-Policy" in html
    )
    assert "Saved revision 2" in html and "Current idea: Later question" in html


def test_review_endpoints_require_local_session(owner):
    from thesis.app import app

    with TestClient(app) as client:
        assert client.get("/api/v1/research-review").status_code == 401
        client.get("/api/v1/session")
        assert client.get("/api/v1/research-review").status_code == 200
        export = client.get("/api/v1/research-review/export")
        assert (
            export.status_code == 200
            and "attachment" in export.headers["content-disposition"]
        )
        assert client.get("/api/v1/research-review?days=2").status_code == 422
