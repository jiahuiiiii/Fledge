"""Source-stated calendar dates for optional event-occurrence conditions."""

import re
from datetime import date, datetime, timezone

MONTHS = {
    name: i
    for i, name in enumerate(
        (
            "january",
            "february",
            "march",
            "april",
            "may",
            "june",
            "july",
            "august",
            "september",
            "october",
            "november",
            "december",
        ),
        1,
    )
}
MONTHS.update({k[:3]: v for k, v in list(MONTHS.items())})
MONTHS["sept"] = 9


def exact_day(text):
    """Accept a whole explicit date, never relative, partial or ambiguous numeric text."""
    text = text.strip()
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
            return date.fromisoformat(text)
        pattern = r"([A-Za-z]+)\.?\s+(\d{1,2})(?:st|nd|rd|th)?(?:,)?\s+(\d{4})"
        match = re.fullmatch(pattern, text, re.I)
        if match:
            month, day, year = match.groups()
        else:
            match = re.fullmatch(
                r"(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\.?\s+(\d{4})", text, re.I
            )
            if not match:
                return None
            day, month, year = match.groups()
        return date(int(year), MONTHS[month.lower()], int(day))
    except (ValueError, KeyError):
        return None


def timing(event, selected, citations, sources):
    """Validate quote ownership and calculate window membership without model arithmetic."""
    by_key = {(c["source_id"], c["passage_id"]): c for c in citations}
    dates = []
    seen = set()
    for item in selected:
        key = (item.source_id, item.passage_id)
        citation = by_key.get(key)
        identity = (*key, item.date_text)
        if not citation or item.date_text not in citation["quote"] or identity in seen:
            raise ValueError(
                "Event date must be unique exact text from its own cited passage."
            )
        seen.add(identity)
        parsed = exact_day(item.date_text)
        # The full date cannot be clipped out of a larger numeric date token.
        if parsed and not re.search(
            r"(?<![\w/\-])" + re.escape(item.date_text) + r"(?![\w/\-])",
            citation["quote"],
        ):
            parsed = None
        source_day = (
            datetime.fromisoformat(sources[item.source_id]["published_at"])
            .astimezone(timezone.utc)
            .date()
        )
        state = (
            "unknown_date"
            if not parsed
            else (
                "after_report"
                if parsed > source_day
                else (
                    "within_window"
                    if date.fromisoformat(event["window_start"])
                    <= parsed
                    <= date.fromisoformat(event["deadline"])
                    else "outside_window"
                )
            )
        )
        detail = dict(
            date_text=item.date_text,
            date=parsed.isoformat() if parsed else None,
            state=state,
        )
        citation.setdefault("occurrence_dates", []).append(detail)
        dates.append(detail)
    accepted = bool(dates) and all(d["state"] == "within_window" for d in dates)
    if accepted:
        message = (
            "Source-stated event date(s): "
            + ", ".join(sorted({d["date"] for d in dates}))
            + ". Within your event window; this is an AI selection of the event's date, not independent verification."
        )
    else:
        message = (
            "The chosen event window is unconfirmed: "
            + (
                "no explicit event date was selected."
                if not dates
                else "one or more selected dates are missing a full calendar day, after the report, or outside your chosen window."
            )
            + " The report's publication date is not substituted for the event date."
        )
    return accepted, message
