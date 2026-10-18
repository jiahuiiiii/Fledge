"""Evaluation only: send the saved fair-test batches to DeepSeek V4.1 Flash on OpenRouter.

Same requests as the other fair-test runs. One host is pinned (no fallbacks, all
parameters required), the JSON schema is enforced, and OpenRouter's reported
actual cost is recorded per call. OpenRouter is not part of the app's spending
ledger, so this script stops before sending once a hard cap is reached.
Nothing is saved to the app database. No automatic retries.

Usage: .venv/bin/python experiments/soclaas_replay/fair_openrouter.py RUN_DIR [--host deepinfra/fp8] [--cap 1.0]
"""
import argparse
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent))
from replay import env, check  # noqa: E402

URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "deepseek/deepseek-v4.1-flash"
NAME = "openrouter-deepseek-v4.1-flash"


def body_for(saved, host):
    return dict(
        model=MODEL,
        messages=[{"role": m["role"], "content": m["content"]} for m in saved["input"]],
        max_tokens=24000,
        response_format={"type": "json_schema", "json_schema": {
            "name": saved["text"]["format"].get("name", "result"), "strict": True,
            "schema": saved["text"]["format"]["schema"]}},
        provider={"only": [host], "order": [host], "allow_fallbacks": False, "require_parameters": True},
        usage={"include": True},
        stream=False,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir")
    parser.add_argument("--host", default="deepinfra/fp8")
    parser.add_argument("--cap", type=float, default=1.0)
    args = parser.parse_args()
    run_dir = Path(args.run_dir)
    key = env("OPENROUTER_API_KEY")
    bodies = [json.loads(p.read_text()) for p in sorted(run_dir.glob("b*.request.json"))]
    spent, lock = [0.0], threading.Lock()

    def send(index, saved):
        with lock:
            if spent[0] >= args.cap:
                return dict(error=f"skipped: cap US${args.cap} reached", seconds=0)
        started = time.monotonic()
        try:
            with httpx.Client(timeout=httpx.Timeout(600, connect=15), follow_redirects=False,
                              transport=httpx.HTTPTransport(retries=0)) as client:
                response = client.post(URL, headers={"Authorization": "Bearer " + key}, json=body_for(saved, args.host))
        except httpx.HTTPError as exc:
            return dict(error=type(exc).__name__, seconds=round(time.monotonic() - started, 1))
        seconds = round(time.monotonic() - started, 1)
        if response.status_code != 200:
            (run_dir / f"b{index:02d}.{NAME}.error.txt").write_text(response.text[:4000])
            return dict(error=f"http_{response.status_code}", seconds=seconds)
        data = response.json()
        (run_dir / f"b{index:02d}.{NAME}.json").write_text(json.dumps(data, indent=2, ensure_ascii=False))
        usage = data.get("usage") or {}
        cost = float(usage.get("cost") or 0)
        with lock:
            spent[0] += cost
        choice = (data.get("choices") or [{}])[0]
        return dict(seconds=seconds, usd=cost, host=data.get("provider"), reported_model=data.get("model"),
                    finish=choice.get("finish_reason"), output_tokens=usage.get("completion_tokens"),
                    input_tokens=usage.get("prompt_tokens"),
                    reasoning_tokens=(usage.get("completion_tokens_details") or {}).get("reasoning_tokens"),
                    text=(choice.get("message") or {}).get("content") or "")

    print(f"sending {len(bodies)} saved batches to {MODEL} pinned to {args.host} (cap US${args.cap})", flush=True)
    with ThreadPoolExecutor(4) as pool:
        results = list(pool.map(lambda a: send(*a), list(enumerate(bodies))))
    rows = []
    for i, (body, r) in enumerate(zip(bodies, results)):
        raw, problems = check(r["text"], body) if r.get("text") else (None, [r.get("error") or f"empty ({r.get('finish')})"])
        r["item_problems"] = problems
        labels = {x["id"]: x for x in (raw or {}).get("items", [])}
        rows.append(dict(batch=i, result={k: v for k, v in r.items() if k != "text"}, items={
            l: dict(relevance=x.get("relevance"), sentiment=x.get("sentiment"), basis=x.get("basis"),
                    statement=x.get("statement"), kind=(x.get("reporting") or {}).get("kind"),
                    impact=(x.get("reporting") or {}).get("impact")) for l, x in labels.items()}))
    (run_dir / f"fair-{NAME}.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False, default=str))
    ok = sum(not r["result"]["item_problems"] for r in rows)
    hosts = sorted({str(r["result"].get("host")) for r in rows})
    print(f"{NAME}: {ok}/{len(rows)} pass; actual cost US${spent[0]:.4f}; hosts used {hosts}", flush=True)


if __name__ == "__main__":
    main()
