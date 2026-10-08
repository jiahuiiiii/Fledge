"""Authored financial statement fixture; never installs into the main account."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from thesis.config import DATA

assert str(DATA).startswith("/private/tmp/thesis-browser-")
from test_performance import financial_bundle
from test_sec_fundamentals import apply
from thesis.research.sec.service import add_company

apply(add_company("MSFT")["instrument_id"], financial_bundle())
print("Synthetic annual/quarterly financial statements prepared; no external calls.")
