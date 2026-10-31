from contextlib import contextmanager
from contextvars import ContextVar
import logging
import os
import re
import threading
import time
import psycopg
from psycopg.rows import dict_row
from psycopg.pq import TransactionStatus
from .config import dsn

# Opening a PostgreSQL connection starts a new server process. The app and its
# background workers open thousands of short transactions, so idle connections
# are kept and reused instead. Each transaction still starts clean: the owner
# setting is transaction-local and every use ends in commit or rollback.
MAX_IDLE = 12
_idle = {}
_lock = threading.Lock()

# Per-request timing, read by the app's timing middleware.
request_stats = ContextVar("request_stats", default=None)


# Opt-in per-statement timing. Set THESIS_SQL_TIMING_MS=<threshold> to log every
# individual SQL statement that runs at or above that many milliseconds; unset or
# 0 keeps connections on their ordinary zero-overhead path. Timing lives on the
# cursor so it catches every statement, including the ~357 call sites that use
# conn.execute(...) directly rather than the one()/rows() helpers. Diagnostic
# only, no schema change: used to find which query in a slow request is costly.
def _sql_timing_threshold():
    try:
        return float(os.environ.get("THESIS_SQL_TIMING_MS", "") or 0)
    except ValueError:
        return 0.0


_SQL_TIMING_MS = _sql_timing_threshold()
_sql_log = logging.getLogger("thesis.timing.sql")


def _query_pattern(query):
    # A short, stable label for one query shape: first ~80 characters with
    # whitespace collapsed. Enough to tell the hot statements apart in a summary.
    text = (
        query
        if isinstance(query, str)
        else query.decode("utf-8", "replace")
        if isinstance(query, (bytes, bytearray))
        else str(query)
    )
    return re.sub(r"\s+", " ", text).strip()[:80]


def _log_slow_query(query, elapsed_ms, rowcount):
    # One short line: duration, rows, and the query collapsed to a single line
    # and capped so the log stays readable.
    text = (
        query
        if isinstance(query, str)
        else query.decode("utf-8", "replace")
        if isinstance(query, (bytes, bytearray))
        else str(query)
    )
    flat = re.sub(r"\s+", " ", text).strip()
    if len(flat) > 300:
        flat = flat[:300] + "…"
    _sql_log.warning("Slow query %.0f ms (%s rows): %s", elapsed_ms, rowcount, flat)


class _TimingCursor(psycopg.Cursor):
    """A cursor that logs any statement at or above the threshold. Installed as
    the connection's cursor factory only while THESIS_SQL_TIMING_MS is set."""

    def execute(self, query, params=None, **kwargs):
        started = time.perf_counter()
        result = super().execute(query, params, **kwargs)
        elapsed = (time.perf_counter() - started) * 1000
        if elapsed >= _SQL_TIMING_MS:
            _log_slow_query(query, elapsed, self.rowcount)
        # Roll each statement up by pattern so the request's timing middleware
        # can report the few query shapes that dominated a slow request.
        stats = request_stats.get()
        if stats is not None:
            pattern = _query_pattern(query)
            by_query = stats.setdefault("by_query", {})
            slot = by_query.get(pattern)
            if slot is None:
                by_query[pattern] = [1, elapsed]
            else:
                slot[0] += 1
                slot[1] += elapsed
        return result


def _connect(target):
    if _SQL_TIMING_MS:
        return psycopg.connect(
            target, row_factory=dict_row, cursor_factory=_TimingCursor
        )
    return psycopg.connect(target, row_factory=dict_row)


def _checkout(target):
    while True:
        with _lock:
            pool = _idle.get(target)
            conn = pool.pop() if pool else None
        if conn is None:
            return _connect(target), True
        if not conn.closed and not conn.broken and conn.info.transaction_status == TransactionStatus.IDLE:
            return conn, False
        conn.close()


def _checkin(target, conn):
    if conn.closed or conn.broken or conn.info.transaction_status != TransactionStatus.IDLE:
        conn.close()
        return
    with _lock:
        pool = _idle.setdefault(target, [])
        if len(pool) < MAX_IDLE:
            pool.append(conn)
            return
    conn.close()


def reset_pool():
    """Close idle connections, e.g. after the database was restarted."""
    with _lock:
        pools = list(_idle.values())
        _idle.clear()
    for pool in pools:
        for conn in pool:
            conn.close()


def _begin(conn, owner, admin, consistent):
    # A scratch cache scoped to this one transaction: read helpers memoize
    # immutable or snapshot-stable lookups here instead of repeating identical
    # point queries. Reset on every transaction start so nothing leaks between
    # them on a pooled connection.
    conn._request_cache = {}
    if consistent:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
    if not admin:
        conn.execute(
            "SELECT set_config('app.user_id', %s, true)",
            (str(owner) if owner else "",),
        )
    elif not consistent:
        conn.execute("SELECT 1")


def _open(target, owner, admin, consistent):
    """A connection with its transaction started. A kept connection that the
    database closed (for example after a restart) is replaced once."""
    try:
        conn, fresh = _checkout(target)
    except psycopg.OperationalError:
        reset_pool()
        raise
    try:
        _begin(conn, owner, admin, consistent)
        return conn, fresh
    except psycopg.OperationalError:
        conn.close()
        if fresh:
            raise
    reset_pool()
    conn = _connect(target)
    try:
        _begin(conn, owner, admin, consistent)
    except BaseException:
        conn.close()
        raise
    return conn, True


@contextmanager
def transaction(owner=None, *, admin=False, source=False, consistent=False):
    target = dsn("thesis_local" if admin else "thesis_source" if source else "thesis_app")
    stats = request_stats.get()
    started = time.perf_counter()
    conn, fresh = _open(target, owner, admin, consistent)
    if stats is not None:
        stats["db_open_ms"] += (time.perf_counter() - started) * 1000
        stats["transactions"] += 1
        stats["new_connections"] += fresh
    try:
        yield conn
    except BaseException:
        if not conn.closed:
            try:
                conn.rollback()
            except psycopg.Error:
                conn.close()
        _checkin(target, conn)
        raise
    else:
        try:
            conn.commit()
        except BaseException:
            conn.close()
            raise
        _checkin(target, conn)
    finally:
        if stats is not None:
            stats["db_ms"] += (time.perf_counter() - started) * 1000


def rows(conn, sql, params=()):
    return conn.execute(sql, params).fetchall()


def one(conn, sql, params=()):
    return conn.execute(sql, params).fetchone()
