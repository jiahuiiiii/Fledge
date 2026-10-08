"""The committed SEC checkpoint can reactivate an earlier immutable source version."""

import json
from thesis.db import one


def current_documents(documents, active_id):
    """SEC uses its committed checkpoint; other sources use their version chains."""
    superseded = {
        str(d["supersedes_id"])
        for d in documents
        if d.get("supersedes_id") and d.get("entitlement") != "sec-public"
    }
    return [
        d
        for d in documents
        if (
            str(d["id"]) == active_id
            if d.get("entitlement") == "sec-public"
            else str(d["id"]) not in superseded
        )
    ]


def active_document(conn, instrument_id, cutoff, documents):
    public = [d for d in documents if d.get("entitlement") == "sec-public"]
    if not public:
        return None
    check = one(
        conn,
        "SELECT cursor FROM source_checks WHERE instrument_id=%s AND source_id='sec-companyfacts' AND outcome='success' AND checked_at<=%s ORDER BY checked_at DESC,received_at DESC,id DESC LIMIT 1",
        (instrument_id, cutoff),
    )
    if check and check["cursor"]:
        try:
            checkpoint = json.loads(check["cursor"])
            selected = (
                checkpoint.get("document_version_id")
                if isinstance(checkpoint, dict)
                else None
            )
            if selected and any(str(d["id"]) == selected for d in public):
                return selected
        except (ValueError, TypeError):
            pass
    # Compatibility for earlier accession-only checkpoints.
    return str(max(public, key=lambda d: (d["available_at"], str(d["id"])))["id"])
