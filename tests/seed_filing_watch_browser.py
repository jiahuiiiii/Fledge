"""Authored journal/source fixture in disposable browser DB; watches remain off."""

import sys
from pathlib import Path
from datetime import timedelta
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from thesis.config import DATA, OWNER

assert str(DATA).startswith("/private/tmp/thesis-browser-")
from thesis.db import transaction
from thesis.research.sec.service import add_company
from thesis.monitoring import filing_watch as watch
from test_performance import financial_bundle
from test_sec_fundamentals import apply

iid = add_company("MSFT")["instrument_id"]
start = watch.utcnow()
result = apply(iid, financial_bundle())
watch.configure(OWNER, iid, False)
with transaction(OWNER) as c:
    for n in range(22):
        check = uuid4()
        when = start - timedelta(seconds=22 - n)
        c.execute(
            "INSERT INTO filing_watch_checks VALUES(%s,%s,%s,%s,%s,%s)",
            (check, OWNER, iid, when, when, when + timedelta(minutes=3)),
        )
        watch._result(
            c,
            OWNER,
            check,
            "failed" if n == 21 else "unchanged",
            watch.utcnow(),
            None if n == 21 else result["source_check_id"],
        )
print(
    "Authored filing history prepared; 22 records, no scheduled watch or external request."
)
