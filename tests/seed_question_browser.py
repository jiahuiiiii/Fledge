"""Fictional question answers for browser checks; no external source or AI requests."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from thesis.config import DATA, OWNER

assert str(DATA).startswith("/private/tmp/thesis-browser-")
from test_conversation import setup, fetcher
from test_sentiment import add_social
from test_research_answers import ask, QUESTION
from thesis.research.answers import Ask, generate
from test_research_answers import response
from thesis.db import transaction
from thesis.research import conversation
from test_answer_context import QUESTION as CONTEXT_QUESTION, contextual_response

iid, post, child, parent = setup(OWNER)
add_social(iid)
conversation.collect(post["id"], fetcher=fetcher(child, parent, []))
def mislabeled_opinion(body):
    import json
    raw = response(body)
    result = json.loads(raw['output'][0]['content'][0]['text'])
    # Reproduce the actual model's news-as-social label error; the UI must use source metadata.
    result['evidence'][0]['kind'] = 'social_opinion'
    raw['output'][0]['content'][0]['text'] = json.dumps(result)
    return raw

first = generate(OWNER, iid, Ask(question=QUESTION), transport=mislabeled_opinion)
follow = "What company disclosure would establish a signed contract?"
second = generate(
    OWNER, iid, Ask(question=follow, parent_id=first["id"]), transport=response
)
generate(OWNER, iid, Ask(question=CONTEXT_QUESTION), transport=contextual_response)
# The exact initial and follow-up requests are already cached; browser clicks never call a provider.
