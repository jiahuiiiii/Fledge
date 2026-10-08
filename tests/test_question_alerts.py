"""Questions stay distinct from beliefs, with exact anchors and old-revision delivery rules."""

import json
from copy import deepcopy
import pytest
from thesis import service, review_digest
from thesis.models import SaveIdea
from thesis.db import transaction, one
from thesis.research import idea_alerts
from thesis.monitoring import news_watch
from thesis.providers import ledger
from test_idea_alerts import setup, newer, provider


def answer_provider(anchor="question", fault=None, side_effect=None):
    def mutate(items):
        for i in items:
            i.update(
                relation="answers",
                reasoning_segment_id="r0" if anchor == "reasoning" else None,
                question_segment_id="q0" if anchor == "question" else None,
                explanation="The report supplies part of the requested evidence; the rest remains unresolved.",
            )
            if fault == "missing":
                i.update(reasoning_segment_id=None, question_segment_id=None)
            elif fault == "foreign":
                i["question_segment_id"] = "q99"
            elif fault == "both":
                i["reasoning_segment_id"] = "r0"
            elif fault == "stance":
                i["relation"] = "supports"
            elif fault == "unrelated":
                i["relation"] = "unrelated"
        return items

    return provider(
        "answers", mutate=mutate, side_effect=side_effect, answer_anchor=anchor
    )


def question(owner):
    iid, saved, analysis = setup(owner)
    saved = service.save_idea(
        owner,
        SaveIdea(
            instrument_id=iid,
            expected_revision=1,
            question="What does Microsoft report about demand?",
            reasoning="I want to know what Microsoft reports about demand. I have not formed an investment view.",
            status="draft",
            conditions=[],
        ),
    )
    return iid, saved, analysis


@pytest.mark.parametrize("anchor", ["question", "reasoning"])
def test_answer_is_reviewable_with_exact_saved_anchor_without_resolving_idea(
    owner, anchor
):
    iid, saved, analysis = question(owner)
    result = idea_alerts.generate(
        owner, iid, analysis["id"], transport=answer_provider(anchor)
    )
    before = ledger.snapshot()
    assert (
        idea_alerts.generate(
            owner,
            iid,
            analysis["id"],
            transport=lambda _: pytest.fail("cached answer called model"),
        )
        == result
    )
    assert ledger.snapshot() == before
    with transaction(owner) as c:
        record = idea_alerts.list_for(c, owner)[0]
        item = record["items"][0]
        assert (
            record["published"]
            and record["noteworthy_count"] == 1
            and not record["review_action"]
        )
        assert item["relation"] == "answers"
        assert item["question_quote"] == (
            "What does Microsoft report about demand?" if anchor == "question" else None
        )
        assert item["reasoning_quote"] == (
            "I want to know what Microsoft reports about demand."
            if anchor == "reasoning"
            else None
        )
        current = idea_alerts.current_idea(c, owner, iid)
        assert (
            str(current["id"]) == saved["version_id"] and current["status"] == "draft"
        )
    _, html = idea_alerts.download(owner, result["id"])
    assert "Evidence toward your question" in html
    assert (
        "Your saved question" if anchor == "question" else "Your saved words"
    ) in html
    digest = review_digest.prepare(owner)
    assert any(str(r["id"]) == result["id"] for r in digest["records"])
    _, digest_html = review_digest.download(owner)
    assert "Evidence toward your question (research remains open)" in digest_html
    idea_alerts.review(owner, result["id"], "unresolved")
    with transaction(owner) as c:
        assert idea_alerts.list_for(c, owner)[0]["review_action"] == "unresolved"
        assert str(idea_alerts.current_idea(c, owner, iid)["id"]) == saved["version_id"]


@pytest.mark.parametrize("fault", ["missing", "foreign", "both", "stance", "unrelated"])
def test_invalid_question_link_is_not_published(owner, fault):
    iid, saved, analysis = question(owner)
    with pytest.raises(ValueError):
        idea_alerts.generate(
            owner, iid, analysis["id"], transport=answer_provider(fault=fault)
        )
    with transaction(owner) as c:
        assert not idea_alerts.list_for(c, owner)


def test_answer_watch_preserves_quiet_baseline_and_does_not_repeat_same_content(owner):
    iid, saved, analysis = question(owner)
    news_watch.configure(owner, iid, True, match_idea=True)
    assert (
        idea_alerts.generate(
            owner,
            iid,
            analysis["id"],
            automatic=True,
            transport=lambda _: pytest.fail("baseline"),
        )["status"]
        == "no_new_sources"
    )
    changed = newer(iid)
    result = idea_alerts.generate(
        owner, iid, changed["id"], automatic=True, transport=answer_provider()
    )
    with transaction(owner) as c:
        record = idea_alerts.list_for(c, owner)[0]
        assert record["delivery_mode"] == "watch" and record["noteworthy_count"] == 1
    before = ledger.snapshot()
    assert (
        idea_alerts.generate(
            owner,
            iid,
            changed["id"],
            automatic=True,
            transport=lambda _: pytest.fail("duplicate answer"),
        )["status"]
        == "no_new_sources"
    )
    assert ledger.snapshot() == before


def test_question_edit_during_answer_check_keeps_original_anchor_in_history(owner):
    iid, saved, analysis = question(owner)

    def edit():
        service.save_idea(
            owner,
            SaveIdea(
                instrument_id=iid,
                expected_revision=2,
                question="Has my question changed?",
                reasoning="I need a different research question.",
                status="draft",
                conditions=[],
            ),
        )

    result = idea_alerts.generate(
        owner, iid, analysis["id"], transport=answer_provider(side_effect=edit)
    )
    assert result["status"] == "historical_only"
    with transaction(owner) as c:
        record = idea_alerts.list_for(c, owner)[0]
        assert not record["published"] and record["historical_revision"]
        assert (
            record["items"][0]["question_quote"]
            == "What does Microsoft report about demand?"
        )


def test_question_answer_request_uses_exact_question_segments_and_changes_identity(
    owner,
):
    iid, saved, analysis = question(owner)
    with transaction(owner) as c:
        packet, _ = idea_alerts.prepare(c, owner, iid, analysis["id"])
    body = idea_alerts.request_for(packet)
    wire = json.loads(body["input"][1]["content"])
    assert wire["question_segments"] == [dict(id="q0", quote=packet["question"])]
    changed = deepcopy(packet)
    changed["question"] = "Is this evidence of actual paid adoption?"
    assert idea_alerts.identity(owner, packet) != idea_alerts.identity(owner, changed)
    schema = body["text"]["format"]["schema"]["properties"]["items"]["items"]["anyOf"][
        0
    ]
    assert set(schema["required"]) == set(schema["properties"])
