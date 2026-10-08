"""Bounded Finnhub acquisition, adapted from Deus's Finnhub article mapping.

Quotes are context, outside research monitoring. News uses immutable shared evidence.
"""

import hashlib
import json
import math
import time
import unicodedata
from datetime import datetime, timezone, timedelta
from uuid import uuid4, uuid5, NAMESPACE_URL
from urllib.parse import urlsplit, urlunsplit
import httpx
from psycopg.types.json import Jsonb
from thesis.db import transaction, one, rows
from thesis.providers.settings import settings
from .acquisition import Batch, Document, Check, ingest_batch
from .sec.service import collection_lock


def key():
    values = settings()
    value = values.get("FINNHUB_API_KEY", "")
    if values.get("THESIS_LIVE_DATA_ENABLED") != "true" or not value:
        raise ValueError("Market data is not connected in this local workspace.")
    return value


def configured():
    try:
        key()
        return True
    except ValueError:
        return False


def reserve_request():
    with transaction(source=True) as conn:
        row = one(
            conn, "SELECT next_at FROM market_request_clock WHERE singleton FOR UPDATE"
        )
        now = datetime.now(timezone.utc)
        slot = max(now, row["next_at"])
        delay = (slot - now).total_seconds()
        if delay > 6:
            raise ValueError("Market requests are busy. Try again later.")
        conn.execute(
            "UPDATE market_request_clock SET next_at=%s WHERE singleton",
            (slot + timedelta(seconds=2),),
        )
    if delay > 0:
        time.sleep(delay)


def fetch(endpoint, params, *, transport=None):
    if endpoint not in ("quote", "company-news", "stock/metric"):
        raise ValueError("Unsupported market endpoint")
    token = key()
    reserve_request()
    try:
        with httpx.Client(
            headers={"X-Finnhub-Token": token},
            timeout=20,
            follow_redirects=False,
            transport=transport,
        ) as client:
            with client.stream(
                "GET", "https://finnhub.io/api/v1/" + endpoint, params=params
            ) as response:
                if response.status_code != 200:
                    raise ValueError(
                        "Finnhub access was denied or rate-limited."
                        if response.status_code in (403, 429)
                        else "Finnhub did not return a usable response."
                    )
                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > 4 * 1024 * 1024:
                        raise ValueError(
                            "Finnhub response exceeded the supported size."
                        )
                return (
                    json.loads(body, parse_float=str)
                    if endpoint == "stock/metric"
                    else json.loads(body)
                )
    except (httpx.HTTPError, json.JSONDecodeError, UnicodeDecodeError):
        raise ValueError(
            "Finnhub could not be read. Previously retrieved data is preserved."
        ) from None


def number(value):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        return None
    return value


def normalize_quote(raw, now):
    if not isinstance(raw, dict):
        raise ValueError("Finnhub returned no usable quote.")
    price, stamp = number(raw.get("c")), number(raw.get("t"))
    if not price or price <= 0 or not stamp or stamp <= 0:
        raise ValueError("Finnhub returned no usable quote.")
    try:
        quoted_at = datetime.fromtimestamp(stamp, timezone.utc)
    except (ValueError, OverflowError, OSError):
        raise ValueError("Quote timestamp is invalid.") from None
    if quoted_at > now + timedelta(minutes=1):
        raise ValueError("Quote timestamp is ahead of the current time.")
    previous = number(raw.get("pc"))
    previous = previous if previous and previous > 0 else None
    low, high = number(raw.get("l")), number(raw.get("h"))
    valid_range = low is not None and high is not None and 0 < low <= price <= high
    opening = number(raw.get("o"))
    return dict(
        price=price,
        previous_close=previous,
        change=price - previous if previous else None,
        change_percent=(price / previous - 1) * 100 if previous else None,
        low=low if valid_range else None,
        high=high if valid_range else None,
        open=opening if opening and opening > 0 else None,
        quoted_at=quoted_at.isoformat(),
        currency="USD",
    )


def provider_text(value, maximum, *, allow_empty=False):
    """Reject one malformed item without changing the text used as evidence."""
    if not isinstance(value, str) or len(value) > maximum:
        raise ValueError("Malformed article text")
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeEncodeError:
        raise ValueError("Malformed article text") from None
    if any(
        unicodedata.category(char) == "Cc" and char not in "\t\n\r" for char in value
    ):
        raise ValueError("Malformed article text")
    value = value.strip()
    if not allow_empty and not value:
        raise ValueError("Malformed article text")
    return value


def safe_url(value):
    provider_text(value, 2048)
    if (
        not isinstance(value, str)
        or len(value) > 2048
        or any(ord(c) < 33 for c in value)
    ):
        raise ValueError("Invalid article link")
    parsed = urlsplit(value)
    if (
        parsed.scheme not in ("http", "https")
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        raise ValueError("Invalid article link")
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ""))


def normalize_news(raw, symbol, now):
    if not isinstance(raw, list):
        raise ValueError("Finnhub returned no usable news response.")
    articles, rejected = {}, 0
    for item in raw:
        try:
            if not isinstance(item, dict):
                raise ValueError("Malformed item")
            related = item.get("related", "")
            if not isinstance(related, str) or (
                related and symbol not in {s.strip() for s in related.split(",")}
            ):
                raise ValueError("Another company")
            url = safe_url(item.get("url"))
            title = provider_text(item.get("headline"), 600)
            summary = provider_text(item.get("summary", ""), 6000, allow_empty=True)
            publisher = provider_text(item.get("source"), 180)
            provider_id = provider_text(str(item.get("id", "")), 100, allow_empty=True)
            stamp = number(item.get("datetime"))
            if not stamp or stamp <= 0:
                raise ValueError("Missing publication time")
            published = datetime.fromtimestamp(stamp, timezone.utc)
            if published > now or published < now - timedelta(days=8):
                raise ValueError("Outside requested publication window")
            article = dict(
                url=url,
                headline=title.strip(),
                body=summary.strip(),
                publisher=publisher.strip(),
                published_at=published,
                provider_id=provider_id,
            )
            # Same link is one item; retain a deterministic version if provider duplicates differ.
            if url not in articles or (published, title, summary) > (
                articles[url]["published_at"],
                articles[url]["headline"],
                articles[url]["body"],
            ):
                articles[url] = article
        except (ValueError, OverflowError, OSError, TypeError):
            rejected += 1
    if raw and not articles:
        raise ValueError(
            "No company news passed the source checks; previous news is preserved."
        )
    return (
        sorted(
            articles.values(), key=lambda a: (a["published_at"], a["url"]), reverse=True
        )[:25],
        rejected,
    )


def commit_news(conn, iid, articles, rejected, now, error=None, *, source_id="finnhub-news", source_name="Finnhub company news", entitlement="finnhub-pitch"):
    if entitlement not in ("finnhub-pitch", "public-news"):
        raise ValueError("Unsupported news access class")
    conn.execute(
        "INSERT INTO sources VALUES(%s,%s,%s) ON CONFLICT DO NOTHING",
        (source_id,source_name,entitlement)
    )
    state = one(
        conn, "SELECT * FROM instrument_state WHERE instrument_id=%s FOR UPDATE", (iid,)
    )
    conn.execute(
        "INSERT INTO instrument_sources VALUES(%s,%s) ON CONFLICT DO NOTHING",
        (iid,source_id),
    )
    documents, metadata = [], []
    for article in articles:
        did = uuid5(NAMESPACE_URL, f"thesis:{'finnhub' if source_id == 'finnhub-news' else source_id}:{iid}:{article['url']}")
        latest = one(
            conn,
            "SELECT v.*,m.publisher FROM document_versions v JOIN market_articles m ON m.document_version_id=v.id WHERE v.document_id=%s ORDER BY v.available_at DESC,v.id DESC LIMIT 1",
            (did,),
        )
        if latest and all(
            latest[k] == article[k]
            for k in ("headline", "body", "published_at", "publisher")
        ):
            continue
        signature = hashlib.sha256(
            json.dumps(article, sort_keys=True, default=str).encode()
        ).hexdigest()
        vid = uuid5(did, signature + (str(latest["id"]) if latest else ""))
        documents.append(
            Document(
                id=did,
                version_id=vid,
                source_id=source_id,
                url=article["url"],
                headline=article["headline"],
                body=article["body"],
                published_at=article["published_at"],
                available_at=now,
                supersedes_id=latest["id"] if latest else None,
                story_key=str(did),
                origin_key=article["publisher"],
            )
        )
        metadata.append((vid, article["publisher"], article["provider_id"]))
    ingest_batch(
        conn,
        Batch(
            instrument_id=iid,
            cutoff=now,
            period=state["period"],
            period_type=state["period_type"],
            sequence=state["sequence"] + 1,
            label=state["label"],
            documents=documents,
            checks=[
                Check(
                    id=uuid4(),
                    source_id=source_id,
                    checked_at=now,
                    outcome="failed" if error else "success",
                    covered_through=None if error else now,
                    error=error,
                )
            ],
        ),
    )
    for record in metadata:
        conn.execute("INSERT INTO market_articles VALUES(%s,%s,%s)", record)


def refresh(iid, *, transport=None):
    key()
    attempt = uuid4()
    with transaction(source=True) as conn:
        collection_lock(conn)
        company = one(
            conn,
            "SELECT i.* FROM instruments i JOIN sec_companies c ON c.instrument_id=i.id WHERE i.id=%s",
            (iid,),
        )
        if not company:
            raise ValueError("Choose a supported real company for market data.")
        now = datetime.now(timezone.utc)
        conn.execute(
            "INSERT INTO market_refresh_state(instrument_id) VALUES(%s) ON CONFLICT DO NOTHING",
            (iid,),
        )
        state = one(
            conn,
            "SELECT * FROM market_refresh_state WHERE instrument_id=%s FOR UPDATE",
            (iid,),
        )
        if state["last_attempt_at"] and now - state["last_attempt_at"] < timedelta(
            minutes=5
        ):
            from thesis.service import Conflict

            raise Conflict(
                "Market refreshes are five minutes apart. Previously retrieved data remains available."
            )
        conn.execute(
            "UPDATE market_refresh_state SET attempt_id=%s,last_attempt_at=%s,lease_until=%s WHERE instrument_id=%s",
            (attempt, now, now + timedelta(minutes=2), iid),
        )
    quote, articles, rejected, errors = None, [], 0, {}
    for endpoint in ("quote", "company-news"):
        try:
            params = dict(symbol=company["symbol"])
            if endpoint == "company-news":
                params.update(
                    {
                        "from": str((now - timedelta(days=7)).date()),
                        "to": str(now.date()),
                    }
                )
            raw = fetch(endpoint, params, transport=transport)
            if endpoint == "quote":
                quote = normalize_quote(raw, datetime.now(timezone.utc))
            else:
                articles, rejected = normalize_news(
                    raw, company["symbol"], datetime.now(timezone.utc)
                )
        except ValueError as exc:
            errors[endpoint] = str(exc)
    with transaction(source=True) as conn:
        collection_lock(conn)
        state = one(
            conn,
            "SELECT * FROM market_refresh_state WHERE instrument_id=%s FOR UPDATE",
            (iid,),
        )
        completed = datetime.now(timezone.utc)
        if (
            state["attempt_id"] != attempt
            or not state["lease_until"]
            or state["lease_until"] < completed
        ):
            raise ValueError("A newer refresh replaced this request.")
        previous = one(
            conn,
            "SELECT quote FROM market_quotes WHERE instrument_id=%s ORDER BY retrieved_at DESC LIMIT 1",
            (iid,),
        )
        if quote and previous and quote["quoted_at"] < previous["quote"]["quoted_at"]:
            errors["quote"] = (
                "Finnhub returned an older quote. The newer stored quote is preserved."
            )
            quote = None
        if quote:
            conn.execute(
                "INSERT INTO market_quotes VALUES(%s,%s,%s,%s)",
                (uuid4(), iid, Jsonb(quote), completed),
            )
        commit_news(
            conn, iid, articles, rejected, completed, errors.get("company-news")
        )
        conn.execute(
            "UPDATE market_refresh_state SET lease_until=NULL,completed_at=%s,quote_error=%s,news_error=%s,news_count=%s,excluded_count=%s WHERE instrument_id=%s",
            (
                completed,
                errors.get("quote"),
                errors.get("company-news"),
                len(articles) if "company-news" not in errors else None,
                rejected,
                iid,
            ),
        )
    return dict(
        quote_ok=quote is not None, news_ok="company-news" not in errors, errors=errors
    )


def tick(now=None):
    """Recover interrupted requests locally, with no external calls."""
    with transaction(source=True) as conn:
        collection_lock(conn)
        now = now or datetime.now(timezone.utc)
        expired = rows(
            conn,
            "SELECT * FROM market_refresh_state WHERE lease_until<%s FOR UPDATE",
            (now,),
        )
        for attempt in expired:
            error = "Market refresh was interrupted. New quote and news coverage are unconfirmed."
            commit_news(conn, attempt["instrument_id"], [], 0, now, error)
            conn.execute(
                "UPDATE market_refresh_state SET attempt_id=NULL,lease_until=NULL,completed_at=%s,quote_error=%s,news_error=%s,news_count=NULL WHERE instrument_id=%s",
                (now, error, error, attempt["instrument_id"]),
            )


def workspace(conn, iid):
    quote = one(
        conn,
        "SELECT quote,retrieved_at FROM market_quotes WHERE instrument_id=%s ORDER BY retrieved_at DESC LIMIT 1",
        (iid,),
    )
    status = one(
        conn, "SELECT * FROM market_refresh_state WHERE instrument_id=%s", (iid,)
    )
    return dict(
        configured=configured(), quote=quote, status=status, minimum_refresh_minutes=5
    )
