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
import hashlib
import re
import xml.etree.ElementTree as ET
from thesis.db import one, rows
from .normalize import REVENUE
from .performance import decimal_text
from .disclosures import SOURCE

METHOD = 'sec-segment-revenue-3'
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


def geography_views(group, scopes):
    """Separate complete disclosures, never search for a subset that sums up.

    A table must carry its own consolidated total. A prose paragraph must
    explicitly describe revenue by country. Every member remains subject to
    the original document-wide conflict checks. Split only when the complete
    disclosed sets are disjoint and account for every original member.
    """
    if group['kind'] != 'Reported geographies' or not group['total'] or Decimal(group['total']) <= 0:
        return [group]
    if any(m['value'] is None or Decimal(m['value']) < 0 for m in group['members']): return [group]
    sets = {}
    for member in group['members']:
        for fact in member['inputs']:
            if fact.get('disclosure_id'):
                sets.setdefault(fact['disclosure_id'], {})[member['member']] = member
    candidates = {}
    for key, members in sets.items():
        scope = scopes[key]
        if len(members) < 2: continue
        if scope['type'] == 'table':
            if not any(f.get('disclosure_id') == key and f['value'] == group['total'] for f in group['total_inputs']): continue
        elif scope['type'] != 'countries': continue
        with localcontext() as ctx:
            ctx.prec = 40
            if sum((Decimal(m['value']) for m in members.values()), Decimal(0)) != Decimal(group['total']): continue
        identity = tuple(sorted(members))
        candidates.setdefault(identity, (scope, list(members.values())))
    identities = list(candidates)
    if not identities or set().union(*map(set, identities)) != {m['member'] for m in group['members']}: return [group]
    if any(set(a) & set(b) for i, a in enumerate(identities) for b in identities[i+1:]): return [group]
    result = []
    for identity, (scope, members) in candidates.items():
        view = deepcopy(group)
        label = 'Countries' if scope['type'] == 'countries' else 'Regions' if all(
            m.split(':')[-1] in ('AmericasMember', 'AsiaPacificMember', 'EMEAMember',
                                'EuropeMiddleEastAndAfricaMember', 'EuropeMiddleEastandAfricaMember') for m in identity
        ) else 'Geographic breakdown'
        with localcontext() as ctx:
            ctx.prec = 28
            for member in (members := deepcopy(members)):
                member['percentage'] = decimal_text(Decimal(member['value']) / Decimal(group['total']) * 100)
        view.update(members=members, chartable=True, reason=None, component_sum=group['total'],
                    view_id=hashlib.sha256('|'.join(identity).encode()).hexdigest()[:16], view_label=label,
                    disclosure=dict(scope))
        result.append(view)
    labels = [g['view_label'] for g in result]
    for index, view in enumerate(result):
        if labels.count(view['view_label']) > 1: view['view_label'] += ' '+str(index+1)
    return sorted(result, key=lambda g:(g['view_label'] != 'Countries', g['view_label'], g['view_id']))


@lru_cache(maxsize=24)
def extract(raw, cik, include_comparatives=False, all_concepts=False):
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
        if name and name[1] == 'DocumentPeriodEndDate' and re.fullmatch(r'https?://xbrl\.sec\.gov/dei/20\d\d(?:-\d\d-\d\d|q[1-4])?',name[0]):
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
    parents = {child: parent for parent in root.iter() for child in parent}
    continuations = {}
    for node in root.iter('{'+IX+'}continuation'):
        key = node.get('id')
        if not key or key in continuations: raise ValueError('Continuation identifiers are missing or duplicated.')
        continuations[key] = node
    scope_ids = {}; scopes = {}
    def disclosure_scope(element):
        node = element; block = None; table = None
        while node in parents:
            node = parents[node]
            if node.tag in ('{'+IX+'}hidden', '{'+IX+'}header'): return None
            if node.tag == '{http://www.w3.org/1999/xhtml}table' and table is None: table = node
            if node.tag in ('{http://www.w3.org/1999/xhtml}p', '{http://www.w3.org/1999/xhtml}div') and block is None: block = node
        container = table if table is not None else block
        if container is None: return None
        if container not in scope_ids:
            key = 'disclosure-'+str(len(scope_ids)+1)
            text = contents(container)
            kind = 'table' if table is not None else 'countries' if len(text) <= 6000 and re.match(
                r'^(?:Net )?(?:revenue|revenues|sales) by countr(?:y|ies)\b', text, re.I) else 'unsupported'
            scope_ids[container] = key
            scopes[key] = dict(type=kind, element_id=container.get('id'))
            if kind == 'countries':
                # A paragraph may cross a page boundary. Follow only the
                # filing's explicit continuation link, from its last block to
                # the next continuation's first block and an unfinished sentence.
                current = container; chain = []
                for _ in range(4):
                    parent = parents.get(current)
                    target = parent.get('continuedAt') if parent is not None and parent.tag == '{'+IX+'}continuation' else None
                    following = continuations.get(target)
                    if (parent is None or not len(parent) or parent[-1] is not current or following is None or not len(following)
                            or target in chain or re.search(r'[.!?;]$', text.rstrip())): break
                    next_block = following[0]
                    tail = contents(next_block)
                    if (next_block.tag not in ('{http://www.w3.org/1999/xhtml}p', '{http://www.w3.org/1999/xhtml}div')
                            or not re.match(r'^[a-z]', tail) or len(text)+len(tail)>6000): break
                    scope_ids[next_block] = key; chain.append(target)
                    text += ' '+tail; current = next_block
                scopes[key]['description'] = text
                if chain: scopes[key]['continuation_ids'] = chain
        return scope_ids[container]
    grouped = {}; totals = {}; fact_ids = set()
    for element in root.iter('{'+IX+'}nonFraction'):
        name = qname(element.get('name'), namespaces)
        context = contexts.get(element.get('contextRef'))
        if not taxonomy(name, 'us-gaap') or name[1] not in REVENUE or not context: continue
        if context['end'] > report_end or (not include_comparatives and context['end'] != report_end): continue
        dimensions = context['dimensions']
        original_dimensions = dimensions
        # The standard operating-segments qualifier is compatible with a
        # segment member, but eliminations/corporate/custom qualifiers are not.
        # Keep original dimensions on each input; conflicts still withhold the
        # category and the full set must reconcile to a whole-company total.
        if len(dimensions) == 2 and any(category(axis) == 'Operating segments' for axis, _, _, _ in dimensions):
            dimensions = [d for d in dimensions if not
                          ((taxonomy(d[0], 'srt') or taxonomy(d[0], 'us-gaap')) and d[0][1] == 'ConsolidationItemsAxis'
                           and taxonomy(d[1], 'us-gaap') and d[1][1] == 'OperatingSegmentsMember')]
        if len(dimensions) > 1 or (dimensions and not category(dimensions[0][0])): continue
        fact_id = element.get('id')
        if fact_id:
            if fact_id in fact_ids: raise ValueError('Relevant fact identifiers are duplicated.')
            fact_ids.add(fact_id)
        value, display, reason = value_of(element, namespaces, units)
        fact = dict(value=value, display=display, reason=reason, fact_id=fact_id,
                    dimensions=[dict(axis=a, member=m) for _, _, a, m in original_dimensions],
                    context_id=element.get('contextRef'), concept=element.get('name'),
                    scale=element.get('scale', '0'), decimals=element.get('decimals'), unit='USD' if element.get('unitRef') in units else None)
        fact['disclosure_id'] = disclosure_scope(element)
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
        groups.extend(geography_views(group, scopes))
    # Never combine or substitute revenue definitions; keep the preferred
    # reported standard concept for each exact axis/period, including its gaps.
    chosen = {}
    for group in sorted(groups,key=lambda g:REVENUE.index(g['concept'].split(':')[1])):
        chosen.setdefault((group['start'],group['end'],group['axis'],group.get('view_id')),group)
    return dict(report_end=report_end, groups=groups if all_concepts else list(chosen.values()), method=METHOD)


def trailing_groups(period, groups):
    """Apply the existing annual + current YTD − prior YTD revenue bridge.

    Only fully reconciled, unchanged member sets can be bridged. No category
    matching by display label, omitted members as zero, or overlapping regions.
    """
    revenue = next((m for m in period['metrics'] if m['key'] == 'revenue'), None)
    if period.get('kind') != 'trailing' or not revenue or revenue['value'] is None:
        return []
    inputs = revenue['inputs']
    if len(inputs) != 3 or not revenue.get('calculated'):
        return []
    # trailing() retains annual, current YTD, comparable prior YTD in this order.
    annual, current, prior = inputs
    if not all(f.get('start') and f.get('end') and f.get('filing_url') for f in inputs): return []
    from datetime import timedelta
    if (date.fromisoformat(annual['end']) + timedelta(days=1)).isoformat() != current['start'] or current['end'] != period['end']:
        return []
    if (date.fromisoformat(prior['end']) + timedelta(days=1)).isoformat() != period['start'] or prior['start'] != annual['start']:
        return []
    if len({f['concept'] for f in inputs}) != 1: return []
    matches = [[g for g in groups if g['chartable'] and g['url'] == f['filing_url'] and
                (g['start'], g['end'], g['total'], g['concept'].split(':')[-1]) == (f['start'], f['end'], f['value'], f['concept'])]
               for f in inputs]
    result = []
    for first in matches[0]:
        axis = first['axis']
        rest = [[g for g in values if g['axis'] == axis and g['kind'] == first['kind']
                 and g.get('view_id') == first.get('view_id') and g.get('view_label') == first.get('view_label')]
                for values in matches[1:]]
        if any(len(values) != 1 for values in rest): continue
        parts = [first, rest[0][0], rest[1][0]]
        member_sets = [{m['member']: m for m in g['members']} for g in parts]
        if not all(set(m) == set(member_sets[0]) for m in member_sets): continue
        members = []
        for key, member in member_sets[0].items():
            rows = [m[key] for m in member_sets]
            if len({r['label'] for r in rows}) != 1: break
            with localcontext() as ctx:
                ctx.prec = 110
                value = Decimal(rows[0]['value']) + Decimal(rows[1]['value']) - Decimal(rows[2]['value'])
            if value < 0: break
            evidence = [dict(f, start=g['start'], end=g['end'], form=g['form'],
                             filing_url=g['url'] + ('#'+f['fact_id'] if f.get('fact_id') else ''))
                        for g, r in zip(parts, rows) for f in r['inputs']]
            members.append(dict(member=key, label=member['label'], value=decimal_text(value), reason=None,
                                inputs=evidence, calculated=True, formula='Previous fiscal year + current fiscal year to date − comparable prior fiscal year to date'))
        else:
            with localcontext() as ctx:
                ctx.prec = 110
                total = sum((Decimal(m['value']) for m in members), Decimal(0))
                if total <= 0 or total != Decimal(revenue['value']): continue
                ctx.prec = 28
                for member in members:
                    member['percentage'] = decimal_text(Decimal(member['value']) / total * 100)
            result.append(dict(first, start=period['start'], end=period['end'], period='Past 12 months', period_id=period['id'],
                               revenue_inputs=deepcopy(inputs), total=revenue['value'], total_inputs=deepcopy(inputs),
                               members=members, calculated=True, url=None, component_sum=revenue['value']))
    return result


def present(conn, iid, flow=None):
    if not one(conn,"SELECT 1 FROM sources WHERE id=%s AND entitlement='sec-public'",(SOURCE,)):
        return dict(status='unavailable', groups=[], message='Original-filing source access is unavailable.', method=METHOD)
    if flow is None:
        from .income_flow import present as income_flow
        flow = income_flow(conn, iid)
    # Exact revenue input URLs include earlier originals only when the income
    # reader has independently proved the intervening amendment chain safe.
    revenue_inputs = [f for p in flow.get('periods', []) for m in p['metrics'] if m['key'] == 'revenue'
                      for f in m['inputs'] if f.get('filing_url')]
    urls = sorted({f['filing_url'] for f in revenue_inputs})
    documents = rows(conn,"SELECT DISTINCT ON (d.url) d.id,d.slot,d.form,d.url,d.published_at,d.available_at,d.content_hash,d.raw_html,s.cik FROM disclosure_documents d JOIN sec_companies s ON s.instrument_id=d.instrument_id WHERE d.instrument_id=%s AND d.source_id=%s AND d.form IN ('10-K','10-K/A','10-Q','10-Q/A') AND (d.url=ANY(%s) OR d.id IN (SELECT document_id FROM disclosure_current WHERE instrument_id=%s AND slot IN ('annual','quarter'))) ORDER BY d.url,d.available_at DESC,d.id DESC",(iid,SOURCE,urls,iid))
    groups=[]; candidates=[]; gaps=[]
    for document in documents:
        try:
            if hashlib.sha256(bytes(document['raw_html'])).hexdigest() != document['content_hash']:
                raise ValueError('The retained original filing could not be verified.')
            result=deepcopy(extract(bytes(document['raw_html']),document['cik'],True,True))
            if result['report_end'] > document['published_at'].date().isoformat(): raise ValueError('Reported period is later than filing acceptance.')
            selected_groups = {}
            for group in sorted(result['groups'], key=lambda g:REVENUE.index(g['concept'].split(':')[-1])):
                required = {f['concept'] for f in revenue_inputs if
                            (f['filing_url'], f['start'], f['end']) == (document['url'], group['start'], group['end'])}
                if required and group['concept'].split(':')[-1] not in required: continue
                selected_groups.setdefault((group['start'],group['end'],group['axis'],group.get('view_id')),group)
            for group in selected_groups.values():
                days=group['duration_days']
                period='Annual' if 350<=days<=380 else 'Quarter' if 70<=days<=105 else 'Fiscal year to date'
                group.update(period=period,document_id=str(document['id']),form=document['form'],url=document['url'],
                             accepted_at=document['published_at'],available_at=document['available_at'],content_hash=document['content_hash'])
                candidates.append(group)
                if group['end'] == result['report_end']:
                    groups.append(group)
            if not result['groups']: gaps.append(dict(document_id=str(document['id']),reason='No supported revenue breakdown in this filing.'))
        except ValueError as error: gaps.append(dict(document_id=str(document['id']),reason=str(error)))
    groups.sort(key=lambda g:(g['end'],g['kind']=='Operating segments',-g['duration_days'],g['accepted_at']),reverse=True)
    derived = [g for period in flow.get('periods', []) for g in trailing_groups(period, candidates)]
    return dict(status='available' if groups else 'empty',groups=groups,gaps=gaps,method=METHOD,limitations=LIMITATIONS,
                filing_urls=[d['url'] for d in documents],
                trailing_groups=derived,
                message='Read the original filings for category definitions and changes.' if groups else 'No supported revenue breakdown is available in the saved original filings.')
