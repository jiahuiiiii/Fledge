"""Authored diagnostic controls, never real-company evidence or app fixtures."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from thesis.research import reporting_basis, sentiment_context
from thesis.research.citations import source_passages


def packet():
    entries = [
        ('news', 'Financing announcement', 'Lumen Devices announced a $2 billion loan for its chip factory. The company stated no expected effect on earnings.'),
        ('social', 'Changed opinion', 'I used to dislike Lumen Devices. I now respect its engineering and think its products are excellent.'),
        ('news', 'Unconfirmed contract report', 'An unnamed source alleges Lumen Devices won the Cedar supply contract. Neither party has confirmed the allegation.'),
        ('social', 'Quoted opinion', 'My friend says Lumen Devices is brilliant. I have no opinion about the company yet.'),
        ('news', 'Company announces factory loan', 'Lumen Devices announced a $2 billion loan for its chip factory. The company stated no expected effect on earnings.'),
        ('social', 'Reply with parent', 'Where did you read that?'),
        ('news', 'Company denies Cedar contract', 'Lumen Devices denied the earlier allegation that it had won the Cedar supply contract. It said it has signed no such contract.'),
        ('social', 'Conflicting current views', 'I love Lumen Devices products, but I think its shares are horribly overpriced. I still hold both views.'),
        ('news', 'Factory loan causes loss', 'Lumen Devices reported a $100 million loss caused by fees on the previously announced $2 billion chip-factory loan.'),
        ('social', 'Lighting question', 'How many lumens do I need for a desk lamp?'),
        ('news', 'Lab opens', 'Lumen Devices opened its Bristol research laboratory on Tuesday. No effect on company earnings was stated.'),
        ('social', 'Vague reaction', 'Great. Just great, Lumen Devices.'),
    ]
    sources = []
    for index, (channel, title, body) in enumerate(entries, 1):
        stamp = (datetime(2026, 10, 7, tzinfo=timezone.utc) + timedelta(minutes=index)).isoformat()
        passages, omitted = source_passages(title, body)
        source = dict(id=f'authored-batch-{index:02d}', label=f'item_{index}', channel=channel,
                      title=title, text=body, passages=passages, omitted_fragment_count=omitted,
                      publisher='Authored evaluation', published_at=stamp, available_at=stamp,
                      content_hash=sha256((title+body).encode()).hexdigest(),
                      url=f'https://example.invalid/batch-control/{index}')
        if channel == 'social':
            source.update(platform='reddit', social_kind='comment', discovery_match='direct',
                          post_key=f'authored:{index}', author_hash=f'authored-author-{index}')
        sources.append(source)
    sources[5]['conversation'] = dict(
        result_id='authored-parent', post_id=sources[5]['id'], parent_key='authored-parent-key',
        parent_type='comment', title='Parent', body='Lumen Devices has the best chips. I love this company.',
        url='https://example.invalid/batch-control/parent', published_at='2026-10-07T00:00:00+00:00',
        checked_at='2026-10-08T00:00:00+00:00', omitted_fragment_count=0,
        passages=[{'id':'p1','quote':'Lumen Devices has the best chips. I love this company.'}])
    return dict(experiment_authored=True, context_policy=sentiment_context.POLICY,
                reporting_policy=reporting_basis.POLICY, comparison_sources=[],
                instrument_id='authored-only', company={'symbol':'LUMD','name':'Lumen Devices'},
                cutoff='2026-10-08T00:00:00+00:00', sources=sources)
