"""Retained source/label replay; arrival subsets and fault clocks are authored.

This helper is restricted to disposable test databases. It does not claim the
model classified each projected subset independently or replay real arrivals.
"""

from copy import deepcopy
from datetime import datetime, timezone, timedelta
import json
import os
from pathlib import Path
from uuid import uuid4

from psycopg import sql
from psycopg.types.json import Jsonb
from thesis.config import DATA
from thesis.db import transaction, one
from thesis.providers import ledger
from thesis.research import sentiment
from thesis.research.sec.service import add_company
from thesis.monitoring import news_watch, watch_history


def load(symbol):
    path = os.environ.get("THESIS_WATCH_REPLAY_CORPUS")
    if not path:
        raise ValueError("Choose a retained replay corpus; no source fetching occurs.")
    return json.loads((Path(path) / "frozen.json").read_text())["packets"][symbol]


class Replay:
    def __init__(self, owner, symbol="GOOGL"):
        assert DATA.parent == Path("/private/tmp") and DATA.name.startswith(
            ("thesis-test-", "thesis-browser-")
        ), "Retained replay requires a disposable database."
        self.owner = owner
        self.case = load(symbol)
        self.iid = add_company(symbol)["instrument_id"]
        assert self.iid == self.case["packet"]["instrument_id"]
        self.clock = datetime.now(timezone.utc)
        with transaction(admin=True) as c:
            c.execute(
                "INSERT INTO sources VALUES('finnhub-news','Finnhub company news','finnhub-pitch') ON CONFLICT DO NOTHING"
            )
            c.execute(
                "INSERT INTO instrument_sources VALUES(%s,'finnhub-news') ON CONFLICT DO NOTHING",
                (self.iid,),
            )
            for table, records in self.case["tables"].items():
                for record in records:
                    c.execute(
                        sql.SQL(
                            "INSERT INTO {} SELECT * FROM jsonb_populate_record(NULL::{},%s) ON CONFLICT DO NOTHING"
                        ).format(sql.Identifier(table), sql.Identifier(table)),
                        (Jsonb(record),),
                    )
        # Exact previously paid response replay in the disposable ledger.
        packet = self.case["packet"]
        call = ledger.execute(
            "retained-watch-replay:" + str(uuid4()),
            sentiment.PROMPT,
            sentiment.request_for(packet),
            transport=lambda _: deepcopy(self.case["call"]["response_body"]),
        )
        assert sentiment.render(call, packet) == self.case["result"]
        self.call_id = call["id"]
        self.initial_budget = ledger.snapshot()
        self.snapshots = []

    def append(self, labels, hour):
        packet, result = deepcopy(self.case["packet"]), deepcopy(self.case["result"])
        packet["sources"] = [s for s in packet["sources"] if s["label"] in labels]
        assert {s["label"] for s in packet["sources"]} == set(labels)
        packet.pop("input_limits", None)
        cutoff = datetime.fromisoformat(self.case["packet"]["cutoff"]) + timedelta(
            minutes=hour
        )
        assert cutoff <= datetime.now(
            timezone.utc
        ), "Replay requires a past source cutoff."
        packet["cutoff"] = cutoff.isoformat()
        packet["replay_provenance"] = {
            "kind": "authored arrival subset of retained classified sources",
            "original_cutoff": self.case["packet"]["cutoff"],
            "original_call": self.case["call"]["id"],
        }
        selected = {s["id"] for s in packet["sources"]}
        references = selected | {s["id"] for s in packet["comparison_sources"]}
        result["items"] = [i for i in result["items"] if i["source_id"] in selected]
        result["coverage_links"] = [
            link
            for link in result["coverage_links"]
            if link["source_id"] in selected
            and link["reference_source_id"] in references
        ]
        result["summary"] = sentiment.summarize(
            result["items"],
            packet["sources"],
            result["coverage_links"],
            packet["comparison_sources"],
        )
        identity = str(uuid4())
        with transaction() as c:
            c.execute(
                "INSERT INTO sentiment_analyses VALUES(%s,%s,%s,%s,%s,%s,%s)",
                (
                    identity,
                    self.iid,
                    "authored-retained-arrival:" + identity,
                    self.call_id,
                    Jsonb(packet),
                    Jsonb(result),
                    datetime.now(timezone.utc),
                ),
            )
            row = one(c, "SELECT * FROM sentiment_analyses WHERE id=%s", (identity,))
            assert not sentiment.present(c, row)["withheld"]
        self.snapshots.append(row)
        return row

    def start(self, hour=0, **settings):
        news_watch.configure(
            self.owner,
            self.iid,
            True,
            now=datetime.now(timezone.utc) - timedelta(minutes=61),
            **settings,
        )

    def run(self, record, hour, *, analyzer=None, refresh=None, idea_analyzer=None):
        # Force only this disposable watch due. Actual start/completion and
        # lease clocks stay real; this is not an hour-long prospective trial.
        with transaction(self.owner) as c:
            c.execute(
                "UPDATE news_watches SET next_check_at=now()-interval '1 second' WHERE owner_id=%s AND instrument_id=%s AND enabled",
                (self.owner, self.iid),
            )
        assert news_watch.run_once(
            self.owner,
            market_refresh=refresh or (lambda _: None),
            social_refresh=lambda: None,
            analyzer=analyzer or (lambda _: {"id": str(record["id"])}),
            idea_analyzer=idea_analyzer,
        )
        return watch_history.history(self.owner, self.iid)["items"][0]

    def alerts(self):
        with transaction(self.owner) as c:
            return news_watch.list_alerts(c, self.owner)
