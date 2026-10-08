from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
import json
import os
from pathlib import Path
import pytest
from thesis.db import transaction, one
from thesis import service
from thesis.research.sec.performance import normalize_performance, METHOD
from thesis.research.sec.service import add_company
from test_sec_fundamentals import bundle, apply, CIK, NOW
from test_integration import payload, drain
from thesis.models import SaveIdea


def financial_bundle():
    annual = bundle(
        annual=True,
        accession="0000789019-25-000001",
        revenue=500,
        prior=400,
        income=100,
    )
    # Latest direct quarter and latest annual are independently selected.
    quarter = bundle(accession="0000789019-25-000002")
    base = deepcopy(annual)
    for k, v in base["submissions"]["filings"]["recent"].items():
        v += quarter["submissions"]["filings"]["recent"][k]
    for tag, data in quarter["companyfacts"]["facts"]["us-gaap"].items():
        base["companyfacts"]["facts"]["us-gaap"][tag]["units"]["USD"] += data["units"][
            "USD"
        ]
    for access, form, start in [
        ("0000789019-25-000001", "10-K", "2024-10-01"),
        ("0000789019-25-000002", "10-Q", "2025-01-01"),
    ]:
        for tag, value in [
            ("NetCashProvidedByUsedInOperatingActivities", 90),
            ("PaymentsToAcquirePropertyPlantAndEquipment", 35),
            ("CashAndCashEquivalentsAtCarryingValue", 70),
            ("LongTermDebtNoncurrent", 30),
            ("LongTermDebtCurrent", 5),
            ("CommercialPaper", 0),
            ("Assets", 200),
            ("Liabilities", 80),
        ]:
            f = dict(
                val=value, end="2025-09-30", accn=access, form=form, filed="2025-10-30"
            )
            if tag in (
                "NetCashProvidedByUsedInOperatingActivities",
                "PaymentsToAcquirePropertyPlantAndEquipment",
            ):
                f["start"] = start
            base["companyfacts"]["facts"]["us-gaap"].setdefault(
                tag, {"units": {"USD": []}}
            )["units"]["USD"].append(f)
    return base


def report(data=None, kind="quarter"):
    return normalize_performance(data or financial_bundle(), CIK, NOW)["reports"][kind]


def metrics(r):
    return {m["key"]: m for m in r["metrics"]}


def test_independent_periods_cash_ytd_and_debt_components():
    b = financial_bundle()
    annual = metrics(report(b, "annual"))
    quarter = metrics(report(b))
    assert annual["revenue"]["value"] == "500" and quarter["revenue"]["value"] == "120"
    assert quarter["operating_cash"]["start"] == "2025-01-01"
    assert quarter["revenue"]["start"] == "2025-07-01"
    assert quarter["free_cash_flow"]["value"] == "55"
    assert quarter["commercial_paper"]["value"] == "0"
    assert quarter["net_income"]["value"] is None
    assert quarter["liabilities_assets"]["value"] == "40"
    assert "total_debt" not in quarter
    assert quarter["revenue"]["prior"]["value"] == "100"


def test_no_quarter_cash_inference_or_cross_accession_stitching():
    b = financial_bundle()
    f = b["companyfacts"]["facts"]["us-gaap"][
        "PaymentsToAcquirePropertyPlantAndEquipment"
    ]["units"]["USD"][-1]
    f["start"] = "2025-07-01"
    m = metrics(report(b))
    assert m["free_cash_flow"]["value"] is None
    assert "different reporting periods" in m["free_cash_flow"]["reason"]
    f["accn"] = "0000789019-24-000001"
    assert metrics(report(b))["capital_spending"]["value"] is None


def test_conflicting_cash_values_missing_currency_and_decimal_precision():
    b = financial_bundle()
    f = b["companyfacts"]["facts"]["us-gaap"]["CashAndCashEquivalentsAtCarryingValue"][
        "units"
    ]["USD"]
    f.append(dict(f[-1], val=71))
    assert metrics(report(b))["cash"]["value"] is None
    f.pop()
    f[-1]["val"] = "70.000"
    assert metrics(report(b))["cash"]["value"] == "70"
    f[-1]["val"] = "1234567890123456.1234567890123456789"
    assert metrics(report(b))["cash"]["value"] == "1234567890123456.1234567890123456789"
    units = b["companyfacts"]["facts"]["us-gaap"][
        "CashAndCashEquivalentsAtCarryingValue"
    ]["units"]
    units["EUR"] = units.pop("USD")
    assert metrics(report(b))["cash"]["value"] is None


@pytest.mark.parametrize("value", ["NaN", "Infinity", "1e101"])
def test_invalid_financial_inputs_fail_closed(value):
    b = financial_bundle()
    b["companyfacts"]["facts"]["us-gaap"]["Assets"]["units"]["USD"][-1]["val"] = value
    with pytest.raises(ValueError):
        report(b)


def test_zero_assets_negative_capex_and_losses():
    b = financial_bundle()
    facts = b["companyfacts"]["facts"]["us-gaap"]
    facts["Assets"]["units"]["USD"][-1]["val"] = 0
    facts["PaymentsToAcquirePropertyPlantAndEquipment"]["units"]["USD"][-1]["val"] = -1
    facts["NetCashProvidedByUsedInOperatingActivities"]["units"]["USD"][-1]["val"] = -20
    m = metrics(report(b))
    assert (
        m["liabilities_assets"]["value"] is None
        and m["free_cash_flow"]["value"] is None
    )
    assert m["operating_cash"]["value"] == "-20"


def test_instant_dates_and_duration_conflicts_do_not_become_current():
    b = financial_bundle()
    facts = b["companyfacts"]["facts"]["us-gaap"]
    cash = facts["CashAndCashEquivalentsAtCarryingValue"]["units"]["USD"][-1]
    cash["end"] = "2025-06-30"
    assert metrics(report(b))["cash"]["value"] is None
    revenues = facts["RevenueFromContractWithCustomerExcludingAssessedTax"]["units"][
        "USD"
    ]
    revenues.append(dict(revenues[-2], start="2025-07-02"))
    assert metrics(report(b))["revenue"]["value"] is None


def test_amendment_without_facts_abstains_and_never_uses_old_accession():
    b = financial_bundle()
    r = b["submissions"]["filings"]["recent"]
    for k, v in r.items():
        v.append(v[-1])
    r["accessionNumber"][-1] = "0000789019-25-000003"
    r["form"][-1] = "10-Q/A"
    r["acceptanceDateTime"][-1] = "2025-10-31T20:00:00Z"
    r["filingDate"][-1] = "2025-10-31"
    latest = report(b)
    assert latest["form"] == "10-Q/A"
    assert all(m["value"] is None for m in latest["metrics"])


def test_wrong_company_and_naive_time_rejected():
    b = financial_bundle()
    b["companyfacts"]["cik"] = 1
    with pytest.raises(ValueError, match="another company"):
        report(b)
    with pytest.raises((ValueError, TypeError)):
        normalize_performance(financial_bundle(), CIK, NOW.replace(tzinfo=None))


def test_snapshot_corrections_returns_and_no_new_monitoring_noise(owner):
    iid = add_company("MSFT")["instrument_id"]
    b = financial_bundle()
    apply(iid, b)
    definition = payload().model_dump()
    definition["instrument_id"] = iid
    service.save_idea(owner, SaveIdea(**definition))
    drain(owner)
    before = service.state(owner, iid)
    sid = before["performance"]["snapshot_id"]
    assert before["performance"]["method"] == METHOD
    change = deepcopy(b)
    change["companyfacts"]["facts"]["us-gaap"]["Assets"]["units"]["USD"][-1][
        "val"
    ] = 250
    apply(iid, change)
    drain(owner)
    after = service.state(owner, iid)
    assert after["performance"]["snapshot_id"] != sid
    assert (
        after["changes"] == before["changes"]
        and after["versions"] == before["versions"]
    )
    apply(iid, b)
    assert service.state(owner, iid)["performance"]["snapshot_id"] == sid
    with transaction() as conn:
        assert (
            one(
                conn,
                "SELECT count(*) n FROM performance_snapshots WHERE instrument_id=%s",
                (iid,),
            )["n"]
            == 2
        )
        assert (
            one(conn, "SELECT data FROM performance_snapshots WHERE id=%s", (sid,))[
                "data"
            ]["reports"]["quarter"]["metrics"][9]["value"]
            == "200"
        )


def test_truncated_response_rolls_back_and_access_withdrawal_hides_financials(owner):
    iid = add_company("MSFT")["instrument_id"]
    apply(iid, financial_bundle())
    before = service.state(owner, iid)["performance"]
    with pytest.raises(ValueError, match="omits or predates"):
        apply(iid, bundle(accession="0000789019-25-000002"))
    assert (
        service.state(owner, iid)["performance"]["snapshot_id"] == before["snapshot_id"]
    )
    with transaction(admin=True) as conn:
        conn.execute(
            "UPDATE sources SET entitlement='fictional' WHERE id='sec-companyfacts'"
        )
    current = service.state(owner, iid)["performance"]
    assert current["status"] == "unavailable" and current["reports"] == {}


def test_read_only_application_role_and_immutable_evidence(owner):
    import psycopg

    iid = add_company("MSFT")["instrument_id"]
    apply(iid, financial_bundle())
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with transaction(owner) as conn:
            conn.execute("UPDATE performance_current SET checked_at=now()")
    with pytest.raises(psycopg.errors.RaiseException):
        with transaction(admin=True) as conn:
            conn.execute("UPDATE performance_snapshots SET method='changed'")


@pytest.mark.parametrize(
    "symbol,annual_fcf,quarter_fcf",
    [
        ("MSFT", "66987000000", "47348000000"),
        ("AAPL", "98767000000", "110197000000"),
        ("GOOGL", "73266000000", "4261000000"),
    ],
)
def test_actual_saved_sec_reports(symbol, annual_fcf, quarter_fcf):
    location = os.environ.get("THESIS_REAL_CORPUS")
    if not location:
        pytest.skip("Opt-in actual SEC corpus")
    record = json.loads((Path(location) / (symbol + ".json")).read_text())
    b = record["payload"]
    data = normalize_performance(
        b, b["companyfacts"]["cik"], datetime.fromisoformat(record["retrieved_at"])
    )
    for kind, expected in [("annual", annual_fcf), ("quarter", quarter_fcf)]:
        r = data["reports"][kind]
        m = metrics(r)
        assert m["free_cash_flow"]["value"] == expected
        assert Decimal(m["liabilities_assets"]["value"]) > 0
        assert all(
            i["accession"] == r["accession"]
            for row in r["metrics"]
            for i in row["inputs"]
        )
        assert m["operating_cash"]["start"] == m["capital_spending"]["start"]
