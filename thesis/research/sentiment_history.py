"""Read-only comparison of recorded source samples, never a market trend."""

from datetime import datetime
from thesis.db import transaction, one, rows
from thesis.service import Missing
from . import sentiment
from .sentiment_context import changed_common_context


def record(conn, iid, identity):
    value = one(
        conn,
        "SELECT * FROM sentiment_analyses WHERE instrument_id=%s AND id=%s",
        (iid, identity),
    )
    if not value:
        raise Missing("Sentiment sample not found for this company.")
    return value


def method(value):
    r = value["result"]
    return {k: r.get(k) for k in ("model", "prompt_version", "summary_policy")}


def summary(conn, value):
    visible = sentiment.present(conn, value)
    item = dict(
        id=visible["id"],
        cutoff=visible["cutoff"],
        created_at=value["created_at"].isoformat(),
        withheld=visible["withheld"],
    )
    if not item["withheld"]:
        item.update(
            summary=visible["summary"],
            coverage=visible["coverage"],
            method=method(value),
            earlier_method=value["result"].get("prompt_version") != sentiment.PROMPT
            or value["result"].get("summary_policy") != sentiment.POLICY,
        )
    return item


def history(iid, before=None):
    with transaction(consistent=True) as conn:
        if not sentiment.market_brief.company_for(iid):
            raise Missing("Choose a supported company.")
        cursor = record(conn, iid, before) if before else None
        condition = (
            " AND ((packet->>'cutoff')::timestamptz,created_at,id)<(%s,%s,%s)"
            if cursor
            else ""
        )
        params = [iid]
        if cursor:
            params += [
                datetime.fromisoformat(cursor["packet"]["cutoff"]),
                cursor["created_at"],
                cursor["id"],
            ]
        values = rows(
            conn,
            "SELECT * FROM sentiment_analyses WHERE instrument_id=%s"
            + condition
            + " ORDER BY (packet->>'cutoff')::timestamptz DESC,created_at DESC,id DESC LIMIT 21",
            params,
        )
        return dict(
            items=[summary(conn, v) for v in values[:20]],
            next_cursor=str(values[19]["id"]) if len(values) > 20 else None,
        )


def key(value):
    return (
        datetime.fromisoformat(value["packet"]["cutoff"]),
        value["created_at"],
        str(value["id"]),
    )


def texts(value, channel):
    items = {i["source_id"]: i for i in value["result"]["items"]}
    return {
        s["content_hash"]: dict(source_id=s["id"], item=items[s["id"]])
        for s in value["packet"]["sources"]
        if s["channel"] == channel
    }


def signature(item):
    return tuple(item[k] for k in ("relevance", "sentiment", "statement", "topic"))


def context(value):
    return {
        (s["channel"], s["content_hash"])
        for s in value["packet"].get("comparison_sources", [])
    }


def links(value):
    sources = {
        s["id"]: s["content_hash"]
        for s in value["packet"]["sources"]
        + value["packet"].get("comparison_sources", [])
    }
    return {
        (sources[c["source_id"]], sources[c["reference_source_id"]], c["relation"])
        for c in value["result"].get("coverage_links", [])
    }


def compare(iid, before, after):
    with transaction(consistent=True) as conn:
        previous, current = record(conn, iid, before), record(conn, iid, after)
        if key(previous) >= key(current):
            raise ValueError(
                "Choose an earlier sample and a later sample in source-cutoff order."
            )
        a, b = sentiment.present(conn, previous), sentiment.present(conn, current)
        if a["withheld"] or b["withheld"]:
            # Do not leak a withdrawn source through a derived delta or the other side.
            return dict(
                withheld=True, before_id=str(before), after_id=str(after), channels={}
            )
        channels = {}
        for channel in ("news", "social"):
            old, new = texts(previous, channel), texts(current, channel)
            changed = []
            counts = dict(added=0, removed=0, relabeled=0, unchanged=0)
            for identity in sorted(old.keys() | new.keys()):
                left, right = old.get(identity), new.get(identity)
                status = (
                    "added"
                    if left is None
                    else (
                        "removed"
                        if right is None
                        else (
                            "relabeled"
                            if signature(left["item"]) != signature(right["item"])
                            else "unchanged"
                        )
                    )
                )
                counts[status] += 1
                changed.append(dict(change=status, before=left, after=right))
            changed.sort(
                key=lambda v: (
                    list(counts).index(v["change"]),
                    (v["after"] or v["before"])["source_id"],
                )
            )
            channels[channel] = dict(counts=counts, items=changed)
        return dict(
            withheld=False,
            before=a,
            after=b,
            channels=channels,
            before_method=method(previous),
            after_method=method(current),
            method_changed=method(previous) != method(current),
            same_selected_text=all(
                c["counts"]["added"] == c["counts"]["removed"] == 0
                for c in channels.values()
            ),
            comparison_context_changed=context(previous) != context(current),
            parent_context_changed=changed_common_context(
                previous["packet"], current["packet"], "social", "hackernews"
            ),
            grouping_changed=links(previous) != links(current),
        )
