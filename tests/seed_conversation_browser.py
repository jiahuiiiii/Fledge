"""Authored conversation context, mocked acquisition/model, disposable DB only."""

import seed_social_platforms_browser
from seed_social_platforms_browser import iid
from thesis.research import conversation, social
from thesis.db import transaction
from datetime import datetime

with transaction() as c:
    posts = [
        p
        for p in social.documents(c, iid, datetime.now().astimezone())
        if p["platform"] == "hackernews"
    ]
for p in posts:
    child = dict(
        id=int(p["post_key"][3:]),
        parent=999,
        type="comment",
        text=p["body"],
        time=int(p["published_at"].timestamp()),
    )
    parent = dict(
        id=999,
        type="comment",
        text="Authored parent: I think Microsoft pricing is fair. Do you agree?",
        time=child["time"] - 60,
        parent=998,
    )
    conversation.collect(
        p["id"],
        fetcher=lambda kind, key, now: child if key == str(child["id"]) else parent,
    )
print("Authored, opposing parent/comment views retained separately; no external calls.")

from thesis.research import sentiment
from test_sentiment import provider

reading = sentiment.generate(iid, transport=provider("negative"))
print(
    "Context-aware authored sample uses a mocked classifier; parents do not add votes."
)

from thesis.config import OWNER
from thesis.research import idea_alerts
from test_idea_alerts import provider as private_provider

idea_alerts.generate(OWNER, iid, reading["id"], transport=private_provider())
print("Authored private connection preserves the same saved parents; model output is mocked.")
