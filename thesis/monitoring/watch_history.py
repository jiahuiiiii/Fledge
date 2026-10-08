"""Append-only scheduled-check evidence; reading never refreshes or analyses."""

from datetime import datetime, timezone
import json
from psycopg.types.json import Jsonb
from thesis.db import transaction, one, rows
from thesis.research import sentiment, social


def start(conn, owner, watch, token, started, lease):
    idea = one(
        conn,
        "SELECT v.id FROM thesis_versions v JOIN theses t ON t.id=v.thesis_id AND t.owner_id=v.owner_id AND t.revision=v.revision WHERE t.owner_id=%s AND t.instrument_id=%s AND t.status<>'archived'",
        (owner, watch["instrument_id"]),
    )
    conn.execute(
        "INSERT INTO watch_checks(id,owner_id,instrument_id,started_at,lease_until,interval_minutes,match_idea,baseline_id,version_id,event_version_id,include_context,idea_purpose) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            token,
            owner,
            watch["instrument_id"],
            started,
            lease,
            watch["interval_minutes"],
            watch["match_idea"],
            watch["baseline_id"],
            idea["id"] if idea else None,
            watch.get("event_version_id"),
            watch.get("include_context", False),
            watch.get("idea_purpose", "reasoning"),
        ),
    )


def finish(
    conn,
    owner,
    check_id,
    status,
    details,
    analysis_id=None,
    idea_check_id=None,
    completed=None,
):
    from thesis.service import canonical

    check = one(
        conn,
        "SELECT * FROM watch_checks WHERE id=%s AND owner_id=%s",
        (check_id, owner),
    )
    completed = completed or datetime.now(timezone.utc)
    # A supplied scheduler clock is used in tests; never persist negative elapsed time.
    completed = max(completed, check["started_at"])
    if analysis_id:
        analysis = one(
            conn,
            "SELECT * FROM sentiment_analyses WHERE id=%s AND instrument_id=%s",
            (analysis_id, check["instrument_id"]),
        )
        if not analysis:
            raise ValueError("Scheduled check analysis belongs to a different company.")
        p = analysis["packet"]
        details = dict(
            details,
            cutoff=p["cutoff"],
            analysis_saved_at=analysis["created_at"],
            selected={
                ch: sum(s["channel"] == ch for s in p["sources"])
                for ch in ("news", "social")
            },
            candidate_news=p.get("available_news_count"),
            candidate_social=p.get("available_social_count"),
        )
        if "context" in details:
            details["context"] = dict(
                details["context"],
                parents_used_by_analysis=sum(
                    bool(s.get("conversation")) for s in p["sources"]
                ),
            )
    details = dict(
        details,
        social_coverage=[
            dict(
                feed=s["feed"],
                label=s["label"],
                enabled=s["enabled"],
                completed_at=s["completed_at"],
                failed=bool(s["error"]),
            )
            for s in social.status(conn, check["instrument_id"])
        ],
    )
    market_health = one(
        conn,
        "SELECT completed_at,news_error,quote_error FROM market_refresh_state WHERE instrument_id=%s",
        (check["instrument_id"],),
    )
    details["market_coverage"] = (
        dict(
            completed_at=market_health["completed_at"],
            news_failed=bool(market_health["news_error"]),
            quote_failed=bool(market_health["quote_error"]),
        )
        if market_health
        else None
    )
    from thesis.research import source_hub
    details["provider_coverage"] = source_hub.status(conn, check["instrument_id"])
    details["coverage_gap"] = bool(
        details.get("market") == "failed"
        or any(s["status"] == "failed" for s in details["provider_coverage"])
        or
        (market_health and market_health["news_error"])
        or any(s["enabled"] and s["failed"] for s in details["social_coverage"])
        or details.get("context", {}).get("coverage_gap")
        or details.get("context", {}).get("status") in ("source_changed", "checking")
    )
    if idea_check_id:
        publication = one(
            conn,
            "SELECT created_at FROM idea_alert_publications WHERE owner_id=%s AND check_id=%s AND mode='watch'",
            (owner, idea_check_id),
        )
        details["idea_alerts"] = int(bool(publication))
    conn.execute(
        "INSERT INTO watch_check_results VALUES(%s,%s,%s,%s,%s,%s,%s)",
        (
            owner,
            check_id,
            completed,
            status,
            analysis_id,
            idea_check_id,
            Jsonb(json.loads(canonical(details))),
        ),
    )


def present(conn, owner, check, result, now):
    w = one(
        conn,
        "SELECT enabled,claim_token,lease_until FROM news_watches WHERE owner_id=%s AND instrument_id=%s",
        (owner, check["instrument_id"]),
    )
    status = (
        result["status"]
        if result
        else (
            "unfinished"
            if not w
            or not w["enabled"]
            or w["claim_token"] != check["id"]
            or now >= check["lease_until"]
            else "running"
        )
    )
    details = result["details"] if result else {}
    withheld = False
    if result and result["analysis_id"]:
        a = one(
            conn,
            "SELECT * FROM sentiment_analyses WHERE id=%s",
            (result["analysis_id"],),
        )
        withheld = not a or sentiment.present(conn, a)["withheld"]
    count = (
        (details.get("company_alerts", 0) + details.get("idea_alerts", 0))
        if result
        else None
    )
    # Never infer a quiet success from a failed or unfinished attempt.
    reason = "The check has no recorded completion yet."
    if status == "unfinished":
        reason = "No completion was recorded before this check stopped or its lease ended. This is a coverage gap, not a quiet result."
    elif status == "failed":
        reason = (
            "The "
            + details.get("failed_stage", "scheduled")
            + " step did not complete. Earlier completed steps are shown; no automatic paid retry was made."
        )
    elif status == "stopped":
        reason = "The watch was stopped or changed while this check was running. Inspect any earlier published updates separately."
    elif status == "completed":
        if count:
            reason = (
                f"{count} grouped update"
                + ("s" if count != 1 else "")
                + " created for review."
            )
        elif details.get("idea_status") == "baseline" or (
            not check["baseline_id"] and not check["match_idea"]
        ):
            reason = "The first source sample established a baseline. No change alert was expected."
        elif details.get("idea_status") == "historical_only":
            reason = "The saved idea or source sample changed during analysis. The result remains historical; no current alert was published."
        elif details.get("idea_status") in ("no_new_sources", "older_sample"):
            reason = "No new eligible text needed a private check. Previously seen reports remain in the source view."
        else:
            reason = "No alert rule triggered within the selected source sample. This does not establish that nothing material happened."
    if status == "completed" and details.get("events") in ("checked", "reused"):
        reason += " An approved-event check also completed; condition reassessment and its updates are recorded separately."
    if status == "completed" and details.get("coverage_gap"):
        reason = "Some sources could not be refreshed; this check used the available sample. " + reason
    if withheld:
        reason = "The analysis details are withheld because access to a consumed source changed."
    return dict(
        id=str(check["id"]),
        instrument_id=str(check["instrument_id"]),
        started_at=check["started_at"].isoformat(),
        completed_at=result["completed_at"].isoformat() if result else None,
        status=status,
        elapsed_seconds=(
            max(0, (result["completed_at"] - check["started_at"]).total_seconds())
            if result
            else None
        ),
        match_idea=check["match_idea"],
        idea_purpose=check.get("idea_purpose", "reasoning"),
        include_context=check.get("include_context", False),
        event_version_id=(
            str(check["event_version_id"]) if check.get("event_version_id") else None
        ),
        interval_minutes=check["interval_minutes"],
        version_id=str(check["version_id"]) if check["version_id"] else None,
        withheld=withheld,
        reason=reason,
        details={} if withheld else details,
        alert_count=None if withheld else count,
        idea_check_id=(
            str(result["idea_check_id"])
            if result and result["idea_check_id"] and not withheld
            else None
        ),
    )


def history(owner, iid, before=None, *, now=None):
    from thesis.service import Missing

    now = now or datetime.now(timezone.utc)
    with transaction(owner, consistent=True) as c:
        anchor = (
            one(
                c,
                "SELECT started_at,id FROM watch_checks WHERE owner_id=%s AND instrument_id=%s AND id=%s",
                (owner, iid, before),
            )
            if before
            else None
        )
        if before and not anchor:
            raise Missing("Earlier watch-check page not found.")
        checks = rows(
            c,
            "SELECT * FROM watch_checks WHERE owner_id=%s AND instrument_id=%s AND (%s::timestamptz IS NULL OR (started_at,id)<(%s::timestamptz,%s::uuid)) ORDER BY started_at DESC,id DESC LIMIT 21",
            (
                owner,
                iid,
                anchor["started_at"] if anchor else None,
                anchor["started_at"] if anchor else None,
                anchor["id"] if anchor else None,
            ),
        )
        return dict(
            items=[
                present(
                    c,
                    owner,
                    check,
                    one(
                        c,
                        "SELECT * FROM watch_check_results WHERE owner_id=%s AND check_id=%s",
                        (owner, check["id"]),
                    ),
                    now,
                )
                for check in checks[:20]
            ],
            next_cursor=str(checks[19]["id"]) if len(checks) > 20 else None,
        )
