"""Daily acquisition -> real SEC contract -> numerical alerts; no live HTTP/AI."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import json
import os
from pathlib import Path
import pytest
import psycopg
from fastapi.testclient import TestClient
from thesis import service, review_digest
from thesis.db import transaction, one, rows
from thesis.monitoring import filing_watch as watch
from thesis.research.sec import service as sec
from thesis.models import SaveIdea
from thesis.providers import ledger
from test_sec_fundamentals import bundle, apply
from test_integration import payload, drain


@pytest.fixture
def company(owner, monkeypatch):
    monkeypatch.setattr(sec.client, "identity", lambda: "Authored test identity")
    return sec.add_company("MSFT")["instrument_id"]


def due(owner, iid, *, reset_source=True):
    with transaction(admin=True) as c:
        c.execute(
            "UPDATE filing_watches SET next_check_at=now()-interval '7 days' WHERE owner_id=%s AND instrument_id=%s",
            (owner, iid),
        )
        if reset_source:
            c.execute(
                "UPDATE sec_refresh_state SET last_attempt_at=NULL WHERE instrument_id=%s",
                (iid,),
            )


def run(owner, data=None):
    return watch.run_once(
        owner,
        refresher=lambda iid: sec.refresh(iid, fetcher=lambda _: data or bundle()),
    )


def test_default_off_immediate_enable_idempotent_and_no_catchup_storm(owner, company):
    assert not watch.run_once(
        owner, refresher=lambda _: pytest.fail("Off watch fetched")
    )
    before = ledger.snapshot()
    first = watch.configure(owner, company, True)
    assert first == watch.configure(owner, company, True)
    due(owner, company)
    assert run(owner)
    with transaction(owner) as c:
        active = watch.settings(c, owner, company)
    assert (
        timedelta(hours=23)
        < active["next_check_at"] - watch.utcnow()
        <= timedelta(hours=24)
    )
    assert not run(owner)
    latest = watch.history(owner, company)["items"][0]
    assert latest["outcome"] == "changed" and latest["filing"]["form"] == "10-Q"
    assert latest["started_at"] - latest["scheduled_at"] > timedelta(days=6)
    assert ledger.snapshot() == before
    watch.configure(owner, company, False)
    with transaction(owner) as c:
        assert watch.settings(c, owner, company)["next_check_at"] is None


def test_changed_inputs_reassess_approved_idea_unchanged_does_not_duplicate(
    owner, company
):
    apply(company, bundle())
    p = payload().model_dump()
    p["instrument_id"] = company
    saved = service.save_idea(owner, SaveIdea(**p))
    drain(owner)
    original = service.state(owner, company)["versions"][0]["evaluations"][0]
    assert original["outcome"] == "met"
    watch.configure(owner, company, True)
    assert run(owner, bundle(revenue=110))
    drain(owner)
    current = service.state(owner, company)
    assert current["versions"][0]["evaluations"][0]["outcome"] == "not_met"
    changes = current["changes"]
    assert len(changes) == 1 and changes[0]["details"]["affected_conditions"]
    count = len(current["versions"][0]["evaluations"])
    due(owner, company)
    assert run(owner, bundle(revenue=110))
    drain(owner)
    again = service.state(owner, company)
    assert len(again["changes"]) == 1
    assert len(again["versions"][0]["evaluations"]) == count
    assert watch.history(owner, company)["items"][0]["outcome"] == "unchanged"
    assert original == next(
        e for e in again["versions"][0]["evaluations"] if e["id"] == original["id"]
    )


def test_shared_cooldown_is_not_success_or_new_http(owner, company):
    sec.refresh(company, fetcher=lambda _: bundle())
    watch.configure(owner, company, True)
    assert watch.run_once(
        owner,
        refresher=lambda iid: sec.refresh(
            iid, fetcher=lambda _: pytest.fail("cooldown fetched")
        ),
    )
    item = watch.history(owner, company)["items"][0]
    assert item["outcome"] == "recent" and item["source_check_id"] is None
    assert "not a successful" in item["message"]


def test_failure_recovery_no_exception_leak_no_retry(owner, company):
    apply(company, bundle())
    watch.configure(owner, company, True)
    calls = []

    def denied(_):
        calls.append(1)
        raise sec.client.SourceFailure(
            "PRIVATE contact/key must not appear", denied=True
        )

    assert watch.run_once(owner, refresher=lambda iid: sec.refresh(iid, fetcher=denied))
    item = watch.history(owner, company)["items"][0]
    assert item["outcome"] == "failed" and "PRIVATE" not in json.dumps(
        item, default=str
    )
    assert not run(owner) and len(calls) == 1
    assert service.state(owner, company)["observations"]
    due(owner, company)
    assert run(owner)
    assert [i["outcome"] for i in watch.history(owner, company)["items"]] == [
        "unchanged",
        "failed",
    ]


def test_one_claim_across_workers(owner, company):
    watch.configure(owner, company, True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = list(pool.map(lambda _: watch.claim(owner), range(2)))
    assert sum(c is not None for c in claims) == 1


def test_late_completion_stays_unconfirmed_and_does_not_retry(
    owner, company, monkeypatch
):
    watch.configure(owner, company, True)

    def late(iid):
        result = sec.refresh(iid, fetcher=lambda _: bundle())
        after = watch.utcnow() + timedelta(minutes=4)
        monkeypatch.setattr(watch, "utcnow", lambda: after)
        return result

    assert watch.run_once(owner, refresher=late)
    item = watch.history(owner, company)["items"][0]
    assert item["outcome"] == "interrupted" and item["source_check_id"] is None
    assert not run(owner)


def test_stop_during_fetch_does_not_restart_watch(owner, company):
    watch.configure(owner, company, True)

    def finish(iid):
        watch.configure(owner, iid, False)
        return sec.refresh(iid, fetcher=lambda _: bundle())

    assert watch.run_once(owner, refresher=finish)
    with transaction(owner) as c:
        setting = watch.settings(c, owner, company)
        assert (
            not setting["enabled"]
            and setting["next_check_at"] is None
            and setting["lease_until"] is None
        )
        assert setting["latest_check"]["outcome"] == "changed"
    assert watch.history(owner, company)["items"][0]["outcome"] == "changed"


def test_old_completion_cannot_clear_new_enrollment_claim(owner, company):
    watch.configure(owner, company, True)
    claimed = []

    def finish(iid):
        watch.configure(owner, iid, False)
        watch.configure(owner, iid, True)
        claimed.append(watch.claim(owner))
        return sec.refresh(iid, fetcher=lambda _: bundle())

    assert watch.run_once(owner, refresher=finish)
    with transaction(owner) as c:
        assert (
            one(
                c, "SELECT claim_token FROM filing_watches WHERE owner_id=%s", (owner,)
            )["claim_token"]
            == claimed[0]["id"]
        )


def test_expired_attempt_visible_readonly_and_recovered_once_even_when_off(
    owner, company, monkeypatch
):
    watch.configure(owner, company, True)
    check = watch.claim(owner)
    watch.configure(owner, company, False)
    later = check["lease_until"] + timedelta(seconds=1)
    monkeypatch.setattr(watch, "utcnow", lambda: later)
    assert watch.history(owner, company)["items"][0]["outcome"] == "interrupted"
    with transaction(owner) as c:
        assert not rows(c, "SELECT * FROM filing_watch_results")
    assert watch.claim(owner) is None and watch.claim(owner) is None
    with transaction(owner) as c:
        assert len(rows(c, "SELECT * FROM filing_watch_results")) == 1


def test_paging_rls_immutable_and_source_membership(owner, company):
    watch.configure(owner, company, True)
    for _ in range(22):
        due(owner, company)
        run(owner)
    page = watch.history(owner, company)
    assert len(page["items"]) == 20
    rest = watch.history(owner, company, page["next_before"])
    assert len(rest["items"]) == 2 and rest["next_before"] is None
    outsider = str(uuid4())
    assert watch.history(outsider, company)["items"] == []
    with pytest.raises(ValueError):
        watch.history(outsider, company, page["next_before"])
    for table in ("filing_watch_checks", "filing_watch_results"):
        with pytest.raises(psycopg.Error):
            with transaction(owner) as c:
                c.execute(f"DELETE FROM {table}")
        with pytest.raises(psycopg.Error):
            with transaction(source=True) as c:
                c.execute(f"SELECT * FROM {table}")
    due(owner, company)
    check = watch.claim(owner)
    old_source = page["items"][0]["source_check_id"]
    with pytest.raises(psycopg.Error):
        with transaction(owner) as c:
            watch._result(
                c, owner, check["id"], "unchanged", watch.utcnow(), old_source
            )


def test_validation_private_api_and_reads_never_fetch(owner, company, monkeypatch):
    from thesis import app as web

    monkeypatch.setattr(web, "OWNER", owner)
    monkeypatch.setattr(sec, "refresh", lambda _: pytest.fail("Read/config fetched"))
    for invalid in ("yes", 1, None):
        with pytest.raises(ValueError):
            watch.configure(owner, company, invalid)
    with pytest.raises(ValueError):
        watch.configure(owner, "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", False)
    client = TestClient(web.app)
    url = f"/api/v1/companies/{company}"
    assert client.get(url + "/filing-checks").status_code == 401
    client.get("/api/v1/session")
    assert client.post(url + "/filing-watch", json={"enabled": True}).status_code == 403
    headers = {"x-thesis-request": "local-ui"}
    assert (
        client.post(
            url + "/filing-watch", headers=headers, json={"enabled": "true"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            url + "/filing-watch",
            headers=headers,
            json={"enabled": True, "owner_id": owner},
        ).status_code
        == 422
    )
    assert (
        client.post(
            url + "/filing-watch", headers=headers, json={"enabled": True}
        ).status_code
        == 200
    )
    assert client.get(url + "/filing-checks").json()["result"]["items"] == []
    assert client.get(f"/api/v1/workspace?instrument_id={company}").json()["result"][
        "filing_watch"
    ]["enabled"]
    with transaction(owner) as c:
        health = review_digest.coverage(
            c, owner, dict(id=company, mode="sec"), watch.utcnow()
        )
    assert health["filing_watch"]["enabled"]


@pytest.mark.parametrize("symbol", ["MSFT", "AAPL", "GOOGL", "NVDA", "AMZN", "META"])
def test_saved_real_company_records_through_scheduled_acquisition(
    owner, monkeypatch, symbol
):
    original = symbol in ("MSFT", "AAPL", "GOOGL")
    location = os.environ.get(
        "THESIS_REAL_CORPUS" if original else "THESIS_EXPANDED_CORPUS"
    )
    if not location:
        pytest.skip("Retained real SEC corpus not configured; never fetch in tests")
    record = json.loads(
        (
            Path(location) / (symbol + (".json" if original else "-bundle.json"))
        ).read_text()
    )
    data = record["payload"] if original else record
    monkeypatch.setattr(sec.client, "identity", lambda: "Authored identity")
    iid = sec.add_company(symbol)["instrument_id"]
    budget = ledger.snapshot()
    watch.configure(owner, iid, True)
    assert run(owner, data)
    first = watch.history(owner, iid)["items"][0]
    assert first["outcome"] == "changed" and first["filing"]["filing_url"].startswith(
        "https://www.sec.gov/Archives/edgar/data/"
    )
    actual = service.state(owner, iid)
    before = actual["fundamentals"]
    assert actual["performance"]["status"] == "available"
    due(owner, iid)
    assert run(owner, data)
    assert watch.history(owner, iid)["items"][0]["outcome"] == "unchanged"
    assert service.state(owner, iid)["fundamentals"] == before
    assert ledger.snapshot() == budget
