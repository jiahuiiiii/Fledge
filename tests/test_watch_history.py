"""Watch journal follows real scheduler boundaries with mocked sources/model calls."""

from datetime import datetime, timezone, timedelta
from uuid import uuid4
import json
import pytest
import psycopg
from fastapi.testclient import TestClient
from thesis import service
from thesis.db import transaction, one, rows
from thesis.monitoring import news_watch, watch_history
from thesis.research import sentiment, idea_alerts, market
from thesis.providers import ledger
from test_market import prepare, commit, news, quote
from test_sentiment import provider, add_social


def begin(owner, *, baseline=True):
    iid = prepare(owner)
    if baseline:
        sentiment.generate(iid, transport=provider("neutral"))
    now = datetime.now(timezone.utc)
    news_watch.configure(owner, iid, True, now=now - timedelta(minutes=61))
    return iid, now


def run(owner, **kw):
    return news_watch.run_once(
        owner,
        market_refresh=lambda _: None,
        social_refresh=lambda: None,
        analyzer=lambda i: sentiment.generate(i, transport=provider("negative")),
        **kw,
    )


def test_first_baseline_and_quiet_are_distinct_and_readonly(owner):
    iid, now = begin(owner, baseline=False)
    before = ledger.snapshot()["calls"]
    assert run(owner)
    result = watch_history.history(owner, iid)["items"][0]
    assert result["status"] == "completed" and result["alert_count"] == 0
    assert "baseline" in result["reason"]
    assert result["details"]["selected"] == {"news": 1, "social": 0}
    assert result["elapsed_seconds"] >= 0
    budget = ledger.snapshot()
    assert watch_history.history(owner, iid)["items"] == [result]
    assert ledger.snapshot() == budget and budget["calls"] == before + 1
    news_watch.configure(owner, iid, True, now=now - timedelta(minutes=61))
    assert run(owner)
    newest = watch_history.history(owner, iid)["items"][0]
    assert "No alert rule triggered" in newest["reason"] and ledger.snapshot() == budget


def test_actual_publication_count_and_immutable_attempt(owner):
    iid, _ = begin(owner)
    commit(
        iid,
        [
            news(
                id=2,
                url="https://example.test/new",
                headline="Microsoft reports weaker margins",
                summary="Microsoft says reported margins fell.",
            )
        ],
    )
    assert run(owner)
    a = watch_history.history(owner, iid)["items"][0]
    assert a["alert_count"] == 1 and a["details"]["company_alerts"] == 1
    with transaction(owner) as c:
        assert len(news_watch.list_alerts(c, owner)) == 1
    for table, col in [("watch_checks", "id"), ("watch_check_results", "check_id")]:
        with pytest.raises(psycopg.Error):
            with transaction(owner) as c:
                c.execute(f"DELETE FROM {table} WHERE {col}=%s", (a["id"],))


@pytest.mark.parametrize(
    "stage",
    [
        "social sources",
        "sentiment analysis",
        "saved-reasoning analysis",
    ],
)
def test_failure_stage_is_not_quiet_and_raw_exception_is_never_exposed(owner, stage):
    iid, _ = begin(owner)

    def fail(*a, **k):
        raise ValueError("secret-token=DO_NOT_COPY")

    args = dict(
        market_refresh=lambda _: None,
        social_refresh=lambda: None,
        analyzer=lambda i: sentiment.generate(i, transport=provider()),
    )
    if stage == "company news":
        args["market_refresh"] = fail
    elif stage == "social sources":
        args["social_refresh"] = fail
    elif stage == "sentiment analysis":
        args["analyzer"] = fail
    else:
        from thesis.models import SaveIdea

        service.save_idea(
            owner,
            SaveIdea(
                instrument_id=iid,
                expected_revision=0,
                question="Do margins support growth?",
                reasoning="I expect durable margins.",
                status="draft",
                conditions=[],
            ),
        )
        news_watch.configure(
            owner,
            iid,
            True,
            now=datetime.now(timezone.utc) - timedelta(minutes=61),
            match_idea=True,
        )
        args["idea_analyzer"] = fail
    assert news_watch.run_once(owner, **args)
    a = watch_history.history(owner, iid)["items"][0]
    assert a["status"] == "failed" and a["details"]["failed_stage"] == stage
    assert "No alert rule triggered" not in a[
        "reason"
    ] and "DO_NOT_COPY" not in json.dumps(a)
    assert not run(owner)


def test_shared_market_cooldown_is_a_cache_boundary_not_a_failed_check(
    owner, monkeypatch
):
    iid, _ = begin(owner)

    import httpx
    from test_market import mock_market

    transport = mock_market(
        monkeypatch,
        lambda req: httpx.Response(
            200, json=quote() if req.url.path.endswith("/quote") else [news()]
        ),
    )

    # Existing real transport adapter is mocked, but its persisted cooldown is actual.
    market.refresh(iid, transport=transport)
    assert news_watch.run_once(
        owner,
        market_refresh=lambda i: market.refresh(
            i, transport=lambda *a: pytest.fail("cooldown made HTTP")
        ),
        social_refresh=lambda: None,
        analyzer=lambda i: sentiment.generate(i, transport=provider()),
    )
    a = watch_history.history(owner, iid)["items"][0]
    assert (
        a["status"] == "completed" and a["details"]["market"] == "shared_recent_check"
    )


def test_partial_source_failure_is_retained_even_after_recovery(owner):
    iid, _ = begin(owner)
    add_social(iid)
    with transaction(source=True) as c:
        c.execute(
            "UPDATE social_refresh_state SET error='Authored source failure' WHERE feed='stocks'"
        )
    try:
        run(owner)
        first = watch_history.history(owner, iid)["items"][0]
        assert first["status"] == "completed" and first["details"]["coverage_gap"]
        with transaction(source=True) as c:
            c.execute("UPDATE social_refresh_state SET error=NULL WHERE feed='stocks'")
        assert watch_history.history(owner, iid)["items"][0]["details"]["coverage_gap"]
    finally:
        with transaction(source=True) as c:
            c.execute("UPDATE social_refresh_state SET error=NULL WHERE feed='stocks'")


def test_stopped_mid_refresh_does_not_request_analysis(owner):
    iid, _ = begin(owner)
    news_watch.run_once(
        owner,
        market_refresh=lambda _: news_watch.configure(owner, iid, False),
        social_refresh=lambda: None,
        analyzer=lambda _: pytest.fail("stopped"),
    )
    a = watch_history.history(owner, iid)["items"][0]
    assert a["status"] == "stopped" and a["details"]["analysis"] == "not_run"


def test_process_loss_leaves_missing_completion_and_does_not_claim_quiet(owner):
    iid, now = begin(owner)

    def killed(_):
        raise KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        news_watch.run_once(owner, market_refresh=killed)
    in_progress = watch_history.history(owner, iid, now=now)["items"][0]
    assert in_progress["status"] == "running" and in_progress["alert_count"] is None
    abandoned = watch_history.history(owner, iid, now=now + timedelta(minutes=16))[
        "items"
    ][0]
    assert abandoned["status"] == "unfinished" and "coverage gap" in abandoned["reason"]
    assert abandoned["completed_at"] is None


def test_other_owner_cannot_read_finish_or_use_cursor(owner):
    iid, _ = begin(owner)
    run(owner)
    a = watch_history.history(owner, iid)["items"][0]
    other = str(uuid4())
    with transaction(admin=True) as c:
        c.execute("INSERT INTO accounts VALUES(%s,%s)", (other, "Other watch tester"))
    assert watch_history.history(other, iid)["items"] == []
    with pytest.raises(service.Missing):
        watch_history.history(other, iid, a["id"])
    with transaction(other) as c:
        assert not rows(c, "SELECT * FROM watch_checks") and not rows(
            c, "SELECT * FROM watch_check_results"
        )
    with pytest.raises(psycopg.Error):
        with transaction(other) as c:
            c.execute(
                "INSERT INTO watch_check_results VALUES(%s,%s,now(),'completed',NULL,NULL,'{}')",
                (other, a["id"]),
            )


def test_withdrawal_hides_derived_counts_from_read_view(owner):
    iid, _ = begin(owner)
    add_social(iid)
    run(owner)
    with transaction(admin=True) as c:
        c.execute("UPDATE social_feeds SET enabled=false")
    try:
        a = watch_history.history(owner, iid)["items"][0]
        assert a["withheld"] and not a["details"] and a["alert_count"] is None
    finally:
        with transaction(admin=True) as c:
            c.execute("UPDATE social_feeds SET enabled=true")


def test_history_pagination_and_authentication(owner):
    from thesis.app import app

    iid, now = begin(owner)
    for i in range(22):
        news_watch.configure(owner, iid, True, now=now - timedelta(minutes=61))
        run(owner)
    first = watch_history.history(owner, iid)
    second = watch_history.history(owner, iid, first["next_cursor"])
    assert (
        len(first["items"]) == 20
        and len(second["items"]) == 2
        and second["next_cursor"] is None
    )
    assert len({r["id"] for r in first["items"] + second["items"]}) == 22
    with TestClient(app) as client:
        assert client.get(f"/api/v1/companies/{iid}/watch-checks").status_code == 401
        client.get("/api/v1/session")
        assert client.get(f"/api/v1/companies/{iid}/watch-checks").status_code == 200


def test_private_publication_is_tied_to_the_exact_check(owner):
    from test_idea_alerts import setup, newer, provider as private_provider

    iid, saved, analysis = setup(owner)
    news_watch.configure(
        owner,
        iid,
        True,
        now=datetime.now(timezone.utc) - timedelta(minutes=61),
        match_idea=True,
    )
    newer(iid)
    run(
        owner,
        idea_analyzer=lambda account, company, aid, **kw: idea_alerts.generate(
            account, company, aid, transport=private_provider(), **kw
        ),
    )
    a = watch_history.history(owner, iid)["items"][0]
    assert a["status"] == "completed" and a["alert_count"] == 1
    assert a["version_id"] == saved["version_id"] and a["details"]["idea_alerts"] == 1
    assert a["details"]["company_alerts"] == 0 and a["idea_check_id"]
    with transaction(owner) as c:
        p = one(
            c,
            "SELECT * FROM idea_alert_publications WHERE owner_id=%s AND check_id=%s",
            (owner, a["idea_check_id"]),
        )
        assert p["mode"] == "watch"


def test_cross_company_journal_references_are_rejected(owner):
    from thesis.research.sec.service import add_company

    iid, _ = begin(owner)
    other = add_company("AAPL")["instrument_id"]
    with transaction(owner) as c:
        w = one(c, "SELECT * FROM news_watches WHERE owner_id=%s", (owner,))
        token = uuid4()
        now = datetime.now(timezone.utc)
        watch_history.start(c, owner, w, token, now, now + timedelta(minutes=15))
        analysis = one(
            c, "SELECT id FROM sentiment_analyses WHERE instrument_id=%s", (iid,)
        )
    from psycopg.types.json import Jsonb

    with pytest.raises(psycopg.Error):
        with transaction(owner) as c:
            c.execute(
                "INSERT INTO watch_checks VALUES(%s,%s,%s,%s,%s,60,false,%s,NULL,NULL)",
                (
                    uuid4(),
                    owner,
                    other,
                    now,
                    now + timedelta(minutes=15),
                    analysis["id"],
                ),
            )
    with pytest.raises(psycopg.Error):
        with transaction(owner) as c:
            c.execute(
                "INSERT INTO watch_check_results VALUES(%s,%s,%s,'completed',NULL,NULL,%s)",
                (owner, token, now - timedelta(seconds=1), Jsonb({})),
            )


def test_one_failed_news_provider_does_not_stop_other_sources(owner):
    iid, _ = begin(owner)
    calls=[]
    def fail(_):
        raise ValueError("secret-token=DO_NOT_COPY")
    assert news_watch.run_once(owner, market_refresh=fail,
        social_refresh=lambda:calls.append("social"),
        analyzer=lambda i: sentiment.generate(i, transport=provider()))
    result=watch_history.history(owner,iid)["items"][0]
    assert calls==["social"] and result["status"]=="completed"
    assert result["details"]["market"]=="failed" and result["details"]["coverage_gap"]
    assert "DO_NOT_COPY" not in json.dumps(result)
