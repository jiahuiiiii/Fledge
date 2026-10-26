from contextlib import contextmanager
from contextvars import ContextVar
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


def _checkout(target):
    while True:
        with _lock:
            pool = _idle.get(target)
            conn = pool.pop() if pool else None
        if conn is None:
            return psycopg.connect(target, row_factory=dict_row), True
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
    conn = psycopg.connect(target, row_factory=dict_row)
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
