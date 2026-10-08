"""Authored social platform cases, mocked AI, disposable database only."""

import seed_sentiment_browser
from seed_sentiment_browser import iid
from thesis.research import hackernews, sentiment
from test_hackernews import transport, item
from test_sentiment import provider

hackernews.refresh(
    iid,
    fetcher=transport(
        {
            str(k): item(
                str(k), f"Microsoft software frustrates me for the authored reason {k}."
            )
            for k in range(1, 6)
        }
    ),
)
sentiment.generate(iid, transport=provider("negative"))
