"""Authored recurring checks, stored using mocked provider replies only."""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from thesis.config import DATA, OWNER

assert str(DATA).startswith("/private/tmp/thesis-browser-")
from thesis import service
from thesis.db import transaction
from thesis.models import SaveIdea
from thesis.providers import ledger
from thesis.research import event_review as E
from thesis.monitoring.event_windows import shift
from test_market import prepare, commit, news
from test_event_conditions import event
from test_event_occurrence import result
from test_integration import payload, drain

iid = prepare(OWNER)
today = datetime.now(timezone.utc).date()
first = shift(today.replace(day=1), -3)
last = shift(first, 3) - timedelta(days=1)
event_date = (first + timedelta(days=2)).isoformat()
commit(
    iid,
    [
        news(
            headline="Authored recurring launch report",
            summary=f"Authored fixture: the product launched on {event_date}. This is a later report of the earlier launch.",
        )
    ],
)
e = event(
    description="A new product launch in each window",
    date_basis="event_occurrence",
    window_start=first.isoformat(),
    deadline=last.isoformat(),
    repeat_months=3,
    repeat_count=3,
)
sv = service.save_idea(
    OWNER,
    SaveIdea(
        **(payload(conditions=False).model_dump() | dict(instrument_id=iid, events=[e]))
    ),
)
drain(OWNER)
sid = service.state(OWNER, iid)["snapshot_id"]
for selected in ({e["condition_id"]: 1}, None):
    with transaction(OWNER) as c:
        p = E.prepare(c, OWNER, sv["version_id"], sid, event_periods=selected)
    E.generate(
        OWNER,
        sv["version_id"],
        sid,
        event_periods=selected,
        transport=lambda _, packet=p: result(packet, event_date),
    )
    drain(OWNER)
print(
    "Authored previous/current recurring checks prepared. Current window is unconfirmed; old window has its own dated confirmation. No watch or live request."
)
