"""Bounded SEC HTTP access. No retries, arbitrary URLs or private model inputs."""

import json
import re
import time
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
import httpx
from thesis.db import transaction, one
from thesis.providers.settings import settings

MAX_BYTES = 20 * 1024 * 1024


class SourceFailure(ValueError):
    def __init__(self, message, denied=False, *, code=None, stage=None, status=None):
        super().__init__(message)
        self.denied = denied
        self.code = code
        self.stage = stage
        self.status = status


def failure_message(error):
    """Explain known failures without exposing exception bodies or contact data."""
    from .normalize import UnsupportedFiling
    if isinstance(error, UnsupportedFiling):
        return 'No supported 10-K, 10-Q or 20-F report was found in the SEC filing list. Other filing formats are not supported.'
    if not isinstance(error, SourceFailure):
        return "SEC refresh failed; no new evidence committed."
    if error.denied:
        return "SEC access denied or rate-limited."
    resource = {
        "submissions": "the filing list",
        "companyfacts": "the reported financial figures",
    }.get(error.stage, "filing data")
    reasons = {
        "timeout": f"SEC took too long to return {resource}.",
        "connection": f"The connection to SEC failed while loading {resource}.",
        "invalid_response": f"SEC returned unreadable data for {resource}.",
        "size_limit": f"SEC returned more data than the supported size limit for {resource}.",
        "busy": "Another filing request is using the SEC connection.",
        "http_status": f"SEC could not supply {resource}.",
    }
    reason = reasons.get(error.code)
    if reason is None:
        return "SEC refresh failed; no new evidence committed."
    if error.code == "http_status" and type(error.status) is int and 100 <= error.status <= 599:
        reason += f" Response code: {error.status}."
    return reason + " No new filing data was saved. Use Update data to try again."


def identity():
    value = settings().get("SEC_USER_AGENT", "").strip()
    if not (
        8 < len(value) < 240 and re.search(r"[^\s@]+@[^\s@]+\.[^\s@]+", value)
    ) or any(ord(c) < 32 or ord(c) > 126 for c in value):
        raise ValueError(
            "Add SEC_USER_AGENT with your project name and contact email to the private .env file."
        )
    if "example.com" in value or "your-email" in value:
        raise ValueError(
            "Replace the SEC_USER_AGENT placeholder with your contact email."
        )
    return value


def reserve_request():
    # Shared by all local processes, at most one request/second (below SEC's 10/s).
    with transaction(source=True) as conn:
        now = datetime.now(timezone.utc)
        row = one(
            conn, "SELECT next_at FROM source_request_clock WHERE singleton FOR UPDATE"
        )
        slot = max(now, row["next_at"])
        delay = (slot - now).total_seconds()
        if delay > 2:
            raise SourceFailure("SEC requests are busy. Try again later.", code="busy")
        conn.execute(
            "UPDATE source_request_clock SET next_at=%s WHERE singleton",
            (slot + timedelta(seconds=1),),
        )
    if delay > 0:
        time.sleep(delay)


def fetch_bundle(cik, *, transport=None):
    user_agent = identity()
    result = {}
    key = None
    try:
        with httpx.Client(
            headers={"User-Agent": user_agent, "Accept": "application/json"},
            timeout=15,
            follow_redirects=False,
            transport=transport,
        ) as client:
            for key, path in (
                ("submissions", f"/submissions/CIK{cik:010d}.json"),
                ("companyfacts", f"/api/xbrl/companyfacts/CIK{cik:010d}.json"),
            ):
                reserve_request()
                with client.stream("GET", "https://data.sec.gov" + path) as response:
                    if response.status_code != 200:
                        raise SourceFailure(
                            (
                                "SEC access was denied or rate-limited."
                                if response.status_code in (403, 429)
                                else "SEC did not return a usable response."
                            ),
                            response.status_code in (403, 429),
                            code="http_status", stage=key, status=response.status_code,
                        )
                    raw = bytearray()
                    for chunk in response.iter_bytes():
                        raw.extend(chunk)
                        if len(raw) > MAX_BYTES:
                            raise SourceFailure(
                                "SEC response exceeded the supported size.",
                                code="size_limit", stage=key,
                            )
                    result[key] = json.loads(raw, parse_float=str)
                    if not isinstance(result[key], dict):
                        raise SourceFailure("SEC response was not a data object.", code="invalid_response", stage=key)
    except httpx.TimeoutException:
        raise SourceFailure("SEC request timed out.", code="timeout", stage=key) from None
    except httpx.HTTPError:
        raise SourceFailure(
            "SEC could not be read. No new evidence was committed.", code="connection", stage=key,
        ) from None
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise SourceFailure("SEC returned unreadable data.", code="invalid_response", stage=key) from None
    return result


def fetch_document(url, *, transport=None):
    """Original HTML on the canonical SEC archive; never follow a redirect."""
    if not re.fullmatch(r'https://www\.sec\.gov/Archives/edgar/data/[1-9]\d*/\d{18}/[A-Za-z0-9_.-]+\.html?',url,re.I) or '..' in url:
        raise SourceFailure('Unsupported original-filing URL.')
    user_agent=identity()
    # Archive access is its own capability. A denial must survive restarts and
    # cannot disable or clear the structured-data endpoint's existing records.
    with transaction(source=True) as conn:
        conn.execute("INSERT INTO provider_clocks(provider) VALUES('sec-disclosures') ON CONFLICT DO NOTHING")
        clock=one(conn,"SELECT * FROM provider_clocks WHERE provider='sec-disclosures' FOR UPDATE")
        now=datetime.now(timezone.utc)
        if clock['denied']:raise SourceFailure('SEC original-document access is denied; a supported connection is required.',True)
        if clock['blocked_until'] and clock['blocked_until']>now:
            raise SourceFailure('SEC original-document access is cooling down; saved filings remain available.')
    reserve_request()
    with transaction(source=True) as conn:
        clock=one(conn,"SELECT * FROM provider_clocks WHERE provider='sec-disclosures' FOR UPDATE")
        if clock['denied'] or (clock['blocked_until'] and clock['blocked_until']>datetime.now(timezone.utc)):
            raise SourceFailure('SEC original-document access changed while waiting; no request was sent.',bool(clock['denied']))
        conn.execute("UPDATE provider_clocks SET requests=CASE WHEN usage_date=CURRENT_DATE THEN requests+1 ELSE 1 END,usage_date=CURRENT_DATE WHERE provider='sec-disclosures'")
    try:
        with httpx.Client(headers={'User-Agent':user_agent,'Accept':'text/html'},timeout=20,follow_redirects=False,transport=transport) as client:
            with client.stream('GET',url) as response:
                if response.status_code in (401,403,429):
                    seconds=900
                    retry=response.headers.get('Retry-After','0')
                    try:seconds=max(seconds,int(retry) if retry.isdigit() else (parsedate_to_datetime(retry)-datetime.now(timezone.utc)).total_seconds())
                    except (ValueError,TypeError,OverflowError):pass
                    with transaction(source=True) as conn:
                        conn.execute("UPDATE provider_clocks SET denied=denied OR %s,blocked_until=greatest(blocked_until,%s) WHERE provider='sec-disclosures'",
                                     (response.status_code in (401,403),datetime.now(timezone.utc)+timedelta(seconds=seconds)))
                    raise SourceFailure(f'SEC original documents returned HTTP {response.status_code}; no retry was made.',response.status_code in (401,403))
                if response.status_code!=200:raise SourceFailure('SEC did not return the original document.')
                body=bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body)>MAX_BYTES:raise SourceFailure('Original filing exceeded the supported size.')
                return bytes(body)
    except httpx.HTTPError:
        raise SourceFailure('SEC original document could not be read; saved filings remain available.') from None
