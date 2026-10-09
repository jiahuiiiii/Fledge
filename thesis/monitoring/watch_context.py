"""Explicitly opted-in, bounded original-parent checks before watched analysis."""

from datetime import datetime, timezone, timedelta
from thesis.db import transaction, one
from thesis.research import sentiment, conversation, hackernews
from thesis.service import Conflict, Missing

LIMIT = 4


def require_active(owner, iid, token, now=None, *, renew=False):
    from .news_watch import WatchStopped

    now = now or datetime.now(timezone.utc)
    with transaction(owner) as conn:
        row = one(
            conn,
            "SELECT enabled,claim_token,lease_until FROM news_watches WHERE owner_id=%s AND instrument_id=%s FOR UPDATE",
            (owner, iid),
        )
        if (
            not row
            or not row["enabled"]
            or row["claim_token"] != token
            or not row["lease_until"]
            or row["lease_until"] <= now
        ):
            raise WatchStopped()
        if renew:
            # Progress keeps this live worker leased. Never revive an expired,
            # stopped or replaced watch, or change its saved schedule/settings.
            conn.execute('UPDATE news_watches SET lease_until=GREATEST(lease_until,%s) WHERE owner_id=%s AND instrument_id=%s AND claim_token=%s',
                         (now + timedelta(minutes=15), owner, iid, token))


def collect(owner, iid, token, details, *, fetcher=None, now=None):
    """Mutate the attempt summary as each public lookup finishes, never publish."""

    def active():
        require_active(owner, iid, token, now)

    active()
    with transaction() as conn:
        packet = sentiment.prepare(conn, iid, now)
    selected = [s for s in packet["sources"] if s.get("platform") == "hackernews"]
    detail = dict(
        status="checking",
        selected_replies=len(selected),
        limit=LIMIT,
        items=[],
        source_requests=0,
    )
    details["context"] = detail

    def request(kind, value, cutoff):
        active()
        if detail["source_requests"] >= LIMIT * 2:
            raise ValueError("Conversation request bound reached.")
        detail["source_requests"] += 1
        return (fetcher or hackernews.fetch)(kind, value, cutoff)

    for source in selected[:LIMIT]:
        active()
        item = dict(source_id=source["id"], outcome="not_checked", reused=False)
        detail["items"].append(item)
        if source.get("conversation"):
            item.update(
                outcome="available",
                reused=True,
                result_id=source["conversation"]["result_id"],
            )
            continue
        try:
            value = conversation.collect(source["id"], fetcher=request, now=now)
            result = value.get("result") or {}
            item.update(
                outcome=result.get("outcome", "unavailable"), result_id=result.get("id")
            )
        except Conflict:
            # A recent/in-flight shared check is not permission for another request.
            item["outcome"] = "shared_recent_check"
        except Missing:
            item["outcome"] = "source_unavailable"
        if item["outcome"] == "failed":
            detail["status"] = "partial"
            break  # No remaining original-API requests after denial/transport failure.
        if item["outcome"] == "source_changed":
            detail["status"] = "source_changed"
            raise ValueError(
                "A selected comment changed; refresh sources before analysis."
            )
    active()
    with transaction() as conn:
        current = sentiment.prepare(conn, iid, now)
    detail["parents_available_for_analysis"] = sum(
        bool(s.get("conversation")) for s in current["sources"]
    )
    detail["coverage_gap"] = bool(
        len(selected) > len(detail["items"])
        or any(i["outcome"] != "available" for i in detail["items"])
        or detail["parents_available_for_analysis"] < min(len(selected), LIMIT)
    )
    if detail["status"] == "checking":
        detail["status"] = "partial" if detail["coverage_gap"] else "completed"
    return detail
