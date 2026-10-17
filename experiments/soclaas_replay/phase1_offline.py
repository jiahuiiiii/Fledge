"""Replay frozen requests/responses through production validation, without DB or HTTP.

Usage: .venv/bin/python experiments/soclaas_replay/phase1_offline.py OUTPUT.json
Only model-visible evidence can be reconstructed from these archives. Missing
historical price captures remain unknown; no current database evidence is added.
"""
import hashlib
import json
import os
from pathlib import Path
import sys

if __name__ == "__main__":
    os.environ["THESIS_TEST_OFFLINE"] = "true"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from thesis.research import sentiment, reporting_basis, sentiment_guards  # noqa: E402

MODELS = {
    "Opus": "opus", "Sonnet": "claude-sonnet-5-5", "Haiku": "claude-haiku-5-5",
    "GPT-5.5": "gpt-5.5-2026-04-23", "GPT-5.4": "gpt-5.4-2026-03-05",
}


def packet_from_request(body):
    value = json.loads(body["input"][1]["content"])
    # The frozen request contains exact passages, IDs, publication times and
    # parent evidence. Restore only validator metadata omitted from the wire.
    for source in value["sources"] + value.get("comparison_sources", []):
        source["text"] = " ".join(p["quote"] for p in source["passages"] if p["id"] != "p0")
        source["content_hash"] = hashlib.sha256(source["text"].encode()).hexdigest()
        context = source.get("conversation")
        if context:
            context.update(result_id="offline-parent", title="", body="", url="",
                           checked_at=source["available_at"])
    return dict(value, reporting_policy=reporting_basis.POLICY,
                guard_policy=sentiment_guards.POLICY)


def replay(paths):
    rows = []
    repaired = total = passed = 0
    for request, response in paths:
        body = json.loads(request.read_text())
        p = packet_from_request(body)
        total += len(p["sources"])
        call = dict(request_body=body, response_body=json.loads(response.read_text()))
        try:
            result = sentiment.render(call, p)
        except ValueError as exc:
            cap = str(exc) == "Too many sentiment items need repair in this batch."
            count = sentiment.render(call, p, enforce_repair_limit=False)["repairs"]["repaired"] if cap else 0
            repaired += count
            rows.append(dict(batch=len(rows), passed=False, error=type(exc).__name__, repaired=count,
                             # Error categories only; no provider text or source identities.
                             repair_limit=cap))
        else:
            count = result["repairs"]["repaired"]
            repaired += count
            passed += 1
            rows.append(dict(batch=len(rows), passed=True, repaired=count))
    return dict(batches=len(rows), passed=passed, items=total,
                repaired_items=repaired,
                repaired_percent=round(100*repaired/max(1,total),3),
                target_passed=passed == len(rows) and repaired/max(1,total) <= .05,
                results=rows)


def main(output):
    meta = ROOT / ".local/live-tests/fair-meta-20261016/run"
    avgo = ROOT / ".local/live-tests/soclaas-avgo-20261016/run15"
    report = dict(paid_cost_usd=0, META={}, AVGO={},
                  limitations=["AVGO has saved Opus responses only for the five target models.",
                               "Price captures absent from frozen requests remain unknown.",
                               "No live checks or semantic correctness are measured here."])
    for name, suffix in MODELS.items():
        paths = [(p,p.with_name(p.name.replace("request.json",suffix+".json")))
                 for p in sorted(meta.glob("*.request.json"))]
        report["META"][name] = replay(paths)
        if name == "Opus":
            report["AVGO"][name] = replay([(p,p.with_name(p.name.replace("request.json","claude.json")))
                                          for p in sorted(avgo.glob("*.request.json"))])
        else:
            report["AVGO"][name] = dict(batches=0,passed=0,target_passed=False,status="missing_saved_responses")
    Path(output).write_text(json.dumps(report, indent=2)+"\n")
    for corpus in ("META","AVGO"):
        for model, stats in report[corpus].items():
            print(corpus,model,stats["passed"],"/",stats["batches"],
                  "repairs",stats.get("repaired_items"),"target",stats["target_passed"])


if __name__ == "__main__":
    main(sys.argv[1])
