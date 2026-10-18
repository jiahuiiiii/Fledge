"""Verified immediate parents for saved Reddit RSS replies.

The thread feed lists comments without parent IDs, so its order is never used.
Reddit's per-reply context feed lists the thread post, the reply's ancestor
line and then the reply. Only the entry directly before the reply is stored, as
that reply's parent, through the existing saved-parent records. Each check is
one paced RSS request; a few run after each live Reddit refresh.
"""
import hashlib
import re
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import httpx
from thesis.db import transaction, one, rows
from thesis.service import Conflict
from . import social, reddit_rss as rss

METHOD = 'reddit-context-rss-1'
MAX_CHECKS = 3
TIME_BUDGET = timedelta(seconds=120)
RETRY_AFTER = timedelta(minutes=15)
MAX_TITLE = 500
MAX_BODY = 6000
AVAILABLE = ("Immediate parent read from Reddit's context feed for this reply. Its time is the feed update time. "
             "Its words remain separate from the reply and do not count as another opinion.")


def _time(entry, field):
    try:
        value = datetime.fromisoformat((entry.findtext(rss.ATOM + field) or '').replace('Z', '+00:00'))
    except ValueError:
        return None
    return value if value.tzinfo else None


def _link(entry):
    return next((l.get('href', '') for l in entry.findall(rss.ATOM + 'link') if l.get('rel', 'alternate') == 'alternate'), '')


def parent(body, comment, now):
    """Return (outcome, parent, explanation, withdrawn) for one saved reply."""
    root = rss.xml(body)
    self_url = next((e.get('href') for e in root.findall(rss.ATOM + 'link') if e.get('rel') == 'self'), None)
    if self_url != rss.endpoint('context', comment):
        raise ValueError('The Reddit context feed does not match this reply.')
    entries = root.findall(rss.ATOM + 'entry')
    ids = [e.findtext(rss.ATOM + 'id') or '' for e in entries]
    thread_url = comment['url'].rsplit('/', 2)[0] + '/'
    if not entries or ids[0] != comment['thread_key'] or _link(entries[0]).rstrip('/') + '/' != thread_url:
        raise ValueError('The Reddit context feed is missing its verified thread post.')
    if ids.count(comment['post_key']) != 1:
        raise ValueError('The Reddit context feed does not contain this reply exactly once.')
    index = ids.index(comment['post_key'])
    # Everything before the reply is its ancestor line: unique comments in the same thread.
    for entry, key in zip(entries[1:index + 1], ids[1:index + 1]):
        if not re.fullmatch(r't1_[a-z0-9]+', key) or _link(entry) != thread_url + key[3:] + '/':
            raise ValueError('The Reddit context feed contains an unverified reply line.')
    if len(set(ids[:index + 1])) != index + 1 or index == 0:
        raise ValueError('The Reddit context feed contains an unverified reply line.')
    target = entries[index]
    text = social.plain_summary(target.findtext(rss.ATOM + 'content') or '')
    if text in ('[removed]', '[deleted]'):
        return 'source_removed', {}, 'The reply was removed. Its saved analysis must no longer be used.', [comment['post_key']]
    if hashlib.sha256(('Reddit comment\n' + text).encode()).hexdigest() != comment['content_hash']:
        return 'source_changed', {}, 'The reply changed after it was saved. Refresh research to save its new version; this saved version stays unchanged.', []
    child_time = _time(target, 'updated')
    if child_time is None or child_time > now:
        raise ValueError('The reply time in the Reddit context feed could not be verified.')
    entry, key = entries[index - 1], ids[index - 1]
    story = index == 1
    title = social.plain_summary(entry.findtext(rss.ATOM + 'title') or '') if story else 'Parent comment'
    content = social.plain_summary(entry.findtext(rss.ATOM + 'content') or '')
    if content in ('[removed]', '[deleted]'):
        return 'unavailable', {}, 'The immediate parent was removed. The saved reply remains separate.', [key]
    published = _time(entry, 'published' if story else 'updated')
    if published is None or published > child_time:
        # An edit after the reply means the current wording may not be what it answered.
        return 'unavailable', {}, 'The immediate parent changed after this reply, so its current wording may not be what the reply answered.', []
    if (not story and not content) or (story and not title) or len(title) > MAX_TITLE or len(content) > MAX_BODY:
        raise ValueError('This parent is outside the bounded conversation view. Open the original discussion.')
    return 'available', dict(
        parent_key=key, parent_type='story' if story else 'comment', title=title, body=content,
        url=thread_url if story else thread_url + key[3:] + '/', published_at=published), AVAILABLE, []


def candidates(conn, iid, now, limit, post_ids=None):
    """Unchecked saved replies; ones admitted only through their thread go first."""
    return rows(conn, """
        SELECT * FROM (
          SELECT DISTINCT ON (p.post_key) p.*, d.thread_key, d.match_basis
          FROM social_posts p JOIN social_discovery d ON d.post_id=p.id
          JOIN social_feeds f ON f.feed=p.feed AND f.enabled
          WHERE p.instrument_id=%s AND p.platform='reddit' AND d.kind='comment' AND d.method=%s
            AND (%s::uuid[] IS NULL OR p.id=ANY(%s::uuid[]))
            AND NOT EXISTS(SELECT 1 FROM social_withdrawals w WHERE w.post_key IN (p.post_key,d.thread_key))
          ORDER BY p.post_key, p.available_at DESC, p.id DESC) latest
        WHERE NOT EXISTS(
          SELECT 1 FROM social_conversation_state s LEFT JOIN social_conversation_results r ON r.id=s.latest_result_id
          WHERE s.post_id=latest.id AND ((s.lease_until IS NOT NULL AND s.lease_until>%s)
            OR (r.id IS NOT NULL AND (r.outcome<>'failed' OR r.checked_at>%s))))
        ORDER BY (latest.match_basis='thread') DESC, length(latest.body), latest.published_at DESC
        LIMIT %s""", (iid, rss.COMMENT_METHOD, post_ids, post_ids, now, now - RETRY_AFTER, limit))


def _claim(post_id, now):
    token = uuid4()
    with transaction(source=True) as conn:
        conn.execute('INSERT INTO social_conversation_state(post_id) VALUES(%s) ON CONFLICT DO NOTHING', (post_id,))
        state = one(conn, 'SELECT * FROM social_conversation_state WHERE post_id=%s FOR UPDATE', (post_id,))
        if state['lease_until'] and state['lease_until'] > now:
            return None
        conn.execute('UPDATE social_conversation_state SET attempt_id=%s,lease_until=%s,last_attempt_at=%s WHERE post_id=%s',
                     (token, now + timedelta(minutes=3), now, post_id))
    return token


def _release(post_id, token):
    with transaction(source=True) as conn:
        conn.execute('UPDATE social_conversation_state SET lease_until=NULL WHERE post_id=%s AND attempt_id=%s', (post_id, token))


def _record(post_id, token, outcome, found, explanation, withdrawn, done):
    with transaction(source=True) as conn:
        from .sec.service import collection_lock
        collection_lock(conn)
        state = one(conn, 'SELECT * FROM social_conversation_state WHERE post_id=%s FOR UPDATE', (post_id,))
        if state['attempt_id'] != token:
            raise Conflict('A newer conversation check replaced this attempt.')
        for key in withdrawn:
            conn.execute('INSERT INTO social_withdrawals VALUES(%s,%s) ON CONFLICT DO NOTHING', (key, done))
        rid = uuid4()
        conn.execute('INSERT INTO social_conversation_results VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                     (rid, post_id, token, outcome, found.get('parent_key'), found.get('parent_type'), found.get('title'),
                      found.get('body'), found.get('url'), found.get('published_at'), done, explanation))
        conn.execute('UPDATE social_conversation_state SET latest_result_id=%s,lease_until=NULL WHERE post_id=%s', (rid, post_id))


def check(iid, *, fetcher=None, now=None, limit=MAX_CHECKS, budget=TIME_BUDGET, post_ids=None, clock=None):
    """Check a few saved replies. Stops at the first refusal, wait or failure."""
    clock = clock or (lambda: datetime.now(timezone.utc))
    started = clock()
    # A supplied time stamps every result, as other source checks do.
    stamp = (lambda: now) if now else clock
    now = now or started
    get = fetcher or rss.read
    with transaction() as conn:
        pending = candidates(conn, iid, now, limit, [str(p) for p in post_ids] if post_ids else None)
    summary = dict(checked=0, available=0, unavailable=0, stopped=None)
    for reply in pending:
        if clock() - started >= budget:
            summary['stopped'] = 'Reply-parent checks paused for this refresh; the rest wait for a later one.'
            break
        token = _claim(reply['id'], now)
        if token is None:
            continue
        comment = dict(url=reply['url'], feed=reply['feed'], post_key=reply['post_key'],
                       thread_key=reply['thread_key'], content_hash=reply['content_hash'])
        stop = None
        try:
            outcome, found, explanation, withdrawn = parent(get('context', comment), comment, stamp())
        except Conflict as exc:
            _release(reply['id'], token)
            summary['stopped'] = str(exc)
            break
        except (httpx.HTTPError, OSError):
            outcome, found, withdrawn = 'failed', {}, []
            explanation = 'The Reddit context feed could not be reached. No automatic retry was made.'
            stop = explanation
        except ValueError as exc:
            # Transport refusals stop further requests; malformed feeds only fail this reply.
            outcome, found, withdrawn = ('failed' if 'Reddit RSS' in str(exc) else 'unavailable'), {}, []
            explanation = str(exc)
            stop = explanation if outcome == 'failed' else None
        _record(reply['id'], token, outcome, found, explanation, withdrawn, stamp())
        summary['checked'] += 1
        summary['available' if outcome == 'available' else 'unavailable'] += 1
        if stop:
            summary['stopped'] = stop
            break
    return summary
