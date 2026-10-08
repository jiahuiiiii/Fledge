import json
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import psycopg
import pytest
from thesis import service
from thesis.config import INSTRUMENT
from thesis.db import transaction, one, rows
from thesis.models import SaveIdea
from thesis.providers import ledger
from thesis.research import proposals
from test_integration import payload, drain
from test_model_budget import response


def request(owner, saved=None):
    return proposals.GenerateRequest(
        instrument_id=INSTRUMENT,
        snapshot_id=service.state(owner)["snapshot_id"],
        base_version_id=saved["version_id"] if saved else None,
        question="Could repeat customer demand support this company?",
    )


def provider(changes=None):
    def send(body):
        packet = json.loads(body["input"][1]["content"])
        s = packet["sources"][0]
        common = dict(
            rationale="A proposed evidence criterion, not proof that demand is durable.",
            citations=[dict(source_id=s["id"], passage_id=s["passages"][0]["id"])],
        )
        items = (
            changes(packet)
            if changes
            else [
                dict(
                    kind="event",
                    operation="add",
                    target_condition_id=None,
                    definition=dict(
                        description="Contract renewals are reported",
                        evidence_requirement="A company report names completed renewal agreements, not plans.",
                        role="required",
                        window_start=None,
                        deadline=None,
                    ),
                    **common
                )
            ]
        )
        for item in items:
            item.setdefault("rationale", common["rationale"])
            item.setdefault("citations", common["citations"])
        return response() | dict(
            model=body["model"],
            id="resp_mock_" + str(uuid4()),
            output=[
                dict(
                    type="message",
                    content=[
                        dict(
                            type="output_text",
                            text=json.dumps(
                                dict(
                                    explanation="Review the proposed evidence requirements and choose a reporting window.",
                                    suggestions=items,
                                )
                            ),
                        )
                    ],
                )
            ],
        )

    return send


def generated(owner, **kw):
    saved = service.save_idea(owner, payload(status="draft", conditions=False))
    return proposals.generate(owner, request(owner, saved), transport=provider(**kw))[
        "proposals"
    ][0]


def complete(p, status="monitoring"):
    candidate = deepcopy(p["candidate"])
    candidate["status"] = status
    for event in candidate["events"]:
        event["window_start"] = event["window_start"] or "2025-01-01"
        event["deadline"] = event["deadline"] or "2026-12-31"
    if not candidate["reasoning"]:
        candidate["reasoning"] = (
            "Authored test belief to investigate, not an investment recommendation."
        )
    return SaveIdea(**candidate)


def test_pending_until_explicit_atomic_approval_and_cache(owner):
    saved = service.save_idea(owner, payload(status="draft", conditions=False))
    r = request(owner, saved)
    before = service.state(owner)["versions"]
    first = proposals.generate(owner, r, transport=provider())
    p = first["proposals"][0]
    assert p["status"] == "pending" and p["candidate"]["events"][0]["deadline"] is None
    assert service.state(owner)["versions"] == before
    budget = ledger.snapshot()
    assert (
        proposals.generate(owner, r, transport=lambda _: pytest.fail("cache")) == first
    )
    assert ledger.snapshot() == budget
    approved = proposals.decide(owner, p["id"], definition=complete(p))
    drain(owner)
    after = service.state(owner)
    assert after["thesis"]["revision"] == 2 and len(after["versions"][0]["events"]) == 1
    assert after["versions"][1] == before[0]
    assert approved["accepted_version_id"] == str(after["versions"][0]["id"])
    assert proposals.decide(owner, p["id"], definition=complete(p)) == approved
    assert service.state(owner)["thesis"]["revision"] == 2
    with pytest.raises(service.Conflict):
        proposals.decide(owner, p["id"])


def test_two_approvals_create_only_one_revision(owner):
    p = generated(owner)
    definition = complete(p)
    with ThreadPoolExecutor(2) as pool:
        results = list(
            pool.map(
                lambda _: proposals.decide(owner, p["id"], definition=definition),
                range(2),
            )
        )
    assert results[0]["accepted_version_id"] == results[1]["accepted_version_id"]
    assert service.state(owner)["thesis"]["revision"] == 2


@pytest.mark.parametrize("change", ["idea", "evidence"])
def test_stale_proposals_never_apply_silently(owner, change):
    p = generated(owner)
    if change == "idea":
        service.save_idea(owner, payload(revision=1, status="draft", conditions=False))
    else:
        service.advance(owner, 0)
    assert service.state(owner)["proposals"][0]["status"] == "stale"
    before = service.state(owner)["versions"]
    with pytest.raises(service.Conflict, match="stale"):
        proposals.decide(owner, p["id"], definition=complete(p))
    assert service.state(owner)["versions"] == before
    rejected = proposals.decide(owner, p["id"])
    assert (
        rejected["status"] == "rejected"
        and proposals.decide(owner, p["id"]) == rejected
    )


def test_wrong_owner_company_and_typed_target_rejected(owner):
    p = generated(owner)
    with transaction(str(uuid4())) as c:
        assert one(c, "SELECT count(*) n FROM idea_proposals")["n"] == 0
    with pytest.raises(service.Missing):
        proposals.decide(str(uuid4()), p["id"], definition=complete(p))
    wrong = complete(p).model_copy(update=dict(instrument_id=uuid4()))
    with pytest.raises(ValueError, match="company"):
        proposals.decide(owner, p["id"], definition=wrong)
    with transaction(owner) as c:
        with pytest.raises(psycopg.errors.RaiseException):
            c.execute(
                "INSERT INTO idea_proposals SELECT %s,owner_id,instrument_id,base_version_id,snapshot_id,call_id,request_key||'-wrong',ordinal,kind,'update',%s,proposed,rationale,citations,packet,created_at FROM idea_proposals WHERE id=%s",
                (uuid4(), uuid4(), p["id"]),
            )


def test_malformed_target_or_citation_does_not_publish(owner):
    saved = service.save_idea(owner, payload())

    def bad(packet):
        return [
            dict(
                kind="numeric",
                operation="update",
                target_condition_id=str(uuid4()),
                definition=dict(
                    metric="revenue_growth",
                    operator=">=",
                    threshold="15",
                    period_type="quarter",
                    max_report_age_days=None,
                    role="required",
                ),
            )
        ]

    with pytest.raises(ValueError, match="target"):
        proposals.generate(owner, request(owner, saved), transport=provider(bad))
    assert service.state(owner)["proposals"] == []


def test_multi_selection_creates_one_revision_and_rolls_back_on_failure(
    owner, monkeypatch
):
    def changes(packet):
        return [
            dict(
                kind="reasoning",
                operation="update",
                question="Can renewals support growth?",
                reasoning="I need explicit renewal evidence before concluding growth is durable.",
            ),
            dict(
                kind="numeric",
                operation="add",
                target_condition_id=None,
                definition=dict(
                    metric="revenue_growth",
                    operator=">=",
                    threshold=None,
                    period_type="quarter",
                    max_report_age_days=None,
                    role="required",
                ),
            ),
        ]

    saved = service.save_idea(owner, payload(status="draft", conditions=False))
    result = proposals.generate(
        owner, request(owner, saved), transport=provider(changes)
    )
    ps = result["proposals"]
    base = ps[0]["base"]
    for p in ps:
        base = proposals.apply_change(base, dict(p, proposed=p["proposed"]))
    base["conditions"][0]["threshold"] = "15"
    base["status"] = "monitoring"
    definition = SaveIdea(**base)
    original = service._save_revision

    def fail(*a, **kw):
        original(*a, **kw)
        raise RuntimeError("simulated failure before decisions")

    monkeypatch.setattr(service, "_save_revision", fail)
    with pytest.raises(RuntimeError):
        proposals.decide_many(owner, [p["id"] for p in ps], definition=definition)
    assert service.state(owner)["thesis"]["revision"] == 1
    assert all(p["status"] == "pending" for p in service.state(owner)["proposals"])
    monkeypatch.setattr(service, "_save_revision", original)
    approved = proposals.decide_many(
        owner, [p["id"] for p in ps], definition=definition
    )
    assert len({p["accepted_version_id"] for p in approved}) == 1
    assert service.state(owner)["thesis"]["revision"] == 2


def test_new_idea_suggestion_does_not_create_phantom_revision(owner):
    result = proposals.generate(
        owner,
        request(owner),
        transport=provider(
            lambda p: [
                dict(
                    kind="reasoning",
                    operation="update",
                    question="What would make renewals durable?",
                    reasoning="I want to investigate whether customer renewals can support future growth.",
                )
            ]
        ),
    )
    assert service.state(owner)["versions"] == []
    p = result["proposals"][0]
    assert p["base_version_id"] is None
    accepted = proposals.decide(owner, p["id"], definition=complete(p, status="draft"))
    state = service.state(owner)
    assert (
        state["thesis"]["revision"] == 1 and state["versions"][0]["status"] == "draft"
    )
    assert state["jobs"] == [] and accepted["status"] == "approved"


def test_edit_during_model_call_produces_stale_suggestion(owner):
    saved = service.save_idea(owner, payload(status="draft", conditions=False))

    def transport(body):
        service.save_idea(owner, payload(revision=1, status="draft", conditions=False))
        return provider()(body)

    result = proposals.generate(owner, request(owner, saved), transport=transport)
    assert result["proposals"][0]["status"] == "stale"
    assert service.state(owner)["thesis"]["revision"] == 2


def test_revoked_source_withholds_proposal_and_blocks_approval(owner, monkeypatch):
    p = generated(owner)
    original = service.permitted_documents
    cited = p["citations"][0]["source_id"]
    monkeypatch.setattr(
        service,
        "permitted_documents",
        lambda *a, **kw: [d for d in original(*a, **kw) if str(d["id"]) != cited],
    )
    scoped = service.state(owner)["proposals"][0]
    assert (
        scoped["candidate"] is None
        and scoped["proposed"] is None
        and scoped["citations"] == []
    )
    with pytest.raises(ValueError, match="unavailable"):
        proposals.decide(owner, p["id"], definition=complete(p))


def test_different_approval_payload_is_not_false_idempotency(owner):
    p = generated(owner)
    first = complete(p)
    proposals.decide(owner, p["id"], definition=first)
    altered = first.model_copy(update=dict(reasoning="Different approval payload"))
    with pytest.raises(service.Conflict):
        proposals.decide(owner, p["id"], definition=altered)


@pytest.mark.parametrize("operation", ["update", "remove"])
def test_numeric_target_identity_and_removal_preserve_old_revision(owner, operation):
    saved = service.save_idea(owner, payload(status="draft"))
    original = service.state(owner)["versions"][0]
    target = str(original["conditions"][0]["condition_id"])

    def changes(packet):
        definition = (
            dict(
                metric=original["conditions"][0]["metric"],
                operator=">=",
                threshold="17",
                period_type="quarter",
                max_report_age_days=None,
                    role="required",
            )
            if operation == "update"
            else None
        )
        return [
            dict(
                kind="numeric",
                operation=operation,
                target_condition_id=target,
                definition=definition,
            )
        ]

    p = proposals.generate(owner, request(owner, saved), transport=provider(changes))[
        "proposals"
    ][0]
    proposals.decide(owner, p["id"], definition=complete(p, status="draft"))
    versions = service.state(owner)["versions"]
    assert versions[1] == original
    if operation == "remove":
        assert target not in {str(c["condition_id"]) for c in versions[0]["conditions"]}
    else:
        changed = next(
            c for c in versions[0]["conditions"] if str(c["condition_id"]) == target
        )
        assert str(changed["threshold"]) == "17"


def test_all_schema_properties_are_required_for_strict_generation():
    # The provider rejects optional properties even when the application model accepts defaults.
    def check(schema):
        if isinstance(schema, dict):
            if schema.get("type") == "object":
                assert set(schema.get("required", [])) == set(
                    schema.get("properties", {})
                )
                assert schema["additionalProperties"] is False
            for value in schema.values():
                check(value)
        elif isinstance(schema, list):
            for value in schema:
                check(value)

    check(proposals.Suggestions.model_json_schema())


def test_approved_definition_export_retains_suggestion_provenance(owner):
    from thesis import review_export

    p = generated(owner)
    accepted = proposals.decide(owner, p["id"], definition=complete(p, status="draft"))
    before = ledger.snapshot()
    _, html = review_export.download(owner, accepted["accepted_version_id"])
    assert "Suggestions reviewed for this revision" in html
    assert "Inspect suggestion source" in html and "proposed evidence criterion" in html
    assert ledger.snapshot() == before


@pytest.mark.parametrize(
    "unfinished",
    [
        "A report confirms paid use and",
        "A report confirms paid use...",
        "A report confirms paid use,",
    ],
)
def test_unfinished_generated_requirement_is_not_published_or_retried(
    owner, unfinished
):
    saved = service.save_idea(owner, payload(status="draft", conditions=False))
    req = request(owner, saved)

    def changes(packet):
        return [
            dict(
                kind="event",
                operation="add",
                target_condition_id=None,
                definition=dict(
                    description="A customer is paying for the product.",
                    evidence_requirement=unfinished,
                    role="required",
                    window_start=None,
                    deadline=None,
                ),
            )
        ]

    with pytest.raises(ValueError, match="unfinished"):
        proposals.generate(owner, req, transport=provider(changes))
    assert not service.state(owner)["proposals"]
    assert len(service.state(owner)["versions"]) == 1
    budget = ledger.snapshot()
    with pytest.raises(ValueError, match="unfinished"):
        proposals.generate(
            owner, req, transport=lambda _: pytest.fail("automatic paid retry")
        )
    assert ledger.snapshot() == budget
