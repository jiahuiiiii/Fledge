"""Authored answer pair in disposable browser data; no live provider request."""

import seed_sentiment_browser
from thesis.config import DATA, OWNER

assert str(DATA).startswith("/private/tmp/thesis-browser-")
from thesis import service
from thesis.models import SaveIdea
from thesis.research import idea_alerts, sentiment
from test_market import commit, news
from test_idea_alerts import provider
from test_sentiment import provider as classify

iid = seed_sentiment_browser.iid
service.save_idea(
    OWNER,
    SaveIdea(
        instrument_id=iid,
        expected_revision=1,
        question="What operating margin did Microsoft report for Q3?",
        reasoning="I want to establish the reported margin before deciding whether to investigate its causes.",
        status="draft",
        conditions=[],
    ),
)
commit(
    iid,
    [
        news(
            id=993,
            url="https://example.test/authored-margin-answer",
            headline="Authored Microsoft Q3 margin report",
            summary="Microsoft reports an operating margin of 38% for Q3. The report does not establish why the margin changed.",
        )
    ],
)
reading = sentiment.generate(iid, transport=classify("neutral"))


def answer(items):
    for i, item in enumerate(items):
        if i == 0:
            item.update(
                reasoning_segment_id=None,
                question_segment_id="q0",
                answer_target="What operating margin did Microsoft report for Q3?",
                answer_excerpt="Microsoft reports an operating margin of 38% for Q3.",
                passages=["p1"],
                explanation="The authored report gives the Q3 margin; it does not explain its causes.",
            )
        else:
            item.update(
                relation="context",
                connection_basis="background",
                answer_kind="background_only",
                answer_target=None,
                answer_excerpt=None,
            )
    return items


idea_alerts.generate(
    OWNER,
    iid,
    reading["id"],
    transport=provider("answers", answer_anchor="question", mutate=answer),
)
print("Authored answer pair ready; no external requests.")
