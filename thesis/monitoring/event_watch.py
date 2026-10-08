"""An explicitly selected approved revision; uses news-watch acquisition and budget."""

from thesis.db import transaction, one


def configure(owner, iid, version_id):
    from thesis.service import Conflict

    with transaction(owner) as c:
        # Same lock order as event-result activation: idea, then watch.
        idea = one(
            c,
            "SELECT * FROM theses WHERE owner_id=%s AND instrument_id=%s FOR UPDATE",
            (owner, iid),
        )
        watch = one(
            c,
            "SELECT * FROM news_watches WHERE owner_id=%s AND instrument_id=%s FOR UPDATE",
            (owner, iid),
        )
        if not watch:
            raise ValueError(
                "Enable the company news watch before selecting event checks."
            )
        if version_id:
            approved = one(
                c,
                """SELECT v.id FROM thesis_versions v WHERE v.owner_id=%s AND v.id=%s
                AND v.thesis_id=%s AND v.revision=%s AND v.status='monitoring'
                AND EXISTS(SELECT 1 FROM version_events e WHERE e.owner_id=v.owner_id AND e.version_id=v.id)""",
                (
                    owner,
                    version_id,
                    idea["id"] if idea else None,
                    idea["revision"] if idea else None,
                ),
            )
            if not watch["enabled"] or not approved or idea["status"] != "monitoring":
                raise Conflict(
                    "Choose the currently approved event revision while the news watch is on."
                )
        if str(watch["event_version_id"] or "") != str(version_id or ""):
            c.execute(
                "UPDATE news_watches SET event_version_id=%s,claim_token=NULL,lease_until=NULL WHERE owner_id=%s AND instrument_id=%s",
                (version_id, owner, iid),
            )
        return dict(event_version_id=str(version_id) if version_id else None)


def active(c, owner, iid, version_id, token, snapshot_id=None):
    idea = one(
        c,
        "SELECT t.status,v.id FROM theses t JOIN thesis_versions v ON v.thesis_id=t.id AND v.owner_id=t.owner_id AND v.revision=t.revision WHERE t.owner_id=%s AND t.instrument_id=%s FOR UPDATE OF t",
        (owner, iid),
    )
    watch = one(
        c,
        "SELECT enabled,claim_token,lease_until,event_version_id FROM news_watches WHERE owner_id=%s AND instrument_id=%s FOR UPDATE",
        (owner, iid),
    )
    from datetime import datetime, timezone

    good = bool(
        idea
        and watch
        and idea["status"] == "monitoring"
        and str(idea["id"]) == str(version_id)
        and watch["enabled"]
        and str(watch["event_version_id"]) == str(version_id)
        and watch["claim_token"] == token
        and watch["lease_until"]
        and watch["lease_until"] > datetime.now(timezone.utc)
    )
    if good and snapshot_id is not None:
        latest = one(
            c,
            "SELECT max(id) id FROM research_snapshots WHERE instrument_id=%s",
            (iid,),
        )
        good = latest["id"] == snapshot_id
    return good


def run(owner, iid, version_id, token, *, transport=None):
    from thesis.research import event_review

    with transaction(owner) as c:
        if not active(c, owner, iid, version_id, token):
            return dict(status="approval_changed")
        snapshot = one(
            c,
            "SELECT id FROM research_snapshots WHERE instrument_id=%s ORDER BY id DESC LIMIT 1",
            (iid,),
        )
    try:
        return event_review.generate(
            owner,
            str(version_id),
            snapshot["id"],
            transport=transport,
            watch_guard=(iid, token),
        )
    except event_review.NoEligibleEvidence:
        return dict(status="no_eligible_evidence")
