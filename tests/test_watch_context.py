"""Opted-in context acquisition uses mocked public sources and model responses."""

from datetime import datetime, timezone, timedelta
from copy import deepcopy
from uuid import uuid4
import httpx
import pytest
from pydantic import ValidationError
from thesis.db import transaction, one
from thesis.research import sentiment, conversation as cv
from thesis.monitoring import news_watch as W, watch_history, watch_context
from thesis.providers import ledger
from thesis.app import WatchSettings
from test_conversation import setup, fetcher
from test_hackernews import hn, item, transport
from test_market import prepare
from test_sentiment import provider


def due(owner, iid, *, include_context=True, now=None):
    W.configure(
        owner,
        iid,
        True,
        now=(now or datetime.now(timezone.utc)) - timedelta(minutes=61),
        include_context=include_context,
    )


def run(owner, *, now=None, **kw):
    return W.run_once(
        owner,
        now=now,
        market_refresh=lambda _: None,
        social_refresh=lambda: None,
        analyzer=kw.pop(
            "analyzer", lambda i: sentiment.generate(i, transport=provider(), now=now)
        ),
        **kw,
    )


def latest(owner, iid):
    return watch_history.history(owner, iid)["items"][0]


def many(owner, count=6):
    iid = prepare(owner)
    children = {
        str(200 + i): item(
            str(200 + i), f"I disagree with Microsoft policy number {i}."
        )
        for i in range(count)
    }
    hn.refresh(iid, fetcher=transport(children))
    parent = dict(
        id=99,
        type="comment",
        text="Microsoft pricing is reasonable in my opinion.",
        time=next(iter(children.values()))["time"] - 60,
    )
    return iid, children, parent


def test_default_off_and_omitted_setting_preserves_explicit_choice(owner):
    iid = prepare(owner)
    assert not W.configure(owner, iid, True)["include_context"]
    assert W.configure(owner, iid, True, include_context=True)["include_context"]
    assert W.configure(owner, iid, True, interval=240)["include_context"]
    assert W.configure(owner, iid, False)["include_context"]
    assert not W.configure(owner, iid, False, include_context=False)["include_context"]
    for value in ("yes", 1, []):
        with pytest.raises(ValueError):
            W.configure(owner, iid, True, include_context=value)
        with pytest.raises(ValidationError):
            WatchSettings(enabled=True, include_context=value)


def test_watch_without_opt_in_never_collects_context(owner):
    iid, _, _, _ = setup(owner)
    due(owner, iid, include_context=False)
    run(owner, context_fetcher=lambda *_: pytest.fail("Unrequested context fetch"))
    saved = latest(owner, iid)
    assert saved["status"] == "completed" and not saved["include_context"]
    assert "context" not in saved["details"]


def test_context_precedes_analysis_and_reuses_recent_parent_next_check(owner):
    iid, post, child, parent = setup(owner)
    calls = []
    due(owner, iid)
    run(owner, context_fetcher=fetcher(child, parent, calls))
    saved = latest(owner, iid)
    assert saved["status"] == "completed" and saved["include_context"]
    detail = saved["details"]["context"]
    assert detail["source_requests"] == 2 and detail["parents_used_by_analysis"] == 1
    assert detail["items"][0]["source_id"] == str(post["id"])
    assert not detail["items"][0]["reused"]
    assert len(calls) == 2 and not saved["details"]["coverage_gap"]
    budget = ledger.snapshot()
    due(owner, iid)
    run(owner, context_fetcher=lambda *_: pytest.fail("Fresh parent fetched twice"))
    repeated = latest(owner, iid)["details"]["context"]
    assert repeated["source_requests"] == 0 and repeated["items"][0]["reused"]
    assert ledger.snapshot() == budget
    assert not watch_history.history(str(uuid4()), iid)["items"]


def test_maximum_four_replies_eight_requests_and_no_parent_votes(owner):
    iid, children, parent = many(owner)
    calls = []

    def get(kind, key, now):
        calls.append(key)
        return deepcopy(parent if key == "99" else children[key])

    due(owner, iid)
    run(owner, context_fetcher=get)
    saved = latest(owner, iid)
    context = saved["details"]["context"]
    assert context["selected_replies"] == 6 and len(context["items"]) == 4
    assert context["source_requests"] == len(calls) == 8
    assert context["parents_used_by_analysis"] == 4
    assert context["coverage_gap"] and saved["details"]["coverage_gap"]
    assert saved["details"]["selected"]["social"] == 6


def test_failure_stops_remaining_lookups_keeps_child_only_analysis_and_gap(owner):
    iid, children, parent = many(owner)
    calls = []

    def denied(kind, key, now):
        calls.append(key)
        raise httpx.HTTPStatusError(
            "secret-token=not-for-logs",
            request=httpx.Request("GET", "https://example.test"),
            response=httpx.Response(403),
        )

    due(owner, iid)
    run(owner, context_fetcher=denied)
    saved = latest(owner, iid)
    assert saved["status"] == "completed" and saved["details"]["coverage_gap"]
    context = saved["details"]["context"]
    assert context["source_requests"] == len(calls) == 1
    assert context["items"][0]["outcome"] == "failed"
    assert context["parents_used_by_analysis"] == 0 and context["status"] == "partial"
    assert "secret-token" not in str(saved)


def test_changed_child_stops_analysis_instead_of_treating_old_text_as_current(owner):
    iid, _, child, parent = setup(owner)
    child["text"] += " My view has changed."
    due(owner, iid)
    budget = ledger.snapshot()
    run(
        owner,
        context_fetcher=fetcher(child, parent, []),
        analyzer=lambda _: pytest.fail("Changed comment analysed"),
    )
    saved = latest(owner, iid)
    assert (
        saved["status"] == "failed"
        and saved["details"]["failed_stage"] == "original reply context"
    )
    assert saved["details"]["context"]["status"] == "source_changed"
    assert saved["details"]["coverage_gap"] and ledger.snapshot() == budget


def test_removed_child_is_withdrawn_before_model_selection(owner):
    iid, _, child, parent = setup(owner)
    child["deleted"] = True
    due(owner, iid)
    run(owner, context_fetcher=fetcher(child, parent, []))
    saved = latest(owner, iid)
    assert saved["status"] == "completed"
    assert saved["details"]["selected"]["social"] == 0
    assert saved["details"]["context"]["items"][0]["outcome"] == "source_removed"


def test_stop_between_child_and_parent_prevents_further_http_and_model(owner):
    iid, _, child, parent = setup(owner)
    due(owner, iid)
    calls = []

    def stop(kind, key, now):
        calls.append(key)
        W.configure(owner, iid, False)
        return child

    budget = ledger.snapshot()
    run(
        owner,
        context_fetcher=stop,
        analyzer=lambda _: pytest.fail("Stopped watch analysed"),
    )
    saved = latest(owner, iid)
    assert saved["status"] == "stopped" and calls == ["123"]
    assert saved["details"]["context"]["status"] == "checking"
    assert saved["details"]["coverage_gap"] and ledger.snapshot() == budget


def test_expired_claim_cannot_start_paid_analysis(owner):
    iid = prepare(owner)
    due(owner, iid)

    def expire():
        with transaction(owner) as c:
            c.execute(
                "UPDATE news_watches SET lease_until=%s WHERE owner_id=%s",
                (datetime.now(timezone.utc) - timedelta(seconds=1), owner),
            )

    W.run_once(
        owner,
        market_refresh=lambda _: None,
        social_refresh=expire,
        analyzer=lambda _: pytest.fail("Expired claim billed"),
        context_fetcher=lambda *_: pytest.fail("Expired claim fetched"),
    )
    assert latest(owner, iid)["status"] == "stopped"


def test_recent_failed_check_is_not_retried_within_cooldown(owner):
    iid, post, child, parent = setup(owner)

    def failed(*_):
        raise httpx.ConnectError("Authored network failure")

    cv.collect(post["id"], fetcher=failed)
    due(owner, iid)
    run(owner, context_fetcher=lambda *_: pytest.fail("Source cooldown ignored"))
    context = latest(owner, iid)["details"]["context"]
    assert context["source_requests"] == 0 and context["coverage_gap"]
    assert context["items"][0]["outcome"] == "shared_recent_check"


def test_model_finishing_after_lease_cannot_publish_or_start_private_call(owner):
    from thesis.research import idea_alerts

    iid = prepare(owner)
    due(owner, iid, include_context=False)

    def late(company):
        result = sentiment.generate(company, transport=provider())
        with transaction(owner) as c:
            token = one(
                c,
                "SELECT claim_token FROM news_watches WHERE owner_id=%s AND instrument_id=%s",
                (owner, iid),
            )["claim_token"]
            c.execute(
                "UPDATE news_watches SET match_idea=true WHERE owner_id=%s", (owner,)
            )
            assert idea_alerts.active_watch(c, owner, iid, token)
            c.execute(
                "UPDATE news_watches SET lease_until=%s WHERE owner_id=%s",
                (datetime.now(timezone.utc) - timedelta(seconds=1), owner),
            )
        assert W.publish(owner, iid, result["id"], claim_token=token) == 0
        with transaction(owner) as c:
            assert not idea_alerts.active_watch(c, owner, iid, token)
        return result

    run(
        owner,
        analyzer=late,
        idea_analyzer=lambda *_a, **_k: pytest.fail("Expired private dispatch"),
    )
    saved = latest(owner, iid)
    assert saved["status"] == "stopped" and saved["alert_count"] == 0
    assert saved["details"]["analysis"] == "completed"


def test_stale_parent_gets_new_original_check_not_silent_reuse(owner):
    iid, post, child, parent = setup(owner)
    first = cv.collect(post["id"], fetcher=fetcher(child, parent, []))
    future = datetime.now(timezone.utc) + timedelta(hours=25)
    due(owner, iid, now=future)
    calls = []
    run(owner, now=future, context_fetcher=fetcher(child, parent, calls))
    saved = latest(owner, iid)
    assert saved["status"] == "completed"
    context = saved["details"]["context"]
    assert context["source_requests"] == 2 and not context["items"][0]["reused"]
    assert context["items"][0]["result_id"] != first["result"]["id"]


def test_context_only_new_reading_keeps_seen_company_alert_quiet(owner):
    iid, _, child, parent = setup(owner)
    prior = sentiment.generate(iid, transport=provider("negative"))
    due(owner, iid)
    run(
        owner,
        context_fetcher=fetcher(child, parent, []),
        analyzer=lambda i: sentiment.generate(i, transport=provider("positive")),
    )
    saved = latest(owner, iid)
    assert saved["status"] == "completed" and saved["alert_count"] == 0
    assert saved["details"]["context"]["parents_used_by_analysis"] == 1
