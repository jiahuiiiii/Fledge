"""Local weekly saved reviews: one atomic transaction, no network or model calls."""

from copy import deepcopy
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import json
from psycopg.types.json import Jsonb
from thesis.db import transaction, one, rows
from thesis import review_digest as digest, service

DEFAULT = dict(
    enabled=False,
    revision=0,
    weekday=0,
    minute_of_day=420,
    time_zone="Asia/Singapore",
    next_due_at=None,
    last_attempt_at=None,
    retry_after=None,
    error=None,
)
ERRORS = {
    "too_many_records": "This weekly review exceeds 1,000 updates and was not truncated. Use the current review filters to inspect them. The local scheduler will check again in an hour.",
    "generation_failed": "The saved review could not be completed. No partial review was published. The local scheduler will try again in an hour while the app runs.",
}


def utcnow():
    return datetime.now(timezone.utc)


def zone(name):
    if not isinstance(name, str) or not 1 <= len(name) <= 80:
        raise ValueError("Choose a valid time zone.")
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError(
            "Choose an available IANA time zone, such as Asia/Singapore."
        ) from None


def occurrence(day, minute, tz):
    """First occurrence of repeated local time; first valid minute after a gap."""
    naive = datetime.combine(day, time(minute // 60, minute % 60))
    for shift in range(2 * 24 * 60 + 1):
        wall = naive + timedelta(minutes=shift)
        valid = []
        for fold in (0, 1):
            instant = wall.replace(tzinfo=tz, fold=fold).astimezone(timezone.utc)
            if instant.astimezone(tz).replace(tzinfo=None) == wall:
                valid.append(instant)
        if valid:
            return min(valid)
    raise ValueError("This local schedule time is unavailable.")


def boundaries(config, now):
    now = digest.clock(now)
    tz = zone(config["time_zone"])
    local = now.astimezone(tz)
    day = local.date() - timedelta(days=(local.weekday() - config["weekday"]) % 7)
    end = occurrence(day, config["minute_of_day"], tz)
    if end > now:
        day -= timedelta(days=7)
        end = occurrence(day, config["minute_of_day"], tz)
    start = occurrence(day - timedelta(days=7), config["minute_of_day"], tz)
    following = occurrence(day + timedelta(days=7), config["minute_of_day"], tz)
    return start, end, following


def settings(c, owner):
    value = one(
        c, "SELECT * FROM review_schedules WHERE owner_id=%s", (owner,)
    ) or deepcopy(DEFAULT)
    value.pop("owner_id", None)
    value["error_message"] = ERRORS.get(value["error"])
    value["unseen_count"] = one(
        c,
        "SELECT count(*) n FROM scheduled_reviews r WHERE owner_id=%s AND NOT EXISTS(SELECT 1 FROM scheduled_review_seen s WHERE s.owner_id=r.owner_id AND s.review_id=r.id)",
        (owner,),
    )["n"]
    return value


def configure(owner, enabled, weekday, minute_of_day, time_zone, *, now=None):
    if (
        type(enabled) is not bool
        or type(weekday) is not int
        or not 0 <= weekday <= 6
        or type(minute_of_day) is not int
        or not 0 <= minute_of_day <= 1439
    ):
        raise ValueError("Choose a weekday and a valid local time.")
    zone(time_zone)
    now = digest.clock(now or utcnow())
    config = dict(
        enabled=enabled,
        weekday=weekday,
        minute_of_day=minute_of_day,
        time_zone=time_zone,
    )
    with transaction(owner) as c:
        c.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s,0))",
            (f"review-schedule:{owner}",),
        )
        old = one(
            c, "SELECT * FROM review_schedules WHERE owner_id=%s FOR UPDATE", (owner,)
        )
        if old and all(old[k] == v for k, v in config.items()):
            return settings(c, owner)
        next_due = boundaries(config, now)[2] if enabled else None
        c.execute(
            """INSERT INTO review_schedules(owner_id,enabled,revision,weekday,minute_of_day,time_zone,next_due_at)
        VALUES(%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(owner_id) DO UPDATE SET enabled=excluded.enabled,revision=excluded.revision,weekday=excluded.weekday,minute_of_day=excluded.minute_of_day,time_zone=excluded.time_zone,next_due_at=excluded.next_due_at,retry_after=NULL,error=NULL""",
            (
                owner,
                enabled,
                (old["revision"] + 1 if old else 1),
                weekday,
                minute_of_day,
                time_zone,
                next_due,
            ),
        )
        return settings(c, owner)


def json_value(value):
    def convert(v):
        if isinstance(v, (datetime, date)):
            return v.isoformat()
        if isinstance(v, (UUID, Decimal)):
            return str(v)
        raise TypeError("Unsupported saved-review value")

    return json.loads(json.dumps(value, default=convert))


def run_once(owner, *, now=None, prepare=None):
    now = digest.clock(now or utcnow())
    selected = None
    try:
        with transaction(owner) as c:
            selected = one(
                c,
                """SELECT * FROM review_schedules WHERE owner_id=%s AND enabled AND next_due_at<=%s
            AND (retry_after IS NULL OR retry_after<=%s) FOR UPDATE SKIP LOCKED""",
                (owner, now, now),
            )
            if not selected:
                return False
            start, end, next_due = boundaries(selected, now)
            report = (prepare or digest.prepare)(
                owner, days=7, cutoff=end, window_start=start, now=now, exporting=True
            )
            # Persist membership and generation-time overview, never duplicate the
            # external source wording. Reopen through current access checks.
            manifest = deepcopy(report)
            manifest["records"] = [
                {
                    k: r[k]
                    for k in (
                        "id",
                        "instrument_id",
                        "version_id",
                        "created_at",
                        "kind",
                        "review_action",
                        "review_at",
                    )
                }
                for r in report["records"]
            ]
            skipped = max(
                0,
                (
                    end.astimezone(zone(selected["time_zone"])).date()
                    - selected["next_due_at"]
                    .astimezone(zone(selected["time_zone"]))
                    .date()
                ).days
                // 7,
            )
            c.execute(
                """INSERT INTO scheduled_reviews VALUES(%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    uuid4(),
                    owner,
                    selected["revision"],
                    end,
                    now,
                    selected["time_zone"],
                    skipped,
                    Jsonb(json_value(manifest)),
                ),
            )
            c.execute(
                "UPDATE review_schedules SET next_due_at=%s,last_attempt_at=%s,retry_after=NULL,error=NULL WHERE owner_id=%s",
                (next_due, now, owner),
            )
        return True
    except Exception as exc:
        if selected is None:
            raise
        code = (
            "too_many_records"
            if isinstance(exc, ValueError) and "1,000" in str(exc)
            else "generation_failed"
        )
        with transaction(owner) as c:
            c.execute(
                """UPDATE review_schedules SET last_attempt_at=%s,retry_after=%s,error=%s
            WHERE owner_id=%s AND enabled AND revision=%s AND next_due_at=%s""",
                (
                    now,
                    now + timedelta(hours=1),
                    code,
                    owner,
                    selected["revision"],
                    selected["next_due_at"],
                ),
            )
        return True


def history(owner, *, before=None):
    with transaction(owner, consistent=True) as c:
        args = [owner]
        where = ""
        if before:
            cursor = one(
                c,
                "SELECT scheduled_at,id FROM scheduled_reviews WHERE owner_id=%s AND id=%s",
                (owner, before),
            )
            if not cursor:
                raise service.Missing("This saved-review page is unavailable.")
            where = " AND (r.scheduled_at,r.id)<(%s,%s)"
            args.extend([cursor["scheduled_at"], cursor["id"]])
        result = rows(
            c,
            """SELECT r.id,r.scheduled_at,r.generated_at,r.time_zone,r.skipped_occurrences,
        r.manifest->'totals' totals,(r.manifest->>'total')::int total,s.seen_at
        FROM scheduled_reviews r LEFT JOIN scheduled_review_seen s ON s.owner_id=r.owner_id AND s.review_id=r.id
        WHERE r.owner_id=%s"""
            + where
            + " ORDER BY r.scheduled_at DESC,r.id DESC LIMIT 21",
            args,
        )
        return dict(
            settings=settings(c, owner),
            items=result[:20],
            next_before=str(result[19]["id"]) if len(result) > 20 else None,
        )


def read(owner, rid, *, page=0, exporting=False):
    if type(page) is not int or not 0 <= page <= 100000:
        raise ValueError("Choose a valid saved-review page.")
    with transaction(owner, consistent=True) as c:
        row = one(
            c,
            "SELECT * FROM scheduled_reviews WHERE owner_id=%s AND id=%s",
            (owner, rid),
        )
        if not row:
            raise service.Missing("This saved review is unavailable.")
        report = deepcopy(row["manifest"])
        events = report["records"]
        if not exporting:
            events = events[page * digest.PAGE_SIZE : (page + 1) * digest.PAGE_SIZE]
        for event in events:
            event["owner_id"] = owner
        records = digest.details(c, owner, events)
        for record in records:
            # Freeze acknowledgement display, never acknowledge an underlying
            # alert by opening or marking the weekly reminder seen.
            record["detail"]["review_action"] = record["review_action"]
        report.update(
            records=records,
            page=page,
            saved_review_id=str(row["id"]),
            scheduled_at=row["scheduled_at"],
            schedule_time_zone=row["time_zone"],
            skipped_occurrences=row["skipped_occurrences"],
            access_checked_at=utcnow(),
        )
        report["cutoff"] = digest.clock(report["cutoff"])
        report["limitation"] = (
            "Saved membership, counts, coverage and review status reflect generation time. Current source access is checked whenever this review is opened or downloaded. Open an individual alert in Updates to acknowledge it. No new source or AI request is made; a quiet review is not evidence that nothing important happened."
        )
        return report


def mark_seen(owner, rid):
    with transaction(owner) as c:
        if not one(
            c,
            "SELECT 1 FROM scheduled_reviews WHERE owner_id=%s AND id=%s",
            (owner, rid),
        ):
            raise service.Missing("This saved review is unavailable.")
        c.execute(
            "INSERT INTO scheduled_review_seen(owner_id,review_id) VALUES(%s,%s) ON CONFLICT DO NOTHING",
            (owner, rid),
        )
        return settings(c, owner)


def download(owner, rid):
    return digest.render_report(read(owner, rid, exporting=True))
