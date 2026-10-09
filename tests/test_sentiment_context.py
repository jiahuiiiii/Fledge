"""Saved original-parent inputs and downstream boundaries; no real model calls."""

from copy import deepcopy
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import json
import pytest
from thesis.db import transaction, one
from thesis.providers import ledger
from thesis.research import (
    sentiment as S,
    sentiment_context as C,
    conversation as cv,
    sentiment_history,
)
from thesis.monitoring import news_watch
from test_conversation import setup, fetcher, unlock
from test_sentiment import provider


def prepared(iid, now=None):
    with transaction() as c:
        return S.prepare(c, iid, now)


def with_context(owner):
    iid, p, child, parent = setup(owner)
    cv.collect(p["id"], fetcher=fetcher(child, parent, []))
    return iid, p, child, parent


def test_context_is_exact_separate_bounded_and_does_not_add_votes(owner):
    iid, p, _, parent = with_context(owner)
    packet = prepared(iid)
    child = next(s for s in packet["sources"] if s["id"] == str(p["id"]))
    assert child["conversation"]["body"] == parent["text"]
    wire = json.loads(S.request_for(packet)["input"][1]["content"])
    projected = next(s for s in wire["sources"] if s["id"] == child["id"])
    assert len(projected["conversation"]["passages"]) == 2
    assert all(p["id"] != "p0" for p in projected["conversation"]["passages"])
    assert (
        "checked_at" not in projected["conversation"]
        and "result_id" not in projected["conversation"]
    )
    reading = S.generate(iid, transport=provider())
    assert reading["coverage"]["parent_contexts"] == 1
    assert reading["summary"]["social_platforms"]["hackernews"]["selected"] == 1
    assert len(reading["items"]) == len(packet["sources"])
    item = next(i for i in reading["items"] if i["source_id"] == child["id"])
    assert item["conversation"]["citations"][0]["quote"] in parent["text"]
    assert {q["source_id"] for q in item["citations"]} == {child["id"]}


def test_rechecking_identical_parent_reuses_original_analysis_and_charge(owner):
    iid, p, child, parent = with_context(owner)
    original = S.generate(iid, transport=provider())
    budget = ledger.snapshot()
    unlock(p["id"])
    cv.collect(p["id"], fetcher=fetcher(child, parent, []))
    repeated = S.generate(
        iid, transport=lambda _: pytest.fail("Unchanged context billed again")
    )
    assert repeated == original and ledger.snapshot() == budget


def test_loading_parent_never_changes_old_analysis_and_history_explains_context(owner):
    iid, p, child, parent = setup(owner)
    old = S.generate(iid, transport=provider())
    cv.collect(p["id"], fetcher=fetcher(child, parent, []))
    new = S.generate(iid, transport=provider())
    assert new["id"] != old["id"]
    with transaction() as c:
        previous = one(c, "SELECT * FROM sentiment_analyses WHERE id=%s", (old["id"],))
        assert S.present(c, previous) == old
    delta = sentiment_history.compare(iid, old["id"], new["id"])
    assert delta["same_selected_text"] and delta["parent_context_changed"]
    assert not delta["method_changed"]


@pytest.mark.parametrize(
    "fault", ["missing", "unknown", "duplicate", "title_only", "foreign_item"]
)
def test_bad_context_citations_fail_before_publication(owner, fault):
    iid, _, _, _ = with_context(owner)
    packet = prepared(iid)
    hn_source = next(s for s in packet["sources"] if s.get("conversation"))

    def bad(items):
        item = next(i for i in items if i["id"] == hn_source["label"])
        if fault == "missing":
            item["context_passages"] = []
        elif fault == "unknown":
            item["context_passages"] = ["p999"]
        elif fault == "duplicate":
            item["context_passages"] *= 2
        elif fault == "title_only":
            item["passages"] = ["p0"]
        else:
            next(i for i in items if i["id"] != hn_source["label"])[
                "context_passages"
            ] = ["p1"]
        return items

    with pytest.raises(ValueError):
        S.generate(iid, transport=provider(mutate=bad))
    with transaction() as c:
        assert not one(
            c, "SELECT 1 FROM sentiment_analyses WHERE instrument_id=%s", (iid,)
        )


def test_older_future_failed_and_removed_context_not_supplied(owner):
    iid, p, child, parent = with_context(owner)
    now = datetime.now(timezone.utc)
    fresh = [dict(id=str(p["id"]), platform="hackernews")]
    with transaction() as c:
        C.attach(c, fresh, p["available_at"])
    assert not fresh[0].get("conversation")
    assert not any(
        s.get("conversation")
        for s in prepared(iid, now + timedelta(hours=25))["sources"]
    )
    unlock(p["id"])
    cv.collect(
        p["id"],
        fetcher=fetcher(child | {"text": "Microsoft changed text."}, parent, []),
    )
    assert not any(s.get("conversation") for s in prepared(iid)["sources"])


def test_parent_removal_withholds_consumed_analysis_history_and_new_themes(owner):
    from thesis.research import discussion_themes as D

    iid, p, _, _ = with_context(owner)
    reading = S.generate(iid, transport=provider())
    with transaction(source=True) as c:
        c.execute("INSERT INTO hn_withdrawals VALUES('hn:99',now())")
    with transaction() as c:
        stored = one(
            c, "SELECT * FROM sentiment_analyses WHERE id=%s", (reading["id"],)
        )
        visible = S.present(c, stored)
    assert visible["withheld"] and visible["sources"] == visible["items"] == []
    assert sentiment_history.history(iid)["items"][0]["withheld"]
    budget = ledger.snapshot()
    with pytest.raises(ValueError, match="Source access changed"):
        D.generate(
            iid,
            reading["id"],
            transport=lambda _: pytest.fail("Withdrawn context dispatched"),
        )
    assert ledger.snapshot() == budget
    assert not any(s.get("conversation") for s in prepared(iid)["sources"])


def test_removal_during_analysis_withholds_response(owner):
    iid, _, _, _ = with_context(owner)

    def withdraw(b):
        with transaction(source=True) as c:
            c.execute("INSERT INTO hn_withdrawals VALUES('hn:99',now())")
        return provider()(b)

    # The batched route now stops before publishing a combined analysis when
    # access changes in flight. The response/charge remains in the ledger.
    with pytest.raises(ValueError, match="source access changed"):
        S.generate(iid, transport=withdraw)
    with transaction() as c:
        assert one(c, "SELECT count(*) n FROM sentiment_analyses WHERE instrument_id=%s", (iid,))["n"] == 0


def test_context_change_is_not_alerted_as_a_new_opinion_even_with_new_text():
    # Five negative -> five positive groups plus a genuinely new comment.
    sources = [
        dict(
            id=str(i),
            channel="social",
            platform="hackernews",
            content_hash=str(i),
            text="Original " + str(i),
            title="HN",
            conversation=dict(content_key="old"),
        )
        for i in range(5)
    ]

    def record(sources, tone):
        items = [
            dict(
                source_id=s["id"],
                channel="social",
                relevance="relevant",
                sentiment=tone,
                statement="opinion",
                topic="general",
            )
            for s in sources
        ]
        return dict(
            packet=dict(sources=sources),
            result=dict(
                items=items,
                summary=S.summarize(items, sources),
                prompt_version=S.PROMPT,
                model="test",
                summary_policy=S.POLICY,
            ),
        )

    before = record(sources, "negative")
    current = deepcopy(sources) + [
        dict(
            sources[0],
            id="new",
            content_hash="new",
            text="New unrelated-to-context opinion",
        )
    ]
    current[0]["conversation"]["content_key"] = "changed"
    assert news_watch.changes(before, record(current, "positive")) == []
    current[0]["conversation"]["content_key"] = "old"
    assert (
        news_watch.changes(before, record(current, "positive"))[0]["kind"]
        == "sentiment"
    )


def test_context_count_and_bytes_are_bounded_without_truncating(monkeypatch):
    now = datetime.now(timezone.utc)

    def row(_, query, args):
        if "hn_withdrawals" in query:
            return None
        return dict(
            id=uuid4(),
            outcome="available",
            checked_at=now,
            parent_key="hn:99",
            parent_type="comment",
            title="Parent comment",
            body="Microsoft software is useful.",
            url="https://news.ycombinator.com/item?id=99",
            published_at=now - timedelta(minutes=2),
        )

    monkeypatch.setattr(C, "one", row)
    sources = [dict(id=str(uuid4()), platform="hackernews") for _ in range(8)]
    C.attach(None, sources, now)
    assert sum(bool(s.get("conversation")) for s in sources) == 4
    assert all(s["context_status"] == "sample_limit" for s in sources[4:])
    monkeypatch.setattr(C, "MAX_BYTES", 1)
    fresh = [dict(id=str(uuid4()), platform="hackernews")]
    C.attach(None, fresh, now)
    assert (
        fresh[0]["context_status"] == "sample_limit" and "conversation" not in fresh[0]
    )


def test_context_evidence_in_alert_export_is_escaped_and_withdrawn(owner):
    from psycopg.types.json import Jsonb
    from thesis import review_digest

    iid, _, _, _ = with_context(owner)
    reading = S.generate(iid, transport=provider())
    selected = next(i for i in reading["items"] if i.get("conversation"))
    # Authored delivery fixture tests the export/access boundary, not alert rules.
    selected["conversation"]["citations"][0]["quote"] += " <script>authored</script>"
    news_watch.configure(owner, iid, False)
    with transaction(owner) as c:
        c.execute(
            "INSERT INTO research_alerts VALUES(%s,%s,%s,'sentiment',%s,%s,NULL,%s,now())",
            (
                uuid4(),
                owner,
                iid,
                reading["id"],
                reading["id"],
                Jsonb(dict(reason="Authored delivery fixture.", items=[selected])),
            ),
        )
    budget = ledger.snapshot()
    html = review_digest.download(owner)[1]
    assert (
        "Parent context used for this label" in html
        and "not another sentiment vote" in html
    )
    assert "&lt;script&gt;authored&lt;/script&gt;" in html and "<script>" not in html
    with transaction(source=True) as c:
        c.execute("INSERT INTO hn_withdrawals VALUES('hn:99',now())")
    html = review_digest.download(owner)[1]
    assert (
        "source excerpts are withheld" in html
        and "I think Microsoft software" not in html
    )
    assert ledger.snapshot() == budget
