"""Private interpretation tests: mocked providers, real restricted database roles."""

import json
from copy import deepcopy
from uuid import uuid4
import pytest
import psycopg
from thesis import service
from thesis.db import transaction, one, rows
from thesis.research import idea_review
from thesis.providers import ledger
from thesis.providers.settings import MODEL
from test_integration import payload, drain


def setup(owner, *, draft=False):
    saved = service.save_idea(
        owner, payload(status="draft" if draft else "monitoring", conditions=not draft)
    )
    drain(owner)
    state = service.state(owner)
    e = state["versions"][0]["evaluations"][0] if not draft else None
    return saved, state["snapshot_id"], str(e["id"]) if e else None


def response(body, **changes):
    p = json.loads(body["input"][1]["content"])
    source = p["sources"][0]
    point = dict(
        relation="unclear",
        reasoning_segment_id=p["reasoning_segments"][0]["id"],
        text="This evidence does not establish future demand.",
        citations=[
            dict(source_id=source["id"], passage_id=source["passages"][0]["id"])
        ],
    )
    point.update(changes)
    return dict(
        id="resp_" + str(uuid4()),
        model=body["model"],
        service_tier="default",
        status="completed",
        usage=dict(input_tokens=100, output_tokens=80),
        output=[
            dict(
                type="message",
                content=[
                    dict(type="output_text", text=json.dumps(dict(points=[point])))
                ],
            )
        ],
    )


def test_private_review_cache_history_and_no_numerical_changes(owner):
    saved, snapshot, eid = setup(owner)
    before = service.state(owner)
    result = idea_review.generate(
        owner, saved["version_id"], snapshot, eid, transport=response
    )
    assert (
        result["evaluation_id"] == eid and result["version_id"] == saved["version_id"]
    )
    again = idea_review.generate(
        owner,
        saved["version_id"],
        snapshot,
        eid,
        transport=lambda _: pytest.fail("cache missed"),
    )
    assert result["id"] == again["id"]
    after = service.state(owner)
    assert before["versions"][0]["conditions"] == after["versions"][0]["conditions"]
    assert before["versions"][0]["evaluations"] == after["versions"][0]["evaluations"]
    assert len(after["versions"][0]["evidence_reviews"]) == 1
    new = service.save_idea(owner, payload(revision=1))
    assert service.state(owner)["versions"][0]["evidence_reviews"] == []
    # Old completion/reopening cannot become an interpretation of the new version.
    assert (
        idea_review.generate(
            owner, saved["version_id"], snapshot, eid, transport=lambda _: pytest.fail()
        )["id"]
        == result["id"]
    )
    assert new["version_id"] != result["version_id"]


def test_qualitative_draft_needs_no_numeric_threshold(owner):
    saved, snapshot, eid = setup(owner, draft=True)
    result = idea_review.generate(
        owner, saved["version_id"], snapshot, transport=response
    )
    assert result["evaluation_id"] is None
    assert not service.state(owner)["versions"][0]["conditions"]
    assert not service.state(owner)["versions"][0]["evaluations"]


@pytest.mark.parametrize(
    "change",
    [
        dict(reasoning_segment_id="r999999"),
        dict(citations=[dict(source_id=str(uuid4()), passage_id="p0")]),
        dict(
            citations=[
                dict(
                    source_id="REPLACE",
                    passage_id="p999999",
                )
            ]
        ),
    ],
)
def test_forged_quote_ids_rejected_and_settled_response_never_repaid(owner, change):
    saved, snapshot, eid = setup(owner)

    def provider(body):
        c = deepcopy(change)
        if c.get("citations", [{}])[0].get("source_id") == "REPLACE":
            c["citations"][0]["source_id"] = json.loads(body["input"][1]["content"])[
                "sources"
            ][0]["id"]
        return response(body, **c)

    with pytest.raises(ValueError):
        idea_review.generate(
            owner, saved["version_id"], snapshot, eid, transport=provider
        )
    calls = ledger.snapshot()["calls"]
    with pytest.raises(ValueError):
        idea_review.generate(
            owner,
            saved["version_id"],
            snapshot,
            eid,
            transport=lambda _: pytest.fail("paid retry"),
        )
    assert ledger.snapshot()["calls"] == calls and ledger.snapshot()["unresolved"] == 0
    assert not service.state(owner)["versions"][0]["evidence_reviews"]


def test_wrong_owner_snapshot_and_evaluation_rejected_before_dispatch(owner):
    saved, snapshot, eid = setup(owner)
    other = str(uuid4())
    with transaction(admin=True) as conn:
        conn.execute("INSERT INTO accounts VALUES(%s,%s)", (other, "Other test"))
    with pytest.raises(service.Missing):
        idea_review.generate(
            other, saved["version_id"], snapshot, eid, transport=lambda _: pytest.fail()
        )
    with pytest.raises(ValueError, match="snapshot"):
        idea_review.generate(
            owner,
            saved["version_id"],
            snapshot + 100000,
            eid,
            transport=lambda _: pytest.fail(),
        )
    with pytest.raises(ValueError, match="assessment"):
        idea_review.generate(
            owner,
            saved["version_id"],
            snapshot,
            str(uuid4()),
            transport=lambda _: pytest.fail(),
        )


def test_replay_never_borrows_later_sources_and_revision_identity_changes(owner):
    saved, snapshot, eid = setup(owner)
    with transaction(owner) as conn:
        old = idea_review.prepare(conn, owner, saved["version_id"], snapshot, eid)
    service.advance(owner, 0)
    drain(owner)
    with transaction(owner) as conn:
        same = idea_review.prepare(conn, owner, saved["version_id"], snapshot, eid)
    assert old == same
    data = service.state(owner)
    new_e = data["versions"][0]["evaluations"][0]
    with transaction(owner) as conn:
        changed = idea_review.prepare(
            conn,
            owner,
            saved["version_id"],
            new_e["manifest"]["snapshot_id"],
            str(new_e["id"]),
        )
    assert any(s["changed"] for s in changed["sources"])
    assert idea_review.identity(owner, old) != idea_review.identity(owner, changed)
    p = payload(revision=1)
    p.reasoning = "Continuity, rather than demand, is the reason I am researching."
    nextversion = service.save_idea(owner, p)
    drain(owner)
    with transaction(owner) as conn:
        revised = idea_review.prepare(
            conn, owner, nextversion["version_id"], service.state(owner)["snapshot_id"]
        )
    assert revised["reasoning"] != old["reasoning"]


def test_code_resolves_original_source_case_spacing_and_reasoning_ellipsis(owner):
    from test_market import commit, news
    from thesis.research.sec.service import add_company

    iid = add_company("MSFT")["instrument_id"]
    original = "“Microsoft  has NOT confirmed the reported contract.”"
    commit(iid, [news(headline=original, summary="")])
    p = payload(status="draft", conditions=False)
    p.instrument_id = iid
    p.reasoning = "“Recurring REVENUE…” still needs verification."
    saved = service.save_idea(owner, p)
    state = service.state(owner, iid)
    with transaction(owner) as conn:
        packet = idea_review.prepare(
            conn, owner, saved["version_id"], state["snapshot_id"]
        )
    request = idea_review.request_for(packet)
    sent = json.loads(request["input"][1]["content"])
    assert all("text" not in source for source in sent["sources"])
    assert all("text" in source for source in packet["sources"])
    # The model supplies only selected IDs. Neither quotation is model-authored.
    output = response(request)
    point = json.loads(output["output"][0]["content"][0]["text"])["points"][0]
    assert "reasoning_quote" not in point and "quote" not in point["citations"][0]
    result = idea_review.render(dict(response_body=output), packet)
    assert result["points"][0]["reasoning_quote"] == p.reasoning
    assert result["points"][0]["citations"][0]["quote"] == original
    assert (
        result["points"][0]["citations"][0]["source_id"] == packet["sources"][0]["id"]
    )


@pytest.mark.parametrize(
    "invented",
    [
        '"Microsoft confirmed the contract"',
        "microsoft confirmed the contract",
        "Microsoft ... confirmed the contract",
    ],
)
def test_model_authored_quote_override_is_rejected_even_with_valid_ids(owner, invented):
    saved, snapshot, eid = setup(owner)
    with transaction(owner) as conn:
        packet = idea_review.prepare(conn, owner, saved["version_id"], snapshot, eid)
    valid = response(idea_review.request_for(packet))
    for location in ("source", "reasoning"):
        altered = deepcopy(valid)
        result = json.loads(altered["output"][0]["content"][0]["text"])
        point = result["points"][0]
        if location == "source":
            point["citations"][0]["quote"] = invented
        else:
            point["reasoning_quote"] = invented
        altered["output"][0]["content"][0]["text"] = json.dumps(result)
        with pytest.raises(ValueError):
            idea_review.render(dict(response_body=altered), packet)


def test_passage_id_is_scoped_to_its_named_source(owner):
    from test_market import commit, news
    from thesis.research.sec.service import add_company

    iid = add_company("MSFT")["instrument_id"]
    body_text = "Microsoft has not independently verified the reported contract."
    commit(
        iid,
        [
            news(
                url="https://example.test/headline-only",
                headline="Microsoft contract report",
                summary="",
            ),
            news(
                url="https://example.test/with-body",
                headline="Microsoft uncertainty remains",
                summary=body_text,
            ),
        ],
    )
    p = payload(status="draft", conditions=False)
    p.instrument_id = iid
    saved = service.save_idea(owner, p)
    state = service.state(owner, iid)
    with transaction(owner) as conn:
        packet = idea_review.prepare(
            conn, owner, saved["version_id"], state["snapshot_id"]
        )
    headline_only = next(s for s in packet["sources"] if not s["text"])
    with_body = next(s for s in packet["sources"] if s["text"] == body_text)
    body_passage = next(p for p in with_body["passages"] if p["quote"] == body_text)
    assert body_passage["id"] not in {p["id"] for p in headline_only["passages"]}
    request = idea_review.request_for(packet)
    forged = response(
        request,
        citations=[dict(source_id=headline_only["id"], passage_id=body_passage["id"])],
    )
    with pytest.raises(ValueError):
        idea_review.render(dict(response_body=forged), packet)
    valid = response(
        request,
        citations=[dict(source_id=with_body["id"], passage_id=body_passage["id"])],
    )
    result = idea_review.render(dict(response_body=valid), packet)
    assert result["points"][0]["citations"][0]["quote"] == body_text


def test_whitespace_only_recovery_preserves_original_not_negation():
    from thesis.research.citations import exact_excerpt

    assert exact_excerpt("Apple stock", "Apple  stock") == "Apple  stock"
    with pytest.raises(ValueError):
        exact_excerpt(
            "Apple confirmed the contract", "Apple has not confirmed the contract"
        )
