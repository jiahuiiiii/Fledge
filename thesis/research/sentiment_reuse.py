"""Reuse a source's saved classification instead of paying to read it again.

A reading covers every eligible source in its window, so hourly readings used
to send the same texts to the AI again and again (each text ~3.7 times on
average across 11-13 Oct 2026). A source whose model-visible content is
unchanged keeps the label from the latest earlier reading made with the same
prompt and policies. Original item models remain recorded across model switches.

Coverage links only point from a newer report to an earlier one, so a link
saved with its newer report stays valid while both reports remain in the
window. Counts are always recalculated over the whole current sample.
"""
import hashlib
from copy import deepcopy

from thesis.db import rows
from thesis.providers import ledger
from . import sentiment_reliability

POLICY = "sentiment-source-reuse-1"
# Earlier readings searched for saved labels: enough to cover a 30-day window
# of hourly watches without reading every historical packet.
LOOKBACK_READINGS = 40


def content_key(source):
    """Everything the classifier saw for this source, except its batch label."""
    from .citations import model_source
    from . import sentiment_context

    value = dict(
        model_source(source),
        passages=source["passages"],
        channel=source["channel"],
        platform=source.get("platform"),
        publisher=source.get("publisher"),
        published_at=source.get("published_at"),
        social_kind=source.get("social_kind"),
        discovery_match=source.get("discovery_match"),
        price_reference=source.get("price_reference"),
        thread_context_key=source.get("thread_context_key"),
        conversation=(
            sentiment_context.wire(source["conversation"])
            if source.get("conversation")
            else None
        ),
    )
    return hashlib.sha256(ledger.canonical(value).encode()).hexdigest()


def compatible(record, packet):
    from .sentiment import PROMPT, POLICY as SUMMARY_POLICY
    from thesis.providers.settings import REASONING_MODEL

    result, saved = record["result"], record["packet"]
    from . import sentiment_task_runner, sentiment_tasks
    accepted_prompts={PROMPT}
    if sentiment_task_runner.enabled():
        accepted_prompts={sentiment_tasks.PROMPT}
        if sentiment_reliability.enabled():accepted_prompts.add(PROMPT)
    return (
        result.get("prompt_version") in accepted_prompts
        and (sentiment_reliability.enabled() or result.get("model") == REASONING_MODEL)
        and result.get("summary_policy") == SUMMARY_POLICY
        and result.get("guard_policy") == packet.get("guard_policy")
        and saved.get("reporting_policy") == packet.get("reporting_policy")
        and saved.get("context_policy") == packet.get("context_policy")
        and saved.get("reddit_thread_policy") == packet.get("reddit_thread_policy")
    )


def usable_item(record, item):
    from . import relevance_prefilter

    # A quick-check skip is reused only under the current quick-check policy.
    return not item.get("prefilter") or (
        (record["result"].get("prefilter") or {}).get("policy") == relevance_prefilter.POLICY
    )


def find(conn, packet):
    """Return {source_id: saved} for current sources with an unchanged saved label.

    saved = dict(item=..., links=[...], analysis_id=..., call_id=...).
    """
    wanted = {content_key(s): s for s in packet["sources"]}
    found = {}
    for record in rows(
        conn,
        "SELECT id,call_id,packet,result FROM sentiment_analyses WHERE instrument_id=%s "
        "ORDER BY created_at DESC,id DESC LIMIT %s",
        (packet["instrument_id"], LOOKBACK_READINGS),
    ):
        if len(found) == len(wanted):
            break
        if not compatible(record, packet):
            continue
        saved_sources = {s["id"]: s for s in record["packet"]["sources"]}
        links = {}
        for link in record["result"].get("coverage_links", []):
            links.setdefault(link["source_id"], []).append(link)
        for item in record["result"].get("items", []):
            source = saved_sources.get(item.get("source_id"))
            if not source or not usable_item(record, item):
                continue
            key = content_key(source)
            current = wanted.get(key)
            if not current or current["id"] in found or current["id"] != source["id"]:
                continue
            copied = deepcopy(item)
            if sentiment_reliability.enabled():
                original_model = ((record["result"].get("prefilter") or {}).get("model")
                                  if item.get("prefilter") else record["result"].get("model"))
                copied["model"] = copied.get("model") or original_model
                from . import sentiment_task_runner
                if sentiment_task_runner.enabled():
                    copied.setdefault('prompt_version',record['result'].get('prompt_version'))
                if item.get("prefilter"):
                    copied.setdefault("call_ids", (record["result"].get("prefilter") or {}).get("call_ids", []))
                else:
                    copied["call_id"] = copied.get("call_id") or str(record["call_id"])
            found[current["id"]] = dict(
                item=copied,
                links=links.get(source["id"], []),
                analysis_id=str(record["id"]),
                call_id=record["call_id"],
            )
    return found


def merge(packet, reused, fresh):
    """Combine reused labels with the new reading and recount the whole sample."""
    from .sentiment import summarize

    labels = {s["id"]: s["label"] for s in packet["sources"]}
    ids = set(labels)
    order = {s["id"]: n for n, s in enumerate(packet["sources"])}
    items = list(fresh.get("items", []))
    links = list(fresh.get("coverage_links", []))
    for source_id, saved in reused.items():
        # Labels are batch-local; keep the saved reading, refresh only its label.
        items.append(dict(deepcopy(saved["item"]), id=labels[source_id]))
        links += [
            deepcopy(link) for link in saved["links"]
            if link.get("reference_source_id") in ids
        ]
    items.sort(key=lambda i: order[i["source_id"]])
    if [i["source_id"] for i in items] != [s["id"] for s in packet["sources"]]:
        raise ValueError("Every source must be read or reused exactly once.")
    result = dict(
        fresh,
        items=items,
        coverage_links=links,
        summary=summarize(items, packet["sources"], links, []),
        source_reuse=dict(
            policy=POLICY,
            reused=len(reused),
            new=len(packet["sources"]) - len(reused),
            analysis_ids=sorted({s["analysis_id"] for s in reused.values()}),
        ),
    )
    if result.get("prefilter") or any(i.get("prefilter") for i in items):
        record = dict(result.get("prefilter") or {})
        from . import relevance_prefilter

        record.setdefault("policy", relevance_prefilter.POLICY)
        record["checked_now"] = record.get("checked", 0)
        record["skipped_now"] = record.get("skipped", 0)
        # Totals describe the whole saved reading, including reused quick checks.
        record["skipped"] = sum(1 for i in items if i.get("prefilter"))
        record["checked"] = record["checked_now"] + len(reused)
        result["prefilter"] = record
    if sentiment_reliability.enabled():
        result["repairs"] = sentiment_reliability.counts(items)
    return result
