"""Turn the five first-login answers into one of four investor types.

The type describes how someone says they plan to invest. It is a plain,
deterministic score (no AI) and is never used to choose, rank or recommend
investments.
"""

TYPES = ('long_term', 'steady_builder', 'swing_trader', 'active_trader')
# Someone who has not invested yet gets their own, honest result.
STARTING = 'starting_out'
# On a tie the calmer style wins: it is the safer description to start from.
TIE_ORDER = TYPES[1], TYPES[0], TYPES[2], TYPES[3]

L, B, S, A = TYPES
POINTS = {
    'experience': {'new': {B: 2, L: 1}, 'etf': {B: 3}, 'stocks': {L: 2, S: 1},
                   'active': {S: 1, A: 2}},
    'trade_frequency': {'daily': {A: 4}, 'weekly': {S: 4}, 'monthly': {B: 4},
                        'rarely': {L: 4}, 'unsure': {B: 1}},
    'drop_reaction': {'sell': {S: 1, A: 2}, 'hold': {B: 2, L: 1}, 'add': {L: 2, B: 1},
                      'check': {L: 1, S: 1}, 'unsure': {B: 1}},
    'goal': {'learn': {B: 1}, 'check': {L: 1, S: 1}, 'monitor': {S: 1, A: 1},
             'news': {S: 1, L: 1}, 'explore': {B: 1}},
}


def classify(answers):
    """Return the investor type key, or None until the style question is answered.

    The two up-front questions (experience, goal) are not enough to tell styles
    apart, except for people who have not started investing yet.
    """
    frequency = answers.get('trade_frequency')
    # "I haven't started yet" means just that, whatever else was answered.
    if frequency == 'unsure' or (answers.get('experience') == 'new' and frequency is None):
        return STARTING
    if frequency is None:
        return None
    score = dict.fromkeys(TYPES, 0)
    for question, table in POINTS.items():
        for kind, points in table.get(answers.get(question), {}).items():
            score[kind] += points
    return max(TIE_ORDER, key=lambda kind: (score[kind], -TIE_ORDER.index(kind)))
