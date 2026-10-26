"""Migration 071: each reading's cutoff in its own indexed column; disposable database only."""
from copy import deepcopy
from datetime import datetime, timedelta
from uuid import uuid4

import psycopg
import pytest
from psycopg.types.json import Jsonb

from thesis.db import one, rows, transaction
from thesis.monitoring import news_watch
from thesis.research import idea_alerts, sentiment, sentiment_history as history
from test_sentiment_history import original, variant


def saved_later_with_earlier_cutoff(iid, identity):
    """Saved after every other reading, but assessed at an earlier cutoff."""
    with transaction() as c:
        source = history.record(c, iid, identity)
    packet = deepcopy(source["packet"])
    packet["cutoff"] = (datetime.fromisoformat(packet["cutoff"]) - timedelta(minutes=5)).isoformat()
    new = str(uuid4())
    with transaction() as c:
        c.execute(
            "INSERT INTO sentiment_analyses VALUES(%s,%s,%s,%s,%s,%s,%s)",
            (new, iid, "authored-earlier-cutoff:" + new, source["call_id"], Jsonb(packet),
             Jsonb(source["result"]), source["created_at"] + timedelta(hours=1)),
        )
    return new


def test_column_mirrors_the_packet_and_latest_still_means_latest_cutoff(owner):
    iid, first = original(owner)
    later = variant(iid, first["id"], minutes=5)
    earlier = saved_later_with_earlier_cutoff(iid, first["id"])
    with transaction(admin=True) as c:
        saved = rows(c, "SELECT id,cutoff,packet->>'cutoff' packet_cutoff FROM sentiment_analyses WHERE instrument_id=%s", (iid,))
        assert len(saved) == 3
        assert all(r["cutoff"] == datetime.fromisoformat(r["packet_cutoff"]) for r in saved)
        assert sentiment.latest(c, iid)["id"] == later
        assert str(idea_alerts.latest_analysis(c, iid)["id"]) == later
    assert [s["id"] for s in history.history(iid)["items"]] == [later, first["id"], earlier]
    page = history.history(iid, before=later)
    assert [s["id"] for s in page["items"]] == [first["id"], earlier]


def test_saved_readings_stay_immutable(owner):
    iid, first = original(owner)
    with pytest.raises(psycopg.Error):
        with transaction(admin=True) as c:
            c.execute("UPDATE sentiment_analyses SET cutoff=now() WHERE id=%s", (first["id"],))


@pytest.mark.parametrize("sql", [
    sentiment.LATEST_SQL,
    "SELECT * FROM sentiment_analyses WHERE instrument_id=%s AND (cutoff,created_at,id)<(now(),now(),gen_random_uuid()) ORDER BY cutoff DESC,created_at DESC,id DESC LIMIT 21",
])
def test_latest_and_history_lookups_use_the_index(owner, sql):
    iid, _ = original(owner)
    with transaction(admin=True) as c:
        c.execute("SET LOCAL enable_seqscan=off")
        plan = "\n".join(r["QUERY PLAN"] for r in rows(c, "EXPLAIN " + sql, (iid,)))
    assert "sentiment_by_cutoff" in plan and "Sort" not in plan.split("\n")[0]


def test_every_latest_lookup_shares_one_query():
    import inspect
    from thesis.research import sentiment_inputs

    for module in (sentiment, sentiment_inputs, idea_alerts, news_watch):
        source = inspect.getsource(module)
        assert "packet->>'cutoff')::timestamptz DESC" not in source, module.__name__
