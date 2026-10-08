import hashlib
import json
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from psycopg.types.json import Jsonb
from .config import OWNER, INSTRUMENT
from .db import transaction, one, rows
from .fixtures import STAGES, ingest, prices
from .monitoring.evaluator import (
    evaluate,
    VERSION,
    LEGACY_VERSION,
    REPORT_VERSION,
    manifest_conditions,
)
from .monitoring.age import age_states, instant
from .monitoring.report_expectations import states as report_states
from .monitoring.events import window_state as event_window_state
from .research.pipeline import evidence_from_articles
from .research.facts import fundamentals, coverage, active_facts
from .research.acquisition import latest_coverage, ingest_batch
from .research.recorded import recorded_batch, AURORA
from .research.snapshots import story_snapshot
from .research.sec.service import capabilities as sec_capabilities
from .research.sec.performance import present as performance_present
from .research.briefs import baseline, source_packet, cached_selection, select_passages


class Conflict(ValueError):
    pass


class Missing(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def stage_info(conn, instrument_id=INSTRUMENT):
    record = one(
        conn, "SELECT * FROM instrument_state WHERE instrument_id=%s", (instrument_id,)
    )
    if not record:
        raise Missing("This company is not supported yet.")
    return dict(
        stage=record["sequence"],
        as_of=record["cutoff"].astimezone(timezone.utc).isoformat(),
        period=record["period"],
        label=record["label"],
        complete=record["scenario_complete"],
        mode=record["mode"],
        period_type=record["period_type"],
    )


def permitted_documents(conn, cutoff, instrument_id=INSTRUMENT):
    return rows(
        conn,
        """SELECT v.*,d.instrument_id,d.url,coalesce(m.publisher,s.name) source_name,s.entitlement,l.origin_key,l.story_key,l.body_hash
       FROM document_versions v JOIN documents d ON d.id=v.document_id JOIN sources s ON s.id=d.source_id
       LEFT JOIN document_lineage l ON l.document_version_id=v.id
       LEFT JOIN market_articles m ON m.document_version_id=v.id
       WHERE d.instrument_id=%s AND s.entitlement IN ('fictional','sec-public','finnhub-pitch','public-news') AND v.available_at<=%s ORDER BY v.available_at,v.id""",
        (instrument_id, cutoff),
    )


def version_instrument(conn, owner, version_id):
    record = one(
        conn,
        "SELECT t.instrument_id FROM thesis_versions v JOIN theses t ON t.id=v.thesis_id AND t.owner_id=v.owner_id WHERE v.id=%s AND v.owner_id=%s",
        (version_id, owner),
    )
    if not record:
        raise Missing("Saved idea not found.")
    return str(record["instrument_id"])


from .monitoring.event_windows import current as event_window


def manifest_events(events):
    # Default publication meaning predates this column; retain old job identities.
    return [
        {
            k: v
            for k, v in e.items()
            if not (
                (k == "date_basis" and v == "report_publication")
                or (k == "repeat_months" and v == 0)
                or (k == "repeat_count" and v == 1)
            )
        }
        for e in events
    ]


def manifest_for(conn, owner, version_id, snapshot=None, assessed_at=None):
    instrument_id = version_instrument(conn, owner, version_id)
    snapshot = snapshot or one(
        conn,
        "SELECT * FROM research_snapshots WHERE instrument_id=%s ORDER BY id DESC LIMIT 1",
        (instrument_id,),
    )
    if not snapshot or str(snapshot["instrument_id"]) != instrument_id:
        raise Missing("No company evidence snapshot is available")
    conditions = rows(
        conn,
        "SELECT * FROM version_conditions WHERE owner_id=%s AND version_id=%s ORDER BY condition_id",
        (owner, version_id),
    )
    events = rows(
        conn,
        "SELECT * FROM version_events WHERE owner_id=%s AND version_id=%s ORDER BY condition_id",
        (owner, version_id),
    )
    from .research.event_review import reusable

    clock = instant(assessed_at or snapshot["cutoff"])
    event_review, event_reuse = (
        reusable(conn, owner, version_id, snapshot["id"], clock=clock)
        if events
        else (None, None)
    )
    if clock < snapshot["cutoff"]:
        raise ValueError("Assessment time cannot precede its evidence cutoff")
    facts = snapshot_facts(conn, snapshot)
    # Coverage is measured at this logical assessment, with no new source request.
    checks, freshness = snapshot_coverage(conn, snapshot, clock)
    return dict(
        snapshot["payload"],
        snapshot_id=snapshot["id"],
        version_id=str(version_id),
        conditions=json.loads(canonical(manifest_conditions(conditions))),
        events=json.loads(canonical(manifest_events(events))),
        event_review_id=str(event_review["id"]) if event_review else None,
        **(dict(event_review_reuse=event_reuse) if event_reuse else {}),
        **(
            {
                "report_expectations": report_states(
                    conditions, facts, snapshot["payload"]["period"], clock
                )
            }
            if any(c.get("expected_period_end") is not None for c in conditions)
            else {}
        ),
        evaluator=(
            REPORT_VERSION
            if any(c.get("expected_period_end") is not None for c in conditions)
            else (
                VERSION
                if any(c.get("role") == "risk" for c in conditions)
                else LEGACY_VERSION
            )
        ),
        model="none",
        assessed_at=clock.isoformat(),
        expiry=age_states(conditions, facts, snapshot["payload"]["period"], clock),
        expiry_method="report-period-age-1",
        event_windows=[
            dict(
                condition_id=str(e["condition_id"]),
                state=event_window_state(e, clock),
                **(
                    {"window": event_window(e, clock)} if e.get("repeat_months") else {}
                ),
            )
            for e in events
        ],
        freshness=freshness,
        source_states={c["source_id"]: c["state"] for c in checks},
        source_check_ids=[str(c["id"]) for c in checks if c["id"]],
    )


def snapshot_facts(conn, snapshot):
    return rows(
        conn,
        "SELECT o.*,coalesce(s.period_type,'quarter') period_type FROM observations o LEFT JOIN fact_scopes s ON s.observation_id=o.id WHERE o.id=ANY(%s::uuid[]) ORDER BY available_at,o.id",
        (snapshot["payload"]["observation_ids"],),
    )


def material_signature(manifest):
    # Exclude polling timestamps/check IDs. Preserve the complete first manifest
    # for each meaningful input set and show latest coverage separately.
    value = {
        key: manifest.get(key)
        for key in (
            "version_id",
            "evaluator",
            "mode",
            "expiry",
            "instrument_id",
            "conditions",
            "events",
            "event_review_id",
            "event_windows",
            "period",
            "period_type",
            "freshness",
            "source_states",
            "stories",
            "observation_ids",
        )
    }
    if "report_expectations" in manifest:
        value["report_expectations"] = manifest["report_expectations"]
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def queue_version(conn, owner, version_id, snapshot=None, assessed_at=None):
    conn.execute(
        "SELECT pg_advisory_xact_lock(hashtextextended(%s,0))",
        ("queue:" + str(owner) + str(version_id),),
    )
    manifest = manifest_for(conn, owner, version_id, snapshot, assessed_at)
    signature = material_signature(manifest)
    previous = one(
        conn,
        "SELECT * FROM jobs WHERE owner_id=%s AND version_id=%s ORDER BY queue_order DESC LIMIT 1",
        (owner, version_id),
    )
    if previous:
        if instant(
            previous["manifest"].get("assessed_at", previous["manifest"]["cutoff"])
        ) > instant(manifest["assessed_at"]):
            return dict(id=previous["id"], status=previous["status"])
        if previous["input_signature"] == signature:
            return dict(id=previous["id"], status=previous["status"])
        if previous["input_signature"] is None and all(
            previous["manifest"].get(k) == manifest.get(k)
            for k in (
                "version_id",
                "conditions",
                "document_ids",
                "observation_ids",
                "period",
                "freshness",
                "evaluator",
                "mode",
                "expiry",
            )
        ):
            return dict(id=previous["id"], status=previous["status"])
    fingerprint = hashlib.sha256(canonical(manifest).encode()).hexdigest()
    return one(
        conn,
        """INSERT INTO jobs(id,owner_id,version_id,fingerprint,manifest,input_signature) VALUES(%s,%s,%s,%s,%s,%s)
      ON CONFLICT(owner_id,fingerprint) DO UPDATE SET fingerprint=EXCLUDED.fingerprint RETURNING id,status""",
        (uuid4(), owner, version_id, fingerprint, Jsonb(manifest), signature),
    )


def snapshot_coverage(conn, snapshot, clock):
    checks = rows(
        conn,
        "SELECT * FROM source_checks WHERE id=ANY(%s::uuid[])",
        (snapshot["payload"]["source_check_ids"],),
    )
    by_source = {c["source_id"]: c for c in checks}
    result = []
    for source in snapshot["payload"]["source_states"]:
        c = by_source.get(source)
        state = (
            "unknown"
            if not c
            else (
                c["outcome"]
                if c["outcome"] != "success"
                else (
                    "stale"
                    if not c["covered_through"]
                    or clock - c["covered_through"] > timedelta(hours=24)
                    else "fresh"
                )
            )
        )
        result.append(
            dict(c or {}, source_id=source, id=c["id"] if c else None, state=state)
        )
    freshness = (
        "unknown"
        if not result or any(c["state"] == "unknown" for c in result)
        else "stale" if any(c["state"] != "fresh" for c in result) else "fresh"
    )
    return result, freshness


def queue_expiries(conn, owner, version_id, snapshot, after, until, inclusive=False):
    from .monitoring.events import boundaries as event_boundaries

    manifest = manifest_for(conn, owner, version_id, snapshot, until)
    boundaries = sorted(
        {instant(a["expires_at"]) for a in manifest["expiry"] if a["expires_at"]}
        | set(event_boundaries(manifest.get("events", [])))
        | {instant(a["check_at"]) for a in manifest.get("report_expectations", [])}
    )
    for boundary in boundaries:
        if (after is None or boundary > after) and (
            boundary < until or inclusive and boundary == until
        ):
            queue_version(conn, owner, version_id, snapshot, boundary)


def queue_current(owner, now=None):
    from .research.sec.service import collection_lock

    with transaction(owner) as conn:
        # Same order as save and acquisition: shared collection before private queue.
        # This freezes the source watermark and wall-clock horizon together.
        collection_lock(conn)
        wall_clock = instant(now or datetime.now(timezone.utc))
        current = rows(
            conn,
            "SELECT v.id,v.start_snapshot,t.instrument_id FROM theses t JOIN thesis_versions v ON v.thesis_id=t.id AND v.owner_id=t.owner_id AND v.revision=t.revision WHERE t.status='monitoring' AND t.owner_id=%s ORDER BY v.id",
            (owner,),
        )
        for version in current:
            conn.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s,0))",
                ("queue:" + str(owner) + str(version["id"]),),
            )
            cursor = one(
                conn,
                "SELECT * FROM monitoring_cursors WHERE owner_id=%s AND version_id=%s",
                (owner, version["id"]),
            )
            after = (
                cursor["last_snapshot"]
                if cursor
                else max(0, version["start_snapshot"] - 1)
            )
            base = one(
                conn,
                "SELECT * FROM research_snapshots WHERE instrument_id=%s AND id=%s",
                (version["instrument_id"], after),
            )
            previous = one(
                conn,
                "SELECT manifest FROM jobs WHERE owner_id=%s AND version_id=%s ORDER BY queue_order DESC LIMIT 1",
                (owner, version["id"]),
            )
            through = cursor["assessed_through"] if cursor else None
            if through is None and previous:
                through = instant(
                    previous["manifest"].get(
                        "assessed_at", previous["manifest"]["cutoff"]
                    )
                )
            snapshots = rows(
                conn,
                "SELECT * FROM research_snapshots WHERE instrument_id=%s AND id>%s ORDER BY id",
                (version["instrument_id"], after),
            )
            for snapshot in snapshots:
                boundary = snapshot["cutoff"]
                if base and (through is None or boundary > through):
                    queue_expiries(conn, owner, version["id"], base, through, boundary)
                queue_version(conn, owner, version["id"], snapshot, boundary)
                base = snapshot
                through = max(through, boundary) if through else boundary
            if not base:
                continue
            horizon = (
                base["cutoff"]
                if base["payload"]["mode"] == "recorded-available-at"
                else max(base["cutoff"], wall_clock)
            )
            horizon = max(horizon, through) if through else horizon
            queue_expiries(conn, owner, version["id"], base, through, horizon, True)
            queue_version(conn, owner, version["id"], base, horizon)
            conn.execute(
                "INSERT INTO monitoring_cursors VALUES(%s,%s,%s,%s) ON CONFLICT(owner_id,version_id) DO UPDATE SET last_snapshot=EXCLUDED.last_snapshot,assessed_through=EXCLUDED.assessed_through",
                (owner, version["id"], base["id"], horizon),
            )


def save_idea(owner, payload):
    with transaction(owner) as conn:
        return _save_revision(conn, owner, payload)


def _save_revision(conn, owner, payload):
    if payload.status == "monitoring" and (
        not (payload.conditions or payload.events) or not payload.reasoning.strip()
    ):
        raise ValueError(
            "Add your reasoning and at least one condition before approving monitoring."
        )
    instrument_id = str(payload.instrument_id)
    ids = [c.condition_id for c in [*payload.conditions, *payload.events]]
    if len(ids) != len(set(ids)):
        raise ValueError("Conditions must have unique identities.")
    from .research.sec.service import collection_lock

    collection_lock(conn)
    info = stage_info(conn, instrument_id)
    conn.execute(
        "SELECT pg_advisory_xact_lock(hashtextextended(%s,0))",
        (str(owner) + instrument_id,),
    )
    current = one(
        conn,
        "SELECT * FROM theses WHERE owner_id=%s AND instrument_id=%s FOR UPDATE",
        (owner, instrument_id),
    )
    revision = current["revision"] if current else 0
    if payload.expected_revision != revision:
        raise Conflict(
            "Your idea changed in another tab. Reload the latest revision before saving this draft."
        )
    thesis_id = current["id"] if current else uuid4()
    if not current:
        conn.execute(
            "INSERT INTO theses(id,owner_id,instrument_id,status) VALUES(%s,%s,%s,%s)",
            (thesis_id, owner, instrument_id, "draft"),
        )
    version_id = uuid4()
    revision += 1
    conn.execute(
        "INSERT INTO thesis_versions(id,owner_id,thesis_id,revision,question,reasoning,status,start_snapshot) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            version_id,
            owner,
            thesis_id,
            revision,
            payload.question,
            payload.reasoning.strip(),
            payload.status,
            one(
                conn,
                "SELECT max(id) n FROM research_snapshots WHERE instrument_id=%s",
                (instrument_id,),
            )["n"],
        ),
    )
    for condition in payload.conditions:
        conn.execute(
            "INSERT INTO version_conditions(owner_id,version_id,condition_id,metric,operator,threshold,unit,basis,period_type,max_report_age_days,role,expected_period_end,expected_report_by) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                owner,
                version_id,
                condition.condition_id,
                condition.metric,
                condition.operator,
                condition.threshold,
                condition.unit,
                condition.basis,
                condition.period_type,
                condition.max_report_age_days,
                condition.role,
                condition.expected_period_end,
                condition.expected_report_by,
            ),
        )
    for event in payload.events:
        conn.execute(
            "INSERT INTO version_events(owner_id,version_id,condition_id,description,evidence_requirement,role,window_start,deadline,date_basis,repeat_months,repeat_count) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                owner,
                version_id,
                event.condition_id,
                event.description,
                event.evidence_requirement,
                event.role,
                event.window_start,
                event.deadline,
                event.date_basis,
                event.repeat_months,
                event.repeat_count,
            ),
        )
    conn.execute(
        "UPDATE theses SET revision=%s,status=%s WHERE id=%s",
        (revision, payload.status, thesis_id),
    )
    job = (
        queue_version(
            conn,
            owner,
            version_id,
            assessed_at=(
                info["as_of"]
                if info["mode"] == "recorded"
                else datetime.now(timezone.utc)
            ),
        )
        if payload.status == "monitoring"
        else None
    )
    return dict(
        thesis_id=str(thesis_id), version_id=str(version_id), revision=revision, job=job
    )


def history(conn, owner, thesis_id):
    versions = rows(
        conn,
        "SELECT * FROM thesis_versions WHERE owner_id=%s AND thesis_id=%s ORDER BY revision DESC",
        (owner, thesis_id),
    )
    from .research.idea_review import public_result

    for version in versions:
        from .research.event_review import public_result as event_public_result

        version["events"] = rows(
            conn,
            "SELECT * FROM version_events WHERE owner_id=%s AND version_id=%s ORDER BY condition_id",
            (owner, version["id"]),
        )
        version["event_reviews"] = [
            event_public_result(r)
            for r in rows(
                conn,
                "SELECT r.*,EXISTS(SELECT 1 FROM event_review_activations a WHERE a.owner_id=r.owner_id AND a.review_id=r.id) activated FROM event_evidence_reviews r WHERE owner_id=%s AND version_id=%s ORDER BY created_at DESC,id",
                (owner, version["id"]),
            )
        ]
        version["evidence_reviews"] = [
            public_result(r)
            for r in rows(
                conn,
                "SELECT * FROM idea_evidence_reviews WHERE owner_id=%s AND version_id=%s ORDER BY created_at DESC,id",
                (owner, version["id"]),
            )
        ]
        version["conditions"] = rows(
            conn,
            "SELECT * FROM version_conditions WHERE owner_id=%s AND version_id=%s ORDER BY metric",
            (owner, version["id"]),
        )
        version["evaluations"] = rows(
            conn,
            """SELECT e.*,r.action review_action,r.created_at reviewed_at FROM evaluations e
           LEFT JOIN review_events r ON r.evaluation_id=e.id AND r.owner_id=e.owner_id
           LEFT JOIN jobs j ON j.owner_id=e.owner_id AND j.fingerprint=e.fingerprint
           WHERE e.owner_id=%s AND e.version_id=%s ORDER BY j.queue_order DESC NULLS LAST,e.manifest->>'cutoff' DESC,e.created_at DESC""",
            (owner, version["id"]),
        )
        for evaluation in version["evaluations"]:
            evaluation["event_results"] = rows(
                conn,
                "SELECT r.*,c.description,c.evidence_requirement,c.role,c.window_start,c.deadline,c.date_basis FROM event_results r JOIN version_events c USING(owner_id,version_id,condition_id) WHERE r.owner_id=%s AND r.evaluation_id=%s ORDER BY c.condition_id",
                (owner, evaluation["id"]),
            )
            by_event = {
                x["condition_id"]: x
                for x in evaluation["manifest"].get("event_windows", [])
            }
            for point in evaluation["event_results"]:
                selected_window = by_event.get(str(point["condition_id"]), {}).get(
                    "window"
                )
                if selected_window:
                    point["window"] = selected_window
            evaluation["results"] = rows(
                conn,
                """SELECT r.*,c.metric,c.operator,c.threshold,c.unit,c.basis,c.period_type,c.max_report_age_days,c.role,c.expected_period_end,c.expected_report_by FROM condition_results r
              JOIN version_conditions c USING(owner_id,version_id,condition_id) WHERE r.owner_id=%s AND r.evaluation_id=%s ORDER BY c.metric""",
                (owner, evaluation["id"]),
            )
    return versions


def state(owner, instrument_id=INSTRUMENT):
    from .research.market import workspace as market_workspace
    from .research.market_brief import packet_for, cached_brief, ordered_news
    from .research.sec.checkpoint import current_documents

    with transaction(owner, consistent=True) as conn:
        exists = one(conn, "SELECT id FROM instruments WHERE id=%s", (instrument_id,))
        if not exists:
            first = one(conn, "SELECT id FROM instruments ORDER BY symbol LIMIT 1")
            if not first:
                return dict(empty=True, catalogue=[], versions=[], instrument=dict(id=None, mode="empty"), research_action=None)
            if str(instrument_id) == INSTRUMENT:
                instrument_id = str(first["id"])
        info = stage_info(conn, instrument_id)
        documents = permitted_documents(conn, info["as_of"], instrument_id)
        docids = [d["id"] for d in documents]
        facts = rows(
            conn,
            "SELECT o.*,coalesce(s.period_type,'quarter') period_type FROM observations o LEFT JOIN fact_scopes s ON s.observation_id=o.id WHERE document_version_id=ANY(%s::uuid[]) AND available_at<=%s ORDER BY available_at,o.id",
            (docids, info["as_of"]),
        )
        from .research.sec.checkpoint import active_document

        active_id = active_document(conn, instrument_id, info["as_of"], documents)
        current_facts = active_facts(facts, documents, active_id)
        claims = rows(
            conn,
            "SELECT * FROM claims WHERE document_version_id=ANY(%s::uuid[]) AND available_at<=%s ORDER BY available_at DESC,id",
            (docids, info["as_of"]),
        )
        idea = one(
            conn,
            "SELECT * FROM theses WHERE owner_id=%s AND instrument_id=%s",
            (owner, instrument_id),
        )
        versions = history(conn, owner, idea["id"]) if idea else []
        from .research.event_review import scoped_point

        allowed_ids = {str(i) for i in docids}
        for version in versions:
            for review in version["event_reviews"]:
                review["events"] = [
                    scoped_point(p, allowed_ids) for p in review["events"]
                ]
            for evaluation in version["evaluations"]:
                if "report_expectations" in evaluation["manifest"] and not set(
                    evaluation["manifest"]["document_ids"]
                ).issubset(allowed_ids):
                    evaluation["manifest"]["report_expectations"] = [
                        dict(a, state="withheld", observed_period_end=None)
                        for a in evaluation["manifest"]["report_expectations"]
                    ]
                evaluation["event_results"] = [
                    scoped_point(p, allowed_ids) for p in evaluation["event_results"]
                ]
                if any(p.get("withheld") for p in evaluation["event_results"]):
                    from .monitoring.events import combined_outcome

                    evaluation["outcome"] = combined_outcome(
                        evaluation["results"] + evaluation["event_results"]
                    )
                    evaluation["availability"] = "partial"
        jobs = rows(
            conn,
            "SELECT j.id,j.version_id,j.status,j.error,j.attempts FROM jobs j JOIN thesis_versions v ON v.id=j.version_id JOIN theses t ON t.id=v.thesis_id WHERE j.owner_id=%s AND t.instrument_id=%s ORDER BY j.created_at DESC LIMIT 12",
            (owner, instrument_id),
        )
        checks, freshness = latest_coverage(
            conn, instrument_id, datetime.fromisoformat(info["as_of"])
        )
        actions = rows(
            conn,
            "SELECT * FROM research_actions WHERE owner_id=%s AND instrument_id=%s ORDER BY created_at DESC LIMIT 1",
            (owner, instrument_id),
        )
        market_clock = datetime.now(timezone.utc)
        latest_snapshot = one(
            conn,
            "SELECT id FROM research_snapshots WHERE instrument_id=%s ORDER BY id DESC LIMIT 1",
            (instrument_id,),
        )
        from .research.proposals import list_for as proposals_for
        from .research import sentiment, social, idea_alerts, sentiment_inputs
        from .research import question_library, source_hub
        from .monitoring import news_watch, filing_watch, review_schedule

        # The response is one explicit source scope; all downstream paths use this set.
        return dict(
            question_library=question_library.present(conn, owner, instrument_id),
            review_schedule=review_schedule.settings(conn, owner),
            proposals=proposals_for(conn, owner, instrument_id),
            filing_watch=filing_watch.settings(conn, owner, instrument_id),
            sentiment=sentiment.latest(conn, instrument_id),
            sentiment_inputs=sentiment_inputs.current(
                conn, instrument_id, market_clock
            ),
            social_status=social.status(conn, instrument_id),
            provider_status=source_hub.status(conn, instrument_id),
            news_watch=one(
                conn,
                "SELECT enabled,interval_minutes,next_check_at,last_check_at,error,match_idea,event_version_id,include_context,idea_purpose FROM news_watches WHERE owner_id=%s AND instrument_id=%s",
                (owner, instrument_id),
            ),
            research_alerts=news_watch.list_alerts(conn, owner),
            idea_alerts=idea_alerts.list_for(conn, owner),
            idea_watch_state=one(
                conn,
                "SELECT * FROM idea_watch_state WHERE owner_id=%s AND instrument_id=%s",
                (owner, instrument_id),
            ),
            instrument=one(
                conn,
                "SELECT i.*,s.sector,s.mode FROM instruments i JOIN instrument_state s ON s.instrument_id=i.id WHERE i.id=%s",
                (instrument_id,),
            ),
            snapshot_id=latest_snapshot["id"] if latest_snapshot else None,
            coverage=freshness,
            market=market_workspace(conn, instrument_id),
            market_news_ids=[
                str(d["id"])
                for d in ordered_news(
                    current_documents(documents, active_id), instrument_id, market_clock
                )
            ],
            market_brief=cached_brief(
                packet_for(documents, instrument_id, active_id, market_clock)
            ),
            active_document_id=active_id,
            catalogue=catalogue(conn, owner),
            changes=changes(conn, owner),
            pending_work=bool(
                one(
                    conn,
                    "SELECT count(*) n FROM jobs WHERE owner_id=%s AND status IN ('pending','running')",
                    (owner,),
                )["n"]
            ),
            demo=info,
            prices=prices(info["as_of"]) if str(instrument_id) == INSTRUMENT else [],
            documents=evidence_from_articles(documents),
            claims=group_claims(claims, documents),
            observations=facts,
            fundamentals=fundamentals(
                current_facts, info["period"], info["period_type"]
            ),
            briefs=baseline(
                current_facts, documents, claims, info["period"], info["period_type"]
            ),
            selected_passages=(
                cached_selection(source_packet(documents, instrument_id, info["as_of"]))
                if documents and all(d["entitlement"] == "fictional" for d in documents)
                else None
            ),
            thesis=idea,
            versions=versions,
            jobs=jobs,
            source_checks=checks,
            sec_status=sec_capabilities(),
            performance=(
                performance_present(conn, instrument_id)
                if info["mode"] == "sec"
                else None
            ),
            filing_calculations=rows(
                conn,
                "SELECT * FROM filing_calculations WHERE document_version_id=ANY(%s::uuid[])",
                (docids,),
            ),
            research_action=actions[0] if actions else None,
        )


def research_action(owner, payload):
    with transaction(owner) as conn:
        conn.execute(
            "INSERT INTO research_actions VALUES(%s,%s,%s,%s,%s,now())",
            (uuid4(), owner, payload.instrument_id, payload.question, payload.action),
        )


def review(owner, evaluation_id, action):
    with transaction(owner) as conn:
        evaluation = one(
            conn,
            "SELECT * FROM evaluations WHERE id=%s AND owner_id=%s",
            (evaluation_id, owner),
        )
        if not evaluation:
            raise Missing("Evaluation not found.")
        existing = one(
            conn,
            "SELECT * FROM review_events WHERE owner_id=%s AND evaluation_id=%s",
            (owner, evaluation_id),
        )
        if existing:
            return existing
        created = one(
            conn,
            "INSERT INTO review_events(id,owner_id,evaluation_id,version_id,action) VALUES(%s,%s,%s,%s,%s) ON CONFLICT(owner_id,evaluation_id) DO NOTHING RETURNING *",
            (uuid4(), owner, evaluation_id, evaluation["version_id"], action),
        )
        return created or one(
            conn,
            "SELECT * FROM review_events WHERE owner_id=%s AND evaluation_id=%s",
            (owner, evaluation_id),
        )


def advance(owner, expected, instrument_id=INSTRUMENT):
    with transaction(admin=True) as conn:
        from .research.sec.service import collection_lock

        collection_lock(conn)
        conn.execute(
            "SELECT instrument_id FROM instrument_state WHERE instrument_id=%s FOR UPDATE",
            (instrument_id,),
        )
        info = stage_info(conn, instrument_id)
        if expected != info["stage"]:
            raise Conflict(
                "The evidence changed in another tab. Refresh before continuing."
            )
        if info["mode"] != "recorded":
            raise ValueError("Use the filing refresh for this company")
        if info["complete"]:
            raise Conflict(
                "The recorded scenario is complete. History remains available."
            )
        ingest_batch(conn, recorded_batch(instrument_id, expected + 1))
        if str(instrument_id) == INSTRUMENT:
            conn.execute("UPDATE demo_state SET stage=%s", (expected + 1,))
    queue_current(owner)
    return dict(stage=expected + 1)


def claim_job(owner):
    with transaction(owner) as conn:
        conn.execute(
            "UPDATE jobs SET status='failed',error='Retry limit reached after worker interruption',lease_until=NULL WHERE status='running' AND lease_until<now() AND attempts>=3"
        )
        job = one(
            conn,
            """SELECT j.* FROM jobs j WHERE j.owner_id=%s AND (j.status='pending' OR (j.status='running' AND j.lease_until<now()))
           AND j.attempts<3 AND NOT EXISTS(SELECT 1 FROM jobs earlier WHERE earlier.owner_id=j.owner_id AND earlier.version_id=j.version_id AND earlier.status IN ('pending','running') AND earlier.queue_order<j.queue_order)
           ORDER BY j.queue_order FOR UPDATE OF j SKIP LOCKED LIMIT 1""",
            (owner,),
        )
        if not job:
            return None
        return one(
            conn,
            "UPDATE jobs SET status='running',attempts=attempts+1,claim_token=%s,lease_until=now()+interval '30 seconds' WHERE id=%s RETURNING *",
            (uuid4(), job["id"]),
        )


def finish_job(owner, job):
    with transaction(owner) as conn:
        current = one(
            conn,
            "SELECT * FROM jobs WHERE id=%s AND owner_id=%s FOR UPDATE",
            (job["id"], owner),
        )
        if (
            not current
            or current["status"] != "running"
            or current["claim_token"] != job.get("claim_token")
        ):
            return False
        manifest = current["manifest"]
        if hashlib.sha256(canonical(manifest).encode()).hexdigest() != current[
            "fingerprint"
        ] or manifest["version_id"] != str(current["version_id"]):
            raise ValueError("Invalid input manifest")
        instrument_id = version_instrument(conn, owner, current["version_id"])
        if manifest.get("instrument_id", instrument_id) != instrument_id:
            raise ValueError("Evaluation company changed")
        permitted = {
            str(d["id"])
            for d in permitted_documents(conn, manifest["cutoff"], instrument_id)
        }
        if not set(manifest["document_ids"]).issubset(permitted):
            raise ValueError("Source access denied")
        conditions = rows(
            conn,
            "SELECT * FROM version_conditions WHERE owner_id=%s AND version_id=%s ORDER BY condition_id",
            (owner, current["version_id"]),
        )
        if json.loads(canonical(conditions)) != [
            dict(
                c,
                max_report_age_days=c.get("max_report_age_days"),
                role=c.get("role", "required"),
                expected_period_end=c.get("expected_period_end"),
                expected_report_by=c.get("expected_report_by"),
            )
            for c in manifest["conditions"]
        ]:
            raise ValueError("Revision manifest changed")
        facts = rows(
            conn,
            "SELECT o.*,coalesce(s.period_type,'quarter') period_type FROM observations o LEFT JOIN fact_scopes s ON s.observation_id=o.id WHERE o.id=ANY(%s::uuid[]) ORDER BY available_at,o.id",
            (manifest["observation_ids"],),
        )
        if len(facts) != len(manifest["observation_ids"]):
            raise ValueError("Missing historical input")
        for fact in facts:
            if (
                str(fact["document_version_id"]) not in manifest["document_ids"]
                or str(fact["instrument_id"]) != instrument_id
                or fact["available_at"] > datetime.fromisoformat(manifest["cutoff"])
            ):
                raise ValueError("Invalid point-in-time input")
        events = rows(
            conn,
            "SELECT * FROM version_events WHERE owner_id=%s AND version_id=%s ORDER BY condition_id",
            (owner, current["version_id"]),
        )
        if json.loads(canonical(manifest_events(events))) != manifest.get("events", []):
            raise ValueError("Event revision manifest changed")
        from .monitoring.events import assess as assess_events, combined_outcome

        event_review = None
        if manifest.get("event_review_id"):
            event_review = one(
                conn,
                "SELECT * FROM event_evidence_reviews r WHERE owner_id=%s AND id=%s AND version_id=%s AND (NOT automatic OR EXISTS(SELECT 1 FROM event_review_activations a WHERE a.owner_id=r.owner_id AND a.review_id=r.id))",
                (
                    owner,
                    manifest["event_review_id"],
                    current["version_id"],
                ),
            )
            if not event_review or not {
                s["id"] for s in event_review["packet"]["sources"]
            }.issubset(permitted):
                raise ValueError(
                    "Event review is unavailable for this exact assessment"
                )
            if event_review["snapshot_id"] != manifest["snapshot_id"]:
                from .research.event_review import validate_reuse

                if not validate_reuse(
                    conn,
                    owner,
                    event_review,
                    manifest["snapshot_id"],
                    manifest.get("event_review_reuse"),
                    clock=manifest.get("assessed_at", manifest["cutoff"]),
                ):
                    raise ValueError(
                        "Reused event interpretation does not match these exact inputs"
                    )
        results = (
            evaluate(
                conditions, facts, manifest["period"], manifest.get("assessed_at")
            )[1]
            if conditions
            else []
        )
        event_results = assess_events(
            events, event_review, manifest.get("assessed_at", manifest["cutoff"])
        )
        outcome = combined_outcome(results + event_results)
        evaluation = one(
            conn,
            "SELECT id FROM evaluations WHERE owner_id=%s AND fingerprint=%s",
            (owner, current["fingerprint"]),
        )
        if not evaluation:
            previous = one(
                conn,
                "SELECT e.* FROM evaluations e LEFT JOIN jobs j ON j.owner_id=e.owner_id AND j.fingerprint=e.fingerprint WHERE e.owner_id=%s AND e.version_id=%s ORDER BY j.queue_order DESC NULLS LAST,e.created_at DESC,e.id DESC LIMIT 1",
                (owner, current["version_id"]),
            )
            eid = uuid4()
            conn.execute(
                "INSERT INTO evaluations(id,owner_id,version_id,fingerprint,manifest,outcome,availability,freshness,disagreement) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    eid,
                    owner,
                    current["version_id"],
                    current["fingerprint"],
                    Jsonb(manifest),
                    outcome,
                    (
                        "partial"
                        if any(
                            r["outcome"] == "unknown" for r in results + event_results
                        )
                        else "available"
                    ),
                    manifest["freshness"],
                    any(r["disagreement"] for r in results + event_results),
                ),
            )
            for result in results:
                conn.execute(
                    "INSERT INTO condition_results VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
                    (
                        owner,
                        eid,
                        current["version_id"],
                        result["condition_id"],
                        result["outcome"],
                        result["observed_value"],
                        result["observation_id"],
                        result["explanation"],
                    ),
                )
            for result in event_results:
                conn.execute(
                    "INSERT INTO event_results(owner_id,evaluation_id,version_id,condition_id,outcome,state,review_id,explanation,citations) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (
                        owner,
                        eid,
                        current["version_id"],
                        result["condition_id"],
                        result["outcome"],
                        result["state"],
                        result["review_id"],
                        result["explanation"],
                        Jsonb(result["citations"]),
                    ),
                )
            if previous:
                record_change(
                    conn,
                    owner,
                    eid,
                    current["version_id"],
                    previous,
                    manifest,
                    results,
                    event_results,
                )
        conn.execute(
            "UPDATE jobs SET status='done',lease_until=NULL,error=NULL WHERE id=%s",
            (current["id"],),
        )


def work_once(owner=OWNER):
    from .research.market import tick as market_tick

    market_tick()
    from .research.sec.service import tick_coverage

    tick_coverage()
    queue_current(owner)
    job = claim_job(owner)
    if not job:
        return False
    try:
        finish_job(owner, job)
    except Exception:
        fail_job(owner, job)
        raise
    return True


def fail_job(owner, job):
    with transaction(owner) as conn:
        return (
            conn.execute(
                "UPDATE jobs SET status='failed',lease_until=NULL,error='Evaluation could not be completed; saved inputs are preserved.' WHERE id=%s AND status='running' AND claim_token=%s",
                (job["id"], job.get("claim_token")),
            ).rowcount
            == 1
        )


def research_selection(expected_stage, instrument_id=INSTRUMENT):
    with transaction() as conn:
        info = stage_info(conn, instrument_id)
        if info["stage"] != expected_stage:
            raise Conflict(
                "The evidence changed. Refresh before requesting this brief."
            )
        packet = source_packet(
            permitted_documents(conn, info["as_of"], instrument_id),
            instrument_id,
            info["as_of"],
        )
    return select_passages(packet)


def catalogue(conn, owner):
    return rows(
        conn,
        """SELECT i.id,i.symbol,i.name,s.sector,s.mode,s.cutoff,t.status,t.revision,v.reasoning,v.question,
      ((SELECT count(*) FROM change_events c JOIN thesis_versions cv ON cv.id=c.version_id LEFT JOIN review_events r ON r.evaluation_id=c.evaluation_id AND r.owner_id=c.owner_id WHERE c.owner_id=%s AND cv.thesis_id=t.id AND r.id IS NULL)
       + (SELECT count(*) FROM research_alerts a LEFT JOIN research_alert_reviews r ON r.alert_id=a.id AND r.owner_id=a.owner_id WHERE a.owner_id=%s AND a.instrument_id=i.id AND r.alert_id IS NULL)
       + (SELECT count(*) FROM idea_alert_checks a JOIN idea_alert_publications p ON p.check_id=a.id AND p.owner_id=a.owner_id LEFT JOIN idea_alert_reviews r ON r.check_id=a.id AND r.owner_id=a.owner_id WHERE a.owner_id=%s AND a.instrument_id=i.id AND r.check_id IS NULL)) unread
      FROM instruments i JOIN instrument_state s ON s.instrument_id=i.id LEFT JOIN theses t ON t.instrument_id=i.id AND t.owner_id=%s
      LEFT JOIN thesis_versions v ON v.thesis_id=t.id AND v.owner_id=t.owner_id AND v.revision=t.revision ORDER BY i.symbol""",
        (owner, owner, owner, owner),
    )


def changes(conn, owner):
    return rows(
        conn,
        """SELECT c.*,i.symbol,i.name,i.id instrument_id,v.question,v.reasoning,v.revision,r.action review_action
      FROM change_events c JOIN thesis_versions v ON v.id=c.version_id AND v.owner_id=c.owner_id JOIN theses t ON t.id=v.thesis_id AND t.owner_id=v.owner_id JOIN instruments i ON i.id=t.instrument_id
      LEFT JOIN review_events r ON r.evaluation_id=c.evaluation_id AND r.owner_id=c.owner_id WHERE c.owner_id=%s ORDER BY c.created_at DESC LIMIT 100""",
        (owner,),
    )


def record_change(
    conn, owner, eid, version_id, previous, manifest, results, event_results=()
):
    old = previous["manifest"]
    before = {
        str(r["condition_id"]): r
        for r in rows(
            conn,
            "SELECT * FROM condition_results WHERE evaluation_id=%s AND owner_id=%s",
            (previous["id"], owner),
        )
    }
    affected = []
    for result in results:
        prior = before.get(result["condition_id"])
        if prior and (
            str(prior["observed_value"]) != str(result["observed_value"])
            or prior["outcome"] != result["outcome"]
        ):
            affected.append(
                dict(
                    condition_id=result["condition_id"],
                    metric=next(
                        c["metric"]
                        for c in manifest["conditions"]
                        if c["condition_id"] == result["condition_id"]
                    ),
                    role=next(
                        c.get("role", "required")
                        for c in manifest["conditions"]
                        if c["condition_id"] == result["condition_id"]
                    ),
                    before_outcome=prior["outcome"],
                    before=(
                        str(prior["observed_value"])
                        if prior["observed_value"] is not None
                        else None
                    ),
                    after=(
                        str(result["observed_value"])
                        if result["observed_value"] is not None
                        else None
                    ),
                    outcome=result["outcome"],
                )
            )
    coverage_changed = old.get("freshness") != manifest["freshness"] or old.get(
        "source_states"
    ) != manifest.get("source_states")
    story_changed = old.get("stories") != manifest.get("stories")
    old_ages = (
        {a["condition_id"]: a["state"] for a in old.get("expiry", [])}
        if isinstance(old.get("expiry"), list)
        else {}
    )
    newly_expired = (
        [
            a
            for a in manifest.get("expiry", [])
            if a["state"] == "expired" and old_ages.get(a["condition_id"]) != "expired"
        ]
        if isinstance(manifest.get("expiry"), list)
        else []
    )
    old_reports = {a["condition_id"]: a for a in old.get("report_expectations", [])}
    affected_reports = [
        dict(a, before=old_reports.get(a["condition_id"], {}).get("state"))
        for a in manifest.get("report_expectations", [])
        if a["state"] != old_reports.get(a["condition_id"], {}).get("state")
    ]
    prior_events = {
        str(r["condition_id"]): r
        for r in rows(
            conn,
            "SELECT * FROM event_results WHERE owner_id=%s AND evaluation_id=%s",
            (owner, previous["id"]),
        )
    }
    affected_events = [
        dict(
            condition_id=r["condition_id"],
            before=prior_events.get(r["condition_id"], {}).get("state"),
            after=r["state"],
            description=next(
                c["description"]
                for c in manifest.get("events", [])
                if c["condition_id"] == r["condition_id"]
            ),
            outcome=r["outcome"],
            **(
                {
                    "window": r["window"],
                    "before_window": next(
                        (
                            x.get("window")
                            for x in old.get("event_windows", [])
                            if x["condition_id"] == r["condition_id"]
                        ),
                        None,
                    ),
                }
                if r.get("window")
                else {}
            ),
        )
        for r in event_results
        if prior_events.get(r["condition_id"], {}).get("state") != r["state"]
        or str(prior_events.get(r["condition_id"], {}).get("review_id"))
        != str(r["review_id"])
        or r.get("window")
        != next(
            (
                x.get("window")
                for x in old.get("event_windows", [])
                if x["condition_id"] == r["condition_id"]
            ),
            None,
        )
    ]
    if (
        not affected
        and not affected_events
        and not affected_reports
        and not coverage_changed
        and not story_changed
    ):
        return
    kind = "figures" if affected else "coverage" if coverage_changed else "evidence"
    if (
        newly_expired
        and not story_changed
        and all(a["before"] == a["after"] for a in affected)
    ):
        kind = "expiry"
    summary = (
        f"{len(affected)} monitored figure{'s' if len(affected)!=1 else ''} changed"
        if affected
        else (
            "Source coverage changed"
            if coverage_changed
            else "New source evidence to review"
        )
    )
    details = dict(
        affected_conditions=affected,
        previous_period=old["period"],
        period=manifest["period"],
        previous_cutoff=old["cutoff"],
        cutoff=manifest["cutoff"],
        coverage_before=old["freshness"],
        coverage_after=manifest["freshness"],
        source_states_before=old.get("source_states", {}),
        source_states_after=manifest.get("source_states", {}),
        evidence_changed=story_changed,
        assessed_at=manifest.get("assessed_at", manifest["cutoff"]),
        newly_expired=newly_expired,
        affected_events=affected_events,
        **({"affected_reports": affected_reports} if affected_reports else {}),
        new_document_ids=sorted(
            set(manifest["document_ids"]) - set(old["document_ids"])
        ),
    )
    if kind == "expiry":
        summary = "Reporting figures passed your age limit"
    if affected_reports:
        kind = "reporting"
        summary = "Expected reporting evidence changed"
    if affected_events:
        kind = "event"
        summary = "Event evidence or deadline needs review"
    conn.execute(
        "INSERT INTO change_events(id,owner_id,version_id,evaluation_id,previous_evaluation_id,kind,summary,details) VALUES(%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
        (
            uuid4(),
            owner,
            version_id,
            eid,
            previous["id"],
            kind,
            summary,
            Jsonb(details),
        ),
    )


def group_claims(claims, documents):
    docs = {str(d["id"]): d for d in documents}
    groups = {}
    for claim in claims:
        key = (
            claim["event_key"],
            claim["kind"],
            claim["stance"],
            claim["quote"].casefold().strip(),
        )
        group = groups.setdefault(
            key, dict(claim, source_version_ids=[], origin_keys=[])
        )
        doc = docs[str(claim["document_version_id"])]
        group["source_version_ids"].append(str(doc["id"]))
        origin = doc.get("origin_key") or doc["source_name"]
        if origin not in group["origin_keys"]:
            group["origin_keys"].append(origin)
    return list(groups.values())
