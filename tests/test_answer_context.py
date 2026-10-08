"""Private question context from retained sources; mocked transport only."""

from copy import deepcopy
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import json
import pytest
from thesis import service
from thesis.db import transaction, one
from thesis.providers import ledger
from thesis.research import answers as A, conversation as cv
from test_sentiment_context import with_context
from test_conversation import setup, fetcher, unlock
from test_research_answers import response

QUESTION = "What do these technical users say about Microsoft software?"


def request(owner, iid, now=None, include_social=True):
    with transaction(owner) as c:
        return A.prepare(
            c, owner, iid, A.Ask(question=QUESTION, include_social=include_social), now
        )


def contextual_response(body, change=None):
    def answer(value, wire):
        child = next(s for s in wire["sources"] if s.get("conversation"))
        cite = dict(source_id=child["id"], passage_id=child["passages"][0]["id"])
        parent = dict(
            source_id=child["id"], passage_id=child["conversation"]["passages"][0]["id"]
        )
        value.update(
            answer="This comment expresses a view about Microsoft software; it is not a representative investor sample.",
            answer_citations=[cite],
            answer_context_citations=[parent],
            evidence=[
                dict(
                    kind="social_opinion",
                    text="The reply and parent are separate messages; neither establishes a company financial result.",
                    citations=[cite],
                    context_citations=[parent],
                )
            ],
        )
        if change:
            change(value, wire)

    return response(body, answer)


def test_question_uses_exact_saved_parent_without_idea_or_sentiment_step(owner):
    iid, post, child, parent = with_context(owner)
    packet = request(owner, iid)
    wire = json.loads(A.request_for(packet)["input"][1]["content"])
    source = next(s for s in wire["sources"] if s.get("conversation"))
    assert source["platform"] == "hackernews" and "Hacker News" in source["publisher"]
    assert not any(p["id"] == "p0" for p in source["passages"])
    assert len(wire["sources"]) == len(packet["sources"]) == 3
    assert {s["channel"] for s in wire["sources"]} == {"news", "social", "filing"}
    assert packet["coverage"]["selected_social_platforms"] == {"hackernews": 1}
    assert packet["coverage"]["parent_contexts"] == 1
    before = ledger.snapshot()
    saved = A.generate(
        owner, iid, A.Ask(question=QUESTION), transport=contextual_response
    )
    assert ledger.snapshot()["calls"] == before["calls"] + 1
    assert not saved["withheld"] and not saved["earlier_method"]
    result = saved["result"]
    assert result["answer_contexts"][0]["body"] == parent["text"]
    assert result["answer_contexts"][0]["source_id"] == str(post["id"])
    assert all(c["quote"] in child["text"] for c in result["answer_citations"])
    assert all(
        c["quote"] in parent["text"] for c in result["answer_contexts"][0]["citations"]
    )
    assert result["evidence"][0]["contexts"] == result["answer_contexts"]
    with transaction(owner) as c:
        assert not one(
            c, "SELECT 1 FROM sentiment_analyses WHERE instrument_id=%s", (iid,)
        )
        assert not service.state(owner, iid)["versions"]
        row = one(c, "SELECT * FROM research_answers WHERE id=%s", (saved["id"],))
        assert (
            str(
                one(
                    c, "SELECT owner_id FROM model_calls WHERE id=%s", (row["call_id"],)
                )["owner_id"]
            )
            == owner
        )
    other = str(uuid4())
    with pytest.raises(service.Missing):
        A.get(other, saved["id"])
    with pytest.raises(service.Missing):
        A.download(other, saved["id"])
    assert A.history(other, iid)["items"] == []


def test_identical_parent_recheck_reuses_original_question_without_charge(owner):
    iid, post, child, parent = with_context(owner)
    saved = A.generate(
        owner, iid, A.Ask(question=QUESTION), transport=contextual_response
    )
    budget = ledger.snapshot()
    unlock(post["id"])
    cv.collect(post["id"], fetcher=fetcher(child, parent, []))
    repeated = A.generate(
        owner,
        iid,
        A.Ask(question=QUESTION),
        transport=lambda _: pytest.fail("Identical parent recheck billed again"),
    )
    assert repeated == saved and ledger.snapshot() == budget


def test_old_answer_stays_original_when_parent_is_later_loaded_or_changed(
    owner, monkeypatch
):
    iid, post, child, parent = setup(owner)
    with monkeypatch.context() as m:
        m.setattr(A, "PROMPT", "thesis-research-answer-3")
        old = A.generate(owner, iid, A.Ask(question=QUESTION), transport=response)
    cv.collect(post["id"], fetcher=fetcher(child, parent, []))
    new = A.generate(
        owner, iid, A.Ask(question=QUESTION), transport=contextual_response
    )
    assert new["id"] != old["id"]
    assert A.get(owner, old["id"])["result"] == old["result"]
    assert A.get(owner, old["id"])["earlier_method"]
    unlock(post["id"])
    cv.collect(
        post["id"],
        fetcher=fetcher(
            child,
            parent | {"text": "Microsoft software raises a different question now."},
            [],
        ),
    )
    assert A.get(owner, new["id"])["result"] == new["result"]
    assert request(owner, iid)["sources"] != new["sources"]


@pytest.mark.parametrize(
    "fault",
    [
        "missing",
        "unknown",
        "duplicate",
        "parent_only",
        "title_only",
        "too_many",
        "news_parent",
        "point_missing",
        "insufficient_parent",
    ],
)
def test_answer_and_point_parent_evidence_boundaries(owner, fault):
    iid, _, _, _ = with_context(owner)
    packet = request(owner, iid)

    def bad(value, wire):
        child = next(s for s in wire["sources"] if s.get("conversation"))
        news = next(s for s in wire["sources"] if s["channel"] == "news")
        if fault == "missing":
            value["answer_context_citations"] = []
        elif fault == "unknown":
            value["answer_context_citations"][0]["passage_id"] = "p999"
        elif fault == "duplicate":
            value["answer_context_citations"] *= 2
        elif fault == "parent_only":
            value["answer_citations"] = [
                dict(source_id=news["id"], passage_id=news["passages"][0]["id"])
            ]
        elif fault == "title_only":
            value["answer_citations"][0]["passage_id"] = "p0"
        elif fault == "too_many":
            value["answer_context_citations"] = [
                dict(source_id=child["id"], passage_id="p" + str(n))
                for n in range(1, 4)
            ]
        elif fault == "news_parent":
            value["answer_citations"] = [
                dict(source_id=news["id"], passage_id=news["passages"][0]["id"])
            ]
            value["answer_context_citations"][0]["source_id"] = news["id"]
        elif fault == "point_missing":
            value["evidence"][0]["context_citations"] = []
        else:
            value.update(coverage="insufficient", answer=None, answer_citations=[])

    with pytest.raises(ValueError):
        A.render(
            dict(response_body=contextual_response(A.request_for(packet), bad)), packet
        )
    with transaction(owner) as c:
        assert not one(
            c, "SELECT 1 FROM research_answers WHERE instrument_id=%s", (iid,)
        )


def test_parent_withdrawal_during_answer_hides_history_and_export(owner):
    iid, _, _, _ = with_context(owner)

    def provider(body):
        with transaction(source=True) as c:
            c.execute("INSERT INTO hn_withdrawals VALUES('hn:99',now())")
        return contextual_response(body)

    saved = A.generate(owner, iid, A.Ask(question=QUESTION), transport=provider)
    assert saved["withheld"] and saved["result"] is None and saved["sources"] == []
    assert A.history(owner, iid)["items"][0]["withheld"]
    html = A.download(owner, saved["id"])[1]
    assert "Answer withheld" in html and "Microsoft software is excellent" not in html


def test_parent_export_retains_separate_quotes_then_withholds_on_removal(owner):
    iid, _, _, _ = with_context(owner)
    saved = A.generate(
        owner, iid, A.Ask(question=QUESTION), transport=contextual_response
    )
    html = A.download(owner, saved["id"])[1]
    assert "Parent context used for this finding" in html
    assert "I think Microsoft software is excellent." in html
    assert "https://news.ycombinator.com/item?id=99" in html
    budget = ledger.snapshot()
    with transaction(source=True) as c:
        c.execute("INSERT INTO hn_withdrawals VALUES('hn:99',now())")
    assert A.get(owner, saved["id"])["withheld"]
    assert "Microsoft software is excellent" not in A.download(owner, saved["id"])[1]
    assert ledger.snapshot() == budget
    assert not any(s.get("conversation") for s in request(owner, iid)["sources"])


def test_social_opt_out_stale_and_failed_parent_checks_do_not_supply_context(owner):
    iid, post, child, parent = with_context(owner)
    opted_out = request(owner, iid, include_social=False)
    assert (
        opted_out["coverage"]["selected_social"]
        == opted_out["coverage"]["parent_contexts"]
        == 0
    )
    assert not any(
        s.get("platform") or s.get("conversation") for s in opted_out["sources"]
    )
    old = request(owner, iid, datetime.now(timezone.utc) + timedelta(hours=25))
    assert old["coverage"]["parent_contexts"] == 0
    unlock(post["id"])
    cv.collect(
        post["id"],
        fetcher=fetcher(
            child | {"text": "Microsoft changed the original comment."}, parent, []
        ),
    )
    assert request(owner, iid)["coverage"]["parent_contexts"] == 0
