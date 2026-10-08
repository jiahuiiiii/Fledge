"""Second-pass publication boundaries. Providers are wholly mocked here."""

import json
from copy import deepcopy
from uuid import uuid4
import pytest
from thesis.db import transaction
from thesis.providers import ledger
from thesis.research import discussion_themes as D, discussion_theme_check as C
from test_discussion_themes import setup, response, check_response, packet_for


def test_checker_receives_original_platform_provenance_without_borrowing_claims(owner):
    iid, aid = setup(owner)
    packet = packet_for(iid, aid)
    candidate = D.render({"response_body": response(D.request_for(packet))}, packet)
    before = deepcopy(packet)
    wire = json.loads(C.request_for(packet, candidate)["input"][1]["content"])
    actual = {s["id"]: s["scope"] for s in wire["source_context"]}
    assert actual == {s["id"]: D.scope(s) for s in packet["sources"]}
    assert set(actual.values()) == {"news", "reddit", "hackernews"}
    assert packet == before
    assert all(
        "author" not in s and "author_hash" not in s for s in wire["source_context"]
    )
    # Platform naming uses stored source provenance, never a generated theme's
    # scope or a claim about a platform inside its prose.
    changed = deepcopy(candidate)
    changed["themes"][0]["scope"] = "hackernews"
    changed_wire = json.loads(C.request_for(packet, changed)["input"][1]["content"])
    assert changed_wire["source_context"] == wire["source_context"]


def test_failed_theme_is_withheld_whole_without_rewriting_valid_themes(owner):
    iid, aid = setup(owner)
    before = ledger.snapshot()["calls"]

    def provider(body):
        if body["text"]["format"]["name"] == "discussion_themes":
            return response(body)
        return check_response(
            body,
            lambda r, p: r["themes"][1].update(
                verdict="withhold",
                reason="Mock compatible views incorrectly presented as disagreement.",
            ),
        )

    saved = D.generate(iid, aid, transport=provider)
    assert ledger.snapshot()["calls"] == before + 2
    assert [t["scope"] for t in saved["result"]["themes"]] == ["news", "hackernews"]
    check = saved["result"]["evidence_check"]
    assert check["withheld_themes"] == 1 and check["policy"] == C.POLICY
    assert saved["earlier_method"] is False
    assert (
        D.generate(iid, aid, transport=lambda _: pytest.fail("cached"))["id"]
        == saved["id"]
    )
    _, html = D.download(iid, saved["id"])
    assert "1 proposed theme was withheld" in html
    assert "The same author also questions the price." not in html


@pytest.mark.parametrize(
    "fault", ["missing", "duplicate", "foreign", "incomplete", "blank_reason"]
)
def test_malformed_check_never_publishes_or_automatically_retries(owner, fault):
    iid, aid = setup(owner)
    calls = []

    def provider(body):
        calls.append(body["text"]["format"]["name"])
        if calls[-1] == "discussion_themes":
            return response(body)

        def corrupt(r, p):
            if fault == "missing":
                r["themes"].pop()
            elif fault == "duplicate":
                r["themes"][1] = deepcopy(r["themes"][0])
            elif fault == "foreign":
                r["gaps"][0]["item_id"] = 999
            elif fault == "blank_reason":
                r["themes"][0]["reason"] = " "

        value = check_response(body, corrupt)
        if fault == "incomplete":
            value["status"] = "incomplete"
        return value

    with pytest.raises(ValueError):
        D.generate(iid, aid, transport=provider)
    assert calls == ["discussion_themes", "discussion_theme_evidence_check"]
    assert D.history(iid, aid)["current"] is None
    with pytest.raises(ValueError):
        D.generate(
            iid,
            aid,
            transport=lambda _: pytest.fail("failed checked response must stay cached"),
        )


def test_existing_candidate_is_reused_and_all_withheld_remains_explicit(owner):
    iid, aid = setup(owner)
    p = packet_for(iid, aid)
    ledger.execute(D.identity(p), D.PROMPT, D.request_for(p), transport=response)
    before = ledger.snapshot()["calls"]

    def provider(body):
        assert body["text"]["format"]["name"] == "discussion_theme_evidence_check"

        def reject(r, p):
            for kind in ("themes", "gaps"):
                for d in r[kind]:
                    d.update(verdict="withhold", reason="Authored unsupported example.")

        return check_response(body, reject)

    saved = D.generate(iid, aid, transport=provider)
    assert ledger.snapshot()["calls"] == before + 1
    assert saved["result"]["themes"] == saved["result"]["gaps"] == []
    assert saved["result"]["evidence_check"]["withheld_themes"] == 3


def test_withdrawal_during_check_withholds_saved_result_and_export(owner):
    iid, aid = setup(owner)

    def provider(body):
        if body["text"]["format"]["name"] == "discussion_theme_evidence_check":
            with transaction(admin=True) as c:
                c.execute("UPDATE social_feeds SET enabled=false")
        return response(body)

    saved = D.generate(iid, aid, transport=provider)
    assert saved["withheld"] and saved["result"] is None and saved["sources"] == []
    assert "withheld" in D.download(iid, saved["id"])[1]


def test_check_identity_covers_quotes_prose_and_policy(owner, monkeypatch):
    iid, aid = setup(owner)
    p = packet_for(iid, aid)
    result = D.render({"response_body": response(D.request_for(p))}, p)
    old = C.identity(p, result)
    changed = deepcopy(result)
    changed["themes"][0]["reading"]["claims"][0][
        "text"
    ] = "Changed unsupported finding."
    assert C.identity(p, changed) != old
    changed = deepcopy(result)
    changed["themes"][0]["reading"]["claims"][0]["citations"][0][
        "quote"
    ] = "Changed quote."
    assert C.identity(p, changed) != old
    synthesis_id = D.identity(p)
    reading_id = D.reading_identity(p)
    monkeypatch.setattr(C, "POLICY", "authored-new-check")
    assert C.identity(p, result) != old
    assert D.reading_identity(p) != reading_id and D.identity(p) == synthesis_id


def test_successful_check_only_filters_original_payload(owner):
    iid, aid = setup(owner)
    p = packet_for(iid, aid)
    candidate = D.render({"response_body": response(D.request_for(p))}, p)
    original = deepcopy(candidate)
    call = dict(id=uuid4(), response_body=check_response(C.request_for(p, candidate)))
    checked = C.apply(call, candidate)
    assert (
        checked["themes"] == candidate["themes"]
        and checked["gaps"] == candidate["gaps"]
    )
    assert candidate == original and "evidence_check" not in candidate
