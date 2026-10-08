from datetime import datetime, date, timezone, timedelta
from copy import deepcopy
import hashlib
import json
from uuid import uuid4
import pytest
from psycopg.types.json import Jsonb
from pydantic import ValidationError
from thesis import service
from thesis.config import INSTRUMENT
from thesis.db import transaction, one, rows
from thesis.models import SaveIdea
from thesis.monitoring.age import age_state, instant
from thesis.monitoring.evaluator import evaluate
from test_integration import payload, drain
from test_sec_fundamentals import bundle, apply
from thesis.research.sec.service import add_company


def with_limits(*limits, revision=0, instrument=INSTRUMENT):
    p = payload(revision=revision).model_dump()
    p["instrument_id"] = instrument
    for c, limit in zip(p["conditions"], limits):
        c["max_report_age_days"] = limit
    return SaveIdea(**p)


def finish_all(owner):
    while job := service.claim_job(owner):
        service.finish_job(owner, job)


@pytest.mark.parametrize("end", ["2024-02-29", "2025-10-04"])
def test_exact_utc_boundary_and_fractional_second(end):
    c = dict(condition_id=uuid4(), max_report_age_days=30)
    d = date.fromisoformat(end)
    deadline = datetime.combine(
        d + timedelta(days=31), datetime.min.time(), timezone.utc
    )
    assert (
        age_state(c, dict(period_end=d), deadline - timedelta(microseconds=1))["state"]
        == "within_limit"
    )
    assert age_state(c, dict(period_end=d), deadline)["state"] == "expired"
    assert age_state(c, {}, deadline)["state"] == "unavailable"
    assert (
        age_state(dict(c, max_report_age_days=None), {}, deadline)["state"]
        == "no_limit"
    )


@pytest.mark.parametrize("limit", [0, -1, 3651, 1.5, True, "30"])
def test_limits_must_be_bounded_whole_days(limit):
    with pytest.raises(ValidationError):
        with_limits(limit)


def test_expired_value_source_and_fresh_coverage_survive(owner):
    service.save_idea(owner, with_limits(1, 1))
    drain(owner)
    data = service.state(owner)
    e = data["versions"][0]["evaluations"][0]
    assert e["outcome"] == "unknown" and e["freshness"] == "fresh"
    assert all(
        r["observed_value"] is not None and r["observation_id"] for r in e["results"]
    )
    assert all("Too old to assess" in r["explanation"] for r in e["results"])
    assert all(a["state"] == "expired" for a in e["manifest"]["expiry"])
    # Repeated local ticks do not enqueue duplicate assessments.
    drain(owner)
    assert service.state(owner)["versions"] == data["versions"]


def test_downtime_crosses_two_boundaries_in_order_then_new_period_recovers(owner):
    service.save_idea(owner, with_limits(30, 60))
    drain(owner)
    baseline = service.state(owner)["versions"][0]["evaluations"][0]
    # No evaluation worker between ingestion and later source development.
    service.advance(owner, 0)
    service.advance(owner, 1)
    service.queue_current(owner)
    finish_all(owner)
    data = service.state(owner)
    evals = list(reversed(data["versions"][0]["evaluations"]))
    states = [[a["state"] for a in e["manifest"]["expiry"]] for e in evals]
    assert evals[0]["id"] == baseline["id"]
    assert sum(a == "expired" for a in states[1]) == 1
    assert sum(a == "expired" for a in states[2]) == 2
    assert all(a == "within_limit" for a in states[-1])
    assert [e["manifest"]["assessed_at"] for e in evals] == sorted(
        e["manifest"]["assessed_at"] for e in evals
    )
    expiry = [c for c in data["changes"] if c["kind"] == "expiry"]
    assert len(expiry) == 2
    assert all(
        c["summary"] == "Reporting figures passed your age limit" for c in expiry
    )
    assert all(
        a["before"] == a["after"]
        for c in expiry
        for a in c["details"]["affected_conditions"]
    )
    drain(owner)
    assert service.state(owner)["versions"] == data["versions"]


def test_sec_clock_expiry_without_a_new_fetch_and_archive_stops_it(owner):
    iid = add_company("MSFT")["instrument_id"]
    apply(iid, bundle())
    age = (datetime.now(timezone.utc).date() - date(2025, 9, 30)).days
    service.save_idea(owner, with_limits(age + 1, age + 3, instrument=iid))
    drain(owner)
    before = service.state(owner, iid)
    first = before["versions"][0]["evaluations"][0]
    due = min(instant(a["expires_at"]) for a in first["manifest"]["expiry"])
    service.queue_current(owner, now=due)
    finish_all(owner)
    after = service.state(owner, iid)
    assert len([c for c in after["changes"] if c["kind"] == "expiry"]) == 1
    assert after["documents"] == before["documents"]
    assert after["source_checks"] == before["source_checks"]
    assert (
        after["versions"][0]["evaluations"][0]["manifest"]["cutoff"]
        == first["manifest"]["cutoff"]
    )
    service.queue_current(owner, now=due + timedelta(hours=2))
    finish_all(owner)
    assert service.state(owner, iid)["versions"] == after["versions"]
    p = with_limits(age + 1, age + 3, revision=1, instrument=iid).model_dump()
    p["status"] = "archived"
    service.save_idea(owner, SaveIdea(**p))
    service.queue_current(owner, now=due + timedelta(days=10))
    finish_all(owner)
    assert (
        service.state(owner, iid)["versions"][1]["evaluations"]
        == after["versions"][0]["evaluations"]
    )


def test_restatement_same_period_cannot_renew_age_and_clearing_keeps_history(owner):
    service.save_idea(owner, with_limits(1, 1))
    drain(owner)
    for stage in range(4):
        service.advance(owner, stage)
    drain(owner)
    expired = service.state(owner)["versions"][0]["evaluations"][0]
    assert expired["outcome"] == "unknown"
    assert sorted(str(r["observed_value"]) for r in expired["results"]) == ["13", "22"]
    service.save_idea(owner, with_limits(None, None, revision=1))
    drain(owner)
    data = service.state(owner)
    assert data["versions"][0]["evaluations"][0]["outcome"] == "not_met"
    assert data["versions"][1]["evaluations"][0] == expired


def test_recorded_clock_ignores_actual_wall_time(owner):
    service.save_idea(owner, with_limits(30, 30))
    drain(owner)
    before = service.state(owner)
    service.queue_current(owner, now=datetime(2090, 1, 1, tzinfo=timezone.utc))
    finish_all(owner)
    assert service.state(owner)["versions"] == before["versions"]


def test_legacy_pending_manifest_keeps_its_original_no_expiry_contract(owner):
    service.save_idea(owner, with_limits(None, None))
    with transaction(owner) as conn:
        job = one(conn, "SELECT * FROM jobs WHERE owner_id=%s", (owner,))
        legacy = deepcopy(job["manifest"])
        legacy.pop("assessed_at")
        legacy.pop("expiry_method")
        legacy["expiry"] = "quarterly-report-scope"
        legacy["evaluator"] = "thesis-evaluator-2"
        for c in legacy["conditions"]:
            c.pop("max_report_age_days")
        digest = hashlib.sha256(service.canonical(legacy).encode()).hexdigest()
        conn.execute(
            "UPDATE jobs SET manifest=%s,fingerprint=%s WHERE id=%s",
            (Jsonb(legacy), digest, job["id"]),
        )
    finish_all(owner)
    e = service.state(owner)["versions"][0]["evaluations"][0]
    assert (
        e["manifest"] == legacy and e["fingerprint"] == digest and e["outcome"] == "met"
    )


def test_save_and_recorded_advance_share_the_same_source_watermark(owner, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from thesis.research.sec import service as collector

    read, advance_waiting, release = Event(), Event(), Event()
    original_info, original_lock = service.stage_info, collector.collection_lock

    def pause_info(*args, **kwargs):
        info = original_info(*args, **kwargs)
        if not read.is_set():
            read.set()
            assert release.wait(5)
        return info

    def lock(conn):
        if read.is_set():
            advance_waiting.set()
        original_lock(conn)

    monkeypatch.setattr(service, "stage_info", pause_info)
    monkeypatch.setattr(collector, "collection_lock", lock)
    with ThreadPoolExecutor(2) as pool:
        saving = pool.submit(service.save_idea, owner, with_limits(30, 60))
        assert read.wait(5)
        advancing = pool.submit(service.advance, owner, 0)
        assert advance_waiting.wait(5)
        assert not advancing.done()
        release.set()
        saved = saving.result(timeout=5)
        advancing.result(timeout=5)
    with transaction(owner) as conn:
        job = one(conn, "SELECT manifest FROM jobs WHERE id=%s", (saved["job"]["id"],))[
            "manifest"
        ]
        assert instant(job["assessed_at"]) >= instant(job["cutoff"])
        facts = rows(
            conn,
            "SELECT available_at FROM observations WHERE id=ANY(%s::uuid[])",
            (job["observation_ids"],),
        )
        assert all(f["available_at"] <= instant(job["assessed_at"]) for f in facts)
    drain(owner)
