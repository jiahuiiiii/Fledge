"""A private list of the companies each account follows, at most five."""
import psycopg
from .db import transaction, one, rows

LIMIT = 5
FULL = f'Your watchlist holds up to {LIMIT} companies. Remove one to add another.'


def companies(owner, conn=None):
    sql = '''SELECT i.id,i.symbol,i.name,w.added_at FROM watchlist_companies w
             JOIN instruments i ON i.id=w.instrument_id WHERE w.owner_id=%s ORDER BY w.added_at,i.symbol'''
    if conn is not None:
        found = rows(conn, sql, (owner,))
    else:
        with transaction(owner) as c:
            found = rows(c, sql, (owner,))
    return [dict(id=str(r['id']), symbol=r['symbol'], name=r['name'], added_at=r['added_at'].isoformat()) for r in found]


def started(conn, owner):
    """True once the account has followed any company, even if it later removed all."""
    return bool(one(conn, 'SELECT 1 FROM watchlist_usage WHERE owner_id=%s', (owner,)))


def summary(owner):
    with transaction(owner) as conn:
        listed = companies(owner, conn)
        used = started(conn, owner)
    return dict(companies=listed, count=len(listed), limit=LIMIT, full=len(listed) >= LIMIT, started=used)


def add(owner, instrument_id):
    try:
        with transaction(owner) as conn:
            if not one(conn, 'SELECT 1 FROM instruments WHERE id=%s', (instrument_id,)):
                raise ValueError('Choose a company from the search first.')
            conn.execute('''INSERT INTO watchlist_companies(owner_id,instrument_id) VALUES(%s,%s)
                            ON CONFLICT DO NOTHING''', (owner, instrument_id))
            conn.execute('INSERT INTO watchlist_usage(owner_id) VALUES(%s) ON CONFLICT DO NOTHING', (owner,))
    except psycopg.errors.CheckViolation as failure:
        if 'watchlist_limit' in str(failure):
            raise ValueError(FULL) from None
        raise
    return summary(owner)


def remove(owner, instrument_id):
    with transaction(owner) as conn:
        conn.execute('DELETE FROM watchlist_companies WHERE owner_id=%s AND instrument_id=%s', (owner, instrument_id))
    return summary(owner)
