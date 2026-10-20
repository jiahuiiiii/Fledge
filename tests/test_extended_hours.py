"""Pre-market and after-hours display quotes; transports are mocked."""
from datetime import datetime, timedelta, timezone
import httpx
import pytest
from thesis.db import transaction, one
from thesis.research import price_history as ph
from tests.test_price_history import payload, setup

DAY = datetime(2026, 10, 20, tzinfo=ph.NY)


def at(hour, minute=0):
    return int(DAY.replace(hour=hour, minute=minute).timestamp())


def intraday(prices, symbol="MSFT"):
    """5-minute chart with the provider's own pre/regular/post periods."""
    stamps = [stamp for stamp, _ in prices]
    return {"chart": {"error": None, "result": [{
        "meta": dict(
            symbol=symbol, currency="USD", exchangeTimezoneName="America/New_York",
            dataGranularity="5m", instrumentType="EQUITY",
            currentTradingPeriod={
                "pre": {"start": at(4), "end": at(9, 30)},
                "regular": {"start": at(9, 30), "end": at(16)},
                "post": {"start": at(16), "end": at(20)},
            },
        ),
        "timestamp": stamps,
        "indicators": {"quote": [{"close": [price for _, price in prices]}]},
    }]}}


def test_pre_market_price_is_labelled_from_provider_periods():
    raw = intraday([(at(8, 20), "101.5"), (at(8, 25), "101.75"), (at(8, 30), None)])
    quote = ph.extended_quote(raw, "MSFT", DAY.replace(hour=8, minute=34))
    assert quote["session"] == "pre-market" and quote["price"] == "101.75"
    assert quote["quoted_at"] == datetime.fromtimestamp(at(8, 25), timezone.utc).isoformat()


def test_after_hours_price_and_overnight():
    raw = intraday([(at(15, 55), "100"), (at(16, 5), "99"), (at(19, 55), "98.5")])
    for when in (DAY.replace(hour=19, minute=58), DAY.replace(hour=23, minute=30)):
        quote = ph.extended_quote(raw, "MSFT", when)
        assert quote["session"] == "after-hours" and quote["price"] == "98.5"


def test_regular_session_and_bad_data_give_no_extended_quote():
    regular = intraday([(at(8), "101"), (at(10), "102")])
    assert ph.extended_quote(regular, "MSFT", DAY.replace(hour=10, minute=3)) is None
    good = intraday([(at(8), "101")])
    now = DAY.replace(hour=8, minute=3)
    assert ph.extended_quote(good, "AAPL", now) is None
    for change in (
        lambda m: m.update(currency="EUR"),
        lambda m: m.update(dataGranularity="1d"),
        lambda m: m.pop("currentTradingPeriod"),
        lambda m: m["currentTradingPeriod"]["pre"].update(start="x"),
    ):
        raw = intraday([(at(8), "101")])
        change(raw["chart"]["result"][0]["meta"])
        assert ph.extended_quote(raw, "MSFT", now) is None
    for price in ("-1", "abc", "NaN"):
        assert ph.extended_quote(intraday([(at(8), price)]), "MSFT", now) is None
    # Future and week-old prices are not "latest".
    assert ph.extended_quote(intraday([(at(8, 30), "101")]), "MSFT", now) is None
    old = intraday([(at(8) - 8 * 86400, "101")])
    assert ph.extended_quote(old, "MSFT", now) is None


def test_extended_request_asks_for_pre_and_post_prices():
    calls = []

    def handler(request):
        calls.append(request)
        assert request.url.host == "query1.finance.yahoo.com"
        params = request.url.params
        assert params["interval"] == "5m" and params["range"] == "1d"
        assert params["includePrePost"] == "true"
        assert "Authorization" not in request.headers
        return httpx.Response(429, json={})

    import thesis.research.price_history as module
    original = module.configured
    module.configured = lambda: True
    try:
        with pytest.raises(ValueError, match="rate-limited"):
            ph.fetch_extended("MSFT", transport=httpx.MockTransport(handler))
    finally:
        module.configured = original
    assert len(calls) == 1


def test_regular_hours_gate():
    assert ph.regular_hours(DAY.replace(hour=10))
    assert not ph.regular_hours(DAY.replace(hour=8, minute=30))
    assert not ph.regular_hours(DAY.replace(hour=16))
    assert not ph.regular_hours(DAY.replace(hour=12) + timedelta(days=5))  # Sunday


def test_refresh_keeps_daily_bars_and_shows_newer_extended_price(owner, monkeypatch):
    iid = setup(owner, monkeypatch)
    now = datetime.now(timezone.utc)
    stamp = int((now - timedelta(minutes=10)).timestamp())
    raw = intraday([(stamp, "123.45")])
    periods = raw["chart"]["result"][0]["meta"]["currentTradingPeriod"]
    periods["pre"] = {"start": stamp - 600, "end": stamp + 3600}
    periods["regular"] = {"start": stamp + 3600, "end": stamp + 7200}
    periods["post"] = {"start": stamp + 7200, "end": stamp + 9000}
    daily = payload()
    ph.refresh(iid, fetcher=lambda *_: daily, extended_fetcher=lambda _: raw)
    with transaction(admin=True) as conn:
        series = one(conn, "SELECT s.series FROM price_history_snapshots s JOIN price_history_state t ON t.current_id=s.id WHERE t.instrument_id=%s", (iid,))["series"]
    assert series["latest_quote"]["session"] == "pre-market"
    assert series["latest_quote"]["price"] == "123.45"
    assert len(series["latest_quote"]["raw_sha256"]) == 64
    assert series["bars"] == ph.normalize(daily, "MSFT", *ph.window(datetime.now(timezone.utc)))["bars"]


def test_extended_failure_never_blocks_the_daily_refresh(owner, monkeypatch):
    iid = setup(owner, monkeypatch)

    def broken(_):
        raise ValueError("Yahoo price history is unavailable.")

    assert ph.refresh(iid, fetcher=lambda *_: payload(), extended_fetcher=broken)["sessions"] == 6
    assert ph.present(iid)["error"] is None


def test_older_extended_price_does_not_replace_a_newer_quote():
    series = {"latest_quote": {"price": "1", "quoted_at": "2026-10-20T14:00:00+00:00", "session": "regular session"}}
    raw = intraday([(at(8), "2")])
    assert ph.with_extended_quote(series, "MSFT", lambda _: raw) == series
