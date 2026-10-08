"""Exclude marked source fragments without altering stored evidence or numbers."""

import json
from copy import deepcopy
from uuid import uuid4

import pytest

from thesis import service
from thesis.db import transaction
from thesis.providers import ledger
from thesis.research import idea_review, market_brief
from thesis.research.citations import model_source, passage_segments, source_passages
from thesis.research.sec.service import add_company
from test_integration import drain, payload
from test_idea_review import response as private_response, setup
from test_market import commit, news, packet as shared_packet, prepare


# Public snippet from the failed Google UI case, replayed without network access.
GOOGLE_COMPLETE = (
    "Alphabet Inc (NASDAQ:GOOG)'s Google has unveiled Gemini 4 Argon, its first "
    "flagship model release since February, saying the model leads benchmarks in "
    "long-horizon coding, finance, legal work and video understanding."
)
GOOGLE_FRAGMENT = (
    "Access is initially limited to select cyber defenders and Google's internal..."
)
GOOGLE_RAW = GOOGLE_COMPLETE + " " + GOOGLE_FRAGMENT


def shared_response(source_id, quote):
    point = dict(
        kind="reported",
        title="Model announcement",
        text="Google reports a model announcement; adoption evidence is not supplied.",
        citations=[dict(source_id=source_id, quote=quote)],
    )
    return dict(
        id=str(uuid4()),
        response_body=dict(
            status="completed",
            output=[
                dict(
                    type="message",
                    content=[
                        dict(type="output_text", text=json.dumps(dict(points=[point])))
                    ],
                )
            ],
        ),
    )


@pytest.mark.parametrize("marker", ["...", "…", "[…]", "[...]", "[ . . . ]", "...."])
def test_fragment_exclusion_preserves_original_ids_and_complete_sentences(marker):
    first = "Google announced a new model."
    fragment = "Access is limited to Google's internal" + marker
    last = "The vendor has not published adoption data."
    text = first + " " + fragment + "\n" + last
    passages, omitted = source_passages("Model announcement", text)
    assert [p["id"] for p in passages] == ["p0", "p1", "p3"]
    assert [p["quote"] for p in passages] == ["Model announcement", first, last]
    assert omitted == 1
    # Users can write unfinished reasoning; source eligibility must not edit it.
    assert passage_segments(fragment, prefix="r") == [dict(id="r0", quote=fragment)]


def test_conservative_ellipsis_filter_also_covers_titles_and_metadata():
    source = dict(
        id="source",
        title="Google's internal...",
        publisher="Google's internal...",
        text="About 47% of sales were routed through partners, Reuters reported, citing a confidential IPO filing....",
    )
    before = deepcopy(source)
    assert source_passages(source["title"], source["text"]) == ([], 2)
    for include_text in (False, True):
        sent = model_source(source, include_text=include_text)
        assert sent["title"] is None and sent["publisher"] is None
        assert sent["omitted_fragment_count"] == 2
        assert "internal" not in json.dumps(sent) and "47%" not in json.dumps(sent)
    assert source == before


def private_packet(owner, iid, *, monitoring=False):
    p = payload(status="monitoring" if monitoring else "draft", conditions=monitoring)
    p.instrument_id = iid
    p.reasoning = "A model launch alone may not demonstrate paid enterprise demand."
    for condition in p.conditions:
        condition.period_type = "annual"
    saved = service.save_idea(owner, p)
    drain(owner)
    state = service.state(owner, iid)
    evaluation = state["versions"][0]["evaluations"][0] if monitoring else None
    eid = str(evaluation["id"]) if evaluation else None
    with transaction(owner) as conn:
        packet = idea_review.prepare(
            conn, owner, saved["version_id"], state["snapshot_id"], eid
        )
    return packet, saved, eid


def test_real_google_fragment_is_absent_from_both_wires_and_ineligible_to_render(owner):
    iid = prepare(owner)
    # Replay exact public prose as an authored adapter item, not a live provider call.
    commit(
        iid,
        [
            news(
                url="https://example.test/google-model",
                headline="Google unveils a new model",
                summary=GOOGLE_RAW,
            )
        ],
    )
    private, saved, eid = private_packet(owner, iid, monitoring=True)
    shared = shared_packet(iid)
    before = service.state(owner, iid)
    preserved = deepcopy((private, shared))
    for module, packet in ((idea_review, private), (market_brief, shared)):
        source = next(s for s in packet["sources"] if s["text"] == GOOGLE_RAW)
        assert [p["id"] for p in source["passages"]] == ["p0", "p1"]
        assert source["omitted_fragment_count"] == packet["omitted_fragment_count"] == 1
        sent = json.loads(module.request_for(packet)["input"][1]["content"])
        encoded = json.dumps(sent)
        assert GOOGLE_COMPLETE in encoded
        assert "internal" not in encoded and GOOGLE_FRAGMENT not in encoded
        assert sent["omitted_fragment_count"] == 1
    assert (private, shared) == preserved
    assert private["omitted_source_count"] == 0
    source = next(s for s in private["sources"] if s["text"] == GOOGLE_RAW)
    request = idea_review.request_for(private)
    forged = private_response(
        request, citations=[dict(source_id=source["id"], passage_id="p2")]
    )
    with pytest.raises(ValueError, match="unsupported passage"):
        idea_review.render(dict(response_body=forged), private)
    # A stale or forged selection list cannot put the raw fragment back in scope.
    forged_packet = deepcopy(private)
    next(s for s in forged_packet["sources"] if s["id"] == source["id"])[
        "passages"
    ].append(dict(id="p2", quote=GOOGLE_FRAGMENT))
    with pytest.raises(ValueError, match="unsupported passage"):
        idea_review.render(dict(response_body=forged), forged_packet)
    for quote in (GOOGLE_FRAGMENT, "Google's internal"):
        with pytest.raises(ValueError, match="unsupported citation"):
            market_brief.render(shared_response(source["id"], quote), shared)
    result = market_brief.render(shared_response(source["id"], GOOGLE_COMPLETE), shared)
    assert result["points"][0]["citations"][0]["quote"] == GOOGLE_COMPLETE
    assert result["omitted_fragment_count"] == 1
    assert "1 source passage" in result["limitation"]
    result = idea_review.generate(
        owner,
        saved["version_id"],
        private["snapshot_id"],
        eid,
        transport=lambda body: private_response(
            body, citations=[dict(source_id=source["id"], passage_id="p1")]
        ),
    )
    assert result["points"][0]["citations"][0]["quote"] == GOOGLE_COMPLETE
    assert result["omitted_fragment_count"] == 1
    assert "1 source passage" in result["limitation"]
    after = service.state(owner, iid)
    assert before["documents"] == after["documents"]
    assert before["versions"][0]["conditions"] == after["versions"][0]["conditions"]
    assert before["versions"][0]["evaluations"] == after["versions"][0]["evaluations"]


def test_ellipsis_headline_is_not_an_alternate_wire_or_citation_path(owner):
    iid = add_company("MSFT")["instrument_id"]
    commit(iid, [news(headline=GOOGLE_FRAGMENT, summary=GOOGLE_COMPLETE)])
    private, _, _ = private_packet(owner, iid)
    shared = shared_packet(iid)
    for module, packet in ((idea_review, private), (market_brief, shared)):
        assert packet["sources"][0]["title"] == GOOGLE_FRAGMENT
        sent = json.loads(module.request_for(packet)["input"][1]["content"])
        assert sent["sources"][0]["title"] is None
        assert "internal" not in json.dumps(sent)
        assert [p["id"] for p in packet["sources"][0]["passages"]] == ["p1"]
    source_id = private["sources"][0]["id"]
    response = private_response(
        idea_review.request_for(private),
        citations=[dict(source_id=source_id, passage_id="p0")],
    )
    with pytest.raises(ValueError, match="unsupported passage"):
        idea_review.render(dict(response_body=response), private)
    with pytest.raises(ValueError, match="unsupported citation"):
        market_brief.render(shared_response(source_id, GOOGLE_FRAGMENT), shared)


def test_all_fragment_packets_withhold_before_spending_and_keep_raw_source(owner):
    iid = add_company("MSFT")["instrument_id"]
    commit(iid, [news(headline="Unfinished...", summary=GOOGLE_FRAGMENT)])
    p = payload(status="draft", conditions=False)
    p.instrument_id = iid
    saved = service.save_idea(owner, p)
    state = service.state(owner, iid)
    before = ledger.snapshot()
    with pytest.raises(ValueError, match="No eligible evidence"):
        idea_review.generate(
            owner,
            saved["version_id"],
            state["snapshot_id"],
            transport=lambda _: pytest.fail("paid call"),
        )
    with pytest.raises(ValueError, match="No complete news passages"):
        market_brief.generate(iid, transport=lambda _: pytest.fail("paid call"))
    assert ledger.snapshot() == before
    assert shared_packet(iid)["sources"][0]["text"] == GOOGLE_FRAGMENT
    assert market_brief.cached_brief(shared_packet(iid)) is None
    assert service.state(owner, iid)["market_brief"] is None


def test_prompt_versions_invalidate_pre_filter_cached_requests(owner, monkeypatch):
    iid = prepare(owner)
    shared = shared_packet(iid)
    assert market_brief.PROMPT == "thesis-market-brief-6"
    new_shared = market_brief.identity(shared)
    monkeypatch.setattr(market_brief, "PROMPT", "thesis-market-brief-4")
    assert market_brief.identity(shared) != new_shared
    saved, snapshot, eid = setup(owner)
    with transaction(owner) as conn:
        private = idea_review.prepare(conn, owner, saved["version_id"], snapshot, eid)
    assert idea_review.PROMPT == "thesis-private-evidence-3"
    new_private = idea_review.identity(owner, private)
    monkeypatch.setattr(idea_review, "PROMPT", "thesis-private-evidence-2")
    assert idea_review.identity(owner, private) != new_private
