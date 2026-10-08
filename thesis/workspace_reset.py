"""Operator-only fresh research workspace; provider accounting is never reset."""
import hashlib
import json
from psycopg import sql
from thesis.db import rows, one

KEEP = {
    "schema_migrations", "accounts", "sources", "social_feeds",
    "source_request_clock", "market_request_clock", "price_history_clock",
    "hn_request_clock", "reddit_request_clock", "provider_clocks", "analyst_target_clock", "social_refresh_lock",
    "company_directory", "workspace_settings", "demo_state",
}


def tables(conn):
    return [r["tablename"] for r in rows(conn, "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")]


def accounting_hash(conn):
    result = {}
    for name in tables(conn):
        if name.startswith("model_"):
            values = rows(conn, sql.SQL("SELECT * FROM {}").format(sql.Identifier(name)))
            result[name] = sorted(json.dumps(row, sort_keys=True, default=str) for row in values)
    return hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()


def clear_research(conn):
    """Call only inside the administrator's transaction after a verified backup."""
    before = accounting_hash(conn)
    names = [name for name in tables(conn) if name not in KEEP and not name.startswith("model_")]
    counts = {name: one(conn, sql.SQL("SELECT count(*) AS n FROM {}").format(sql.Identifier(name)))["n"] for name in names}
    # No CASCADE: a newly introduced protected FK must fail, never erase accounting.
    conn.execute(sql.SQL("TRUNCATE {} RESTART IDENTITY").format(sql.SQL(",").join(map(sql.Identifier, names))))
    conn.execute("UPDATE workspace_settings SET seed_demo=false,reset_at=clock_timestamp() WHERE singleton")
    conn.execute("UPDATE demo_state SET stage=0 WHERE singleton")
    conn.execute("UPDATE social_refresh_lock SET attempt_id=NULL,lease_until=NULL,last_attempt_at=NULL WHERE singleton")
    if accounting_hash(conn) != before:
        raise RuntimeError("Reset changed protected model accounting; transaction must roll back.")
    return dict(cleared=counts, accounting_sha256=before)
