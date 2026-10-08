from copy import deepcopy
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from uuid import uuid4
import json
from pathlib import Path
import os
import pytest
from pydantic import ValidationError
from thesis import valuation, service
from thesis.db import transaction, one, rows
from thesis.research import multiples
from test_performance import financial_bundle
from test_sec_fundamentals import apply
from thesis.research.sec.service import add_company


def request(iid, snapshot, **kw):
    return dict(
        instrument_id=iid,
        performance_id=str(snapshot),
        title="Authored valuation cases",
        method="earnings",
        years=2,
        growth_step="5",
        margin_step="5",
        cases=[
            dict(
                name="Case A",
                growth="10",
                margin="20",
                multiple="25",
                rationale="Authored numerical illustration, not a forecast.",
                reference_id=None,
            )
        ],
        **kw
    )


def setup(owner):
    # The shared owner fixture truncates sources after migrations.
    with transaction(admin=True) as conn:
        conn.execute(
            "INSERT INTO sources VALUES('finnhub-financials','Finnhub reported multiples','finnhub-pitch') ON CONFLICT DO NOTHING"
        )
    iid = add_company("MSFT")["instrument_id"]
    apply(iid, financial_bundle())
    sid = service.state(owner, iid)["performance"]["snapshot_id"]
    return iid, request(iid, sid)


def test_explicit_equity_math_and_two_axis_sensitivity(owner):
    iid, data = setup(owner)
    result = valuation.preview(owner, valuation.ScenarioRequest(**data))
    c = result["result"]["cases"][0]
    assert (
        c["revenue"] == "605"
        and c["net_income"] == "121"
        and c["equity_value"] == "3025"
    )
    assert result["result"]["target_period_end"] == "2027-09-30"
    assert c["sensitivity"]["columns"] == ["15", "20", "25"]
    assert c["sensitivity"]["rows"][1]["cells"][1]["equity_value"] == "3025"
    assert len(c["sensitivity"]["rows"]) == 3
    assert result["saved"] is False
    data["method"] = "sales"
    data["cases"][0].update(margin=None, multiple="4")
    c = valuation.preview(owner, valuation.ScenarioRequest(**data))["result"]["cases"][
        0
    ]
    assert c["net_income"] is None and c["equity_value"] == "2420"
    assert c["sensitivity"]["columns"] == ["3", "4", "5"]
    assert (
        len(
            valuation.preview(owner, valuation.ScenarioRequest(**data))["result"][
                "formulas"
            ]
        )
        == 2
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("growth", "NaN"),
        ("growth", "201"),
        ("margin", "101"),
        ("multiple", "0"),
        ("multiple", "Infinity"),
        ("growth", "0.1234567"),
    ],
)
def test_bad_financial_assumptions_rejected(field, value):
    p = request(str(uuid4()), str(uuid4()))
    p["cases"][0][field] = value
    with pytest.raises(ValidationError):
        valuation.ScenarioRequest(**p)


def test_incomplete_duplicate_and_wrong_method_inputs_rejected():
    p = request(str(uuid4()), str(uuid4()))
    p["cases"][0]["margin"] = None
    with pytest.raises(ValidationError):
        valuation.ScenarioRequest(**p)
    p["method"] = "sales"
    p["cases"] *= 2
    with pytest.raises(ValidationError):
        valuation.ScenarioRequest(**p)
    p["cases"] = p["cases"][:1]
    p["years"] = True
    with pytest.raises(ValidationError):
        valuation.ScenarioRequest(**p)


@pytest.mark.parametrize("growth,margin", [("-100", "20"), ("10", "0"), ("10", "-5")])
def test_zero_or_loss_makes_earnings_multiple_undefined(owner, growth, margin):
    _, data = setup(owner)
    data["cases"][0].update(growth=growth, margin=margin)
    c = valuation.preview(owner, valuation.ScenarioRequest(**data))["result"]["cases"][
        0
    ]
    assert c["equity_value"] is None and "Positive projected earnings" in c["reason"]
    assert all(
        "reason" in cell for row in c["sensitivity"]["rows"] for cell in row["cells"]
    )


def test_source_pin_new_data_and_later_history(owner):
    iid, data = setup(owner)
    saved = valuation.save(owner, valuation.SaveScenario(**data, request_id=uuid4()))
    b = financial_bundle()
    b["companyfacts"]["facts"]["us-gaap"][
        "RevenueFromContractWithCustomerExcludingAssessedTax"
    ]["units"]["USD"][0]["val"] = 600
    apply(iid, b)
    with pytest.raises(service.Conflict):
        valuation.preview(owner, valuation.ScenarioRequest(**data))
    original = valuation.get(owner, saved["id"])
    assert original["newer_financials_available"]
    assert (
        original["packet"]["base"]["value"] == "500"
        and original["result"]["cases"][0]["equity_value"] == "3025"
    )
    assert valuation.context(owner, iid)["saved"][0]["id"] == saved["id"]


def test_idempotent_concurrent_save_conflicting_key_and_owner_isolation(owner):
    from concurrent.futures import ThreadPoolExecutor
    import psycopg

    iid, data = setup(owner)
    req = valuation.SaveScenario(**data, request_id=uuid4())
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: valuation.save(owner, req), range(2)))
    assert results[0]["id"] == results[1]["id"]
    altered = req.model_copy(update={"title": "Different case"})
    with pytest.raises(service.Conflict):
        valuation.save(owner, altered)
    other = uuid4()
    with transaction(admin=True) as conn:
        conn.execute(
            "INSERT INTO accounts VALUES(%s,%s)", (other, "Other test account")
        )
    assert valuation.context(other, iid)["saved"] == []
    with pytest.raises(service.Missing):
        valuation.get(other, results[0]["id"])
    with transaction(other) as conn:
        assert rows(conn, "SELECT id FROM valuation_scenarios") == []
    with pytest.raises(psycopg.errors.RaiseException):
        with transaction(admin=True) as conn:
            conn.execute("UPDATE valuation_scenarios SET request_hash='changed'")


def test_missing_annual_and_wrong_company_are_not_annualized(owner):
    iid, data = setup(owner)
    other = add_company("AAPL")["instrument_id"]
    data["instrument_id"] = other
    with pytest.raises(service.Missing):
        valuation.preview(owner, valuation.ScenarioRequest(**data))
    from test_sec_fundamentals import bundle

    only = add_company("GOOGL")["instrument_id"]
    b = bundle()
    b["companyfacts"]["cik"] = 1652044
    b["submissions"]["cik"] = "0001652044"
    apply(only, b)
    data["instrument_id"] = only
    data["performance_id"] = str(
        service.state(owner, only)["performance"]["snapshot_id"]
    )
    with pytest.raises(ValueError, match="annual filing"):
        valuation.preview(owner, valuation.ScenarioRequest(**data))


def provider(symbol="MSFT", pe="28.5", ps="11.2"):
    return {"symbol": symbol, "metricType": "all", "metric": {"peTTM": pe, "psTTM": ps}}


def test_reference_validation_empty_negative_and_wrong_company():
    values = multiples.normalized(provider(pe=-1, ps=None), "MSFT")
    assert all(v["value"] is None for v in values.values())
    assert multiples.normalized(provider(pe=True), "MSFT")["earnings"]["value"] is None
    with pytest.raises(ValueError):
        multiples.normalized(provider("AAPL"), "MSFT")


def test_manual_reference_refresh_cooldown_and_preserved_failure(owner):
    iid, data = setup(owner)
    calls = []

    def fetch(endpoint, params):
        calls.append((endpoint, params))
        return provider()

    ref = multiples.refresh(iid, fetcher=fetch)
    with pytest.raises(ValueError, match="one hour"):
        multiples.refresh(iid, fetcher=fetch)
    assert len(calls) == 1
    case = data["cases"][0]
    case.update(reference_id=ref["id"], multiple="28.5")
    response = valuation.preview(owner, valuation.ScenarioRequest(**data))
    assert response["packet"]["references"][0]["id"] == ref["id"]
    case["multiple"] = "25"
    with pytest.raises(ValueError, match="differs"):
        valuation.preview(owner, valuation.ScenarioRequest(**data))
    with transaction(source=True) as conn:
        conn.execute(
            "UPDATE multiple_refresh_state SET last_attempt_at=now()-interval '2 hours' WHERE instrument_id=%s",
            (iid,),
        )

    def fail(*args):
        raise RuntimeError("Secret provider body must not be stored")

    with pytest.raises(ValueError):
        multiples.refresh(iid, fetcher=fail)
    c = valuation.context(owner, iid)["references"][0]
    assert (
        c["reference"]["id"] == UUID(ref["id"])
        and "Secret" not in c["refresh"]["error"]
    )


from uuid import UUID


def test_withdrawal_hides_sources_and_derived_values_in_private_export(owner):
    iid, data = setup(owner)
    data["title"] = "<script>alert(1)</script>"
    saved = valuation.save(owner, valuation.SaveScenario(**data, request_id=uuid4()))
    name, html = valuation.download(owner, saved["id"])
    assert "<script>" not in html and "&lt;script&gt;" in html and "3025" in html
    assert "sensitivity" in html and "default-src 'none'" in html
    with transaction(admin=True) as conn:
        conn.execute(
            "UPDATE sources SET entitlement='fictional' WHERE id='sec-companyfacts'"
        )
    r = valuation.get(owner, saved["id"])
    assert r["withheld"] and r["packet"] is None and r["result"] is None
    assert "3025" not in valuation.download(owner, saved["id"])[1]
    with pytest.raises(ValueError):
        valuation.preview(owner, valuation.ScenarioRequest(**data))


def test_authenticated_endpoints(owner, monkeypatch):
    from fastapi.testclient import TestClient
    import thesis.app as module

    iid, data = setup(owner)
    monkeypatch.setattr(module, "OWNER", owner)
    client = TestClient(module.app)
    assert client.get("/api/v1/companies/" + iid + "/valuation").status_code == 401
    client.get("/api/v1/session")
    headers = {"X-Thesis-Request": "local-ui"}
    assert (
        client.post("/api/v1/valuation/preview", json=data, headers=headers).status_code
        == 200
    )
    assert client.post("/api/v1/valuation/preview", json=data).status_code == 403
    saved = client.post(
        "/api/v1/valuation/save",
        json=dict(data, request_id=str(uuid4())),
        headers=headers,
    ).json()["result"]
    assert client.get("/api/v1/valuations/" + saved["id"]).status_code == 200
    r = client.get("/api/v1/valuations/" + saved["id"] + "/export")
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    assert (
        len(
            client.get("/api/v1/companies/" + iid + "/valuation").json()["result"][
                "saved"
            ]
        )
        == 1
    )


@pytest.mark.parametrize("symbol", ["MSFT", "AAPL", "GOOGL"])
def test_actual_saved_filing_scenario_math(owner, symbol):
    corpus = os.environ.get("THESIS_REAL_CORPUS")
    if not corpus:
        pytest.skip("Opt-in actual SEC corpus")
    b = json.loads((Path(corpus) / (symbol + ".json")).read_text())["payload"]
    iid = add_company(symbol)["instrument_id"]
    apply(iid, b)
    performance = service.state(owner, iid)["performance"]
    p = request(iid, performance["snapshot_id"])
    p["years"] = 1
    p["cases"][0].update(growth="0", margin="10", multiple="10")
    result = valuation.preview(owner, valuation.ScenarioRequest(**p))
    # Fixed authored assumptions make equity numerically equal to annual revenue.
    assert Decimal(result["result"]["cases"][0]["equity_value"]) == Decimal(
        result["packet"]["base"]["value"]
    )
    assert result["packet"]["base"]["start"] < result["packet"]["base"]["end"]


def test_reference_expired_attempt_cannot_publish(owner):
    iid, _ = setup(owner)

    def late(*args):
        with transaction(source=True) as conn:
            conn.execute(
                "UPDATE multiple_refresh_state SET lease_until=now()-interval '1 second' WHERE instrument_id=%s",
                (iid,),
            )
        return provider()

    with pytest.raises(ValueError):
        multiples.refresh(iid, fetcher=late)
    with transaction() as conn:
        assert one(conn, "SELECT count(*) n FROM multiple_references")["n"] == 0


def test_reference_withdrawal_hides_saved_derived_result(owner):
    iid, data = setup(owner)
    ref = multiples.refresh(iid, fetcher=lambda *args: provider())
    data["cases"][0].update(reference_id=ref["id"], multiple="28.5")
    saved = valuation.save(owner, valuation.SaveScenario(**data, request_id=uuid4()))
    with transaction(admin=True) as conn:
        conn.execute(
            "UPDATE sources SET entitlement='fictional' WHERE id='finnhub-financials'"
        )
    assert valuation.get(owner, saved["id"])["withheld"]
    assert valuation.context(owner, iid)["references"][0]["reference"] is None
    assert "3448.5" not in valuation.download(owner, saved["id"])[1]
    with pytest.raises(ValueError):
        valuation.preview(owner, valuation.ScenarioRequest(**data))
