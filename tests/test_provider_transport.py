"""HTTP contract and diagnostics: mocked transport only, never real keys."""

from uuid import uuid4
import httpx
import pytest
from thesis.providers import openai, ledger
from thesis.providers.settings import REASONING_MODEL


@pytest.mark.parametrize(
    "model,read_timeout", [(REASONING_MODEL, 180), ("legacy-mini", 60)]
)
def test_client_request_id_and_timeout_are_bounded_without_retry(
    monkeypatch, model, read_timeout
):
    seen = {}
    call_id = uuid4()
    monkeypatch.setattr(openai, "live_key", lambda _: "fake-local-test-key")
    monkeypatch.setattr(
        ledger, "authorize_dispatch", lambda *a, **k: seen.update(authorized=True)
    )

    class Client:
        def __init__(self, **kwargs):
            assert kwargs["timeout"].read == read_timeout
            assert kwargs["timeout"].connect == 15
            assert kwargs["follow_redirects"] is False

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def post(self, url, **kwargs):
            assert seen["authorized"]
            seen["headers"] = kwargs["headers"]
            seen["calls"] = seen.get("calls", 0) + 1
            return httpx.Response(200, json={"id": "response-only"})

    monkeypatch.setattr(openai.httpx, "Client", Client)
    assert openai.send({"model": model}, call_id) == {"id": "response-only"}
    assert seen["headers"]["X-Client-Request-Id"] == str(call_id) and seen["calls"] == 1


def test_timeout_is_specific_and_does_not_expose_exception_or_retry(monkeypatch):
    monkeypatch.setattr(openai, "live_key", lambda _: "secret-never-log")
    monkeypatch.setattr(ledger, "authorize_dispatch", lambda *a, **k: None)
    calls = []

    class Client:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def post(self, *a, **kwargs):
            calls.append(1)
            raise httpx.ReadTimeout("secret-never-log")

    monkeypatch.setattr(openai.httpx, "Client", Client)
    with pytest.raises(openai.ProviderFailure, match="^transport_timeout$"):
        openai.send({"model": REASONING_MODEL}, uuid4())
    assert len(calls) == 1
