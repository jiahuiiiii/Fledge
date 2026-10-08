"""One transactional evidence-batch contract for recorded and future permitted adapters."""

from datetime import date, datetime, timezone, timedelta
from calendar import monthrange
import re
from hashlib import sha256
from uuid import UUID, uuid4
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from thesis.db import one, rows
from .pipeline import normalize_article, validate_claim


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Fact(Strict):
    id: UUID
    metric: Literal["revenue_growth", "operating_margin"]
    value: Decimal = Field(ge=-100, le=1000, allow_inf_nan=False)
    period: str
    period_start: date
    period_end: date
    unit: Literal["percent"] = "percent"
    basis: Literal["reported"] = "reported"
    supersedes_id: UUID | None = None
    period_type: Literal["quarter", "annual"] = "quarter"
    period_convention: Literal["calendar", "filing-dates"] = "calendar"

    @model_validator(mode="after")
    def calendar_quarter(self):
        if self.period_convention == "filing-dates":
            label = "Year" if self.period_type == "annual" else "Quarter"
            bounds = (350, 380) if self.period_type == "annual" else (70, 110)
            days = (self.period_end - self.period_start).days + 1
            if (
                self.period != f"{label} ended {self.period_end}"
                or not bounds[0] <= days <= bounds[1]
            ):
                raise ValueError("Invalid fiscal reporting period")
            return self
        if self.period_type != "quarter":
            raise ValueError("Calendar fixtures support quarters only")
        if not re.fullmatch(r"\d{4}-Q[1-4]", self.period):
            raise ValueError("Only an explicit calendar quarter is supported")
        year = int(self.period[:4])
        quarter = int(self.period[-1])
        start_month = (quarter - 1) * 3 + 1
        end_month = quarter * 3
        if self.period_start != date(year, start_month, 1) or self.period_end != date(
            year, end_month, monthrange(year, end_month)[1]
        ):
            raise ValueError("Period label and calendar-quarter boundaries disagree")
        return self


class Claim(Strict):
    id: UUID
    kind: Literal["reported", "guidance", "news_report", "interpretation"]
    stance: Literal["support", "challenge", "unknown"]
    title: str
    body: str
    quote: str


class Document(Strict):
    id: UUID
    version_id: UUID
    source_id: str
    url: str
    headline: str
    body: str
    published_at: datetime
    available_at: datetime
    supersedes_id: UUID | None = None
    story_key: str
    origin_key: str
    facts: list[Fact] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)


class Check(Strict):
    id: UUID
    source_id: str
    checked_at: datetime
    outcome: Literal["success", "failed", "denied"]
    cursor: str | None = None
    covered_through: datetime | None = None
    error: str | None = None


class Batch(Strict):
    instrument_id: UUID
    cutoff: datetime
    period: str
    sequence: int = Field(ge=0)
    label: str
    scenario_complete: bool = False
    period_type: Literal["quarter", "annual"] = "quarter"
    documents: list[Document] = Field(default_factory=list)
    checks: list[Check] = Field(default_factory=list)

    @model_validator(mode="after")
    def times(self):
        stamps = (
            [self.cutoff]
            + [s for d in self.documents for s in (d.published_at, d.available_at)]
            + [c.checked_at for c in self.checks]
        )
        if any(t.tzinfo is None for t in stamps):
            raise ValueError("Evidence timestamps need a timezone")
        for d in self.documents:
            if any(
                f.period_end > d.published_at.astimezone(timezone.utc).date()
                for f in d.facts
            ):
                raise ValueError("Reported period cannot end after source publication")
            if d.available_at < d.published_at or d.available_at > self.cutoff:
                raise ValueError("Invalid source availability")
        for c in self.checks:
            if c.checked_at > self.cutoff:
                raise ValueError("Future source check")
            if c.covered_through and (
                c.covered_through.tzinfo is None or c.covered_through > c.checked_at
            ):
                raise ValueError("Invalid coverage cutoff")
            if c.outcome != "success" and (
                c.cursor is not None or c.covered_through is not None
            ):
                raise ValueError("Failed checks cannot advance a cursor")
        return self


def ingest_batch(conn, batch):
    """Caller owns the transaction. Cursor/check and all evidence commit together."""
    state = one(
        conn,
        "SELECT * FROM instrument_state WHERE instrument_id=%s FOR UPDATE",
        (batch.instrument_id,),
    )
    if not state:
        raise ValueError("Unsupported company")
    if batch.cutoff < state["cutoff"] or batch.sequence < state["sequence"]:
        raise ValueError("A new batch cannot move source progress backwards")
    expected = {
        s["source_id"]
        for s in rows(
            conn,
            "SELECT source_id FROM instrument_sources WHERE instrument_id=%s",
            (batch.instrument_id,),
        )
    }
    for d in batch.documents:
        source = one(conn, "SELECT * FROM sources WHERE id=%s", (d.source_id,))
        if (
            d.source_id not in expected
            or not source
            or source["entitlement"] not in ("fictional", "sec-public", "finnhub-pitch", "public-news")
        ):
            raise ValueError("Source is not permitted for this company")
        article = normalize_article(
            dict(
                id=str(d.version_id),
                headline=d.headline,
                summary=d.body,
                source_name=source["name"],
                source_type="recorded",
                url=d.url,
                published_at=d.published_at,
                fetched_at=d.available_at,
            )
        )
        existing = one(conn, "SELECT * FROM documents WHERE id=%s", (d.id,))
        if existing and (
            str(existing["instrument_id"]) != str(batch.instrument_id)
            or existing["source_id"] != d.source_id
            or existing["url"] != d.url
        ):
            raise ValueError("Document identity changed")
        conn.execute(
            "INSERT INTO documents VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            (d.id, batch.instrument_id, d.source_id, d.url),
        )
        existing = one(
            conn, "SELECT * FROM document_versions WHERE id=%s", (d.version_id,)
        )
        if existing:
            if (
                existing["content_hash"] != article.content_hash
                or existing["document_id"] != d.id
                or any(
                    existing[k] != getattr(d, k)
                    for k in (
                        "headline",
                        "body",
                        "published_at",
                        "available_at",
                        "supersedes_id",
                    )
                )
            ):
                raise ValueError("Immutable source version changed")
            lineage = one(
                conn,
                "SELECT * FROM document_lineage WHERE document_version_id=%s",
                (d.version_id,),
            )
            if not lineage or any(
                lineage[k] != getattr(d, k) for k in ("origin_key", "story_key")
            ):
                raise ValueError("Immutable source lineage changed")
            facts = rows(
                conn,
                "SELECT o.*,coalesce(s.period_type,'quarter') period_type,coalesce(s.period_convention,'calendar') period_convention FROM observations o LEFT JOIN fact_scopes s ON s.observation_id=o.id WHERE document_version_id=%s",
                (d.version_id,),
            )
            claims = rows(
                conn,
                "SELECT * FROM claims WHERE document_version_id=%s",
                (d.version_id,),
            )
            for stored, supplied, label in (
                (facts, d.facts, "observations"),
                (claims, d.claims, "claims"),
            ):
                indexed = {r["id"]: r for r in stored}
                if len(supplied) != len(indexed) or {r.id for r in supplied} != set(
                    indexed
                ):
                    raise ValueError(f"Immutable source {label} changed")
                for r in supplied:
                    if any(
                        indexed[r.id][k] != value for k, value in r.model_dump().items()
                    ):
                        raise ValueError(f"Immutable source {label} changed")
            continue
        conn.execute(
            "INSERT INTO document_versions VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                d.version_id,
                d.id,
                article.content_hash,
                d.headline,
                d.body,
                d.published_at,
                d.available_at,
                d.supersedes_id,
            ),
        )
        conn.execute(
            "INSERT INTO document_lineage VALUES(%s,%s,%s,%s)",
            (
                d.version_id,
                d.origin_key,
                d.story_key,
                sha256(d.body.encode()).hexdigest(),
            ),
        )
        for f in d.facts:
            conn.execute(
                "INSERT INTO observations VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    f.id,
                    batch.instrument_id,
                    d.version_id,
                    f.metric,
                    f.value,
                    f.unit,
                    f.basis,
                    f.period,
                    f.period_start,
                    f.period_end,
                    d.available_at,
                    f.supersedes_id,
                ),
            )
        for f in d.facts:
            conn.execute(
                "INSERT INTO fact_scopes VALUES(%s,%s,%s)",
                (f.id, f.period_type, f.period_convention),
            )
        for c in d.claims:
            validate_claim(
                dict(
                    instrument_id=batch.instrument_id,
                    quote=c.quote,
                    available_at=d.available_at,
                ),
                dict(
                    instrument_id=batch.instrument_id,
                    body=d.body,
                    available_at=d.available_at,
                ),
            )
            conn.execute(
                "INSERT INTO claims VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    c.id,
                    batch.instrument_id,
                    d.version_id,
                    c.kind,
                    c.stance,
                    c.title,
                    c.body,
                    c.quote,
                    d.story_key,
                    d.available_at,
                ),
            )
    for c in batch.checks:
        existing = one(conn, "SELECT * FROM source_checks WHERE id=%s", (c.id,))
        if existing and (
            str(existing["instrument_id"]) != str(batch.instrument_id)
            or existing["stage"] != batch.sequence
            or any(
                existing[k] != getattr(c, k)
                for k in (
                    "source_id",
                    "checked_at",
                    "outcome",
                    "cursor",
                    "covered_through",
                    "error",
                )
            )
        ):
            raise ValueError(
                "An immutable source-check identity was reused with different content"
            )
        if c.source_id not in expected:
            raise ValueError("Source check belongs to another company")
        conn.execute(
            "INSERT INTO source_checks(id,stage,source_id,checked_at,outcome,cursor,covered_through,error,instrument_id) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            (
                c.id,
                batch.sequence,
                c.source_id,
                c.checked_at,
                c.outcome,
                c.cursor,
                c.covered_through,
                c.error,
                batch.instrument_id,
            ),
        )
    conn.execute(
        "UPDATE instrument_state SET cutoff=%s,period=%s,sequence=%s,label=%s,scenario_complete=%s,period_type=%s WHERE instrument_id=%s",
        (
            batch.cutoff,
            batch.period,
            batch.sequence,
            batch.label,
            batch.scenario_complete,
            batch.period_type,
            batch.instrument_id,
        ),
    )
    from .snapshots import capture_snapshot

    capture_snapshot(conn, batch.instrument_id)


def latest_coverage(conn, instrument_id, cutoff):
    checks = rows(
        conn,
        """SELECT s.source_id,sources.name,c.id,c.checked_at,c.outcome,c.cursor,c.covered_through,c.error
       FROM instrument_sources s JOIN sources ON sources.id=s.source_id
       LEFT JOIN LATERAL(SELECT * FROM source_checks WHERE instrument_id=s.instrument_id AND source_id=s.source_id AND checked_at<=%s ORDER BY checked_at DESC,received_at DESC,id DESC LIMIT 1)c ON true
       WHERE s.instrument_id=%s ORDER BY s.source_id""",
        (cutoff, instrument_id),
    )
    for c in checks:
        c["state"] = (
            "unknown"
            if not c["id"]
            else (
                "denied"
                if c["outcome"] == "denied"
                else (
                    "failed"
                    if c["outcome"] != "success"
                    else (
                        "stale"
                        if not c["covered_through"]
                        or cutoff - c["covered_through"] > timedelta(hours=24)
                        else "fresh"
                    )
                )
            )
        )
    freshness = (
        "unknown"
        if not checks or any(c["state"] == "unknown" for c in checks)
        else "stale" if any(c["state"] != "fresh" for c in checks) else "fresh"
    )
    return checks, freshness
