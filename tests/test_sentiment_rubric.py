"""Authored development contracts; passing fixtures does not measure AI judgment."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from thesis.providers import ledger
from thesis.research import sentiment_tasks as T, sentiment_task_runner as R, sentiment as S
from thesis.research.citations import source_passages
from test_sentiment_tasks import packet, call, tones


DATA = json.loads((Path(__file__).resolve().parents[1] /
    'experiments/sentiment_batching/rubric_cases.json').read_text())
CASES = DATA['cases']


def case_packet(case):
    p = packet()
    source = deepcopy(p['sources'][0])
    source.update(id='authored-rubric-' + case['id'], label='item_1',
                  title=case.get('title', 'Authored discussion'), text=case['text'],
                  channel=case['channel'], url='https://example.invalid/rubric/' + case['id'])
    source['passages'], _ = source_passages(source['title'], source['text'])
    if source['channel'] == 'social':
        source.update(platform='reddit', social_kind='comment', discovery_match='direct')
    if case.get('parent'):
        # Use the existing required-parent fixture shape, never infer a thread.
        from experiments.sentiment_batching.controls import packet as controls
        source['conversation'] = deepcopy(controls()['sources'][5]['conversation'])
        source['conversation'].update(body=case['parent'],
            passages=[dict(id='p1', quote=case['parent'])])
    return dict(p, company=DATA['company'], sources=[source])


@pytest.fixture(autouse=True)
def no_dispatch(monkeypatch):
    monkeypatch.setattr(ledger, 'execute', lambda *a, **k: pytest.fail('Offline rubric test dispatched'))


@pytest.mark.parametrize('case', CASES, ids=lambda c: c['id'])
def test_development_inputs_keep_complete_text_and_parent_without_answer_leak(case):
    p = case_packet(case)
    before = deepcopy(p)
    body = T.request_for('tone', p)
    payload = json.loads(body['input'][1]['content'])
    source = payload['sources'][0]
    assert source['passages'] == p['sources'][0]['passages']
    assert case['text'] == ' '.join(q['quote'] for q in source['passages'] if q['id'] != 'p0')
    assert 'expected' not in source and 'reason' not in source
    assert 'cases' not in payload
    assert case['text'] not in body['input'][0]['content']
    if case.get('parent'):
        assert source['conversation']['passages'] == [dict(id='p1', quote=case['parent'])]
    assert p == before
    assert len(body['input'][0]['content']) <= 6000
    assert len(ledger.canonical(body).encode()) <= 48000


@pytest.mark.parametrize('case', CASES, ids=lambda c: c['id'])
def test_authored_reference_shapes_and_citations_are_accepted_without_repair(case):
    p = case_packet(case)
    item = tones(p)[0] | case['expected']
    item['passages'] = [q['id'] for q in p['sources'][0]['passages'] if q['id'] != 'p0'][:3]
    if case['id'] == 'superseded-view':
        item.update(passages=['p2'], previous_passages=['p1'])
    if case.get('parent'):
        item['context_passages'] = ['p1']
    original = deepcopy(item)
    result = T.tone_labels(call(dict(items=[item])), p)[0]
    assert {k: result[k] for k in case['expected']} == case['expected']
    rendered = S.render(call(dict(items=[item], coverage_links=[])), dict(p, reporting_policy=None))
    assert rendered['repairs']['repaired'] == 0
    assert {k: rendered['items'][0][k] for k in case['expected']} == case['expected']
    assert item == original
    bad = deepcopy(item)
    bad['passages'] = ['not-a-supplied-passage']
    with pytest.raises(ValueError):
        T.tone_labels(call(dict(items=[bad])), p)


def test_prompt_revision_changes_tone_request_identity_but_not_event_or_source_inputs(monkeypatch):
    p = case_packet(next(c for c in CASES if c['channel'] == 'news'))
    tone = T.request_for('tone', p)
    event = T.request_for('event', p)
    identity = R.identity(p)
    key = R.key_for('tone', tone, p)
    with monkeypatch.context() as old:
        old.setattr(T, 'INSTRUCTIONS', dict(T.INSTRUCTIONS, tone='Authored earlier tone instructions'))
        assert R.identity(p) != identity
        previous = T.request_for('tone', p)
        assert R.key_for('tone', previous, p) != key
        assert previous['input'][1] == tone['input'][1]
        assert previous['text'] == tone['text']
        assert T.request_for('event', p) == event


def test_development_examples_are_separate_from_teaching_snippets_and_cover_all_tones():
    assert len({c['id'] for c in CASES}) == len(CASES) == 16
    assert {c['expected']['sentiment'] for c in CASES} == {'positive', 'negative', 'mixed', 'neutral', 'unclear'}
    assert 'Not owner labels' in DATA['provenance']
    for text, label in T.TONE_TEACHING_EXAMPLES:
        assert text in T.INSTRUCTIONS['tone'] and label in T.INSTRUCTIONS['tone']
        assert all(text != c['text'] for c in CASES)
