"""Authored sources and mocked model checks only, in disposable storage."""

import seed_sentiment_browser
from thesis.config import DATA, OWNER

assert str(DATA).startswith("/private/tmp/thesis-browser-")
from thesis import service
from thesis.models import SaveIdea
from thesis.research import idea_alerts
from test_idea_alerts import provider
from test_check_purpose import question_provider
from unittest.mock import patch

iid = seed_sentiment_browser.iid
analysis = seed_sentiment_browser.current
# Retain an earlier selection record alongside current checks.
original_prepare = idea_alerts.prepare


def legacy_prepare(*args, **kwargs):
    packet, status = original_prepare(*args, **kwargs)
    packet.pop("selection_policy")
    packet.pop("unusable_source_count")
    packet.pop("purpose")
    return packet, status


with patch.object(idea_alerts, "prepare", legacy_prepare):
    idea_alerts.generate(OWNER, iid, analysis["id"], transport=provider("risk"))
service.save_idea(
    OWNER,
    SaveIdea(
        instrument_id=iid,
        expected_revision=1,
        question="What does the report say about Microsoft margins?",
        reasoning="I want to investigate the reported margin change before forming a view.",
        status="draft",
        conditions=[],
    ),
)


def answer(items):
    for i, item in enumerate(items):
        item.update(
            relation="answers" if i == 0 else "context",
            reasoning_segment_id=None,
            question_segment_id="q0",
            explanation=(
                "The authored report describes weaker margins; it does not establish their cause."
                if i == 0
                else "This social opinion does not supply reported margin evidence."
            ),
        )
    return items


idea_alerts.generate(
    OWNER,
    iid,
    analysis["id"],
    purpose="question",
    transport=question_provider(mutate=answer),
)
service.save_idea(
    OWNER,
    SaveIdea(
        instrument_id=iid,
        expected_revision=2,
        question="Does adoption justify the product story?",
        reasoning="I now want actual enterprise adoption evidence before relying on a new product story.",
        status="draft",
        conditions=[],
    ),
)
idea_alerts.generate(OWNER, iid, analysis["id"], transport=provider("possible_link"))
print(
    "Private alert fixture: two earlier-revision alerts including a question answer and a quiet possible-connection check; no external requests."
)
