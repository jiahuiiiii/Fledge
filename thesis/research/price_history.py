"""Daily Yahoo chart acquisition adapted from Deus pipeline/price_feed.py.

Whole-window snapshots avoid mixing prices across split-adjustment vintages.
This data is display context only and never enters evidence/monitoring manifests.
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
    end = now.astimezone(NY).replace(hour=0, minute=0, second=0, microsecond=0)
    return end - timedelta(days=366), end


def fetch(symbol, start, end, *, transport=None):
    from .directory import valid_symbol
    if not valid_symbol(symbol) or not configured():
        raise ValueError("Daily price history is not connected for this company.")
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
                params=dict(
                    period1=int(start.timestamp()),
                    period2=int(end.timestamp()),
                    interval="1d",
                    events="div,splits",
                    includePrePost="false",
                ),
            ) as response:
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


def normalize(payload, symbol, start, end):
    try:
        chart = payload["chart"]
        if chart.get("error") or len(chart["result"]) != 1:
            raise ValueError()
        result = chart["result"][0]
        meta = result["meta"]
        if (
            meta["symbol"] != symbol
            or meta["currency"] != "USD"
            or meta["instrumentType"] != "EQUITY"
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
            if not start.date() <= day < end.date():
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
                )
            )
        bars.sort(key=lambda b: b["date"])
        if not bars:
            raise ValueError("No complete past trading session was supplied.")
        return dict(
            symbol=symbol,
            currency="USD",
            exchange_timezone="America/New_York",
            interval="1d",
            basis=BASIS,
            requested_start=start.date().isoformat(),
            requested_end_exclusive=end.date().isoformat(),
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


def refresh(iid, *, fetcher=None):
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
        if state["last_attempt_at"] and now - state["last_attempt_at"] < timedelta(
            hours=1
        ):
            raise ValueError(
                "Daily-history refreshes are one hour apart. Saved prices remain available."
            )
        conn.execute(
            "UPDATE price_history_state SET attempt_id=%s,last_attempt_at=%s,lease_until=%s,error=NULL WHERE instrument_id=%s",
            (attempt, now, now + timedelta(minutes=2), iid),
        )
    start, end = window(now)
    try:
        payload = (fetcher or fetch)(company["symbol"], start, end)
        series = normalize(payload, company["symbol"], start, end)
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
                state["last_attempt_at"] + timedelta(hours=1)
                if state and state["last_attempt_at"]
                else None
            ),
            check_stale=bool(
                snapshot and now - snapshot["retrieved_at"] > timedelta(hours=24)
            ),
        )
