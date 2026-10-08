"""Code-owned window/deadline outcomes around explicitly requested AI evidence checks.

Each condition explicitly chooses publication or source-stated occurrence dates.
No report is not proof of failure or of safety. All dates are inclusive UTC dates.
"""

from datetime import date, datetime, time, timedelta, timezone
from .age import instant
from .event_windows import windows, effective


def boundaries(events):
    return sorted(
        {
            datetime.combine(
                date.fromisoformat(str(e[k]))
                + timedelta(days=1 if k == "deadline" else 0),
                time(),
                timezone.utc,
            )
            for original in events
            for e in windows(original)
            for k in ("window_start", "deadline")
        }
    )


def window_state(event, clock):
    event, _ = effective(event, clock)
    day = instant(clock).date()
    start, end = date.fromisoformat(str(event["window_start"])), date.fromisoformat(
        str(event["deadline"])
    )
    return (
        "not_started"
        if day < start
        else "deadline_unconfirmed" if day > end else "within_window"
    )


def assess(events, review, clock):
    checked = {
        r["condition_id"]: r for r in (review or {}).get("result", {}).get("events", [])
    }
    result = []
    for event in events:
        cid = str(event["condition_id"])
        point = checked.get(cid)
        _, selected_window = effective(event, clock)
        recurring = bool(event.get("repeat_months"))
        if recurring and (not point or point.get("window") != selected_window):
            point = None
        occurrence = event.get("date_basis") == "event_occurrence"
        phase = window_state(event, clock)
        evidence = point["status"] if point else "not_checked"
        citations = point.get("citations", []) if point else []
        outcome = "unknown"
        state = evidence
        if phase == "not_started":
            state = "not_started"
            explanation = "The chosen report window has not started. No event outcome is established."
        elif evidence == "confirmed":
            outcome = "met" if event["role"] == "required" else "not_met"
            state = "confirmed" if event["role"] == "required" else "risk_reported"
            explanation = (
                "AI interpretation found a report matching your required event and evidence criteria. "
                if event["role"] == "required"
                else "AI interpretation found a report matching the risk you chose to watch. "
            ) + point["explanation"]
        else:
            state = phase if phase == "deadline_unconfirmed" else evidence
            prefix = (
                "The report deadline passed without confirmation in the checked evidence. This does not prove the event failed to happen. "
                if phase == "deadline_unconfirmed"
                else ""
            )
            explanation = prefix + (
                point["explanation"]
                if point
                else "Event evidence has not been checked for this exact revision and source snapshot. No automatic AI call was made."
            )
        if occurrence:
            explanation = explanation.replace(
                "chosen report window", "chosen event window"
            ).replace("report deadline", "event deadline")
        result.append(
            dict(
                condition_id=cid,
                outcome=outcome,
                state=state,
                explanation=explanation,
                citations=citations,
                review_id=(
                    str(review["id"]) if review and (point or not recurring) else None
                ),
                disagreement=evidence == "conflicting",
                **({"window": selected_window} if recurring else {}),
            )
        )
    return result


def combined_outcome(results):
    return (
        "not_met"
        if any(r["outcome"] == "not_met" for r in results)
        else "unknown" if any(r["outcome"] == "unknown" for r in results) else "met"
    )
