"""Reported revenue categories from retained Inline XBRL, without network or AI.

This bounded reader is not a general XBRL processor. It supports standard
US-GAAP revenue, a single business/product/geography axis and simple USD units. Different
dimensions, periods and concepts are never pooled; charts require reconciliation.
"""
from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, localcontext
from functools import lru_cache
import io
import re
import xml.etree.ElementTree as ET
from thesis.db import one, rows
from .normalize import REVENUE
from .performance import decimal_text
from .disclosures import SOURCE

METHOD = 'sec-segment-revenue-1'
XI = 'http://www.xbrl.org/2003/instance'
XD = 'http://xbrl.org/2006/xbrldi'
IX = 'http://www.xbrl.org/2013/inlineXBRL'
ISO = 'http://www.xbrl.org/2003/iso4217'
VOID = '{http://www.w3.org/2001/XMLSchema-instance}nil'
LIMITATIONS = [
    'These are the company’s reported categories, not standardized peer segments.',
    'Only supported single-dimension US-GAAP USD revenue facts are read. Nested dimensions, custom revenue concepts and IFRS remain outside this view.',
    'Geographies can overlap; this view does not infer a country/region hierarchy. Shipping destination, customer location and economic exposure are not interchangeable. Read the filing for its attribution basis.',
    'Category labels expand the filing’s member tags; they are not independently verified business descriptions.',
    'Percentages are shown only when every retained category is usable and nonnegative, and their sum exactly matches consolidated revenue for the same concept and period.',
    'Quarter, fiscal year to date and annual periods stay separate. Missing facts are not zero; this does not change saved research or monitoring rules.',
]


def contents(element):
    # ix:exclude is not part of an Inline XBRL fact's value.
    text = element.text or ''
    for child in element:
        if child.tag != '{'+IX+'}exclude': text += contents(child)
        text += child.tail or ''
    return ' '.join(text.split())


def qname(value, namespaces):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z_][\w.-]*:[A-Za-z_][\w.-]*', value): return None
    prefix, local = value.split(':')
    return (namespaces[prefix], local) if prefix in namespaces else None


def taxonomy(name, family):
    return bool(name and re.fullmatch(r'https?://fasb\.org/'+family+r'/20\d\d(?:-\d\d-\d\d)?', name[0]))


def category(axis):
    if taxonomy(axis, 'us-gaap') and axis[1] == 'StatementBusinessSegmentsAxis': return 'Operating segments'
    if (taxonomy(axis, 'srt') or taxonomy(axis, 'us-gaap')) and axis[1] == 'ProductOrServiceAxis': return 'Products and services'
    if (taxonomy(axis, 'srt') or taxonomy(axis, 'us-gaap')) and axis[1] == 'StatementGeographicalAxis': return 'Reported geographies'
    return None


def value_of(element, namespaces, units):
    raw = contents(element)
    if element.get(VOID) in ('true', '1'): return None, raw, 'The filing marks this value as missing.'
    if element.get('unitRef') not in units: return None, raw, 'A simple USD unit is not established.'
    if element.get('continuedAt') or element.get('target') or element.get('tupleRef'):
        return None, raw, 'This Inline XBRL fact structure is unsupported.'
    form = qname(element.get('format'), namespaces)
    if element.get('format') and not (form and form[1] in ('num-dot-decimal', 'numdotdecimal') and
            form[0] in ('http://www.xbrl.org/inlineXBRL/transformation/2010-04-20',
                        'http://www.xbrl.org/inlineXBRL/transformation/2011-07-31',
                        'http://www.xbrl.org/inlineXBRL/transformation/2015-02-26',
                        'http://www.xbrl.org/inlineXBRL/transformation/2020-02-12',
                        'http://www.xbrl.org/inlineXBRL/transformation/2022-02-16')):
        return None, raw, 'The numeric transformation is unsupported.'
    digits = raw.replace(' ', '')
    if not re.fullmatch(r'(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?', digits):
        return None, raw, 'The displayed numeric value is unsupported.'
    try:
        if len(digits.replace(',', '').replace('.', '').lstrip('0')) > 28: raise ValueError()
        scale = int(element.get('scale', '0'))
        decimals = element.get('decimals')
        if decimals != 'INF' and (decimals is None or not -18 <= int(decimals) <= 18): raise ValueError()
        if not -12 <= scale <= 12 or element.get('sign') not in (None, '-'): raise ValueError()
        with localcontext() as ctx:
            ctx.prec = 40
            value = Decimal(digits.replace(',', '')) * Decimal(10)**scale
            if element.get('sign') == '-': value = -value
        if abs(value) > 10**16: raise ValueError()
        return decimal_text(value), raw, None
    except (ValueError, InvalidOperation):
        return None, raw, 'The numeric scale, sign or precision is unsupported.'


def unique(facts):
    if not facts: return None, 'A matching fact is unavailable.'
    if any(f['reason'] for f in facts): return None, next(f['reason'] for f in facts if f['reason'])
    if len({f['value'] for f in facts}) != 1: return None, 'The filing contains conflicting facts for this category and period.'
    return facts[0]['value'], None


@lru_cache(maxsize=4)
def extract(raw, cik):
    if not isinstance(raw, bytes) or len(raw) > 20_000_000 or re.search(br'<!\s*(DOCTYPE|ENTITY)\b', raw, re.I):
        raise ValueError('Original filing XML is unsupported or exceeds its size limit.')
    namespaces = {}
    try:
        parser = ET.iterparse(io.BytesIO(raw), events=('start-ns', 'start', 'end'))
        count = depth = 0
        for event, item in parser:
            if event == 'start-ns':
                prefix, uri = item
                if prefix in namespaces and namespaces[prefix] != uri: raise ValueError('Rebound XML namespaces are unsupported.')
                namespaces[prefix] = uri
            elif event == 'start':
                depth += 1
                if depth > 128: raise ValueError('Original filing XML is nested too deeply.')
            else:
                depth -= 1
                count += 1
                if count > 200_000: raise ValueError('Original filing XML contains too many elements.')
        root = parser.root
    except ET.ParseError:
        raise ValueError('Original filing is not supported well-formed Inline XBRL.') from None
    units = set(); unit_ids = set()
    for unit in root.iter('{'+XI+'}unit'):
        if not unit.get('id') or unit.get('id') in unit_ids: raise ValueError('Unit identifiers are missing or duplicated.')
        unit_ids.add(unit.get('id'))
        if len(unit) == 1 and unit[0].tag == '{'+XI+'}measure' and qname(contents(unit[0]), namespaces) == (ISO, 'USD'):
            units.add(unit.get('id'))
    contexts = {}; seen = set()
    for node in root.iter('{'+XI+'}context'):
        key = node.get('id')
        if not key or key in seen: raise ValueError('Context identifiers are missing or duplicated.')
        seen.add(key)
        identifiers = list(node.iter('{'+XI+'}identifier'))
        if len(identifiers) != 1 or identifiers[0].get('scheme') != 'http://www.sec.gov/CIK': continue
        identifier = contents(identifiers[0])
        if not identifier.isdigit() or int(identifier) != int(cik): continue
        start, end = node.find('{'+XI+'}period/{'+XI+'}startDate'), node.find('{'+XI+'}period/{'+XI+'}endDate')
        if start is None or end is None: continue
        try: start, end = date.fromisoformat(contents(start)), date.fromisoformat(contents(end))
        except ValueError: continue
        days = (end-start).days+1
        if not 70 <= days <= 380: continue
        dimensions = [(qname(n.get('dimension'), namespaces), qname(contents(n), namespaces), n.get('dimension'), contents(n)) for n in node.iter('{'+XD+'}explicitMember')]
        if next(node.iter('{'+XD+'}typedMember'), None) is not None or any(not axis or not member for axis, member, _, _ in dimensions): continue
        if any(child.tag != '{'+XD+'}explicitMember' for container in list(node.iter('{'+XI+'}segment'))+list(node.iter('{'+XI+'}scenario')) for child in container): continue
        contexts[key] = dict(start=start.isoformat(), end=end.isoformat(), days=days, dimensions=dimensions)
    report_dates = set()
    for element in root.iter('{'+IX+'}nonNumeric'):
        name = qname(element.get('name'), namespaces)
        if name and name[1] == 'DocumentPeriodEndDate' and re.fullmatch(r'https?://xbrl\.sec\.gov/dei/20\d\d(?:-\d\d-\d\d)?',name[0]):
            context = contexts.get(element.get('contextRef'))
            if not context or context['dimensions'] or element.get('continuedAt') or element.get(VOID) in ('true', '1'): continue
            raw_date = contents(element)
            for form in ('%Y-%m-%d', '%B %d, %Y', '%b %d, %Y'):
                try:
                    parsed_date = datetime.strptime(raw_date, form).date().isoformat()
                    if parsed_date == context['end']: report_dates.add(parsed_date)
                    break
                except ValueError: pass
    if len(report_dates) != 1: raise ValueError('The filing’s reporting-period end is missing or ambiguous.')
    report_end = next(iter(report_dates))
    grouped = {}; totals = {}; fact_ids = set()
    for element in root.iter('{'+IX+'}nonFraction'):
        name = qname(element.get('name'), namespaces)
        context = contexts.get(element.get('contextRef'))
        if not taxonomy(name, 'us-gaap') or name[1] not in REVENUE or not context or context['end'] != report_end: continue
        dimensions = context['dimensions']
        if len(dimensions) > 1 or (dimensions and not category(dimensions[0][0])): continue
        fact_id = element.get('id')
        if fact_id:
            if fact_id in fact_ids: raise ValueError('Relevant fact identifiers are duplicated.')
            fact_ids.add(fact_id)
        value, display, reason = value_of(element, namespaces, units)
        fact = dict(value=value, display=display, reason=reason, fact_id=fact_id,
                    context_id=element.get('contextRef'), concept=element.get('name'),
                    scale=element.get('scale', '0'), decimals=element.get('decimals'), unit='USD' if element.get('unitRef') in units else None)
        period = (context['start'], context['end'], name)
        if not dimensions:
            totals.setdefault(period, []).append(fact); continue
        axis, member, axis_qname, member_qname = dimensions[0]
        key = period + (axis,)
        group = grouped.setdefault(key, dict(start=context['start'], end=context['end'], duration_days=context['days'],
            concept=element.get('name'), axis=axis_qname, kind=category(axis), members={}))
        group['members'].setdefault(member, dict(tag=member_qname,facts=[]))['facts'].append(fact)
    groups = []
    for key, group in grouped.items():
        total_facts = totals.get(key[:3], [])
        total, total_reason = unique(total_facts)
        members = []
        for member_name, record in sorted(group.pop('members').items()):
            member, facts = record['tag'], record['facts']
            value, reason = unique(facts)
            name = re.sub(r'(?:Member)+$', '', member.split(':',1)[1])
            label = re.sub(r'(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])', ' ', name)
            label = re.sub(r'(?<=[a-z])(including|and|of)(?= [A-Z])', r' \1', label)
            if re.fullmatch(r'https?://xbrl\.sec\.gov/country/20\d\d(?:-\d\d-\d\d)?',member_name[0]):
                label = {'US':'United States','SG':'Singapore','TW':'Taiwan'}.get(name, f'{name} (filing country code)')
            members.append(dict(member=member, label=label, value=value, reason=reason, inputs=facts, percentage=None))
        with localcontext() as ctx:
            ctx.prec = 40
            sum_value = sum((Decimal(m['value']) for m in members), Decimal(0)) if all(m['value'] is not None for m in members) else None
        reason = total_reason or next((m['reason'] for m in members if m['reason']), None)
        if not reason and (sum_value is None or sum_value != Decimal(total)): reason = 'The categories do not exactly reconcile to consolidated revenue; percentage mix is withheld.'
        if not reason and (Decimal(total) <= 0 or any(Decimal(m['value']) < 0 for m in members)): reason = 'Zero total or negative adjustments prevent a percentage mix.'
        if len(members)>50: raise ValueError('Too many reported revenue categories for this view.')
        if not reason:
            for member in members:
                with localcontext() as ctx:
                    ctx.prec=28
                    member['percentage']=decimal_text(Decimal(member['value'])/Decimal(total)*100)
        group.update(members=members, total=total, total_inputs=total_facts,
                     component_sum=decimal_text(sum_value) if sum_value is not None else None, chartable=not reason, reason=reason)
        groups.append(group)
    # Never combine or substitute revenue definitions; keep the preferred
    # reported standard concept for each exact axis/period, including its gaps.
    chosen = {}
    for group in sorted(groups,key=lambda g:REVENUE.index(g['concept'].split(':')[1])):
        chosen.setdefault((group['start'],group['end'],group['axis']),group)
    return dict(report_end=report_end, groups=list(chosen.values()), method=METHOD)


def present(conn, iid):
    if not one(conn,"SELECT 1 FROM sources WHERE id=%s AND entitlement='sec-public'",(SOURCE,)):
        return dict(status='unavailable', groups=[], message='Original-filing source access is unavailable.', method=METHOD)
    documents = rows(conn,"SELECT d.id,d.slot,d.form,d.url,d.published_at,d.available_at,d.content_hash,d.raw_html,s.cik FROM disclosure_current c JOIN disclosure_documents d ON d.id=c.document_id AND d.instrument_id=c.instrument_id JOIN sec_companies s ON s.instrument_id=c.instrument_id WHERE c.instrument_id=%s AND c.slot IN ('annual','quarter') ORDER BY d.published_at DESC",(iid,))
    groups=[]; gaps=[]
    for document in documents:
        try:
            result=deepcopy(extract(bytes(document['raw_html']),document['cik']))
            if result['report_end'] > document['published_at'].date().isoformat(): raise ValueError('Reported period is later than filing acceptance.')
            for group in result['groups']:
                days=group['duration_days']
                period='Annual' if 350<=days<=380 else 'Quarter' if 70<=days<=105 else 'Fiscal year to date'
                group.update(period=period,document_id=str(document['id']),form=document['form'],url=document['url'],
                             accepted_at=document['published_at'],available_at=document['available_at'],content_hash=document['content_hash'])
                groups.append(group)
            if not result['groups']: gaps.append(dict(document_id=str(document['id']),reason='No supported revenue breakdown in this filing.'))
        except ValueError as error: gaps.append(dict(document_id=str(document['id']),reason=str(error)))
    groups.sort(key=lambda g:(g['end'],g['kind']=='Operating segments',-g['duration_days']),reverse=True)
    return dict(status='available' if groups else 'empty',groups=groups,gaps=gaps,method=METHOD,limitations=LIMITATIONS,
                message='Read the original filings for category definitions and changes.' if groups else 'No supported revenue breakdown is available in the saved original filings.')
