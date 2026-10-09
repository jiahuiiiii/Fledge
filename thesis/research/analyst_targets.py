"""Bounded public analyst targets, separate from user-assumption valuations.

No browser impersonation, hidden API, model call, automatic retry or fallback.
Only the visible forecast summary/table is parsed; scripts are never evaluated.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
from html.parser import HTMLParser
import re
import time
from uuid import uuid4

import httpx
from psycopg.types.json import Jsonb
from thesis.db import transaction, one
from thesis.providers.settings import settings
from thesis.service import Conflict
from .sec.service import COMPANIES, collection_lock
from .sec.performance import decimal_text

SOURCE = 'stockanalysis-targets'
MAX_BYTES = 2_000_000
USER_AGENT = 'Thesis-local-pitch/0.1'
FAILURE = 'Analyst targets could not be refreshed. Earlier data is retained; no automatic retry.'


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip = 0
        self.in_title = False
        self.title = []
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'noscript'):
            self.skip += 1
        if tag == 'title':
            self.in_title = True

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript'):
            self.skip = max(0, self.skip - 1)
        if tag == 'title':
            self.in_title = False

    def handle_data(self, value):
        if not self.skip and value.strip():
            self.parts.append(value.strip())
            if self.in_title:
                self.title.append(value.strip())


def url(symbol):
    from .directory import valid_symbol
    if not valid_symbol(symbol):
        raise ValueError('Analyst targets are not supported for this company.')
    return f'https://stockanalysis.com/stocks/{symbol.lower()}/forecast/'


def normalized(html, symbol):
    source_url = url(symbol)
    if not isinstance(html, str) or len(html.encode()) > MAX_BYTES:
        raise ValueError('Forecast page exceeded its supported size.')
    parser = VisibleText()
    parser.feed(html)
    text = re.sub(r'\s+', ' ', ' '.join(parser.parts))
    title = ' '.join(parser.title)
    if f'({symbol}) Stock Forecast' not in title or not re.search(
        rf'(?:NASDAQ|NYSE|NYSEAMERICAN): {re.escape(symbol)} · [^·]{{1,45}} · USD\b', text
    ):
        raise ValueError('Forecast company, exchange or USD currency could not be verified.')
    sections = re.findall(r'Stock Price Forecast (.*?) Analyst Ratings', text)
    if len(sections) != 1:
        raise ValueError('A unique public forecast section is unavailable.')
    section = sections[0]
    money = r'([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)'
    table = re.search(r'Target Low Average Median High Price \$'+money+r' \$'+money+r' \$'+money+r' \$'+money+r'\b', section)
    count = re.search(r'According to ([0-9]+) analysts polled by S&P Global,', section)
    mean = re.search(r'average price target of \$'+money+r'\.', section)
    low = re.search(r'while the lowest is \$'+money+r' ', section)
    high = re.search(r'and the highest is \$'+money+r' ', section)
    if not all((table, count, mean, low, high)) or 'average 1-year stock price forecast' not in section:
        raise ValueError('The public target table, poll or horizon is missing or changed.')
    values = [Decimal(v.replace(',', '')) for v in table.groups()]
    if not (all(0 < v <= 1_000_000 for v in values) and
            values[0] <= values[1] <= values[3] and values[0] <= values[2] <= values[3]):
        raise ValueError('Analyst target range is inconsistent.')
    if [values[1], values[0], values[3]] != [Decimal(m.group(1).replace(',', '')) for m in (mean, low, high)]:
        raise ValueError('The source summary and target table disagree.')
    if not 1 <= int(count.group(1)) <= 1000:
        raise ValueError('Analyst poll size is unsupported.')
    page_date = None
    updated = re.search(r'Data Sources: S&P Global Market Intelligence and TipRanks Last updated: ([A-Z][a-z]{2} [0-9]{1,2}, [0-9]{4})', text)
    if updated:
        page_date = datetime.strptime(updated.group(1), '%b %d, %Y').date()
        if page_date > datetime.now(timezone.utc).date():
            raise ValueError('Source page update date is in the future.')
    return dict(symbol=symbol, currency='USD', horizon_months=12,
                targets=dict(zip(('low', 'mean', 'median', 'high'), map(decimal_text, values))),
                polled_analysts=int(count.group(1)), target_contributors=None,
                provider_as_of=None, page_updated_on=page_date.isoformat() if page_date else None,
                publisher='Stock Analysis', provider='S&P Global',
                url=source_url, method='stockanalysis-visible-targets-1',
                source_excerpt=section[:3000], page_sha256=sha256(html.encode()).hexdigest())


def allowed(conn):
    return bool(one(conn, "SELECT 1 FROM sources WHERE id=%s AND entitlement='local-stockanalysis-targets'", (SOURCE,)))


def fetch(symbol, *, transport=None, dispatch_gate=None):
    address = url(symbol)
    if settings().get('THESIS_LIVE_DATA_ENABLED') != 'true':
        raise ValueError('Live valuation data is not connected.')
    with transaction(source=True) as conn:
        clock = one(conn, 'SELECT next_at FROM analyst_target_clock WHERE singleton FOR UPDATE')
        now = datetime.now(timezone.utc)
        slot = max(now, clock['next_at'])
        delay = (slot-now).total_seconds()
        if delay > 6:
            raise ValueError('Target requests are busy. Try again later.')
        conn.execute('UPDATE analyst_target_clock SET next_at=%s WHERE singleton', (slot+timedelta(seconds=2),))
    if delay > 0:
        time.sleep(delay)
    if dispatch_gate:
        dispatch_gate()
    try:
        with httpx.Client(headers={'User-Agent':USER_AGENT}, timeout=25, follow_redirects=False, transport=transport) as client:
            with client.stream('GET', address) as response:
                if response.status_code != 200:
                    raise ValueError('Public target access was denied or unavailable.')
                if 'text/html' not in response.headers.get('content-type', ''):
                    raise ValueError('The public target response is not an HTML page.')
                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > MAX_BYTES:
                        raise ValueError('Forecast page exceeded its supported size.')
                return body.decode('utf-8')
    except (httpx.HTTPError, UnicodeDecodeError):
        raise ValueError('Public target page could not be read.') from None


def current(conn, iid):
    permitted = allowed(conn)
    saved = one(conn, 'SELECT id,data,retrieved_at FROM analyst_target_snapshots WHERE instrument_id=%s ORDER BY retrieved_at DESC,id DESC LIMIT 1', (iid,)) if permitted else None
    state = one(conn, 'SELECT last_attempt_at,completed_at,lease_until,error FROM analyst_target_state WHERE instrument_id=%s', (iid,))
    now = datetime.now(timezone.utc)
    if state and state['lease_until'] and state['lease_until'] <= now:
        state['error'] = 'The last target check did not finish. Earlier data is retained.'
    if saved:
        saved['stale'] = now-saved['retrieved_at'] > timedelta(days=1)
    return dict(available=permitted, snapshot=saved, refresh=state)


def refresh(iid, fetcher=None, *, purpose='targets'):
    from . import public_forecasts
    if purpose not in ('targets', 'financials'):
        raise ValueError('Unknown public forecast scope.')
    permission = allowed if purpose == 'targets' else public_forecasts.allowed
    committed = False
    now = datetime.now(timezone.utc)
    attempt = uuid4()
    with transaction(source=True) as conn:
        collection_lock(conn)
        company = one(conn, 'SELECT i.symbol FROM instruments i JOIN sec_companies s ON s.instrument_id=i.id WHERE i.id=%s', (iid,))
        if not company or not permission(conn):
            raise ValueError('Analyst targets are unavailable for this company/source.')
        collect_targets = allowed(conn)
        collect_financials = public_forecasts.allowed(conn)
        conn.execute('INSERT INTO analyst_target_state(instrument_id) VALUES(%s) ON CONFLICT DO NOTHING', (iid,))
        state = one(conn, 'SELECT * FROM analyst_target_state WHERE instrument_id=%s FOR UPDATE', (iid,))
        if state['lease_until'] and state['lease_until'] > now:
            raise Conflict('An analyst target check is already running.')
        if state['last_attempt_at'] and now-state['last_attempt_at'] < timedelta(days=1):
            raise Conflict('Analyst targets can be checked once per company every 24 hours. Saved data remains available.')
        conn.execute('UPDATE analyst_target_state SET attempt_id=%s,last_attempt_at=%s,lease_until=%s,error=NULL WHERE instrument_id=%s', (attempt,now,now+timedelta(minutes=2),iid))
    try:
        def gate():
            with transaction(source=True) as conn:
                state = one(conn, 'SELECT attempt_id,lease_until FROM analyst_target_state WHERE instrument_id=%s', (iid,))
                if (not permission(conn) or not state or state['attempt_id'] != attempt or
                        not state['lease_until'] or state['lease_until'] <= datetime.now(timezone.utc)):
                    raise ValueError('Public forecast access or request ownership changed.')
        gate()
        html = fetcher(company['symbol']) if fetcher else fetch(company['symbol'], dispatch_gate=gate)
        data = financial = None
        target_error = financial_error = None
        try: data = normalized(html, company['symbol'])
        except ValueError as exc: target_error = str(exc)
        try: financial = public_forecasts.normalized(html, company['symbol'])
        except ValueError as exc: financial_error = str(exc)
        with transaction(source=True) as conn:
            collection_lock(conn)
            now = datetime.now(timezone.utc)
            state = one(conn, 'SELECT attempt_id,lease_until FROM analyst_target_state WHERE instrument_id=%s FOR UPDATE', (iid,))
            if state['attempt_id'] != attempt or not state['lease_until'] or state['lease_until'] <= now or not permission(conn):
                raise ValueError('Target check expired or source access changed.')
            sid = None
            if data and collect_targets and allowed(conn):
                sid = uuid4()
                conn.execute('INSERT INTO analyst_target_snapshots VALUES(%s,%s,%s,%s)', (sid,iid,Jsonb(data),now))
            if collect_financials and public_forecasts.allowed(conn):
                fid = uuid4()
                conn.execute('INSERT INTO public_financial_forecasts VALUES(%s,%s,%s,%s,%s,%s,%s)',
                             (fid,iid,now,sha256(html.encode()).hexdigest(),html,Jsonb(financial) if financial else None,financial_error))
                if purpose == 'financials': sid = fid if financial else None
            requested_error = target_error if purpose == 'targets' else financial_error
            conn.execute('UPDATE analyst_target_state SET completed_at=%s,lease_until=NULL,error=%s WHERE instrument_id=%s', (now,FAILURE if target_error and collect_targets else None,iid))
        committed = True
        if requested_error:
            raise ValueError(requested_error)
        return dict(id=str(sid))
    except Exception:
        if not committed:
            with transaction(source=True) as conn:
                collection_lock(conn)
                conn.execute('UPDATE analyst_target_state SET lease_until=NULL,error=%s WHERE instrument_id=%s AND attempt_id=%s', (FAILURE,iid,attempt))
        raise ValueError(FAILURE if purpose == 'targets' else 'Public financial forecasts could not be refreshed. Earlier data is retained; no automatic retry.') from None
