"""Whether a social post has been withdrawn, answered from a per-transaction
cache of the (small) withdrawal set.

Presenting a workspace checks withdrawal status once per social post for every
saved reading on the page — tens of thousands of identical point lookups. The
set of withdrawn post_keys is tiny and, inside one read-only transaction, fixed,
so it is loaded once per transaction (db._begin resets the cache) and checked in
memory. Callers that run outside a transaction cache fall back to a direct query.
"""
from thesis.db import one, rows


def _withdrawn(conn):
    cache = getattr(conn, "_request_cache", None)
    if cache is None:
        return None
    found = cache.get("withdrawn")
    if found is None:
        found = cache["withdrawn"] = {
            r["post_key"]
            for r in rows(
                conn,
                "SELECT post_key FROM hn_withdrawals"
                " UNION SELECT post_key FROM social_withdrawals",
            )
        }
    return found


def is_withdrawn(conn, post_key):
    found = _withdrawn(conn)
    if found is None:
        return bool(
            one(
                conn,
                "SELECT 1 FROM hn_withdrawals WHERE post_key=%s"
                " UNION SELECT 1 FROM social_withdrawals WHERE post_key=%s",
                (post_key, post_key),
            )
        )
    return post_key in found
