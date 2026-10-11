"""A home page tailored to each account's answers and watchlist.

Everything here changes wording, order and next steps. It never names a
company the user has not chosen and never suggests buying or selling.
"""
from . import profile as profiles, watchlist

INTEREST_LABELS = {
    'technology': 'Technology', 'banks': 'Banks and finance', 'healthcare': 'Healthcare',
    'consumer': 'Consumer brands', 'energy': 'Energy', 'industrials': 'Industrials',
    'property': 'Property', 'communications': 'Media and telecoms',
}

# Starter-question ids match frontend/src/lib/companion.js; order follows the goal.
STARTER_ORDER = {
    'learn': ['business', 'growth', 'risks', 'outlook'],
    'check': ['risks', 'outlook', 'growth', 'business'],
    'monitor': ['outlook', 'risks', 'growth', 'business'],
}

HEADLINES = {
    'learn': 'Understand how your companies make money',
    'check': 'Test your stock ideas against the evidence',
    'monitor': 'Keep track of what changes for the companies you follow',
}


def next_step(profile, listed):
    if not profile['completed']:
        return dict(action='onboarding', label='Answer four quick questions so Fledge can fit your home page to you')
    if not listed:
        return dict(action='add_company', label='Add a company you own or want to understand')
    if profile['goal'] == 'monitor':
        return dict(action='watch', label='Turn on a watch for a company on your list')
    if profile['goal'] == 'check':
        return dict(action='save_reasoning', label='Write down why you like a company and what would change your mind')
    return dict(action='read_overview', label='Start with how your first company makes money')


def build(owner):
    profile = profiles.get(owner)
    listed = watchlist.summary(owner)
    goal = profile.get('goal', 'learn')
    interests = [i for i in profile.get('interests', []) if i in INTEREST_LABELS]
    return dict(
        profile=profile,
        detail_mode=profile.get('detail_mode', 'explain'),
        headline=HEADLINES[goal] if profile['completed'] else 'Welcome to Fledge',
        starter_order=STARTER_ORDER[goal],
        interests=[dict(id=i, label=INTEREST_LABELS[i]) for i in interests],
        watchlist=listed,
        next_step=next_step(profile, listed['companies']),
    )
