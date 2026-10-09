"""Daily-chart contracts; transports are mocked and storage is disposable."""

from datetime import datetime, timezone, timedelta
from copy import deepcopy
from pathlib import Path
from uuid import uuid4
import json
import httpx
import pytest
import psycopg
from thesis.db import transaction, one, rows
from thesis.research import price_history as ph
from thesis.research.sec.service import add_company


def payload(symbol="MSFT", count=6):
    start, end = ph.window(datetime.now(timezone.utc))
    days = []
    day = end - timedelta(days=1)
    while len(days) < count:
        if day.weekday() < 5:
            days.append(day)
        day -= timedelta(days=1)
    days.sort()
    return {
        "chart": {
            "error": None,
            "result": [
                {
                    "meta": dict(
                        symbol=symbol,
                        currency="USD",
                        instrumentType="EQUITY",
                        exchangeTimezoneName="America/New_York",
                        dataGranularity="1d",
                    ),
                    "timestamp": [
                        int(d.replace(hour=9, minute=30).timestamp()) for d in days
                    ],
                    "indicators": {
                        "quote": [
                            dict(
                                open=["100.123456789"] * count,
                                high=["110"] * count,
                                low=["90"] * count,
                                close=["105.2"] * count,
                                volume=[1000000 + i for i in range(count)],
                            )
                        ]
                    },
                }
            ],
        }
    }


def norm(raw):
    return ph.normalize(raw, "MSFT", *ph.window(datetime.now(timezone.utc)))


def setup(owner, monkeypatch):
    monkeypatch.setattr(ph, "configured", lambda: True)
    with transaction(admin=True) as c:
        c.execute(
            "INSERT INTO sources VALUES('yahoo-price-history','Yahoo daily history','local-yahoo-history') ON CONFLICT DO NOTHING"
        )
    return add_company("MSFT")["instrument_id"]


def age(iid):
    with transaction(admin=True) as c:
        c.execute(
            "UPDATE price_history_state SET last_attempt_at=now()-interval '2 hours' WHERE instrument_id=%s",
            (iid,),
        )


def test_exact_prices_alignment_missing_volume_and_incomplete_current_day():
    raw = payload()
    r = raw["chart"]["result"][0]
    q = r["indicators"]["quote"][0]
    q["close"][1] = None
    q["volume"][3] = None
    # A current-day entry without OHLC stays unknown; arrays cannot shift.
    r["timestamp"].append(
        int(
            datetime.now(timezone.utc)
            .astimezone(ph.NY)
            .replace(hour=9, minute=30)
            .timestamp()
        )
    )
    cutoff = datetime.now(timezone.utc).astimezone(ph.NY).replace(hour=17)
    series = ph.normalize(raw, "MSFT", *ph.window(cutoff))
    assert (
        len(series["bars"]) == 5
        and series["omitted_sessions"] == 2
        and series["outside_window_sessions"] == 0
    )
    assert series["bars"][0]["open"] == "100.123456789"
    assert (
        series["bars"][1]["volume"] == "1000002" and series["bars"][2]["volume"] is None
    )
    assert series["missing_volume_sessions"] == 1


def today_payload(now):
    raw = payload(count=2)
    result = raw["chart"]["result"][0]
    opening = now.astimezone(ph.NY).replace(hour=9, minute=30, second=0, microsecond=0)
    result["timestamp"] = [int((opening - timedelta(days=1)).timestamp()), int(opening.timestamp())]
    result["meta"].update(
        regularMarketPrice="106.3456789", regularMarketTime=int(now.timestamp()),
        exchangeDataDelayedBy=15,
        currentTradingPeriod={"regular": {"start": int(opening.timestamp()), "end": int(opening.replace(hour=16, minute=0).timestamp())}},
    )
    return raw


@pytest.mark.parametrize("hour,provisional", [(11, True), (17, False)])
def test_latest_same_day_bar_and_quote_before_new_york_midnight(hour, provisional):
    now = datetime(2026, 10, 8, hour, 15, tzinfo=ph.NY)
    start, end = ph.window(now)
    assert end == now
    series = ph.normalize(today_payload(now), "MSFT", start, end)
    assert series["bars"][-1]["date"] == "2026-10-08"
    assert series["bars"][-1]["provisional"] is provisional
    assert series["latest_quote"]["price"] == "106.3456789"
    assert series["latest_quote"]["quoted_at"] == now.astimezone(timezone.utc).isoformat()
    assert series["delay_minutes"] == 15


def test_future_bars_and_future_quotes_are_not_latest_and_unknown_close_stays_provisional():
    now = datetime(2026, 10, 8, 11, 15, tzinfo=ph.NY)
    raw = today_payload(now)
    result = raw["chart"]["result"][0]
    result["timestamp"][-1] += 86400
    result["meta"]["regularMarketTime"] += 60
    series = ph.normalize(raw, "MSFT", *ph.window(now))
    assert len(series["bars"]) == 1 and series["outside_window_sessions"] == 1
    assert series["latest_quote"] is None
    raw = today_payload(now.replace(hour=17))
    del raw["chart"]["result"][0]["meta"]["currentTradingPeriod"]
    assert ph.normalize(raw, "MSFT", *ph.window(now.replace(hour=17)))["bars"][-1]["provisional"]


def test_new_york_dst_cutoff_keeps_current_day_in_both_seasons():
    for month, utc_hour in [(1, 15), (7, 14)]:
        now = datetime(2026, month, 8, utc_hour, tzinfo=timezone.utc)
        start, end = ph.window(now)
        assert end.hour == 10 and end.date() == now.date()
        assert start.hour == 0


def test_delayed_quote_before_bell_does_not_finalize_same_day_candle():
    now = datetime(2026, 10, 8, 16, 5, tzinfo=ph.NY)
    raw = today_payload(now)
    raw["chart"]["result"][0]["meta"]["regularMarketTime"] = int(now.replace(hour=15, minute=59).timestamp())
    assert ph.normalize(raw, "MSFT", *ph.window(now))["bars"][-1]["provisional"]


def test_latest_after_hours_quote_is_separate_from_daily_candle():
    now = datetime(2026, 10, 8, 18, tzinfo=ph.NY)
    raw = today_payload(now.replace(hour=16))
    raw["chart"]["result"][0]["meta"].update(postMarketPrice="111", postMarketTime=int(now.timestamp()))
    series = ph.normalize(raw, "MSFT", *ph.window(now))
    assert series["latest_quote"]["session"] == "after-hours"
    assert series["latest_quote"]["price"] == "111"
    assert series["bars"][-1]["close"] == "105.2"


def test_quote_received_during_fetch_is_eligible_but_future_quotes_stay_unknown():
    now = datetime(2026, 10, 8, 11, 15, tzinfo=ph.NY)
    received = now + timedelta(seconds=3)
    raw = today_payload(received)
    series = ph.normalize(raw, "MSFT", *ph.window(now), observed_at=received)
    assert series["latest_quote"]["quoted_at"] == received.astimezone(timezone.utc).isoformat()
    raw["chart"]["result"][0]["meta"]["regularMarketTime"] += 60
    assert ph.normalize(raw, "MSFT", *ph.window(now), observed_at=received)["latest_quote"] is None


def test_refresh_allows_updates_after_one_minute_not_one_hour(owner, monkeypatch):
    iid = setup(owner, monkeypatch)
    ph.refresh(iid, fetcher=lambda *_: payload())
    with pytest.raises(ValueError, match="one minute"):
        ph.refresh(iid, fetcher=lambda *_: pytest.fail("too soon"))
    with transaction(admin=True) as conn:
        conn.execute("UPDATE price_history_state SET last_attempt_at=now()-interval '61 seconds' WHERE instrument_id=%s", (iid,))
    ph.refresh(iid, fetcher=lambda *_: payload())
    assert ph.present(iid)["refresh_interval_seconds"] == 60


@pytest.mark.parametrize(
    "fault",
    [
        "symbol",
        "currency",
        "timezone",
        "interval",
        "type",
        "high",
        "zero",
        "nan",
        "bool",
        "volume",
        "duplicate",
        "timestamp",
        "empty",
        "error",
    ],
)
def test_bad_metadata_or_values_cannot_enter_chart(fault):
    raw = payload()
    r = raw["chart"]["result"][0]
    q = r["indicators"]["quote"][0]
    fields = {
        "symbol": ("symbol", "AAPL"),
        "currency": ("currency", "EUR"),
        "timezone": ("exchangeTimezoneName", "UTC"),
        "interval": ("dataGranularity", "1mo"),
        "type": ("instrumentType", "ETF"),
    }
    if fault in fields:
        r["meta"][fields[fault][0]] = fields[fault][1]
    elif fault == "high":
        q["high"][0] = "80"
    elif fault == "zero":
        q["close"][0] = "0"
    elif fault == "nan":
        q["close"][0] = "NaN"
    elif fault == "bool":
        q["open"][0] = True
    elif fault == "volume":
        q["volume"][0] = "3.5"
    elif fault == "duplicate":
        r["timestamp"][1] = r["timestamp"][0]
    elif fault == "timestamp":
        r["timestamp"][0] = False
    elif fault == "empty":
        r["timestamp"] = []
    elif fault == "error":
        raw["chart"]["error"] = {"description": "<script>provider error</script>"}
    with pytest.raises(ValueError, match="Daily history did not match"):
        norm(raw)


def test_exchange_dates_use_historical_timezone_rules_not_current_fixed_offset():
    start = datetime(2026, 1, 1, tzinfo=ph.NY)
    end = datetime(2026, 8, 1, tzinfo=ph.NY)
    raw = payload(count=2)
    r = raw["chart"]["result"][0]
    r["timestamp"] = [
        int(datetime(2026, 1, 5, 4, 30, tzinfo=timezone.utc).timestamp()),
        int(datetime(2026, 7, 6, 4, 30, tzinfo=timezone.utc).timestamp()),
    ]
    assert [b["date"] for b in ph.normalize(raw, "MSFT", start, end)["bars"]] == [
        "2026-01-04",
        "2026-07-06",
    ]


def test_short_arrays_are_not_shifted_or_filled_and_single_session_is_valid():
    raw = payload(count=3)
    r = raw["chart"]["result"][0]
    r["indicators"]["quote"][0]["close"] = ["101"]
    series = norm(raw)
    assert len(series["bars"]) == 1 and series["omitted_sessions"] == 2
    assert series["bars"][0]["volume"] == "1000000"


def test_current_snapshot_survives_bad_older_and_truncated_replies(owner, monkeypatch):
    iid = setup(owner, monkeypatch)
    original = payload()
    rid = ph.refresh(iid, fetcher=lambda *_: original)["id"]
    for mutate in ("bad", "older", "missing"):
        age(iid)
        raw = deepcopy(original)
        r = raw["chart"]["result"][0]
        if mutate == "bad":
            r["meta"]["symbol"] = "GOOGL"
        elif mutate == "older":
            r["timestamp"].pop()
        else:
            r["indicators"]["quote"][0]["close"][1] = None
        with pytest.raises(ValueError, match="earlier prices are retained"):
            ph.refresh(iid, fetcher=lambda *_: raw)
        data = ph.present(iid)
        assert str(data["snapshot"]["id"]) == rid and data["error"]
    with transaction() as c:
        assert one(c, "SELECT count(*) n FROM price_history_snapshots")["n"] == 1


def test_full_snapshot_correction_and_return_do_not_mix_adjustment_vintages(
    owner, monkeypatch
):
    iid = setup(owner, monkeypatch)
    a = payload()
    b = deepcopy(a)
    for k in ("open", "high", "low", "close"):
        b["chart"]["result"][0]["indicators"]["quote"][0][k] = [
            str(float(v) / 2)
            for v in b["chart"]["result"][0]["indicators"]["quote"][0][k]
        ]
    ids = []
    for raw in (a, b, a):
        age(iid)
        ids.append(ph.refresh(iid, fetcher=lambda *_: raw)["id"])
    assert len(set(ids)) == 3 and str(ph.present(iid)["snapshot"]["id"]) == ids[-1]
    with transaction() as c:
        old = one(
            c, "SELECT series FROM price_history_snapshots WHERE id=%s", (ids[0],)
        )
        middle = one(
            c, "SELECT series FROM price_history_snapshots WHERE id=%s", (ids[1],)
        )
        assert (
            old["series"]["bars"][0]["close"] == "105.2"
            and middle["series"]["bars"][0]["close"] == "52.6"
        )
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with transaction() as c:
            c.execute("UPDATE price_history_snapshots SET symbol='X'")
    with pytest.raises(psycopg.errors.RaiseException):
        with transaction(admin=True) as c:
            c.execute("UPDATE price_history_snapshots SET symbol='X'")


def test_concurrent_refresh_cooldown_and_late_result_fencing(owner, monkeypatch):
    iid = setup(owner, monkeypatch)

    def fetch(*_):
        with pytest.raises(ValueError, match="already running"):
            ph.refresh(iid, fetcher=lambda *_: pytest.fail("concurrent network"))
        with transaction(admin=True) as c:
            c.execute(
                "UPDATE price_history_state SET attempt_id=%s WHERE instrument_id=%s",
                (uuid4(), iid),
            )
        return payload()

    with pytest.raises(ValueError):
        ph.refresh(iid, fetcher=fetch)
    assert ph.present(iid)["snapshot"] is None
    with pytest.raises(ValueError):
        ph.refresh(iid, fetcher=lambda *_: pytest.fail("cooldown network"))


def test_withdrawal_hides_stored_series_and_fences_inflight_response(
    owner, monkeypatch
):
    iid = setup(owner, monkeypatch)
    ph.refresh(iid, fetcher=lambda *_: payload())
    age(iid)

    def withdraw(*_):
        with transaction(admin=True) as c:
            c.execute(
                "UPDATE sources SET entitlement='fictional' WHERE id=%s", (ph.SOURCE,)
            )
        return payload()

    with pytest.raises(ValueError):
        ph.refresh(iid, fetcher=withdraw)
    data = ph.present(iid)
    assert not data["available"] and data["snapshot"] is None
    with pytest.raises(ValueError):
        ph.refresh(iid, fetcher=lambda *_: pytest.fail("withdrawn source network"))


def test_transport_uses_bounded_public_endpoint_no_token_redirect_or_retry(
    owner, monkeypatch
):
    iid = setup(owner, monkeypatch)
    calls = []

    def handler(request):
        calls.append(request)
        assert request.url.host == "query1.finance.yahoo.com"
        assert (
            "X-Finnhub-Token" not in request.headers
            and "Authorization" not in request.headers
        )
        assert (
            request.url.params["interval"] == "1d"
            and request.url.params["includePrePost"] == "false"
        )
        return httpx.Response(403, json={"error": "no access"})

    with pytest.raises(ValueError, match="denied"):
        ph.fetch(
            "MSFT",
            *ph.window(datetime.now(timezone.utc)),
            transport=httpx.MockTransport(handler),
        )
    assert len(calls) == 1


def test_read_routes_are_cached_and_no_paid_or_source_call_occurs(owner, monkeypatch):
    from fastapi.testclient import TestClient
    from thesis.app import app

    iid = setup(owner, monkeypatch)
    ph.refresh(iid, fetcher=lambda *_: payload())
    monkeypatch.setattr(ph, "fetch", lambda *_: pytest.fail("reading fetched source"))
    with TestClient(app) as client:
        client.get("/api/v1/session")
        response = client.get(f"/api/v1/companies/{iid}/price-history")
        assert response.status_code == 200
        assert len(response.json()["result"]["snapshot"]["series"]["bars"]) == 6
        assert (
            client.post(f"/api/v1/companies/{iid}/price-history/refresh").status_code
            == 403
        )
    with transaction(source=True) as c:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            c.execute("SELECT * FROM thesis_versions")
