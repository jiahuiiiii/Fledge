"""Visible annual forecasts from the same bounded page as analyst targets.

There is deliberately no independent fetcher, request clock or hidden-data reader.
Original pages/observations are immutable; forecast currency is never inferred
from the stock quote's currency. Pro/Upgrade cells stay unavailable.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from html.parser import HTMLParser
import re
from thesis.db import one, rows
from .sec.performance import decimal_text

SOURCE = 'stockanalysis-forecasts'
METHOD = 'stockanalysis-visible-financial-forecasts-1'
LIMITATION = ('Limited public annual forecasts, not management guidance or reported results. '
              'EPS uses non-GAAP adjusted earnings. Forecast currency and per-metric contributor counts '
              'are not established. Observation time is not a verified pre-release vintage.')


class PublicTables(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.parts = []
        self.title = []
        self.tables = []
        self.table = self.row = self.cell = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        hidden = (tag in ('script', 'style', 'noscript', 'template') or 'hidden' in attrs or
                  attrs.get('aria-hidden') == 'true' or
                  bool(re.search(r'display\s*:\s*none|visibility\s*:\s*hidden', attrs.get('style', ''), re.I)))
        skipped = hidden or bool(self.stack and self.stack[-1][1])
        if tag not in ('area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'):
            self.stack.append((tag, skipped))
        if skipped:
            return
        if tag == 'table':
            if self.table is not None:
                raise ValueError('Nested forecast tables are unsupported.')
            self.table = []
        elif self.table is not None:
            if tag == 'tr': self.row = []
            elif tag in ('td', 'th'): self.cell = []

    def handle_data(self, data):
        if self.stack and self.stack[-1][1]: return
        if data.strip(): self.parts.append(data.strip())
        if any(tag == 'title' for tag, _ in self.stack): self.title.append(data)
        if self.cell is not None: self.cell.append(data)

    def handle_endtag(self, tag):
        skipped = bool(self.stack and self.stack[-1][1])
        if not skipped:
            if tag in ('td', 'th') and self.cell is not None:
                if self.row is None: raise ValueError('Malformed forecast row.')
                self.row.append(' '.join(''.join(self.cell).split())); self.cell = None
            elif tag == 'tr' and self.row is not None:
                self.table.append(self.row); self.row = None
            elif tag == 'table' and self.table is not None:
                self.tables.append(self.table); self.table = None
        for index in range(len(self.stack)-1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]; break


def amount(text):
    match = re.fullmatch(r'(-?\d+(?:,\d{3})*(?:\.\d+)?)([BMT]?)', text)
    if not match: raise ValueError('A visible forecast value is unavailable or changed.')
    number, unit = match.groups()
    multiplier = {'': 1, 'M': 10**6, 'B': 10**9, 'T': 10**12}[unit]
    value = Decimal(number.replace(',', '')) * multiplier
    precision = Decimal(10) ** -len(number.partition('.')[2]) * multiplier
    if abs(value) > 10**16: raise ValueError('Forecast value is outside supported bounds.')
    return value, precision


def normalized(html, symbol):
    from .analyst_targets import MAX_BYTES, url
    if not isinstance(html, str) or len(html.encode()) > MAX_BYTES:
        raise ValueError('Forecast page exceeded its supported size.')
    parser = PublicTables(); parser.feed(html)
    text = re.sub(r'\s+', ' ', ' '.join(parser.parts))
    title = ''.join(parser.title)
    if f'({symbol}) Stock Forecast' not in title or not re.search(
            rf'(?:NASDAQ|NYSE|NYSEAMERICAN): {re.escape(symbol)} · [^·]{{1,45}} · USD\b', text):
        raise ValueError('Public forecast company identity could not be verified.')
    if ('financial forecasts are provided by S&P Global Market Intelligence' not in text or
            'EPS and Forward PE are based on non-GAAP adjusted numbers.' not in text):
        raise ValueError('Forecast provider or adjusted earnings convention is missing.')
    def table(label):
        matches = [t for t in parser.tables if t and t[0] and t[0][0] == label]
        if len(matches) != 1: raise ValueError('A unique visible financial forecast table is unavailable.')
        values = matches[0]
        if not 2 <= len(values[0]) <= 20 or any(len(r) != len(values[0]) for r in values):
            raise ValueError('Forecast table columns are inconsistent.')
        if len({r[0] for r in values}) != len(values): raise ValueError('Duplicate forecast rows.')
        return {r[0]: r[1:] for r in values}
    annual, revenue, eps = table('Fiscal Year'), table('Revenue'), table('EPS')
    years = revenue['Revenue']
    if years != eps['EPS'] or len(set(years)) != len(years) or not all(re.fullmatch(r'20\d\d', y) for y in years):
        raise ValueError('Revenue and EPS forecast years do not agree.')
    forecasts = []; restricted = []
    try:
        for j, year in enumerate(years):
            fiscal = 'FY '+year
            if annual['Fiscal Year'].count(fiscal) != 1: raise ValueError('Forecast fiscal year is ambiguous.')
            i = annual['Fiscal Year'].index(fiscal)
            values = [annual[key][i] for key in ('Revenue', 'EPS', 'No. Analysts')]
            values += [t[key][j] for t in (revenue, eps) for key in ('Low', 'Avg', 'High')]
            if any(v in ('Upgrade', 'Pro') for v in values):
                restricted.append(year); continue
            end = datetime.strptime(annual['Period Ending'][i], '%b %d, %Y').date()
            if abs(end.year-int(year)) > 1: raise ValueError('Forecast fiscal date is inconsistent.')
            metrics = []
            for key, label, source in [('revenue', 'Revenue', revenue), ('eps', 'EPS', eps)]:
                low, average, high = [amount(source[k][j])[0] for k in ('Low','Avg','High')]
                precise, precision = amount(annual[label][i])
                if not low <= average <= high or not low <= precise <= high:
                    raise ValueError('Public forecast range is inconsistent.')
                if abs(precise-average) > (precision+amount(source['Avg'][j])[1])/2:
                    raise ValueError('Public forecast average and annual table disagree.')
                if key == 'revenue' and low < 0: raise ValueError('Negative forecast revenue is unsupported.')
                metrics.append(dict(key=key, low=decimal_text(low), average=decimal_text(precise),
                                    high=decimal_text(high), range_average=decimal_text(average),
                                    source_display=dict(low=source['Low'][j], average=annual[label][i], high=source['High'][j]),
                                    analysts=None, basis='non-GAAP adjusted' if key=='eps' else 'source revenue convention'))
            count = annual['No. Analysts'][i]
            count = int(count) if count.isdigit() and 1 <= int(count) <= 1000 else None
            forecasts.append(dict(fiscal_year=int(year), period_end=end.isoformat(), period_type='annual',
                                  currency=None, displayed_analyst_count=count, metrics=metrics))
    except (KeyError, IndexError) as exc:
        raise ValueError('Required forecast rows are missing.') from exc
    if not forecasts: raise ValueError('No complete public annual forecast is available.')
    updated = re.search(r'Data Sources: S&P Global Market Intelligence and TipRanks Last updated: ([A-Z][a-z]{2} \d{1,2}, \d{4})', text)
    page_date = datetime.strptime(updated.group(1), '%b %d, %Y').date() if updated else None
    if page_date and page_date > datetime.now(timezone.utc).date(): raise ValueError('Future page update date.')
    return dict(symbol=symbol, forecasts=forecasts, restricted_years=restricted, method=METHOD,
                publisher='Stock Analysis', provider='S&P Global Market Intelligence', url=url(symbol),
                page_updated_on=page_date.isoformat() if page_date else None, provider_as_of=None,
                page_quote_currency='USD', limitation=LIMITATION)


def allowed(conn):
    return bool(one(conn, "SELECT 1 FROM sources WHERE id=%s AND entitlement='local-stockanalysis-forecasts'", (SOURCE,)))


def current(conn, iid):
    state = one(conn, 'SELECT last_attempt_at,lease_until,error FROM analyst_target_state WHERE instrument_id=%s', (iid,))
    next_at = state['last_attempt_at']+timedelta(days=1) if state and state['last_attempt_at'] else None
    if not allowed(conn): return dict(available=False, snapshot=None, history=[], next_check_at=next_at)
    history = rows(conn, 'SELECT id,observed_at,page_sha256,data FROM public_financial_forecasts WHERE instrument_id=%s AND data IS NOT NULL ORDER BY observed_at DESC,id DESC LIMIT 20', (iid,))
    latest = one(conn, 'SELECT error,observed_at FROM public_financial_forecasts WHERE instrument_id=%s ORDER BY observed_at DESC,id DESC LIMIT 1', (iid,))
    snapshot = history[0] if history else None
    if snapshot: snapshot = dict(snapshot, stale=datetime.now(timezone.utc)-snapshot['observed_at'] > timedelta(days=1))
    page_error = state['error'] if state and (not latest or state['last_attempt_at'] > latest['observed_at']) else None
    if state and state['lease_until'] and state['lease_until'] <= datetime.now(timezone.utc):
        page_error = 'The last public page check did not finish. Earlier forecasts are retained.'
    return dict(available=True, snapshot=snapshot, history=history, next_check_at=next_at,
                error=page_error or (latest['error'] if latest else None),
                limitation=LIMITATION)
