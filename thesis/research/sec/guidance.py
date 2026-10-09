"""Conservative, read-only management outlook from immutable original releases.

No model, network, new source allowance or inferred accounting definitions.
Unrecognized prose remains an excerpt; only the explicit grammar below yields
typed numbers. Historical releases and actuals keep their original identities.
"""
from datetime import date, datetime, timezone
from decimal import Decimal
import re

from thesis.db import one, rows
from .disclosures import SOURCE, present as disclosures_present
from .performance import decimal_text
from .normalize import REVENUE

METHOD = 'sec-management-outlook-1'
MONTHS = 'January February March April May June July August September October November December'.split()
DATE = r'(?:' + '|'.join(MONTHS) + r') \d{1,2},? \d{4}'
HEADING = re.compile(r'^(?:(?:first|second|third|fourth|Q[1-4]|full|fiscal|year|quarter|202\d|203\d|[ /–—-])\s*)*(?:(?:business|financial)\s+)?(?:outlook|guidance)(?: for [\w ,/–—-]+)?$', re.I)
PERIOD = r'(?:(?:(?:first|second|third|fourth) quarter|full year|fiscal year)(?: (?:of )?fiscal year)?(?: 20\d{2})?\s+)'
NUMBER = r'\d{1,6}(?:\.\d{1,6})?'
MONEY = re.compile(r'^(?:' + PERIOD + r')?(?:consolidated )?(?:(?P<basis>non-GAAP|GAAP|adjusted) )?revenue (?:guidance|outlook)(?: (?:of|is|at)|:)\s+(?P<approx>approximately |about )?(?P<currency>US\$|USD\s*|\$)(?P<low>' + NUMBER + r')(?:\s*(?:to|–|-)\s*(?:US\$|USD\s*|\$)?(?P<high>' + NUMBER + r'))? (?P<scale>million|billion)[;.]?$', re.I)
MARGIN = re.compile(r'^(?:' + PERIOD + r')?(?P<basis>non-GAAP|GAAP|adjusted) operating (?:income|margin) (?:guidance|outlook)(?: (?:of|is|at)|:)\s+(?P<approx>approximately |about )?(?P<low>' + NUMBER + r')(?:\s*(?:to|–|-)\s*(?P<high>' + NUMBER + r'))? (?:percent|%)(?: of (?:projected |expected )?revenue)?[;.]?$', re.I)
LIMITATIONS = [
    'Management guidance is the company’s own outlook, separate from analyst consensus and reported results.',
    'This bounded reader recognizes selected prose outlook sections. Tables, complex ranges, segment forecasts and other wording may require the original release.',
    'A dollar sign alone does not establish currency. An unlabeled revenue forecast does not establish GAAP accounting.',
    'Comparisons use retained SEC filing results, not necessarily the earliest earnings announcement. No alert or research condition is created.',
]


def timestamp(value):
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('A source timestamp needs a timezone.')
    return parsed.astimezone(timezone.utc)


def calendar(value):
    return datetime.strptime(value.replace(',', ''), '%B %d %Y').date().isoformat()


def typed(quote):
    text = quote.lstrip('•*- ').strip()
    match = MONEY.fullmatch(text) or MARGIN.fullmatch(text)
    if not match:
        return dict(metric=None, label='Company outlook', low=None, high=None, unit=None, basis=None, approximate=False)
    money = match.re is MONEY
    scale = Decimal(10) ** (9 if match['scale'].lower() == 'billion' else 6) if money else Decimal(1)
    low = Decimal(match['low']) * scale
    high = Decimal(match['high']) * scale if match['high'] else low
    if high < low or (not money and high > 100):
        return dict(metric=None, label='Company outlook', low=None, high=None, unit=None, basis=None, approximate=False)
    basis = match['basis'].lower() if match['basis'] else None
    return dict(metric='revenue' if money else 'operating_margin', label='Revenue' if money else 'Operating income as a share of revenue',
                low=decimal_text(low), high=decimal_text(high),
                unit=('USD' if match['currency'].upper().startswith(('US$', 'USD')) else None) if money else 'percent',
                basis=basis, approximate=bool(match['approx']))


def extract(record):
    """Exact source-offset excerpts, with no fallback from nearby actual results."""
    data = record['data']
    body, passages = data['body'], data['passages']
    if not isinstance(body, str) or len(body) > 2_000_000 or len(passages) > 40_000:
        raise ValueError('Unsupported release size.')
    if any(body[p['start']:p['end']] != p['quote'] for p in passages):
        raise ValueError('The saved release contains inconsistent passage offsets.')
    sections = []
    for i, passage in enumerate(passages):
        if len(passage['quote']) > 140 or not HEADING.fullmatch(passage['quote']):
            continue
        chosen, characters, truncated = [], 0, False
        for item in passages[i + 1:]:
            text = item['quote']
            if text.isdigit():
                continue  # Printed page number, not a guidance statement.
            # Stop at a short following heading, preserving complete sentences
            # and bullet statements. Table fragments remain unsupported.
            if len(text) < 100 and not re.search(r'[.;:]$|^[•*\-]|[|%$]|\b(?:guidance|outlook|expected|expect|will|ending)\b', text, re.I):
                break
            if len(chosen) == 14 or characters + len(text) > 7000:
                truncated = True
                break
            chosen.append(item)
            characters += len(text)
        if not chosen:
            continue
        # Period metadata comes only from the heading and opening context,
        # before the first metric. Two periods cannot be silently collapsed.
        lead = []
        for p in chosen:
            if re.search(r'^[•*\-]|\b(?:revenue|operating income|earnings per share) (?:guidance|outlook)\b', p['quote'], re.I):
                break
            lead.append(p['quote'])
        context = passage['quote'] + '\n' + '\n'.join(lead[:2])
        ends = set()
        for value in re.findall(r'\bending\s+(' + DATE + r')\b', context, re.I):
            try:
                ends.add(calendar(value))
            except ValueError:
                pass
        quarter = bool(re.search(r'\bquarter\b|\bQ[1-4]\b', context, re.I))
        annual = bool(re.search(r'\bfull year\b|\byear ending\b', context, re.I))
        period_type = 'quarter' if quarter and not annual else 'annual' if annual and not quarter else None
        forecasts = []
        for p in chosen:
            text = p['quote']
            if re.search(r'\b(?:guidance|outlook|expect(?:s|ed)?|project(?:s|ed)?)\b', text, re.I) and re.search(r'\d|\$|%', text) and re.search(r'\b(?:revenue|income|margin|EPS|earnings|cash flow)\b', text, re.I):
                forecasts.append(dict(p, **typed(text)))
        if forecasts:
            scope = context + '\n' + '\n'.join(f['quote'] for f in forecasts)
            quarters = {m.group(0).lower() for m in re.finditer(r'\b(?:first|second|third|fourth) quarter\b|\bQ[1-4]\b', scope, re.I)}
            quarter_names = {'q1': 'first quarter', 'q2': 'second quarter', 'q3': 'third quarter', 'q4': 'fourth quarter'}
            quarters = {quarter_names.get(q, q) for q in quarters}
            years = set(re.findall(r'\bfiscal year (20\d{2})\b', scope, re.I))
            conflicting = len(quarters) > 1 or len(years) > 1
            review_status = bool(re.search(r'\b(?:withdraw\w*|suspend\w*|previous|prior|no longer|not provid\w*)\b', '\n'.join(p['quote'] for p in chosen), re.I))
            sections.append(dict(id=passage['id'], heading=passage['quote'], heading_evidence=passage,
                                 period_end=next(iter(ends)) if len(ends) == 1 and not conflicting else None,
                                 period_type=period_type if not conflicting else None, review_status=review_status,
                                 forecasts=forecasts, passages=chosen, truncated=truncated))
        if len(sections) == 4:
            break
    datelines = []
    for p in passages:
        if p['start'] > 6000:
            break
        found = re.search(r'[–—]\s*(' + DATE + r')\s*[–—]', p['quote'], re.I)
        if found:
            try:
                value = calendar(found[1])
                if value <= timestamp(record['published_at']).date().isoformat():
                    datelines.append(dict(date=value, **p))
            except ValueError:
                pass
    stated_date = datelines[0] if len({d['date'] for d in datelines}) == 1 else None
    return dict(method=METHOD, sections=sections, stated_release_date=stated_date)


def compare(forecast, section, release, reports):
    """Compare only clearly typed pre-period-end guidance with matching GAAP facts.

    Keeping the first retained non-amended filing prevents a later restatement
    from silently replacing the original comparison. Evidence IDs stay visible.
    """
    reasons = []
    if section.get('review_status') or section.get('truncated'):
        reasons.append('The source’s guidance status or bounded context requires manual review.')
    if forecast['metric'] != 'revenue':
        reasons.append('Automatic comparison supports whole-company revenue only.')
    else:
        if forecast['basis'] != 'gaap':
            reasons.append('The outlook does not explicitly use the GAAP basis of the saved revenue results.')
        if forecast['unit'] != 'USD':
            reasons.append('A matching USD currency is not explicit in this outlook.')
    end = section['period_end']
    kind = section['period_type']
    if not end or not kind:
        reasons.append('A single supported fiscal period and ending date are not explicit.')
    elif max(timestamp(release['available_at']).date().isoformat(), timestamp(release['published_at']).date().isoformat()) >= end:
        reasons.append('This version was not both filed and saved before the forecast period ended.')
    candidates = sorted((r for r in reports if r['report']['period_end'] == end and r['report']['period_type'] == kind and not r['report']['form'].endswith('/A')),
                        key=lambda r: (timestamp(r['report']['published_at']), timestamp(r['first_recorded_at']), str(r['snapshot_id'])))
    if not candidates:
        reasons.append('No matching retained original filing result is available yet.')
    if reasons:
        return dict(status='uncompared', reasons=reasons)
    saved = candidates[0]
    report = saved['report']
    values = [m for m in report['metrics'] if m['key'] == 'revenue']
    row = values[0] if len(values) == 1 else None
    if not row or row['value'] is None or row['unit'] != 'USD' or row['end'] != end or row.get('calculated'):
        return dict(status='uncompared', reasons=['The first retained matching filing lacks a compatible reported revenue figure.'])
    inputs = row.get('inputs', [])
    if len(inputs) != 1 or inputs[0].get('unit') != 'USD' or inputs[0].get('end') != end or inputs[0].get('start') != row.get('start') or inputs[0].get('accession') != report['accession'] or inputs[0].get('value') != row['value'] or inputs[0].get('namespace') != 'us-gaap' or inputs[0].get('concept') not in REVENUE:
        return dict(status='uncompared', reasons=['The retained result does not have a single matching filing input.'])
    try:
        duration = (date.fromisoformat(end) - date.fromisoformat(row['start'])).days + 1
        actual = Decimal(row['value'])
        low, high = Decimal(forecast['low']), Decimal(forecast['high'])
        if not actual.is_finite() or not (80 <= duration <= 100 if kind == 'quarter' else 350 <= duration <= 380):
            raise ValueError()
        if timestamp(report['published_at']).date().isoformat() <= end:
            raise ValueError()
    except (ValueError, TypeError):
        return dict(status='uncompared', reasons=['The result has an incompatible duration, value or filing date.'])
    return dict(status='compared', actual=decimal_text(actual), unit='USD',
                relation='below' if actual < low else 'above' if actual > high else 'within' if low != high else 'equal',
                difference=decimal_text(actual - low) if low == high else None,
                approximate=forecast['approximate'], report=report, snapshot_id=saved['snapshot_id'],
                payload_id=saved['payload_id'], first_recorded_at=saved['first_recorded_at'], input=inputs[0])


def present(conn, iid):
    source = disclosures_present(conn, iid)
    if source['status'] == 'unavailable':
        return dict(status='unavailable', message=source['message'], releases=[], limitations=LIMITATIONS)
    current = {str(d['id']) for d in source['documents'] if d['slot'].startswith('earnings_release')}
    # Historical releases require their retained parent results filing. A stale
    # current exhibit is not relabeled as the latest company's outlook.
    records = rows(conn, """SELECT d.id,d.accession,d.url,d.headline,d.published_at,d.available_at,d.data
      FROM disclosure_documents d WHERE d.instrument_id=%s AND d.form='earnings-release'
      AND EXISTS(SELECT 1 FROM disclosure_documents p WHERE p.instrument_id=d.instrument_id AND p.accession=d.accession AND p.slot='earnings_filing')
      ORDER BY d.published_at DESC,d.available_at DESC,d.id LIMIT 21""", (iid,))
    actuals = []
    if one(conn, "SELECT 1 FROM sources WHERE id='sec-companyfacts' AND entitlement='sec-public'"):
        actuals = rows(conn, """SELECT * FROM (
          SELECT DISTINCT ON (r.key,r.value->>'period_end') p.id snapshot_id,p.payload_id,
                 p.created_at first_recorded_at,r.value report
          FROM performance_snapshots p CROSS JOIN LATERAL jsonb_each(p.data->'reports') r
          WHERE p.instrument_id=%s AND p.method=%s AND jsonb_typeof(r.value)='object'
            AND right(r.value->>'form',2)<>'/A'
          ORDER BY r.key,r.value->>'period_end',(r.value->>'published_at')::timestamptz,p.created_at,p.id
        ) first_results ORDER BY report->>'period_end' DESC LIMIT 100""", (iid, 'sec-performance-1'))
    releases = []
    for item in records[:20]:
        try:
            extracted = extract(item)
        except (ValueError, KeyError, TypeError):
            extracted = dict(method=METHOD, sections=[], stated_release_date=None)
        release = {k: v for k, v in item.items() if k != 'data'}
        release.update(extracted, current=str(item['id']) in current)
        for section in release['sections']:
            for forecast in section['forecasts']:
                forecast['comparison'] = compare(forecast, section, release, actuals)
        releases.append(release)
    return dict(status='available' if releases else 'empty', method=METHOD, releases=releases,
                history_limited=len(records) > 20, source_status=source.get('source_status'),
                message='Read the dated outlook from saved original earnings releases. Unrecognized sections remain in the original document.', limitations=LIMITATIONS)
