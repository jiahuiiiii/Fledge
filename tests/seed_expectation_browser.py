"""Disposable authored expectation history and cached extraction; no live calls."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from thesis.config import DATA, OWNER

assert str(DATA).startswith("/private/tmp/thesis-browser-")
from test_expectations import setup, response
from test_market import commit, news
from thesis.research import expectations as E

iid = setup(OWNER)
first = E.generate(iid, transport=response)
commit(
    iid,
    [
        news(
            id=803,
            headline="Microsoft analyst revision",
            summary="Harbor Research raised its Microsoft revenue estimate. No new figure or target period was stated.",
            url="https://example.test/analyst-revision",
        )
    ],
)


def changed(body):
    import json

    raw = response(body)
    result = json.loads(raw["output"][0]["content"][0]["text"])
    p = json.loads(body["input"][1]["content"])
    s = next(s for s in p["sources"] if s["title"] == "Microsoft analyst revision")
    q = next(q for q in s["passages"] if q["quote"].startswith("Harbor Research"))
    result["items"].append(
        dict(
            source_id=s["id"],
            category="analyst_view",
            summary="The report says Harbor Research raised its Microsoft revenue estimate, without giving the new amount.",
            passages=[q["id"]],
            attribution_quote="Harbor Research",
            value_quote=None,
            horizon_quote=None,
            change="raised",
            change_quote="raised its Microsoft revenue estimate",
        )
    )
    raw["output"][0]["content"][0]["text"] = json.dumps(result)
    return raw


E.generate(iid, transport=changed)
print(
    "Authored expectations fixture: two immutable readings, management outlook and analyst revision, exact cached extraction; no paid calls."
)
