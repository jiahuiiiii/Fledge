"""Synthetic market evidence, never the user's real data or keys."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from thesis.config import DATA

assert str(DATA).startswith("/private/tmp/thesis-browser-")
import json
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from psycopg.types.json import Jsonb
from thesis.db import transaction
from thesis.research import market, market_brief
from thesis.research.sec.service import add_company
from test_sec_fundamentals import apply, bundle

company = add_company("MSFT")["instrument_id"]
apply(company, bundle(annual=True, revenue=130, prior=100, income=30))
now = datetime.now(timezone.utc)
items = [
    dict(
        id=i,
        headline=f"Synthetic report {i}: Microsoft has not confirmed the proposed contract.",
        summary="This is authored browser-test evidence. The company has not confirmed the reported contract.",
        related="MSFT",
        datetime=int((now - timedelta(hours=i + 1)).timestamp()),
        source="Synthetic Wire",
        url=f"https://example.test/synthetic-{i}",
    )
    for i in range(7)
]
# The standalone market journey exercises the shared-brief omission disclosure.
# The idea journey imports this setup and supplies its own corrected fragment.
fragment_fixture = __name__ == "__main__"
if fragment_fixture:
    items[0]["summary"] += " An unfinished market fixture mentions future terms..."
articles, rejected = market.normalize_news(items, "MSFT", now)
with transaction(source=True) as conn:
    market.collection_lock(conn)
    market.commit_news(conn, company, articles, rejected, now)
    q = market.normalize_quote(
        dict(c=110, pc=100, o=105, h=112, l=103, t=int(now.timestamp())), now
    )
    conn.execute(
        "INSERT INTO market_quotes VALUES(%s,%s,%s,%s)",
        (uuid4(), company, Jsonb(q), now),
    )
    conn.execute(
        "INSERT INTO market_refresh_state(instrument_id,last_attempt_at,completed_at,news_count,excluded_count) VALUES(%s,%s,%s,7,0)",
        (company, now, now),
    )


def provider(body):
    packet = json.loads(body["input"][1]["content"])
    if fragment_fixture:
        assert packet["omitted_fragment_count"] == 1
        assert "unfinished market fixture" not in json.dumps(packet)
    s = packet["sources"][0]
    point = dict(
        kind="uncertainty",
        title="A reported contract remains unconfirmed",
        text="The supplied synthetic report does not establish that the contract was signed.",
        citations=[dict(source_id=s["id"], quote=s["text"])],
    )
    return dict(
        id="resp_synthetic_browser",
        model=body["model"],
        service_tier="default",
        status="completed",
        usage=dict(input_tokens=100, output_tokens=80),
        output=[
            dict(
                type="message",
                content=[
                    dict(type="output_text", text=json.dumps(dict(points=[point])))
                ],
            )
        ],
    )


market_brief.generate(company, transport=provider)
print("Synthetic market workspace seeded; no external calls")
