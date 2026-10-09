"""Explicit original-parent inspection, separate from saved AI input/labels."""

from datetime import datetime, timezone, timedelta
import hashlib
import re
from uuid import uuid4
import httpx
from thesis.db import transaction, one
from thesis.service import Missing, Conflict
from . import hackernews as hn
from .social import plain_summary

COOLDOWN = timedelta(minutes=15)


def post(conn, identity):
    value = one(
        conn,
        "SELECT p.*,f.enabled,d.method AS discovery_method FROM social_posts p JOIN social_feeds f ON f.feed=p.feed LEFT JOIN social_discovery d ON d.post_id=p.id WHERE p.id=%s",
        (identity,),
    )
    if (
        not value
        or not value["enabled"]
        or one(
            conn, "SELECT 1 FROM hn_withdrawals WHERE post_key=%s UNION SELECT 1 FROM social_withdrawals WHERE post_key=%s", (value["post_key"],value["post_key"])
        )
    ):
        raise Missing(
            "This original comment is unavailable for conversation inspection."
        )
    return value


def present(conn, identity, now=None):
    original=post(conn, identity)
    now = now or datetime.now(timezone.utc)
    state = one(
        conn, "SELECT * FROM social_conversation_state WHERE post_id=%s", (identity,)
    )
    result = (
        one(
            conn,
            "SELECT * FROM social_conversation_results WHERE id=%s",
            (state["latest_result_id"],),
        )
        if state and state["latest_result_id"]
        else None
    )
    running = bool(state and state["lease_until"] and state["lease_until"] > now)
    value = dict(
        post_id=str(identity),
        can_refresh=original['platform']=='hackernews',
        checking=running,
        completion_missing=bool(state and state["lease_until"] and not running),
        next_check_at=(
            (state["last_attempt_at"] + COOLDOWN).isoformat()
            if state and state["last_attempt_at"]
            else None
        ),
        result=None,
    )
    if original.get('discovery_method') == 'reddit-comment-rss-updated-1' and not result:
        value['unavailable_reason'] = 'The Reddit feed does not identify the immediate reply parent. Open the original thread for context; refreshing this feed cannot reconstruct the reply tree.'
    if result:
        withheld = result["parent_key"] and one(
            conn,
            "SELECT 1 FROM hn_withdrawals WHERE post_key=%s UNION SELECT 1 FROM social_withdrawals WHERE post_key=%s",
            (result["parent_key"],result["parent_key"]),
        )
        value["result"] = dict(
            id=str(result["id"]),
            outcome="unavailable" if withheld else result["outcome"],
            checked_at=result["checked_at"].isoformat(),
            explanation=(
                "The parent is no longer available. Its retained text is withheld."
                if withheld
                else result["explanation"]
            ),
        )
        if result["outcome"] == "available" and not withheld:
            value["result"].update(
                parent_type=result["parent_type"],
                title=result["title"],
                body=result["body"],
                url=result["url"],
                published_at=result["published_at"].isoformat(),
            )
    return value


def read(identity):
    with transaction(consistent=True) as conn:
        return present(conn, identity)


def parent_content(raw, key, child_time, now):
    if not isinstance(raw, dict) or str(raw.get("id")) != key:
        raise ValueError("Parent identity could not be verified.")
    if raw.get("deleted") is True or raw.get("dead") is True:
        return None, True
    kind = raw.get("type")
    if kind not in {"story", "comment"} or type(raw.get("time")) is not int:
        raise ValueError("The parent is not an available story or comment.")
    published = datetime.fromtimestamp(raw["time"], timezone.utc)
    if not published <= child_time <= now:
        raise ValueError("The parent and comment dates are incompatible.")
    title = (
        plain_summary(raw.get("title", ""))
        if isinstance(raw.get("title", ""), str)
        else ""
    )
    body = (
        plain_summary(raw.get("text", ""))
        if isinstance(raw.get("text", ""), str)
        else ""
    )
    if (
        (kind == "comment" and not body)
        or (kind == "story" and not title)
        or len(title) > 500
        or len(body) > 6000
        or hn.RECRUITMENT.search(title + " " + body)
    ):
        raise ValueError(
            "This parent is outside the bounded conversation view. Open the original discussion."
        )
    return (
        dict(
            parent_key="hn:" + key,
            parent_type=kind,
            title=title if kind == "story" else "Parent comment",
            body=body,
            url="https://news.ycombinator.com/item?id=" + key,
            published_at=published,
        ),
        False,
    )


def collect(identity, *, fetcher=None, now=None):
    supplied_clock = now
    now = now or datetime.now(timezone.utc)
    token = uuid4()
    with transaction(source=True) as conn:
        original = post(conn, identity)
        if original['platform']!='hackernews':
            raise ValueError('Use Refresh research to check this Reddit discussion and its replies together.')
        conn.execute(
            "INSERT INTO social_conversation_state(post_id) VALUES(%s) ON CONFLICT DO NOTHING",
            (identity,),
        )
        state = one(
            conn,
            "SELECT * FROM social_conversation_state WHERE post_id=%s FOR UPDATE",
            (identity,),
        )
        if state["lease_until"] and state["lease_until"] > now:
            raise Conflict("This conversation is already being checked.")
        if state["last_attempt_at"] and now - state["last_attempt_at"] < COOLDOWN:
            raise Conflict("This conversation was checked recently; wait 15 minutes.")
        conn.execute(
            "UPDATE social_conversation_state SET attempt_id=%s,lease_until=%s,last_attempt_at=%s WHERE post_id=%s",
            (token, now + timedelta(minutes=3), now, identity),
        )
    fetcher = fetcher or hn.fetch
    outcome = "unavailable"
    explanation = "The original parent is unavailable."
    parent = {}
    withdrawn = []
    try:
        key = original["post_key"][3:]
        raw = fetcher("item", key, now)
        if not isinstance(raw, dict) or str(raw.get("id")) != key:
            raise ValueError("The original comment identity could not be verified.")
        if raw.get("deleted") is True or raw.get("dead") is True:
            withdrawn.append(original["post_key"])
            outcome = "source_removed"
            explanation = (
                "The comment was removed. Its saved analysis must no longer be used."
            )
        else:
            if (
                raw.get("type") != "comment"
                or not isinstance(raw.get("text"), str)
                or type(raw.get("time")) is not int
            ):
                raise ValueError("The original comment is incomplete.")
            child_time = datetime.fromtimestamp(raw["time"], timezone.utc)
            body = plain_summary(raw["text"])
            digest = hashlib.sha256(
                ("Hacker News comment\n" + body).encode()
            ).hexdigest()
            if (
                digest != original["content_hash"]
                or child_time != original["published_at"]
            ):
                outcome = "source_changed"
                explanation = "The original comment changed. Refresh social posts before inspecting its new conversation; this saved version stays unchanged."
            else:
                parent_key = str(raw.get("parent", ""))
                if (
                    not re.fullmatch(r"[1-9][0-9]{0,11}", parent_key)
                    or parent_key == key
                ):
                    raise ValueError("No valid immediate parent was supplied.")
                parent, removed = parent_content(
                    fetcher("item", parent_key, now), parent_key, child_time, now
                )
                if removed:
                    withdrawn.append("hn:" + parent_key)
                    parent = {}
                    explanation = "The immediate parent was removed. The saved comment remains separate."
                else:
                    outcome = "available"
                    explanation = "One original parent, checked now for reading. The parent’s words or headline are separate from the saved comment and do not automatically establish the reply’s opinion. Loading context does not change saved AI labels. A new sentiment analysis may use this recently checked parent."
    except httpx.HTTPStatusError as exc:
        outcome = "failed"
        explanation = f"The original API returned HTTP {exc.response.status_code}. No retry or fallback was made."
    except (httpx.HTTPError, OSError):
        outcome = "failed"
        explanation = (
            "The original discussion could not be reached. No automatic retry was made."
        )
    except (ValueError, TypeError, OverflowError) as exc:
        outcome = "unavailable"
        explanation = (
            str(exc)
            if isinstance(exc, ValueError)
            else "The original discussion response was incomplete."
        )
    with transaction(source=True) as conn:
        from .sec.service import collection_lock

        collection_lock(conn)
        done = supplied_clock or datetime.now(timezone.utc)
        state = one(
            conn,
            "SELECT * FROM social_conversation_state WHERE post_id=%s FOR UPDATE",
            (identity,),
        )
        if state["attempt_id"] != token:
            raise Conflict("A newer conversation check replaced this attempt.")
        for key in withdrawn:
            conn.execute(
                "INSERT INTO hn_withdrawals VALUES(%s,%s) ON CONFLICT DO NOTHING",
                (key, done),
            )
        rid = uuid4()
        conn.execute(
            "INSERT INTO social_conversation_results VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                rid,
                identity,
                token,
                outcome,
                parent.get("parent_key"),
                parent.get("parent_type"),
                parent.get("title"),
                parent.get("body"),
                parent.get("url"),
                parent.get("published_at"),
                done,
                explanation,
            ),
        )
        conn.execute(
            "UPDATE social_conversation_state SET latest_result_id=%s,lease_until=NULL WHERE post_id=%s",
            (rid, identity),
        )
        if outcome == "source_removed":
            return dict(
                post_id=str(identity),
                source_removed=True,
                result=dict(
                    outcome=outcome,
                    explanation=explanation,
                    checked_at=done.isoformat(),
                ),
            )
        return present(conn, identity, done)
