"""Singapore timestamp presentation; never change stored values or date rules."""

from datetime import datetime
from zoneinfo import ZoneInfo

SINGAPORE = ZoneInfo("Asia/Singapore")
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sept", "Oct", "Nov", "Dec")


def stamp(value, *, seconds=False, fallback="Not recorded"):
    if not value:
        return fallback
    try:
        parsed = (
            value
            if isinstance(value, datetime)
            else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        )
        # A calendar date or a timestamp without an offset is not an instant.
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            return fallback
        local = parsed.astimezone(SINGAPORE)
        clock = local.strftime("%H:%M:%S" if seconds else "%H:%M")
        return f"{local.day} {MONTHS[local.month - 1]} {local.year}, {clock} SGT"
    except (ValueError, TypeError, OverflowError):
        return fallback


def reporting_age_explanation(explanation, age):
    age = age or {}
    saved = (
        f"Too old to assess: the period ended {age.get('period_end')}. "
        f"Your {age.get('max_report_age_days')}-day limit expired at {age.get('expires_at')}. "
        "The last figure and source are retained."
    )
    if explanation != saved:
        return explanation
    local = stamp(age["expires_at"], fallback=None)
    return explanation.replace(age["expires_at"], local) if local else explanation
