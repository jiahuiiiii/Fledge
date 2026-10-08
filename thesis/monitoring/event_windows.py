"""Finite calendar windows, anchored to the original chosen dates."""

from calendar import monthrange
from datetime import date
from .age import instant


def shift(day, months):
    day = date.fromisoformat(str(day))
    year, month0 = divmod(day.year * 12 + day.month - 1 + months, 12)
    last = monthrange(year, month0 + 1)[1]
    target_day = (
        last if day.day == monthrange(day.year, day.month)[1] else min(day.day, last)
    )
    return date(year, month0 + 1, target_day)


def windows(event):
    step, count = event.get("repeat_months", 0), event.get("repeat_count", 1)
    if (
        step not in (0, 1, 3, 12)
        or not isinstance(count, int)
        or isinstance(count, bool)
        or not 1 <= count <= 12
        or (step == 0) != (count == 1)
    ):
        raise ValueError(
            "Choose one window, or 2–12 monthly, quarterly or yearly windows."
        )
    result = []
    for i in range(count):
        start, end = shift(event["window_start"], step * i), shift(
            event["deadline"], step * i
        )
        if (
            end < start
            or end == date.max
            or (result and start <= date.fromisoformat(result[-1]["deadline"]))
        ):
            raise ValueError(
                "Recurring windows must be ordered, non-overlapping calendar dates."
            )
        result.append(
            dict(
                index=i + 1,
                count=count,
                window_start=start.isoformat(),
                deadline=end.isoformat(),
            )
        )
    if (
        date.fromisoformat(result[-1]["deadline"])
        - date.fromisoformat(result[0]["window_start"])
    ).days > 3650:
        raise ValueError("Keep the complete schedule within ten years.")
    return result


def current(event, clock, index=None):
    choices = windows(event)
    if index is not None:
        if (
            isinstance(index, bool)
            or not isinstance(index, int)
            or not 1 <= index <= len(choices)
        ):
            raise ValueError("Choose an existing window in this condition's schedule.")
        return choices[index - 1]
    day = instant(clock).date().isoformat()
    return next((w for w in reversed(choices) if w["window_start"] <= day), choices[0])


def effective(event, clock, index=None):
    window = current(event, clock, index)
    return (
        dict(
            event,
            window_start=date.fromisoformat(window["window_start"]),
            deadline=date.fromisoformat(window["deadline"]),
        ),
        window,
    )
