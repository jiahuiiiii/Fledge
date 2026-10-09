"""Full-corpus classification uses only disposable storage and mocked models."""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from hashlib import sha256
from uuid import uuid4
from unittest.mock import patch
import pytest

from thesis.db import transaction
from thesis.providers import ledger
from thesis.research import sentiment as S, sentiment_batching as B
from test_market import prepare, commit, news
from test_sentiment import provider
from test_sentiment_batching import packet
from test_model_budget import clean_model_ledger


def large_packet(n=66):
    p = packet()
    original = next(s for s in p['sources'] if s['channel'] == 'news')
    p['sources'] = []
    for i in range(n):
        source = deepcopy(original)
        source.update(id=str(uuid4()), label=f'item_{i+1}', content_hash=f'unique-{i}',
                      title=f'Microsoft distinct report {i}',
                      published_at=(datetime(2026, 10, 9, tzinfo=timezone.utc)-timedelta(minutes=i)).isoformat())
        p['sources'].append(source)
    return p


def test_sixty_six_sources_fit_batches_and_merge_every_classification(owner):
    p = large_packet(); before = deepcopy(p)
    parts = B.plan(p)
    assert p == before
    assert Counter(s['id'] for part in parts for s in part['sources']) == Counter(s['id'] for s in p['sources'])
    assert len(parts) >= 9
    assert all(len(part['sources']) <= 8 and len(ledger.canonical(S.request_for(part)).encode()) <= B.MAX_BYTES for part in parts)
    assert all(len(part['comparison_sources']) <= B.MAX_COMPARISONS for part in parts)
    with patch.object(B, 'check_access'):
        result, calls = B.run(p, transport=provider('neutral'))
        assert len(result['items']) == 66 and result['summary']['news']['selected'] == 66
        assert result['summary']['news']['relevant'] == 66
        assert result['batching']['comparison_context_bounded']
        saved = ledger.snapshot()
        again, reused = B.run(p, transport=lambda _: pytest.fail('cached call dispatched'))
    assert again == result and [c['id'] for c in calls] == [c['id'] for c in reused]
    assert ledger.snapshot() == saved


def test_full_pool_keeps_every_news_item_and_distinct_same_thread_reply(owner):
    iid = prepare(owner)
    reports = [news(id=i+1, url=f'https://example.test/full/{i}', headline=f'Microsoft report {i}', summary=f'Distinct complete Microsoft wording for report {i}.') for i in range(66)]
    for start in range(0, len(reports), 25):
        commit(iid, reports[start:start+25])
    now = datetime.now(timezone.utc)
    posts = [dict(id=str(uuid4()), platform='reddit', title=f'Microsoft reply {i}', body=f'A distinct Microsoft investment opinion {i}.', content_hash=f'reddit-{i}',
                  feed='stocks', post_key=f'reddit:reply{i}', thread_key='reddit:shared-thread', social_kind='comment', match_basis='direct',
                  published_at=now-timedelta(minutes=1), available_at=now, url=f'https://www.reddit.com/r/stocks/comments/a/reply{i}', author_hash=None) for i in range(45)]
    duplicate = dict(posts[0], id=str(uuid4()), post_key='reddit:duplicate')
    missing_context = dict(posts[0], id=str(uuid4()), post_key='reddit:context', content_hash='context', match_basis='thread')
    with patch.object(S.social, 'documents', return_value=posts+[duplicate,missing_context]):
        with transaction() as conn:
            p = S.prepare(conn, iid, now)
    assert len([s for s in p['sources'] if s['channel'] == 'news']) == 67
    assert len([s for s in p['sources'] if s['channel'] == 'social']) == 45
    counts = p['selection']['scopes']['reddit']
    assert counts == dict(candidates=47, eligible=45, excluded=dict(exact_duplicate=1, required_context_unavailable=1))
    assert not p['comparison_sources'] and 'input_limits' not in p
    assert p['selection']['policy'] == S.SELECTION_POLICY


def test_batch_parent_limits_split_without_losing_later_parents():
    p = packet()
    parent = dict(parent_key='hn:1', parent_type='comment', published_at='2026-10-09T00:00:00+00:00',
                  passages=[dict(id='p1', quote='A complete original parent passage.')])
    p['sources'] = [dict(s, channel='social', platform='hackernews', conversation=deepcopy(parent)) for s in p['sources']]
    parts = B.plan(p)
    assert [len(part['sources']) for part in parts] == [4,4,4]
    assert [s for part in parts for s in part['sources']] == p['sources']


@pytest.mark.parametrize('platform,kind', [('hackernews', 'comment'), ('hackernews', None), ('reddit', 'comment')])
@pytest.mark.parametrize('has_parent', [False, True])
@pytest.mark.parametrize('body', ['', 'Microsoft hits its highest price... like clockwork.'])
def test_comment_without_complete_own_body_is_counted_before_planning(owner, platform, kind, has_parent, body):
    iid = prepare(owner)
    now = datetime.now(timezone.utc)
    post = dict(id=str(uuid4()), platform=platform, title='Community comment', body=body,
                content_hash='unreadable-comment', feed='stocks', post_key='comment:unreadable',
                published_at=now, available_at=now, url='https://example.test/comment', author_hash=None)
    if kind:
        post.update(social_kind=kind, thread_key='thread:1', match_basis='direct')
    parent = dict(parent_key='thread:1', parent_type='story', published_at=now.isoformat(),
                  passages=[dict(id='p0', quote='Microsoft is wonderful.')])
    def attach(_conn, sources, _cutoff, **_kwargs):
        if has_parent:
            for s in sources:
                if s['id'] == post['id']:
                    s['conversation'] = deepcopy(parent)
    with patch.object(S.social, 'documents', return_value=[post]), patch.object(S.sentiment_context, 'attach', side_effect=attach):
        with transaction() as conn:
            prepared = S.prepare(conn, iid, now)
    assert post['id'] not in {s['id'] for s in prepared['sources']}
    assert prepared['selection']['scopes'][platform] == dict(
        candidates=1, eligible=0, excluded={'no_complete_body_passages': 1})
    assert sum(len(p['sources']) for p in B.plan(prepared)) == 1
    assert all(s['channel'] == 'news' for s in prepared['sources'])


def test_headline_only_news_and_authored_post_titles_stay_eligible(owner):
    iid = prepare(owner)
    commit(iid, [news(id=99, url='https://example.test/headline-only',
                     headline='Microsoft announces a product.', summary='Unfinished detail...')])
    now = datetime.now(timezone.utc)
    post = dict(id=str(uuid4()), platform='reddit', title='I like Microsoft stock.', body='',
                content_hash='authored-post-title', feed='stocks', post_key='reddit:post',
                social_kind='post', thread_key='reddit:post', match_basis='direct',
                published_at=now, available_at=now, url='https://example.test/post', author_hash=None)
    with patch.object(S.social, 'documents', return_value=[post]):
        with transaction() as conn:
            prepared = S.prepare(conn, iid, now)
    assert len(prepared['sources']) == 3
    assert post['id'] in {s['id'] for s in prepared['sources']}
    B.plan(prepared)


def test_complete_comment_body_survives_other_omitted_fragments(owner):
    iid = prepare(owner)
    now = datetime.now(timezone.utc)
    post = dict(id=str(uuid4()), platform='hackernews', title='Hacker News comment',
                body='Microsoft revenue... I still dislike its pricing.',
                content_hash='partly-readable', feed='hackernews', post_key='hn:complete',
                social_kind='comment', thread_key='hn:thread', match_basis='direct',
                published_at=now, available_at=now, url='https://example.test/comment', author_hash=None)
    with patch.object(S.social, 'documents', return_value=[post]):
        with transaction() as conn:
            prepared = S.prepare(conn, iid, now)
    child = next(s for s in prepared['sources'] if s['id'] == post['id'])
    assert child['passages'] == [dict(id='p0', quote='Hacker News comment'),
                                 dict(id='p2', quote='I still dislike its pricing.')]
    assert child['omitted_fragment_count'] == 1
    assert prepared['selection']['scopes']['hackernews'] == dict(candidates=1, eligible=1, excluded={})
    B.plan(prepared)


def test_full_plan_insufficient_budget_stops_before_dispatch(owner):
    p = large_packet()
    with patch.object(ledger, 'snapshot', return_value=dict(remaining_usd='0.01')), patch.object(ledger, 'execute') as execute:
        with pytest.raises(ledger.BudgetBlocked, match='complete 66-source reading'):
            B.run(p)
        execute.assert_not_called()


def test_missing_or_duplicate_classification_in_later_batch_blocks_merge():
    p = large_packet(24); parts = B.plan(p)
    calls = [dict(response_body=provider('neutral')(S.request_for(part))) for part in parts]
    import json
    body = json.loads(calls[-1]['response_body']['output'][0]['content'][0]['text'])
    body['items'].pop()
    calls[-1]['response_body']['output'][0]['content'][0]['text'] = json.dumps(body)
    with pytest.raises(ValueError, match='every source exactly once'):
        B.combine(p, parts, calls)
