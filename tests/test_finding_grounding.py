"""Cited-source boundaries; model interpretation is evaluated separately."""
from copy import deepcopy
import json
import pytest
from thesis.db import transaction
from thesis.research import answers as A, sentiment as S
from test_market import prepare
from test_sentiment import add_social
from test_research_answers import response
from test_sentiment_context import with_context


@pytest.mark.parametrize('kind', ['reported', 'social_opinion', 'interpretation', 'contrary'])
def test_social_claim_cannot_be_laundered_by_adding_a_news_citation(owner, kind):
    iid = prepare(owner)
    add_social(iid)
    with transaction(owner) as c:
        packet = A.prepare(c, owner, iid, A.Ask(question='What is said about Microsoft margins?'))
    def change(result, wire):
        social = next(s for s in wire['sources'] if s['channel'] == 'social')
        news = next(s for s in wire['sources'] if s['channel'] == 'news')
        result['evidence'] = [dict(
            kind=kind, text='A social poster expresses concern about Microsoft margins.',
            citations=[dict(source_id=s['id'], passage_id=s['passages'][-1]['id']) for s in [social, news]],
            context_citations=[],
        )]
    call = dict(response_body=response(A.request_for(packet), change))
    if kind == 'reported':
        with pytest.raises(ValueError, match='Social opinion'):
            A.render(call, packet)
    else:
        rendered = A.render(call, packet)
        assert rendered['evidence'][0]['kind'] == kind
        assert len(rendered['evidence'][0]['citations']) == 2


def test_sentiment_platform_input_is_original_metadata_not_an_extra_vote(owner):
    iid, post, child, parent = with_context(owner)
    add_social(iid)
    with transaction(owner) as c:
        packet = S.prepare(c, iid)
    original = deepcopy(packet)
    wire = json.loads(S.request_for(packet)['input'][1]['content'])
    lookup = {s['id']: s for s in packet['sources']}
    assert len(wire['sources']) == len(packet['sources'])
    for source in wire['sources']:
        assert source.get('platform') == lookup[source['id']].get('platform')
        assert 'author_hash' not in source and 'content_hash' not in source
    assert {s.get('platform') for s in wire['sources']} == {None, 'reddit', 'hackernews'}
    assert packet == original
