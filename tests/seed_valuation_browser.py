"""Authored statement and multiple inputs for an isolated browser journey."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from thesis.config import DATA

assert str(DATA).startswith("/private/tmp/thesis-browser-")
from test_performance import financial_bundle
from test_sec_fundamentals import apply
from thesis.research.sec.service import add_company
from thesis.research.multiples import refresh

b = financial_bundle()
for spec in b["companyfacts"]["facts"]["us-gaap"].values():
    for f in spec["units"]["USD"]:
        f["val"] *= 1000000000
msft = add_company("MSFT")["instrument_id"]
apply(msft, b)
aapl = add_company("AAPL")["instrument_id"]
for iid, symbol in ((msft, "MSFT"), (aapl, "AAPL")):
    refresh(
        iid,
        fetcher=lambda endpoint, params: {
            "symbol": params["symbol"],
            "metric": {"peTTM": 28.5, "psTTM": 11.2},
        },
    )
from thesis.research import analyst_targets
from test_analyst_targets import page as target_fixture
for iid in (msft, aapl):
    analyst_targets.refresh(iid, fetcher=target_fixture)
print("Authored statement, multiple and target fixtures ready; no external requests.")
