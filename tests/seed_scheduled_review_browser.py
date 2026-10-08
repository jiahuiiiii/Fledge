"""Authored saved-review examples with an explicit simulated clock; no live calls."""

import seed_digest_browser  # noqa: F401 — installs the authored prerequisite fixture
from datetime import datetime, timedelta, timezone
from thesis.config import OWNER, DATA
from thesis.monitoring import review_schedule as R

assert str(DATA).startswith("/private/tmp/thesis-browser-")
due = (datetime.now(timezone.utc) + timedelta(minutes=2)).replace(
    second=0, microsecond=0
)
args = (due.weekday(), due.hour * 60 + due.minute, "UTC")
R.configure(OWNER, True, *args, now=due - timedelta(days=1))
assert R.run_once(OWNER, now=due)
assert R.run_once(OWNER, now=due + timedelta(days=7))
R.configure(OWNER, False, *args, now=due + timedelta(days=7))
assert len(R.history(OWNER)["items"]) == 2
print(
    "Authored weekly review fixture: one populated and one quiet week; simulated future clock, schedule left off."
)
