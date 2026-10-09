"""Read-time amendment resolution from retained, permission-checked evidence.

No issuer allowlist, historical rewrite, new cross-accession arithmetic or network.
Unknown wording/unsupported tables never authorize carrying older figures forward.
"""
from copy import deepcopy
from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re

from thesis.db import one, rows
from .normalize import filing_rows
from .disclosure_text import FilingHTML, archive_url, METHOD as TEXT_METHOD

METHOD = 'sec-amendment-resolution-1'
MAX_CHAIN = 8
META = ('period_type', 'accession', 'form', 'period_end', 'published_at', 'filed_on', 'filing_url')


class Tables(FilingHTML):
    """Visible table cells only; use the original reader's hidden/script policy."""
    def __init__(self):
        super().__init__()
        self.active = []
        self.tables = []

    def handle_starttag(self, tag, attrs):
        super().handle_starttag(tag, attrs)
        if self.ignored:
            return
        if tag == 'table':
            self.active.append(dict(rows=[], cells=None, cell=None))
        if self.active:
            table = self.active[-1]
            if tag == 'tr': table['cells'] = []
            if tag in ('td', 'th') and table['cells'] is not None:
                table['cell'] = []
                table['cells'].append(table['cell'])

    def handle_data(self, text):
        super().handle_data(text)
        if not self.ignored and self.active and self.active[-1]['cell'] is not None:
            self.active[-1]['cell'].append(text)

    def handle_endtag(self, tag):
        if not self.ignored and self.active:
            table = self.active[-1]
            if tag in ('td', 'th'): table['cell'] = None
            if tag == 'tr' and table['cells'] is not None:
                table['rows'].append([re.sub(r'\s+', ' ', ''.join(cell)).strip() for cell in table['cells']])
                table['cells'] = table['cell'] = None
            if tag == 'table':
                self.tables.append(self.active.pop()['rows'])
        super().handle_endtag(tag)


def note_evidence(document):
    body = document['data']['body']
    match = re.search(r'(?im)^explanatory\s+note\s*$', body)
    if not match:
        return None
    end = re.search(r'(?im)^(?:part\s+[ivx]+|item\s+\d|signatures)\b', body[match.end():])
    stop = match.end() + end.start() if end else len(body)
    note = body[match.end():stop].strip()
    if len(note) > 8000 or not note:
        return None
    # Even a boilerplate unchanged sentence cannot clear an identified restatement.
    if re.search(r'restat|non.reliance|no longer.{0,30}relied|material (?:error|misstatement)', note, re.I):
        return None
    sentences = re.split(r'(?<=[.!?])\s+', note)
    for sentence in sentences:
        if not re.match(r'(?:this amendment(?: no\.?\s*\d+)?|this amended (?:annual|quarterly) report|no changes (?:have been|are|were) made)\b', sentence, re.I):
            continue
        if re.search(r'\b(?:except|unless|other than|excepting|subsequent|to reflect|for events|otherwise|if|pending|proposed|will)\b', sentence, re.I):
            continue
        # Do not mistake "unchanged for 2024" or "unchanged except ..." for an
        # unconditional statement about this filing's financial statements.
        if not re.search(r'\bfinancial statements(?:\s+(?:and|or)\s+(?:the |related |accompanying )*notes(?: thereto)?)?[.!]?$', sentence, re.I):
            continue
        if re.search(r'\b(?:does not|do not) (?:amend|modify|change|revise|update)(?:,?\s+(?:or|and)?\s*(?:amend|modify|change|revise|update))* (?:any of |the |our |its )*(?:consolidated )?financial statements\b', sentence, re.I) or re.search(r'\bno changes (?:have been|are|were) made to (?:the |our |its )*(?:consolidated )?financial statements\b', sentence, re.I):
            start = body.index(sentence, match.end())
            return dict(kind='unchanged_statements', quote=sentence, start=start, end=start + len(sentence))
    return None


def date_pattern(value):
    d = date.fromisoformat(value)
    return rf'{d.strftime("%B")}\s+0?{d.day}\s*,?\s*{d.year}'


def repeated_totals(document, report):
    """Only exact USD totals in simple two-column, explicitly dated period tables."""
    metrics = {m['key']: m for m in report['metrics']}
    revenue = metrics['revenue']
    prior = revenue.get('prior')
    if not prior or revenue['value'] is None:
        return {}
    raw = bytes(document['raw_html']).decode('utf-8-sig')
    currencies = set(re.findall(r'<(?:\w+:)?measure\b[^>]*>\s*iso4217:(\w+)\s*</', raw, re.I))
    if currencies != {'USD'}:
        return {}
    parser = Tables()
    parser.feed(raw)
    parser.close()
    matches = {'revenue': [], 'operating_income': []}
    period = r'years?\s+ended' if report['period_type'] == 'annual' else r'three\s+months\s+ended'
    for index, table in enumerate(parser.tables):
        header = ' '.join(' '.join(row) for row in table[:8])
        if re.search(r'previously reported|originally reported|before restatement', header, re.I):
            continue
        dates = [re.search(date_pattern(v), header, re.I) for v in (revenue['end'], prior['end'])]
        if not all(dates) or dates[0].start() >= dates[1].start() or not re.search(period, header, re.I):
            continue
        if re.search(r'\b(?:six|nine|twelve)\s+months\s+ended', header, re.I) and report['period_type'] == 'quarter':
            continue
        units = re.findall(r'\bin (millions|thousands)\b', header, re.I)
        if len(set(u.lower() for u in units)) != 1 or re.search(r'€|£|CAD|AUD|Canadian|Australian|euros', header, re.I):
            continue
        factor = Decimal(1000000 if units[0].lower() == 'millions' else 1000)
        for row in table:
            cells = [cell for cell in row if cell]
            if not cells:
                continue
            label = re.sub(r'[:\s]+$', '', cells[0]).lower()
            key = 'revenue' if label in ('total net revenue', 'total revenue', 'total revenues', 'total net sales') else 'operating_income' if label in ('total operating income', 'total operating income (loss)', 'total income from operations') else None
            if not key or not any('$' in cell for cell in cells[1:]):
                continue
            text = ' '.join(cells[1:]).replace('$', '').strip()
            if re.search(r'[^\d\s,().\-]', text):
                continue
            tokens = re.findall(r'\(?-?\d[\d,]*(?:\.\d+)?\)?', text)
            if len(tokens) != 2:
                continue
            try:
                values = [Decimal(t.replace(',', '').replace('(', '-').replace(')', '')) * factor for t in tokens]
            except InvalidOperation:
                continue
            matches[key].append((values, dict(kind='repeated_table', table=index, header=header, row=' | '.join(cells))))
    result = {}
    for key, entries in matches.items():
        candidate = metrics[key]
        comparison = candidate.get('prior')
        if candidate['value'] is None or not comparison or not entries:
            continue
        expected = [Decimal(candidate['value']), Decimal(comparison['value'])]
        if all(values == expected for values, _ in entries):
            result[key] = entries[0][1]
    return result


class Resolver:
    def __init__(self, bundle, cik, now, documents, documents_allowed=True):
        if any(str(bundle[k].get('cik')).lstrip('0') != str(cik) for k in ('submissions', 'companyfacts')):
            raise ValueError('Amendment evidence belongs to another issuer.')
        self.bundle, self.cik, self.now, self.documents = bundle, cik, now, documents
        self.documents_allowed = documents_allowed
        self.basis_id = hashlib.sha256(json.dumps({a: (str(d['id']),d['content_hash']) for a,d in documents.items()},sort_keys=True).encode()).hexdigest()
        self.filings = filing_rows(bundle['submissions'], now)
        self.cache = {}
        self.proofs = {}

    def report(self, filing):
        from .performance import normalize_performance
        accession = filing['accessionNumber']
        if accession not in self.cache:
            selected = dict(self.bundle, submissions=deepcopy(self.bundle['submissions']))
            recent = selected['submissions']['filings']['recent']
            i = recent['accessionNumber'].index(accession)
            selected['submissions']['filings']['recent'] = {k: [v[i]] for k, v in recent.items()}
            kind = 'annual' if filing['form'].startswith('10-K') else 'quarter'
            self.cache[accession] = normalize_performance(selected, self.cik, self.now)['reports'][kind]
        return self.cache[accession]

    def chain(self, filing):
        chain = [f for f in self.filings if f['form'].removesuffix('/A') == filing['form'].removesuffix('/A') and f['end'] == filing['end'] and f['accepted_at'] <= filing['accepted_at']]
        if not chain or len(chain) > MAX_CHAIN or chain[0]['form'].endswith('/A') or any(not f['form'].endswith('/A') for f in chain[1:]):
            return []
        return chain if chain[-1]['accessionNumber'] == filing['accessionNumber'] else []

    def document(self, filing):
        try:
            return self._document(filing)
        except (ValueError, KeyError, TypeError, UnicodeError):
            return None

    def _document(self, filing):
        doc = self.documents.get(filing['accessionNumber'])
        if not doc or doc['form'] != filing['form'] or doc['url'] != archive_url(self.cik, filing['accessionNumber'], filing['primaryDocument']):
            return None
        data = doc['data']
        if data.get('method') != TEXT_METHOD or data.get('report_period_end') != filing['end'].isoformat():
            return None
        if str(doc['published_at']) != str(filing['accepted_at']):
            # Datetime timezone representations may differ; compare actual instants.
            from datetime import datetime
            if datetime.fromisoformat(str(doc['published_at'])) != filing['accepted_at']:
                return None
        if hashlib.sha256(bytes(doc['raw_html'])).hexdigest() != doc['content_hash'] or hashlib.sha256(data['body'].encode()).hexdigest() != data['text_hash']:
            return None
        return doc

    def conflicts(self, amendment, metric):
        # Contradictory, foreign-currency or conflicting amended inputs cannot be
        # masked with an older figure, regardless of the explanatory note.
        evidence = metric.get('inputs', []) + ([metric['prior']] if metric.get('prior') else [])
        for fact in evidence:
            units = self.bundle['companyfacts'].get('facts', {}).get(fact['namespace'], {}).get(fact['concept'], {}).get('units', {})
            for unit, values in units.items():
                for row in values:
                    if row.get('accn') != amendment['accessionNumber'] or row.get('end') != fact['end']:
                        continue
                    if row.get('start') != fact.get('start'):
                        continue
                    if unit != fact['unit'] or Decimal(str(row['val'])) != Decimal(fact['value']):
                        return True
        return False

    def proof(self, amendment, ancestor, metric):
        doc = self.document(amendment)
        if not doc or self.conflicts(amendment, metric):
            return None
        cache_key = (amendment['accessionNumber'], ancestor['accessionNumber'])
        if cache_key not in self.proofs:
            report = self.report(ancestor)
            note = note_evidence(doc)
            if note and any(self.conflicts(amendment, m) for m in report['metrics']):
                note = None
            self.proofs[cache_key] = (note, repeated_totals(doc, report))
        note, totals = self.proofs[cache_key]
        standard = next((m for m in self.report(ancestor)['metrics'] if m['key'] == metric['key']), None)
        if not standard or any(metric.get(k) != standard.get(k) for k in ('value', 'start', 'end')):
            totals = {}  # A direct-quarter table cannot validate a trailing/YTD total.
        support = []
        if note:
            support = [note]
        elif metric['key'] in ('revenue', 'revenue_growth') and 'revenue' in totals:
            support = [totals['revenue']]
        elif metric['key'] == 'operating_margin' and len(totals) == 2:
            support = list(totals.values())
        elif metric['key'] == 'operating_income' and 'operating_income' in totals:
            support = [totals['operating_income']]
        if not support:
            return None
        return dict(accession=amendment['accessionNumber'], form=amendment['form'], url=doc['url'], document_id=str(doc['id']), content_hash=doc['content_hash'], available_at=doc['available_at'], support=support)

    def resolve(self, filing, metrics, builder=None):
        if not filing['form'].endswith('/A'):
            return metrics, None
        chain = self.chain(filing)
        result = deepcopy(metrics)
        inherited, revised, unresolved = [], [], []
        missing_docs = []
        for row in result:
            if row['value'] is not None:
                revised.append(row['key'])
                row['filing_resolution'] = dict(status='amended', message='Reported in the amended filing.', source_url=archive_url(self.cik, filing['accessionNumber'], filing['primaryDocument']), amendments=[])
                continue
            proofs = []
            # Unknown/conflicting current inputs never acquire an older value.
            if not re.search(r'conflict|unsupported|outside|denominator|different|negative|invalid|precision|unusable|not applied', row.get('reason') or '', re.I):
                for i in range(len(chain) - 2, -1, -1):
                    ancestor = chain[i]
                    report = self.report(ancestor)
                    candidate_rows = builder(ancestor) if builder else report['metrics']
                    candidate = next((m for m in candidate_rows if m['key'] == row['key']), None)
                    if not candidate or candidate['value'] is None:
                        continue
                    try:
                        proofs = [self.proof(later, ancestor, candidate) for later in chain[i + 1:]]
                    except (ValueError, KeyError, TypeError, UnicodeError, InvalidOperation):
                        proofs = [None]
                    if all(proofs):
                        row.update(deepcopy(candidate))
                        row['source_report'] = {key: report[key] for key in META}
                        for fact in row.get('inputs', []) + ([row['prior']] if row.get('prior') else []):
                            fact_filing = next((f for f in self.filings if f['accessionNumber'] == fact['accession']), None)
                            if fact_filing:
                                fact['filing_url'] = self.report(fact_filing)['filing_url']
                        row['filing_resolution'] = dict(status='retained', message='Earlier filing figures retained: later amendments explicitly leave the financial statements unchanged or repeat these exact dated totals.', source_url=report['filing_url'], amendments=proofs)
                        inherited.append(row['key'])
                        break
            if row['value'] is None:
                unresolved.append(row['key'])
                missing_docs = [f['accessionNumber'] for f in chain[1:] if not self.document(f)]
                message = 'Amendment scope is unclear; an earlier figure cannot be confirmed unchanged.'
                if not chain: message = 'The complete original-and-amendment chain is unavailable.'
                elif not self.documents_allowed: message = 'Original-filing access is unavailable; earlier figures are withheld.'
                elif missing_docs: message = 'Amendment text is missing or unavailable. Check original filings to establish whether earlier figures remain valid.'
                row['reason'] = message + ' ' + (row.get('reason') or '')
                row['filing_resolution'] = dict(status='unresolved', message=message, amendments=[])
        summary = dict(method=METHOD, retained=inherited, amended=revised, unresolved=unresolved, needs_documents=bool(missing_docs) and self.documents_allowed, missing_documents=missing_docs,
                       message='Amendment checked: each figure keeps its own filing and evidence.' if inherited or revised else 'Amendment needs evidence before earlier figures can be used.')
        return result, summary


def retained_resolver(conn, iid, bundle, cik, now):
    documents = {}
    allowed = bool(one(conn, "SELECT 1 FROM sources WHERE id='sec-disclosures' AND entitlement='sec-public'"))
    if allowed:
        records = rows(conn, "SELECT DISTINCT ON (accession) id,accession,form,url,published_at,available_at,content_hash,raw_html,data FROM disclosure_documents WHERE instrument_id=%s AND form IN ('10-K/A','10-Q/A') ORDER BY accession,available_at DESC,id DESC", (iid,))
        for doc in records:
            documents[doc['accession']] = doc
    return Resolver(bundle, cik, now, documents,allowed)


def combined_evidence(*metrics):
    evidence = [m['filing_resolution'] for m in metrics if m.get('filing_resolution', {}).get('status') == 'retained']
    if not evidence:
        return {}
    amendments = {}
    for entry in evidence:
        for amendment in entry['amendments']:
            saved = amendments.setdefault(amendment['document_id'], dict(amendment, support=[]))
            for support in amendment['support']:
                if support not in saved['support']:
                    saved['support'].append(support)
    return dict(filing_resolution=dict(status='retained', message='Inputs include earlier filing figures confirmed unchanged by later amendments.', amendments=list(amendments.values())))


def present(conn, iid, source):
    amended = [r for r in source.get('reports', {}).values() if r and r['form'].endswith('/A')]
    if source.get('status') != 'available' or not amended:
        return source
    saved = one(conn, 'SELECT p.payload,p.retrieved_at,c.cik FROM source_payloads p JOIN sec_companies c ON c.instrument_id=p.instrument_id WHERE p.id=%s AND p.instrument_id=%s', (source['payload_id'], iid))
    if not saved:
        return source
    resolver = retained_resolver(conn, iid, saved['payload'], saved['cik'], saved['retrieved_at'])
    result = deepcopy(source)
    for report in result['reports'].values():
        if not report or not report['form'].endswith('/A'):
            continue
        filing = next((f for f in resolver.filings if f['accessionNumber'] == report['accession']), None)
        if filing:
            report['metrics'], report['amendment_resolution'] = resolver.resolve(filing, report['metrics'])
    result['projection_method'] = METHOD
    result['based_on_snapshot_id'], result['snapshot_id'] = result['snapshot_id'], None
    result['projection_id'] = hashlib.sha256(json.dumps(result, default=str, sort_keys=True).encode()).hexdigest()
    # Persisted valuation cases still require the unmodified snapshot and cannot
    # treat a current read-time projection as that historical calculation base.
    result['recorded_basis'] = deepcopy(source)
    return result
