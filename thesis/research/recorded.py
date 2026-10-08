"""Authored adapters produce the same typed batch contract as future live adapters."""

from datetime import datetime
from thesis.fixtures import RELEASES, STAGES, uid, dt, authored_claims
from thesis.config import INSTRUMENT
from thesis.db import one
from .acquisition import Batch, ingest_batch

AURORA = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
AURORA_STAGES = [
    dict(as_of="2025-07-25T12:00:00+00:00", period="2025-Q2", label="Q2 baseline"),
    dict(
        as_of="2025-10-20T12:00:00+00:00",
        period="2025-Q2",
        label="Component delay report",
    ),
    dict(as_of="2025-10-25T12:00:00+00:00", period="2025-Q3", label="Q3 results"),
    dict(
        as_of="2025-10-26T12:00:00+00:00",
        period="2025-Q3",
        label="Supplier access denied",
    ),
    dict(
        as_of="2025-10-27T12:00:00+00:00", period="2025-Q3", label="Coverage restored"
    ),
]
AURORA_RELEASES = {
    0: dict(
        key="q2",
        source="company",
        title="Aurora Devices Q2: growth of 8%, margin of 14%",
        body="Aurora Devices reported quarterly revenue growth of 8% year over year and operating margin of 14%. Management expects its new sensor range to launch in the fourth quarter. Orders for that range have not been disclosed.",
        growth="8",
        margin="14",
        period="2025-Q2",
        start="2025-04-01",
        end="2025-06-30",
    ),
    1: dict(
        key="components",
        source="wire",
        title="Report: a component delay may affect Aurora’s sensor launch",
        body="Sample Hardware Wire reports a possible component delay affecting Aurora Devices. Aurora has not confirmed a launch delay. The size of any sales impact is unknown.",
    ),
    2: dict(
        key="q3",
        source="company",
        title="Aurora Devices Q3: growth of 10%, margin of 11%",
        body="Aurora Devices reported quarterly revenue growth of 10% year over year and operating margin of 11%. Management attributed lower margin to higher component costs. The company did not announce a new launch date.",
        growth="10",
        margin="11",
        period="2025-Q3",
        start="2025-07-01",
        end="2025-09-30",
    ),
}


def recorded_batch(instrument_id, stage):
    northstar = str(instrument_id) == INSTRUMENT
    if not northstar and str(instrument_id) != AURORA:
        raise ValueError("No recorded scenario for this company")
    stages = STAGES if northstar else AURORA_STAGES
    entry = (RELEASES if northstar else AURORA_RELEASES).get(stage)
    info = stages[stage]
    stamp = dt(info["as_of"])
    prefix = "" if northstar else "aurora-"
    sources = ["company", "wire"] if northstar else ["aurora-company", "aurora-wire"]
    documents = []
    if entry:
        docid = uid(prefix + entry["key"])
        verid = uid(prefix + f"document-{stage}")
        facts = []
        if "period" in entry:
            for metric, key in [
                ("revenue_growth", "growth"),
                ("operating_margin", "margin"),
            ]:
                facts.append(
                    dict(
                        id=uid(prefix + f"{stage}-{metric}"),
                        metric=metric,
                        value=entry[key],
                        period=entry["period"],
                        period_start=entry["start"],
                        period_end=entry["end"],
                        supersedes_id=(
                            uid(f"2-{metric}") if northstar and stage == 4 else None
                        ),
                    )
                )
        if northstar:
            authored = authored_claims(stage)
        elif stage == 0:
            authored = [
                (
                    "reported",
                    "unknown",
                    "Growth at 8%, margin at 14%",
                    "Reported performance is a starting point for research, not a forecast.",
                    "quarterly revenue growth of 8% year over year",
                ),
                (
                    "guidance",
                    "unknown",
                    "Management expects a fourth-quarter sensor launch",
                    "Orders and the launch outcome remain unknown.",
                    "Management expects its new sensor range to launch in the fourth quarter.",
                ),
            ]
        elif stage == 1:
            authored = [
                (
                    "news_report",
                    "challenge",
                    "Component timing needs confirmation",
                    "This report raises a launch question; it is not company confirmation.",
                    "Aurora has not confirmed a launch delay.",
                )
            ]
        else:
            authored = [
                (
                    "reported",
                    "support",
                    "Revenue growth increased to 10%",
                    "Growth and margin may move in different directions.",
                    "quarterly revenue growth of 10% year over year",
                ),
                (
                    "reported",
                    "challenge",
                    "Operating margin fell to 11%",
                    "Review the margin assumption separately from revenue growth.",
                    "operating margin of 11%",
                ),
            ]
        claims = [
            dict(
                id=uid(prefix + f"claim-{stage}-{i}"),
                kind=k,
                stance=st,
                title=t,
                body=b,
                quote=q,
            )
            for i, (k, st, t, b, q) in enumerate(authored)
        ]
        source = entry["source"] if northstar else "aurora-" + entry["source"]
        documents.append(
            dict(
                id=docid,
                version_id=verid,
                source_id=source,
                url=f"fixture://{'northstar' if northstar else 'aurora'}/{entry['key']}",
                headline=entry["title"],
                body=entry["body"],
                published_at=stamp,
                available_at=stamp,
                supersedes_id=uid("document-2") if northstar and stage == 4 else None,
                story_key=entry["key"],
                origin_key=source,
                facts=facts,
                claims=claims,
            )
        )
    failure = stage == 3
    checks = [
        dict(
            id=uid(prefix + f"check-{stage}-{source}"),
            source_id=source,
            checked_at=stamp,
            outcome=("failed" if northstar else "denied") if failure else "success",
            cursor=None if failure else str(stage),
            covered_through=None if failure else stamp,
            error="Recorded supplier failure" if failure else None,
        )
        for source in sources
    ]
    return Batch(
        instrument_id=instrument_id,
        cutoff=stamp,
        period=info["period"],
        sequence=stage,
        label=info["label"],
        scenario_complete=stage == 4,
        documents=documents,
        checks=checks,
    )


def seed_aurora(conn):
    conn.execute(
        "INSERT INTO instruments VALUES(%s,%s,%s) ON CONFLICT DO NOTHING",
        (AURORA, "AURQ", "Aurora Devices"),
    )
    conn.execute(
        "INSERT INTO instrument_state(instrument_id,cutoff,period,label,sector) VALUES(%s,%s,'2025-Q2','Q2 baseline','Industrial sensors') ON CONFLICT DO NOTHING",
        (AURORA, AURORA_STAGES[0]["as_of"]),
    )
    for key, name in [
        ("aurora-company", "Aurora company release"),
        ("aurora-wire", "Sample Hardware Wire"),
    ]:
        conn.execute(
            "INSERT INTO sources VALUES(%s,%s,'fictional') ON CONFLICT DO NOTHING",
            (key, name),
        )
        conn.execute(
            "INSERT INTO instrument_sources VALUES(%s,%s) ON CONFLICT DO NOTHING",
            (AURORA, key),
        )
    if not one(
        conn,
        "SELECT id FROM document_versions WHERE id=%s",
        (uid("aurora-document-0"),),
    ):
        ingest_batch(conn, recorded_batch(AURORA, 0))
