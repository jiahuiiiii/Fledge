"""Authored fictional source corpus. No network/provider is called."""

from datetime import datetime, timezone, date, timedelta
from uuid import uuid5, NAMESPACE_URL
import math
from .config import INSTRUMENT, OWNER
from .db import transaction, one
from .research.pipeline import normalize_article, validate_claim

STAGES = [
    dict(label="Q2 baseline", as_of="2025-07-24T12:00:00+00:00", period="2025-Q2"),
    dict(label="Renewal report", as_of="2025-10-18T14:05:00+00:00", period="2025-Q2"),
    dict(label="Q3 results", as_of="2025-10-24T12:00:00+00:00", period="2025-Q3"),
    dict(label="Source outage", as_of="2025-10-25T12:00:00+00:00", period="2025-Q3"),
    dict(
        label="Revenue restatement", as_of="2025-10-28T12:00:00+00:00", period="2025-Q3"
    ),
]


def uid(value):
    return str(uuid5(NAMESPACE_URL, "thesis-fixture:" + value))


def dt(value):
    return datetime.fromisoformat(value)


RELEASES = {
    0: dict(
        key="q2",
        source="company",
        title="Northstar Q2: growth of 18%, operating margin of 21%",
        body="Northstar Software reported quarterly revenue growth of 18% year over year and a reported operating margin of 21%. Management expects enterprise renewals to remain steady. This guidance is a company expectation, not analyst consensus.",
        period="2025-Q2",
        growth="18",
        margin="21",
        start="2025-04-01",
        end="2025-06-30",
    ),
    1: dict(
        key="renewals",
        source="wire",
        title="Report: two Northstar renewals may move into next quarter",
        body="Sample Industry Wire reports that two Northstar enterprise customers may complete their renewals next quarter. Northstar has not confirmed these contract timings or values. The impact on revenue is unknown.",
    ),
    2: dict(
        key="q3",
        source="company",
        title="Northstar Q3: growth slows to 12%, operating margin rises to 22%",
        body="Northstar Software reported quarterly revenue growth of 12% year over year and a reported operating margin of 22%. No contract-specific explanation was supplied. These results do not establish whether the previously reported renewals caused the slower growth.",
        period="2025-Q3",
        growth="12",
        margin="22",
        start="2025-07-01",
        end="2025-09-30",
    ),
    4: dict(
        key="q3",
        source="company",
        title="Northstar restates Q3 revenue growth to 13%",
        body="Northstar Software restated quarterly year-over-year revenue growth from 12% to 13%. Reported operating margin remains 22%. The correction replaces the earlier growth figure; prior research records must retain what was known at their cutoff.",
        period="2025-Q3",
        growth="13",
        margin="22",
        start="2025-07-01",
        end="2025-09-30",
    ),
}


def authored_claims(stage):
    claims = []
    if stage == 0:
        claims = [
            (
                "reported",
                "support",
                "Growth at 18%, operating margin at 21%",
                "The baseline supports investigating durable enterprise growth.",
                "quarterly revenue growth of 18% year over year",
            ),
            (
                "guidance",
                "unknown",
                "Management expects renewals to remain steady",
                "This is management guidance. Independent consensus is unavailable.",
                "Management expects enterprise renewals to remain steady.",
            ),
        ]
    elif stage == 1:
        claims = [
            (
                "news_report",
                "challenge",
                "Renewal timing needs confirmation",
                "One independent fictional report raises a timing question; it is not company confirmation.",
                "two Northstar enterprise customers may complete their renewals next quarter",
            )
        ]
    elif stage == 2:
        claims = [
            (
                "reported",
                "challenge",
                "Revenue growth slowed to 12%",
                "Compare the growth observation with your original reasoning and chosen condition.",
                "quarterly revenue growth of 12% year over year",
            ),
            (
                "reported",
                "support",
                "Operating margin increased to 22%",
                "Margin expansion supports a separate part of the idea.",
                "reported operating margin of 22%",
            ),
        ]
    else:
        claims = [
            (
                "reported",
                "challenge",
                "Revenue growth was corrected to 13%",
                "The latest fact changes; the original 12% remains in historical evaluations.",
                "restated quarterly year-over-year revenue growth from 12% to 13%",
            ),
            (
                "reported",
                "support",
                "Operating margin remains at 22%",
                "The correction leaves the reported margin figure unchanged.",
                "Reported operating margin remains 22%.",
            ),
        ]
    return claims


def ingest(conn, stage):
    from .research.recorded import recorded_batch
    from .research.acquisition import ingest_batch

    ingest_batch(conn, recorded_batch(INSTRUMENT, stage))


def seed():
    with transaction(admin=True) as conn:
        if not one(conn, "SELECT seed_demo FROM workspace_settings WHERE singleton")["seed_demo"]:
            conn.execute("INSERT INTO accounts VALUES(%s,'Local workspace') ON CONFLICT DO NOTHING", (OWNER,))
            return
        conn.execute(
            "INSERT INTO accounts VALUES(%s,%s) ON CONFLICT DO NOTHING",
            (OWNER, "Local fictional demo"),
        )
        conn.execute(
            "INSERT INTO instruments VALUES(%s,%s,%s) ON CONFLICT DO NOTHING",
            (INSTRUMENT, "NSTR", "Northstar Software"),
        )
        conn.execute(
            "INSERT INTO instrument_state(instrument_id,cutoff,period,label,sector) VALUES(%s,'2025-07-24T12:00:00Z','2025-Q2','Q2 baseline','Enterprise software') ON CONFLICT DO NOTHING",
            (INSTRUMENT,),
        )
        for key, name in [
            ("company", "Northstar company release"),
            ("wire", "Sample Industry Wire"),
        ]:
            conn.execute(
                "INSERT INTO sources VALUES(%s,%s,%s) ON CONFLICT DO NOTHING",
                (key, name, "fictional"),
            )
        for source in ("company", "wire"):
            conn.execute(
                "INSERT INTO instrument_sources VALUES(%s,%s) ON CONFLICT DO NOTHING",
                (INSTRUMENT, source),
            )
        if not one(
            conn, "SELECT id FROM document_versions WHERE id=%s", (uid("document-0"),)
        ):
            ingest(conn, 0)
        from .research.recorded import seed_aurora

        seed_aurora(conn)
        from .research.snapshots import capture_snapshot

        for instrument in (INSTRUMENT, "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"):
            if not one(
                conn,
                "SELECT id FROM research_snapshots WHERE instrument_id=%s LIMIT 1",
                (instrument,),
            ):
                capture_snapshot(conn, instrument)


def prices(cutoff):
    result = []
    day = date(2025, 5, 1)
    previous = 101.2
    end = date.fromisoformat(cutoff[:10])
    i = 0
    while day <= end:
        if day.weekday() < 5:
            close = round(
                101 + i * 0.35 + math.sin(i * 0.55) * 2.8 - (max(0, i - 115) * 1.4), 2
            )
            result.append(
                dict(
                    date=day.isoformat(),
                    open=previous,
                    close=close,
                    high=round(max(close, previous) + 1.4, 2),
                    low=round(min(close, previous) - 1.1, 2),
                    volume=100000 + (i * 17431) % 190000,
                )
            )
            previous = close
            i += 1
        day += timedelta(days=1)
    return result[-64:]
