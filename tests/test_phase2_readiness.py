"""Readiness assessment is offline; live reads use a disposable read-only DB."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import psycopg
from psycopg.rows import dict_row
import pytest

from experiments.soclaas_replay.phase2_readiness import assess, collect, report, EXPECTED
from thesis.config import dsn
from thesis.db import transaction
from thesis.providers import ledger
from test_watch_history import begin, run

START = datetime(2026, 10, 17, tzinfo=timezone.utc)


def saved_call(hours=0, *, usd="1", settled=True, model=EXPECTED[2]):
    at = START + timedelta(hours=hours)
    return dict(created_at=at, finished_at=at + timedelta(minutes=1) if settled else None,
                model=model, status="settled" if settled else "unresolved",
                charged_nano_usd=int(Decimal(usd) * ledger.NANO) if settled else None,
                reserved_nano_usd=int(Decimal(usd) * ledger.NANO))


def evaluate(checks=None, calls=None, *, hours=48, deployed=True, selection=EXPECTED):
    return assess(START, START + timedelta(hours=hours),
                  checks or dict(completed=100, new_policy_completed=100), calls or [],
                  selection=selection, deployment_confirmed=deployed)


def test_exact_completion_cost_boundary_and_zero_switch_cost():
    value=evaluate(dict(completed=97,failed=1,stopped=1,unfinished=1,new_policy_completed=97),
                   [saved_call(usd="3"),saved_call(24,usd="3")])
    assert value["passed"] and value["completion_percent"] == 97
    assert [d["maximum_usd"] for d in value["daily_windows"]] == ["3","3"]
    assert value["switch_catch_up_usd"] == "0" and value["switch_performed"] is False


@pytest.mark.parametrize("checks", [dict(completed=96, unfinished=4),
                                     dict(completed=96, failed=2, stopped=2), {}])
def test_unfinished_failed_stopped_and_empty_windows_cannot_pass(checks):
    value=assess(START,START+timedelta(hours=48),checks,[],selection=EXPECTED,deployment_confirmed=True)
    assert not value["passed"] and value["gates"]["completion"] == "failed"
    if not checks: assert value["completion_percent"] is None


def test_elapsed_time_deployment_and_new_policy_each_required():
    assert evaluate(hours=47.99)["gates"]["completion"] == "pending"
    assert evaluate(deployed=False)["gates"]["deployment"] == "pending"
    assert not evaluate(deployed=False)["passed"]
    assert evaluate(dict(completed=100))["gates"]["new_reliability_observed"] == "pending"


def test_cost_includes_uncertain_maximum_and_stops_at_exact_window_end():
    value=evaluate(calls=[saved_call(usd="2.90"),saved_call(1,usd=".11",settled=False),
                          saved_call(-1,usd="99"),saved_call(48,usd="99")])
    assert value["gates"]["daily_cost"] == "failed" and value["unsettled_calls"] == 1
    assert value["daily_windows"][0]["maximum_usd"] == "3.01"
    assert value["daily_windows"][0]["settled_usd"] == "2.9"
    assert sum(d["calls"] for d in value["daily_windows"]) == 2
    assert evaluate(calls=[saved_call(usd=".01",settled=False)])["gates"]["daily_cost"] == "pending"


def test_later_settlement_is_still_a_hold_at_the_observation_end():
    call=saved_call(usd=".5");call["finished_at"]=START+timedelta(hours=49)
    value=evaluate(calls=[call])
    assert value["unsettled_calls"] == 1 and value["daily_windows"][0]["settled_usd"] == "0"


def test_other_configuration_or_observed_model_prevents_acceptance():
    assert evaluate(selection=("anthropic","claude-haiku-5-5","claude-sonnet-5-5"))["gates"]["selected_models"] == "failed"
    assert evaluate(calls=[saved_call(model="other")])["gates"]["selected_models"] == "failed"


def test_clock_validation_and_first_48_hours_are_fixed():
    with pytest.raises(ValueError,match="timezone"):
        assess(START.replace(tzinfo=None),START,{},[],selection=EXPECTED)
    with pytest.raises(ValueError,match="precedes"):
        evaluate(hours=-1)
    value=evaluate(hours=72,calls=[saved_call(48,usd="20")])
    assert value["elapsed_hours"] == 48 and value["passed"]


def test_live_reader_aggregates_without_mutation_and_excludes_experiments(owner):
    iid, _ = begin(owner,baseline=False)
    since=datetime.now(timezone.utc)-timedelta(seconds=1)
    assert run(owner)
    with transaction(admin=True) as conn:
        # Give this existing mocked call an experiment identity, only in the test DB.
        # Settled rows are immutable, so make a separate mocked ledger call instead.
        existing=conn.execute("SELECT request_body FROM model_calls ORDER BY created_at DESC LIMIT 1").fetchone()["request_body"]
    from test_sentiment import provider
    ledger.execute("experiment:readiness-authored", "authored", existing,transport=provider())
    until=datetime.now(timezone.utc)
    before=ledger.snapshot()
    with psycopg.connect(dsn("thesis_local"),row_factory=dict_row,
                         options="-c default_transaction_read_only=on") as conn:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        checks,calls=collect(conn,since,until)
        assert checks["completed"] == 1 and checks["new_policy_completed"] == 1
        assert len(calls) == 1
        with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
            conn.execute("INSERT INTO demo_state VALUES(false,0)")
    value=report(since,as_of=until)
    assert not value["passed"] and value["checks"]["total"] == 1
    assert str(owner) not in str(value) and iid not in str(value)
    assert ledger.snapshot() == before


def test_late_watch_result_is_unfinished_at_cutoff(owner):
    begin(owner,baseline=False)
    since=datetime.now(timezone.utc)-timedelta(seconds=1)
    assert run(owner)
    with transaction(admin=True) as conn:
        start=conn.execute("SELECT started_at FROM watch_checks ORDER BY started_at DESC LIMIT 1").fetchone()["started_at"]
    with psycopg.connect(dsn("thesis_local"),row_factory=dict_row,
                         options="-c default_transaction_read_only=on") as conn:
        checks,_=collect(conn,since,start+timedelta(microseconds=1))
    assert checks["unfinished"] == 1 and checks["completed"] == 0
