from contextlib import contextmanager
import psycopg
from psycopg.rows import dict_row
from .config import dsn


@contextmanager
def transaction(owner=None, *, admin=False, source=False, consistent=False):
    with psycopg.connect(
        dsn("thesis_local" if admin else "thesis_source" if source else "thesis_app"),
        row_factory=dict_row,
    ) as conn:
        if consistent:
            conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        if not admin:
            conn.execute(
                "SELECT set_config('app.user_id', %s, true)",
                (str(owner) if owner else "",),
            )
        yield conn


def rows(conn, sql, params=()):
    return conn.execute(sql, params).fetchall()


def one(conn, sql, params=()):
    return conn.execute(sql, params).fetchone()
