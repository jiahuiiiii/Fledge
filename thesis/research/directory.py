"""Search a cached public SEC listing directory, never a model-generated identity."""
import json
import re
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import httpx
from psycopg.types.json import Jsonb
from thesis.db import transaction, one, rows
from .catalogue import COMPANIES
from .sec import client

URL = "https://www.sec.gov/files/company_tickers_exchange.json"
EXCHANGES = {"Nasdaq", "NYSE", "NYSE American", "Cboe BZX"}


def valid_symbol(symbol):
    # Class/preferred/warrant suffixes need provider-specific mappings first.
    return isinstance(symbol, str) and bool(re.fullmatch(r"[A-Z]{1,5}", symbol))


def normalize(payload):
    if not isinstance(payload, dict) or payload.get("fields") != ["cik", "name", "ticker", "exchange"]:
        raise ValueError("The SEC listing directory has an unexpected format.")
    data = payload.get("data")
    if not isinstance(data, list) or not 1 <= len(data) <= 30000:
        raise ValueError("The SEC listing directory is empty or too large.")
    result, seen = [], set()
    for row in data:
        if not isinstance(row, list) or len(row) != 4:
            raise ValueError("The SEC listing directory contains an invalid row.")
        cik, name, symbol, exchange = row
        if not isinstance(cik, int) or isinstance(cik, bool) or not 0 < cik < 10**10:
            raise ValueError("The directory contains an invalid company identity.")
        if not isinstance(name, str) or not 1 <= len(name) <= 300 or not isinstance(symbol, str) or not re.fullmatch(r"[A-Z0-9.-]{1,15}", symbol):
            raise ValueError("The directory contains an invalid listing.")
        if exchange not in EXCHANGES:
            continue
        if symbol in seen:
            raise ValueError("The directory contains conflicting ticker identities.")
        seen.add(symbol)
        result.append(dict(symbol=symbol, name=name, cik=cik, exchange=exchange))
    if not result:
        raise ValueError("No supported US exchange listings were returned.")
    return result


def fetch():
    identity = client.identity()
    client.reserve_request()
    try:
        with httpx.Client(headers={"User-Agent": identity, "Accept": "application/json"}, timeout=20, follow_redirects=False) as transport:
            with transport.stream("GET", URL) as response:
                if response.status_code != 200:
                    raise ValueError("The SEC directory is unavailable or rate-limited. Saved listings remain searchable.")
                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > 4 * 1024 * 1024:
                        raise ValueError("The SEC directory exceeded the supported size.")
                return json.loads(body)
    except (httpx.HTTPError, UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("The SEC directory could not be read. Saved listings remain searchable.") from None


def refresh(fetcher=None):
    now, attempt = datetime.now(timezone.utc), uuid4()
    with transaction(source=True) as conn:
        state = one(conn, "SELECT * FROM company_directory WHERE singleton FOR UPDATE")
        if state["lease_until"] and state["lease_until"] > now:
            raise ValueError("The company directory is already updating.")
        if state["attempted_at"] and now - state["attempted_at"] < timedelta(minutes=5):
            raise ValueError("Please wait five minutes before updating listings again.")
        conn.execute("UPDATE company_directory SET attempted_at=%s,attempt_id=%s,lease_until=%s,error=NULL WHERE singleton", (now, attempt, now + timedelta(minutes=1)))
    try:
        listings = normalize((fetcher or fetch)())
        with transaction(source=True) as conn:
            state = one(conn, "SELECT * FROM company_directory WHERE singleton FOR UPDATE")
            if state["attempt_id"] != attempt or state["lease_until"] <= datetime.now(timezone.utc):
                raise ValueError("This directory update expired. Previous listings are retained.")
            conn.execute("UPDATE company_directory SET listings=%s,retrieved_at=%s,lease_until=NULL,error=NULL WHERE singleton", (Jsonb(listings), datetime.now(timezone.utc)))
        return search("")
    except Exception:
        with transaction(source=True) as conn:
            conn.execute("UPDATE company_directory SET lease_until=NULL,error='Listing update failed. Previous listings are retained.' WHERE singleton AND attempt_id=%s", (attempt,))
        raise ValueError("Listing update failed. Previous listings are retained; try again later.") from None


def search(query):
    query = query.strip().upper()
    if len(query) > 80:
        raise ValueError("Search by a ticker or a shorter company name.")
    with transaction() as conn:
        state = one(conn, "SELECT * FROM company_directory WHERE singleton")
        existing = rows(conn, "SELECT i.id,i.symbol,s.cik FROM instruments i JOIN sec_companies s ON s.instrument_id=i.id")
    listing = state["listings"] or [dict(symbol=s, name=v[1], cik=v[0], exchange="Nasdaq") for s, v in COMPANIES.items()]
    matching = [r for r in listing if not query or query in r["symbol"] or all(word in r["name"].upper() for word in query.split())]
    matching.sort(key=lambda r: (r["symbol"] != query, not r["symbol"].startswith(query), r["symbol"] not in COMPANIES if not query else False, r["symbol"]))
    registered = {r["cik"]: r for r in existing}
    result = []
    for item in matching[:20]:
        previous = registered.get(item["cik"])
        blocked = None
        if not valid_symbol(item["symbol"]):
            blocked = "This share-class symbol is not supported yet."
        if previous and previous["symbol"] != item["symbol"]:
            blocked = f"This issuer is already researched as {previous['symbol']}. Separate share-class workspaces are not supported yet."
        result.append(dict(item, available=not blocked, limitation=blocked, instrument_id=str(previous["id"]) if previous and previous["symbol"] == item["symbol"] else None))
    return dict(companies=result, total=len(matching), retrieved_at=state["retrieved_at"], stale=bool(state["retrieved_at"] and datetime.now(timezone.utc)-state["retrieved_at"] > timedelta(days=7)), error=state["error"], source_url=URL)


def resolve(symbol):
    if not valid_symbol(symbol):
        raise ValueError("Choose a supported US ticker from search results.")
    with transaction() as conn:
        state = one(conn, "SELECT * FROM company_directory WHERE singleton")
    # Existing presets remain available if the directory is temporarily offline.
    if symbol in COMPANIES:
        cik, name, sector = COMPANIES[symbol]
        return cik, name, sector
    if not state["retrieved_at"] or datetime.now(timezone.utc)-state["retrieved_at"] > timedelta(days=7):
        raise ValueError("Update the company directory before adding a new listing.")
    found = next((r for r in state["listings"] if r["symbol"] == symbol), None)
    if not found:
        raise ValueError("This ticker was not found in the SEC US listing directory.")
    return found["cik"], found["name"], "Not yet classified"
