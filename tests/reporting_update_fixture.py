"""Wholly authored sequence, reusable only by disposable tests/browser seeds."""

import json
from datetime import datetime, timezone, timedelta
from thesis import service
from thesis.models import SaveIdea
from thesis.research import sentiment
from thesis.monitoring import news_watch
from test_market import prepare, commit, news
from test_sentiment import provider


def classify(body):
    raw = provider("neutral")(body)
    supplied = json.loads(body["input"][1]["content"])
    output = json.loads(raw["output"][0]["content"][0]["text"])
    by_label = {s["label"]: s for s in supplied["sources"]}
    all_sources = supplied["sources"] + supplied["comparison_sources"]
    old = next(
        (
            s
            for s in all_sources
            if s["title"] == "Authored Microsoft service-closure report"
        ),
        None,
    )
    update = next(
        (
            s
            for s in supplied["sources"]
            if s["title"] == "Authored Microsoft clarification"
        ),
        None,
    )
    for item in output["items"]:
        s = by_label[item["id"]]
        item["sentiment"] = (
            "negative"
            if s["title"] == "Authored Microsoft service-closure report"
            else "neutral"
        )
        item["basis"] = "stated_outcome" if item["sentiment"] == "negative" else "descriptive"
        if "reporting" in item:
            item["reporting"].update(impact="adverse" if item["sentiment"] == "negative" else "not_stated")
    if old and update:
        output["coverage_links"] = [
            dict(
                item_id=update["label"],
                reference_id=old["label"],
                relation="contradicts",
                explanation="The newer authored report denies the earlier service-closure claim.",
                item_passages=["p1"],
                reference_passages=["p1"],
            )
        ]
    raw["output"][0]["content"][0]["text"] = json.dumps(output)
    return raw


def begin(owner, *, due=True):
    iid = prepare(owner)
    service.save_idea(
        owner,
        SaveIdea(
            instrument_id=iid,
            expected_revision=0,
            question="Will this service remain available?",
            reasoning="I need to understand whether a reported closure affects the service.",
            status="draft",
            conditions=[],
        ),
    )
    sentiment.generate(iid, transport=classify)
    now = datetime.now(timezone.utc)
    news_watch.configure(
        owner, iid, True, now=now - timedelta(minutes=61) if due else now
    )
    return iid, now


def acquire(iid, *, clarification=False):
    now = datetime.now(timezone.utc)
    records = [
        news(
            id=701,
            url="https://example.test/authored-closure",
            headline="Authored Microsoft service-closure report",
            summary="An unconfirmed report says Microsoft will close the service.",
            datetime=int((now - timedelta(minutes=4)).timestamp()),
        )
    ]
    if clarification:
        records.append(
            news(
                id=702,
                url="https://example.test/authored-clarification",
                headline="Authored Microsoft clarification",
                summary="Microsoft denies that the service will close. It says the service remains available.",
                datetime=int((now - timedelta(minutes=2)).timestamp()),
            )
        )
    commit(iid, records)


def run(owner, now, *, refresh=None, analyzer=None):
    return news_watch.run_once(
        owner,
        now=now,
        market_refresh=refresh or (lambda _: None),
        social_refresh=lambda: None,
        analyzer=analyzer or (lambda iid: sentiment.generate(iid, transport=classify)),
    )
