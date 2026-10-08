"""Bounded Reddit feed adapter, adapted from Deus's public RSS source.

No accounts, cookies, comment scraping, proxy rotation or access-denial fallback.
"""

import hashlib
import html
import re
from datetime import datetime, timezone, timedelta
from uuid import uuid4, uuid5, NAMESPACE_URL
from xml.etree import ElementTree as ET
import httpx
from thesis.db import transaction, rows, one
from .sec.service import COMPANIES
from .catalogue import mentions as company_mentioned

FEEDS = ("stocks", "investing", "wallstreetbets")
ATOM = "{http://www.w3.org/2005/Atom}"
_HTML_TAG = re.compile(r"<[^>]+>")
_SUBMITTED_BY_FOOTER = re.compile(
    r"\s*submitted by\s+/u/[\w-]+(?:\s+to\s+r/[\w-]+)?\s*\[link\]\s*\[comments\]\s*$",
    re.I,
)


def plain_summary(raw):
    # Deus strips tags before entities so escaped angle brackets survive.
    text = html.unescape(_HTML_TAG.sub(" ", raw))
    return _SUBMITTED_BY_FOOTER.sub("", " ".join(text.split()))


def parse_feed(content, feed, now, lookback_days=7):
    if feed not in FEEDS or now.tzinfo is None:
        raise ValueError("Unsupported social feed or missing clock")
    if (
        len(content) > 2000000
        or b"<!DOCTYPE" in content.upper()
        or b"<!ENTITY" in content.upper()
    ):
        raise ValueError("Unsupported social feed size or XML declaration")
    root = ET.fromstring(content)
    if root.tag != ATOM + "feed":
        raise ValueError("The social source did not return an Atom feed")
    result = []
    excluded = 0
    for entry in root.findall(ATOM + "entry")[:50]:
        try:
            key = entry.findtext(ATOM + "id") or ""
            title = plain_summary(entry.findtext(ATOM + "title") or "")
            body = plain_summary(
                entry.findtext(ATOM + "content")
                or entry.findtext(ATOM + "summary")
                or ""
            )
            links = entry.findall(ATOM + "link")
            url = next(
                (
                    l.get("href", "")
                    for l in links
                    if l.get("rel", "alternate") == "alternate"
                ),
                "",
            )
            posted = datetime.fromisoformat(
                (
                    entry.findtext(ATOM + "published")
                    or entry.findtext(ATOM + "updated")
                    or ""
                ).replace("Z", "+00:00")
            )
            if (
                not key
                or not title
                or len(title) > 600
                or len(body) > 12000
                or posted.tzinfo is None
                or not now - timedelta(days=lookback_days) <= posted <= now
            ):
                raise ValueError("Unavailable post scope")
            if not re.fullmatch(
                r"https://(?:www\.)?reddit\.com/r/[A-Za-z0-9_]+/comments/[A-Za-z0-9]+/[^?#\s]*",
                url,
            ):
                raise ValueError("Unsupported post URL")
            author = entry.findtext(ATOM + "author/" + ATOM + "name")
            result.append(
                dict(
                    post_key=key,
                    title=title,
                    body=body,
                    url=url,
                    published_at=posted,
                    feed=feed,
                    author_hash=(
                        hashlib.sha256(author.encode()).hexdigest() if author else None
                    ),
                    content_hash=hashlib.sha256(
                        (title + "\n" + body).encode()
                    ).hexdigest(),
                )
            )
        except (ValueError, TypeError):
            excluded += 1
    return result, excluded


def mentions(post, symbol, company_name=None):
    return company_mentioned(post["title"] + " " + post["body"], symbol, company_name)


def fetch(feed):
    from .reddit_research import request
    if feed not in FEEDS:
        raise ValueError('Unsupported social feed')
    return request(f'https://www.reddit.com/r/{feed}/new/.rss', {'limit':50}, atom=True)


def refresh(*, fetcher=None, now=None, lookback_days=7):
    from thesis.service import Conflict
    from .sec.service import collection_lock

    now = now or datetime.now(timezone.utc)
    fetcher = fetcher or fetch
    token = uuid4()
    with transaction(source=True) as c:
        row = one(c, "SELECT * FROM social_refresh_lock WHERE singleton FOR UPDATE")
        if row["lease_until"] and row["lease_until"] > now:
            raise Conflict("Social sources are already being checked.")
        if row["last_attempt_at"] and now - row["last_attempt_at"] < timedelta(
            minutes=15
        ):
            raise Conflict(
                "Social sources were checked recently. The next check is available after 15 minutes."
            )
        c.execute(
            "UPDATE social_refresh_lock SET attempt_id=%s,lease_until=%s,last_attempt_at=%s WHERE singleton",
            (token, now + timedelta(minutes=3), now),
        )
        enabled = {
            r["feed"] for r in rows(c, "SELECT feed FROM social_feeds WHERE enabled")
        }
    gathered = {}
    for feed in FEEDS:
        if feed not in enabled:
            continue
        try:
            content = fetcher(feed)
            done = (
                now
                if now is not None and fetcher is not fetch
                else datetime.now(timezone.utc)
            )
            posts, excluded = parse_feed(content, feed, done, lookback_days)
            gathered[feed] = (posts, excluded, None, done)
        except httpx.HTTPStatusError as e:
            gathered[feed] = (
                [],
                0,
                f"Reddit returned HTTP {e.response.status_code}. No access workaround was attempted.",
                datetime.now(timezone.utc),
            )
        except (ValueError, Conflict, httpx.HTTPError, ET.ParseError):
            gathered[feed] = (
                [],
                0,
                "Social feed could not be read. Previous posts may be older.",
                datetime.now(timezone.utc),
            )
    with transaction(source=True) as c:
        collection_lock(c)
        row = one(c, "SELECT * FROM social_refresh_lock WHERE singleton FOR UPDATE")
        if row["attempt_id"] != token:
            raise Conflict("A newer social check replaced this attempt.")
        companies = rows(
            c,
            "SELECT i.id,i.symbol,i.name FROM instruments i JOIN sec_companies s ON s.instrument_id=i.id",
        )
        for feed, (posts, excluded, error, done) in gathered.items():
            matched = 0
            for company in companies:
                for post in posts:
                    if not mentions(
                        post, company["symbol"], company["name"]
                    ):
                        continue
                    matched += 1
                    pid = uuid5(
                        NAMESPACE_URL,
                        str(company["id"])
                        + ":reddit:"
                        + post["post_key"]
                        + ":"
                        + post["content_hash"],
                    )
                    c.execute(
                        "INSERT INTO social_posts VALUES(%s,%s,'reddit',%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                        (
                            pid,
                            company["id"],
                            feed,
                            post["post_key"],
                            post["author_hash"],
                            post["content_hash"],
                            post["title"],
                            post["body"],
                            post["url"],
                            post["published_at"],
                            done,
                        ),
                    )
            c.execute(
                "INSERT INTO social_refresh_state VALUES(%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(feed) DO UPDATE SET last_attempt_at=excluded.last_attempt_at,completed_at=excluded.completed_at,post_count=excluded.post_count,matched_count=excluded.matched_count,excluded_count=excluded.excluded_count,error=excluded.error",
                (feed, now, done, len(posts), matched, excluded, error),
            )
        c.execute("UPDATE social_refresh_lock SET lease_until=NULL WHERE singleton")
    return {
        "checked": list(gathered),
        "failures": sum(bool(v[2]) for v in gathered.values()),
    }


def documents(conn, iid, cutoff, lookback_days=7):
    data = rows(
        conn,
        "SELECT DISTINCT ON (p.post_key) p.*,d.thread_key,d.kind AS social_kind,d.match_basis FROM social_posts p JOIN social_feeds f ON f.feed=p.feed AND f.enabled LEFT JOIN social_discovery d ON d.post_id=p.id WHERE NOT EXISTS(SELECT 1 FROM hn_withdrawals w WHERE w.post_key IN (p.post_key,d.thread_key) AND p.platform='hackernews') AND NOT EXISTS(SELECT 1 FROM social_withdrawals w WHERE w.post_key IN (p.post_key,d.thread_key)) AND p.instrument_id=%s AND p.available_at<=%s AND p.published_at<=%s AND p.published_at>=%s ORDER BY p.post_key,p.available_at DESC,p.id DESC",
        (iid, cutoff, cutoff, cutoff - timedelta(days=lookback_days)),
    )
    return sorted(data, key=lambda p: (p["published_at"], str(p["id"])), reverse=True)


def status(conn, iid=None):
    result = rows(
        conn,
        "SELECT f.feed,f.enabled,s.completed_at,s.post_count,s.matched_count,s.excluded_count,s.error FROM social_feeds f LEFT JOIN social_refresh_state s ON s.feed=f.feed WHERE f.feed NOT IN ('hackernews','x') ORDER BY f.feed",
    )

    for value in result:
        value.update(
            platform="reddit",
            label="Reddit · r/" + value["feed"],
            notice="Reddit has announced RSS retirement on 13 November 2026.",
        )
    if iid:
        directed = one(conn,'SELECT * FROM reddit_company_checks WHERE instrument_id=%s',(iid,))
        if directed:
            result=[dict(directed,feed='reddit-company',platform='reddit',label='Reddit company discussions',
                         enabled=any(v['enabled'] for v in result),
                         notice='Company-name and ticker search across enabled investing communities; up to 50 posts and replies from three threads. This is a bounded sample, not a complete archive.')]
        value = one(
            conn,
            "SELECT f.feed,f.enabled,s.completed_at,s.post_count,s.matched_count,s.excluded_count,s.error FROM social_feeds f LEFT JOIN hn_refresh_state s ON s.instrument_id=%s WHERE f.feed='hackernews'",
            (iid,),
        )
        value.update(
            platform="hackernews",
            label="Hacker News comments",
            notice="Exact company-name discovery plus verified replies from up to three company-related threads. Tech-community discussion, not all investors. Parent wording is context, not another opinion.",
        )
        result.append(value)
    return result


def publisher(record):
    if record.get('platform')=='x':return 'X · public posts'
    return (
        "Hacker News · comments"
        if record.get("platform") == "hackernews"
        else "Reddit · r/" + record["feed"]
    )


def balanced(records):
    """Alternate platforms newest-first within each; unused slots remain usable."""
    buckets = [
        [p for p in records if p.get("platform", "reddit") == platform]
        for platform in ("reddit", "hackernews", "x")
    ]
    ordered = [
        bucket[index]
        for index in range(max(map(len, buckets), default=0))
        for bucket in buckets
        if index < len(bucket)
    ]
    # Deus enriches before classification. Keep conversation variety rather than
    # treating a large thread or identical pasted text as independent evidence.
    counts,seen,result = {},set(),[]
    for post in ordered:
        thread=post.get('thread_key') or post['post_key']
        key=(post.get('platform','reddit'),' '.join((post['title']+' '+post['body']).split()))
        if key in seen or counts.get(thread,0)>=2:
            continue
        seen.add(key)
        counts[thread]=counts.get(thread,0)+1
        result.append(post)
    return result


def refresh_company(iid):
    from thesis.service import Conflict
    from . import hackernews, reddit_research, x_source

    result = dict(checked=[], failures=0, recent=[])
    for label, run in [
        ("reddit", lambda: reddit_research.refresh(iid)),
        ("hackernews", lambda: hackernews.refresh(iid,include_threads=True)),
        ("x", lambda: x_source.refresh(iid)),
    ]:
        try:
            value = run()
            result["checked"] += value.get("checked", [label] if value.get("status")=="ready" else [])
            result["failures"] += value.get("failures", int(value.get("status")=="failed"))
            if label=="x": result["x"] = value
        except Conflict:
            result["recent"].append(label)
    return result
