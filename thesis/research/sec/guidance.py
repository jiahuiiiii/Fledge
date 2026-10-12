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
from . import guidance_formats as formats

METHOD = 'sec-management-outlook-3'
MONTHS = 'January February March April May June July August September October November December'.split()
DATE = r'(?:' + '|'.join(MONTHS) + r') \d{1,2},? \d{4}'
HEADING = re.compile(r'^(?:(?:first|second|third|fourth|Q[1-4]|full|fiscal|year|quarter|202\d|203\d|[ /–—-])\s*)*(?:(?:business|financial)\s+)?(?:outlook|guidance)(?: for [\w ,/–—-]+)?$', re.I)
PERIOD = r'(?:(?:(?:first|second|third|fourth) quarter|full year|fiscal year)(?: (?:of )?fiscal year)?(?: 20\d{2})?\s+)'
NUMBER = r'\d{1,6}(?:\.\d{1,6})?'
MONEY = re.compile(r'^(?:' + PERIOD + r')?(?:consolidated )?(?:(?P<basis>non-GAAP|GAAP|adjusted) )?revenue (?:guidance|outlook)(?: (?:of|is|at)|:)\s+(?P<approx>approximately |about )?(?P<currency>US\$|USD\s*|\$)(?P<low>' + NUMBER + r')(?:\s*(?:to|–|-)\s*(?:US\$|USD\s*|\$)?(?P<high>' + NUMBER + r'))? (?P<scale>million|billion)[;.]?$', re.I)
MARGIN = re.compile(r'^(?:' + PERIOD + r')?(?P<basis>non-GAAP|GAAP|adjusted) operating (?:income|margin) (?:guidance|outlook)(?: (?:of|is|at)|:)\s+(?P<approx>approximately |about )?(?P<low>' + NUMBER + r')(?:\s*(?:to|–|-)\s*(?P<high>' + NUMBER + r'))? (?:percent|%)(?: of (?:projected |expected )?revenue)?[;.]?$', re.I)
LIMITATIONS = [
    'Management guidance is the company’s own outlook, separate from analyst consensus and reported results.',
    'This reader supports whole-company revenue statements and bounded guidance tables. Unsupported layouts and segment-only forecasts remain explicit gaps.',
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
    """Read explicit outlook sections, keeping exact original passage evidence."""
    data = record['data']
    body, passages = data['body'], data['passages']
    if not isinstance(body, str) or len(body) > 2_000_000 or len(passages) > 40_000:
        raise ValueError('Unsupported release size.')
    if any(body[p['start']:p['end']] != p['quote'] for p in passages):
        raise ValueError('The saved release contains inconsistent passage offsets.')
    names=[record.get('company_name',''),record.get('symbol','')]
    sections=[]
    for i, heading in enumerate(passages):
        prefix=[]
        if formats.DATE_HEADING.fullmatch(heading['quote']):
            parent=next((j for j in range(i-1,max(-1,i-18),-1) if formats.HEAD.fullmatch(passages[j]['quote'])),None)
            if parent is None or any(formats.STOP.fullmatch(p['quote']) for p in passages[parent+1:i]):continue
            prefix.extend(p for p in passages[max(0,parent-3):parent] if re.search(r'in (?:millions|billions|thousands)',p['quote'],re.I))
            for p in passages[parent:i]:
                if formats.DATE_HEADING.fullmatch(p['quote']):break
                prefix.append(p)
        elif len(heading['quote'])>140 or not formats.HEAD.fullmatch(heading['quote']):continue
        else:
            # Nested outlook/reconciliation headings can supply scale and fiscal
            # label; only the bounded adjacent heading block is inherited.
            parent=next((j for j in range(i-1,max(-1,i-5),-1) if formats.HEAD.fullmatch(passages[j]['quote'])),None)
            if heading['quote'].lower().startswith('outlook for three months') and parent is not None and all(not re.search(r'\$|revenues?\b',p['quote'],re.I) for p in passages[parent:i]):prefix=passages[parent:i]
        chosen=[];characters=0;truncated=False
        for item in passages[i+1:]:
            text=item['quote']
            if text.isdigit():continue
            if len(text)<200 and (formats.HEAD.fullmatch(text) or formats.DATE_HEADING.fullmatch(text) or formats.STOP.fullmatch(text)):break
            if len(chosen)>=60 or characters+len(text)>16000:
                truncated=True;break
            chosen.append(item);characters+=len(text)
        if not chosen:continue
        forecasts=[];first_metric=None
        for j,p in enumerate(chosen):
            text=p['quote']
            table=formats.table_forecast(chosen,j,prefix)
            f=table or formats.prose(text,names)
            if not f['metric']:
                old=typed(text)
                if old['metric']:f=old
            if table or (re.search(r'\b(?:guidance|outlook|expect(?:s|ed)?|project(?:s|ed)?|anticipate(?:s|d)?)\b',text,re.I) and re.search(r'\d|\$|%',text) and re.search(r'\b(?:revenues?|net sales|income|margin|EPS|earnings|cash flow)\b',text,re.I)):
                evidence=f.pop('evidence', [p])
                # Quote is a contiguous original slice, including split rows.
                quote=body[evidence[0]['start']:evidence[-1]['end']]
                forecasts.append(dict(p,**f,quote=quote,end=evidence[-1]['end'],evidence=evidence))
                if first_metric is None:first_metric=j
        if not forecasts:continue
        # Metric-specific periods may live in the first sentence. Do not take
        # annual tax-rate horizons or later unrelated metrics as revenue dates.
        lead=chosen[:first_metric if first_metric is not None else 2]
        first_revenue=next((f for f in forecasts if f['metric']=='revenue'),forecasts[0])
        context='\n'.join(p['quote'] for p in prefix)+'\n'+heading['quote']+'\n'+'\n'.join(p['quote'] for p in lead)
        first_sentence,comparison_review=(formats.forecast_context(first_revenue['quote'],context) if first_revenue['metric']=='revenue' else (formats.first_sentence(first_revenue['quote']),False))
        context+='\n'+first_sentence
        metadata=formats.period(context)
        ends=set()
        for value in re.findall(r'\b(?:ending|ended)\s+('+DATE+r')\b',context,re.I):
            try:ends.add(calendar(value))
            except ValueError:pass
        review=bool(re.search(r'\b(?:withdraw\w*|suspend\w*|previous guidance|prior guidance|no longer provid\w*.{0,30}guidance|not provid\w*.{0,30}guidance)\b','\n'.join(p['quote'] for p in chosen),re.I))
        values={(f['low'],f['high'],f['unit']) for f in forecasts if f['metric']=='revenue'}
        review_message='This section refers to earlier or withdrawn guidance. Read the original context.' if review else None
        if comparison_review:review=True;review_message='The comparison period could not be confirmed as earlier than the forecast. Read the original wording.'
        if len(values)>1:review=True;review_message='This section contains different revenue ranges. Read the original context before choosing a figure.'
        if metadata['period_conflict']:review=True;review_message='More than one forecast period is mentioned. A single period could not be identified reliably.'
        sections.append(dict(id=heading['id'],heading=heading['quote'],heading_evidence=heading,
            **metadata,period_end=next(iter(ends)) if len(ends)==1 and not metadata['period_conflict'] else None,
            review_status=review,review_message=review_message,forecasts=forecasts,passages=chosen,context_evidence=prefix,truncated=truncated))
        if len(sections)>=12:break
    # Repeated reconciliation tables remain evidence but must not produce a
    # second, conflicting display point for the identical stated forecast.
    for section in sections:
        if section['period_end'] or section['review_status'] or section['period_conflict']:continue
        numeric={(f['low'],f['high'],f['unit']) for f in section['forecasts'] if f['metric']=='revenue'}
        matches=[s for s in sections if s is not section and s['period_type']==section['period_type'] and s['period_end']
                 and not s['review_status'] and not s['period_conflict'] and not s['truncated']
                 and numeric and numeric=={(f['low'],f['high'],f['unit']) for f in s['forecasts'] if f['metric']=='revenue'}]
        ends={s['period_end'] for s in matches}
        # Quarter/year labels must not contradict the reconciliation's named period.
        matches=[s for s in matches if not s.get('period_label') or s['period_label']==section.get('period_label')]
        peers=[s for s in sections if s is not section and not s['period_end'] and s['period_type']==section['period_type'] and s.get('period_label')!=section.get('period_label') and numeric=={(f['low'],f['high'],f['unit']) for f in s['forecasts'] if f['metric']=='revenue'}]
        if len(ends)==1 and matches and not peers:
            section['period_end']=next(iter(ends))
            section['period_evidence']=[dict(heading=s['heading_evidence'],passages=s['passages'],context=s['context_evidence']) for s in matches]
    unique=[]
    for section in sections:
        revenues=[f for f in section['forecasts'] if f['metric']=='revenue']
        identity=(section.get('period_label'),section.get('period_end'),tuple(sorted({(f['low'],f['high'],f['unit']) for f in revenues},key=str)))
        if revenues and identity[0] and any(s.get('_identity')==identity for s in unique):continue
        if revenues and any(s['period_type']==section['period_type'] and s['period_end'] and s['period_end']==section['period_end'] and s.get('_identity',())[2]==identity[2] for s in unique):continue
        section['_identity']=identity;unique.append(section)
    for section in unique:section.pop('_identity')
    datelines=[]
    for p in passages:
        if p['start']>6000:break
        found=re.search(r'[–—]\s*('+DATE+r')\s*[–—]',p['quote'],re.I)
        if found:
            try:
                value=calendar(found[1])
                if value<=timestamp(record['published_at']).date().isoformat():datelines.append(dict(date=value,**p))
            except ValueError:pass
    stated_date=datelines[0] if len({d['date'] for d in datelines})==1 else None
    return dict(method=METHOD,sections=unique,stated_release_date=stated_date)


def availability(releases, source, today=None):
    """Reasons for the current overview; saved historical readings stay readable."""
    today=today or datetime.now(timezone.utc).date().isoformat()
    def result(code,message):return dict(code=code,message=message)
    if source.get('status')=='unavailable':return result('source_unavailable',source['message'])
    current=[r for r in releases if r['current']]
    if not current:
        state=source.get('source_status') or {}
        if state.get('last_error'):return result('collection_failed','The latest earnings-release check failed. Saved older releases remain available; use Update data to try again.')
        coverage=state.get('coverage') or []
        missing=next((c for c in coverage if c.get('slot','').startswith('earnings_release') and c['status']!='available'),None)
        return result('release_missing',('The results filing is saved, but its linked earnings release has not been collected. Use Update data.' if missing else 'No current earnings release is saved. Use Update data to collect it.'))
    if any(r.get('read_error') for r in current):return result('extraction_failed','The saved release could not be read reliably. Open the original release or use Update data to check the source.')
    sections=[s for r in current for s in r['sections']]
    numeric=[s for s in sections if any(f['metric']=='revenue' for f in s['forecasts'])]
    usable=[s for s in numeric if not s['review_status'] and not s['truncated'] and not s.get('period_conflict')]
    if any(s['period_end'] and s['period_end']>=today for s in usable):return result('available','Revenue guidance is available from the latest saved earnings release.')
    if any(not s['period_end'] and s.get('period_label') for s in usable):return result('named_period','The latest release gives revenue guidance for a named fiscal period, but no exact ending date. Read the stated period before treating it as current.')
    if usable and all(s['period_end'] and s['period_end']<today for s in usable):return result('expired','The latest saved revenue guidance covers a period that has ended. It remains available as historical guidance.')
    if numeric:return result('needs_review','Revenue guidance was found, but its period, withdrawal wording or incomplete context needs review. Read the original wording below.')
    if any(f['metric']=='revenue_growth' for s in sections for f in s['forecasts']):return result('growth_only','The latest release gives a revenue growth rate, but no whole-company revenue amount. Read the percentage guidance below.')
    if sections:return result('unsupported_format','An outlook was found, but a whole-company revenue amount could not be extracted reliably. Read the original wording below.')
    return result('not_in_release','No numerical revenue outlook was found in the saved earnings release. Guidance given only in earnings calls or other documents is not covered here.')


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
        return dict(status='unavailable', message=source['message'], releases=[], availability=availability([],source), limitations=LIMITATIONS)
    current = {str(d['id']) for d in source['documents'] if d['slot'].startswith('earnings_release')}
    # Historical releases require their retained parent results filing. A stale
    # current exhibit is not relabeled as the latest company's outlook.
    records = rows(conn, """SELECT d.id,d.accession,d.url,d.headline,d.published_at,d.available_at,d.data,i.name company_name,i.symbol
      FROM disclosure_documents d JOIN instruments i ON i.id=d.instrument_id WHERE d.instrument_id=%s AND d.form='earnings-release'
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
            extracted = dict(method=METHOD, sections=[], stated_release_date=None, read_error=True)
        release = {k: v for k, v in item.items() if k != 'data'}
        release.update(extracted, current=str(item['id']) in current)
        for section in release['sections']:
            for forecast in section['forecasts']:
                forecast['comparison'] = compare(forecast, section, release, actuals)
        releases.append(release)
    return dict(status='available' if releases else 'empty', method=METHOD, releases=releases,
                history_limited=len(records) > 20, source_status=source.get('source_status'), availability=availability(releases,source),
                message='Read the dated outlook from saved original earnings releases. Unrecognized sections remain in the original document.', limitations=LIMITATIONS)
