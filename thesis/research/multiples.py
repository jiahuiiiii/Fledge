"""Optional Finnhub reference multiples. Never auto-selects a valuation assumption."""

from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation
from uuid import uuid4
from psycopg.types.json import Jsonb
from thesis.db import transaction, one, rows
from .market import fetch
from .sec.service import COMPANIES, collection_lock


def normalized(payload, symbol):
    if (
        not isinstance(payload, dict)
        or payload.get("symbol") != symbol
        or not isinstance(payload.get("metric"), dict)
    ):
        raise ValueError("Reference response does not match the selected company.")
    values = {}
    for name, field in (("earnings", "peTTM"), ("sales", "psTTM")):
        raw = payload["metric"].get(field)
        value = None
        try:
            number = Decimal(str(raw))
            if (
                isinstance(raw, bool)
                or not number.is_finite()
                or not 0 < number <= 10000
            ):
                raise ValueError()
            value = str(number)
        except (ValueError, InvalidOperation):
            pass
        values[name] = dict(
            value=value,
            field=field,
            reason=None if value else "No positive usable TTM multiple supplied.",
        )
    return values


def allowed(conn):
    return bool(
        one(
            conn,
            "SELECT id FROM sources WHERE id='finnhub-financials' AND entitlement='finnhub-pitch'",
        )
    )


def refresh(iid, fetcher=None):
    now = datetime.now(timezone.utc)
    attempt = uuid4()
    with transaction(source=True) as conn:
        collection_lock(conn)
        company = one(conn, "SELECT i.symbol FROM instruments i JOIN sec_companies s ON s.instrument_id=i.id WHERE i.id=%s", (iid,))
        if not company or not allowed(conn):
            raise ValueError(
                "Reference multiples are unavailable for this company/source."
            )
        conn.execute(
            "INSERT INTO multiple_refresh_state(instrument_id) VALUES(%s) ON CONFLICT DO NOTHING",
            (iid,),
        )
        current = one(
            conn,
            "SELECT * FROM multiple_refresh_state WHERE instrument_id=%s FOR UPDATE",
            (iid,),
        )
        if current["lease_until"] and current["lease_until"] > now:
            raise ValueError("A reference check is already running.")
        if current["last_attempt_at"] and now - current["last_attempt_at"] < timedelta(
            hours=1
        ):
            raise ValueError(
                "Reference checks are one hour apart. Saved values remain available."
            )
        conn.execute(
            "UPDATE multiple_refresh_state SET attempt_id=%s,last_attempt_at=%s,lease_until=%s,error=NULL WHERE instrument_id=%s",
            (attempt, now, now + timedelta(minutes=2), iid),
        )
    try:
        payload = (fetcher or fetch)(
            "stock/metric", {"symbol": company["symbol"], "metric": "all"}
        )
        metrics = normalized(payload, company["symbol"])
        with transaction(source=True) as conn:
            collection_lock(conn)
            now = datetime.now(timezone.utc)
            current = one(
                conn,
                "SELECT * FROM multiple_refresh_state WHERE instrument_id=%s FOR UPDATE",
                (iid,),
            )
            if (
                current["attempt_id"] != attempt
                or not current["lease_until"]
                or current["lease_until"] <= now
                or not allowed(conn)
            ):
                raise ValueError("Reference attempt expired or source access changed.")
            rid = uuid4()
            conn.execute(
                "INSERT INTO multiple_references VALUES(%s,%s,%s,%s,%s,%s)",
                (rid, iid, company["symbol"], Jsonb(metrics), Jsonb(payload), now),
            )
            conn.execute(
                "UPDATE multiple_refresh_state SET lease_until=NULL,completed_at=%s WHERE instrument_id=%s",
                (now, iid),
            )
        return dict(id=str(rid))
    except Exception:
        with transaction(source=True) as conn:
            collection_lock(conn)
            conn.execute(
                "UPDATE multiple_refresh_state SET lease_until=NULL,error='Reference check failed; earlier values are retained.' WHERE instrument_id=%s AND attempt_id=%s",
                (iid, attempt),
            )
        raise ValueError(
            "Reference check failed; earlier values are retained. No automatic retry."
        ) from None


def catalogue(conn):
    permitted = allowed(conn)
    result = []
    for company in rows(
        conn,
        "SELECT i.id,i.symbol,i.name FROM instruments i JOIN sec_companies c ON c.instrument_id=i.id ORDER BY i.symbol",
    ):
        reference = (
            one(
                conn,
                "SELECT id,symbol,metrics,retrieved_at FROM multiple_references WHERE instrument_id=%s ORDER BY retrieved_at DESC,id DESC LIMIT 1",
                (company["id"],),
            )
            if permitted
            else None
        )
        state = one(
            conn,
            "SELECT last_attempt_at,lease_until,completed_at,error FROM multiple_refresh_state WHERE instrument_id=%s",
            (company["id"],),
        )
        if (
            state
            and state["lease_until"]
            and state["lease_until"] <= datetime.now(timezone.utc)
        ):
            state["error"] = (
                "The last reference check did not finish; earlier values are retained."
            )
        result.append(
            dict(**company, reference=reference, refresh=state, available=permitted)
        )
    return result
