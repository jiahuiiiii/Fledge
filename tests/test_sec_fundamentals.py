from copy import deepcopy
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from uuid import uuid4
import httpx
import pytest
from thesis import service
from thesis.db import transaction, one
from thesis.models import SaveIdea
from thesis.research.sec.normalize import normalize, REVENUE
from thesis.research.sec.service import add_company, commit_bundle, refresh
from thesis.research.sec import client
from test_integration import payload, drain

CIK = 789019
NOW = datetime(2026, 10, 1, tzinfo=timezone.utc)


def bundle(
    annual=False, accession="0000789019-25-000001", revenue=120, prior=100, income=30
):
    form = "10-K" if annual else "10-Q"
    start = "2024-10-01" if annual else "2025-07-01"
    prior_start = "2023-10-01" if annual else "2024-07-01"
    end = "2025-09-30"
    prior_end = "2024-09-30"
    filed = "2025-10-30"

    def fact(value, s, e):
        return dict(
            val=value,
            start=s,
            end=e,
            accn=accession,
            form=form,
            filed=filed,
            fy=2025,
            fp="FY" if annual else "Q1",
        )

    facts = {
        "cik": CIK,
        "entityName": "Example operating company",
        "facts": {
            "us-gaap": {
                REVENUE[0]: {
                    "units": {
                        "USD": [
                            fact(revenue, start, end),
                            fact(prior, prior_start, prior_end),
                        ]
                    }
                },
                "OperatingIncomeLoss": {"units": {"USD": [fact(income, start, end)]}},
            }
        },
    }
    submissions = {
        "cik": str(CIK).zfill(10),
        "name": "Example operating company",
        "filings": {
            "recent": {
                "accessionNumber": [accession],
                "form": [form],
                "filingDate": [filed],
                "reportDate": [end],
                "acceptanceDateTime": [filed + "T20:00:00Z"],
                "primaryDocument": ["example-20250930.htm"],
            }
        },
    }
    return dict(companyfacts=facts, submissions=submissions)


def parsed(data=None):
    data = data or bundle()
    return normalize(data["companyfacts"], data["submissions"], CIK, NOW)


def apply(iid, data):
    with transaction(admin=True) as conn:
        return commit_bundle(conn, iid, data, datetime.now(timezone.utc))


def test_direct_quarter_excludes_ytd_and_keeps_exact_input_dates():
    data = bundle()
    facts = data["companyfacts"]["facts"]["us-gaap"]
    ytd = deepcopy(facts[REVENUE[0]]["units"]["USD"][0])
    ytd.update(start="2025-01-01", val=400)
    facts[REVENUE[0]]["units"]["USD"].append(ytd)
    result = parsed(data)
    assert result["period"] == "Quarter ended 2025-09-30"
    assert [Decimal(c["value"]) for c in result["calculations"]] == [
        Decimal("20"),
        Decimal("25"),
    ]
    assert all(
        c["inputs"][0]["accession"] == result["accession"]
        for c in result["calculations"]
    )


def test_annual_and_53_week_dates_are_not_calendar_quarters():
    data = bundle(annual=True)
    for concept in data["companyfacts"]["facts"]["us-gaap"].values():
        for f in concept["units"]["USD"]:
            if f["end"] == "2025-09-30":
                f.update(start="2024-09-29", end="2025-10-04")
            else:
                f.update(start="2023-10-01", end="2024-09-28")
    data["submissions"]["filings"]["recent"]["reportDate"] = ["2025-10-04"]
    result = parsed(data)
    assert result["period_type"] == "annual"
    assert Decimal(result["calculations"][0]["value"]) == 20


@pytest.mark.parametrize(
    "mutation", ["currency", "conflict", "zero", "different-period", "wrong-accession"]
)
def test_incompatible_ratio_inputs_abstain(mutation):
    data = bundle()
    facts = data["companyfacts"]["facts"]["us-gaap"]
    if mutation == "currency":
        facts["OperatingIncomeLoss"]["units"]["EUR"] = facts["OperatingIncomeLoss"][
            "units"
        ].pop("USD")
    elif mutation == "conflict":
        other = deepcopy(facts[REVENUE[0]])
        other["units"]["USD"][0]["val"] = 999
        facts[REVENUE[1]] = other
    elif mutation == "zero":
        facts[REVENUE[0]]["units"]["USD"][0]["val"] = 0
    elif mutation == "different-period":
        facts["OperatingIncomeLoss"]["units"]["USD"][0]["start"] = "2025-07-02"
    else:
        facts["OperatingIncomeLoss"]["units"]["USD"][0]["accn"] = "0000789019-25-000002"
    result = parsed(data)
    assert result["calculations"][1]["value"] is None
    assert result["calculations"][1]["reason"]


def test_wrong_company_and_naive_timestamp_fail():
    data = bundle()
    data["companyfacts"]["cik"] = 320193
    with pytest.raises(ValueError, match="another company"):
        parsed(data)
    data = bundle()
    data["submissions"]["filings"]["recent"]["acceptanceDateTime"] = [
        "2025-10-30T20:00:00"
    ]
    with pytest.raises(ValueError, match="timezone"):
        parsed(data)


def test_no_display_rounding_before_condition_evaluation(owner):
    iid = add_company("MSFT")["instrument_id"]
    apply(iid, bundle(revenue=1149999, prior=1000000))
    p = payload().model_dump()
    p.update(instrument_id=iid)
    p["conditions"] = p["conditions"][:1]
    service.save_idea(owner, SaveIdea(**p))
    drain(owner)
    result = service.state(owner, iid)["versions"][0]["evaluations"][0]["results"][0]
    assert (
        result["observed_value"] == Decimal("14.999900")
        and result["outcome"] == "not_met"
    )


def test_annual_scope_is_explicit_and_private_history_preserved(owner):
    iid = add_company("MSFT")["instrument_id"]
    apply(iid, bundle(annual=True))
    p = payload().model_dump()
    p["instrument_id"] = iid
    saved = service.save_idea(owner, SaveIdea(**p))
    drain(owner)
    data = service.state(owner, iid)
    assert data["demo"]["period_type"] == "annual"
    assert data["versions"][0]["evaluations"][0]["outcome"] == "unknown"
    assert data["fundamentals"][0]["value"] == 20
    p["expected_revision"] = 1
    for c in p["conditions"]:
        c["period_type"] = "annual"
    service.save_idea(owner, SaveIdea(**p))
    drain(owner)
    data = service.state(owner, iid)
    assert data["versions"][0]["evaluations"][0]["outcome"] == "met"
    assert data["versions"][1]["evaluations"][0]["outcome"] == "unknown"
    assert data["selected_passages"] is None
    with pytest.raises(ValueError, match="fictional"):
        service.research_selection(data["demo"]["stage"], iid)


def test_repeated_bundle_creates_no_extra_version_or_review(owner):
    iid = add_company("MSFT")["instrument_id"]
    data = bundle()
    apply(iid, data)
    p = payload().model_dump()
    p["instrument_id"] = iid
    service.save_idea(owner, SaveIdea(**p))
    drain(owner)
    before = service.state(owner, iid)
    apply(iid, data)
    drain(owner)
    after = service.state(owner, iid)
    assert (
        before["documents"] == after["documents"]
        and before["versions"] == after["versions"]
    )
    assert not after["changes"]
    assert (
        after["filing_calculations"][0]["calculations"][0]["inputs"][1]["value"]
        == "100"
    )


def test_amendment_without_figures_does_not_resurrect_old_facts(owner):
    iid = add_company("MSFT")["instrument_id"]
    apply(iid, bundle())
    p = payload().model_dump()
    p["instrument_id"] = iid
    service.save_idea(owner, SaveIdea(**p))
    drain(owner)
    old = service.state(owner, iid)["versions"][0]["evaluations"][0]
    data = bundle(accession="0000789019-25-000002")
    recent = data["submissions"]["filings"]["recent"]
    recent["form"] = ["10-Q/A"]
    recent["acceptanceDateTime"] = ["2025-10-31T20:00:00Z"]
    recent["filingDate"] = ["2025-10-31"]
    data["companyfacts"]["facts"] = {}
    apply(iid, data)
    drain(owner)
    current = service.state(owner, iid)
    assert all(f["value"] is None for f in current["fundamentals"])
    assert current["versions"][0]["evaluations"][0]["outcome"] == "unknown"
    assert current["versions"][0]["evaluations"][1]["id"] == old["id"]
    assert current["versions"][0]["evaluations"][1]["results"] == old["results"]


def test_failed_refresh_keeps_evidence_and_records_coverage_gap(owner):
    iid = add_company("MSFT")["instrument_id"]
    apply(iid, bundle())
    before = service.state(owner, iid)

    def denied(cik):
        raise client.SourceFailure("private transport details", denied=True)

    with pytest.raises(ValueError, match="denied"):
        refresh(iid, fetcher=denied)
    after = service.state(owner, iid)
    assert after["documents"] == before["documents"]
    assert after["source_checks"][0]["state"] == "denied"
    with pytest.raises(ValueError, match="15 minutes"):
        refresh(iid, fetcher=lambda _: bundle())


def test_sec_http_allowlist_user_agent_limits_and_no_retry(owner, monkeypatch):
    monkeypatch.setattr(
        client, "identity", lambda: "Thesis tests developer@example.org"
    )
    monkeypatch.setattr(client, "reserve_request", lambda: None)
    requests = []

    def handler(request):
        requests.append(request)
        assert request.url.host == "data.sec.gov"
        assert request.headers["User-Agent"] == "Thesis tests developer@example.org"
        return httpx.Response(403, text="sensitive unexpected body")

    with pytest.raises(client.SourceFailure, match="denied"):
        client.fetch_bundle(CIK, transport=httpx.MockTransport(handler))
    assert len(requests) == 1


def test_no_contact_identity_means_no_network(monkeypatch):
    monkeypatch.setattr(client, "settings", lambda: {"SEC_USER_AGENT": ""})
    with pytest.raises(ValueError, match="SEC_USER_AGENT"):
        client.fetch_bundle(CIK)


def test_equivalent_reordered_and_unused_facts_make_no_review_noise(owner):
    iid = add_company("MSFT")["instrument_id"]
    data = bundle()
    apply(iid, data)
    p = payload().model_dump()
    p["instrument_id"] = iid
    service.save_idea(owner, SaveIdea(**p))
    drain(owner)
    before = service.state(owner, iid)
    values = data["companyfacts"]["facts"]["us-gaap"][REVENUE[0]]["units"]["USD"]
    values.reverse()
    apply(iid, data)
    drain(owner)
    ytd = deepcopy(values[-1])
    ytd.update(start="2025-01-01", val=400)
    values.append(ytd)
    apply(iid, data)
    drain(owner)
    after = service.state(owner, iid)
    assert (
        before["documents"] == after["documents"]
        and before["versions"] == after["versions"]
    )
    assert after["changes"] == []
    with transaction() as conn:
        assert (
            one(
                conn,
                "SELECT count(*) n FROM source_payloads WHERE instrument_id=%s",
                (iid,),
            )["n"]
            == 3
        )


def test_stale_filing_response_cannot_move_active_period_backwards(owner):
    iid = add_company("MSFT")["instrument_id"]
    apply(iid, bundle())
    before = service.state(owner, iid)
    older = bundle(annual=True, accession="0000789019-24-000001")
    recent = older["submissions"]["filings"]["recent"]
    recent.update(
        reportDate=["2024-09-30"],
        filingDate=["2024-10-30"],
        acceptanceDateTime=["2024-10-30T20:00:00Z"],
    )
    with pytest.raises(ValueError, match="refresh failed"):
        refresh(iid, fetcher=lambda _: older)
    after = service.state(owner, iid)
    assert after["demo"]["period"] == before["demo"]["period"]
    assert after["documents"] == before["documents"]
    assert after["source_checks"][0]["state"] == "failed"


def test_transport_preserves_fractional_numeric_lexemes(owner, monkeypatch):
    import json

    data = bundle()
    literal = "1234567890123456.12345678901234567890123456789"
    data["companyfacts"]["facts"]["us-gaap"][REVENUE[0]]["units"]["USD"][0][
        "val"
    ] = "__DECIMAL__"
    monkeypatch.setattr(
        client, "identity", lambda: "Thesis tests developer@example.org"
    )
    monkeypatch.setattr(client, "reserve_request", lambda: None)

    def handler(request):
        result = (
            data["submissions"]
            if "/submissions/" in request.url.path
            else data["companyfacts"]
        )
        return httpx.Response(
            200, text=json.dumps(result).replace('"__DECIMAL__"', literal)
        )

    response = client.fetch_bundle(CIK, transport=httpx.MockTransport(handler))
    fact = response["companyfacts"]["facts"]["us-gaap"][REVENUE[0]]["units"]["USD"][0]
    assert fact["val"] == literal
    result = parsed(response)
    assert result["calculations"][0]["inputs"][0]["value"] == literal
    iid = add_company("MSFT")["instrument_id"]
    apply(iid, response)
    assert (
        service.state(owner, iid)["filing_calculations"][0]["calculations"][0][
            "inputs"
        ][0]["value"]
        == literal
    )


def test_coverage_ages_and_interrupted_request_becomes_visible_without_http(owner):
    from thesis.research.sec.service import tick_coverage

    iid = add_company("MSFT")["instrument_id"]
    apply(iid, bundle())
    future = datetime.now(timezone.utc) + timedelta(hours=25)
    tick_coverage(future)
    assert service.state(owner, iid)["source_checks"][0]["state"] == "stale"
    with transaction(source=True) as conn:
        conn.execute(
            "UPDATE sec_refresh_state SET lease_until=%s WHERE instrument_id=%s",
            (future - timedelta(seconds=1), iid),
        )
    tick_coverage(future)
    data = service.state(owner, iid)
    assert data["source_checks"][0]["state"] == "failed"
    assert "interrupted" in data["source_checks"][0]["error"]


def test_collector_role_cannot_read_private_ideas_or_model_keys(owner):
    import psycopg

    with transaction(source=True) as conn:
        assert one(
            conn,
            "SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user",
        ) == dict(rolsuper=False, rolbypassrls=False)
    for table in ("theses", "model_calls", "model_budget"):
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            with transaction(source=True) as conn:
                conn.execute("SELECT * FROM " + table)


def test_equivalent_number_spellings_do_not_create_updates(owner):
    iid = add_company("MSFT")["instrument_id"]
    data = bundle()
    apply(iid, data)
    p = payload().model_dump()
    p["instrument_id"] = iid
    service.save_idea(owner, SaveIdea(**p))
    drain(owner)
    before = service.state(owner, iid)
    for value in ("120.0", "1.20E2"):
        data["companyfacts"]["facts"]["us-gaap"][REVENUE[0]]["units"]["USD"][0][
            "val"
        ] = value
        apply(iid, data)
        drain(owner)
        after = service.state(owner, iid)
        assert (
            after["documents"] == before["documents"]
            and after["versions"] == before["versions"]
        )
        assert after["changes"] == []


def test_expired_attempt_cannot_commit_its_late_network_result(owner):
    from thesis.research.sec.service import tick_coverage

    iid = add_company("MSFT")["instrument_id"]

    def delayed(cik):
        with transaction(source=True) as conn:
            conn.execute(
                "UPDATE sec_refresh_state SET lease_until=%s WHERE instrument_id=%s",
                (datetime.now(timezone.utc) - timedelta(seconds=1), iid),
            )
        tick_coverage()
        return bundle()

    with pytest.raises(ValueError, match="refresh failed"):
        refresh(iid, fetcher=delayed)
    state = service.state(owner, iid)
    assert not state["documents"]
    assert "interrupted" in state["source_checks"][0]["error"]


def test_completion_timestamp_is_taken_after_collection_lock(owner, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event, current_thread
    import thesis.research.sec.service as sec_service

    iid = add_company("MSFT")["instrument_id"]
    apply(iid, bundle())
    fetching = Event()
    release_response = Event()
    waiting_for_lock = Event()
    original_lock = sec_service.collection_lock

    def lock(conn):
        if (
            current_thread().name.startswith("ThreadPoolExecutor")
            and release_response.is_set()
        ):
            waiting_for_lock.set()
        original_lock(conn)

    monkeypatch.setattr(sec_service, "collection_lock", lock)

    def fetcher(cik):
        fetching.set()
        assert release_response.wait(5)
        return bundle()

    with ThreadPoolExecutor(1) as pool:
        future = pool.submit(refresh, iid, fetcher=fetcher)
        assert fetching.wait(5)
        with transaction(source=True) as conn:
            original_lock(conn)
            release_response.set()
            assert waiting_for_lock.wait(5)
            # A local age tick can progress state while a completed HTTP response
            # waits for this lock. Its later commit must take a newer timestamp.
            conn.execute(
                "UPDATE instrument_state SET cutoff=%s WHERE instrument_id=%s",
                (datetime.now(timezone.utc), iid),
            )
        assert future.result(timeout=5)["changed"] is False
    assert service.state(owner, iid)["source_checks"][0]["state"] == "fresh"


def test_corrected_source_can_return_to_an_earlier_value_without_rewriting_history(
    owner,
):
    iid = add_company("MSFT")["instrument_id"]
    original = bundle()
    apply(iid, original)
    p = payload().model_dump()
    p["instrument_id"] = iid
    service.save_idea(owner, SaveIdea(**p))
    drain(owner)
    original_id = service.state(owner, iid)["active_document_id"]
    changed = bundle(revenue=110)
    apply(iid, changed)
    drain(owner)
    changed_data = service.state(owner, iid)
    assert changed_data["fundamentals"][0]["value"] == 10
    assert apply(iid, original)["changed"] is True
    drain(owner)
    restored = service.state(owner, iid)
    assert restored["active_document_id"] == original_id
    assert restored["fundamentals"][0]["value"] == 20
    assert len(restored["documents"]) == 2
    assert len(restored["versions"][0]["evaluations"]) == 3
    assert len(restored["changes"]) == 2
    assert (
        restored["versions"][0]["evaluations"][1]["id"]
        == changed_data["versions"][0]["evaluations"][0]["id"]
    )
    assert apply(iid, original)["changed"] is False
