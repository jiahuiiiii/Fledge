"""The five-question investor-type quiz: scoring and storage."""
import pytest
from thesis import profile
from thesis.investor_type import classify, TYPES


@pytest.mark.parametrize('answers,expected', [
    (dict(experience='active', horizon='short', trade_frequency='daily', drop_reaction='sell', goal='monitor'), 'active_trader'),
    (dict(experience='stocks', horizon='short', trade_frequency='weekly', drop_reaction='check', goal='check'), 'swing_trader'),
    (dict(experience='etf', horizon='long', trade_frequency='monthly', drop_reaction='hold', goal='learn'), 'steady_builder'),
    (dict(experience='stocks', horizon='long', trade_frequency='rarely', drop_reaction='add', goal='check'), 'long_term'),
    (dict(experience='new', trade_frequency='unsure', drop_reaction='unsure', goal='learn'), 'starting_out'),
    (dict(experience='new', goal='news'), 'starting_out'),  # known from the first question alone
    (dict(experience='stocks', goal='news'), None),  # style not answered yet
    ({}, None),
])
def test_classify(answers, expected):
    assert classify(answers) == expected


def test_every_type_is_reachable_and_ties_prefer_calmer_styles():
    assert {classify(dict(trade_frequency=f, drop_reaction='hold')) for f in ('daily', 'weekly', 'monthly', 'rarely')} == set(TYPES)
    # A tie goes to the calmer style.
    assert classify(dict(trade_frequency='unsure')) == 'starting_out'
    assert classify(dict(experience='etf', trade_frequency='unsure', drop_reaction='unsure')) == 'starting_out'
    assert classify(dict(experience='etf', trade_frequency='monthly', drop_reaction='unsure')) == 'steady_builder'
    assert classify(dict(experience='new', trade_frequency='rarely')) == 'long_term'


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
    assert older['trade_frequency'] is None and older['investor_type'] is None


def test_two_question_start_then_optional_style(owner):
    start = profile.save(owner, 'stocks', goal='news')  # the only up-front questions
    assert start['completed'] and start['horizon'] == 'unsure' and start['investor_type'] is None
    typed = profile.save(owner, 'stocks', goal='news', trade_frequency='rarely', drop_reaction='add')
    assert typed['investor_type'] == 'long_term' and typed['horizon'] == 'long'
    assert profile.save(owner, 'new', goal='learn')['investor_type'] == 'starting_out'
