"""Displayed lean: positive vs negative, neutral separate. Pure; no DB or network."""
from copy import deepcopy
import pytest
from thesis.research import sentiment as S


def sample(positive=0, negative=0, neutral=0, mixed=0, unclear=0, tone='mixed / balanced'):
    return dict(tone=tone, counts=dict(positive=positive, negative=negative, neutral=neutral, mixed=mixed, unclear=unclear))


@pytest.mark.parametrize('counts,expected', [
    # 18 October live news counts: META, GOOGL, NVDA, AVGO.
    (dict(positive=26, negative=9, neutral=34, mixed=18), 'positive leaning'),
    (dict(positive=21, negative=13, neutral=28, mixed=4), 'mixed / balanced'),
    (dict(positive=22, negative=19, neutral=40, mixed=9), 'mixed / balanced'),
    (dict(positive=21, negative=13, neutral=19, mixed=9), 'mixed / balanced'),
    (dict(positive=4, negative=12, neutral=30), 'negative leaning'),
    (dict(positive=5, negative=0, neutral=40), 'positive leaning'),
    (dict(positive=10, negative=5), 'positive leaning'),  # exactly twice leads
    (dict(positive=2, negative=1, neutral=20), 'mostly neutral'),
    (dict(positive=2, negative=1, neutral=1, mixed=6), 'mixed / balanced'),
])
def test_lean_compares_positive_with_negative_only(counts, expected):
    assert S.lean(sample(**counts)) == expected


@pytest.mark.parametrize('tone', ['thin sample', 'separate platform samples'])
def test_samples_without_a_lean_keep_their_saved_tone(tone):
    assert S.lean(sample(positive=30, tone=tone)) == tone


def test_display_copy_keeps_the_saved_majority_tone_and_never_changes_the_record():
    saved = dict(news=sample(positive=26, negative=9, neutral=34, mixed=18),
                 social=dict(sample(positive=3, negative=1), tone='separate platform samples'),
                 social_platforms=dict(reddit=sample(positive=1, negative=8, neutral=2, tone='negative leaning'),
                                       hackernews=sample(positive=1, tone='thin sample')))
    before = deepcopy(saved)
    shown = S.displayed(saved)
    assert saved == before
    news = shown['news']
    assert news['tone'] == 'positive leaning' and news['majority_tone'] == 'mixed / balanced'
    assert news['directional_groups'] == 35 and news['lean_policy'] == S.LEAN_POLICY
    assert news['counts'] == saved['news']['counts']
    assert shown['social']['tone'] == 'separate platform samples'
    assert shown['social_platforms']['reddit']['tone'] == 'negative leaning'
    assert shown['social_platforms']['hackernews']['tone'] == 'thin sample'
    assert S.displayed(None) == {}
