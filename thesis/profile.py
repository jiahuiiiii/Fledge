"""First-login questions and per-account display preferences.

Answers tailor explanations and the home page. They are never used to choose,
rank or recommend investments.
"""
from .db import transaction, one
from .investor_type import classify

EXPERIENCE = ('new', 'etf', 'stocks', 'active')
INTERESTS = ('technology', 'banks', 'healthcare', 'consumer', 'energy',
             'industrials', 'property', 'communications', 'unsure')
HORIZONS = ('short', 'medium', 'long', 'unsure')
GOALS = ('learn', 'check', 'monitor', 'news')
MODES = ('explain', 'data')
FREQUENCIES = ('daily', 'weekly', 'monthly', 'rarely', 'unsure')
DROPS = ('sell', 'hold', 'add', 'check', 'unsure')


def default_mode(experience):
    # Newer investors start with plain-language explanations; anyone can switch.
    # Everyone starts in Beginner; Pro tools are switched on from the account menu.
    return 'explain'


def public(row):
    if not row:
        return {'completed': False}
    return {
        'completed': True,
        'experience': row['experience'],
        'interests': list(row['interests']),
        'horizon': row['horizon'],
        'goal': row['goal'],
        'trade_frequency': row['trade_frequency'],
        'drop_reaction': row['drop_reaction'],
        'investor_type': classify(row),
        'detail_mode': row['detail_mode'],
        'completed_at': row['completed_at'].isoformat(),
    }


def get(owner):
    with transaction(owner) as conn:
        return public(one(conn, 'SELECT * FROM investor_profiles WHERE owner_id=%s', (owner,)))


# Holding period follows from the trading-style answer; it is not asked.
HORIZON_FROM_FREQUENCY = {'daily': 'short', 'weekly': 'short', 'monthly': 'long',
                          'rarely': 'long', 'unsure': 'unsure', None: 'unsure'}


def save(owner, experience, interests=(), horizon=None, goal='learn', detail_mode=None,
         trade_frequency=None, drop_reaction=None):
    interests = list(interests)
    horizon = horizon or HORIZON_FROM_FREQUENCY.get(trade_frequency, 'unsure')
    if experience not in EXPERIENCE or horizon not in HORIZONS or goal not in GOALS:
        raise ValueError('Answer each question before continuing.')
    if trade_frequency not in (None, *FREQUENCIES) or drop_reaction not in (None, *DROPS):
        raise ValueError('Answer each question before continuing.')
    if (not isinstance(interests, list) or len(set(interests)) != len(interests)
            or any(i not in INTERESTS for i in interests)):
        raise ValueError('Choose interests from the list.')
    if 'unsure' in interests and len(interests) > 1:
        raise ValueError('Choose specific interests or "Not sure yet", not both.')
    # Retaking the quiz keeps the Beginner/Pro choice unless a new one is given.
    mode = detail_mode or default_mode(experience)
    if mode not in MODES:
        raise ValueError('Choose how much detail to show.')
    with transaction(owner) as conn:
        row = one(conn, '''INSERT INTO investor_profiles(owner_id,experience,interests,horizon,goal,detail_mode,
            trade_frequency,drop_reaction)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT(owner_id) DO UPDATE SET experience=EXCLUDED.experience,interests=EXCLUDED.interests,
            horizon=EXCLUDED.horizon,goal=EXCLUDED.goal,
            detail_mode=COALESCE(%s,investor_profiles.detail_mode),
            trade_frequency=EXCLUDED.trade_frequency,drop_reaction=EXCLUDED.drop_reaction,updated_at=now()
            RETURNING *''', (owner, experience, interests, horizon, goal, mode, trade_frequency, drop_reaction,
                  detail_mode))
    return public(row)


def set_mode(owner, detail_mode):
    if detail_mode not in MODES:
        raise ValueError('Choose how much detail to show.')
    with transaction(owner) as conn:
        row = one(conn, 'UPDATE investor_profiles SET detail_mode=%s,updated_at=now() WHERE owner_id=%s RETURNING *',
                  (detail_mode, owner))
    if not row:
        raise ValueError('Answer the first-login questions before changing this setting.')
    return public(row)
