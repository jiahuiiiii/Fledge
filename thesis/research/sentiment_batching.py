"""Bounded whole-source requests, durable ledger reuse and all-or-nothing output.

No source fetches, automatic retries or separate allowance.
The original model ledger retains every response, including failed attempts.
"""
from collections import Counter
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
import re
import threading
from decimal import Decimal
from pydantic import ValidationError

import psycopg
from thesis.config import dsn
from thesis.db import transaction, one
from thesis.providers import ledger
from thesis.service import Conflict

POLICY = "sentiment-whole-source-batches-6"
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
    # Comparison reports only serve news coverage links, so a batch without
    # news carries none (it used to repeat up to 16 unused reports).
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
        if len(ledger.canonical(sentiment.request_for(part)).encode()) > max_bytes:
            # Keep the topic and targets whole; optional saved siblings are the
            # only discussion text that may be omitted, with an explicit count.
            part['thread_extras'] = False
    part['comparison_selection'] = dict(available=before, supplied=len(part['comparison_sources']))
    return part


def plan(packet, *, max_sources=MAX_SOURCES, max_bytes=MAX_BYTES):
    from .sentiment import request_for
    from . import sentiment_context, reddit_thread_context
    max_bytes = min(max_bytes, ledger.MAX_REQUEST_BYTES)
    if type(max_sources) is not int or not 1 <= max_sources <= MAX_SOURCES:
        raise ValueError("Invalid sentiment batch size")
    sources = reddit_thread_context.ordered(packet["sources"])
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
    if part.get("_request_key"):
        return part["_request_key"]
    key = model_identity(part) + ":" + POLICY
    return key + ":reread:" + part["reread_token"] if part.get("reread_token") else key


def plan_identity(packet):
    from . import sentiment_task_runner
    if sentiment_task_runner.enabled():
        return sentiment_task_runner.identity(packet)
    keys = [part_identity(part) for part in plan(packet)]
    return "sentiment-batched:" + hashlib.sha256(ledger.canonical(keys).encode()).hexdigest()


def check_access(conn, packet):
    from . import sentiment, sentiment_context, sentiment_guards, reddit_thread_context
    allowed = sentiment.permitted_ids(conn, {"packet": packet, "instrument_id": packet["instrument_id"]})
    if not sentiment_guards.allowed(conn, packet) or not reddit_thread_context.access_allowed(packet, allowed) or any(s["id"] not in allowed or not sentiment_context.allowed(conn, s)
           for s in packet["sources"] + packet.get("comparison_sources", [])):
        raise ValueError("Sentiment source access changed. Saved batches cannot be used for this sample.")


def prior_attempt(part):
    from .sentiment import render
    from . import sentiment_reliability
    base = part_identity(part)
    latest = None
    with transaction() as conn:
        for attempt in range(0 if part.get("_split_child") else MAX_EXPLICIT_RETRIES, -1, -1):
            key = base if not attempt else base + f":retry:{attempt}"
            call = ledger.find(conn, key)
            if call:
                if latest is None:
                    latest = (call, attempt)
                if not sentiment_reliability.enabled():
                    return call, attempt
                try:
                    render(call, part)
                except ValueError:
                    continue
                return call, attempt
    return latest or (None, 0)


def split_parts(part):
    """One terminal split, with identities tied to the exhausted original request."""
    middle = (len(part["sources"]) + 1) // 2
    parent = hashlib.sha256(part_identity(part).encode()).hexdigest()
    children = []
    for index, sources in enumerate((part["sources"][:middle], part["sources"][middle:])):
        child = part_for(part, sources, max_bytes=MAX_BYTES)
        child["_request_key"] = part_identity(child) + f":split:{parent}:{index}"
        child["_split_child"] = True
        children.append(child)
    return children


def has_attempt(key):
    # The ledger permits redispatch after failures. This pipeline requires an
    # explicit retry key instead; uncertain charges must never be resent here.
    with transaction() as conn:
        return bool(one(conn, "SELECT 1 FROM model_calls WHERE request_key=%s OR starts_with(request_key,%s) LIMIT 1",
                        (key, key + ledger.REDISPATCH)))


def recovery_parts(parts, *, split_failed=False):
    from . import sentiment_reliability
    from .sentiment import render
    if not sentiment_reliability.enabled():
        return parts
    expanded = []
    for part in parts:
        saved, attempt = prior_attempt(part)
        invalid = False
        if saved:
            try:
                render(saved, part)
            except ValueError:
                invalid = True
        if invalid and attempt == MAX_EXPLICIT_RETRIES and len(part["sources"]) > 1:
            children = split_parts(part)
            if split_failed or any(has_attempt(part_identity(child)) for child in children):
                expanded.extend(children)
                continue
        expanded.append(part)
    return expanded


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
            elif type(error) is ValueError and str(error).strip():
                # Validators raise fixed sentences, never model text.
                check = " ".join(str(error).split())[:200].rstrip(".")
                details.update(check=check, reason=f"The AI's result did not pass the source and evidence checks ({check}).")
        charge = call.get('charged_nano_usd')
        if charge is not None:
            details['charged_usd'] = str(Decimal(charge) / ledger.NANO)
    else:
        details.update(code="request_failed", reason="The AI request could not finish.")
    return details


def failure_message(failed, total, completed, details, *, saved=False, unsent=None):
    prefix = f"A saved batch (batch {failed} of {total}) needs attention." if saved else f"Batch {failed} of {total} stopped."
    message = f"{prefix} {details['reason']} {completed} completed batch{'es are' if completed != 1 else ' is'} saved."
    later = total - failed if unsent is None else unsent
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
    contexts = {}
    provenance = {}
    for part, call in zip(parts, calls):
        checked = render(call, part)
        provenance.update({i["source_id"]: {k: i[k] for k in ("model", "call_id", "repair") if k in i}
                           for i in checked["items"]})
        if part.get('reddit_thread_context'):
            contexts.update({item['source_id']: item['thread_context'] for item in checked['items'] if item.get('thread_context')})
        output = raw(call)
        merged["items"].extend(output["items"])
        merged["coverage_links"].extend(output["coverage_links"])
    # Recheck cross-batch relations and count groups once against all sources.
    result = render({"response_body": {"status": "completed", "output": [
        {"type": "message", "content": [{"type": "output_text", "text": json.dumps(merged)}]}
    ]}}, packet, enforce_repair_limit=False)
    for item in result['items']:
        if item['source_id'] in contexts:
            item['thread_context'] = contexts[item['source_id']]
        item.update(provenance[item['source_id']])
    return result


def run(packet, *, transport=None, progress=None, retry_failed=False, prefilter=None, split_failed=False):
    """Return (result, calls). A cheap quick check first drops only sources it
    calls clearly unrelated; everything else gets the full reading."""
    from . import relevance_prefilter, sentiment_task_runner
    if sentiment_task_runner.enabled():
        return sentiment_task_runner.run(packet,transport=transport,progress=progress,prefilter=prefilter,
                                         retry_failed=retry_failed,split_failed=split_failed)
    full = packet
    record, quick = None, []
    if prefilter is None:
        prefilter = relevance_prefilter.enabled()
    if prefilter and packet["sources"]:
        # Validate source/context bounds before spending. The ledger checks
        # allowance separately for each quick or full-reading request.
        plan(packet)
        with transaction() as conn:
            check_access(conn, packet)
            if split_failed and any(ledger.find(conn, relevance_prefilter.request_key(body)) is None
                                    for body in relevance_prefilter.plan(packet)):
                raise ValueError("Saved inputs changed. Refresh & analyse before requesting smaller-batch recovery.")
        if progress:
            progress(dict(completed=0, total=0, source_counts=[], failed=None,
                          message=f"Quick relevance check · {len(packet['sources'])} sources"))
        kept, skipped, record, quick = relevance_prefilter.run(packet, transport=transport)
        keep = set(kept)
        packet = dict(packet, sources=[s for s in packet["sources"] if s["id"] in keep])
    if packet["sources"]:
        result, calls = _run(packet, transport=transport, progress=progress, retry_failed=retry_failed, split_failed=split_failed)
    else:
        result, calls = relevance_prefilter_empty(packet), []
        result["batching"] = dict(policy=POLICY, completed=0, total=0, source_counts=[],
                                  comparison_limit=MAX_COMPARISONS, comparison_context_bounded=False)
    if record is not None:
        result = relevance_prefilter.merge(full, result, record)
    return result, quick + calls


def fully_saved(packet, *, prefilter=None):
    """True when the quick check and every full-reading batch are settled and usable."""
    from . import relevance_prefilter, sentiment_task_runner
    if sentiment_task_runner.enabled():
        try:sentiment_task_runner.run(packet,prefilter=prefilter,saved_only=True)
        except Exception:return False
        return True
    from .sentiment import render
    if prefilter is None:
        prefilter = relevance_prefilter.enabled()
    try:
        if prefilter and packet["sources"]:
            by_label = {s["label"]: s["id"] for s in packet["sources"]}
            skip = set()
            for body in relevance_prefilter.plan(packet):
                with transaction() as conn:
                    call = ledger.find(conn, relevance_prefilter.request_key(body))
                if not call:
                    return False
                found = relevance_prefilter.labels(call, body) or {}
                skip |= {by_label[label] for label, value in found.items() if value == "unrelated"}
            packet = dict(packet, sources=[s for s in packet["sources"] if s["id"] not in skip])
        for part in recovery_parts(plan(packet)) if packet["sources"] else []:
            call, attempt = prior_attempt(part)
            if not call or attempt:
                return False
            render(call, part)
    except Exception:
        return False
    return True


def run_reusing(packet, reused, *, transport=None, progress=None, retry_failed=False, prefilter=None, split_failed=False):
    """Send only sources without a saved label; reused labels keep their reading.

    Earlier news still goes along as comparison context, so a new report can be
    linked to an older one. Counts are recalculated over the whole sample.
    """
    from . import sentiment_reuse, sentiment_task_runner
    if sentiment_task_runner.enabled():
        return sentiment_task_runner.run(packet,reused,transport=transport,progress=progress,prefilter=prefilter,
                                         retry_failed=retry_failed,split_failed=split_failed)
    from .sentiment import POLICY as SUMMARY_POLICY, PROMPT
    from thesis.providers.settings import SENTIMENT_MODEL as REASONING_MODEL
    # When every request of the whole-sample reading is already saved (e.g. only
    # the rendering policy changed), reading it again is free and keeps the new
    # reading tied to the same paid calls.
    if not reused or fully_saved(packet, prefilter=prefilter):
        return run(packet, transport=transport, progress=progress,
                   retry_failed=retry_failed, prefilter=prefilter, split_failed=split_failed)
    fresh_sources = [s for s in packet["sources"] if s["id"] not in reused]
    if fresh_sources:
        sub = dict(packet, sources=fresh_sources, comparison_sources=[
            deepcopy(s) for s in packet["sources"]
            if s["channel"] == "news" and s["id"] in reused
        ])
        if progress:
            progress(dict(completed=0, total=0, source_counts=[], failed=None,
                          message=f"{len(reused)} sources already read · reading {len(fresh_sources)} new"))
        fresh, calls = run(sub, transport=transport, progress=progress,
                           retry_failed=retry_failed, prefilter=prefilter, split_failed=split_failed)
    else:
        with transaction() as conn:
            check_access(conn, packet)
        if progress:
            progress(dict(completed=0, total=0, source_counts=[], failed=None,
                          message=f"All {len(reused)} sources were already read · no AI request needed"))
        fresh = dict(items=[], coverage_links=[], summary_policy=SUMMARY_POLICY,
                     model=REASONING_MODEL, prompt_version=PROMPT,
                     guard_policy=packet.get("guard_policy"),
                     batching=dict(policy=POLICY, completed=0, total=0, source_counts=[],
                                   comparison_limit=MAX_COMPARISONS,
                                   comparison_context_bounded=False))
        calls = []
    return sentiment_reuse.merge(packet, reused, fresh), calls


class BatchFailed(Exception):
    """One batch's request or result failed; carries what failure_details needs."""

    def __init__(self, index, call, error):
        super().__init__(str(error))
        self.index, self.call, self.error = index, call, error


def _run(packet, *, transport=None, progress=None, retry_failed=False, split_failed=False):
    from . import parallel
    from .sentiment import request_for, render, PROMPT
    parts = recovery_parts(plan(packet), split_failed=split_failed)
    if split_failed and not any(p.get("_split_child") for p in parts):
        # A stale recovery button must not turn into a fresh full-pool reading.
        for part in parts:
            saved, _ = prior_attempt(part)
            if saved is None:
                if has_attempt(part_identity(part)):
                    raise ledger.BudgetBlocked("An earlier AI request has no settled response. Smaller-batch recovery cannot resend it.")
                raise ValueError("No saved batch is ready for smaller-batch recovery. Refresh & analyse first.")
            render(saved, part)
    total = len(parts)
    calls = [None] * total
    sizes = [len(p["sources"]) for p in parts]
    lock = threading.RLock()

    def done():
        return sum(call is not None for call in calls)

    def report(message, failed=None, failure=None):
        if progress:
            # Batches run in parallel; progress (and a watch's lease renewal) is serialized.
            with lock:
                progress(dict(completed=done(), total=total, source_counts=sizes,
                              failed=failed, message=message,
                              **({'failure': failure} if failure else {})))

    report(f"0 of {total} batches complete · {len(packet['sources'])} eligible sources")
    # Saved batches are reused first (no network); only the rest are sent.
    pending = []
    for index, part in enumerate(parts):
        previous, attempt = prior_attempt(part)
        key = part_identity(part)
        if previous:
            try:
                render(previous, part)
            except ValueError as exc:
                if not retry_failed or attempt >= MAX_EXPLICIT_RETRIES or part.get("_split_child"):
                    details = failure_details(previous, exc)
                    if attempt == MAX_EXPLICIT_RETRIES and not part.get("_split_child") and len(part["sources"]) > 1:
                        details["split_available"] = True
                    message = failure_message(index + 1, total, done(), details, saved=True,
                                              unsent=total - done() - 1)
                    message += " The one explicit retry has also been used." if attempt else " Refresh & analyse can retry this batch once if its inputs are unchanged; paid AI uses the existing allowance."
                    report(message, index + 1, details)
                    raise ValueError(message) from None
                key += f":retry:{attempt + 1}"
                if has_attempt(key):
                    raise ledger.BudgetBlocked("The explicit retry has no usable settled response. It was not resent.")
            else:
                calls[index] = previous
                continue
        elif has_attempt(key):
            raise ledger.BudgetBlocked("An earlier AI request has no settled response. It was not resent; review its charge before starting a separate re-read.")
        elif part.get("_split_child") and not split_failed:
            message = "Smaller-batch recovery is unfinished. Choose Retry with smaller batches to continue explicitly."
            report(message, index + 1, dict(code="split_unfinished", reason=message, split_available=True))
            raise ledger.BudgetBlocked(message)
        pending.append((index, part, key))
    if done():
        report(f"{done()} of {total} batches complete · reused saved results")

    def task(index, part, key):
        def send():
            # A stopped watch or replaced run raises here, before anything is sent.
            report(f"{done()} of {total} batches complete · reading batch {index + 1}")
            with transaction() as conn:
                check_access(conn, packet)
            call = None
            try:
                call = ledger.execute(key, PROMPT, request_for(part), transport=transport)
                render(call, part)
            except Exception as exc:
                raise BatchFailed(index, call, exc) from None
            with lock:
                calls[index] = call
            report(f"{done()} of {total} batches complete")
        return send

    results, errors = parallel.run_all([task(*item) for item in pending])
    if errors:
        ordered = [errors[i] for i in sorted(errors)]
        # Stops, replaced runs and withdrawn sources keep their own exception.
        control = next((e for e in ordered if not isinstance(e, BatchFailed)), None)
        if control is not None:
            raise control
        blocked = next((e for e in ordered if isinstance(e.error, ledger.BudgetBlocked)), None)
        if blocked is not None:
            report(str(blocked.error), blocked.index + 1)
            raise blocked.error
        first = ordered[0]
        details = failure_details(first.call, first.error)
        if (first.call and first.call.get("request_key", "").endswith(":retry:1")
                and not parts[first.index].get("_split_child") and len(parts[first.index]["sources"]) > 1):
            details["split_available"] = True
        unsent = sum(result is parallel.SKIPPED for i, result in enumerate(results) if i not in errors)
        message = failure_message(first.index + 1, total, done(), details, unsent=unsent)
        if len(ordered) > 1:
            others = len(ordered) - 1
            message += f" {others} other batch{'es' if others != 1 else ''} running at the same time also stopped."
        report(message, first.index + 1, details)
        raise ValueError(message) from None
    with transaction() as conn:
        check_access(conn, packet)
    report("All batches complete · checking the combined result")
    result = combine(packet, parts, calls)
    result["batching"] = dict(policy=POLICY, completed=total, total=total, source_counts=sizes,
                             split_batches=sum(bool(p.get("_split_child")) for p in parts),
                             comparison_limit=MAX_COMPARISONS,
                             comparison_context_bounded=any(p['comparison_selection']['supplied'] < p['comparison_selection']['available'] for p in parts))
    return result, calls


def relevance_prefilter_empty(packet):
    """Every source was skipped by the quick check: no full-reading call is made."""
    from .sentiment import POLICY as SUMMARY_POLICY, PROMPT, summarize
    from thesis.providers.settings import SENTIMENT_MODEL as REASONING_MODEL
    return dict(items=[], coverage_links=[], summary=summarize([], packet["sources"], [], packet.get("comparison_sources", [])),
                summary_policy=SUMMARY_POLICY, model=REASONING_MODEL, prompt_version=PROMPT,
                guard_policy=packet.get("guard_policy"))
