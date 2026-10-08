"""Synthetic SEC-shaped inputs, only for a disposable browser-test instance."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from thesis.config import DATA

assert str(DATA).startswith(
    "/private/tmp/thesis-browser-"
), "Test seeding cannot touch the app database"
from test_sec_fundamentals import bundle, apply
from thesis.research.sec.service import add_company

company = add_company("MSFT")
apply(company["instrument_id"], bundle(annual=True, revenue=130, prior=100, income=30))
print("Seeded synthetic SEC-shaped browser evidence in disposable storage")
