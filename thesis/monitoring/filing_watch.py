"""Explicit daily SEC checks; durable claims/history, no model calls or HTTP retry."""

from datetime import datetime, timezone, timedelta
from uuid import uuid4
from thesis.db import transaction, one, rows
from thesis.research.sec import service as sec

INTERVAL = timedelta(hours=24)
LEASE = timedelta(minutes=3)
MESSAGES = {
    "changed": "Supported numerical filing inputs changed. Approved conditions are queued for reassessment; an alert requires a meaningful assessment change.",
    "unchanged": "SEC check completed. Supported numerical inputs are unchanged; other saved financial statement rows may have refreshed.",
    "recent": "No new request: another filing attempt occurred within 15 minutes. Check source coverage for its result; this is not a successful check by this watch.",
    "failed": "Filing check failed. Saved figures remain; no new evidence is confirmed. The next daily check remains scheduled.",
    "interrupted": "This check did not record a completion before its lease expired. Source coverage may have changed; no automatic retry was made.",
}


def utcnow():
    return datetime.now(timezone.utc)


def configure(owner, iid, enabled, *, now=None):
    if type(enabled) is not bool:
        raise ValueError("Choose whether daily filing checks are on or off.")
    if enabled:
        sec.client.identity()
    now = now or utcnow()
    with transaction(owner) as c:
        if not one(c, "SELECT 1 FROM sec_companies WHERE instrument_id=%s", (iid,)):
            raise ValueError("Choose a supported filing company.")
        c.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s,0))",
            (f"filing-watch:{owner}:{iid}",),
        )
        old = one(
            c,
            "SELECT * FROM filing_watches WHERE owner_id=%s AND instrument_id=%s FOR UPDATE",
            (owner, iid),
        )
        if old is None or old["enabled"] != enabled:
            c.execute(
                """INSERT INTO filing_watches(owner_id,instrument_id,enabled,next_check_at)
                VALUES(%s,%s,%s,%s) ON CONFLICT(owner_id,instrument_id) DO UPDATE
                SET enabled=excluded.enabled,next_check_at=excluded.next_check_at,
                    claim_token=NULL,lease_until=NULL""",
                (owner, iid, enabled, now if enabled else None),
            )
        return settings(c, owner, iid)


def settings(c, owner, iid):
    watch = one(
        c,
        "SELECT enabled,next_check_at,lease_until FROM filing_watches WHERE owner_id=%s AND instrument_id=%s",
        (owner, iid),
    )
    watch = watch or dict(enabled=False, next_check_at=None, lease_until=None)
    latest = one(
        c,
        """SELECT a.started_at,a.lease_until,r.completed_at,r.outcome,r.message
        FROM filing_watch_checks a LEFT JOIN filing_watch_results r ON r.check_id=a.id
        WHERE a.owner_id=%s AND a.instrument_id=%s ORDER BY a.started_at DESC,a.id DESC LIMIT 1""",
        (owner, iid),
    )
    if latest and latest["outcome"] is None:
        latest["outcome"] = (
            "interrupted" if utcnow() >= latest["lease_until"] else "running"
        )
        latest["message"] = MESSAGES.get(
            latest["outcome"], "Filing check is in progress. No completed result yet."
        )
    watch["latest_check"] = latest
    return watch


def _result(c, owner, check, outcome, completed, source_id=None):
    c.execute(
        """INSERT INTO filing_watch_results(check_id,owner_id,completed_at,outcome,source_check_id,message)
        VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
        (check, owner, completed, outcome, source_id, MESSAGES[outcome]),
    )


def claim(owner, *, now=None):
    now = now or utcnow()
    with transaction(owner) as c:
        # Close expired journals even if the user has since stopped the watch.
        expired = rows(
            c,
            """SELECT a.id FROM filing_watch_checks a
            WHERE a.owner_id=%s AND a.lease_until<=%s AND NOT EXISTS
            (SELECT 1 FROM filing_watch_results r WHERE r.check_id=a.id)
            ORDER BY a.id""",
            (owner, now),
        )
        for old in expired:
            _result(c, owner, old["id"], "interrupted", now)
        w = one(
            c,
            """SELECT * FROM filing_watches WHERE owner_id=%s AND enabled
            AND next_check_at<=%s AND (lease_until IS NULL OR lease_until<=%s)
            ORDER BY next_check_at,instrument_id FOR UPDATE SKIP LOCKED LIMIT 1""",
            (owner, now, now),
        )
        if not w:
            return None
        check = uuid4()
        lease = now + LEASE
        c.execute(
            """UPDATE filing_watches SET claim_token=%s,lease_until=%s,next_check_at=%s
            WHERE owner_id=%s AND instrument_id=%s""",
            (check, lease, now + INTERVAL, owner, w["instrument_id"]),
        )
        c.execute(
            "INSERT INTO filing_watch_checks VALUES(%s,%s,%s,%s,%s,%s)",
            (check, owner, w["instrument_id"], w["next_check_at"], now, lease),
        )
        return dict(id=check, instrument_id=w["instrument_id"], lease_until=lease)


def run_once(owner, *, refresher=None):
    check = claim(owner)
    if not check:
        return False
    source_id = None
    try:
        result = (refresher or sec.refresh)(str(check["instrument_id"]))
        outcome = "changed" if result["changed"] else "unchanged"
        source_id = result["source_check_id"]
    except sec.RecentlyChecked:
        outcome = "recent"
    except Exception:
        # Provider text/contact identity/exception bodies never enter private history.
        outcome = "failed"
    completed = utcnow()
    if completed >= check["lease_until"]:
        outcome, source_id = "interrupted", None
    with transaction(owner) as c:
        _result(c, owner, check["id"], outcome, completed, source_id)
        # An in-flight shared retrieval may finish after stop. It must not restart
        # this watch or overwrite a later enrollment/claim.
        c.execute(
            """UPDATE filing_watches SET claim_token=NULL,lease_until=NULL
            WHERE owner_id=%s AND instrument_id=%s AND claim_token=%s""",
            (owner, check["instrument_id"], check["id"]),
        )
    return True


def history(owner, iid, before=None):
    now = utcnow()
    with transaction(owner) as c:
        cursor = None
        if before:
            cursor = one(
                c,
                "SELECT started_at,id FROM filing_watch_checks WHERE owner_id=%s AND instrument_id=%s AND id=%s",
                (owner, iid, before),
            )
            if not cursor:
                raise ValueError("This filing-check page is unavailable.")
        params = [owner, iid]
        where = ""
        if cursor:
            where = " AND (a.started_at,a.id)<(%s,%s)"
            params += [cursor["started_at"], cursor["id"]]
        items = rows(
            c,
            """SELECT a.*,r.completed_at,r.outcome,r.message,r.source_check_id,
                s.cursor,s.checked_at AS source_checked_at
            FROM filing_watch_checks a LEFT JOIN filing_watch_results r ON r.check_id=a.id
            LEFT JOIN source_checks s ON s.id=r.source_check_id
            WHERE a.owner_id=%s AND a.instrument_id=%s"""
            + where
            + " ORDER BY a.started_at DESC,a.id DESC LIMIT 21",
            params,
        )
        for item in items:
            if item["outcome"] is None:
                item["outcome"] = (
                    "interrupted" if now >= item["lease_until"] else "running"
                )
                item["message"] = MESSAGES.get(
                    item["outcome"],
                    "Filing check is in progress. No completed result yet.",
                )
            # The saved SEC checkpoint, never the currently active filing.
            if item["cursor"]:
                import json

                checkpoint = json.loads(item.pop("cursor"))
                filing = one(
                    c,
                    "SELECT filing_url,form,period_end FROM filing_calculations WHERE document_version_id=%s",
                    (checkpoint.get("document_version_id"),),
                )
                item["filing"] = filing
            item.pop("cursor", None)
            item.pop("owner_id", None)
        return dict(
            items=items[:20],
            next_before=str(items[19]["id"]) if len(items) > 20 else None,
        )
