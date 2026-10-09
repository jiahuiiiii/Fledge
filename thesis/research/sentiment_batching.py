"""Bounded whole-source requests, durable ledger reuse and all-or-nothing output.

No source fetches, automatic retries, extra model stage or separate allowance.
The original model ledger retains every response, including failed attempts.
"""
from collections import Counter
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json

import psycopg
from thesis.config import dsn
from thesis.db import transaction, one
from thesis.providers import ledger
from thesis.service import Conflict

POLICY = "sentiment-whole-source-batches-1"
MAX_SOURCES = 8
# Conservative serialized-request bound, including prompt/schema/comparisons.
# This is an input-size heuristic, not a prediction of reasoning/output tokens.
MAX_BYTES = 48000
MAX_EXPLICIT_RETRIES = 1


@contextmanager
def company_lock(iid):
    with psycopg.connect(dsn(), autocommit=True) as conn:
        locked = conn.execute("SELECT pg_try_advisory_lock(hashtextextended(%s,0))",
                              ("sentiment-company:" + str(iid),)).fetchone()[0]
        if not locked:
            raise Conflict("Sentiment analysis is already running for this company.")
        yield


def part_for(packet, sources):
    part = deepcopy(packet)
    part["sources"] = deepcopy(sources)
    selected = {s["id"] for s in sources}
    part["comparison_sources"] = deepcopy(packet.get("comparison_sources", [])) + [
        deepcopy(s) for s in packet["sources"]
        if s["channel"] == "news" and s["id"] not in selected
    ]
    return part


def plan(packet, *, max_sources=MAX_SOURCES, max_bytes=MAX_BYTES):
    from .sentiment import request_for
    if type(max_sources) is not int or not 1 <= max_sources <= MAX_SOURCES:
        raise ValueError("Invalid sentiment batch size")
    sources = packet["sources"]
    if not sources or len({s["id"] for s in sources}) != len(sources):
        raise ValueError("Sentiment batches require distinct complete sources.")
    parts, selected = [], []
    for source in sources:
        candidate = part_for(packet, selected + [source])
        fits = len(selected) < max_sources and len(ledger.canonical(request_for(candidate)).encode()) <= max_bytes
        if selected and not fits:
            parts.append(part_for(packet, selected))
            selected = []
        selected.append(source)
        if len(ledger.canonical(request_for(part_for(packet, selected))).encode()) > max_bytes:
            raise ValueError("One complete source and its context exceed this analysis limit. No batch was sent.")
    parts.append(part_for(packet, selected))
    return parts


def part_identity(part):
    from .sentiment import model_identity
    return model_identity(part) + ":" + POLICY


def plan_identity(packet):
    keys = [part_identity(part) for part in plan(packet)]
    return "sentiment-batched:" + hashlib.sha256(ledger.canonical(keys).encode()).hexdigest()


def check_access(conn, packet):
    from . import sentiment, sentiment_context
    allowed = sentiment.permitted_ids(conn, {"packet": packet, "instrument_id": packet["instrument_id"]})
    if any(s["id"] not in allowed or not sentiment_context.allowed(conn, s)
           for s in packet["sources"] + packet.get("comparison_sources", [])):
        raise ValueError("Sentiment source access changed. Saved batches cannot be used for this sample.")


def prior_attempt(part):
    base = part_identity(part)
    with transaction() as conn:
        for attempt in range(MAX_EXPLICIT_RETRIES, -1, -1):
            key = base if not attempt else base + f":retry:{attempt}"
            call = one(conn, "SELECT * FROM model_calls WHERE request_key=%s", (key,))
            if call:
                return call, attempt
    return None, 0


def raw(call):
    from .sentiment import Classification
    body = call["response_body"]
    texts = [p["text"] for item in body.get("output", []) if item.get("type") == "message"
             for p in item.get("content", []) if p.get("type") == "output_text"]
    if body.get("status") != "completed" or len(texts) != 1:
        raise ValueError("Sentiment response incomplete")
    return Classification.model_validate_json(texts[0]).model_dump()


def combine(packet, parts, calls):
    from .sentiment import render
    if len(parts) != len(calls) or Counter(s["id"] for p in parts for s in p["sources"]) != Counter(s["id"] for s in packet["sources"]):
        raise ValueError("All sentiment batches must finish before combining results.")
    merged = dict(items=[], coverage_links=[])
    for part, call in zip(parts, calls):
        render(call, part)
        output = raw(call)
        merged["items"].extend(output["items"])
        merged["coverage_links"].extend(output["coverage_links"])
    # Recheck cross-batch relations and count groups once against all sources.
    return render({"response_body": {"status": "completed", "output": [
        {"type": "message", "content": [{"type": "output_text", "text": json.dumps(merged)}]}
    ]}}, packet)


def run(packet, *, transport=None, progress=None, retry_failed=False):
    from .sentiment import request_for, render, PROMPT
    parts = plan(packet)
    calls = []
    sizes = [len(p["sources"]) for p in parts]

    def report(message, failed=None):
        if progress:
            progress(dict(completed=len(calls), total=len(parts), source_counts=sizes,
                          failed=failed, message=message))

    report(f"0 of {len(parts)} batches complete")
    for index, part in enumerate(parts):
        with transaction() as conn:
            check_access(conn, packet)
        previous, attempt = prior_attempt(part)
        key = part_identity(part)
        if previous:
            if previous["status"] != "settled":
                report("An earlier batch needs charge review; completed batches are saved.", index + 1)
                raise ledger.BudgetBlocked("An earlier batch may already have been sent. No automatic retry; its charge needs review.")
            try:
                render(previous, part)
            except ValueError:
                if not retry_failed or attempt >= MAX_EXPLICIT_RETRIES:
                    report(f"Batch {index + 1} needs attention; completed batches are saved.", index + 1)
                    raise ValueError("A saved batch did not pass validation. Completed batches are retained. " +
                                     ("The one explicit retry has also been used." if attempt else "Refresh & analyse can retry this batch once if its inputs are unchanged.")) from None
                key += f":retry:{attempt + 1}"
            else:
                calls.append(previous)
                report(f"{len(calls)} of {len(parts)} batches complete · reused saved result")
                continue
        report(f"{len(calls)} of {len(parts)} batches complete · reading batch {index + 1}")
        try:
            call = ledger.execute(key, PROMPT, request_for(part), transport=transport)
            render(call, part)
        except Exception as exc:
            report(f"Batch {index + 1} could not finish; {len(calls)} completed batches are saved.", index + 1)
            if isinstance(exc, ledger.BudgetBlocked):
                raise
            raise ValueError(f"Batch {index + 1} of {len(parts)} did not pass validation. Completed batches are saved; no automatic retry was made.") from None
        calls.append(call)
        report(f"{len(calls)} of {len(parts)} batches complete")
    with transaction() as conn:
        check_access(conn, packet)
    report("All batches complete · checking the combined result")
    result = combine(packet, parts, calls)
    result["batching"] = dict(policy=POLICY, completed=len(parts), total=len(parts), source_counts=sizes)
    return result, calls
