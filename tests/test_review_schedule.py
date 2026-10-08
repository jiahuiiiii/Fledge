"""Scheduled local reviews preserve membership, ownership and current source access."""

from datetime import datetime, timedelta, timezone, date
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import pytest
from psycopg.types.json import Jsonb
from thesis.monitoring import review_schedule as R
from thesis import review_digest, service
from thesis.db import transaction, one, rows
from thesis.providers import ledger
from thesis.research import idea_alerts as A
from test_idea_alerts import setup, provider


def due_config(owner):
    now = datetime.now(timezone.utc)
    due = (now + timedelta(minutes=2)).replace(second=0, microsecond=0)
    R.configure(
        owner,
        True,
        due.weekday(),
        due.hour * 60 + due.minute,
        "UTC",
        now=due - timedelta(days=1),
    )
    return due


def saved(owner):
    iid, _, reading = setup(owner)
    alert = A.generate(owner, iid, reading["id"], transport=provider("risk"))
    due = due_config(owner)
    assert R.run_once(owner, now=due + timedelta(seconds=1))
    item = R.history(owner)["items"][0]
    return iid, alert, item, due


def test_defaults_off_configuration_idempotence_and_changes_reset_future(owner):
    with transaction(owner) as c:
        assert not R.settings(c, owner)["enabled"]
    assert not R.run_once(owner)
    now = datetime(2026, 10, 3, 0, tzinfo=timezone.utc)
    first = R.configure(owner, True, 0, 420, "Asia/Singapore", now=now)
    assert first["next_due_at"] == datetime(2026, 10, 4, 23, tzinfo=timezone.utc)
    assert (
        R.configure(owner, True, 0, 420, "Asia/Singapore", now=now + timedelta(days=1))
        == first
    )
    changed = R.configure(owner, True, 1, 480, "Asia/Singapore", now=now)
    assert changed["revision"] == 2 and changed["next_due_at"] > now
    stopped = R.configure(owner, False, 1, 480, "Asia/Singapore", now=now)
    assert not stopped["enabled"] and stopped["next_due_at"] is None
    assert not R.run_once(owner, now=now + timedelta(days=30))


@pytest.mark.parametrize(
    "change",
    [
        dict(enabled=1),
        dict(weekday=True),
        dict(weekday=7),
        dict(minute_of_day=-1),
        dict(minute_of_day=1440),
        dict(time_zone="../UTC"),
        dict(time_zone="not/a-zone"),
    ],
)
def test_invalid_settings_rejected_without_enrollment(owner, change):
    args = dict(enabled=True, weekday=0, minute_of_day=420, time_zone="UTC") | change
    with pytest.raises(ValueError):
        R.configure(owner, **args)
    with transaction(owner) as c:
        assert not one(c, "SELECT 1 FROM review_schedules WHERE owner_id=%s", (owner,))


def test_dst_gap_fold_and_calendar_week_boundaries():
    tz = R.zone("America/New_York")
    assert R.occurrence(date(2026, 3, 8), 150, tz) == datetime(
        2026, 3, 8, 7, tzinfo=timezone.utc
    )
    assert R.occurrence(date(2026, 11, 1), 90, tz) == datetime(
        2026, 11, 1, 5, 30, tzinfo=timezone.utc
    )
    cfg = dict(weekday=6, minute_of_day=420, time_zone="America/New_York")
    start, end, nxt = R.boundaries(cfg, datetime(2026, 3, 8, 12, tzinfo=timezone.utc))
    assert (end - start) == timedelta(hours=167) and (nxt - end) == timedelta(days=7)


def test_ready_review_is_atomic_deduplicated_and_makes_no_paid_calls(
    owner, monkeypatch
):
    iid, _, reading = setup(owner)
    A.generate(owner, iid, reading["id"], transport=provider("risk"))
    before = ledger.snapshot()
    monkeypatch.setattr(
        ledger, "execute", lambda *a, **k: pytest.fail("Scheduled review called AI")
    )
    due = due_config(owner)
    assert not R.run_once(owner, now=due - timedelta(microseconds=1))
    assert R.run_once(owner, now=due)
    assert not R.run_once(owner, now=due + timedelta(minutes=5))
    result = R.history(owner)
    assert len(result["items"]) == 1 and result["settings"]["unseen_count"] == 1
    assert result["items"][0]["total"] == 1
    assert ledger.snapshot() == before


def test_late_restart_saves_latest_week_once_and_preserves_older_unread(owner):
    iid, _, reading = setup(owner)
    A.generate(owner, iid, reading["id"], transport=provider("risk"))
    due = due_config(owner)
    late = due + timedelta(days=22)
    assert R.run_once(owner, now=late)
    result = R.history(owner)
    item = result["items"][0]
    assert item["skipped_occurrences"] == 3 and item["scheduled_at"] == due + timedelta(
        days=21
    )
    report = R.read(owner, item["id"])
    assert report["total"] == 0 and report["totals"]["older_pending_count"] == 1
    assert not R.run_once(owner, now=late)


def test_snapshot_survives_edits_and_seen_does_not_acknowledge_alert(owner):
    iid, alert, item, due = saved(owner)
    before = R.read(owner, item["id"])
    from thesis.models import SaveIdea

    service.save_idea(
        owner,
        SaveIdea(
            instrument_id=iid,
            expected_revision=1,
            question="A different research question",
            reasoning="A changed belief for this fixture.",
            status="draft",
            conditions=[],
        ),
    )
    A.review(owner, alert["id"], "unresolved")
    R.mark_seen(owner, item["id"])
    R.mark_seen(owner, item["id"])
    after = R.read(owner, item["id"])
    assert (
        before["totals"] == after["totals"]
        and after["records"][0]["review_action"] is None
    )
    assert after["records"][0]["detail"]["review_action"] is None
    assert before["companies"] == after["companies"]
    assert after["records"][0]["detail"]["revision"] == 1
    assert R.history(owner)["settings"]["unseen_count"] == 0
    with transaction(owner) as c:
        assert (
            one(
                c,
                "SELECT count(*) n FROM scheduled_review_seen WHERE owner_id=%s",
                (owner,),
            )["n"]
            == 1
        )
        assert A.list_for(c, owner)[0]["review_action"] == "unresolved"
    filename, html = R.download(owner, item["id"])
    assert (
        "Saved membership" in html and "Source cutoff" in html and "<script" not in html
    )


def test_owner_isolation_and_append_only_reports(owner):
    _, _, item, _ = saved(owner)
    other = str(uuid4())
    assert not R.history(other)["items"]
    with pytest.raises(service.Missing):
        R.read(other, item["id"])
    with pytest.raises(service.Missing):
        R.mark_seen(other, item["id"])
    with pytest.raises(service.Missing):
        R.download(other, item["id"])
    with pytest.raises(Exception):
        with transaction(owner) as c:
            c.execute(
                "UPDATE scheduled_reviews SET skipped_occurrences=9 WHERE id=%s",
                (item["id"],),
            )
    with transaction(owner) as c:
        assert (
            one(
                c,
                "SELECT skipped_occurrences FROM scheduled_reviews WHERE id=%s",
                (item["id"],),
            )["skipped_occurrences"]
            == 0
        )


def test_source_withdrawal_rechecks_saved_report_and_export(owner):
    _, _, item, _ = saved(owner)
    with transaction(admin=True) as c:
        constraint = one(
            c,
            "SELECT pg_get_constraintdef(oid) definition FROM pg_constraint WHERE conrelid='sources'::regclass AND conname='sources_entitlement_check'",
        )
        values = rows(c, "SELECT id,entitlement FROM sources")
        c.execute(
            "ALTER TABLE sources DROP CONSTRAINT IF EXISTS sources_entitlement_check"
        )
        c.execute("UPDATE sources SET entitlement='withdrawn'")
    try:
        report = R.read(owner, item["id"])
        assert all(r["detail"]["withheld"] for r in report["records"])
        html = R.download(owner, item["id"])[1]
        assert (
            "The supplied report may challenge" not in html
            and "Source access changed" in html
        )
    finally:
        from psycopg import sql

        with transaction(admin=True) as c:
            for v in values:
                c.execute(
                    "UPDATE sources SET entitlement=%s WHERE id=%s",
                    (v["entitlement"], v["id"]),
                )
            if constraint:
                c.execute(
                    sql.SQL(
                        "ALTER TABLE sources ADD CONSTRAINT sources_entitlement_check {}"
                    ).format(sql.SQL(constraint["definition"]))
                )


def test_generation_failure_rolls_back_and_retries_only_after_backoff(owner):
    setup(owner)
    due = due_config(owner)

    def fail(*a, **k):
        raise ValueError("This report exceeds 1,000 records.")

    assert R.run_once(owner, now=due, prepare=fail)
    h = R.history(owner)
    assert not h["items"] and h["settings"]["error"] == "too_many_records"
    assert h["settings"]["next_due_at"] == due
    assert not R.run_once(
        owner,
        now=due + timedelta(minutes=59),
        prepare=lambda *a, **k: pytest.fail("Retried too soon"),
    )
    assert R.run_once(owner, now=due + timedelta(hours=1))
    h = R.history(owner)
    assert len(h["items"]) == 1 and h["settings"]["error"] is None


def test_competing_local_workers_create_one_review(owner):
    setup(owner)
    due = due_config(owner)
    entered = Event()
    release = Event()

    def hold(*args, **kwargs):
        entered.set()
        assert release.wait(5)
        return review_digest.prepare(*args, **kwargs)

    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(R.run_once, owner, now=due, prepare=hold)
        assert entered.wait(5)
        assert not R.run_once(owner, now=due)
        release.set()
        assert first.result(timeout=5)
    assert len(R.history(owner)["items"]) == 1


def test_saved_membership_rejects_foreign_or_fabricated_event(owner):
    _, _, item, _ = saved(owner)
    with transaction(owner) as c:
        row = one(c, "SELECT * FROM scheduled_reviews WHERE id=%s", (item["id"],))
    row["manifest"]["records"][0]["id"] = str(uuid4())
    with pytest.raises(Exception):
        with transaction(owner) as c:
            c.execute(
                "INSERT INTO scheduled_reviews VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    uuid4(),
                    owner,
                    99,
                    row["scheduled_at"],
                    row["generated_at"],
                    "UTC",
                    0,
                    Jsonb(row["manifest"]),
                ),
            )


def test_routes_require_session_local_intent_and_valid_fields(owner):
    from fastapi.testclient import TestClient
    from thesis.app import app

    client = TestClient(app)
    assert client.get("/api/v1/scheduled-reviews").status_code == 401
    client.get("/api/v1/session")
    assert client.get("/api/v1/scheduled-reviews").status_code == 200
    assert client.post("/api/v1/review-schedule", json={}).status_code == 403
    response = client.post(
        "/api/v1/review-schedule",
        headers={"X-Thesis-Request": "local-ui"},
        json=dict(enabled="yes", weekday=0, minute_of_day=420, time_zone="UTC"),
    )
    assert response.status_code == 422


def test_stop_serializes_with_generation_and_prevents_future_reviews(owner):
    setup(owner)
    due = due_config(owner)
    entered, release, stopping = Event(), Event(), Event()

    def hold(*args, **kwargs):
        entered.set()
        assert release.wait(5)
        return review_digest.prepare(*args, **kwargs)

    def stop():
        stopping.set()
        return R.configure(
            owner, False, due.weekday(), due.hour * 60 + due.minute, "UTC", now=due
        )

    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(R.run_once, owner, now=due, prepare=hold)
        assert entered.wait(5)
        second = pool.submit(stop)
        assert stopping.wait(5)
        release.set()
        assert first.result(timeout=5)
        assert not second.result(timeout=5)["enabled"]
    assert len(R.history(owner)["items"]) == 1
    assert not R.run_once(owner, now=due + timedelta(days=7))


def test_half_open_week_does_not_repeat_boundary_event(owner):
    _, _, item, _ = saved(owner)
    report = R.read(owner, item["id"])
    boundary = review_digest.clock(report["records"][0]["created_at"])
    first = review_digest.prepare(
        owner, cutoff=boundary, window_start=boundary - timedelta(days=7), now=boundary
    )
    following = review_digest.prepare(
        owner,
        cutoff=boundary + timedelta(days=7),
        window_start=boundary,
        now=boundary + timedelta(days=7),
    )
    assert first["total"] == 1 and following["total"] == 0
    assert following["totals"]["older_pending_count"] == 1


def test_saved_pages_export_and_history_keep_all_members(owner):
    from thesis.models import SaveIdea

    iid, _, reading = setup(owner)
    for i in range(23):
        if i:
            service.save_idea(
                owner,
                SaveIdea(
                    instrument_id=iid,
                    expected_revision=i,
                    question=f"Case {i}",
                    reasoning=f"Case {i} may support margins.",
                    status="draft",
                    conditions=[],
                ),
            )
        A.generate(owner, iid, reading["id"], transport=provider("risk"))
    due = due_config(owner)
    assert R.run_once(owner, now=due)
    rid = R.history(owner)["items"][0]["id"]
    assert len(R.read(owner, rid)["records"]) == 20
    assert len(R.read(owner, rid, page=1)["records"]) == 3
    assert R.read(owner, rid, page=1)["total"] == 23
    assert R.download(owner, rid)[1].count("<section>") == 23
    for i in range(1, 22):
        assert R.run_once(owner, now=due + timedelta(days=i * 7))
    history = R.history(owner)
    assert len(history["items"]) == 20
    older = R.history(owner, before=history["next_before"])
    assert len(older["items"]) == 2 and older["next_before"] is None
    assert str(older["items"][-1]["id"]) == str(rid)


@pytest.mark.parametrize("invalid", ["duplicate", "no_start"])
def test_invalid_manifest_bounds_and_duplicates_rejected(owner, invalid):
    _, _, item, _ = saved(owner)
    with transaction(owner) as c:
        row = one(c, "SELECT * FROM scheduled_reviews WHERE id=%s", (item["id"],))
    m = row["manifest"]
    if invalid == "duplicate":
        m["records"] *= 2
        m["total"] = 2
    else:
        del m["window_start"]
    with pytest.raises(Exception):
        with transaction(owner) as c:
            c.execute(
                "INSERT INTO scheduled_reviews VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    uuid4(),
                    owner,
                    99,
                    row["scheduled_at"],
                    row["generated_at"],
                    "UTC",
                    0,
                    Jsonb(m),
                ),
            )
