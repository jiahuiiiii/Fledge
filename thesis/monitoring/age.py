"""User-defined age limits, independent of source-check freshness and retrieval."""

from datetime import date, datetime, time, timedelta, timezone
from thesis.research.facts import resolve_fact


def instant(value):
    result = datetime.fromisoformat(value) if isinstance(value, str) else value
    if result.tzinfo is None:
        raise ValueError("Assessment time requires a timezone")
    return result.astimezone(timezone.utc)


def age_state(condition, observation, assessed_at):
    limit = condition.get("max_report_age_days")
    result = dict(
        condition_id=str(condition["condition_id"]),
        max_report_age_days=limit,
        state="no_limit",
        period_end=None,
        expires_at=None,
    )
    if limit is None:
        return result
    end = observation.get("period_end") if observation else None
    if not end:
        return dict(result, state="unavailable")
    end = date.fromisoformat(end) if isinstance(end, str) else end
    # A limit of N includes the entire UTC date N days after period end.
    deadline = datetime.combine(end + timedelta(days=limit + 1), time(), timezone.utc)
    return dict(
        result,
        period_end=end.isoformat(),
        expires_at=deadline.isoformat(),
        state="expired" if instant(assessed_at) >= deadline else "within_limit",
    )


def age_states(conditions, observations, period, assessed_at):
    result = []
    for c in conditions:
        resolved = resolve_fact(
            observations,
            c["metric"],
            period,
            c["unit"],
            c["basis"],
            c.get("period_type", "quarter"),
        )
        result.append(age_state(c, resolved["observation"], assessed_at))
    return result
