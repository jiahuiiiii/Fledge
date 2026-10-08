"""Only fictional daily bars in disposable browser storage."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from thesis.config import DATA

assert str(DATA).startswith("/private/tmp/thesis-browser-")
from thesis.research.sec.service import add_company
from thesis.research import price_history as ph
from test_price_history import payload
from thesis.db import transaction

ph.configured = lambda: True
iid = add_company("MSFT")["instrument_id"]
raw = payload(count=252)
q = raw["chart"]["result"][0]["indicators"]["quote"][0]
for i in range(252):
    value = 100 + i * 0.3 + (i % 7) * 0.4
    for name, change in (("open", -0.4), ("high", 2), ("low", -2), ("close", 0)):
        q[name][i] = str(value + change)
q["volume"][240] = None
ph.refresh(iid, fetcher=lambda *_: raw)
add_company("AAPL")
print("Authored daily-price fixture ready; no provider calls.")
