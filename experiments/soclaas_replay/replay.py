"""Evaluation only: replay saved AVGO sentiment requests on SOC LaaS and compare.

Reads exact saved Claude request/response pairs from model_calls (read-only),
sends the identical system prompt, sources and schema to the SOC LaaS
OpenAI-compatible endpoint, checks each answer with the app's own structural
rules, and writes everything to an output folder. Nothing is written to the
app database or the model ledger. No automatic retries.

Usage:
  .venv/bin/python experiments/soclaas_replay/replay.py OUT_DIR [--limit 15] [--workers 2]
      [--format json_object|json_schema] [--effort none|low|medium|high] [--max-tokens N]
"""
import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import psycopg
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from thesis.config import dsn  # noqa: E402
from thesis.research.sentiment import Classification  # noqa: E402

URL = "https://soclaas-api.comp.nus.edu.sg/v1/chat/completions"


def env(name):
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith(name + "="):
            return line.split("=", 1)[1].split(" #")[0].strip().strip('"').strip("'")
    raise SystemExit(f"{name} is missing from .env")


def saved_calls(limit):
    with psycopg.connect(dsn("thesis_local"), row_factory=dict_row,
                         options="-c default_transaction_read_only=on") as conn:
        return conn.execute(
            "SELECT id, created_at, request_body, response_body, output_tokens,"
            " extract(epoch from finished_at-created_at) seconds FROM model_calls"
            " WHERE purpose='thesis-source-sentiment-24' AND model='claude-opus-5-5'"
            " AND status='settled'"
            " AND (request_body->'input'->1->>'content')::jsonb->'company'->>'symbol'='AVGO'"
            " ORDER BY created_at DESC LIMIT %s", (limit,)).fetchall()


def text_of(response_body):
    return next(p["text"] for o in response_body["output"] if o.get("type") == "message"
                for p in o["content"] if p.get("type") == "output_text")


OPTIONS = dict(format="json_object", effort=None, max_tokens=None)


def to_chat(body, model):
    system, user = (m["content"] for m in body["input"])
    schema = body["text"]["format"]["schema"]
    if OPTIONS["format"] == "json_schema":
        # The server enforces the schema while decoding, as Claude's API does,
        # so the schema is not repeated in the instructions.
        content = system
        response_format = {"type": "json_schema", "json_schema": {
            "name": body["text"]["format"].get("name", "result"), "strict": True, "schema": schema}}
    else:
        # Same translation as thesis/providers/deepseek.py: JSON mode, schema in instructions.
        content = (system + "\n\nReturn only one json object, with no other text or code "
                   "fences, that validates against this JSON schema:\n"
                   + json.dumps(schema, sort_keys=True))
        response_format = {"type": "json_object"}
    return dict(
        model=model,
        messages=[{"role": "system", "content": content}, {"role": "user", "content": user}],
        max_tokens=OPTIONS["max_tokens"] or body["max_output_tokens"],
        response_format=response_format,
        **({"reasoning_effort": OPTIONS["effort"]} if OPTIONS["effort"] else {}),
        stream=False,
    )


def branches(schema):
    found = {}
    for b in schema["properties"]["items"]["items"]["anyOf"]:
        found[b["properties"]["id"]["enum"][0]] = b

    def enum(prop):
        items = prop.get("items", {})
        if "$ref" in items:
            items = schema["$defs"][items["$ref"].split("/")[-1]]
        return set(items.get("enum") or [])
    return {k: dict(
        passages=enum(b["properties"]["passages"]),
        context=enum(b["properties"]["context_passages"]),
        context_min=b["properties"]["context_passages"].get("minItems", 0),
        reporting=(set(b["properties"]["reporting"]["properties"]["passages"]["items"]["enum"])
                   if "reporting" in b["properties"] else None),
        social="price_claims" in b["properties"]
        and b["properties"]["price_claims"].get("maxItems") != 0,
    ) for k, b in found.items()}


def check(text, body):
    """Structural/consistency rules the app applies (sentiment.render, reporting_basis.render)."""
    problems = []
    try:
        start, end = text.find("{"), text.rfind("}")
        raw = json.loads(text[start:end + 1])
        result = Classification.model_validate(raw)
    except Exception as exc:  # noqa: BLE001
        return None, [f"not valid result JSON: {type(exc).__name__}: {str(exc)[:200]}"]
    rules = branches(body["text"]["format"]["schema"])
    ids = [i.id for i in result.items]
    if sorted(ids) != sorted(rules):
        problems.append(f"labels mismatch: missing {sorted(set(rules) - set(ids))}, "
                        f"extra/duplicate {sorted(set(i for i in ids if ids.count(i) > 1 or i not in rules))}")
    for item in result.items:
        r = rules.get(item.id)
        if not r:
            continue
        tag = item.id
        if not item.passages or set(item.passages) - r["passages"]:
            problems.append(f"{tag}: passages not from this source")
        if set(item.context_passages) - r["context"] or len(item.context_passages) < r["context_min"]:
            problems.append(f"{tag}: bad context passages")
        if item.relevance != "relevant" and item.sentiment != "unclear":
            problems.append(f"{tag}: {item.relevance} source with directional label")
        if ((item.sentiment == "neutral" and item.basis != "descriptive")
                or (item.sentiment == "unclear" and item.basis != "unclear")
                or (item.sentiment in {"positive", "negative", "mixed"}
                    and item.basis not in {"expressed_evaluation", "stated_outcome"})):
            problems.append(f"{tag}: sentiment {item.sentiment} vs basis {item.basis}")
        if item.previous_passages and (not r["social"] or item.relevance != "relevant"):
            problems.append(f"{tag}: earlier-attitude passages outside a relevant social post")
        if r["reporting"] is not None:
            rep = item.reporting
            if rep is None:
                problems.append(f"{tag}: news item missing reporting evidence")
            else:
                event = rep.kind in {"reported_event", "unconfirmed_event"}
                if bool(rep.passages) != event or set(rep.passages) - r["reporting"]:
                    problems.append(f"{tag}: reporting passages inconsistent with kind")
                if not event and rep.impact != "not_stated":
                    problems.append(f"{tag}: non-event carries impact")
                if event and item.relevance != "relevant":
                    problems.append(f"{tag}: event on non-relevant item")
        elif item.reporting is not None:
            problems.append(f"{tag}: reporting on social item")
        if not r["social"] and item.price_claims:
            problems.append(f"{tag}: price claims on news")
    return raw, problems


def send(call, key, model, out):
    body = call["request_body"]
    started = time.monotonic()
    record = dict(call_id=str(call["id"]), saved_at=call["created_at"].isoformat())
    try:
        with httpx.Client(timeout=httpx.Timeout(600, connect=15), follow_redirects=False,
                          transport=httpx.HTTPTransport(retries=0)) as client:
            response = client.post(URL, headers={"Authorization": "Bearer " + key},
                                   json=to_chat(body, model))
        record["seconds"] = round(time.monotonic() - started, 1)
        record["http"] = response.status_code
        if response.status_code != 200:
            record["error"] = f"http_{response.status_code}"
            (out / f"{call['id']}.error.txt").write_text(response.text[:4000])
            return record
        data = response.json()
        (out / f"{call['id']}.soclaas.json").write_text(json.dumps(data, indent=2, ensure_ascii=False))
        choice = data["choices"][0]
        record.update(finish=choice.get("finish_reason"), usage=data.get("usage"),
                      reported_model=data.get("model"))
        record["text"] = choice["message"].get("content") or ""
    except httpx.TimeoutException:
        record.update(seconds=round(time.monotonic() - started, 1), error="timeout")
    except httpx.RequestError as exc:
        record.update(seconds=round(time.monotonic() - started, 1), error=type(exc).__name__)
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("out")
    parser.add_argument("--limit", type=int, default=15)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--format", choices=("json_object", "json_schema"), default="json_object")
    parser.add_argument("--effort", choices=("none", "low", "medium", "high"))
    parser.add_argument("--max-tokens", type=int)
    args = parser.parse_args()
    OPTIONS.update(format=args.format, effort=args.effort, max_tokens=args.max_tokens)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    key, model = env("SOC_LAAS_API_KEY"), env("SOC_LAAS_MODEL")
    calls = saved_calls(args.limit)
    for c in calls:
        (out / f"{c['id']}.request.json").write_text(json.dumps(c["request_body"], ensure_ascii=False))
        (out / f"{c['id']}.claude.json").write_text(json.dumps(c["response_body"], indent=2, ensure_ascii=False))
    print(f"replaying {len(calls)} saved AVGO batches on {model} with {OPTIONS}", flush=True)
    (out / "options.json").write_text(json.dumps(dict(OPTIONS, model=model)))
    with ThreadPoolExecutor(args.workers) as pool:
        records = list(pool.map(lambda c: send(c, key, model, out), calls))
    rows = []
    for call, rec in zip(calls, records):
        body = call["request_body"]
        claude_raw, claude_problems = check(text_of(call["response_body"]), body)
        soc_raw, soc_problems = (check(rec["text"], body) if rec.get("text")
                                 else (None, [rec.get("error") or f"empty ({rec.get('finish')})"]))
        sources = {s["label"]: s for s in json.loads(body["input"][1]["content"])["sources"]}
        cl = {i["id"]: i for i in (claude_raw or {}).get("items", [])}
        so = {i["id"]: i for i in (soc_raw or {}).get("items", [])}
        items = []
        for label, src in sources.items():
            a, b = cl.get(label, {}), so.get(label, {})
            items.append(dict(
                label=label, channel=src.get("channel"), platform=src.get("platform"),
                title=(src.get("title") or "")[:140],
                claude=dict(relevance=a.get("relevance"), sentiment=a.get("sentiment"),
                            basis=a.get("basis"), statement=a.get("statement"),
                            kind=(a.get("reporting") or {}).get("kind"),
                            impact=(a.get("reporting") or {}).get("impact")),
                soclaas=dict(relevance=b.get("relevance"), sentiment=b.get("sentiment"),
                             basis=b.get("basis"), statement=b.get("statement"),
                             kind=(b.get("reporting") or {}).get("kind"),
                             impact=(b.get("reporting") or {}).get("impact")),
            ))
        rows.append(dict(
            call_id=str(call["id"]), saved_at=call["created_at"].isoformat(),
            claude_seconds=round(float(call["seconds"]), 1), claude_output_tokens=call["output_tokens"],
            soclaas=dict({k: v for k, v in rec.items() if k != "text"}),
            claude_problems=claude_problems, soclaas_problems=soc_problems,
            claude_links=len((claude_raw or {}).get("coverage_links", [])),
            soclaas_links=len((soc_raw or {}).get("coverage_links", [])),
            items=items))
    (out / "comparison.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False))
    ok = sum(not r["soclaas_problems"] for r in rows)
    print(f"done: {ok}/{len(rows)} SOC LaaS answers pass the app's checks; see {out/'comparison.json'}")


if __name__ == "__main__":
    main()
