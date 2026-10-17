"""Evaluation only: send the saved fair-test batches to several OpenAI models.

Same requests as fair_compare/fair_claude (only the model name changes), through
the app's ledger with experiment request keys. Models other than the app's two
configured ones get an evaluation price profile in this process only, at the
official per-token prices below (checked 17 Oct 2026 on developers.openai.com).
Nothing on disk or in the running app changes. No automatic retries.

Usage: .venv/bin/python experiments/soclaas_replay/fair_openai.py RUN_DIR MODEL [MODEL ...]
"""
import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent))
from thesis.providers import ledger, settings, openai  # noqa: E402
from fair_claude import run  # noqa: E402
from replay import check  # noqa: E402
from concurrent.futures import ThreadPoolExecutor  # noqa: E402

# nano-USD per token: input, cached input, output (= US$ per 1M tokens x 1000).
PRICES = {
    "gpt-5.5-2026-04-23": (5000, 500, 30000),
    "gpt-5.4-2026-03-05": (2500, 250, 15000),
    "gpt-5.4-mini-2026-03-17": (750, 75, 4500),
    "gpt-5.4-nano-2026-03-17": (200, 20, 1250),
}


def allow(model):
    assert settings.PROVIDER == "openai", "the app must be on the OpenAI provider"
    if model == settings.REASONING_MODEL:
        return  # gpt-5.4 already has the app's own low-effort sentiment profile
    i, c, o = PRICES[model]
    profile = ledger.PriceProfile(model, f"eval-{model}-sentiment-low-12000-20261017", i, c, o,
                                  ledger.SENTIMENT_LOW_MAX_OUTPUT, "low")
    ledger.PROFILES = (profile,) + tuple(p for p in ledger.PROFILES if p.model != model or p.version != profile.version)
    settings.REASONING_MODEL = model
    settings.select = lambda values: (settings.PROVIDER, settings.MODEL, model)


openai.request_timeout = lambda body: httpx.Timeout(180, connect=15, read=300)


def main():
    run_dir, models = Path(sys.argv[1]), sys.argv[2:]
    bodies = [json.loads(p.read_text()) for p in sorted(run_dir.glob("b*.request.json"))]
    original = settings.REASONING_MODEL
    for model in models:
        settings.REASONING_MODEL = original
        allow(model)
        print(f"sending {len(bodies)} saved batches to {model}", flush=True)
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
