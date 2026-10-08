"""Replay saved actual public filings into disposable storage; no source/model calls."""

import sys, os, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from thesis.config import DATA

assert str(DATA).startswith("/private/tmp/thesis-browser-")
from thesis.research.sec.service import add_company, refresh

corpus = Path(os.environ["THESIS_EXPANDED_CORPUS"])
for symbol in ("NVDA", "AMZN", "META"):
    bundle = json.loads((corpus / (symbol + "-bundle.json")).read_text())
    refresh(add_company(symbol)["instrument_id"], fetcher=lambda _, b=bundle: b)
print(
    "Replayed saved actual NVIDIA/Amazon/Meta public SEC bundles; no new retrieval or paid calls."
)
