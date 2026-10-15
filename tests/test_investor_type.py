"""The five-question investor-type quiz: scoring and storage."""
import pytest
from thesis import profile
from thesis.investor_type import classify, TYPES


@pytest.mark.parametrize('answers,expected', [
    (dict(experience='active', horizon='short', trade_frequency='daily', drop_reaction='sell', goal='monitor'), 'active_trader'),
    (dict(experience='stocks', horizon='short', trade_frequency='weekly', drop_reaction='check', goal='check'), 'swing_trader'),
    (dict(experience='etf', horizon='long', trade_frequency='monthly', drop_reaction='hold', goal='learn'), 'steady_builder'),
    (dict(experience='stocks', horizon='long', trade_frequency='rarely', drop_reaction='add', goal='check'), 'long_term'),
    (dict(experience='new', horizon='unsure', trade_frequency='unsure', drop_reaction='unsure', goal='learn'), 'steady_builder'),
    ({}, 'steady_builder'),  # nothing answered: the calmest description
])
def test_classify(answers, expected):
    assert classify(answers) == expected


def test_every_type_is_reachable_and_ties_prefer_calmer_styles():
    assert {classify(dict(trade_frequency=f)) for f in ('daily', 'weekly', 'monthly', 'rarely')} == set(TYPES)
    # Long-term and active tie on a short horizon alone; the calmer label wins.
    assert classify(dict(horizon='short')) == 'swing_trader'


def test_answers_are_saved_validated_and_keep_pro_mode(owner):
    saved = profile.save(owner, 'active', [], 'short', 'monitor', trade_frequency='daily', drop_reaction='sell')
    assert saved['investor_type'] == 'active_trader' and saved['trade_frequency'] == 'daily'
    profile.set_mode(owner, 'data')
    retaken = profile.save(owner, 'etf', ['banks'], 'long', 'learn', trade_frequency='monthly', drop_reaction='hold')
    assert retaken['investor_type'] == 'steady_builder' and retaken['detail_mode'] == 'data'
    for bad in (dict(trade_frequency='hourly'), dict(drop_reaction='panic')):
        with pytest.raises(ValueError):
            profile.save(owner, 'new', [], 'long', 'learn', **bad)
    older = profile.save(owner, 'stocks', [], 'long', 'check')  # older clients send four answers
    assert older['trade_frequency'] is None and older['investor_type'] in TYPES
