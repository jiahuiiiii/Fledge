"""Export isolation, historical fidelity and inert output; no provider calls."""

from copy import deepcopy
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from thesis import service, review_export
from thesis.config import OWNER
from thesis.db import transaction
from thesis.providers import ledger
from thesis.research import idea_review
from test_integration import payload, drain
from test_private_isolation import review_response, another_account


def test_selected_historical_assessment_survives_changes_and_archive(
    owner, monkeypatch
):
    first = service.save_idea(owner, payload())
    drain(owner)
    original = service.state(owner)["versions"][0]["evaluations"][0]
    service.advance(owner, 0)
    drain(owner)
    service.save_idea(owner, payload(revision=1, threshold="99", status="archived"))
    monkeypatch.setattr(
        ledger, "execute", lambda *a, **k: pytest.fail("Export attempted paid call")
    )
    filename, html = review_export.download(
        owner, first["version_id"], evaluation_id=original["id"]
    )
    assert "-r1-" in filename
    assert "revision 1 · monitoring when saved" in html
    assert "18.00%" in html and "99%" not in html
    assert "At least 15%" in html and "Recorded fictional demonstration" in html
    assert "12.00%" not in html
    assert "Evidence cutoff" in html and "Not marked reviewed" in html
    assert "No new data or paid model request" in html


def test_definition_export_does_not_imply_evaluation_or_include_later_research(owner):
    first = service.save_idea(owner, payload(status="draft", conditions=False))
    record = review_export.prepare(owner, first["version_id"])
    html = review_export.render(record)
    assert record["sources"] == {} and record["cutoff"] is None
    assert "No evidence assessed in this definition export" in html
    assert "No numerical conditions were defined" in html
    assert (
        "Saved AI interpretation" not in html
        and "Historical source register" not in html
    )


def test_cross_owner_and_mismatched_record_are_rejected(owner):
    first = service.save_idea(owner, payload())
    drain(owner)
    e = service.state(owner)["versions"][0]["evaluations"][0]
    second = service.save_idea(owner, payload(revision=1))
    other = another_account()
    with pytest.raises(service.Missing):
        review_export.prepare(other, first["version_id"], evaluation_id=e["id"])
    with pytest.raises(service.Missing):
        review_export.prepare(owner, second["version_id"], evaluation_id=e["id"])
    with pytest.raises(service.Missing):
        review_export.prepare(owner, first["version_id"], comparison_id=uuid4())
    with pytest.raises(ValueError, match="Choose one"):
        review_export.prepare(
            owner, first["version_id"], evaluation_id=e["id"], comparison_id=uuid4()
        )


def test_actual_source_gate_withholds_old_result_when_access_is_removed(owner):
    saved = service.save_idea(owner, payload())
    drain(owner)
    evaluation = service.state(owner)["versions"][0]["evaluations"][0]
    with transaction(admin=True) as conn:
        definition=conn.execute("SELECT pg_get_constraintdef(oid) definition FROM pg_constraint WHERE conrelid='sources'::regclass AND conname='sources_entitlement_check'").fetchone()["definition"]
        original=conn.execute("SELECT id,entitlement FROM sources").fetchall()
        conn.execute("ALTER TABLE sources DROP CONSTRAINT sources_entitlement_check")
        conn.execute("UPDATE sources SET entitlement='restricted'")
    try:
        report = review_export.prepare(owner, saved["version_id"], evaluation_id=evaluation["id"])
        html = review_export.render(report)
        assert report["sources"] == {} and report["unavailable_source_count"] > 0
        assert "18.00%" not in html and "Historical result withheld" in html
        assert "source-text" in html
    finally:
        with transaction(admin=True) as conn:
            for source in original:
                conn.execute("UPDATE sources SET entitlement=%s WHERE id=%s",(source["entitlement"],source["id"]))
            conn.execute("ALTER TABLE sources ADD CONSTRAINT sources_entitlement_check " + definition)


def test_selected_comparison_quotes_are_escaped_and_restricted_citations_withheld(
    owner,
):
    saved = service.save_idea(owner, payload(status="draft", conditions=False))
    state = service.state(owner)
    result = idea_review.generate(
        owner, saved["version_id"], state["snapshot_id"], transport=review_response
    )
    before = ledger.snapshot()
    report = review_export.prepare(
        owner, saved["version_id"], comparison_id=result["id"]
    )
    html = review_export.render(report)
    assert (
        "Saved AI interpretation" in html
        and result["points"][0]["citations"][0]["quote"] in html
    )
    assert ledger.snapshot() == before
    unsafe = deepcopy(report)
    unsafe["version"]["reasoning"] = "<script>alert('private')</script>"
    unsafe["comparison"]["points"][0]["text"] = "<img src=x onerror=alert(1)>"
    for d in unsafe["sources"].values():
        d["url"] = "javascript:alert(1)"
    html = review_export.render(unsafe)
    assert "<script>" not in html and "<img" not in html and "javascript:" not in html
    assert "&lt;script&gt;" in html and "&lt;img" in html
    unsafe["sources"] = {}
    html = review_export.render(unsafe)
    assert "Interpretation withheld" in html and "&lt;img" not in html


def test_download_endpoint_requires_session_and_returns_attachment(owner):
    from thesis.app import app

    saved = service.save_idea(OWNER, payload(status="draft", conditions=False))
    path = f"/api/v1/ideas/versions/{saved['version_id']}/review-export"
    with TestClient(app) as client:
        assert client.get(path).status_code == 401
        client.get("/api/v1/session")
        response = client.get(path)
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        assert response.headers["content-disposition"].startswith(
            'attachment; filename="fledge-'
        )
        assert response.headers["cache-control"] == "no-store"
        assert (
            client.get(
                path, headers={"origin": "https://elsewhere.invalid"}
            ).status_code
            == 403
        )


def test_export_does_not_disclose_raw_provider_calls_or_other_ideas(owner):
    first = service.save_idea(owner, payload())
    drain(owner)
    other = another_account()
    other_payload = payload(status="draft", conditions=False).model_copy(
        update={"reasoning": "OTHER PRIVATE REASONING SECRET"}
    )
    service.save_idea(other, other_payload)
    filename, html = review_export.download(owner, first["version_id"])
    assert (
        "OTHER PRIVATE" not in html
        and "request_body" not in html
        and "Authorization" not in html
    )
