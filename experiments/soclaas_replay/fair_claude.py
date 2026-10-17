"""Evaluation only: rerun the exact fair_compare batches on other Claude models.

Sends the exact saved request bodies (only the model name changes), so every model
gets byte-identical inputs. Calls go through the app's ledger with experiment
request keys. Answers are judged by replay.check, which applies the same rules
sentiment.render enforced on this run (one label per source, own passages, tone vs
basis, relevance vs direction, news-only event fields, event passages vs kind). Nothing is saved as a
reading, alert or watch result.

Usage: .venv/bin/python experiments/soclaas_replay/fair_claude.py RUN_DIR MODEL [MODEL ...]
"""
import hashlib
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent))
from thesis.providers import ledger  # noqa: E402
from thesis.research import sentiment  # noqa: E402
from fair_compare import TAG  # noqa: E402
from replay import check  # noqa: E402
import time  # noqa: E402



def run(model, index, body):
    body = dict(body, model=model)
    key = f"{TAG}:{model}:{hashlib.sha256(ledger.canonical(body).encode()).hexdigest()}"
    started = time.monotonic()
    try:
        call = ledger.execute(key, sentiment.PROMPT, body)
    except Exception as exc:  # noqa: BLE001
        return dict(error=f"{type(exc).__name__}: {str(exc)[:300]}", seconds=round(time.monotonic() - started, 1))
    usage = call["response_body"].get("usage") or {}
    text = sentiment.response_text(call) if call["response_body"].get("status") == "completed" else ""
    return dict(seconds=round(time.monotonic() - started, 1), call_id=str(call["id"]),
                usd=(call.get("charged_nano_usd") or 0) / 1e9, output_tokens=usage.get("output_tokens"),
                text=text, response=call["response_body"])


def allow_in_this_process(model):
    """Let one other already-priced model of the configured provider run here only.

    The app allows only its configured quick and main models. This changes nothing
    on disk and nothing in the running app; the ledger still prices every call.
    """
    from thesis.providers import settings
    if model in (settings.MODEL, settings.REASONING_MODEL):
        return
    if model not in settings.TWIN_PRICES.get(settings.PROVIDER, {}):
        raise SystemExit(f"{model} has no recorded {settings.PROVIDER} price")
    settings.REASONING_MODEL = model
    settings.select = lambda values: (settings.PROVIDER, settings.MODEL, model)


def main():
    run_dir, models = Path(sys.argv[1]), sys.argv[2:]
    for model in models:
        allow_in_this_process(model)
    bodies = [json.loads(p.read_text()) for p in sorted(run_dir.glob("b*.request.json"))]
    print(f"sending {len(bodies)} saved batches to {models}", flush=True)
    for model in models:
        with ThreadPoolExecutor(4) as pool:
            results = list(pool.map(lambda a: run(model, *a), list(enumerate(bodies))))
        rows = []
        for i, (body, r) in enumerate(zip(bodies, results)):
            (run_dir / f"b{i:02d}.{model}.json").write_text(json.dumps(r.pop("response", None), indent=2, ensure_ascii=False, default=str))
            raw, problems = check(r["text"], body) if r.get("text") else (None, [r.get("error") or "empty"])
            r["item_problems"] = problems
            labels = {x["id"]: x for x in (raw or {}).get("items", [])}
            rows.append(dict(batch=i, result={k: v for k, v in r.items() if k != "text"}, items={
                l: dict(relevance=x.get("relevance"), sentiment=x.get("sentiment"), basis=x.get("basis"),
                        statement=x.get("statement"), kind=(x.get("reporting") or {}).get("kind"),
                        impact=(x.get("reporting") or {}).get("impact")) for l, x in labels.items()}))
        (run_dir / f"fair-{model}.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False, default=str))
        ok = sum(not r["result"]["item_problems"] for r in rows)
        print(f"{model}: {ok}/{len(rows)} pass; US${sum(r['result'].get('usd') or 0 for r in rows):.3f}", flush=True)


if __name__ == "__main__":
    main()
