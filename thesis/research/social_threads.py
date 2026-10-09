"""Store verified thread relationships separately from each author's words.

Deus enriches a Reddit post before classification. Thesis retains each reply as
an individual source and pins its original parent, rather than pooling authors.
"""
from uuid import uuid4
from thesis.db import one

METHOD = "deus-thread-discovery-1"


def save(conn, post_id, thread_key, kind, match_basis, checked_at, parent=None, *, method=None):
    conn.execute(
        "INSERT INTO social_discovery VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
        (post_id, thread_key, kind, match_basis, method or METHOD),
    )
    if not parent:
        return
    # Do not race an explicit conversation check. Reuse unchanged fresh context.
    conn.execute("INSERT INTO social_conversation_state(post_id) VALUES(%s) ON CONFLICT DO NOTHING", (post_id,))
    state = one(conn, "SELECT * FROM social_conversation_state WHERE post_id=%s FOR UPDATE", (post_id,))
    if state['lease_until'] and state['lease_until'] > checked_at:
        return
    current = one(conn, "SELECT * FROM social_conversation_results WHERE id=%s", (state['latest_result_id'],)) if state['latest_result_id'] else None
    if current and current['checked_at'] >= checked_at:
        return
    rid, attempt = uuid4(), uuid4()
    conn.execute(
        "INSERT INTO social_conversation_results VALUES(%s,%s,%s,'available',%s,%s,%s,%s,%s,%s,%s,%s)",
        (rid,post_id,attempt,parent['parent_key'],parent['parent_type'],parent['title'],parent['body'],parent['url'],parent['published_at'],checked_at,
         "Original parent read from the same public HTML thread. Its words remain separate from the reply and do not count as another opinion." if method == 'reddit-public-html-1' else
         "Original parent verified during company discussion research. Its words remain separate from the reply and do not count as another opinion."),
    )
    conn.execute("UPDATE social_conversation_state SET latest_result_id=%s,last_attempt_at=%s WHERE post_id=%s", (rid,checked_at,post_id))
