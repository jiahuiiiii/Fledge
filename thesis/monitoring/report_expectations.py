"""Explicit dates for required reporting evidence, not inferred filing deadlines."""

from datetime import date, datetime, time, timedelta, timezone
from .age import instant
from thesis.research.facts import resolve_fact


def expectation(condition, observation, clock, resolution=None):
    target, due = condition.get("expected_period_end"), condition.get(
        "expected_report_by"
    )
    if target is None and due is None:
        return None
    target, due = date.fromisoformat(str(target)), date.fromisoformat(str(due))
    end = (
        date.fromisoformat(str(observation["period_end"]))
        if observation and observation.get("period_end")
        else None
    )
    check_at = datetime.combine(due + timedelta(days=1), time(), timezone.utc)
    state = (
        "available"
        if end and end >= target
        else "overdue" if instant(clock) >= check_at else "waiting"
    )
    if (
        resolution
        and resolution.get("disagreement")
        and any(
            o.get("period_end") and date.fromisoformat(str(o["period_end"])) >= target
            for o in resolution.get("candidates", [])
        )
    ):
        state = "conflicting"
    return dict(
        condition_id=str(condition["condition_id"]),
        period_type=condition.get("period_type", "quarter"),
        expected_period_end=target.isoformat(),
        expected_report_by=due.isoformat(),
        check_at=check_at.isoformat(),
        observed_period_end=end.isoformat() if end else None,
        state=state,
    )


def states(conditions, observations, period, clock):
    result = []
    for condition in conditions:
        if condition.get("expected_period_end") is None:
            continue
        resolved = resolve_fact(
            observations,
            condition["metric"],
            period,
            condition["unit"],
            condition["basis"],
            condition.get("period_type", "quarter"),
        )
        result.append(expectation(condition, resolved["observation"], clock, resolved))
    return result


def explanation(state):
    target, due = state["expected_period_end"], state["expected_report_by"]
    if state["state"] == "available":
        return f"Required {state['period_type']} figures are available for a period ending {state['observed_period_end']}, meeting your on-or-after {target} period requirement. This does not establish when the company filed or when the figures were first published."
    if state["state"] == "conflicting":
        return f"Conflicting {state['period_type']} figures cover your required on-or-after {target} period. The numerical outcome remains unknown; inspect the conflicting sources. This is different from a missing filing."
    if state["state"] == "waiting":
        return f"You expect {state['period_type']} figures for a period ending on or after {target} by {due}, inclusive UTC. Until then, any compatible saved figures are assessed under your other conditions."
    return f"Expected figures are missing after your chosen {due} date: this condition needs {state['period_type']} figures for a period ending on or after {target}. The outcome is unknown; the last figure and source remain available. Missing evidence in this app does not prove the company filed late or failed to report."
