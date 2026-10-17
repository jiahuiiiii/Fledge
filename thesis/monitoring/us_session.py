"""NYSE regular cash-equity sessions, verified calendar for 2026–2028.

Source: https://ir.theice.com/press/news-details/2025/NYSE-Group-Announces-2026-2027-and-2028-Holiday-and-Early-Closings-Calendar/default.aspx
Unknown years are deliberately hourly, pending a calendar update. Unscheduled
closures are not predicted; quote freshness is checked separately by consumers.
"""
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

NEW_YORK = ZoneInfo("America/New_York")
CLOSED = {
    2026: "01-01 01-19 02-16 04-03 05-25 06-19 07-03 09-07 11-26 12-25",
    2027: "01-01 01-18 02-15 03-26 05-31 06-18 07-05 09-06 11-25 12-24",
    2028: "01-17 02-21 04-14 05-29 06-19 07-04 09-04 11-23 12-25",
}
EARLY = {date(2026, 11, 27), date(2026, 12, 24), date(2027, 11, 26),
         date(2028, 7, 3), date(2028, 11, 24)}


def bounds(day):
    if day.year not in CLOSED or day.weekday() >= 5 or day.strftime("%m-%d") in CLOSED[day.year].split():
        return None
    return (datetime.combine(day, time(9, 30), NEW_YORK),
            datetime.combine(day, time(13 if day in EARLY else 16), NEW_YORK))


def fast_interval(now):
    if now.tzinfo is None:
        raise ValueError("The market-hours clock needs a timezone.")
    local = now.astimezone(NEW_YORK)
    session = bounds(local.date())
    return 15 if session and session[0] - timedelta(hours=1) <= local < session[1] + timedelta(hours=1) else 60


def next_fast_check(now):
    """An hourly off-hours check must not jump over the next fast window."""
    next_at = now + timedelta(minutes=fast_interval(now))
    local = now.astimezone(NEW_YORK)
    for offset in (0, 1, 2, 3, 4):
        session = bounds(local.date() + timedelta(days=offset))
        if session:
            opening = session[0] - timedelta(hours=1)
            if now < opening < next_at:
                next_at = opening
    return next_at
