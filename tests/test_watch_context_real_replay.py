"""Optional retained HN-response replay. No live requests or model evaluation."""

import os
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
import pytest
from thesis.db import transaction, one
from thesis.providers import ledger
from thesis.research import sentiment, hackernews, conversation
from thesis.research.sec.service import add_company
from thesis.monitoring import news_watch, watch_context, watch_history

CORPUS = os.environ.get("THESIS_HN_CONTEXT_CORPUS")
pytestmark = pytest.mark.skipif(
    not CORPUS, reason="Retained public HN context corpus not configured; no fetching"
)
PAIRS = {
    "MSFT": [("49931986", "49931871"), ("49931269", "49929025")],
    "NVDA": [
        ("49931557", "49926773"),
        ("49931224", "49924543"),
        ("49930146", "49929929"),
    ],
}


@pytest.mark.parametrize("symbol", list(PAIRS))
def test_real_original_reply_pairs_through_watch_acquisition(
    owner, symbol, monkeypatch
):
    root = Path(CORPUS)
    replies = {
        child: json.loads((root / f"{symbol}-{child}-{child}.json").read_text())
        for child, parent in PAIRS[symbol]
    }
    parents = {
        parent: json.loads((root / f"{symbol}-{child}-{parent}.json").read_text())
        for child, parent in PAIRS[symbol]
    }
    now = datetime(2026, 10, 3, 0, 0, tzinfo=timezone.utc)
    iid = add_company(symbol)["instrument_id"]
    hackernews.refresh(
        iid,
        fetcher=lambda kind, key, cutoff: (
            {"hits": [{"objectID": k} for k in replies]}
            if kind == "search"
            else replies[key]
        ),
        now=now,
    )
    budget = ledger.snapshot()
    monkeypatch.setattr(
        ledger, "execute", lambda *_a, **_k: pytest.fail("Replay called model")
    )
    calls = []

    def original(kind, key, cutoff):
        assert kind == "item"
        calls.append(key)
        return replies[key] if key in replies else parents[key]

    # A real model result is deliberately not fabricated: stop at the dispatch boundary.
    packets = []

    def stop_before_model(company):
        with transaction() as c:
            packet = sentiment.prepare(c, company, now)
        packets.append(packet)
        raise ValueError("Authored replay stop before model dispatch")

    news_watch.configure(
        owner, iid, True, now=now - timedelta(minutes=61), include_context=True
    )
    assert news_watch.run_once(
        owner,
        now=now,
        market_refresh=lambda _: None,
        social_refresh=lambda: None,
        context_fetcher=original,
        analyzer=stop_before_model,
    )
    saved = watch_history.history(owner, iid, now=now)["items"][0]
    assert (
        saved["status"] == "failed"
        and saved["details"]["failed_stage"] == "sentiment analysis"
    )
    detail = saved["details"]["context"]
    assert detail["status"] == "completed"
    assert detail["source_requests"] == len(calls) == 2 * len(PAIRS[symbol])
    packet = packets[0]
    assert len(packet["sources"]) == len(PAIRS[symbol])
    for s in packet["sources"]:
        child_key = s["post_key"][3:]
        context = s["conversation"]
        parent_key = context["parent_key"][3:]
        assert int(parent_key) == replies[child_key]["parent"]
        assert s["text"] == conversation.plain_summary(replies[child_key]["text"])
        assert (
            datetime.fromisoformat(context["published_at"]).timestamp()
            == parents[parent_key]["time"]
        )
        original_parent = parents[parent_key]
        for passage in context["passages"]:
            raw = (
                original_parent.get("title", "")
                if passage["id"] == "p0"
                else original_parent.get("text", "")
            )
            assert " ".join(passage["quote"].split()) in " ".join(
                conversation.plain_summary(raw).split()
            )
    assert ledger.snapshot() == budget and not saved["alert_count"]
    with transaction() as c:
        assert not one(
            c, "SELECT 1 FROM sentiment_analyses WHERE instrument_id=%s", (iid,)
        )
    news_watch.configure(owner, iid, False)
