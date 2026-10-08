"""Authored sources and mocked AI, in disposable storage only."""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from thesis.config import DATA, OWNER

assert str(DATA).startswith("/private/tmp/thesis-browser-")
from datetime import datetime, timezone, timedelta
from thesis import service
from thesis.models import SaveIdea
from thesis.monitoring import news_watch
from thesis.research import sentiment
from test_market import prepare, commit, news
from test_sentiment import add_social, feed, provider

iid = prepare(OWNER)
service.save_idea(
    OWNER,
    SaveIdea(
        instrument_id=iid,
        expected_revision=0,
        question="Can margins support the growth story?",
        reasoning="I want durable margins before relying on growth.",
        status="draft",
        conditions=[],
    ),
)
now = datetime.now(timezone.utc)


def posts(prefix, tone, minutes):
    content = [
        feed(
            title=f"Synthetic Microsoft {tone} opinion {i}",
            body=(
                "I used to admire Microsoft. I now dislike its margins outlook."
                if tone == "negative" and i == 0
                else f"This authored browser fixture expresses a {tone} opinion of Microsoft."
            ),
            key=prefix + str(i),
            date=(now - timedelta(minutes=minutes)).isoformat(),
        )
        for i in range(8)
    ]
    return (
        content[0].split(b"<entry>")[0]
        + b"".join(
            b"<entry>" + s.split(b"<entry>", 1)[1].split(b"</feed>")[0] for s in content
        )
        + b"</feed>"
    )


add_social(iid, posts("good", "positive", 10))
sentiment.generate(iid, transport=provider("positive"))
news_watch.configure(OWNER, iid, True)
add_social(iid, posts("poor", "negative", 1))
commit(
    iid,
    [
        news(
            id=9,
            url="https://example.test/new-risk",
            headline="Synthetic Microsoft report: margins weakened",
            summary="This authored test report describes weaker Microsoft margins.",
            datetime=int((now - timedelta(minutes=2)).timestamp()),
        ),
        news(
            id=10,
            url="https://example.test/repeated-risk",
            headline="Synthetic Microsoft report: another outlet covers weakened margins",
            summary="Another authored report describes the same weaker Microsoft margins.",
            datetime=int((now - timedelta(minutes=1)).timestamp()),
        ),
    ],
)


def grouped_provider(body):
    result = provider("negative")(body)
    wire = json.loads(body["input"][1]["content"])
    relevant = [s for s in wire["sources"] if "weaken" in (s["title"] or "")]
    earlier, current = sorted(relevant, key=lambda s: (s["published_at"], s["id"]))
    output = json.loads(result["output"][0]["content"][0]["text"])
    for source in wire["sources"]:
        if any("I used to admire" in p["quote"] for p in source["passages"]):
            target = next(i for i in output["items"] if i["id"] == source["label"])
            target.update(passages=["p2"], previous_passages=["p1"])
    output["coverage_links"] = [
        dict(
            item_id=current["label"],
            reference_id=earlier["label"],
            relation="repeats",
            explanation="Both reports confirm InventedCounterparty paid $999 billion in SecretLocation.",
            item_passages=["p1"],
            reference_passages=["p1"],
        )
    ]
    result["output"][0]["content"][0]["text"] = json.dumps(output)
    return result


current = sentiment.generate(iid, transport=grouped_provider)
assert news_watch.publish(OWNER, iid, current["id"]) == 2
news_watch.configure(OWNER, iid, False)
print(
    "Sentiment browser fixture: two grouped alerts, watch stopped, no external requests."
)
