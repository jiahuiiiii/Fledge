"""Seed an exact private-review history with mocked providers in disposable storage."""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from thesis.config import DATA, OWNER

assert str(DATA).startswith("/private/tmp/thesis-browser-")

# This fixture creates SEC-shaped fundamentals, fictional company news and a
# mocked shared briefing. It does not read a key or call an external provider.
from seed_market_browser import company
from thesis import service
from thesis.db import transaction
from thesis.models import SaveIdea
from thesis.providers.settings import MODEL
from thesis.research import idea_review, market, market_brief

REASONING = (
    "A proposed enterprise contract could support recurring revenue. "
    "I would reconsider if Microsoft denied the contract."
)
ORIGINAL_TEXT = (
    "This is authored browser-test evidence. The company has not confirmed "
    "the reported contract."
)
CORRECTED_TEXT = (
    "Synthetic correction: Microsoft denied the proposed enterprise contract. "
    "The earlier report was unconfirmed. This is authored browser-test evidence. "
    "An unfinished synthetic description mentions future contract terms..."
)


def response(points, model=MODEL):
    return dict(
        id="resp_synthetic_idea_" + str(uuid4()),
        model=model,
        service_tier="default",
        status="completed",
        usage=dict(input_tokens=100, output_tokens=80),
        output=[
            dict(
                type="message",
                content=[
                    dict(type="output_text", text=json.dumps(dict(points=points)))
                ],
            )
        ],
    )


def private_provider(body):
    packet = json.loads(body["input"][1]["content"])
    assert all(
        segment["quote"] in REASONING for segment in packet["reasoning_segments"]
    )
    passages = [
        (source, passage)
        for source in packet["sources"]
        for passage in source["passages"]
    ]
    denied = next(
        (
            pair
            for pair in passages
            if "Microsoft denied the proposed enterprise contract" in pair[1]["quote"]
        ),
        None,
    )
    if denied:
        assert packet["omitted_fragment_count"] == 1
        assert "unfinished synthetic description" not in json.dumps(packet)
    source, passage = denied or next(
        pair
        for pair in passages
        if "company has not confirmed the reported contract" in pair[1]["quote"]
    )
    reasoning_quote = (
        "I would reconsider if Microsoft denied the contract."
        if denied
        else "A proposed enterprise contract could support recurring revenue."
    )
    segment = next(
        segment
        for segment in packet["reasoning_segments"]
        if reasoning_quote in segment["quote"]
    )
    return response(
        [
            dict(
                relation="challenges" if denied else "unclear",
                reasoning_segment_id=segment["id"],
                text=(
                    "The corrected source denies the contract, directly testing your stated reason to reconsider. "
                    "The reported growth and margin conditions are unchanged."
                    if denied
                    else "The original report is unconfirmed, so it does not establish the proposed source of recurring revenue."
                ),
                citations=[dict(source_id=source["id"], passage_id=passage["id"])],
            )
        ],
        model=body["model"],
    )


def latest_assessment():
    for _ in range(100):
        service.queue_current(OWNER)
        service.work_once(OWNER)
        state = service.state(OWNER, company)
        evaluations = state["versions"][0]["evaluations"]
        if (
            evaluations
            and evaluations[0]["manifest"]["snapshot_id"] == state["snapshot_id"]
        ):
            return state, evaluations[0]
        time.sleep(0.05)
    raise RuntimeError("Synthetic assessment did not complete")


saved = service.save_idea(
    OWNER,
    SaveIdea(
        instrument_id=company,
        expected_revision=0,
        question="Would the proposed enterprise contract support recurring demand?",
        reasoning=REASONING,
        status="monitoring",
        conditions=[
            dict(
                condition_id=uuid4(),
                metric=metric,
                operator=">=",
                threshold=value,
                period_type="annual",
            )
            for metric, value in (("revenue_growth", "15"), ("operating_margin", "20"))
        ],
    ),
)
first, initial = latest_assessment()
original_results = initial["results"]
idea_review.generate(
    OWNER,
    saved["version_id"],
    initial["manifest"]["snapshot_id"],
    str(initial["id"]),
    transport=private_provider,
)

now = datetime.now(timezone.utc)
articles, rejected = market.normalize_news(
    [
        dict(
            id=0,
            headline="Synthetic correction: Microsoft denies the proposed contract",
            summary=CORRECTED_TEXT,
            related="MSFT",
            datetime=int(now.timestamp()),
            source="Synthetic Wire",
            url="https://example.test/synthetic-0",
        )
    ],
    "MSFT",
    now,
)
with transaction(source=True) as conn:
    market.collection_lock(conn)
    market.commit_news(conn, company, articles, rejected, now)
    conn.execute(
        "UPDATE market_refresh_state SET completed_at=%s,last_attempt_at=%s,news_count=1 WHERE instrument_id=%s",
        (now, now, company),
    )
latest, corrected = latest_assessment()
assert str(initial["id"]) != str(corrected["id"])
assert initial["outcome"] == corrected["outcome"] == "met"
assert [(r["observed_value"], r["outcome"]) for r in original_results] == [
    (r["observed_value"], r["outcome"]) for r in corrected["results"]
]
idea_review.generate(
    OWNER,
    saved["version_id"],
    corrected["manifest"]["snapshot_id"],
    str(corrected["id"]),
    transport=private_provider,
)


def shared_provider(body):
    packet = json.loads(body["input"][1]["content"])
    source = next(
        s for s in packet["sources"]
        if "Microsoft denied the proposed enterprise contract" in s["text"]
    )
    assert "unfinished synthetic description" not in json.dumps(packet)
    citation = dict(source_id=source["id"], quote=source["text"])
    return response(
        [
            dict(
                kind="reported",
                title="Microsoft denies the reported contract",
                text="The supplied synthetic correction says Microsoft denied the proposed contract.",
                citations=[citation],
            ),
            dict(
                kind="uncertainty",
                title="Other growth questions remain open",
                text="This correction does not establish the outlook for other sources of demand.",
                citations=[citation],
            ),
        ],
        model=body["model"],
    )


market_brief.generate(company, transport=shared_provider)
final = service.state(OWNER, company)
assert len(final["versions"][0]["evidence_reviews"]) == 2
assert any(c["kind"] == "evidence" for c in final["changes"])

# A qualitative-only idea must retain every comparison after another source
# snapshot, a reasoning edit and archiving, without any numeric assessment.
aurora = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
draft_reasoning = "Sensor launch interest does not prove recurring customer demand."
draft = service.save_idea(
    OWNER,
    SaveIdea(
        instrument_id=aurora,
        expected_revision=0,
        question="Could the sensor launch support recurring demand?",
        reasoning=draft_reasoning,
        status="draft",
        conditions=[],
    ),
)


def qualitative_provider(label):
    def provider(body):
        packet = json.loads(body["input"][1]["content"])
        source = packet["sources"][0]
        passage = source["passages"][0]
        return response(
            [
                dict(
                    relation="unclear",
                    reasoning_segment_id=packet["reasoning_segments"][0]["id"],
                    text=label + " This supplied evidence does not establish the full saved belief.",
                    citations=[dict(source_id=source["id"], passage_id=passage["id"])],
                )
            ],
            model=body["model"],
        )
    return provider


idea_review.generate(
    OWNER,
    draft["version_id"],
    service.state(OWNER, aurora)["snapshot_id"],
    transport=qualitative_provider("First qualitative comparison before the later development."),
)
service.advance(OWNER, 0, aurora)
idea_review.generate(
    OWNER,
    draft["version_id"],
    service.state(OWNER, aurora)["snapshot_id"],
    transport=qualitative_provider("Second qualitative comparison after the later development."),
)
revised = service.save_idea(
    OWNER,
    SaveIdea(
        instrument_id=aurora,
        expected_revision=1,
        question="Can component supply remain reliable?",
        reasoning="Component supply must remain reliable before I can form a stronger view.",
        status="draft",
        conditions=[],
    ),
)
idea_review.generate(
    OWNER,
    revised["version_id"],
    service.state(OWNER, aurora)["snapshot_id"],
    transport=qualitative_provider("Comparison of the revised component-supply reasoning."),
)
service.save_idea(
    OWNER,
    SaveIdea(
        instrument_id=aurora,
        expected_revision=2,
        question="Can component supply remain reliable?",
        reasoning="Component supply must remain reliable before I can form a stronger view.",
        status="archived",
        conditions=[],
    ),
)
qualitative = service.state(OWNER, aurora)
assert all(not v["evaluations"] for v in qualitative["versions"])
assert sum(len(v["evidence_reviews"]) for v in qualitative["versions"]) == 3
print(
    "Seeded exact numeric/source history and three qualitative comparisons across snapshots, revision and archive; no external calls"
)
