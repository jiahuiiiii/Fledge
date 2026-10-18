"""Evaluation only: send one frozen quality plan to a cheaper model on OpenRouter.

The same 50 owner cases and 6 hard cases, request text and strict JSON schema as
the GPT-5.4 run. Answers pass the app's own tone validator (T.tone_labels via
V.parse); a malformed answer is a recorded failure, never retried. OpenRouter's
reported cost is recorded per call and a hard cap stops sending. OpenRouter is
not part of the app's spending ledger. Nothing is saved to the app database.

Usage: .venv/bin/python experiments/soclaas_replay/quality_openrouter.py PLAN MANIFEST MODEL OUT [--cap 0.25]
"""
import argparse
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent))
from replay import env  # noqa: E402
from experiments.soclaas_replay import sentiment_quality_validation as V  # noqa: E402

URL = "https://openrouter.ai/api/v1/chat/completions"


def supported(model):
    data = httpx.get("https://openrouter.ai/api/v1/models", timeout=30).json()["data"]
    found = next((m for m in data if m["id"] == model), None)
    if not found:
        raise SystemExit(f"Unknown OpenRouter model {model}.")
    return set(found.get("supported_parameters") or [])


def body_for(saved, model, params):
    fmt = saved["text"]["format"]
    body = dict(
        model=model,
        messages=[{"role": m["role"], "content": m["content"]} for m in saved["input"]],
        max_tokens=saved["max_output_tokens"],
        response_format={"type": "json_schema", "json_schema": {"name": fmt.get("name", "result"), "strict": True, "schema": fmt["schema"]}},
        provider={"require_parameters": True},
        usage={"include": True},
        stream=False,
    )
    if "reasoning" in params:
        body["reasoning"] = {"effort": saved.get("reasoning", {}).get("effort", "low")}
    return body


def as_call(text):
    """The Responses-API shape the app's validator reads."""
    return dict(response_body=dict(status="completed", output=[dict(type="message", content=[dict(type="output_text", text=text)])]))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("plan", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("model")
    parser.add_argument("out", type=Path)
    parser.add_argument("--cap", type=float, default=0.25)
    parser.add_argument("--resume", action="store_true", help="Send only cases skipped by an earlier cap; never resend an attempted case.")
    args = parser.parse_args()
    plan, manifest = json.loads(args.plan.read_text()), json.loads(args.manifest.read_text())
    cases = V.validate(plan, manifest)
    params = supported(args.model)
    earlier = {}
    if args.resume:
        old = json.loads((args.out / "report.json").read_text())
        if old["model"] != args.model or old["plan_fingerprint"] != plan["fingerprint"]:
            raise SystemExit("Resume needs the same model and frozen plan.")
        earlier = {(r["scope"], r["id"]): r for r in old["results"] if not str(r.get("error", "")).startswith("skipped:")}
        spent_before = old["cost_usd"]
    else:
        args.out.mkdir(parents=True, exist_ok=False)
        spent_before = 0.0
    key = env("OPENROUTER_API_KEY")
    spent, lock = [spent_before], threading.Lock()

    def send(case):
        if (case["scope"], case["id"]) in earlier:
            return {k: v for k, v in earlier[(case["scope"], case["id"])].items() if k not in ("scope", "id", "expected_tone")}
        with lock:
            if spent[0] >= args.cap:
                return dict(error=f"skipped: cap US${args.cap} reached")
        started = time.monotonic()
        try:
            with httpx.Client(timeout=httpx.Timeout(300, connect=15), follow_redirects=False,
                              transport=httpx.HTTPTransport(retries=0)) as client:
                response = client.post(URL, headers={"Authorization": "Bearer " + key}, json=body_for(case["body"], args.model, params))
        except httpx.HTTPError as exc:
            return dict(error=type(exc).__name__, seconds=round(time.monotonic() - started, 1))
        seconds = round(time.monotonic() - started, 1)
        name = case["scope"] + "-" + case["id"]
        if response.status_code != 200:
            (args.out / f"{name}.error.txt").write_text(response.text[:4000])
            return dict(error=f"http_{response.status_code}", seconds=seconds)
        data = response.json()
        (args.out / f"{name}.response.json").write_text(json.dumps(data, indent=2, ensure_ascii=False))
        usage = data.get("usage") or {}
        with lock:
            spent[0] += float(usage.get("cost") or 0)
        choice = (data.get("choices") or [{}])[0]
        text = (choice.get("message") or {}).get("content") or ""
        row = dict(seconds=seconds, usd=float(usage.get("cost") or 0), host=data.get("provider"),
                   finish=choice.get("finish_reason"), input_tokens=usage.get("prompt_tokens"), output_tokens=usage.get("completion_tokens"))
        try:
            prediction, repaired = V.parse(as_call(text), case["packet"])
            row.update(passed=True, prediction=prediction, repaired=repaired)
        except (ValueError, KeyError, TypeError) as exc:
            row.update(passed=False, error="validator: " + str(exc)[:300])
        return row

    print(f"sending {len(cases)} requests to {args.model} (cap US${args.cap})", flush=True)
    with ThreadPoolExecutor(4) as pool:
        rows = list(pool.map(send, cases))
    results = [dict(scope=c["scope"], id=c["id"], expected_tone=c.get("expected_tone"), **r) for c, r in zip(cases, rows)]
    owner = {r["id"]: r["prediction"] for r in results if r.get("passed") and r["scope"] == "owner50"}
    hard = [r for r in results if r["scope"] == "hard6"]
    report = dict(model=args.model, plan_fingerprint=plan["fingerprint"], requests=len(results),
                  passed=sum(bool(r.get("passed")) for r in results), cost_usd=round(spent[0], 6),
                  hard_correct=sum(1 for r in hard if r.get("passed") and r["prediction"]["sentiment"] == r["expected_tone"]),
                  median_seconds=sorted(r.get("seconds", 0) for r in results)[len(results) // 2],
                  hosts=sorted({str(r.get("host")) for r in results}), results=results, automatic_retries=0)
    (args.out / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    (args.out / "owner-predictions.json").write_text(json.dumps(dict(fingerprint=manifest["fingerprint"], predictions=owner), indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != "results"}), flush=True)


if __name__ == "__main__":
    main()
