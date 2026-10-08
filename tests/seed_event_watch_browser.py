"""Authored reports/model responses only, in the disposable browser database."""

import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from thesis.config import DATA, OWNER

assert str(DATA).startswith("/private/tmp/thesis-browser-")
from test_event_watch import setup, select, run
from test_event_conditions import event
from test_integration import payload, drain
from test_sec_fundamentals import apply, bundle
from thesis import service
from thesis.models import SaveIdea
from thesis.monitoring import news_watch

today = datetime.now(timezone.utc).date().isoformat()
iid, saved, article = setup(OWNER, window_start=today, deadline=today)
select(OWNER, iid, saved)
run(OWNER, iid, saved)
drain(OWNER)
# A different numerical filing outside the report window leaves eligible event
# sources identical, and the later assessment stores its reuse proof.
apply(iid, bundle(annual=True, revenue=110))
drain(OWNER)
news_watch.configure(OWNER, iid, True, now=datetime.now(timezone.utc))
p = payload(revision=1, conditions=False).model_dump() | dict(
    instrument_id=iid, events=[event(window_start=today, deadline=today, role="risk")]
)
service.save_idea(OWNER, SaveIdea(**p))
drain(OWNER)
print(
    "Authored event watch, reused source interpretation and paused changed revision prepared. Next source check is one hour away; no live HTTP or model call."
)
