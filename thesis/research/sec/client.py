"""Bounded SEC HTTP access. No retries, arbitrary URLs or private model inputs."""

import json
import re
import time
from datetime import datetime, timezone, timedelta
import httpx
from thesis.db import transaction, one
from thesis.providers.settings import settings

MAX_BYTES = 20 * 1024 * 1024


class SourceFailure(ValueError):
    def __init__(self, message, denied=False):
        super().__init__(message)
        self.denied = denied


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
            raise SourceFailure("SEC requests are busy. Try again later.")
        conn.execute(
            "UPDATE source_request_clock SET next_at=%s WHERE singleton",
            (slot + timedelta(seconds=1),),
        )
    if delay > 0:
        time.sleep(delay)


def fetch_bundle(cik, *, transport=None):
    user_agent = identity()
    result = {}
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
                        )
                    raw = bytearray()
                    for chunk in response.iter_bytes():
                        raw.extend(chunk)
                        if len(raw) > MAX_BYTES:
                            raise SourceFailure(
                                "SEC response exceeded the supported size."
                            )
                    result[key] = json.loads(raw, parse_float=str)
    except (httpx.HTTPError, json.JSONDecodeError, UnicodeDecodeError):
        raise SourceFailure(
            "SEC could not be read. No new evidence was committed."
        ) from None
    return result
