"""Evaluation only: send identical fresh sentiment batches to Claude Opus and DeepSeek.

Builds one current packet for a company with the app's own sentiment.prepare and
batch planner, then sends every batch to both models at the same time:
  - Claude: through the app's ledger (normal accounting, experiment request keys,
    so app readings never reuse these calls)
  - DeepSeek V4.1 Flash on SOC LaaS: strict JSON schema, default thinking.
Both answers are judged by the app's real validator (sentiment.render). Nothing is
saved as a reading, alert or watch result.

Usage: .venv/bin/python experiments/soclaas_replay/fair_compare.py SYMBOL OUT_DIR [--sources 128] [--batches 16]
"""
import argparse
import hashlib
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent))
from thesis.db import transaction, one  # noqa: E402
from thesis.providers import ledger  # noqa: E402
from thesis.providers.deepseek import from_completion  # noqa: E402
from thesis.research import sentiment, sentiment_batching  # noqa: E402
from replay import env, check, URL  # noqa: E402

TAG = "experiment:fair-compare-20261016"


def soclaas_body(body, model):
    return dict(
        model=model,
        messages=[{"role": m["role"], "content": m["content"]} for m in body["input"]],
        max_tokens=24000,
        response_format={"type": "json_schema", "json_schema": {
            "name": body["text"]["format"].get("name", "result"), "strict": True,
            "schema": body["text"]["format"]["schema"]}},
        stream=False,
    )


def judge(call, part):
    try:
        sentiment.render(call, part)
        return None
    except Exception as exc:  # noqa: BLE001
        return f"{type(exc).__name__}: {str(exc)[:300]}"


def run_opus(index, part, body, out):
    key = f"{TAG}:opus:{hashlib.sha256(ledger.canonical(body).encode()).hexdigest()}"
    started = time.monotonic()
    try:
        call = ledger.execute(key, sentiment.PROMPT, body)
    except Exception as exc:  # noqa: BLE001
        return dict(error=f"{type(exc).__name__}: {str(exc)[:300]}", seconds=round(time.monotonic() - started, 1))
    seconds = round(time.monotonic() - started, 1)
    (out / f"b{index:02d}.opus.json").write_text(json.dumps(call["response_body"], indent=2, ensure_ascii=False, default=str))
    usage = call["response_body"].get("usage") or {}
    return dict(seconds=seconds, call_id=str(call["id"]), model=call["model"],
                usd=(call.get("charged_nano_usd") or 0) / 1e9,
                output_tokens=usage.get("output_tokens"), problem=judge(call, part),
                text=sentiment.response_text(call) if call["response_body"].get("status") == "completed" else "")


def run_deepseek(index, part, body, out, key, model):
    started = time.monotonic()
    try:
        with httpx.Client(timeout=httpx.Timeout(600, connect=15), follow_redirects=False,
                          transport=httpx.HTTPTransport(retries=0)) as client:
            response = client.post(URL, headers={"Authorization": "Bearer " + key},
                                   json=soclaas_body(body, model))
    except httpx.HTTPError as exc:
        return dict(error=type(exc).__name__, seconds=round(time.monotonic() - started, 1))
    seconds = round(time.monotonic() - started, 1)
    if response.status_code != 200:
        return dict(error=f"http_{response.status_code}", seconds=seconds)
    data = response.json()
    (out / f"b{index:02d}.deepseek.json").write_text(json.dumps(data, indent=2, ensure_ascii=False))
    shaped = from_completion(data, body["model"])
    call = dict(request_body=body, response_body=shaped)
    text = ""
    if shaped["status"] == "completed":
        text = shaped["output"][0]["content"][0]["text"]
    usage = data.get("usage") or {}
    return dict(seconds=seconds, model=data.get("model"), output_tokens=usage.get("completion_tokens"),
                reasoning_tokens=(usage.get("completion_tokens_details") or {}).get("reasoning_tokens"),
                finish=data["choices"][0].get("finish_reason"), problem=judge(call, part), text=text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol")
    parser.add_argument("out")
    parser.add_argument("--sources", type=int, default=128)
    parser.add_argument("--batches", type=int, default=16)
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with transaction() as c:
        iid = str(one(c, "SELECT id FROM instruments WHERE symbol=%s", (args.symbol,))["id"])
        packet = sentiment.prepare(c, iid)
    total = len(packet["sources"])
    packet["sources"] = sorted(packet["sources"], key=lambda s: (s["published_at"], s["id"]), reverse=True)[:args.sources]
    parts = sentiment_batching.plan(packet)[:args.batches]
    print(f"{args.symbol}: {total} eligible sources in the 7-day packet; newest {len(packet['sources'])} "
          f"planned; sending {len(parts)} batches ({sum(len(p['sources']) for p in parts)} sources) to both models", flush=True)
    key, model = env("SOC_LAAS_API_KEY"), env("SOC_LAAS_MODEL")
    bodies = [sentiment.request_for(p) for p in parts]
    for i, (p, b) in enumerate(zip(parts, bodies)):
        (out / f"b{i:02d}.request.json").write_text(json.dumps(b, ensure_ascii=False))
    with ThreadPoolExecutor(2) as opus_pool, ThreadPoolExecutor(2) as ds_pool:
        opus = [opus_pool.submit(run_opus, i, p, b, out) for i, (p, b) in enumerate(zip(parts, bodies))]
        ds = [ds_pool.submit(run_deepseek, i, p, b, out, key, model) for i, (p, b) in enumerate(zip(parts, bodies))]
        results = [(o.result(), d.result()) for o, d in zip(opus, ds)]
    rows = []
    for i, (part, body, (o, d)) in enumerate(zip(parts, bodies, results)):
        items = {}
        for name, r in (("opus", o), ("deepseek", d)):
            raw, item_problems = check(r.get("text") or "", body) if r.get("text") else (None, [r.get("error") or f"empty ({r.get('finish')})"])
            r["item_problems"] = item_problems
            for it in (raw or {}).get("items", []):
                items.setdefault(it["id"], {})[name] = dict(
                    relevance=it.get("relevance"), sentiment=it.get("sentiment"), basis=it.get("basis"),
                    statement=it.get("statement"), kind=(it.get("reporting") or {}).get("kind"),
                    impact=(it.get("reporting") or {}).get("impact"))
        sources = {s["label"]: s for s in part["sources"]}
        rows.append(dict(batch=i, sources=len(sources),
                         opus={k: v for k, v in o.items() if k != "text"},
                         deepseek={k: v for k, v in d.items() if k != "text"},
                         items=[dict(label=l, channel=s["channel"], platform=s.get("platform"),
                                     title=(s.get("title") or "")[:140], **items.get(l, {}))
                                for l, s in sources.items()]))
    (out / "fair.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False, default=str))
    print("opus passes", sum(r["opus"].get("problem") is None and not r["opus"].get("error") for r in rows),
          "| deepseek passes", sum(r["deepseek"].get("problem") is None and not r["deepseek"].get("error") for r in rows),
          f"of {len(rows)}; see {out / 'fair.json'}")


if __name__ == "__main__":
    main()
