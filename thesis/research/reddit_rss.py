"""Company/ticker RSS search, with original sources and explicit reply coverage.

RSS is a separately verified capability. Legacy JSON/HTML denials stay intact.
No redirects, credentials, browser impersonation or alternate hosts are used.
"""
import hashlib
import math
import re
import time
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from threading import Lock
from urllib.parse import urlencode
from xml.etree import ElementTree as ET

import httpx
from thesis.config import DATA, ROOT
from thesis.db import transaction, one
from thesis.providers.settings import settings
from thesis.service import Conflict
from . import social
from .catalogue import company_alias

METHOD = 'reddit-hot-rss-1'
SEARCH_METHOD = 'reddit-company-search-rss-1'
COMMENT_METHOD = 'reddit-comment-rss-updated-1'
UA = 'Thesis/0.1 (Deus-derived public RSS research)'
LOCK = Lock()
PREFIX = 'reddit-rss:'
ATOM = social.ATOM


def xml(body):
    if len(body) > 2_000_000 or b'<!DOCTYPE' in body.upper() or b'<!ENTITY' in body.upper():
        raise ValueError('Reddit RSS returned unsupported XML.')
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        raise ValueError('Reddit RSS did not return a readable feed.') from None
    if root.tag != ATOM + 'feed':
        raise ValueError('Reddit RSS did not return a discussion feed.')
    return root


def endpoint(kind, value):
    if kind == 'posts' and value in social.FEEDS:
        return f'https://www.reddit.com/r/{value}/hot/.rss'
    if kind == 'search' and isinstance(value, dict):
        symbol, feeds, days = value.get('symbol'), value.get('feeds'), value.get('days')
        if (isinstance(symbol, str) and re.fullmatch(r'[A-Z]{1,5}', symbol)
                and isinstance(feeds, (list, tuple)) and feeds
                and all(feed in social.FEEDS for feed in feeds)
                and type(days) is int and days in (1, 7, 30)):
            alias = company_alias(value.get('name'))
            query = f'"{symbol}"' + (f' OR "{alias}"' if alias else '')
            communities = '+'.join(sorted(set(feeds)))
            return f'https://www.reddit.com/r/{communities}/search.rss?' + urlencode(dict(
                q=query, restrict_sr='on', sort='new', t={1:'day',7:'week',30:'month'}[days], limit=50))
    if kind == 'comments' and isinstance(value, dict):
        match = re.fullmatch(r'https://www\.reddit\.com/r/([A-Za-z0-9_]+)/comments/([a-z0-9]+)/([A-Za-z0-9_-]+)/?', value.get('url', ''))
        if match and match[1].lower() == value.get('feed') and match[1].lower() in social.FEEDS and 't3_' + match[2] == value.get('post_key'):
            return value['url'].rstrip('/') + '/.rss'
    raise ValueError('Unsupported Reddit RSS destination.')


def _check_clock(row, now):
    if row['denied']:
        raise ValueError('Reddit RSS access was denied for this source. Collection is paused.')
    if row['blocked_until'] and row['blocked_until'] > now:
        raise Conflict('Reddit RSS is cooling down after HTTP 429; next check after ' + row['blocked_until'].astimezone(timezone.utc).strftime('%d %b, %H:%M UTC') + '.')


def remember_reset(headers, now):
    """Honor an exhausted response window without treating it as a new denial."""
    try:
        remaining = float(headers['X-Ratelimit-Remaining'])
        reset = float(headers['X-Ratelimit-Reset'])
        if not math.isfinite(remaining) or not math.isfinite(reset) or remaining > 0 or reset < 0:
            return
        until = now + timedelta(seconds=reset + 1)
    except (KeyError, TypeError, ValueError, OverflowError):
        return
    with transaction(source=True) as c:
        c.execute('INSERT INTO provider_clocks(provider,next_at) VALUES(%s,%s) ON CONFLICT(provider) DO UPDATE SET next_at=GREATEST(provider_clocks.next_at,excluded.next_at)',
                  (PREFIX + 'quota', until))


def wait_notice(next_at):
    return 'Reddit RSS is waiting for its request window; next check after ' + next_at.astimezone(timezone.utc).strftime('%d %b, %H:%M UTC') + '.'


def read(kind, value, *, transport=None, cache_only=False):
    url = endpoint(kind, value)
    if transport is None and not cache_only:
        if DATA != ROOT / '.local' or settings().get('THESIS_LIVE_DATA_ENABLED') != 'true':
            raise ValueError('Reddit RSS source loading is switched off in this workspace.')
    # Only one local request at a time. Persistent global pacing also protects
    # against other processes; each cache key has its own fifteen-minute lease.
    with LOCK:
        now = datetime.now(timezone.utc)
        cache_key = PREFIX + url.removeprefix('https://www.reddit.com/')
        # Hot feeds and search are the same post-reading capability. A denial
        # on either must also stop the other, including cached retrieval.
        capability = PREFIX + ('posts' if kind == 'search' else kind)
        with transaction(source=True) as c:
            for key in (PREFIX + 'all', PREFIX + 'quota', capability, cache_key):
                c.execute('INSERT INTO provider_clocks(provider) VALUES(%s) ON CONFLICT DO NOTHING', (key,))
            global_clock = one(c, 'SELECT * FROM provider_clocks WHERE provider=%s FOR UPDATE', (PREFIX + 'all',))
            scope = one(c, 'SELECT * FROM provider_clocks WHERE provider=%s FOR UPDATE', (capability,))
            quota = one(c, 'SELECT * FROM provider_clocks WHERE provider=%s FOR UPDATE', (PREFIX + 'quota',))
            _check_clock(scope, now)
            cached = one(c, 'SELECT * FROM public_feed_cache WHERE provider=%s', (cache_key,))
            if cached and now - cached['retrieved_at'] < timedelta(minutes=15 if not cache_only else 1440):
                return bytes(cached['body'])
            if cache_only:
                raise Conflict(f'No recent saved Reddit {kind} feed is available; no request was made during the cooldown.')
            _check_clock(global_clock, now)
            if now.date().isoformat() >= '2026-11-13':
                raise ValueError('Reddit RSS support has ended; a supported connection is needed.')
            lease = one(c, 'SELECT * FROM provider_clocks WHERE provider=%s FOR UPDATE', (cache_key,))
            if lease['next_at'] > now:
                raise Conflict('This Reddit RSS feed was checked recently; saved sources are retained.')
            used = global_clock['requests'] if global_clock['usage_date'] == now.date() else 0
            if used >= 240:
                raise Conflict('The daily Reddit RSS request limit has been reached.')
            start = max(now, global_clock['next_at'], quota['next_at'])
            # Defer long backlogs rather than spending the company's entire
            # collection lease asleep. Cached sources remain available.
            if start - now > timedelta(seconds=60):
                raise Conflict(wait_notice(start))
            c.execute('UPDATE provider_clocks SET next_at=%s,requests=%s,usage_date=%s WHERE provider=%s',
                      (start + timedelta(seconds=30), used + 1, now.date(), PREFIX + 'all'))
            c.execute('UPDATE provider_clocks SET next_at=%s WHERE provider=%s', (start + timedelta(minutes=15), cache_key))
        time.sleep(max(0, (start - datetime.now(timezone.utc)).total_seconds()))
        with transaction(source=True) as c:
            for key in (PREFIX + 'all', capability):
                _check_clock(one(c, 'SELECT * FROM provider_clocks WHERE provider=%s', (key,)), datetime.now(timezone.utc))
            quota = one(c, 'SELECT next_at FROM provider_clocks WHERE provider=%s', (PREFIX + 'quota',))
            if quota['next_at'] > datetime.now(timezone.utc):
                raise Conflict(wait_notice(quota['next_at']))
        try:
            with httpx.Client(timeout=httpx.Timeout(20, connect=6), follow_redirects=False,
                              trust_env=False, transport=transport,
                              headers={'User-Agent': UA, 'Accept': 'application/atom+xml'}) as client:
                with client.stream('GET', url) as response:
                    remember_reset(response.headers, datetime.now(timezone.utc))
                    if response.status_code in (401, 403, 429):
                        now = datetime.now(timezone.utc)
                        seconds = 900
                        retry = response.headers.get('Retry-After', '')
                        try:
                            seconds = max(seconds, int(retry) if retry.isdigit() else (parsedate_to_datetime(retry) - now).total_seconds())
                        except (TypeError, ValueError, OverflowError):
                            pass
                        until = now + timedelta(seconds=seconds)
                        with transaction(source=True) as c:
                            if response.status_code == 429:
                                c.execute('UPDATE provider_clocks SET blocked_until=%s WHERE provider=%s',
                                          (until, PREFIX + 'all'))
                            else:
                                c.execute('UPDATE provider_clocks SET denied=true WHERE provider=%s', (capability,))
                        retry_notice = (' Next check after ' + until.astimezone(timezone.utc).strftime('%d %b, %H:%M UTC') + '.') if response.status_code == 429 else ''
                        raise ValueError(f'Reddit RSS {kind} returned HTTP {response.status_code}. Collection stopped; saved sources are retained.' + retry_notice)
                    if response.status_code != 200:
                        raise ValueError(f'Reddit RSS {kind} returned HTTP {response.status_code}; no redirect or retry was followed.')
                    if not any(t in response.headers.get('Content-Type', '').lower() for t in ('application/atom+xml', 'application/xml', 'text/xml')):
                        raise ValueError('Reddit RSS returned a page rather than a feed.')
                    body = bytearray()
                    for part in response.iter_bytes():
                        body.extend(part)
                        if len(body) > 2_000_000:
                            raise ValueError('Reddit RSS exceeded the reading limit.')
            body = bytes(body)
            xml(body)
        except httpx.HTTPError:
            raise ValueError(f'Reddit RSS {kind} could not be reached. Saved sources are retained.') from None
        with transaction(source=True) as c:
            c.execute('INSERT INTO public_feed_cache VALUES(%s,%s,%s) ON CONFLICT(provider) DO UPDATE SET body=excluded.body,retrieved_at=excluded.retrieved_at',
                      (cache_key, body, datetime.now(timezone.utc)))
        return body


def posts(body, feed, now, days, *, search=False):
    root = xml(body)
    enabled = tuple(feed) if search and isinstance(feed, (list, tuple)) else (feed,)
    if not enabled or any(f not in social.FEEDS for f in enabled):
        raise ValueError('Unsupported Reddit communities.')
    # Never substitute an edit timestamp for the original publication date.
    for entry in list(root.findall(ATOM + 'entry'))[50 if search else 25:]:
        root.remove(entry)
    missing = 0
    for entry in list(root.findall(ATOM + 'entry')):
        if not entry.findtext(ATOM + 'published'):
            root.remove(entry)
            missing += 1
    parsed, excluded = social.parse_feed(ET.tostring(root), enabled[0], now, days)
    result, seen = [], set()
    for post in parsed:
        match = re.fullmatch(r'https://www\.reddit\.com/r/([A-Za-z0-9_]+)/comments/([a-z0-9]+)/[A-Za-z0-9_-]+/?', post['url'])
        if not match or match[1].lower() not in enabled or post['post_key'] != 't3_' + match[2] or post['post_key'] in seen:
            excluded += 1
            continue
        seen.add(post['post_key'])
        post['feed'] = match[1].lower()
        post['kind'] = 'post'
        post['thread_key'] = post['post_key']
        post['method'] = SEARCH_METHOD if search else METHOD
        result.append(post)
    return result, excluded + missing


def replies(body, post, now, days):
    root = xml(body)
    self_url = next((e.get('href') for e in root.findall(ATOM+'link') if e.get('rel')=='self'), None)
    if self_url != endpoint('comments', post):
        raise ValueError('Reddit comment feed does not match the requested thread.')
    entries = root.findall(ATOM+'entry')
    original = next((e for e in entries if e.findtext(ATOM+'id')==post['post_key']), None)
    if original is None or social.plain_summary(original.findtext(ATOM+'title') or '') != post['title']:
        raise ValueError('Reddit comment feed is missing its verified thread identity.')
    try:
        published = datetime.fromisoformat((original.findtext(ATOM+'published') or '').replace('Z','+00:00'))
    except ValueError:
        raise ValueError('Reddit thread publication time is missing.') from None
    if published != post['published_at']:
        raise ValueError('Reddit thread publication time changed since discovery.')
    if social.plain_summary(original.findtext(ATOM+'content') or '') in ('[removed]', '[deleted]'):
        return [], [post['post_key']]
    result, removed, seen = [], [], set()
    for entry in [e for e in entries if (e.findtext(ATOM+'id') or '').startswith('t1_')][:50]:
        key = entry.findtext(ATOM+'id') or ''
        url = next((l.get('href','') for l in entry.findall(ATOM+'link') if l.get('rel','alternate')=='alternate'), '')
        if not re.fullmatch(r't1_[a-z0-9]+',key) or key in seen or url != post['url'].rstrip('/')+'/'+key[3:]+'/':
            continue
        seen.add(key)
        text = social.plain_summary(entry.findtext(ATOM+'content') or '')
        if text in ('[removed]', '[deleted]'):
            removed.append(key)
            continue
        author = entry.findtext(ATOM+'author/'+ATOM+'name')
        # Reddit comment Atom entries expose updated, not published, and no
        # immediate-parent ID. Preserve that date basis, never invent a parent.
        try:
            dated = datetime.fromisoformat((entry.findtext(ATOM+'updated') or '').replace('Z','+00:00'))
        except ValueError:
            continue
        if dated.tzinfo is None or not max(published,now-timedelta(days=days)) <= dated <= now or not text or len(text)>12000 or author=='/u/AutoModerator':
            continue
        title = 'Reddit comment'
        result.append(dict(post_key=key,feed=post['feed'],title=title,body=text,url=url,
                           published_at=dated,thread_key=post['post_key'],kind='comment',method=COMMENT_METHOD,
                           author_hash=hashlib.sha256(author.encode()).hexdigest() if author and author!='/u/[deleted]' else None,
                           content_hash=hashlib.sha256((title+'\n'+text).encode()).hexdigest()))
    return result, removed


def collect(company, days, enabled, now, fetcher=None, *, cache_only=False):
    get = fetcher or read
    selected, comments, removed = [], [], []
    discovered = excluded = 0
    checks = {'posts': dict(fetched=0, matched=0, errors=[]), 'comments': dict(fetched=0, matched=0, errors=[])}
    def cached(kind, value):
        if fetcher:
            raise Conflict('No cached feed was supplied for this source check.')
        return read(kind,value,cache_only=True)
    live_allowed=not cache_only
    seen=set()
    def accept(candidates, skipped):
        nonlocal discovered, excluded
        candidates=[p for p in candidates if p['post_key'] not in seen]
        seen.update(p['post_key'] for p in candidates)
        discovered += len(candidates)
        checks['posts']['fetched'] += len(candidates)
        matches = [p for p in candidates if social.mentions(p, company['symbol'], company['name'])]
        selected.extend(matches)
        excluded += skipped + len(candidates) - len(matches)
    query=dict(company, feeds=enabled, days=days)
    try:
        accept(*posts((get if live_allowed else cached)('search', query), enabled, now, days, search=True))
        if not live_allowed:
            checks['posts']['cached'] = True
    except (ValueError, Conflict, httpx.HTTPError) as exc:
        checks['posts']['errors'].append(str(exc))
        live_allowed=False
    # Previously acquired hot feeds supplement discovery without spending
    # another request per community. Missing optional caches are not failures.
    # New company search is the sole live post-discovery request.
    for feed in enabled:
        try:
            candidates, skipped = posts(cached('posts', feed), feed, now, days)
            accept(candidates, skipped)
            checks['posts']['cached'] = True
        except Conflict:
            pass
        except (ValueError, httpx.HTTPError) as exc:
            checks['posts']['errors'].append(str(exc))
            live_allowed=False
    for post in sorted(selected, key=lambda p: (social.mentions(dict(title=p['title'],body=''),company['symbol'],company['name']),p['published_at']), reverse=True)[:3]:
        try:
            reply, withdrawn = replies((get if live_allowed else cached)('comments', post), post, now, days)
            if not live_allowed:
                checks['comments']['cached'] = True
            # Without a verified immediate parent, only a comment's own
            # company mention can admit it. Never borrow its thread title.
            eligible=[p for p in reply if social.mentions(p,company['symbol'],company['name'])][:12]
            comments.extend(eligible)
            removed.extend(withdrawn)
            checks['comments']['fetched'] += len(reply)
            excluded += len(reply)-len(eligible)
        except (ValueError, Conflict, httpx.HTTPError) as exc:
            checks['comments']['errors'].append(str(exc))
            live_allowed=False
    checks['posts']['matched'] = len(selected)
    checks['comments']['matched'] = len(comments)
    errors = [error for check in checks.values() for error in check['errors']]
    return dict(posts=selected, comments=comments, removed=removed, discovered=discovered,
                excluded=excluded, checks=checks, error=' '.join(errors) or None)
