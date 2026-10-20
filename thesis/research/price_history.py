"""Daily Yahoo chart acquisition adapted from Deus pipeline/price_feed.py.

Whole-window snapshots avoid mixing prices across split-adjustment vintages.
Completed captures can also provide explicitly dated arithmetic context for
source sentiment. They do not establish author attitude or company events.
"""

import hashlib
import json
import time
from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo
from uuid import uuid4
import httpx
from psycopg.types.json import Jsonb
from thesis.db import transaction, one
from thesis.providers.settings import settings
from .sec.service import COMPANIES, collection_lock

NY = ZoneInfo("America/New_York")
SOURCE = "yahoo-price-history"
BASIS = "Yahoo OHLC, split-adjusted as supplied; not dividend-adjusted. No independent corporate-action reconciliation."
REFRESH_INTERVAL = timedelta(seconds=60)


def configured():
    return settings().get("THESIS_LIVE_DATA_ENABLED") == "true"


def allowed(conn):
    return bool(
        one(
            conn,
            "SELECT id FROM sources WHERE id=%s AND entitlement='local-yahoo-history'",
            (SOURCE,),
        )
    )


def window(now):
    end = now.astimezone(NY)
    start = end.replace(hour=0, minute=0, second=0, microsecond=0)
    return start - timedelta(days=366), end


def latest_quote(meta, end):
    """Optional provider quote, kept separate from daily OHLC and its date."""
    quotes = []
    for price_key, time_key, session in (
        ("regularMarketPrice", "regularMarketTime", "regular session"),
        ("preMarketPrice", "preMarketTime", "pre-market"),
        ("postMarketPrice", "postMarketTime", "after-hours"),
    ):
        try:
            price = decimal(meta.get(price_key))
            stamp = meta.get(time_key)
            if isinstance(stamp, bool) or not isinstance(stamp, int) or stamp <= 0:
                continue
            at = datetime.fromtimestamp(stamp, timezone.utc)
            if not end - timedelta(days=7) <= at <= end:
                continue
            quotes.append(dict(price=str(price), quoted_at=at.isoformat(), session=session))
        except (ValueError, OverflowError, OSError):
            continue
    return max(quotes, key=lambda q: q["quoted_at"]) if quotes else None


def _wait_for_slot():
    """Shared Yahoo pacing: one request every two seconds across companies."""
    with transaction(source=True) as conn:
        row = one(
            conn, "SELECT next_at FROM price_history_clock WHERE singleton FOR UPDATE"
        )
        now = datetime.now(timezone.utc)
        slot = max(now, row["next_at"])
        delay = (slot - now).total_seconds()
        if delay > 6:
            raise ValueError("Price-history requests are busy. Try again later.")
        conn.execute(
            "UPDATE price_history_clock SET next_at=%s WHERE singleton",
            (slot + timedelta(seconds=2),),
        )
    if delay > 0:
        time.sleep(delay)


def fetch(symbol, start, end, *, transport=None):
    from .directory import valid_symbol
    if not valid_symbol(symbol) or not configured():
        raise ValueError("Daily price history is not connected for this company.")
    return _chart(symbol, dict(
        period1=int(start.timestamp()),
        period2=int(end.timestamp()),
        interval="1d",
        events="div,splits",
        includePrePost="false",
    ), transport)


def fetch_extended(symbol, *, transport=None):
    """Today's 5-minute prices including pre-market and after-hours trading.
    Used only for the latest displayed quote, never for daily bars or alerts."""
    from .directory import valid_symbol
    if not valid_symbol(symbol) or not configured():
        raise ValueError("Extended-hours prices are not connected for this company.")
    return _chart(symbol, dict(range="1d", interval="5m", includePrePost="true"), transport)


def _chart(symbol, params, transport):
    _wait_for_slot()
    try:
        with httpx.Client(
            headers={"User-Agent": "Thesis-local-pitch/0.1"},
            timeout=20,
            follow_redirects=False,
            transport=transport,
        ) as client:
            with client.stream(
                "GET",
                f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
                params=params,
            ) as response:
                from .source_observations import record
                record("yahoo_history", response.status_code)
                if response.status_code != 200:
                    raise ValueError(
                        "Yahoo price-history access was denied or rate-limited."
                        if response.status_code in (401, 403, 429)
                        else "Yahoo price history is unavailable."
                    )
                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > 1024 * 1024:
                        raise ValueError(
                            "Daily price response exceeded the supported size."
                        )
                return json.loads(body, parse_float=str)
    except (httpx.HTTPError, json.JSONDecodeError, UnicodeDecodeError):
        raise ValueError(
            "Daily price history could not be read. Earlier prices are retained."
        ) from None


def extended_quote(payload, symbol, observed_at):
    """Latest pre-market or after-hours price from a 5-minute chart, labelled
    by the provider's own trading periods. Regular-session prices are left to
    the daily chart; anything unexpected gives None (no extended quote)."""
    try:
        result = payload["chart"]["result"]
        if payload["chart"].get("error") or len(result) != 1:
            return None
        result = result[0]
        meta = result["meta"]
        if (
            meta.get("symbol") != symbol
            or meta.get("currency") != "USD"
            or meta.get("exchangeTimezoneName") != "America/New_York"
            or meta.get("dataGranularity") != "5m"
        ):
            return None
        periods = meta["currentTradingPeriod"]
        spans = {}
        for key, label in (("pre", "pre-market"), ("post", "after-hours")):
            period = periods[key]
            begin, finish = period["start"], period["end"]
            if type(begin) is not int or type(finish) is not int or not 0 < begin < finish:
                return None
            spans[label] = (begin, finish)
        stamps = result["timestamp"]
        closes = result["indicators"]["quote"][0]["close"]
        if not isinstance(stamps, list) or not isinstance(closes, list) or len(stamps) > 400:
            return None
        limit = int(observed_at.timestamp())
        for stamp, close in sorted(zip(stamps, closes), reverse=True):
            if type(stamp) is not int or not 0 < stamp <= limit or close is None:
                continue
            if stamp < limit - 7 * 86400:
                return None
            session = next((label for label, (begin, finish) in spans.items()
                            if begin <= stamp < finish), None)
            if not session:
                return None  # The newest price is regular-session (or unlabelled).
            price = decimal(close)
            return dict(price=str(price), quoted_at=datetime.fromtimestamp(stamp, timezone.utc).isoformat(),
                        session=session, interval="5m")
        return None
    except (KeyError, TypeError, IndexError, ValueError, OverflowError, OSError, AttributeError):
        return None


def decimal(value, *, zero=False):
    try:
        if isinstance(value, bool) or not isinstance(value, (str, int, float)):
            raise ValueError()
        d = Decimal(str(value))
        if not d.is_finite() or d < 0 or (not zero and d == 0) or d > Decimal("1e13"):
            raise ValueError()
        return d
    except (InvalidOperation, ValueError):
        raise ValueError("A daily price or volume is invalid.") from None


def at(values, index):
    # Deus's aligned-array selection; never compact closes before OHLCV lookup.
    return values[index] if isinstance(values, list) and index < len(values) else None


def normalize(payload, symbol, start, end, *, observed_at=None, instrument_type="EQUITY"):
    if instrument_type not in ("EQUITY", "ETF"):
        raise ValueError("Unsupported daily price instrument type.")
    observed_at = observed_at or end
    try:
        chart = payload["chart"]
        if chart.get("error") or len(chart["result"]) != 1:
            raise ValueError()
        result = chart["result"][0]
        meta = result["meta"]
        if (
            meta["symbol"] != symbol
            or meta["currency"] != "USD"
            or meta["instrumentType"] != instrument_type
            or meta["exchangeTimezoneName"] != "America/New_York"
            or meta["dataGranularity"] != "1d"
        ):
            raise ValueError()
        stamps = result["timestamp"]
        q = result["indicators"]["quote"]
        if not isinstance(stamps, list) or not 1 <= len(stamps) <= 400 or len(q) != 1:
            raise ValueError()
        q = q[0]
        if any(
            not isinstance(q.get(k), list)
            for k in ("open", "high", "low", "close", "volume")
        ):
            raise ValueError()
        bars = []
        seen = set()
        omitted = 0
        missing_volume = 0
        outside = 0
        for i, stamp in enumerate(stamps):
            if isinstance(stamp, bool) or not isinstance(stamp, int) or stamp <= 0:
                raise ValueError()
            day = datetime.fromtimestamp(stamp, NY).date()
            if not start.date() <= day <= end.date() or stamp > int(observed_at.timestamp()):
                outside += 1
                continue
            if day.isoformat() in seen:
                raise ValueError("Duplicate daily session in provider data.")
            seen.add(day.isoformat())
            raw = {k: at(q[k], i) for k in ("open", "high", "low", "close")}
            if any(v is None for v in raw.values()):
                omitted += 1
                continue
            values = {k: decimal(v) for k, v in raw.items()}
            if (
                not values["low"]
                <= min(values["open"], values["close"])
                <= max(values["open"], values["close"])
                <= values["high"]
            ):
                raise ValueError(
                    "Daily high/low does not contain its opening and closing price."
                )
            volume = at(q["volume"], i)
            if volume is not None:
                volume = decimal(volume, zero=True)
                if volume != volume.to_integral_value():
                    raise ValueError("Daily volume is not a whole number.")
            else:
                missing_volume += 1
            bars.append(
                dict(
                    date=day.isoformat(),
                    **{k: str(v) for k, v in values.items()},
                    volume=str(volume) if volume is not None else None,
                    provisional=day == end.date(),
                )
            )
        bars.sort(key=lambda b: b["date"])
        if not bars:
            raise ValueError("No complete past trading session was supplied.")
        # A same-day bar is final only after a supplied, matching regular-session
        # end. Never invent a close time for holidays, early closes or missing metadata.
        regular = meta.get("currentTradingPeriod", {}).get("regular", {})
        regular_end = regular.get("end")
        regular_start = regular.get("start")
        quote_time = meta.get("regularMarketTime")
        if (
            type(regular_end) is int and type(regular_start) is int
            and 0 < regular_start < regular_end <= int(observed_at.timestamp())
            and type(quote_time) is int
            and regular_end <= quote_time <= int(observed_at.timestamp())
            and datetime.fromtimestamp(regular_start, NY).date() == end.date()
            and datetime.fromtimestamp(regular_end, NY).date() == end.date()
        ):
            for bar in bars:
                if bar["date"] == end.date().isoformat():
                    bar["provisional"] = False
        delay = meta.get("exchangeDataDelayedBy")
        delay = delay if type(delay) is int and 0 <= delay <= 1440 else None
        return dict(
            symbol=symbol,
            currency="USD",
            exchange_timezone="America/New_York",
            interval="1d",
            basis=BASIS,
            requested_start=start.date().isoformat(),
            requested_end_exclusive=(end.date() + timedelta(days=1)).isoformat(),
            requested_through=end.isoformat(),
            latest_quote=latest_quote(meta, observed_at),
            delay_minutes=delay,
            bars=bars,
            omitted_sessions=omitted,
            missing_volume_sessions=missing_volume,
            outside_window_sessions=outside,
            partial_window=bars[0]["date"]
            > (start + timedelta(days=7)).date().isoformat(),
            old_last_session=bars[-1]["date"]
            < (end - timedelta(days=7)).date().isoformat(),
        )
    except (KeyError, TypeError, IndexError, OverflowError, OSError, ValueError) as exc:
        # Provider payloads never become UI HTML or unfiltered exception detail.
        raise ValueError(
            "Daily history did not match the selected company, daily interval, dates or price checks."
        ) from None


def refresh(iid, *, fetcher=None, extended_fetcher=None):
    attempt = uuid4()
    with transaction(source=True) as conn:
        collection_lock(conn)
        now = datetime.now(timezone.utc)
        company = one(
            conn,
            "SELECT i.symbol FROM instruments i JOIN sec_companies s ON s.instrument_id=i.id WHERE i.id=%s",
            (iid,),
        )
        if (
            not company
            or not allowed(conn)
            or not configured()
        ):
            raise ValueError(
                "Daily price history is unavailable for this company/source."
            )
        conn.execute(
            "INSERT INTO price_history_state(instrument_id) VALUES(%s) ON CONFLICT DO NOTHING",
            (iid,),
        )
        state = one(
            conn,
            "SELECT * FROM price_history_state WHERE instrument_id=%s FOR UPDATE",
            (iid,),
        )
        if state["lease_until"] and state["lease_until"] > now:
            raise ValueError("A price-history refresh is already running.")
        if state["last_attempt_at"] and now - state["last_attempt_at"] < REFRESH_INTERVAL:
            raise ValueError(
                "Price refreshes are one minute apart. Saved prices remain available."
            )
        conn.execute(
            "UPDATE price_history_state SET attempt_id=%s,last_attempt_at=%s,lease_until=%s,error=NULL WHERE instrument_id=%s",
            (attempt, now, now + timedelta(minutes=2), iid),
        )
    start, end = window(now)
    try:
        payload = (fetcher or fetch)(company["symbol"], start, end)
        series = normalize(
            payload, company["symbol"], start, end,
            observed_at=datetime.now(timezone.utc),
        )
        if extended_fetcher or (fetcher is None and not regular_hours(datetime.now(timezone.utc))):
            series = with_extended_quote(series, company["symbol"], extended_fetcher)
        with transaction(source=True) as conn:
            collection_lock(conn)
            now = datetime.now(timezone.utc)
            state = one(
                conn,
                "SELECT * FROM price_history_state WHERE instrument_id=%s FOR UPDATE",
                (iid,),
            )
            if (
                state["attempt_id"] != attempt
                or not state["lease_until"]
                or state["lease_until"] <= now
                or not allowed(conn)
            ):
                raise ValueError("Price refresh expired or source access changed.")
            if state["current_id"]:
                previous = one(
                    conn,
                    "SELECT series FROM price_history_snapshots WHERE id=%s",
                    (state["current_id"],),
                )["series"]["bars"]
                dates = {b["date"] for b in series["bars"]}
                if previous[-1]["date"] > series["bars"][-1]["date"] or any(
                    b["date"] >= series["requested_start"] and b["date"] not in dates
                    for b in previous
                ):
                    raise ValueError(
                        "The response lost retained sessions; earlier history is preserved."
                    )
            sid = uuid4()
            raw = json.dumps(
                payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            )
            conn.execute(
                "INSERT INTO price_history_snapshots VALUES(%s,%s,%s,%s,%s,%s,%s)",
                (
                    sid,
                    iid,
                    company["symbol"],
                    Jsonb(payload),
                    Jsonb(series),
                    hashlib.sha256(raw.encode()).hexdigest(),
                    now,
                ),
            )
            conn.execute(
                "UPDATE price_history_state SET current_id=%s,lease_until=NULL,completed_at=%s,error=NULL WHERE instrument_id=%s",
                (sid, now, iid),
            )
        return dict(id=str(sid), sessions=len(series["bars"]))
    except Exception:
        with transaction(source=True) as conn:
            collection_lock(conn)
            conn.execute(
                "UPDATE price_history_state SET lease_until=NULL,error='Daily-history refresh failed; earlier prices are retained. No automatic retry.' WHERE instrument_id=%s AND attempt_id=%s",
                (iid, attempt),
            )
        raise ValueError(
            "Daily-history refresh failed; earlier prices are retained. No automatic retry."
        ) from None


def regular_hours(now):
    """Weekday 09:30-16:00 New York: the daily chart's own quote is current,
    so no extra extended-hours request is made. Holidays still ask; the
    provider's trading periods then decide the label."""
    local = now.astimezone(NY)
    minutes = local.hour * 60 + local.minute
    return local.weekday() < 5 and 9 * 60 + 30 <= minutes < 16 * 60


def with_extended_quote(series, symbol, fetcher=None):
    """Prefer a newer pre-market/after-hours price for display. Optional: a
    failed or unlabelled extended read keeps the daily chart's quote."""
    if fetcher is None and not configured():
        return series
    try:
        raw = (fetcher or fetch_extended)(symbol)
        quote = extended_quote(raw, symbol, datetime.now(timezone.utc))
    except Exception:
        return series
    if not quote:
        return series
    current = series.get("latest_quote")
    if current and current["quoted_at"] >= quote["quoted_at"]:
        return series
    text = json.dumps(raw, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    quote["raw_sha256"] = hashlib.sha256(text.encode()).hexdigest()
    return {**series, "latest_quote": quote, "regular_quote": current}


def present(iid):
    from thesis.service import Missing

    with transaction(consistent=True) as conn:
        company = one(
            conn,
            "SELECT i.symbol FROM instruments i JOIN sec_companies s ON s.instrument_id=i.id WHERE i.id=%s",
            (iid,),
        )
        if not company:
            raise Missing("No daily-history workspace exists for this company.")
        permitted = allowed(conn)
        state = one(
            conn, "SELECT * FROM price_history_state WHERE instrument_id=%s", (iid,)
        )
        snapshot = (
            one(
                conn,
                "SELECT id,series,retrieved_at FROM price_history_snapshots WHERE id=%s",
                (state["current_id"],),
            )
            if permitted and state and state["current_id"]
            else None
        )
        now = datetime.now(timezone.utc)
        error = state["error"] if state else None
        if state and state["lease_until"] and state["lease_until"] <= now:
            error = "The last daily-history refresh did not finish. Saved prices are retained."
        return dict(
            symbol=company["symbol"],
            provider="Yahoo Finance",
            source_url=f'https://finance.yahoo.com/quote/{company["symbol"]}/history/',
            available=permitted,
            configured=configured(),
            snapshot=snapshot,
            error=error,
            refreshing=bool(
                state and state["lease_until"] and state["lease_until"] > now
            ),
            last_attempt_at=state["last_attempt_at"] if state else None,
            next_refresh_at=(
                state["last_attempt_at"] + REFRESH_INTERVAL
                if state and state["last_attempt_at"]
                else None
            ),
            check_stale=bool(
                snapshot and now - snapshot["retrieved_at"] > timedelta(hours=24)
            ),
            refresh_interval_seconds=int(REFRESH_INTERVAL.total_seconds()),
        )
