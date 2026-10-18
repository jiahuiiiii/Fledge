"""Reddit reply parents from each reply's context feed; HTTP simulated, DB disposable."""
from datetime import datetime, timedelta, timezone
from xml.sax.saxutils import escape
import httpx
import pytest
from thesis.db import transaction, one, rows
from thesis.research import reddit_rss as rss, reddit_research, reddit_parents as P, reddit_thread_context, social, sentiment
from thesis.research.citations import model_source
from thesis.service import Conflict
from test_market import prepare
from test_sentiment import feed

THREAD = 'https://www.reddit.com/r/stocks/comments/abc123/discussion/'
POST = dict(title='Microsoft earnings outlook worries investors',
            body='I am concerned about Microsoft margins, but I am not saying a collapse is certain.')


@pytest.fixture(autouse=True)
def clocks(db, monkeypatch):
    with transaction(admin=True) as c:
        c.execute("DELETE FROM provider_clocks WHERE provider LIKE 'reddit-rss:%%'")
        c.execute("DELETE FROM public_feed_cache WHERE provider LIKE 'reddit-rss:%%'")
    monkeypatch.setattr(rss.time, 'sleep', lambda _: None)


def entry(key, body, updated, link=None):
    return (f'<entry><id>{key}</id><title>/u/reader on {escape(POST["title"])}</title>'
            f'<link href="{link or THREAD + key[3:] + "/"}"/><updated>{updated.isoformat()}</updated>'
            f'<author><name>/u/reader-{key}</name></author><content>{escape(body)}</content></entry>')


def root(published):
    return (f'<entry><id>t3_abc123</id><title>{escape(POST["title"])}</title><link href="{THREAD}"/>'
            f'<published>{published.isoformat()}</published><updated>{published.isoformat()}</updated>'
            f'<content>{escape(POST["body"])}</content></entry>')


def thread_feed(published, comments):
    self_url = THREAD + '.rss'
    return (f'<feed xmlns="http://www.w3.org/2005/Atom"><link rel="self" href="{self_url}"/>' + root(published)
            + ''.join(entry(*c) for c in comments) + '</feed>').encode()


def context_feed(published, chain, target, *, self_url=None, first=None):
    self_url = self_url or THREAD + target[3:] + '/.rss?context=8'
    return (f'<feed xmlns="http://www.w3.org/2005/Atom"><link rel="self" href="{self_url}"/>'
            + (first if first is not None else root(published)) + ''.join(entry(*c) for c in chain) + '</feed>').encode()


def comment(key='t1_reply2', body='Same here.'):
    import hashlib
    return dict(url=THREAD + key[3:] + '/', feed='stocks', post_key=key, thread_key='t3_abc123',
                content_hash=hashlib.sha256(('Reddit comment\n' + body).encode()).hexdigest())


def times():
    now = datetime.now(timezone.utc).replace(microsecond=0)
    return now, now - timedelta(minutes=1), now - timedelta(seconds=20), now - timedelta(seconds=10)


def test_context_endpoint_is_bound_to_one_saved_reply():
    assert rss.endpoint('context', comment()) == THREAD + 'reply2/.rss?context=8'
    for change in (dict(feed='investing'), dict(thread_key='t3_other1'), dict(post_key='t1_other2'),
                   dict(url='https://old.reddit.com/r/stocks/comments/abc123/discussion/reply2/'), dict(url=THREAD + 'reply2/?x=1')):
        with pytest.raises(ValueError, match='Unsupported'):
            rss.endpoint('context', dict(comment(), **change))


def test_reply_to_comment_uses_only_the_entry_directly_before_it():
    now, published, first, second = times()
    deeper = [('t1_comment1', 'Microsoft margins concern me.', first - timedelta(seconds=5)),
              ('t1_middle1', 'Margins will recover.', first), ('t1_reply2', 'Same here.', second),
              ('t1_child3', 'A later reply below it.', now)]
    outcome, found, _, withdrawn = P.parent(context_feed(published, deeper, 't1_reply2'), comment(), now)
    assert outcome == 'available' and not withdrawn
    assert found == dict(parent_key='t1_middle1', parent_type='comment', title='Parent comment',
                         body='Margins will recover.', url=THREAD + 'middle1/', published_at=first)


def test_top_level_reply_has_the_thread_post_as_its_parent():
    now, published, _, second = times()
    outcome, found, _, _ = P.parent(context_feed(published, [('t1_reply2', 'Same here.', second)], 't1_reply2'), comment(), now)
    assert outcome == 'available'
    assert found == dict(parent_key='t3_abc123', parent_type='story', title=POST['title'], body=POST['body'],
                         url=THREAD, published_at=published)


@pytest.mark.parametrize('change', ['self', 'no_root', 'missing', 'twice', 'other_thread', 'future'])
def test_unverified_context_feeds_are_rejected(change):
    now, published, first, second = times()
    chain = [('t1_comment1', 'Microsoft margins concern me.', first), ('t1_reply2', 'Same here.', second)]
    options = {}
    if change == 'self':
        options['self_url'] = THREAD + 'reply2/.rss'
    if change == 'no_root':
        options['first'] = ''
    if change == 'missing':
        chain = chain[:1]
    if change == 'twice':
        chain = chain + chain[1:]
    if change == 'other_thread':
        chain[0] = ('t1_comment1', 'Microsoft margins concern me.', first, 'https://www.reddit.com/r/stocks/comments/zzz999/other/comment1/')
    if change == 'future':
        chain[1] = ('t1_reply2', 'Same here.', now + timedelta(minutes=5))
    with pytest.raises(ValueError):
        P.parent(context_feed(published, chain, 't1_reply2', **options), comment(), now)


@pytest.mark.parametrize('change,outcome,withdrawn', [
    ('reply_changed', 'source_changed', []), ('reply_removed', 'source_removed', ['t1_reply2']),
    ('parent_removed', 'unavailable', ['t1_comment1']), ('parent_edited_later', 'unavailable', [])])
def test_changed_or_removed_messages_are_never_attached(change, outcome, withdrawn):
    now, published, first, second = times()
    parent, reply = ['t1_comment1', 'Microsoft margins concern me.', first], ['t1_reply2', 'Same here.', second]
    if change == 'reply_changed':
        reply[1] = 'Same here, edited.'
    if change == 'reply_removed':
        reply[1] = '[removed]'
    if change == 'parent_removed':
        parent[1] = '[deleted]'
    if change == 'parent_edited_later':
        parent[2] = now
    result = P.parent(context_feed(published, [tuple(parent), tuple(reply)], 't1_reply2'), comment(), now)
    assert result[0] == outcome and result[1] == {} and result[3] == withdrawn


def collected(owner, extra=(), **refresh):
    """Two saved replies: a company mention and a short reply that needs its parent."""
    iid = prepare(owner)
    now, published, first, second = times()
    comments = [('t1_comment1', 'Microsoft margins concern me.', first), ('t1_reply2', 'Same here.', second), *extra]
    calls = []
    chains = {'t1_reply2': [comments[0], comments[1]], 't1_comment1': [comments[0]]}
    for c in extra:
        chains[c[0]] = [c]

    def get(kind, value):
        calls.append((kind, value.get('post_key') if isinstance(value, dict) else None))
        if kind == 'search':
            return feed(date=published.isoformat())
        if kind == 'comments':
            return thread_feed(published, comments)
        return context_feed(published, chains[value['post_key']], value['post_key'])
    result = reddit_research.refresh(iid, collector='rss', fetcher=get, now=now, **refresh)
    return iid, now, result, calls, get


def test_refresh_verifies_parents_and_sentiment_reads_them(owner):
    iid, now, result, calls, _ = collected(owner, check_parents=True)
    # The thread-only short reply is checked first; each check is one context request.
    assert [c for c in calls if c[0] == 'context'] == [('context', 't1_reply2'), ('context', 't1_comment1')]
    assert result['parents'] == dict(checked=2, available=2, unavailable=0, stopped=None)
    assert '2 reply parents verified' in result['message']
    with transaction() as c:
        packet = sentiment.prepare(c, iid, now)
        reply = next(s for s in packet['sources'] if s.get('post_key') == 't1_reply2')
        assert reply['conversation']['parent_key'] == 't1_comment1'
        assert reply['conversation']['parent_type'] == 'comment'
        assert 'verified immediate reply parent is supplied' in model_source(reply)['source_note']
        thread = reddit_thread_context.wire(packet, packet['sources'], extras=False)[0]
        message = next(m for m in thread['messages'] if m['message_key'] == 't1_reply2')
        assert message['parent_key'] == 't1_comment1'
        # The verified parent is a required message, not an optional sibling.
        assert any(m['message_key'] == 't1_comment1' for m in thread['messages'])
        top = next(s for s in packet['sources'] if s.get('post_key') == 't1_comment1')
        assert top['conversation']['parent_type'] == 'story'


def test_injected_collection_checks_no_parents_unless_asked(owner):
    iid, now, result, calls, _ = collected(owner)
    assert 'parents' not in result and not any(c[0] == 'context' for c in calls)
    with transaction() as c:
        assert not rows(c, 'SELECT 1 FROM social_conversation_results')


def test_checks_are_bounded_once_per_reply_and_resume_later(owner):
    extra = [(f't1_extra{i}', f'Microsoft reply number {i}.', datetime.now(timezone.utc) - timedelta(seconds=5)) for i in range(3)]
    iid, now, result, calls, get = collected(owner, extra=extra, check_parents=True)
    assert result['parents']['checked'] == P.MAX_CHECKS
    first = [c[1] for c in calls if c[0] == 'context']
    assert first[0] == 't1_reply2' and len(first) == P.MAX_CHECKS
    calls.clear()
    assert P.check(iid, fetcher=get, now=now, limit=10)['checked'] == 2
    assert not set(c[1] for c in calls) & set(first)
    calls.clear()
    assert P.check(iid, fetcher=get, now=now, limit=10)['checked'] == 0 and not calls


def test_wait_releases_the_reply_and_records_nothing(owner):
    iid, now, _, _, _ = collected(owner)
    def waiting(kind, value):
        raise Conflict('Reddit RSS is waiting for its request window.')
    assert P.check(iid, fetcher=waiting, now=now)['stopped'].startswith('Reddit RSS is waiting')
    with transaction() as c:
        assert not rows(c, 'SELECT 1 FROM social_conversation_results')
        assert all(r['lease_until'] is None for r in rows(c, 'SELECT * FROM social_conversation_state'))


def test_refusal_stops_checks_and_retries_only_after_cooldown(owner):
    iid, now, _, _, get = collected(owner)
    calls = []
    def refused(kind, value):
        calls.append(value['post_key'])
        raise ValueError('Reddit RSS context returned HTTP 429. Collection stopped; saved sources are retained.')
    summary = P.check(iid, fetcher=refused, now=now)
    assert calls == ['t1_reply2'] and summary['unavailable'] == 1 and '429' in summary['stopped']
    with transaction() as c:
        assert one(c, 'SELECT outcome FROM social_conversation_results')['outcome'] == 'failed'
    # The refused reply is not retried within its cooldown; an untried one can be.
    calls.clear()
    P.check(iid, fetcher=refused, now=now + timedelta(minutes=5))
    assert calls == ['t1_comment1']
    later = P.check(iid, fetcher=get, now=now + timedelta(minutes=16), limit=5)
    assert later['checked'] == later['available'] == 1


def test_time_budget_stops_new_requests(owner):
    iid, now, _, _, get = collected(owner)
    ticks = iter([now, now, now + P.TIME_BUDGET])
    summary = P.check(iid, fetcher=get, now=now, clock=lambda: next(ticks))
    assert summary['checked'] == 1 and 'paused' in summary['stopped']


def test_malformed_feed_marks_only_that_reply_unavailable(owner):
    iid, now, _, _, get = collected(owner)
    def mixed(kind, value):
        if value['post_key'] == 't1_reply2':
            return b'<feed xmlns="http://www.w3.org/2005/Atom"/>'
        return get(kind, value)
    summary = P.check(iid, fetcher=mixed, now=now)
    assert summary == dict(checked=2, available=1, unavailable=1, stopped=None)


def test_reddit_parent_stays_usable_for_the_discussion_window(owner):
    iid, now, _, _, get = collected(owner)
    P.check(iid, fetcher=get, now=now)
    with transaction() as c:
        later = sentiment.prepare(c, iid, now + timedelta(days=3))
        reply = next(s for s in later['sources'] if s.get('post_key') == 't1_reply2')
        assert reply['context_status'] == 'included'


def test_withdrawn_parent_is_not_supplied(owner):
    iid, now, _, _, get = collected(owner)
    P.check(iid, fetcher=get, now=now)
    with transaction(source=True) as c:
        c.execute('INSERT INTO social_withdrawals VALUES(%s,%s)', ('t1_comment1', now))
    with transaction() as c:
        packet = sentiment.prepare(c, iid, now, allow_empty=True)
        assert not any(s.get('conversation', {}).get('parent_key') == 't1_comment1' for s in packet['sources'])


def test_context_requests_stop_before_the_shared_daily_limit():
    now = datetime.now(timezone.utc)
    with transaction(admin=True) as c:
        c.execute("INSERT INTO provider_clocks(provider,requests,usage_date) VALUES('reddit-rss:all',%s,%s) ON CONFLICT(provider) DO UPDATE SET requests=excluded.requests,usage_date=excluded.usage_date",
                  (rss.CONTEXT_DAILY_LIMIT, now.date()))
    calls = []
    transport = httpx.MockTransport(lambda request: calls.append(request) or httpx.Response(200))
    with pytest.raises(Conflict, match='Reply-parent checks pause'):
        rss.read('context', comment(), transport=transport)
    assert not calls


def test_parent_check_fault_never_fails_the_collected_refresh(owner, monkeypatch):
    iid, now, _, _, get = collected(owner)
    monkeypatch.setattr(P, 'parent', lambda *a: {}['broken'])
    result = reddit_research.refresh(iid, collector='rss', fetcher=get, now=now + timedelta(minutes=16), check_parents=True)
    assert result['status'] == 'ready' and result['parents']['checked'] == 0
    assert 'could not run' in result['parents']['stopped']
