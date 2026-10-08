"""Ordered immutable shared evidence snapshots, independent of private reasoning."""

import hashlib
from datetime import timezone
from psycopg.types.json import Jsonb
from thesis.db import one, rows
from .acquisition import latest_coverage


def story_snapshot(documents):
    superseded = {str(d["supersedes_id"]) for d in documents if d.get("supersedes_id")}
    values = {
        (
            d.get("story_key") or str(d["document_id"]),
            d.get("origin_key") or d["source_name"],
            (
                d.get("content_hash")
                if d.get("entitlement") in ("finnhub-pitch", "public-news")
                else d.get("body_hash")
                or hashlib.sha256(d["body"].encode()).hexdigest()
            ),
        )
        for d in documents
        if str(d["id"]) not in superseded
    }
    return [dict(story_key=s, origin_key=o, body_hash=h) for s, o, h in sorted(values)]


def capture_snapshot(conn, instrument_id):
    state = one(
        conn, "SELECT * FROM instrument_state WHERE instrument_id=%s", (instrument_id,)
    )
    docs = rows(
        conn,
        """SELECT v.*,d.instrument_id,s.entitlement,s.name source_name,l.origin_key,l.story_key,l.body_hash
      FROM document_versions v JOIN documents d ON d.id=v.document_id JOIN sources s ON s.id=d.source_id
      LEFT JOIN document_lineage l ON l.document_version_id=v.id
      WHERE d.instrument_id=%s AND s.entitlement IN ('fictional','sec-public','finnhub-pitch','public-news') AND v.available_at<=%s ORDER BY v.available_at,v.id""",
        (instrument_id, state["cutoff"]),
    )
    docids = [str(d["id"]) for d in docs]
    from .sec.checkpoint import active_document, current_documents

    active_id = active_document(conn, instrument_id, state["cutoff"], docs)
    factdocs = [active_id] if active_id else docids
    facts = rows(
        conn,
        "SELECT id FROM observations WHERE document_version_id=ANY(%s::uuid[]) AND available_at<=%s ORDER BY available_at,id",
        (factdocs, state["cutoff"]),
    )
    checks, freshness = latest_coverage(conn, instrument_id, state["cutoff"])
    payload = dict(
        instrument_id=str(instrument_id),
        document_ids=docids,
        observation_ids=[str(f["id"]) for f in facts],
        source_check_ids=[str(c["id"]) for c in checks if c["id"]],
        cutoff=state["cutoff"].astimezone(timezone.utc).isoformat(),
        period=state["period"],
        stage=state["sequence"],
        mode=(
            "recorded-available-at"
            if state["mode"] == "recorded"
            else "sec-first-retrieved"
        ),
        period_type=state["period_type"],
        freshness=freshness,
        source_states={c["source_id"]: c["state"] for c in checks},
        stories=story_snapshot(current_documents(docs, active_id)),
        active_document_id=active_id,
    )
    # Replaying an exact batch must not manufacture a new transition.
    previous = one(
        conn,
        "SELECT * FROM research_snapshots WHERE instrument_id=%s ORDER BY id DESC LIMIT 1",
        (instrument_id,),
    )
    if previous and previous["payload"] == payload:
        return previous
    return one(
        conn,
        "INSERT INTO research_snapshots(instrument_id,cutoff,payload) VALUES(%s,%s,%s) RETURNING *",
        (instrument_id, state["cutoff"], Jsonb(payload)),
    )
