"""The company read carries alert status only; details load separately; disposable database only."""
from fastapi.testclient import TestClient

from thesis import service
from thesis.db import transaction
from thesis.monitoring import news_watch


def test_status_only_list_never_loads_readings(owner, monkeypatch):
    monkeypatch.setattr("thesis.research.sentiment.present", lambda *a, **k: (_ for _ in ()).throw(AssertionError("loaded a reading")))
    with transaction(owner, consistent=True) as c:
        assert all(a.get("status_only") for a in news_watch.list_alerts(c, owner, previous=False, details=False))


def test_company_read_sends_status_only_alerts(owner, monkeypatch):
    seen = []
    real = news_watch.list_alerts
    monkeypatch.setattr(news_watch, "list_alerts", lambda *a, **k: seen.append(k) or real(*a, **k))
    service.state(owner, include_financials=False)
    assert seen and seen[-1].get("details") is False


def test_alerts_endpoint_returns_this_companys_details(owner, monkeypatch):
    import thesis.app as module

    monkeypatch.setattr(module, "OWNER", owner)
    client = TestClient(module.app, base_url="http://127.0.0.1")
    client.get("/api/v1/session")
    iid = service.state(owner, include_financials=False)["instrument"]["id"]
    calls = []
    real = news_watch.list_alerts
    monkeypatch.setattr(news_watch, "list_alerts", lambda *a, **k: calls.append(k) or real(*a, **k))
    response = client.get(f"/api/v1/companies/{iid}/alerts")
    assert response.status_code == 200 and isinstance(response.json()["result"], list)
    assert calls[-1]["detail_instrument"] == str(iid) and calls[-1].get("details", True)
