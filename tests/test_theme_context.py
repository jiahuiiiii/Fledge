"""Exact saved-parent evidence in both theme stages; all providers mocked."""

from copy import deepcopy
import json
import pytest
from thesis.db import transaction, one
from thesis.providers import ledger
from thesis.research import sentiment as S, sentiment_context, conversation as cv
from thesis.research import discussion_themes as D, discussion_theme_check as C
from test_conversation import setup, fetcher, unlock
from test_sentiment import provider as classify
from test_discussion_themes import response, check_response, packet_for


def context_case(owner):
    iid, post, child, parent = setup(owner)
    parent["text"] += " An incomplete parent statement..."
    cv.collect(post["id"], fetcher=fetcher(child, parent, []))
    reading = S.generate(iid, transport=classify())
    return iid, post, child, parent, reading


def withdraw():
    with transaction(source=True) as c:
        c.execute("INSERT INTO hn_withdrawals VALUES('hn:99',now())")


def test_both_theme_stages_use_the_same_parent_with_separate_citations(owner):
    iid, _, child, parent, reading = context_case(owner)
    packet = packet_for(iid, reading["id"])
    original = next(s for s in packet["sources"] if s.get("conversation"))
    calls = []

    def provider(body):
        calls.append(deepcopy(body))
        return response(body)

    result = D.generate(iid, reading["id"], transport=provider)
    assert len(calls) == 2
    synthesis = json.loads(calls[0]["input"][1]["content"])
    checking = json.loads(calls[1]["input"][1]["content"])
    s = next(s for s in synthesis["sources"] if s.get("conversation"))
    c = next(s for s in checking["source_context"] if s.get("conversation"))
    assert (
        s["conversation"]
        == c["conversation"]
        == sentiment_context.wire(original["conversation"])
    )
    assert (
        len(synthesis["sources"])
        == len(checking["source_context"])
        == len(packet["sources"])
    )
    assert "An incomplete parent statement" not in json.dumps(synthesis)
    assert "An incomplete parent statement" not in json.dumps(checking)
    assert result["coverage"]["parent_contexts"] == 1
    theme = next(t for t in result["result"]["themes"] if t["scope"] == "hackernews")
    claim = theme["reading"]["claims"][0]
    assert theme["source_count"] == 1
    assert all(q["quote"] in child["text"] for q in claim["citations"])
    assert all(q["quote"] in parent["text"] for q in claim["conversation"]["citations"])
    assert claim["conversation"]["result_id"] == original["conversation"]["result_id"]
    checked_claim = next(t for t in checking["themes"] if t["scope"] == "hackernews")[
        "reading"
    ]["claims"][0]
    assert set(checked_claim["conversation"]) == {
        "parent_type",
        "published_at",
        "citations",
    }
    assert (
        checked_claim["conversation"]["citations"] == claim["conversation"]["citations"]
    )
    assert (
        "context_passages"
        in calls[0]["text"]["format"]["schema"]["$defs"]["Claim"]["required"]
    )
    for body in calls:
        assert body["max_output_tokens"] == 6000
        assert body["store"] is False
    _, html = D.download(iid, result["id"])
    assert "Parent context used for this finding" in html
    assert "not another source or independent confirmation" in html
    assert "https://news.ycombinator.com/item?id=99" in html
    assert "I think Microsoft software is excellent." in html
    assert "An incomplete parent statement" not in html


def test_later_parent_change_cannot_rewrite_theme_input_or_charge_again(owner):
    iid, post, child, parent, reading = context_case(owner)
    packet = packet_for(iid, reading["id"])
    result = D.generate(iid, reading["id"], transport=response)
    before = ledger.snapshot()
    unlock(post["id"])
    cv.collect(
        post["id"],
        fetcher=fetcher(
            child, parent | {"text": "A later and unrelated parent view."}, []
        ),
    )
    assert packet_for(iid, reading["id"]) == packet
    assert (
        D.generate(
            iid,
            reading["id"],
            transport=lambda _: pytest.fail("Old saved context rebilled"),
        )
        == result
    )
    assert ledger.snapshot() == before


def test_old_comment_only_theme_and_sample_stay_unchanged_after_parent_load(
    owner, monkeypatch
):
    iid, post, child, parent = setup(owner)
    reading = S.generate(iid, transport=classify())
    with monkeypatch.context() as m:
        m.setattr(D, "PROMPT", "thesis-discussion-themes-6")
        m.setattr(C, "POLICY", "discussion-theme-evidence-check-1")
        saved = D.generate(iid, reading["id"], transport=response)
    cv.collect(post["id"], fetcher=fetcher(child, parent, []))
    packet = packet_for(iid, reading["id"])
    assert packet["coverage"]["parent_contexts"] == 0
    assert not any(s.get("conversation") for s in packet["sources"])
    old = D.get(iid, saved["id"])
    assert old["result"] == saved["result"] and old["earlier_method"]
    assert "Parent context used" not in D.download(iid, saved["id"])[1]


@pytest.mark.parametrize(
    "fault",
    ["missing", "unknown", "duplicate", "foreign_item", "title_only", "too_many"],
)
def test_bad_parent_references_never_reach_checker(owner, fault):
    iid, _, _, _, reading = context_case(owner)
    calls = []

    def bad(result, wire):
        claim = next(t for t in result["themes"] if t["scope"] == "hackernews")[
            "reading"
        ]["claims"][0]
        if fault == "missing":
            claim["context_passages"] = []
        elif fault == "unknown":
            claim["context_passages"] = ["p999"]
        elif fault == "duplicate":
            claim["context_passages"] *= 2
        elif fault == "title_only":
            claim["passages"] = ["p0"]
        elif fault == "too_many":
            claim["context_passages"] = ["p1", "p2", "p3"]
        else:
            next(t for t in result["themes"] if t["scope"] == "news")["reading"][
                "claims"
            ][0]["context_passages"] = ["p1"]

    def provider(body):
        calls.append(body["text"]["format"]["name"])
        return response(body, bad)

    with pytest.raises(ValueError):
        D.generate(iid, reading["id"], transport=provider)
    assert calls == ["discussion_themes"]
    assert D.history(iid, reading["id"])["current"] is None


@pytest.mark.parametrize("stage", ["before", "synthesis", "checker", "after"])
def test_parent_withdrawal_controls_both_stages_history_and_export(owner, stage):
    iid, _, _, _, reading = context_case(owner)
    calls = []
    if stage == "before":
        withdraw()

    def provider(body):
        calls.append(body["text"]["format"]["name"])
        if stage == "synthesis" or (stage == "checker" and len(calls) == 2):
            withdraw()
        return response(body)

    if stage in {"before", "synthesis"}:
        with pytest.raises(ValueError, match="Source access changed"):
            D.generate(iid, reading["id"], transport=provider)
        assert len(calls) == (0 if stage == "before" else 1)
        assert D.history(iid, reading["id"])["current"] is None
    else:
        saved = D.generate(iid, reading["id"], transport=provider)
        if stage == "after":
            withdraw()
        hidden = D.get(iid, saved["id"])
        assert (
            hidden["withheld"] and hidden["result"] is None and hidden["sources"] == []
        )
        assert D.history(iid, reading["id"])["current"]["withheld"]
        html = D.download(iid, saved["id"])[1]
        assert "are withheld" in html and "I think Microsoft software" not in html
        assert len(calls) == 2


def test_checker_cannot_mutate_context_when_filtering_failed_theme(owner):
    iid, _, _, _, reading = context_case(owner)
    packet = packet_for(iid, reading["id"])
    candidate = D.render({"response_body": response(D.request_for(packet))}, packet)
    original = deepcopy(candidate)
    request = C.request_for(packet, candidate)

    def reject(result, wire):
        rejected = next(
            t["item_id"] for t in wire["themes"] if t["scope"] == "hackernews"
        )
        result["themes"][rejected].update(
            verdict="withhold", reason="Authored parent/child attribution failure."
        )

    checked = C.apply(
        dict(id="authored-check", response_body=check_response(request, reject)),
        candidate,
    )
    assert candidate == original
    assert checked["themes"] == [
        t for t in original["themes"] if t["scope"] != "hackernews"
    ]
    assert checked["evidence_check"]["withheld_themes"] == 1


def test_checker_identity_covers_selected_parent_evidence_without_raw_body(owner):
    iid, _, _, _, reading = context_case(owner)
    packet = packet_for(iid, reading["id"])
    candidate = D.render({"response_body": response(D.request_for(packet))}, packet)
    original = C.identity(packet, candidate)
    changed = deepcopy(candidate)
    context = next(t for t in changed["themes"] if t["scope"] == "hackernews")[
        "reading"
    ]["claims"][0]["conversation"]
    context["body"] += " Do not send this stored raw text."
    context["checked_at"] = "2026-10-03T00:00:00Z"
    assert C.identity(packet, changed) == original
    context["citations"][0]["quote"] = "A different selected parent passage."
    assert C.identity(packet, changed) != original
