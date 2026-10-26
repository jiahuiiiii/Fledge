"""Saved filing figures (migration 072); authored filings, mocked AI, disposable database only."""
from uuid import uuid4

import psycopg
import pytest

from thesis.db import one, transaction
from thesis.research.sec import disclosures, filing_figures as FF, financial_depth as D, financial_recovery as R
from thesis.research.sec import income_flow as IF, segment_revenue as SR
from thesis.research.sec.service import add_company
from test_disclosures import disclosure_scope, metadata, reset_attempt  # noqa: F401  (fixture)
from test_financial_recovery import response, setup, source
from test_model_budget import clean_model_ledger  # noqa: F401  (fixture)
from test_sec_fundamentals import apply, bundle


def read(owner, iid):
    with transaction(owner, consistent=True) as c:
        return D.present(c, iid)


def saved(owner, iid):
    with transaction(owner) as c:
        return one(c, "SELECT count(*) n FROM filing_figures WHERE instrument_id=%s", (iid,))["n"]


@pytest.fixture
def builds(monkeypatch):
    calls, real = [], D.build
    monkeypatch.setattr(D, "build", lambda c, i: calls.append(i) or real(c, i))
    return calls


def test_saved_figures_equal_a_fresh_build_and_are_reused(owner, disclosure_scope, builds):
    iid, _ = setup(owner)
    first = read(owner, iid)
    assert first["status"] == "available" and builds == [iid] and saved(owner, iid) == 1
    again = read(owner, iid)
    assert builds == [iid] and again == first
    with transaction(owner, consistent=True) as c:
        assert D.build(c, iid) == again


def change_payload(owner, iid, monkeypatch):
    apply(iid, bundle(annual=True, revenue=70_000_000_000))


def change_document(owner, iid, monkeypatch):
    reset_attempt(iid)
    disclosures.refresh(iid, submissions=metadata(), fetcher=lambda _: source().replace(b">40<", b">41<"))


def change_access(owner, iid, monkeypatch):
    with transaction(admin=True) as c:
        c.execute("UPDATE sources SET entitlement='fictional' WHERE id='sec-disclosures'")


def change_reading(owner, iid, monkeypatch):
    with transaction(owner, consistent=True) as c:
        plan = R.present(c, iid)
    R.generate(owner, iid, plan["document"]["id"], plan["plan_id"], transport=response)


def change_review(owner, iid, monkeypatch):
    change_reading(owner, iid, monkeypatch)
    read(owner, iid)  # the new reading's figures are saved first
    with transaction(owner) as c:
        reading = one(c, "SELECT id FROM financial_recovery_readings WHERE instrument_id=%s", (iid,))
    R.review(owner, iid, str(reading["id"]), ["cost"], None)


def change_version(owner, iid, monkeypatch):
    monkeypatch.setattr(FF, "VERSION", "filing-figures-test")


def change_method(owner, iid, monkeypatch):
    monkeypatch.setattr(D, "METHOD", "sec-financial-depth-test")


@pytest.mark.parametrize("change", [change_payload, change_document, change_access, change_reading,
                                    change_review, change_version, change_method])
def test_every_input_change_rebuilds(owner, disclosure_scope, clean_model_ledger, builds, monkeypatch, change):
    iid, _ = setup(owner)
    before = read(owner, iid)
    rows_before = saved(owner, iid)
    change(owner, iid, monkeypatch)
    builds.clear()
    after = read(owner, iid)
    assert builds == [iid], "a changed input reused saved figures"
    with transaction(owner, consistent=True) as c:
        assert after == D.build(c, iid)
    if after["status"] == "available":
        assert saved(owner, iid) > rows_before  # change_review saves twice
    builds.clear()
    assert read(owner, iid) == after and builds == ([] if after["status"] == "available" else [iid])
    assert before["status"] == "available"


def test_reviewed_figures_stay_with_their_account(owner, disclosure_scope, clean_model_ledger, builds):
    iid, _ = setup(owner)
    change_review(owner, iid, None)
    mine = read(owner, iid)
    with transaction(admin=True) as c:
        other = str(uuid4())
        c.execute("INSERT INTO accounts VALUES(%s,%s)", (other, "Other account"))
    assert saved(other, iid) == 0
    builds.clear()
    theirs = read(other, iid)
    assert builds == [iid] and saved(other, iid) == 1
    assert mine["recovery_basis"] != theirs["recovery_basis"]


def test_reads_without_an_account_are_never_saved(owner, disclosure_scope, builds):
    iid, _ = setup(owner)
    assert read(None, iid)["status"] == "available" and read(None, iid)["status"] == "available"
    assert builds == [iid, iid] and saved(owner, iid) == 0


def test_unfinished_figures_are_not_saved_and_saved_rows_are_immutable(owner, disclosure_scope):
    empty = add_company("MSFT")["instrument_id"]
    assert read(owner, empty)["status"] == "empty" and saved(owner, empty) == 0
    iid, _ = setup(owner)
    read(owner, iid)
    with pytest.raises(psycopg.Error):
        with transaction(owner) as c:
            c.execute("UPDATE filing_figures SET depth='{}' WHERE instrument_id=%s", (iid,))


def test_dates_and_decimals_anywhere_read_back_equal():
    from datetime import date, datetime, timezone
    from decimal import Decimal

    value = dict(checked_at=datetime(2025, 9, 30, 12, tzinfo=timezone.utc),
                 trailing=[dict(end=date(2025, 9, 30), value=Decimal("64000000000.5"),
                                inputs=[dict(filed=datetime(2025, 10, 30, tzinfo=timezone.utc), text="x")])],
                 note=None, flag=True)
    import json
    assert FF.decode(json.loads(json.dumps(FF.encode(value)))) == value


KINDS = {"income_flow": (IF, lambda c, i: IF.present(c, i)), "segment_revenue": (SR, lambda c, i: SR.present(c, i))}


@pytest.fixture(params=sorted(KINDS))
def kind(request, monkeypatch):
    module, present = KINDS[request.param]
    calls, real = [], module.build
    monkeypatch.setattr(module, "build", lambda c, i, *a: calls.append(i) or real(c, i, *a))
    return request.param, module, present, calls


def read_kind(owner, iid, present):
    with transaction(owner, consistent=True) as c:
        return present(c, iid)


def test_income_flow_and_segments_are_saved_and_reused(owner, disclosure_scope, kind):
    name, module, present, calls = kind
    iid, _ = setup(owner)
    first = read_kind(owner, iid, present)
    assert calls == [iid]
    again = read_kind(owner, iid, present)
    assert calls == [iid] and again == first
    with transaction(owner, consistent=True) as c:
        assert module.build(c, iid) == again


@pytest.mark.parametrize("change", [change_payload, change_document, change_access, change_reading,
                                    change_review, change_version])
def test_income_flow_and_segments_rebuild_on_every_input_change(owner, disclosure_scope, clean_model_ledger,
                                                                 kind, monkeypatch, change):
    name, module, present, calls = kind
    iid, _ = setup(owner)
    read_kind(owner, iid, present)
    change(owner, iid, monkeypatch)
    calls.clear()
    after = read_kind(owner, iid, present)
    if not calls:
        # Withdrawn access answers before the saved table: nothing reused.
        assert change is change_access and after["status"] == "unavailable"
        return
    assert calls == [iid], f"{name}: a changed input reused a saved result"
    with transaction(owner, consistent=True) as c:
        assert after == module.build(c, iid)


def test_each_kind_has_its_own_saved_row(owner, disclosure_scope):
    iid, _ = setup(owner)
    read(owner, iid)
    for _, present in KINDS.values():
        read_kind(owner, iid, present)
    with transaction(owner) as c:
        assert one(c, "SELECT count(DISTINCT basis) n FROM filing_figures WHERE instrument_id=%s", (iid,))["n"] >= 2


def test_recovery_basis_does_not_depend_on_fact_order(owner, disclosure_scope):
    iid, _ = setup(owner)
    facts = [dict(concept="SellingGeneralAndAdministrativeExpense", value=str(n), start="2024-01-01", end=f"2024-0{n}-28")
             for n in range(1, 6)]
    with transaction(owner) as c:
        one_way = R.apply_reviewed(c, iid, {"_original_facts": {"X": facts}, "_recovery_basis": "b"}, [])
        other_way = R.apply_reviewed(c, iid, {"_original_facts": {"X": facts[::-1]}, "_recovery_basis": "b"}, [])
    assert one_way["_recovery_basis"] == other_way["_recovery_basis"]
