"""Bounded whole-source requests, durable ledger reuse and all-or-nothing output.

No source fetches, automatic retries, extra model stage or separate allowance.
The original model ledger retains every response, including failed attempts.
"""
from collections import Counter
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
import re
from decimal import Decimal
from pydantic import ValidationError

import psycopg
from thesis.config import dsn
from thesis.db import transaction, one
from thesis.providers import ledger
from thesis.service import Conflict

POLICY = "sentiment-whole-source-batches-5"
MAX_SOURCES = 8
# Conservative serialized-request bound, including prompt/schema/comparisons.
# This is an input-size heuristic, not a prediction of reasoning/output tokens.
MAX_BYTES = 48000
MAX_EXPLICIT_RETRIES = 1
MAX_COMPARISONS = 16


@contextmanager
def company_lock(iid):
    with psycopg.connect(dsn(), autocommit=True) as conn:
        locked = conn.execute("SELECT pg_try_advisory_lock(hashtextextended(%s,0))",
                              ("sentiment-company:" + str(iid),)).fetchone()[0]
        if not locked:
            raise Conflict("Sentiment analysis is already running for this company.")
        yield


def part_for(packet, sources, *, max_bytes=None):
    from . import coverage, sentiment
    part = deepcopy(packet)
    part["sources"] = deepcopy(sources)
    selected = {s["id"] for s in sources}
    references = deepcopy(packet.get("comparison_sources", [])) + [
        deepcopy(s) for s in packet["sources"]
        if s["channel"] == "news" and s["id"] not in selected
    ]
    news = [s for s in sources if s['channel'] == 'news']
    if news:
        references = [ref for ref in references if any(coverage._order(ref) < coverage._order(s) for s in news)]
    # Ranking selects comparison context, never source relevance or eligibility.
    words = lambda s: set(re.findall(r'[a-z0-9]{3,}', (s['title'] + ' ' + s['text']).lower()))
    targets = [words(s) for s in news]
    references.sort(key=lambda ref: (
        max((len(words(ref) & target) / max(1, len(words(ref) | target)) for target in targets), default=0),
        coverage._order(ref)), reverse=True)
    before = len(references)
    part['comparison_sources'] = references[:MAX_COMPARISONS]
    if max_bytes is not None:
        # Reduce comparison context only; originals and parents stay whole.
        while part['comparison_sources'] and len(ledger.canonical(sentiment.request_for(part)).encode()) > max_bytes:
            part['comparison_sources'].pop()
    part['comparison_selection'] = dict(available=before, supplied=len(part['comparison_sources']))
    return part


def plan(packet, *, max_sources=MAX_SOURCES, max_bytes=MAX_BYTES):
    from .sentiment import request_for
    from . import sentiment_context
    max_bytes = min(max_bytes, ledger.MAX_REQUEST_BYTES)
    if type(max_sources) is not int or not 1 <= max_sources <= MAX_SOURCES:
        raise ValueError("Invalid sentiment batch size")
    sources = packet["sources"]
    if not sources or len({s["id"] for s in sources}) != len(sources):
        raise ValueError("Sentiment batches require distinct complete sources.")
    parts, selected = [], []
    for source in sources:
        candidate = part_for(packet, selected + [source], max_bytes=max_bytes)
        parents = [s['conversation'] for s in candidate['sources'] if s.get('conversation')]
        fits = (len(selected) < max_sources
                and len(parents) <= sentiment_context.MAX_PARENTS
                and sum(len(ledger.canonical(p['passages']).encode()) for p in parents) <= sentiment_context.MAX_BYTES
                and len(ledger.canonical(request_for(candidate)).encode()) <= max_bytes)
        if selected and not fits:
            parts.append(part_for(packet, selected, max_bytes=max_bytes))
            selected = []
        selected.append(source)
        if len(ledger.canonical(request_for(part_for(packet, selected, max_bytes=max_bytes))).encode()) > max_bytes:
            raise ValueError("One complete source and its context exceed this analysis limit. No batch was sent.")
    parts.append(part_for(packet, selected, max_bytes=max_bytes))
    return parts


def part_identity(part):
    from .sentiment import model_identity
    return model_identity(part) + ":" + POLICY


def plan_identity(packet):
    keys = [part_identity(part) for part in plan(packet)]
    return "sentiment-batched:" + hashlib.sha256(ledger.canonical(keys).encode()).hexdigest()


def check_access(conn, packet):
    from . import sentiment, sentiment_context, sentiment_guards
    allowed = sentiment.permitted_ids(conn, {"packet": packet, "instrument_id": packet["instrument_id"]})
    if not sentiment_guards.allowed(conn, packet) or any(s["id"] not in allowed or not sentiment_context.allowed(conn, s)
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
    from .sentiment import Classification, response_text
    return Classification.model_validate_json(response_text(call)).model_dump()


def failure_details(call, error):
    """Bounded diagnostics: never display provider errors or model text."""
    from .sentiment import IncompleteResponse, response_text
    details = dict(code="invalid_result", reason="The AI's result did not pass the source and evidence checks.")
    if call:
        try:
            response_text(call)
        except IncompleteResponse as exc:
            code = "output_limit" if (call['response_body'].get('incomplete_details') or {}).get('reason') == 'max_output_tokens' else "incomplete_response"
            details.update(code=code, reason=str(exc))
        else:
            if isinstance(error, ValidationError):
                details.update(code="invalid_format", reason="The AI's response did not match the required result format.")
        charge = call.get('charged_nano_usd')
        if charge is not None:
            details['charged_usd'] = str(Decimal(charge) / ledger.NANO)
    else:
        details.update(code="request_failed", reason="The AI request could not finish.")
    return details


def failure_message(failed, total, completed, details, *, saved=False):
    prefix = f"A saved batch (batch {failed} of {total}) needs attention." if saved else f"Batch {failed} of {total} stopped."
    message = f"{prefix} {details['reason']} {completed} completed batch{'es are' if completed != 1 else ' is'} saved."
    later = total - failed
    if later:
        message += f" {later} later batch{'es were' if later != 1 else ' was'} not sent in this run."
    if 'charged_usd' in details:
        message += f" The unsuccessful call cost US${Decimal(details['charged_usd']):.4f}."
    return message + " No combined reading was published and no automatic retry was made."


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


def preflight(parts, *, retry_failed=False):
    """Check the complete plan; per-call reservations still enforce the cap."""
    from .sentiment import render, request_for
    needed = 0
    for part in parts:
        previous, attempt = prior_attempt(part)
        if previous:
            if previous['status'] != 'settled':
                raise ledger.BudgetBlocked('An earlier batch may already have been sent. No automatic retry; its charge needs review.')
            try:
                render(previous, part)
            except ValueError:
                if not retry_failed or attempt >= MAX_EXPLICIT_RETRIES:
                    continue
            else:
                continue
        needed += ledger.estimate(request_for(part))
    budget = ledger.snapshot()
    remaining = Decimal(budget['remaining_usd'])
    maximum = Decimal(needed) / ledger.NANO
    if maximum > remaining:
        raise ledger.BudgetBlocked(
            f'The complete {sum(len(p["sources"]) for p in parts)}-source reading needs a maximum allowance of US${maximum:.4f}; '
            f'US${remaining:.4f} is available. No new batches were sent. Completed batches remain saved.')
    return dict(maximum_new_usd=str(maximum), available_usd=str(remaining))


def run(packet, *, transport=None, progress=None, retry_failed=False):
    from .sentiment import request_for, render, PROMPT
    parts = plan(packet)
    calls = []
    sizes = [len(p["sources"]) for p in parts]

    def report(message, failed=None, failure=None):
        if progress:
            progress(dict(completed=len(calls), total=len(parts), source_counts=sizes,
                          failed=failed, message=message,
                          **({'failure': failure} if failure else {})))

    report(f"0 of {len(parts)} batches complete · {len(packet['sources'])} eligible sources")
    try:
        preflight(parts, retry_failed=retry_failed)
    except ledger.BudgetBlocked as exc:
        report(str(exc))
        raise
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
            except ValueError as exc:
                if not retry_failed or attempt >= MAX_EXPLICIT_RETRIES:
                    details = failure_details(previous, exc)
                    message = failure_message(index + 1, len(parts), len(calls), details, saved=True)
                    message += " The one explicit retry has also been used." if attempt else " Refresh & analyse can retry this batch once if its inputs are unchanged; paid AI uses the existing allowance."
                    report(message, index + 1, details)
                    raise ValueError(message) from None
                key += f":retry:{attempt + 1}"
            else:
                calls.append(previous)
                report(f"{len(calls)} of {len(parts)} batches complete · reused saved result")
                continue
        report(f"{len(calls)} of {len(parts)} batches complete · reading batch {index + 1}")
        call = None
        try:
            call = ledger.execute(key, PROMPT, request_for(part), transport=transport)
            render(call, part)
        except Exception as exc:
            if isinstance(exc, ledger.BudgetBlocked):
                report(str(exc), index + 1)
                raise
            details = failure_details(call, exc)
            message = failure_message(index + 1, len(parts), len(calls), details)
            report(message, index + 1, details)
            raise ValueError(message) from None
        calls.append(call)
        report(f"{len(calls)} of {len(parts)} batches complete")
    with transaction() as conn:
        check_access(conn, packet)
    report("All batches complete · checking the combined result")
    result = combine(packet, parts, calls)
    result["batching"] = dict(policy=POLICY, completed=len(parts), total=len(parts), source_counts=sizes,
                             comparison_limit=MAX_COMPARISONS,
                             comparison_context_bounded=any(p['comparison_selection']['supplied'] < p['comparison_selection']['available'] for p in parts))
    return result, calls
