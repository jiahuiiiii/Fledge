"""Recorded scheduled attempts with fictional source/model adapters; no paid calls."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from thesis.config import DATA, OWNER

assert str(DATA).startswith("/private/tmp/thesis-browser-")
from datetime import datetime, timezone, timedelta
from thesis.monitoring import news_watch
from thesis.research import sentiment
from thesis.db import transaction
from test_market import prepare, commit, news
from test_sentiment import provider, add_social

iid = prepare(OWNER)
add_social(iid)


# First run creates baseline; second run produces one grouped update.
def due(**kwargs):
    news_watch.configure(
        OWNER,
        iid,
        True,
        now=datetime.now(timezone.utc) - timedelta(minutes=61),
        **kwargs,
    )


def check(**kwargs):
    return news_watch.run_once(
        OWNER,
        market_refresh=lambda _: None,
        social_refresh=lambda: None,
        analyzer=lambda i: sentiment.generate(i, transport=provider()),
        **kwargs,
    )


due()
check()
commit(
    iid,
    [
        news(
            id=3,
            url="https://example.test/change",
            headline="Microsoft reports a margin decline",
            summary="Authored browser report: Microsoft operating margins declined.",
        )
    ],
)
due()
check()
with transaction(source=True) as c:
    c.execute(
        "UPDATE social_refresh_state SET error='Authored feed failure' WHERE feed='stocks'"
    )
due()
check()
due()


def failed(_):
    raise ValueError("Authored fetch error")


news_watch.run_once(OWNER, market_refresh=lambda _: None, social_refresh=lambda: None, analyzer=failed)
due()


def lost(_):
    raise KeyboardInterrupt()


try:
    news_watch.run_once(OWNER, market_refresh=lost)
except KeyboardInterrupt:
    pass
from test_hackernews import hn, item, transport
from test_conversation import fetcher

child = item()
hn.refresh(iid, fetcher=transport({"123": child}))
parent = dict(
    id=99,
    type="comment",
    text="Microsoft pricing deserves more investigation.",
    time=child["time"] - 60,
)
due(include_context=True)
check(context_fetcher=fetcher(child, parent, []))
news_watch.configure(OWNER, iid, False, include_context=False)
print(
    "Six recorded fictional checks: baseline, published update, partial coverage, failure, missing completion and original-parent context. Watch disabled."
)
