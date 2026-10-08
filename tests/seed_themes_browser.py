"""Two exact authored source samples; mock responses only, disposable database."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from thesis.config import DATA, OWNER

assert str(DATA).startswith("/private/tmp/thesis-browser-")
from test_discussion_themes import setup, response, legacy_fixture
from test_market import commit, news
from test_sentiment import provider
from thesis.research import discussion_themes as D, sentiment, conversation, social
from thesis.db import transaction
from datetime import datetime, timezone

iid, aid = setup(OWNER)
legacy_fixture(iid, D.generate(iid, aid, transport=response))
commit(
    iid,
    [
        news(
            id=810,
            headline="Microsoft later software report",
            summary="Microsoft users report a changed product experience.",
            url="https://example.test/later",
        )
    ],
)
with transaction() as c:
    post = next(p for p in social.documents(c, iid, datetime.now(timezone.utc)) if p["platform"] == "hackernews")
child = dict(id=int(post["post_key"][3:]), type="comment", parent=99, text=post["body"], time=int(post["published_at"].timestamp()))
parent = dict(id=99, type="comment", parent=98, text="Authored parent: I think Microsoft software is reliable. Do you agree?", time=child["time"]-60)
conversation.collect(post["id"], fetcher=lambda kind, key, now: child if key == str(child["id"]) else parent)
a = sentiment.generate(iid, transport=provider())
D.generate(iid, a["id"], transport=response)
print(
    "Three authored theme readings including a legacy format and one with saved parent context, using mocked models; all watches off."
)
