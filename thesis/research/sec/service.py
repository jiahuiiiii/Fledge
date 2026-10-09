"""Connect structured SEC fundamentals to the shared acquisition/history contract."""

import hashlib
import json
from datetime import datetime, timezone, timedelta
from uuid import uuid4, uuid5, NAMESPACE_URL
from psycopg.types.json import Jsonb
from thesis.db import transaction, one
from thesis.research.acquisition import Batch, Document, Fact, Check, ingest_batch
from . import client
from .normalize import normalize
from ..catalogue import COMPANIES


def collection_lock(conn):
    # One short shared-source transaction at a time; HTTP occurs outside this lock.
    conn.execute(
        "SELECT pg_advisory_xact_lock(hashtextextended('thesis-sec-collection',0))"
    )


def stable(value):
    return uuid5(NAMESPACE_URL, "thesis:sec:" + value)


def capabilities():
    try:
        client.identity()
        configured = True
    except ValueError:
        configured = False
    return dict(
        configured=configured,
        companies=[
            dict(symbol=s, name=v[1], id=str(stable(str(v[0]))))
            for s, v in COMPANIES.items()
        ],
        minimum_refresh_minutes=15,
    )


def add_company(symbol):
    from ..directory import resolve

    cik, name, sector = resolve(symbol)
    iid = stable(str(cik))
    now = datetime.now(timezone.utc)
    with transaction(source=True) as conn:
        collection_lock(conn)
        existing = one(conn, "SELECT i.id,i.symbol,s.cik FROM instruments i LEFT JOIN sec_companies s ON s.instrument_id=i.id WHERE i.symbol=%s OR s.cik=%s", (symbol,cik))
        if existing:
            if existing["symbol"] != symbol or existing["cik"] != cik:
                raise ValueError("This ticker or issuer is already registered under a different identity. Existing research is preserved.")
            return dict(instrument_id=str(existing["id"]))
        conn.execute(
            "INSERT INTO instruments VALUES(%s,%s,%s) ON CONFLICT DO NOTHING",
            (iid, symbol, name),
        )
        conn.execute(
            "INSERT INTO instrument_state(instrument_id,cutoff,period,label,mode,sector) VALUES(%s,%s,'Not yet available','Filing data not fetched','sec',%s) ON CONFLICT DO NOTHING",
            (iid, now, sector),
        )
        conn.execute(
            "INSERT INTO sec_companies VALUES(%s,%s) ON CONFLICT DO NOTHING", (iid, cik)
        )
        conn.execute(
            "INSERT INTO sources VALUES('sec-companyfacts','SEC structured filings','sec-public') ON CONFLICT DO NOTHING"
        )
        conn.execute(
            "INSERT INTO instrument_sources VALUES(%s,'sec-companyfacts') ON CONFLICT DO NOTHING",
            (iid,),
        )
        conn.execute(
            "INSERT INTO sec_refresh_state(instrument_id) VALUES(%s) ON CONFLICT DO NOTHING",
            (iid,),
        )
        from thesis.research.snapshots import capture_snapshot

        capture_snapshot(conn, iid)
    return dict(instrument_id=str(iid))


def commit_bundle(conn, iid, bundle, now):
    collection_lock(conn)
    company = one(conn, "SELECT * FROM sec_companies WHERE instrument_id=%s", (iid,))
    if not company:
        raise ValueError("Company does not use the SEC adapter")
    result = normalize(
        bundle["companyfacts"], bundle["submissions"], company["cik"], now
    )
    state = one(
        conn, "SELECT * FROM instrument_state WHERE instrument_id=%s FOR UPDATE", (iid,)
    )
    active = one(
        conn,
        "SELECT f.period_end,v.published_at FROM filing_calculations f JOIN document_versions v ON v.id=f.document_version_id JOIN documents d ON d.id=v.document_id WHERE d.instrument_id=%s ORDER BY v.available_at DESC,v.id DESC LIMIT 1",
        (iid,),
    )
    if active and (result["period_end"], result["published_at"]) < (
        active["period_end"],
        active["published_at"],
    ):
        raise ValueError(
            "SEC response predates the current filing; current evidence is preserved"
        )
    canonical = json.dumps(bundle, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    pid = stable(str(iid) + ":payload:" + digest)
    conn.execute(
        "INSERT INTO source_payloads VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
        (pid, iid, digest, Jsonb(bundle), now),
    )
    # A source version is keyed by the normalized selected accession/inputs, not
    # retrieval time or unrelated changes elsewhere in the companyfacts response.
    normalized = {
        k: v for k, v in result.items() if k not in ("name", "facts", "calculations")
    }
    normalized["calculations"] = [
        dict(
            c,
            inputs=[
                {k: v for k, v in f.items() if k not in ("fy", "fp", "frame")}
                for f in c["inputs"]
            ],
        )
        for c in result["calculations"]
    ]
    signature = hashlib.sha256(
        json.dumps(normalized, sort_keys=True, default=str).encode()
    ).hexdigest()
    url = result["filing_url"]
    did = stable(url)
    vid = stable(url + signature)
    existing = one(conn, "SELECT id FROM document_versions WHERE id=%s", (vid,))
    previous_snapshot = one(
        conn,
        "SELECT payload FROM research_snapshots WHERE instrument_id=%s ORDER BY id DESC LIMIT 1",
        (iid,),
    )
    previous_active = (
        previous_snapshot["payload"].get("active_document_id")
        if previous_snapshot
        else None
    )
    sequence = state["sequence"] + 1
    documents = []
    if not existing:
        previous = one(
            conn,
            "SELECT id FROM document_versions WHERE document_id=%s ORDER BY available_at DESC LIMIT 1",
            (did,),
        )
        body = f"Structured filing calculation, not a verbatim filing excerpt.\n\n{result['name']} · {result['form']} · {result['period']}\nAccession: {result['accession']}\nOriginal filing: {url}\n"
        facts = []
        for calculation in result["calculations"]:
            body += f"\n{calculation['metric']}: {calculation['value']+'%' if calculation['value'] is not None else calculation['reason']}\nFormula: {calculation['formula']}\n"
            for f in calculation["inputs"]:
                body += f"{f['concept']}: USD {f['value']}, {f['start']} to {f['end']}, accession {f['accession']}\n"
            if calculation["value"] is not None:
                previous_fact = one(
                    conn,
                    "SELECT id FROM observations WHERE instrument_id=%s AND metric=%s AND period=%s ORDER BY available_at DESC LIMIT 1",
                    (iid, calculation["metric"], result["period"]),
                )
                facts.append(
                    Fact(
                        id=stable(str(vid) + calculation["metric"]),
                        metric=calculation["metric"],
                        value=calculation["value"],
                        period=result["period"],
                        period_start=result["period_start"],
                        period_end=result["period_end"],
                        period_type=result["period_type"],
                        period_convention="filing-dates",
                        supersedes_id=previous_fact["id"] if previous_fact else None,
                    )
                )
        body += (
            "\n"
            + "\n".join(result["limitations"])
            + "\nStructured data version: "
            + signature
        )
        # First-retrieved availability is deliberately conservative. A filing date
        # never backdates when this installation first learned an observation.
        documents = [
            Document(
                id=did,
                version_id=vid,
                source_id="sec-companyfacts",
                url=url,
                headline=f"{result['name']} · {result['form']} · {result['period']}",
                body=body,
                published_at=result["published_at"],
                available_at=now,
                supersedes_id=previous["id"] if previous else None,
                story_key=result["accession"],
                origin_key="sec:" + str(company["cik"]),
                facts=facts,
            )
        ]
    batch = Batch(
        instrument_id=iid,
        cutoff=now,
        period=result["period"],
        period_type=result["period_type"],
        sequence=sequence,
        label=f"{result['form']} · filed {result['filed_on']}",
        documents=documents,
        checks=[
            Check(
                id=uuid4(),
                source_id="sec-companyfacts",
                checked_at=now,
                outcome="success",
                cursor=json.dumps(
                    dict(accession=result["accession"], document_version_id=str(vid)),
                    sort_keys=True,
                ),
                covered_through=now,
            )
        ],
    )
    ingest_batch(conn, batch)
    if not existing:
        conn.execute(
            "INSERT INTO filing_calculations VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                vid,
                pid,
                result["accession"],
                result["form"],
                url,
                result["period_type"],
                result["period_start"],
                result["period_end"],
                Jsonb(result["calculations"]),
                Jsonb(result["facts"]),
                Jsonb(result["limitations"]),
            ),
        )
    from .performance import persist

    persist(conn, iid, pid, bundle, company["cik"], now)
    conn.execute('INSERT INTO sec_payload_current VALUES(%s,%s,%s) ON CONFLICT(instrument_id) DO UPDATE SET payload_id=excluded.payload_id,checked_at=excluded.checked_at',(iid,pid,now))
    return dict(
        instrument_id=str(iid),
        source_check_id=str(batch.checks[0].id),
        changed=not bool(existing)
        or bool(previous_active and previous_active != str(vid)),
        period=result["period"],
    )


class RecentlyChecked(ValueError):
    """A bounded shared cooldown; not a successful new source check."""


def refresh(iid, *, fetcher=None):
    # Production always obtains a declared identity before reserving an attempt.
    if fetcher is None:
        client.identity()
    now = datetime.now(timezone.utc)
    attempt = uuid4()
    with transaction(source=True) as conn:
        collection_lock(conn)
        company = one(
            conn, "SELECT * FROM sec_companies WHERE instrument_id=%s", (iid,)
        )
        if not company:
            raise ValueError("This company does not use SEC filings.")
        state = one(
            conn,
            "SELECT * FROM sec_refresh_state WHERE instrument_id=%s FOR UPDATE",
            (iid,),
        )
        if state["last_attempt_at"] and now - state["last_attempt_at"] < timedelta(
            minutes=15
        ):
            raise RecentlyChecked(
                "SEC was checked recently. Wait 15 minutes between attempts; saved evidence remains available."
            )
        conn.execute(
            "UPDATE sec_refresh_state SET attempt_id=%s,last_attempt_at=%s,lease_until=%s,last_error=NULL WHERE instrument_id=%s",
            (attempt, now, now + timedelta(minutes=2), iid),
        )
    try:
        bundle = (fetcher or client.fetch_bundle)(company["cik"])
        with transaction(source=True) as conn:
            collection_lock(conn)
            checked = datetime.now(timezone.utc)
            current = one(
                conn,
                "SELECT attempt_id,lease_until FROM sec_refresh_state WHERE instrument_id=%s FOR UPDATE",
                (iid,),
            )
            if (
                current["attempt_id"] != attempt
                or not current["lease_until"]
                or checked > current["lease_until"]
            ):
                raise ValueError("This source attempt was replaced or expired.")
            result = commit_bundle(conn, iid, bundle, checked)
            conn.execute(
                "UPDATE sec_refresh_state SET lease_until=NULL WHERE instrument_id=%s",
                (iid,),
            )
        return result
    except Exception as error:
        # No exception bodies/response text or contact identity are persisted.
        message = (
            "SEC access denied or rate-limited."
            if isinstance(error, client.SourceFailure) and error.denied
            else "SEC refresh failed; no new evidence committed."
        )
        with transaction(source=True) as conn:
            collection_lock(conn)
            checked = datetime.now(timezone.utc)
            current = one(
                conn,
                "SELECT attempt_id FROM sec_refresh_state WHERE instrument_id=%s FOR UPDATE",
                (iid,),
            )
            if current["attempt_id"] == attempt:
                info = one(
                    conn,
                    "SELECT * FROM instrument_state WHERE instrument_id=%s FOR UPDATE",
                    (iid,),
                )
                ingest_batch(
                    conn,
                    Batch(
                        instrument_id=iid,
                        cutoff=checked,
                        period=info["period"],
                        period_type=info["period_type"],
                        sequence=info["sequence"] + 1,
                        label="Filing refresh unavailable",
                        checks=[
                            Check(
                                id=uuid4(),
                                source_id="sec-companyfacts",
                                checked_at=checked,
                                outcome=(
                                    "denied"
                                    if isinstance(error, client.SourceFailure)
                                    and error.denied
                                    else "failed"
                                ),
                                error=message,
                            )
                        ],
                    ),
                )
                conn.execute(
                    "UPDATE sec_refresh_state SET lease_until=NULL,last_error=%s WHERE instrument_id=%s",
                    (message, iid),
                )
        raise ValueError(message) from None


def tick_coverage(now=None):
    """Age shared coverage and expose interrupted retrievals; never performs HTTP."""
    from thesis.db import rows
    from thesis.research.acquisition import latest_coverage
    from thesis.research.snapshots import capture_snapshot

    with transaction(source=True) as conn:
        collection_lock(conn)
        now = now or datetime.now(timezone.utc)
        companies = rows(
            conn,
            "SELECT s.* FROM instrument_state s JOIN sec_companies c ON c.instrument_id=s.instrument_id ORDER BY s.instrument_id FOR UPDATE OF s",
        )
        for state in companies:
            iid = state["instrument_id"]
            if now < state["cutoff"]:
                continue
            refresh_state = one(
                conn,
                "SELECT * FROM sec_refresh_state WHERE instrument_id=%s FOR UPDATE",
                (iid,),
            )
            if refresh_state["lease_until"] and refresh_state["lease_until"] < now:
                message = "Previous filing refresh was interrupted. New evidence is unconfirmed."
                ingest_batch(
                    conn,
                    Batch(
                        instrument_id=iid,
                        cutoff=now,
                        period=state["period"],
                        period_type=state["period_type"],
                        sequence=state["sequence"] + 1,
                        label="Filing refresh interrupted",
                        checks=[
                            Check(
                                id=uuid4(),
                                source_id="sec-companyfacts",
                                checked_at=now,
                                outcome="failed",
                                error=message,
                            )
                        ],
                    ),
                )
                conn.execute(
                    "UPDATE sec_refresh_state SET lease_until=NULL,attempt_id=NULL,last_error=%s WHERE instrument_id=%s",
                    (message, iid),
                )
            else:
                checks, freshness = latest_coverage(conn, iid, now)
                latest = one(
                    conn,
                    "SELECT payload FROM research_snapshots WHERE instrument_id=%s ORDER BY id DESC LIMIT 1",
                    (iid,),
                )
                states = {c["source_id"]: c["state"] for c in checks}
                if latest and latest["payload"]["source_states"] != states:
                    conn.execute(
                        "UPDATE instrument_state SET cutoff=%s WHERE instrument_id=%s",
                        (now, iid),
                    )
                    capture_snapshot(conn, iid)
