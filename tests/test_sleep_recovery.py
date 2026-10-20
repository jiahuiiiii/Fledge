"""Recovery after the computer sleeps: invented clocks, mocked providers, disposable ledger."""
from copy import deepcopy
from datetime import timedelta
import logging
from unittest.mock import patch
from uuid import uuid4
import pytest
from psycopg.types.json import Jsonb
from thesis import wake
from thesis.db import transaction, one
from thesis.monitoring import news_watch, watch_history
from thesis.providers import ledger
from thesis.research import sentiment as S, sentiment_batching as B, sentiment_task_runner as R
from test_model_budget import clean_model_ledger  # noqa: F401
from test_market import prepare
from test_sentiment import provider
from test_sentiment_batching import packet
from test_watch_history import begin
from test_sentiment_tasks import packet as task_packet


class Clocks:
    """Wall time keeps running during sleep; the awake clock does not."""

    def __init__(self):
        self.wall, self.awake = 1_000_000.0, 500.0

    def run(self, seconds):
        self.wall += seconds
        self.awake += seconds

    def sleep(self, seconds):
        self.wall += seconds


def guard(clocks):
    return wake.Guard(wall=lambda: clocks.wall, awake=lambda: clocks.awake)


def test_waking_holds_work_until_the_computer_stays_awake():
    clocks = Clocks()
    g = guard(clocks)
    assert g.settled()
    clocks.run(5)
    assert g.settled()
    clocks.sleep(1200)
    assert not g.settled()
    clocks.run(wake.SETTLE_SECONDS - 1)
    assert not g.settled()
    clocks.run(1)
    assert g.settled()


def test_power_nap_wakes_keep_extending_the_hold():
    clocks = Clocks()
    g = guard(clocks)
    g.settled()
    for _ in range(3):
        clocks.sleep(1000)
        assert not g.settled()
        clocks.run(2)  # a two-second Power Nap
        assert not g.settled()
    clocks.run(wake.SETTLE_SECONDS)
    assert g.settled()


def test_small_or_backwards_clock_corrections_are_not_sleep():
    clocks = Clocks()
    g = guard(clocks)
    g.settled()
    clocks.sleep(wake.SLEEP_JUMP_SECONDS)  # at the threshold, not over it
    assert g.settled()
    clocks.wall -= 3600  # wall clock set back
    assert g.settled()
    clocks.run(5)
    assert g.settled()


def test_backoff_doubles_to_a_ceiling_and_logs_once_per_outage(caplog):
    b = wake.Backoff(1.5, name="Telegram rating check", ceiling=60)
    assert b.delay() == 1.5
    with caplog.at_level(logging.WARNING, logger="thesis"):
        for _ in range(10):
            b.failed(TimeoutError("https://api.telegram.org/bot<secret>/getUpdates"))
        assert b.delay() == 60
        b.succeeded()
    assert b.delay() == 1.5
    messages = [r.getMessage() for r in caplog.records]
    assert messages == [
        "Telegram rating check failed (TimeoutError). Trying again with longer pauses, up to 60 seconds.",
        "Telegram rating check works again after 10 failed attempts.",
    ]
    assert not any("telegram.org" in m or "secret" in m for m in messages)


def test_no_request_is_reserved_or_sent_right_after_waking(monkeypatch):
    from thesis.providers import settings, openai
    monkeypatch.setattr(settings, "live_key", lambda model=None: "invented-test-key")
    monkeypatch.setattr(openai, "send", lambda *a, **k: pytest.fail("A request was sent"))
    monkeypatch.setattr(wake, "settled", lambda: False)
    before = ledger.snapshot()["calls"]
    with pytest.raises(ledger.WakePaused):
        ledger.execute("wake-paused-test", "test", dict(model=settings.MODEL))
    assert ledger.snapshot()["calls"] == before


def test_unsettled_quick_check_names_only_its_own_sources(owner):
    p = packet()
    p["sources"] = p["sources"][1:]

    def broken(body):
        raise TimeoutError()
    with patch.object(B, "check_access"):
        with pytest.raises(ledger.BudgetBlocked):
            B.run(p, transport=broken, prefilter=True)
        with pytest.raises(B.HeldSources) as held:
            B.run(p, transport=lambda _: pytest.fail("retry"), prefilter=True)
    assert held.value.source_ids and held.value.source_ids <= {s["id"] for s in p["sources"]}


def test_unsettled_tone_task_names_its_batch_and_is_never_resent():
    p = task_packet()
    expected = {s["id"] for s in R.plan("tone", p, p["sources"])[0]["sources"]}

    def timeout(body):
        raise TimeoutError("Invented timeout")
    with patch.object(B, "check_access"):
        with pytest.raises(ledger.BudgetBlocked):
            R.run(p, transport=timeout, prefilter=False)
        with pytest.raises(B.HeldSources) as held:
            R.run(task_packet(), transport=lambda _: pytest.fail("Uncertain charge resent"), prefilter=False)
    assert held.value.source_ids == expected


def held_generation(owner, held_count=1):
    iid = prepare(owner)
    p = packet()
    p["instrument_id"] = iid
    held_ids = {s["id"] for s in p["sources"][:held_count]}
    attempts = []
    real = B.run_reusing

    def run_reusing(pkt, reused, **kw):
        attempts.append([s["id"] for s in pkt["sources"]])
        if held_ids & set(attempts[-1]):
            raise B.HeldSources("An earlier sentiment task may have been sent. No automatic paid retry; review its charge.",
                                held_ids)
        return real(pkt, reused, **dict(kw, transport=provider("neutral")))
    patches = (patch.object(S, "prepare", side_effect=lambda *a, **k: deepcopy(p)), patch.object(B, "check_access"),
               patch.object(S, "present", side_effect=lambda c, r, **_: r), patch.object(B, "run_reusing", run_reusing))
    return iid, p, held_ids, attempts, patches


def test_scheduled_reading_leaves_out_only_held_sources_and_reuses_its_result(owner):
    iid, p, held_ids, attempts, patches = held_generation(owner)
    with patches[0], patches[1], patches[2], patches[3]:
        row = S.generate(iid, transport=provider("neutral"))
        assert len(attempts) == 2
        assert {s["id"] for s in row["packet"]["sources"]} == {s["id"] for s in p["sources"]} - held_ids
        held = row["packet"]["held_sources"]
        assert [h["id"] for h in held] == sorted(held_ids) and set(held[0]) == {"id", "channel", "reason"}
        assert row["result"]["held_sources"]["count"] == 1 and ":held:" in row["request_key"]
        assert all(i["source_id"] not in held_ids for i in row["result"]["items"])
        # The next check hits the same block, then finds the saved partial reading free.
        again = S.generate(iid, transport=lambda _: pytest.fail("paid again"))
        assert again["id"] == row["id"] and len(attempts) == 3


def test_explicit_recovery_and_fully_held_samples_still_stop(owner):
    iid, p, held_ids, attempts, patches = held_generation(owner)
    with patches[0], patches[1], patches[2], patches[3]:
        for options in (dict(retry_failed=True), dict(split_failed=True), dict(reread_token=uuid4())):
            with pytest.raises(B.HeldSources):
                S.generate(iid, transport=provider("neutral"), **options)
    iid, p, held_ids, attempts, patches = held_generation(owner, held_count=len(packet()["sources"]))
    with patches[0], patches[1], patches[2], patches[3]:
        with pytest.raises(B.HeldSources):
            S.generate(iid, transport=provider("neutral"))
        assert len(attempts) == 1


def baseline_id(owner, iid):
    with transaction(owner) as c:
        return one(c, "SELECT baseline_id FROM news_watches WHERE owner_id=%s AND instrument_id=%s",
                   (owner, iid))["baseline_id"]


def test_partial_reading_publishes_no_alert_and_keeps_the_baseline(owner):
    iid, _ = begin(owner)
    before = baseline_id(owner, iid)

    def partial(i):
        full = S.generate(i, transport=provider("negative"))
        with transaction(admin=True) as c:
            row = one(c, "SELECT * FROM sentiment_analyses WHERE id=%s", (full["id"],))
            reason = "An earlier sentiment task may have been sent."
            held = one(c, "INSERT INTO sentiment_analyses VALUES(%s,%s,%s,%s,%s,%s,now()) RETURNING *", (
                uuid4(), i, row["request_key"] + ":held:test", row["call_id"],
                Jsonb(dict(row["packet"], held_sources=[dict(id="held", channel="news", reason=reason)])),
                Jsonb(dict(row["result"], held_sources=dict(count=1, reason=reason)))))
            return S.present(c, held)

    assert news_watch.run_once(owner, market_refresh=lambda _: None, social_refresh=lambda: None, analyzer=partial)
    item = watch_history.history(owner, iid)["items"][0]
    assert item["status"] == "completed" and item["details"]["held_sources"] == 1
    assert item["alert_count"] == 0
    assert "1 source was left unread" in item["reason"] and "Alerts wait for the next complete reading." in item["reason"]
    assert baseline_id(owner, iid) == before


@pytest.mark.parametrize("skip,error", [
    ("other_lane_busy", lambda: __import__("thesis.service", fromlist=["Conflict"]).Conflict(
        "Sentiment analysis is already running for this company.")),
    ("computer_woke", lambda: ledger.WakePaused("The computer woke from sleep moments ago. Nothing was sent; "
                                                "this check runs again once the connection is back.")),
])
def test_overlap_and_wake_are_skips_that_retry_soon_within_the_limit(owner, skip, error, caplog):
    iid, now = begin(owner)

    def due_at():
        with transaction(owner) as c:
            return one(c, "SELECT next_check_at FROM news_watches WHERE owner_id=%s AND instrument_id=%s",
                       (owner, iid))["next_check_at"]

    def raise_(_):
        raise error()

    clock = now
    with caplog.at_level(logging.WARNING):
        for _ in range(news_watch.QUICK_RETRIES):
            assert news_watch.run_once(owner, now=clock, market_refresh=lambda _: None,
                                       social_refresh=lambda: None, analyzer=raise_)
            item = watch_history.history(owner, iid)["items"][0]
            assert item["status"] == "stopped" and item["details"]["skip_reason"] == skip
            assert "tries again" in item["reason"]
            assert due_at() == clock + timedelta(minutes=news_watch.BUSY_RETRY_MINUTES)
            clock = due_at() + timedelta(seconds=1)
        # Each retry fetches sources again, so skips share the quick-retry limit.
        assert news_watch.run_once(owner, now=clock, market_refresh=lambda _: None,
                                   social_refresh=lambda: None, analyzer=raise_)
        assert due_at() == clock + timedelta(minutes=60)
    assert not any(r.exc_info for r in caplog.records if "Scheduled" in r.getMessage())
