"""Discussion packaging, provenance and bounds. No provider/model requests."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from unittest.mock import patch

import pytest

from thesis.providers import ledger
from thesis.research import sentiment as S, sentiment_batching as B
from thesis.research import reddit_thread_context as T, relevance_prefilter as R
from thesis.research.sentiment_context import changed_common_context
from test_sentiment import provider
from test_sentiment_batching import packet as base_packet
from test_model_budget import clean_model_ledger


def discussion(count=4, *, root=True, text_size=0):
    packet = base_packet()
    sample = packet['sources'][-1]
    sources = []
    for index in range(count):
        source = deepcopy(sample)
        body = ('A' * text_size + ' ' if text_size else '') + f'Company outlook comment {index}.'
        source.update(id=f'source-{index}', label=f'item_{index+1}', channel='social',
                      platform='reddit', post_key=f't1_c{index}', thread_key='t3_topic',
                      social_kind='comment', discovery_match='direct',
                      author_hash='same-author' if index < 2 else f'author-{index}',
                      title='Reddit comment', text=body, content_hash=f'hash-{index}',
                      passages=[dict(id='p0', quote='Reddit comment'), dict(id='p1', quote=body)],
                      url=f'https://www.reddit.com/r/stocks/comments/topic/title/c{index}/',
                      timestamp_basis='feed_updated')
        sources.append(source)
    packet['sources'] = sources
    posts = []
    if root:
        posts = [dict(id='root-source', platform='reddit', post_key='t3_topic',
                      title='Company earnings discussion', body='The outlook is debated.',
                      author_hash='topic-author',
                      published_at=datetime(2026, 10, 12, tzinfo=timezone.utc),
                      available_at=datetime(2026, 10, 12, tzinfo=timezone.utc),
                      url='https://www.reddit.com/r/stocks/comments/topic/title/')]
    packet['reddit_thread_policy'] = T.POLICY
    packet['reddit_thread_context'] = T.attach(sources, posts)
    return packet


def payload(body):
    return json.loads(body['input'][1]['content'])


def test_topic_and_all_saved_comments_are_supplied_together_without_invented_depth():
    packet = discussion(4)
    before = deepcopy(packet)
    part = B.plan(packet)[0]
    wire = payload(S.request_for(part))
    thread = wire['reddit_threads'][0]
    assert thread['saved_message_count'] == thread['supplied_message_count'] == 5
    assert thread['messages'][0]['role'] == 'topic'
    assert thread['messages'][0]['passages'][0]['quote'] == 'Company earnings discussion'
    assert all(m['parent_key'] is None for m in thread['messages'])
    assert all('depth' not in m for m in thread['messages'])
    assert thread['complete_thread'] is False and thread['topic_available']
    comments = thread['messages'][1:]
    assert comments[0]['author_key'] == comments[1]['author_key'] != comments[2]['author_key']
    assert all('passages' not in m and m['source_label'] in {s['label'] for s in wire['sources']} for m in comments)
    assert packet == before


def test_more_than_eight_comments_keep_topic_and_saved_siblings_in_each_request():
    packet = discussion(13)
    parts = B.plan(packet)
    assert [len(p['sources']) for p in parts] == [8, 5]
    assert sorted(s['id'] for p in parts for s in p['sources']) == sorted(s['id'] for s in packet['sources'])
    for part in parts:
        body = S.request_for(part)
        thread = payload(body)['reddit_threads'][0]
        assert thread['supplied_message_count'] == 14
        assert len(ledger.canonical(body).encode()) <= B.MAX_BYTES
        assert sum('source_label' in m for m in thread['messages']) == len(part['sources'])


def test_unknown_root_is_explicit_and_other_threads_are_not_substituted():
    packet = discussion(root=False)
    context = payload(S.request_for(B.plan(packet)[0]))['reddit_threads'][0]
    assert context['topic_available'] is False
    assert not any(m['role'] == 'topic' for m in context['messages'])
    unrelated = deepcopy(packet['sources'][0])
    unrelated.update(id='other', label='item_99', thread_key='t3_elsewhere', post_key='t1_elsewhere')
    packet['sources'].insert(1, unrelated)
    packet['reddit_thread_context'] = T.attach(packet['sources'], [])
    wires = payload(S.request_for(B.plan(packet)[0]))['reddit_threads']
    assert len(wires) == 2
    assert all(m['message_key'] != 't1_elsewhere' for m in wires[0]['messages'])


def test_known_reply_links_are_explicit_but_feed_order_never_creates_links():
    packet = discussion()
    packet['sources'][1]['conversation'] = dict(parent_key='t1_c0')
    packet['sources'][2]['conversation'] = dict(parent_key='t1_c1')
    packet['reddit_thread_context'] = T.attach(packet['sources'], [])
    wire = T.wire(packet, [packet['sources'][2]])[0]
    messages = {m['message_key']: m for m in wire['messages']}
    assert messages['t1_c2']['parent_key'] == 't1_c1'
    assert messages['t1_c1']['parent_key'] == 't1_c0'
    assert messages['t1_c0']['parent_key'] is None


def test_long_threads_drop_whole_optional_messages_with_counts_and_keep_originals():
    packet = discussion(13, text_size=4500)
    before = deepcopy(packet)
    parts = B.plan(packet)
    assert len(parts) > 2
    for part in parts:
        body = S.request_for(part)
        assert len(ledger.canonical(body).encode()) <= B.MAX_BYTES
        thread = payload(body)['reddit_threads'][0]
        assert thread['topic_available'] and thread['omitted_saved_messages'] > 0
        assert thread['supplied_message_count'] + thread['omitted_saved_messages'] == 14
        for source in payload(body)['sources']:
            assert len(source['passages'][1]['quote']) > 4500
    assert packet == before


def test_oversized_topic_blocks_before_any_request():
    packet = discussion()
    packet['reddit_thread_context'][0]['messages'][0]['passages'] = [dict(id='p0', quote='A'*B.MAX_BYTES)]
    with patch.object(ledger, 'execute') as execute:
        with pytest.raises(ValueError, match='No batch was sent'):
            B.plan(packet)
        execute.assert_not_called()


def test_quick_check_also_receives_discussion_and_keeps_context_after_filtering():
    packet = discussion(13)
    body = R.plan(packet)[0]
    assert payload(body)['reddit_threads'][0]['supplied_message_count'] == 14
    assert all(s['text'] == packet['sources'][i]['text'] for i, s in enumerate(payload(body)['sources']))
    filtered = dict(packet, sources=packet['sources'][3:])
    assert T.wire(filtered, filtered['sources'])[0]['saved_message_count'] == 14


def test_comments_cannot_cite_generic_heading_as_own_attitude():
    packet = discussion()
    branches = S.request_for(packet)['text']['format']['schema']['properties']['items']['items']['anyOf']
    for source, branch in zip(packet['sources'], branches):
        definition = branch['properties']['passages']['items']['$ref'].split('/')[-1]
        assert S.request_for(packet)['text']['format']['schema']['$defs'][definition]['enum'] == ['p1']


def body_provider(body):
    def own(items):
        for item in items:
            item['passages'] = ['p1']
        return items
    return provider('neutral', mutate=own)(body)


def test_combined_reading_preserves_exact_context_supplied_to_each_batch_and_reuses(owner):
    packet = discussion(13, text_size=4500)
    parts = B.plan(packet)
    with patch.object(B, 'check_access'):
        result, calls = B.run(packet, transport=body_provider, prefilter=False)
        again, reused = B.run(packet, transport=lambda _: pytest.fail('duplicate call'), prefilter=False)
    assert again == result and [c['id'] for c in calls] == [c['id'] for c in reused]
    assert len(result['items']) == 13
    for part in parts:
        expected = T.wire(part, part['sources'], extras=part.get('thread_extras', True))[0]
        for source in part['sources']:
            item = next(i for i in result['items'] if i['source_id'] == source['id'])
            actual = item['thread_context']
            assert actual['omitted_saved_messages'] == expected['omitted_saved_messages']
            assert {m['message_key'] for m in actual['messages']} == {m['message_key'] for m in expected['messages']}


def test_context_only_topic_access_is_required_for_dispatch_and_saved_reading():
    packet = discussion()
    permitted = {s['id'] for s in packet['sources']}
    assert not T.access_allowed(packet, permitted)
    assert T.access_allowed(packet, permitted | {'root-source'})
    record = dict(id='saved', instrument_id=packet['instrument_id'], packet=packet)
    with patch.object(S, 'permitted_ids', return_value=permitted), patch.object(S.sentiment_guards, 'allowed', return_value=True):
        with pytest.raises(ValueError, match='access changed'):
            B.check_access(None, packet)
        assert S.present(None, record)['withheld']


def test_changed_discussion_context_is_not_a_new_author_opinion():
    before = discussion()
    after = deepcopy(before)
    after['sources'][0]['thread_context_key'] = 'changed-topic'
    assert changed_common_context(before, after, 'social', 'reddit')
    assert not changed_common_context(before, after, 'social', 'hackernews')
