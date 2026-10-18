"""Read-only local operator report for the selected GPT pair's first 48 hours.

Run after the matching phase 1 backend/frontend installation, supplying its
confirmed deployment time. This script never operates app processes or calls
providers. Output contains aggregate counts/costs, without account identities.
Without --deployment-confirmed it reports preparation only, never acceptance.
"""
import argparse
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from thesis.config import dsn  # noqa: E402
from thesis.providers import settings  # noqa: E402
from thesis.research.sentiment_reliability import POLICY  # noqa: E402

HOURS = 48
NANO = Decimal(1_000_000_000)
EXPECTED = ("openai", settings.OPENAI_MODEL, settings.OPENAI_REASONING_MODEL)


def aware(value):
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Observation times must include a timezone")
    return value.astimezone(timezone.utc)


def assess(since, as_of, checks, calls, *, selection, deployment_confirmed=False):
    """Pure assessment of counts and saved ledger rows; never infers paid costs."""
    since, as_of = aware(since), aware(as_of)
    if as_of < since:
        raise ValueError("Observation end precedes its start")
    deadline = since + timedelta(hours=HOURS)
    until = min(as_of, deadline)
    full = as_of >= deadline
    total = sum(checks.get(status, 0) for status in ("completed", "failed", "stopped", "unfinished"))
    completed = checks.get("completed", 0)
    completion = Decimal(completed) / total if total else None
    daily = []
    models = set()
    unsettled = 0
    for offset in (0, 24):
        start = since + timedelta(hours=offset)
        end = start + timedelta(hours=24)
        charged = ceiling = count = 0
        for call in calls:
            created = aware(call["created_at"])
            if not (start <= created < min(until, end)):
                continue
            models.add(call["model"])
            count += 1
            finished = call.get("finished_at")
            settled = (call["status"] == "settled" and finished is not None
                       and aware(finished) <= until)
            if settled:
                charged += call["charged_nano_usd"]
                ceiling += call["charged_nano_usd"]
            else:
                ceiling += call["reserved_nano_usd"]
                unsettled += 1
        daily.append(dict(start=start.isoformat(), end=end.isoformat(),
                          complete=until >= end, calls=count,
                          settled_usd=str(Decimal(charged) / NANO),
                          maximum_usd=str(Decimal(ceiling) / NANO)))
    # A partial day can already exceed the limit, but cannot pass it yet.
    daily_status = ("failed" if any(Decimal(d["maximum_usd"]) > 3 for d in daily)
                    else "passed" if full and not unsettled else "pending")
    model_ok = tuple(selection) == EXPECTED and models <= set(EXPECTED[1:])
    gates = dict(
        deployment="passed" if deployment_confirmed else "pending",
        selected_models="passed" if model_ok else "failed",
        completion=("pending" if not full else
                    "passed" if completion is not None and completion >= Decimal(".97") else "failed"),
        new_reliability_observed="passed" if checks.get("new_policy_completed", 0) else "pending",
        daily_cost=daily_status,
        # This phase retains the existing OpenAI pair; it performs no switch.
        switch_catch_up="passed" if tuple(selection) == EXPECTED else "pending",
    )
    return dict(
        since=since.isoformat(), as_of=as_of.isoformat(), measured_until=until.isoformat(),
        required_hours=HOURS, elapsed_hours=round((until - since).total_seconds() / 3600, 4),
        selected_provider=selection[0], quick_model=selection[1], bulk_model=selection[2],
        checks=dict(checks, total=total),
        completion_percent=None if completion is None else round(float(completion * 100), 4),
        daily_windows=daily, unsettled_calls=unsettled,
        switch_performed=False if tuple(selection) == EXPECTED else None,
        switch_catch_up_usd="0" if tuple(selection) == EXPECTED else None,
        gates=gates, passed=all(status == "passed" for status in gates.values()),
        limitations=[
            "Uses recorded watch attempts, including unfinished attempts; missed schedule slots are not inferred.",
            "Daily costs use consecutive 24-hour windows from the observation start, excluding experiment: calls.",
            "Deployment confirmation is supplied by the operator after installation; this script cannot install or restart.",
            "This report does not replace the separate META/AVGO replay or the phase 1 three-day observation.",
        ],
    )


def collect(conn, since, until):
    """Aggregate across this local installation; caller enforces read-only mode."""
    result = conn.execute(
        "SELECT count(*) FILTER(WHERE r.status='completed') completed,"
        "count(*) FILTER(WHERE r.status='failed') failed,"
        "count(*) FILTER(WHERE r.status='stopped') stopped,"
        "count(*) FILTER(WHERE r.status IS NULL) unfinished,"
        "count(*) FILTER(WHERE r.status='completed' AND a.result->'repairs'->>'policy'=%s) new_policy_completed "
        "FROM watch_checks c LEFT JOIN watch_check_results r ON r.check_id=c.id AND r.completed_at<=%s "
        "LEFT JOIN sentiment_analyses a ON a.id=r.analysis_id "
        "WHERE c.started_at>=%s AND c.started_at<%s",
        (POLICY, until, since, until),
    ).fetchone()
    calls = conn.execute(
        "SELECT created_at,finished_at,model,status,charged_nano_usd,reserved_nano_usd "
        "FROM model_calls WHERE created_at>=%s AND created_at<%s "
        "AND request_key NOT LIKE 'experiment:%%' ORDER BY created_at",
        (since, until),
    ).fetchall()
    return dict(result), calls


def report(since, *, as_of=None, deployment_confirmed=False):
    import psycopg
    from psycopg.rows import dict_row
    since = aware(since)
    as_of = aware(as_of or datetime.now(timezone.utc))
    if as_of > datetime.now(timezone.utc) or as_of < since:
        raise ValueError("Choose an observation end between its start and now")
    until = min(as_of, since + timedelta(hours=HOURS))
    with psycopg.connect(dsn("thesis_local"), row_factory=dict_row,
                         options="-c default_transaction_read_only=on") as conn:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        checks, calls = collect(conn, since, until)
    return assess(since, as_of, checks, calls, selection=settings._models(),
                  deployment_confirmed=deployment_confirmed)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--since", type=datetime.fromisoformat, required=True,
                        help="Confirmed installation time including timezone")
    parser.add_argument("--as-of", type=datetime.fromisoformat)
    parser.add_argument("--deployment-confirmed", action="store_true",
                        help="Only use after the phase 1 backend and frontend are installed")
    args = parser.parse_args()
    print(json.dumps(report(args.since, as_of=args.as_of,
                            deployment_confirmed=args.deployment_confirmed), indent=2))
