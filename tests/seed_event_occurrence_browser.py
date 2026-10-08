"""Authored occurrence-date reading in the isolated browser database."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from thesis.config import DATA, OWNER

assert str(DATA).startswith("/private/tmp/thesis-browser-")
from test_event_watch import setup, select, run
from test_event_occurrence import result
from test_market import commit
from test_integration import drain
from thesis import service
from thesis.db import transaction
from thesis.research import event_review as E
from thesis.monitoring import news_watch

iid, sv, article = setup(
    OWNER,
    date_basis="event_occurrence",
    window_start="2026-09-01",
    deadline="2026-09-30",
)
article["summary"] = (
    "Authored fixture: the named product became generally available on September 3, 2026."
)
commit(iid, [article])
select(OWNER, iid, sv)


def transport(_):
    with transaction(OWNER) as c:
        p = E.prepare(
            c, OWNER, sv["version_id"], service.state(OWNER, iid)["snapshot_id"]
        )
    return result(p)


run(OWNER, iid, sv, transport=transport)
drain(OWNER)
news_watch.configure(OWNER, iid, False)
print("Authored dated event and its alert prepared; watch stopped, no live calls.")
