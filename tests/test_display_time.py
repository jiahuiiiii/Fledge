from datetime import datetime, timezone

import pytest

from thesis.display_time import stamp, reporting_age_explanation
from thesis.review_export import stamp as export_stamp
from thesis.monitoring.telegram_message import stamp as alert_stamp
from thesis.research.reddit_rss import wait_notice, _check_clock
from thesis.service import Conflict


@pytest.mark.parametrize("value,expected", [
    ("2026-10-11T23:50:00Z", "12 Oct 2026, 07:50 SGT"),
    ("2026-10-11T16:00:00Z", "12 Oct 2026, 00:00 SGT"),
    ("2026-12-31T16:00:00Z", "1 Jan 2027, 00:00 SGT"),
    ("2026-10-12T07:50:00+08:00", "12 Oct 2026, 07:50 SGT"),
    ("2026-09-03T04:26:00+08:00", "3 Sept 2026, 04:26 SGT"),
])
def test_singapore_timestamp(value, expected):
    assert stamp(value) == expected


def test_preserves_input_and_exports_seconds():
    value = datetime(2026, 10, 11, 23, 50, 32, 123000, tzinfo=timezone.utc)
    before = value.isoformat()
    assert export_stamp(value) == "12 Oct 2026, 07:50:32 SGT"
    assert alert_stamp(value) == "12 Oct 2026, 07:50 SGT"
    assert value.isoformat() == before


@pytest.mark.parametrize("value", [None, "", "invalid", "2026-10-12", "2026-10-12T07:50:00", datetime(2026, 10, 12)])
def test_never_invents_a_timestamp(value):
    assert stamp(value, fallback="Not supplied") == "Not supplied"


def test_cooldown_text_changes_presentation_only():
    until = datetime(2026, 10, 11, 16, tzinfo=timezone.utc)
    now = datetime(2026, 10, 11, 15, tzinfo=timezone.utc)
    row = {"denied": False, "blocked_until": until}
    assert "12 Oct 2026, 00:00 SGT" in wait_notice(until)
    with pytest.raises(Conflict, match="12 Oct 2026, 00:00 SGT"):
        _check_clock(row, now)
    assert row["blocked_until"] == until
    _check_clock(row, until)  # Same original deadline; no wait at expiry.


def test_saved_age_reason_is_formatted_only_when_exact():
    age = {"period_end": "2026-10-01", "max_report_age_days": 10, "expires_at": "2026-10-12T00:00:00+00:00"}
    text = "Too old to assess: the period ended 2026-10-01. Your 10-day limit expired at 2026-10-12T00:00:00+00:00. The last figure and source are retained."
    assert reporting_age_explanation(text, age) == text.replace(age["expires_at"], "12 Oct 2026, 08:00 SGT")
    assert reporting_age_explanation(text, None) == text
    assert reporting_age_explanation("Original quote " + age["expires_at"], age) == "Original quote " + age["expires_at"]
    assert age["expires_at"] == "2026-10-12T00:00:00+00:00"


def test_theme_download_uses_singapore_times_without_mutating_saved_text(monkeypatch):
    from copy import deepcopy
    from thesis.research import discussion_themes
    value = {"id": "reading", "cutoff": "2026-12-31T16:00:01Z", "created_at": "2026-12-31T16:00:02Z", "withheld": True}
    before = deepcopy(value)
    monkeypatch.setattr(discussion_themes, "get", lambda *a: value)
    _, html = discussion_themes.download("company", "reading")
    assert "1 Jan 2027, 00:00:01 SGT" in html and "1 Jan 2027, 00:00:02 SGT" in html
    assert value == before
