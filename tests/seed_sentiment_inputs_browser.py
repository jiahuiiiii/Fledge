"""Unanalysed authored news/replies, with an unchanged earlier mocked reading."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from thesis.config import DATA, OWNER

assert str(DATA).startswith("/private/tmp/thesis-browser-")
from thesis.research import sentiment, hackernews
from thesis.research.sec.service import add_company
from test_market import prepare, commit, news
from test_sentiment import provider, add_social
from test_hackernews import item, transport

iid = prepare(OWNER)
add_social(iid)
sentiment.generate(iid, transport=provider())
commit(
    iid,
    [
        news(
            id=44,
            url="https://example.test/unanalysed",
            headline="Microsoft introduces an authored product preview",
            summary="This new browser-fixture report has never received a sentiment label.",
        )
    ],
)
hackernews.refresh(
    iid,
    fetcher=transport(
        {
            "123": item(
                text="I wonder whether Microsoft pricing will change. This is an authored new reply."
            )
        }
    ),
)
apple = add_company("AAPL")["instrument_id"]
hackernews.refresh(
    apple,
    fetcher=transport(
        {
            "456": item(
                key="456",
                text="I use Apple products, but this authored post is only an opinion.",
            )
        }
    ),
)
print(
    "Current-source browser: new Microsoft news/HN text after one saved reading; Apple has raw HN text and no analysis. No live request."
)
