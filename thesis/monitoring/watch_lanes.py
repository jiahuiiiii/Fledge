"""Independent fast-news leases; slow watches retain their saved schedule."""
import os
from datetime import timedelta
from thesis.db import one
from .us_session import fast_interval, next_fast_check


def enabled():
    value = os.environ.get("THESIS_SENTIMENT_LANES")
    if value is None and os.environ.get("THESIS_TEST_OFFLINE") != "true":
        from thesis.providers.settings import settings
        value = settings().get("THESIS_SENTIMENT_LANES")
    return str(value or "false").lower() in {"true", "1", "on"}


def present(conn, owner, iid):
    watch = one(conn,
        "SELECT enabled,interval_minutes,next_check_at,last_check_at,error,match_idea,event_version_id,include_context,idea_purpose "
        "FROM news_watches WHERE owner_id=%s AND instrument_id=%s", (owner, iid))
    if watch and enabled():
        fast = one(conn, "SELECT next_check_at,last_check_at,error FROM fast_watch_state WHERE owner_id=%s AND instrument_id=%s", (owner, iid))
        watch = dict(watch, lanes_enabled=True, fast_check=dict(fast) if fast else None)
    return watch


def active(conn, owner, iid, token, now, *, watch=None, renew=False, lock=True):
    """Caller locks the watch first; both lanes use the same lock order."""
    locking = " FOR UPDATE" if lock else ""
    watch = watch or one(conn, "SELECT * FROM news_watches WHERE owner_id=%s AND instrument_id=%s" + locking, (owner, iid))
    if not watch or not watch["enabled"]:
        return False
    if token is None:
        return True
    table = "news_watches"
    claim = watch
    if watch["claim_token"] != token:
        if not enabled():
            return False
        table = "fast_watch_state"
        claim = one(conn, "SELECT * FROM fast_watch_state WHERE owner_id=%s AND instrument_id=%s" + locking, (owner, iid))
    if not claim or claim["claim_token"] != token or not claim["lease_until"] or claim["lease_until"] <= now:
        return False
    if renew:
        conn.execute(f"UPDATE {table} SET lease_until=GREATEST(lease_until,%s) WHERE owner_id=%s AND instrument_id=%s AND claim_token=%s",
                     (now + timedelta(minutes=15), owner, iid, token))
    return True


def claim_fast(conn, owner, now, token):
    # Runtime rows are created only when the approved lane is enabled. There is
    # no preference backfill and no reuse of a slow watch's lease or due time.
    conn.execute(
        "INSERT INTO fast_watch_state(owner_id,instrument_id,next_check_at) "
        "SELECT owner_id,instrument_id,%s FROM news_watches WHERE owner_id=%s AND enabled "
        "ON CONFLICT DO NOTHING", (now, owner))
    watch = one(conn,
        "SELECT w.* FROM news_watches w JOIN fast_watch_state f USING(owner_id,instrument_id) "
        "WHERE w.owner_id=%s AND w.enabled AND f.next_check_at<=%s "
        "AND (f.lease_until IS NULL OR f.lease_until<=%s) "
        "ORDER BY f.next_check_at,w.instrument_id FOR UPDATE OF w SKIP LOCKED LIMIT 1",
        (owner, now, now))
    if not watch:
        return None
    iid = watch["instrument_id"]
    state = one(conn, "SELECT * FROM fast_watch_state WHERE owner_id=%s AND instrument_id=%s FOR UPDATE", (owner, iid))
    if state["lease_until"] and state["lease_until"] > now:
        return None
    conn.execute("UPDATE fast_watch_state SET claim_token=%s,lease_until=%s,next_check_at=%s WHERE owner_id=%s AND instrument_id=%s",
                 (token, now + timedelta(minutes=15), next_fast_check(now), owner, iid))
    return dict(watch, lane="fast", interval_minutes=fast_interval(now))
