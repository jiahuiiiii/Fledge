"""Explicit question-only checks and watch-purpose boundaries. Mocked models."""

import json
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import pytest
from pydantic import ValidationError
from thesis import service, review_digest
from thesis.app import IdeaAlertRequest, WatchSettings
from thesis.db import transaction, one
from thesis.providers import ledger
from thesis.monitoring import news_watch as W, watch_history
from thesis.research import idea_alerts as A
from test_idea_alerts import setup, newer, provider as broad_provider
from test_model_budget import response


def question_provider(relation="answers", mutate=None, side_effect=None):
    def call(body):
        wire = json.loads(body["input"][1]["content"])
        assert "reasoning" not in wire and "reasoning_segments" not in wire
        assert wire["purpose"] == "question"
        items = [
            dict(
                id=s["label"],
                relation=relation,
                reasoning_segment_id=None,
                question_segment_id="q0" if relation == "answers" else None,
                passages=[
                    next(
                        p["id"]
                        for p in s["passages"]
                        if not s.get("conversation") or p["id"] != "p0"
                    )
                ],
                context_passages=(
                    [s["conversation"]["passages"][0]["id"]]
                    if s.get("conversation")
                    else []
                ),
                explanation="The supplied source reports part of the requested fact; this does not establish an investment conclusion.",
            )
            for s in wire["sources"]
        ]
        if mutate:
            items = mutate(items)
        if side_effect:
            side_effect()
        return response() | dict(
            model=body["model"],
            id="resp_" + str(uuid4()),
            output=[
                dict(
                    type="message",
                    content=[
                        dict(type="output_text", text=json.dumps(dict(items=items)))
                    ],
                )
            ],
        )

    return call


def raw_check(owner, cid):
    with transaction(owner) as c:
        return one(c, "SELECT * FROM idea_alert_checks WHERE id=%s", (cid,))


def packet(owner, iid, reading, purpose="question"):
    with transaction(owner) as c:
        return A.prepare(c, owner, iid, reading["id"], purpose=purpose)[0]


def test_question_contract_has_no_belief_or_risk_and_distinct_identity(owner):
    iid, _, reading = setup(owner, True)
    p = packet(owner, iid, reading)
    request = A.request_for(p)
    props = request["text"]["format"]["schema"]["properties"]["items"]["items"][
        "anyOf"
    ][0]["properties"]
    assert set(props["relation"]["enum"]) == A.QUESTION_RELATIONS
    assert props["reasoning_segment_id"] == {"type": "null"}
    wire = json.loads(request["input"][1]["content"])
    assert "reasoning" not in wire and "reasoning_segments" not in wire
    assert wire["question"] == p["question"]
    broad = p | {"purpose": "reasoning"}
    legacy = {k: v for k, v in broad.items() if k != "purpose"}
    assert A.request_for(broad) == A.request_for(legacy) and A.identity(
        owner, broad
    ) == A.identity(owner, legacy)
    assert A.identity(owner, p) != A.identity(owner, broad)


@pytest.mark.parametrize(
    "fault",
    [
        "risk",
        "supports",
        "challenges",
        "reasoning_anchor",
        "missing_question",
        "foreign_question",
        "dual_anchor",
    ],
)
def test_off_purpose_output_is_rejected_before_publication(owner, fault):
    iid, _, reading = setup(owner)

    def mutate(items):
        if fault in ("risk", "supports", "challenges"):
            items[0]["relation"] = fault
        elif fault == "reasoning_anchor":
            items[0].update(reasoning_segment_id="r0", question_segment_id=None)
        elif fault == "missing_question":
            items[0]["question_segment_id"] = None
        elif fault == "foreign_question":
            items[0]["question_segment_id"] = "q100"
        else:
            items[0]["reasoning_segment_id"] = "r0"
        return items

    with pytest.raises(ValueError):
        A.generate(
            owner,
            iid,
            reading["id"],
            purpose="question",
            transport=question_provider(mutate=mutate),
        )
    with transaction(owner) as c:
        assert A.list_for(c, owner) == []


def test_explicit_question_answer_roundtrip_cache_and_exports(owner):
    iid, _, reading = setup(owner)
    checked = A.generate(
        owner, iid, reading["id"], purpose="question", transport=question_provider()
    )
    before = ledger.snapshot()
    assert (
        A.generate(
            owner,
            iid,
            reading["id"],
            purpose="question",
            transport=lambda _: pytest.fail("repeat"),
        )["id"]
        == checked["id"]
    )
    assert ledger.snapshot() == before
    raw = raw_check(owner, checked["id"])
    with transaction(owner) as c:
        shown = A.present(c, owner, raw)
        assert (
            shown["purpose"] == "question"
            and shown["purpose_label"] == "Answers to saved question"
        )
        assert (
            shown["published"]
            and shown["prompt_version"] == A.QUESTION_PROMPT
            and not shown["earlier_method"]
        )
    for html in [A.download(owner, checked["id"])[1], review_digest.download(owner)[1]]:
        assert "Check focus: Answers to saved question" in html
    with transaction(str(uuid4())) as c:
        assert not A.list_for(c, str(uuid4()))


@pytest.mark.parametrize("relation", ["context", "unclear", "unrelated"])
def test_question_background_stays_quiet(owner, relation):
    iid, _, reading = setup(owner)
    checked = A.generate(
        owner,
        iid,
        reading["id"],
        purpose="question",
        transport=question_provider(relation),
    )
    with transaction(owner) as c:
        assert not A.present(c, owner, raw_check(owner, checked["id"]))["published"]


@pytest.mark.parametrize("purpose", ["question", "reasoning"])
def test_watch_purpose_persists_and_automatic_uses_saved_choice(owner, purpose):
    iid, _, reading = setup(owner)
    W.configure(owner, iid, True, match_idea=True, idea_purpose=purpose)
    assert W.configure(owner, iid, True, interval=240)["idea_purpose"] == purpose
    fresh = newer(iid)
    chosen = question_provider() if purpose == "question" else broad_provider()
    # Caller cannot silently override a scheduled watch's chosen purpose.
    checked = A.generate(
        owner,
        iid,
        fresh["id"],
        automatic=True,
        purpose=("reasoning" if purpose == "question" else "question"),
        transport=chosen,
    )
    assert raw_check(owner, checked["id"])["packet"]["purpose"] == purpose
    assert service.state(owner, iid)["news_watch"]["idea_purpose"] == purpose


def test_watch_switch_is_quiet_and_old_inflight_result_cannot_publish(owner):
    iid, _, _ = setup(owner)
    W.configure(owner, iid, True, match_idea=True, idea_purpose="question")
    fresh = newer(iid)
    checked = A.generate(
        owner,
        iid,
        fresh["id"],
        automatic=True,
        transport=question_provider(
            side_effect=lambda: W.configure(owner, iid, True, idea_purpose="reasoning")
        ),
    )
    assert checked["status"] == "historical_only"
    with transaction(owner) as c:
        assert not A.present(c, owner, raw_check(owner, checked["id"]))["published"]
    before = ledger.snapshot()
    assert (
        A.generate(
            owner,
            iid,
            fresh["id"],
            automatic=True,
            transport=lambda _: pytest.fail("Focus switch replayed baseline"),
        )["status"]
        == "no_new_sources"
    )
    assert ledger.snapshot() == before


def test_manual_other_purpose_does_not_consume_current_watch_work(owner):
    iid, _, _ = setup(owner)
    W.configure(owner, iid, True, match_idea=True, idea_purpose="reasoning")
    fresh = newer(iid)
    manual = A.generate(
        owner, iid, fresh["id"], purpose="question", transport=question_provider()
    )
    auto = A.generate(
        owner, iid, fresh["id"], automatic=True, transport=broad_provider()
    )
    assert (
        manual["status"] == auto["status"] == "checked" and manual["id"] != auto["id"]
    )
    assert raw_check(owner, manual["id"])["packet"]["purpose"] == "question"
    assert raw_check(owner, auto["id"])["packet"]["purpose"] == "reasoning"


def test_scheduled_history_pins_selected_purpose(owner):
    iid, _, _ = setup(owner)
    W.configure(
        owner,
        iid,
        True,
        match_idea=True,
        idea_purpose="question",
        now=datetime.now(timezone.utc) - timedelta(minutes=61),
    )
    fresh = newer(iid)
    assert W.run_once(
        owner,
        market_refresh=lambda _: None,
        social_refresh=lambda: None,
        analyzer=lambda _: fresh,
        idea_analyzer=lambda *a, **kw: A.generate(
            *a, **kw, transport=question_provider()
        ),
    )
    recorded = watch_history.history(owner, iid)["items"][0]
    assert recorded["idea_purpose"] == "question" and recorded["status"] == "completed"
    W.configure(owner, iid, False, idea_purpose="reasoning")
    assert watch_history.history(owner, iid)["items"][0]["idea_purpose"] == "question"


@pytest.mark.parametrize("bad", ["other", "", 1, False])
def test_unknown_purpose_rejected_without_changes(owner, bad):
    iid, _, reading = setup(owner)
    before = ledger.snapshot()
    with pytest.raises((ValueError, TypeError)):
        A.generate(
            owner,
            iid,
            reading["id"],
            purpose=bad,
            transport=lambda _: pytest.fail("invalid purpose dispatch"),
        )
    with pytest.raises((ValueError, TypeError)):
        W.configure(owner, iid, True, idea_purpose=bad)
    with pytest.raises(ValidationError):
        WatchSettings(enabled=True, idea_purpose=bad)
    with pytest.raises(ValidationError):
        IdeaAlertRequest(
            analysis_id=reading["id"], version_id=str(uuid4()), purpose=bad
        )
    assert ledger.snapshot() == before
    with transaction(owner) as c:
        assert not one(c, "SELECT * FROM news_watches WHERE owner_id=%s", (owner,))


def test_question_only_draft_does_not_require_an_invented_belief(owner):
    from thesis.models import SaveIdea

    iid, _, reading = setup(owner)
    service.save_idea(
        owner,
        SaveIdea(
            instrument_id=iid,
            expected_revision=1,
            question="What launch timing has been reported?",
            reasoning="",
            status="draft",
            conditions=[],
        ),
    )
    result = A.generate(
        owner, iid, reading["id"], purpose="question", transport=question_provider()
    )
    assert result["status"] == "checked"
    assert W.configure(owner, iid, True, match_idea=True, idea_purpose="question")[
        "enabled"
    ]
    with pytest.raises(ValueError):
        W.configure(owner, iid, True, idea_purpose="reasoning")
    with transaction(owner) as c:
        assert (
            one(c, "SELECT idea_purpose FROM news_watches WHERE owner_id=%s", (owner,))[
                "idea_purpose"
            ]
            == "question"
        )
    with pytest.raises(ValueError):
        A.generate(
            owner,
            iid,
            reading["id"],
            purpose="reasoning",
            transport=lambda _: pytest.fail("Missing belief dispatched"),
        )


def test_api_transmits_explicit_purpose_and_rejects_unknown_mode(owner, monkeypatch):
    from fastapi.testclient import TestClient
    import thesis.app as server

    iid, saved, reading = setup(owner)
    monkeypatch.setattr(server, "OWNER", owner)
    original = A.generate
    monkeypatch.setattr(
        A,
        "generate",
        lambda *a, **kw: original(*a, **kw, transport=question_provider()),
    )
    with TestClient(server.app) as client:
        client.get("/api/v1/session")
        route = f"/api/v1/companies/{iid}/idea-alert-check"
        body = dict(
            analysis_id=reading["id"],
            version_id=saved["version_id"],
            purpose="question",
        )
        response = client.post(
            route, json=body, headers={"X-Thesis-Request": "local-ui"}
        )
        assert response.status_code == 200, response.text
        assert (
            raw_check(owner, response.json()["result"]["id"])["packet"]["purpose"]
            == "question"
        )
        assert (
            client.post(
                route,
                json=body | {"purpose": "implicit-risk"},
                headers={"X-Thesis-Request": "local-ui"},
            ).status_code
            == 422
        )


def test_question_schema_binds_each_item_to_its_own_source_and_parent(owner):
    from test_idea_context import case

    iid, _, _, _, _, reading = case(owner)
    p = packet(owner, iid, reading)
    req = A.request_for(p)
    schema = req["text"]["format"]["schema"]
    branches = schema["properties"]["items"]["items"]["anyOf"]
    wire = json.loads(req["input"][1]["content"])
    assert len(branches) == len(p["sources"])
    for branch, source in zip(branches, wire["sources"]):
        props = branch["properties"]
        assert props["id"]["enum"] == [source["label"]]
        assert set(props["passages"]["items"]["enum"]) == {
            p["id"]
            for p in source["passages"]
            if not source.get("conversation") or p["id"] != "p0"
        }
        assert list(props).index("passages") < list(props).index("explanation")
        if source.get("conversation"):
            assert props["context_passages"]["minItems"] == 1
            assert props["context_passages"]["items"]["enum"] == [
                p["id"] for p in source["conversation"]["passages"]
            ]
            assert source["context_scope"] == "saved_parent_supplied"
        else:
            assert props["context_passages"]["maxItems"] == 0
            assert source["context_scope"] == "no_parent_supplied"
    rendered = A.render({"response_body": question_provider()(req)}, p)
    assert rendered["noteworthy_count"] == len(p["sources"])
    assert any(i.get("conversation") for i in rendered["items"])
