import json
from datetime import datetime, timezone
from uuid import uuid4
import pytest
from thesis.research.briefs import source_packet, render_selection, baseline, QUESTIONS
from thesis.fixtures import RELEASES, STAGES, dt
from thesis.providers.settings import MODEL


def document(body="Revenue grew 12%. The cause is unknown."):
    return dict(
        id=str(uuid4()),
        instrument_id="NSTR",
        entitlement="fictional",
        headline="Authored report",
        body=body,
        source_name="Company",
        published_at=dt(STAGES[2]["as_of"]),
        available_at=dt(STAGES[2]["as_of"]),
        supersedes_id=None,
        content_hash="authored",
    )


def call(ids):
    return dict(
        id=str(uuid4()),
        response_body=dict(
            status="completed",
            output=[
                dict(
                    type="message",
                    content=[
                        dict(type="output_text", text=json.dumps(dict(passage_ids=ids)))
                    ],
                )
            ],
        ),
    )


def test_selection_retains_whole_negated_sentence_and_provenance():
    doc = document("Management has not confirmed a renewal loss. The cause is unknown.")
    packet = source_packet([doc], "NSTR", STAGES[2]["as_of"])
    result = render_selection(call([packet["passages"][0]["id"]]), packet)
    assert (
        result["passages"][0]["quote"]
        == "Management has not confirmed a renewal loss. The cause is unknown."
    )
    assert result["passages"][0]["document_id"] == doc["id"]


@pytest.mark.parametrize(
    "change",
    [
        {"entitlement": "finnhub-personal"},
        {"instrument_id": "OTHER"},
        {"available_at": dt(STAGES[4]["as_of"])},
    ],
)
def test_model_packet_rejects_restricted_wrong_company_and_future_sources(change):
    with pytest.raises(ValueError):
        source_packet([document() | change], "NSTR", STAGES[2]["as_of"])


def test_selection_rejects_fabrication_duplicates_and_incomplete():
    packet = source_packet([document()], "NSTR", STAGES[2]["as_of"])
    passage = packet["passages"][0]["id"]
    for ids in (["made-up"], [passage, passage]):
        with pytest.raises(ValueError):
            render_selection(call(ids), packet)
    bad = call([passage])
    bad["response_body"]["status"] = "incomplete"
    with pytest.raises(ValueError):
        render_selection(bad, packet)


def test_restatement_replaces_current_source_without_losing_old_history():
    old = document()
    new = document("Revenue was corrected to 13%.") | dict(supersedes_id=old["id"])
    packet = source_packet([old, new], "NSTR", STAGES[2]["as_of"])
    assert packet["source_ids"] == [new["id"]]
    assert old["body"] == "Revenue grew 12%. The cause is unknown."


def test_baseline_is_fact_driven_without_stage_or_hardcoded_values():
    obs = dict(
        id="a",
        metric="revenue_growth",
        value="7.25",
        period="2026-Q1",
        unit="percent",
        basis="reported",
        document_version_id="d",
        available_at="2026-04-01",
    )
    result = baseline([obs], [], [], "2026-Q1")[QUESTIONS[0]]
    assert "7.25%" in result["text"] and "2026-Q1" in result["text"]
    assert "18%" not in result["text"] and result["evidence_ids"] == ["d"]


def test_omitted_denial_remains_visible_as_incomplete_selection():
    doc = document(
        "U.S. customers reported delays.\n\nManagement denied that contracts were cancelled."
    )
    packet = source_packet([doc], "NSTR", STAGES[2]["as_of"])
    assert packet["passages"][0]["quote"] == "U.S. customers reported delays."
    result = render_selection(call([packet["passages"][0]["id"]]), packet)
    assert result["omitted_passage_count"] == 1
    assert "omit" in result["limitation"]


def test_empty_source_workspace_remains_usable(owner, monkeypatch):
    from thesis import service
    from thesis.providers.ledger import snapshot

    before = snapshot()["calls"]
    monkeypatch.setattr(service, "permitted_documents", lambda *args: [])
    data = service.state(owner)
    assert data["selected_passages"] is None and data["documents"] == []
    assert all(f["status"] == "unavailable" for f in data["fundamentals"])
    assert snapshot()["calls"] == before


def test_expectations_baseline_separates_guidance_from_performance():
    claim = dict(
        title="Management expects renewals to stay steady",
        kind="guidance",
        stance="unknown",
        document_version_id="d",
    )
    briefs = baseline([], [], [claim], "2026-Q1")
    assert briefs[QUESTIONS[2]]["text"] != briefs[QUESTIONS[0]]["text"]
    assert "Management expects" in briefs[QUESTIONS[2]]["text"]
    assert "cannot establish" in briefs[QUESTIONS[2]]["text"]


def test_equivalent_timezone_offsets_share_a_model_request_identity():
    from datetime import timedelta

    doc = document()
    offset = timezone(timedelta(hours=8))
    same = doc | {
        "available_at": doc["available_at"].astimezone(offset),
        "published_at": doc["published_at"].astimezone(offset),
    }
    assert source_packet([doc], "NSTR", doc["available_at"]) == source_packet(
        [same], "NSTR", same["available_at"]
    )
