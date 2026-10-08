"""Authored correction demonstration in disposable storage, never a live event."""

import sys
from pathlib import Path
from datetime import timedelta

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from thesis.config import DATA, OWNER

assert str(DATA).startswith("/private/tmp/thesis-browser-")
from reporting_update_fixture import begin, acquire, run
from thesis.monitoring import news_watch
from thesis.db import transaction

iid, now = begin(OWNER, due=False)
acquire(iid)
assert run(OWNER, now + timedelta(hours=1))
acquire(iid, clarification=True)
assert run(OWNER, now + timedelta(hours=2))
news_watch.configure(OWNER, iid, False)
with transaction(OWNER) as c:
    alerts = news_watch.list_alerts(c, OWNER)
assert len(alerts) == 2
assert alerts[0]["payload"]["coverage_links"][0]["relation"] == "contradicts"
print(
    "Authored reporting sequence: original adverse report, neutral clarification, two alerts, watch stopped; no external calls."
)
