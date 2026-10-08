"""Large complete authored sources; isolated mocked-provider browser flow."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from thesis.config import DATA, OWNER

assert str(DATA).startswith("/private/tmp/thesis-browser-")
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from psycopg.types.json import Jsonb
from thesis.db import transaction
from thesis.research import sentiment
from test_market import prepare, commit, news
from test_sentiment import add_social, feed, provider
from test_sentiment_history import variant

iid = prepare(OWNER)
now = datetime.now(timezone.utc)
commit(
    iid,
    [
        news(
            id=700 + i,
            url=f"https://example.test/large/{i}",
            headline=f"Microsoft authored report number {i}",
            summary=f"Microsoft research fixture {i} "
            + ("complete source wording " * 65)
            + ".",
            datetime=int((now - timedelta(minutes=30 + i)).timestamp()),
        )
        for i in range(24)
    ],
)
feeds = [
    feed(
        title=f"Microsoft authored opinion {i}",
        body=f"I dislike Microsoft example {i} "
        + ("complete opinion wording " * 65)
        + ".",
        key="limit" + str(i),
        date=(now - timedelta(minutes=2 + i)).isoformat(),
    )
    for i in range(8)
]
body = (
    feeds[0].split(b"<entry>")[0]
    + b"".join(
        b"<entry>" + f.split(b"<entry>", 1)[1].split(b"</feed>")[0] for f in feeds
    )
    + b"</feed>"
)
add_social(iid, body)
with transaction() as c:
    p = sentiment.prepare(c, iid)
assert p.get(
    "input_limits"
), "Authored source fixture must actually exceed the request bound"
current = sentiment.generate(iid, transport=provider())
earlier = current["id"]
later = variant(iid, earlier, minutes=1)
with transaction(OWNER) as c:
    c.execute(
        "INSERT INTO research_alerts VALUES(%s,%s,%s,'new_reporting',%s,%s,NULL,%s,now())",
        (
            uuid4(),
            OWNER,
            iid,
            later,
            earlier,
            Jsonb(
                dict(
                    reason="Authored source-limit display fixture.",
                    items=current["items"][:1],
                )
            ),
        ),
    )
print("Bounded source browser seeded:", p["input_limits"], len(p["sources"]))
