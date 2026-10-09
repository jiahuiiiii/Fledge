"""Bounded, dated parent context for new HN classifications; never extra votes."""

import hashlib
from datetime import datetime, timedelta
from thesis.db import one
from thesis.providers.ledger import canonical
from .citations import source_passages

POLICY = "saved-parent-context-1"
MAX_BYTES = 8000
MAX_PARENT_BYTES = 3000
MAX_PARENTS = 4


def attach(conn, sources, cutoff, *, batch_limits=True):
    used_bytes = count = 0
    for source in sources:
        if source.get("platform") not in {"hackernews", "reddit"}:
            continue
        source.pop("conversation", None)
        source["context_status"] = "not_saved"
        row = one(
            conn,
            """SELECT r.* FROM social_conversation_state s
            JOIN social_conversation_results r ON r.id=s.latest_result_id
            WHERE s.post_id=%s AND r.checked_at<=%s""",
            (source["id"], cutoff),
        )
        if not row:
            continue
        source["context_status"] = row["outcome"]
        if row["outcome"] != "available":
            continue
        if one(
            conn, "SELECT 1 FROM hn_withdrawals WHERE post_key=%s UNION SELECT 1 FROM social_withdrawals WHERE post_key=%s", (row["parent_key"],row["parent_key"])
        ):
            source["context_status"] = "withdrawn"
            continue
        if cutoff - row["checked_at"] > timedelta(hours=24):
            source["context_status"] = "old_check"
            continue
        passages, omitted = source_passages(row["title"], row["body"])
        if row["parent_type"] == "comment":
            passages = [p for p in passages if p["id"] != "p0"]
        size = len(canonical(passages).encode())
        if not passages:
            source["context_status"] = "no_complete_passages"
            continue
        if (
            (batch_limits and count >= MAX_PARENTS)
            or size > MAX_PARENT_BYTES
            or (batch_limits and used_bytes + size > MAX_BYTES)
        ):
            source["context_status"] = "sample_limit"
            continue
        context = dict(
            result_id=str(row["id"]),
            post_id=source["id"],
            parent_key=row["parent_key"],
            parent_type=row["parent_type"],
            title=row["title"],
            body=row["body"],
            url=row["url"],
            published_at=row["published_at"].isoformat(),
            checked_at=row["checked_at"].isoformat(),
            passages=passages,
            omitted_fragment_count=omitted,
        )
        # Rechecking identical text does not cause another paid classification.
        context["content_key"] = hashlib.sha256(
            canonical(wire(context)).encode()
        ).hexdigest()
        source["conversation"] = context
        source["context_status"] = "included"
        count += 1
        used_bytes += size


def wire(context):
    return {
        k: context[k] for k in ("parent_key", "parent_type", "published_at", "passages")
    }


def allowed(conn, source):
    context = source.get("conversation")
    if not context:
        return True
    # A derived reading consumes this exact immutable parent version. A later
    # different/failed check cannot silently substitute another context.
    row = one(
        conn,
        "SELECT * FROM social_conversation_results WHERE id=%s AND post_id=%s",
        (context["result_id"], source["id"]),
    )
    return bool(
        row
        and row["outcome"] == "available"
        and row["parent_key"] == context["parent_key"]
        and not one(
            conn,
            "SELECT 1 FROM hn_withdrawals WHERE post_key=%s UNION SELECT 1 FROM social_withdrawals WHERE post_key=%s",
            (context["parent_key"],context["parent_key"]),
        )
    )


def changed_common_context(previous, current, channel, platform):
    def selected(packet):
        return {
            s["content_hash"]: (s.get("conversation") or {}).get("content_key")
            for s in packet["sources"]
            if s["channel"] == channel
            and (not platform or s.get("platform", "reddit") == platform)
        }

    old, new = selected(previous), selected(current)
    return any(old[k] != new[k] for k in old.keys() & new.keys())


def evidence(source, passage_ids):
    context = source.get("conversation")
    if not context:
        if passage_ids:
            raise ValueError("No conversation context was supplied for this item.")
        return None
    passages = {p["id"]: p["quote"] for p in context["passages"]}
    if (
        not passage_ids
        or len(passage_ids) != len(set(passage_ids))
        or any(p not in passages for p in passage_ids)
    ):
        raise ValueError(
            "Context-aware labels require exact passages from their own parent."
        )
    return {
        k: context[k]
        for k in (
            "result_id",
            "parent_type",
            "title",
            "body",
            "url",
            "published_at",
            "checked_at",
        )
    } | dict(
        citations=[dict(passage_id=p, quote=passages[p]) for p in passage_ids],
        limitation="Immediate parent used as context, not another sentiment vote or proof that the commenter agrees. Parent text was checked at the shown time; historical edits are unknown.",
    )
