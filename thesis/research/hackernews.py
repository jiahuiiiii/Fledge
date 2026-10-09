"""Bounded HN comment discovery via Algolia, text verified through HN's API.

No parent/thread inference, popularity scoring, account credentials or retries.
Search candidates are not themselves evidence. Current original comments are.
"""

import hashlib
import re
import time
from itertools import zip_longest
from datetime import datetime, timezone, timedelta
from uuid import uuid4, uuid5, NAMESPACE_URL
import httpx
from thesis.db import transaction, one, rows
from .catalogue import COMPANIES, mentions, company_search_name
from .social import plain_summary

RECRUITMENT = re.compile(
    r"r[ée]sum[ée]|willing to relocate|looking for (?:work|a job)|(?:remote|onsite).{0,80}(?:full[ -]time|founding engineer)|we(?:’|'|&#x27;)?re hiring",
    re.I,
)

def fetch(kind, value, now, *, lookback_days=7, company_name=None):
    # Cross-company persisted request pacing, with no transaction during HTTP.
    with transaction(source=True) as conn:
        row = one(
            conn, "SELECT next_at FROM hn_request_clock WHERE singleton FOR UPDATE"
        )
        start = max(datetime.now(timezone.utc), row["next_at"])
        conn.execute(
            "UPDATE hn_request_clock SET next_at=%s WHERE singleton",
            (start + timedelta(seconds=1),),
        )
    time.sleep(max(0, (start - datetime.now(timezone.utc)).total_seconds()))
    from .directory import valid_symbol
    if kind in {"search", "stories"} and valid_symbol(value):
        url = "https://hn.algolia.com/api/v1/search_by_date"
        params = dict(
            query='"' + company_search_name(value, company_name) + '"',
            tags="story" if kind == "stories" else "comment",
            hitsPerPage=8 if kind == "stories" else 40,
            typoTolerance="false", queryType="prefixNone",
            numericFilters=f"created_at_i>{int((now-timedelta(days=lookback_days)).timestamp())}",
            restrictSearchableAttributes="title" if kind == "stories" else "comment_text",
        )
    elif kind == "item" and re.fullmatch(r"[1-9][0-9]{0,11}", str(value)):
        url, params = f"https://hacker-news.firebaseio.com/v0/item/{value}.json", None
    else:
        raise ValueError("Unsupported HN request")
    with httpx.Client(
        timeout=httpx.Timeout(6, connect=3),
        follow_redirects=False,
        headers={
            "User-Agent": "ThesisResearchPrototype/0.1 (local company research)",
            "Accept": "application/json",
        },
    ) as client:
        with client.stream("GET", url, params=params) as response:
            response.raise_for_status()
            data = bytearray()
            for chunk in response.iter_bytes():
                data.extend(chunk)
                if len(data) > 2000000:
                    raise ValueError("HN response exceeded size limit")
    import json

    return json.loads(data)


def candidates(result, limit=12):
    if not isinstance(result, dict) or not isinstance(result.get("hits"), list):
        raise ValueError("HN search response is unavailable")
    return list(
        dict.fromkeys(
            str(h.get("objectID", ""))
            for h in result["hits"][:limit]
            if isinstance(h, dict)
            and re.fullmatch(r"[1-9][0-9]{0,11}", str(h.get("objectID", "")))
        )
    )


def parse_item(raw, key, symbol, now, *, lookback_days=7, company_name=None, verified_parent=None):
    if not isinstance(raw, dict) or str(raw.get("id")) != key:
        raise ValueError("HN original comment identity is unavailable")
    if raw.get("deleted") is True or raw.get("dead") is True:
        return None, True
    if (
        raw.get("type") != "comment"
        or not isinstance(raw.get("text"), str)
        or type(raw.get("time")) is not int
    ):
        raise ValueError("HN item is not a complete comment")
    published = datetime.fromtimestamp(raw["time"], timezone.utc)
    body = plain_summary(raw["text"])
    if (
        not now - timedelta(days=lookback_days) <= published <= now
        or not body
        or len(body) > 12000
        or RECRUITMENT.search(body)
        or not (mentions(body, symbol, company_name) or (
            verified_parent and str(raw.get('parent')) == verified_parent['parent_key'][3:]
            and mentions(verified_parent['title'] + ' ' + verified_parent['body'], symbol, company_name)
            and verified_parent['published_at'] <= published
        ))
    ):
        return None, False
    title = "Hacker News comment"  # Do not attribute a parent headline to its author.
    author = raw.get("by")
    return (
        dict(
            platform="hackernews",
            feed="hackernews",
            post_key="hn:" + key,
            title=title,
            body=body,
            url="https://news.ycombinator.com/item?id=" + key,
            published_at=published,
            author_hash=(
                hashlib.sha256(("hackernews:" + author).encode()).hexdigest()
                if isinstance(author, str)
                else None
            ),
            content_hash=hashlib.sha256((title + "\n" + body).encode()).hexdigest(),
        ),
        False,
    )


def refresh(iid, *, fetcher=None, now=None, lookback_days=7, include_threads=False):
    from thesis.service import Conflict
    from .sec.service import collection_lock

    supplied_clock = now
    now = now or datetime.now(timezone.utc)
    token = uuid4()
    with transaction(source=True) as conn:
        company = one(
            conn,
            "SELECT i.symbol,i.name FROM instruments i JOIN sec_companies s ON s.instrument_id=i.id WHERE i.id=%s",
            (iid,),
        )
        if not company:
            raise ValueError("Choose a supported company for discussion research.")
        if not one(conn, "SELECT enabled FROM social_feeds WHERE feed='hackernews'")[
            "enabled"
        ]:
            return dict(checked=[], failures=0, status='blocked', message='Hacker News is switched off; no discussion check was made.')
        conn.execute(
            "INSERT INTO hn_refresh_state(instrument_id) VALUES(%s) ON CONFLICT DO NOTHING",
            (iid,),
        )
        state = one(
            conn,
            "SELECT * FROM hn_refresh_state WHERE instrument_id=%s FOR UPDATE",
            (iid,),
        )
        if state["lease_until"] and state["lease_until"] > now:
            raise Conflict("Hacker News comments are already being checked.")
        if state["last_attempt_at"] and now - state["last_attempt_at"] < timedelta(
            minutes=15
        ):
            raise Conflict(
                "Hacker News comments were checked recently; wait 15 minutes."
            )
        conn.execute(
            "UPDATE hn_refresh_state SET attempt_id=%s,lease_until=%s,last_attempt_at=%s WHERE instrument_id=%s",
            (token, now + timedelta(minutes=5), now, iid),
        )
        # Recheck up to eight retained comments even if removed from the search index.
        prior = rows(
            conn,
            "SELECT DISTINCT ON(post_key) post_key,published_at FROM social_posts WHERE instrument_id=%s AND platform='hackernews' AND published_at>=%s ORDER BY post_key,published_at DESC",
            (iid, now - timedelta(days=lookback_days)),
        )
        prior = sorted(prior, key=lambda p: p["published_at"], reverse=True)[:8]
    fetcher = fetcher or (lambda kind, value, clock: fetch(kind, value, clock, lookback_days=lookback_days, company_name=company["name"]))
    posts, withdrawn, excluded, checked, errors = [], [], 0, 0, []
    parents, originals = {}, {}
    search_available, api_denied = True, False
    try:
        keys = candidates(fetcher("search", company["symbol"], now), 40 if include_threads else 12)
    except (ValueError, httpx.HTTPError):
        keys = []
        search_available = False
        errors.append("Search failed; retained comments may be older.")
    # Adapt Deus's original-story discovery and enrichment before classification.
    # Verify a story on HN before reading any of its replies; index text is never evidence.
    if include_threads and search_available:
        from .conversation import parent_content
        try:
            stories = fetcher("stories", company["symbol"], now)
            inspected = 0
            for key in candidates(stories, 8):
                raw = fetcher("item", key, now)
                if isinstance(raw, dict) and (raw.get('deleted') or raw.get('dead')):
                    withdrawn.append('hn:' + key)
                    continue
                parent, removed = parent_content(raw, key, now, now)
                if removed or parent['parent_type'] != 'story' or not mentions(parent['title']+' '+parent['body'], company['symbol'], company['name']):
                    continue
                if not now - timedelta(days=lookback_days) <= parent['published_at'] <= now:
                    continue
                children = raw.get('kids', [])
                if not isinstance(children, list):
                    continue
                for child in children[:8]:
                    if type(child) is int and child > 0:
                        parents[str(child)] = parent
                inspected += 1
                if inspected >= 3:
                    break
        except httpx.HTTPStatusError as exc:
            api_denied = exc.response.status_code in (401,403,429) and exc.request.url.host == 'hacker-news.firebaseio.com'
            errors.append(f"Discussion discovery returned HTTP {exc.response.status_code}; denied requests were not retried.")
        except (ValueError, TypeError, OverflowError, httpx.HTTPError):
            errors.append("Some original discussion threads could not be checked.")
    # Balance direct mentions with thread replies instead of letting one busy thread fill the sample.
    thread_keys = list(parents)
    direct = list(dict.fromkeys(keys + [p["post_key"][3:] for p in prior]))
    if include_threads:
        keys = list(dict.fromkeys([k for pair in zip_longest(direct[:24], thread_keys) for k in pair if k]))[:48]
    else:
        keys = direct[:20]
    for key in ([] if api_denied else keys):
        try:
            raw = fetcher("item", key, now)
            post, removed = parse_item(raw, key, company["symbol"], now, lookback_days=lookback_days, company_name=company["name"], verified_parent=parents.get(key))
            checked += 1
            if removed:
                withdrawn.append("hn:" + key)
            elif post:
                posts.append(post)
                originals[post['post_key']] = raw
            else:
                excluded += 1
        except httpx.HTTPStatusError as exc:
            api_denied = True
            excluded += 1
            errors.append(
                f"Original API returned HTTP {exc.response.status_code}; remaining comments were not requested."
            )
            break
        except (ValueError, TypeError, OverflowError, OSError, httpx.HTTPError):
            excluded += 1
            errors.append("An original comment could not be verified.")
    if include_threads and not api_denied:
        # Deus enriches before classification. Also recover immediate context for
        # direct-search replies ("they", quoted claims, etc.), not just thread hits.
        from .conversation import parent_content
        for p in [p for p in posts if p['post_key'][3:] not in parents][:3]:
            raw=originals[p['post_key']]
            parent_key=str(raw.get('parent',''))
            if not re.fullmatch(r'[1-9][0-9]{0,11}',parent_key):
                continue
            try:
                parent,removed=parent_content(fetcher('item',parent_key,now),parent_key,p['published_at'],now)
                if removed:
                    withdrawn.append('hn:'+parent_key)
                else:
                    parents[p['post_key'][3:]]=parent
            except httpx.HTTPStatusError:
                errors.append('Original reply context could not be reached; remaining parent checks stopped.')
                break
            except (ValueError,TypeError,OverflowError,httpx.HTTPError):
                continue
    done = supplied_clock or datetime.now(timezone.utc)
    error = " ".join(dict.fromkeys(errors)) or None
    with transaction(source=True) as conn:
        collection_lock(conn)
        state = one(
            conn,
            "SELECT attempt_id FROM hn_refresh_state WHERE instrument_id=%s FOR UPDATE",
            (iid,),
        )
        if state["attempt_id"] != token:
            raise Conflict("A newer HN check replaced this attempt.")
        for key in withdrawn:
            conn.execute(
                "INSERT INTO hn_withdrawals VALUES(%s,%s) ON CONFLICT DO NOTHING",
                (key, done),
            )
        for p in posts:
            pid = uuid5(
                NAMESPACE_URL,
                str(iid) + ":hackernews:" + p["post_key"] + ":" + p["content_hash"],
            )
            conn.execute(
                "INSERT INTO social_posts VALUES(%s,%s,'hackernews','hackernews',%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                (
                    pid,
                    iid,
                    p["post_key"],
                    p["author_hash"],
                    p["content_hash"],
                    p["title"],
                    p["body"],
                    p["url"],
                    p["published_at"],
                    done,
                ),
            )
            if include_threads:
                from .social_threads import save
                parent = parents.get(p['post_key'][3:])
                # Only the verified immediate parent can be attached.
                if parent and str(originals[p['post_key']].get('parent')) != parent['parent_key'][3:]:
                    parent = None
                save(conn,pid,(parent or {}).get('parent_key',p['post_key']),'comment',
                     'direct' if mentions(p['body'],company['symbol'],company['name']) else 'thread',done,parent)
        conn.execute(
            "UPDATE hn_refresh_state SET lease_until=NULL,completed_at=%s,post_count=%s,matched_count=%s,excluded_count=%s,error=%s WHERE instrument_id=%s",
            (done, checked, len(posts), excluded, error, iid),
        )
    result=dict(checked=["hackernews"], failures=int(bool(error)))
    if include_threads:
        result.update(message=error or f'{len(posts)} verified comments matched in this {lookback_days}-day search sample; {checked} original comments checked. This is a limited sample, not all Hacker News discussion.', matched=len(posts))
    return result
