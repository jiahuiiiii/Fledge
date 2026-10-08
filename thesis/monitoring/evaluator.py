"""Typed, three-valued evaluation adapted from Kestrel pipeline/evaluator.py.

Preserves missing != failed and definite failure dominating ALL; removes trading
signals and requires a nonempty, exactly aligned condition set.
"""

from decimal import Decimal
from ..research.facts import resolve_fact
from .age import age_state
from .report_expectations import expectation, explanation as report_explanation

LEGACY_VERSION = "thesis-evaluator-4"
VERSION = "thesis-evaluator-5"
REPORT_VERSION = "thesis-evaluator-6"


def manifest_conditions(conditions):
    # Absence has always meant required. Preserve legacy manifests/signatures so
    # installing this feature alone does not enqueue assessments or create alerts.
    return [
        {
            k: v
            for k, v in c.items()
            if not (
                (k == "role" and v == "required")
                or (k in ("expected_period_end", "expected_report_by") and v is None)
            )
        }
        for c in conditions
    ]


def outcome_label(result):
    if result.get("role", "required") == "risk":
        return {
            "met": "Risk threshold not reached",
            "not_met": "Risk threshold reached",
            "unknown": "Not enough evidence",
        }[result["outcome"]]
    return {
        "met": "Condition met",
        "not_met": "Condition not met",
        "unknown": "Not enough evidence",
    }[result["outcome"]]


def evaluate(conditions, observations, period, assessed_at=None):
    if not conditions:
        raise ValueError("Monitoring needs at least one approved condition")
    results = []
    for condition in conditions:
        role = condition.get("role", "required")
        if role not in ("required", "risk"):
            raise ValueError("Unsupported numerical condition role")
        resolution = resolve_fact(
            observations,
            condition["metric"],
            period,
            condition["unit"],
            condition["basis"],
            condition.get("period_type", "quarter"),
        )
        observation = resolution["observation"]
        age = age_state(condition, observation, assessed_at) if assessed_at else None
        report = (
            expectation(condition, observation, assessed_at, resolution)
            if assessed_at
            else None
        )
        if report and report["state"] == "overdue":
            outcome = "unknown"
            reason = report_explanation(report)
        elif observation is None:
            outcome = "unknown"
            reason = resolution["reason"]
        elif age and age["state"] == "expired":
            outcome = "unknown"
            reason = f"Too old to assess: the period ended {age['period_end']}. Your {age['max_report_age_days']}-day limit expired at {age['expires_at']}. The last figure and source are retained."
        elif age and age["state"] == "unavailable":
            outcome = "unknown"
            reason = "Reporting period end is unavailable, so your age limit cannot be checked."
        else:
            value = Decimal(str(observation["value"]))
            threshold = Decimal(str(condition["threshold"]))
            passed = (
                value >= threshold
                if condition["operator"] == ">="
                else value <= threshold
            )
            if role == "risk":
                outcome = "not_met" if passed else "met"
                reason = (
                    f"Reported {value}%; your risk rule is {condition['operator']} {threshold}%. "
                    + (
                        "This risk threshold was reached; review the evidence."
                        if passed
                        else "This risk threshold was not reached. That does not establish that the investment is safe."
                    )
                )
            else:
                outcome = "met" if passed else "not_met"
                reason = f"{value}% {condition['operator']} {threshold}%: condition {'met' if passed else 'not met'}"
        results.append(
            dict(
                condition_id=str(condition["condition_id"]),
                outcome=outcome,
                observed_value=observation["value"] if observation else None,
                observation_id=str(observation["id"]) if observation else None,
                explanation=reason,
                disagreement=resolution["disagreement"],
            )
        )
    outcome = (
        "not_met"
        if any(r["outcome"] == "not_met" for r in results)
        else "unknown" if any(r["outcome"] == "unknown" for r in results) else "met"
    )
    return outcome, results
