"""Bounded source diagnostics, without leaking transport bodies or identities."""
import httpx
import pytest

from thesis.db import transaction, one
from thesis.research.sec import client
from thesis.research.sec.service import add_company, refresh
from test_sec_fundamentals import CIK, bundle, apply


@pytest.mark.parametrize("stage", ["submissions", "companyfacts"])
@pytest.mark.parametrize("failure,code,phrase", [
    ("timeout", "timeout", "took too long"),
    ("connection", "connection", "connection to SEC failed"),
    ("invalid_json", "invalid_response", "unreadable data"),
    ("invalid_object", "invalid_response", "unreadable data"),
    ("size", "size_limit", "size limit"),
    ("http", "http_status", "Response code: 503"),
])
def test_fetch_failure_records_safe_stage_without_retry(monkeypatch, stage, failure, code, phrase):
    monkeypatch.setattr(client, "identity", lambda: "Private identity private@example.org")
    monkeypatch.setattr(client, "reserve_request", lambda: None)
    monkeypatch.setattr(client, "MAX_BYTES", 32)
    requests = []

    def handler(request):
        requests.append(request)
        current = "submissions" if "/submissions/" in request.url.path else "companyfacts"
        if current != stage:
            return httpx.Response(200, json={})
        if failure == "timeout":
            raise httpx.ReadTimeout("private token and request body", request=request)
        if failure == "connection":
            raise httpx.ConnectError("private token and request body", request=request)
        if failure == "invalid_json":
            return httpx.Response(200, content=b"private invalid response")
        if failure == "invalid_object":
            return httpx.Response(200, json=[])
        if failure == "size":
            return httpx.Response(200, content=b"x" * 33)
        return httpx.Response(503, text="private token and request body")

    with pytest.raises(client.SourceFailure) as caught:
        client.fetch_bundle(CIK, transport=httpx.MockTransport(handler))
    error = caught.value
    assert error.code == code
    assert error.stage == stage
    assert len(requests) == (1 if stage == "submissions" else 2)
    message = client.failure_message(error)
    assert phrase in message
    assert ("filing list" if stage == "submissions" else "reported financial figures") in message
    assert "private" not in message and "example.org" not in message


def test_busy_and_unknown_errors_do_not_echo_exception_text(monkeypatch):
    monkeypatch.setattr(client, "identity", lambda: "Private identity private@example.org")

    def busy():
        raise client.SourceFailure("private details", code="busy")

    monkeypatch.setattr(client, "reserve_request", busy)
    with pytest.raises(client.SourceFailure) as caught:
        client.fetch_bundle(CIK, transport=httpx.MockTransport(lambda _: pytest.fail("No dispatch when busy")))
    assert "Another filing request" in client.failure_message(caught.value)
    for error in [ValueError("private details"), client.SourceFailure("private details", code="private token")]:
        assert client.failure_message(error) == "SEC refresh failed; no new evidence committed."
    assert client.failure_message(client.SourceFailure("private details", denied=True, code="timeout")) == "SEC access denied or rate-limited."
    malformed_metadata = client.SourceFailure("private details", code="http_status", stage="private details", status="private details")
    assert "private" not in client.failure_message(malformed_metadata)


def test_known_failure_survives_refresh_without_changing_saved_filing(owner):
    iid = add_company("MSFT")["instrument_id"]
    apply(iid, bundle())
    with transaction(admin=True, consistent=True) as conn:
        before = one(conn, "SELECT * FROM sec_payload_current WHERE instrument_id=%s", (iid,))

    def fail(_):
        raise client.SourceFailure("private URL and contact identity", code="timeout", stage="companyfacts")

    with pytest.raises(ValueError, match="took too long.*reported financial figures") as caught:
        refresh(iid, fetcher=fail)
    with transaction(admin=True, consistent=True) as conn:
        assert one(conn, "SELECT * FROM sec_payload_current WHERE instrument_id=%s", (iid,)) == before
        state = one(conn, "SELECT * FROM sec_refresh_state WHERE instrument_id=%s", (iid,))
        check = one(conn, "SELECT outcome,error FROM source_checks WHERE instrument_id=%s AND source_id='sec-companyfacts' ORDER BY checked_at DESC LIMIT 1", (iid,))
    assert state["last_error"] == str(caught.value) == check["error"]
    assert state["lease_until"] is None and check["outcome"] == "failed"
    assert "private" not in str(caught.value)
    with pytest.raises(ValueError, match="15 minutes"):
        refresh(iid, fetcher=lambda _: pytest.fail("Cooldown still applies"))
