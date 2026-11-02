"""Read retained original statement facts for research, never monitoring.

All recovery is pinned to an exact filing and original cells. No issuer rules,
network requests, fabricated zeros, or changes to stored Company Facts payloads.
"""
from copy import deepcopy
from datetime import date
from decimal import Decimal, localcontext
from functools import lru_cache
from collections import OrderedDict
import hashlib
import io
import json
import pickle
import re
import threading
import xml.etree.ElementTree as ET

from thesis.db import one, rows
from .performance import decimal_text
from .normalize import filing_rows, REVENUE
from .disclosure_text import archive_url
from .segment_revenue import XI, XD, IX, ISO, contents, qname, taxonomy, value_of

METHOD = 'original-statement-recovery-2'
XH = '{http://www.w3.org/1999/xhtml}'
DEBT = {'LongTermDebtCurrent', 'LongTermDebtNoncurrent', 'ShortTermBorrowings', 'CommercialPaper'}


@lru_cache(maxsize=32)
def read(raw, cik):
    if len(raw) > 20_000_000 or re.search(br'<!\s*(DOCTYPE|ENTITY)\b', raw, re.I):
        raise ValueError('Unsupported original filing XML.')
    namespaces = {}; depth = count = 0
    try:
        parser = ET.iterparse(io.BytesIO(raw), events=('start-ns', 'start', 'end'))
        for event, item in parser:
            if event == 'start-ns':
                prefix, uri = item
                if prefix in namespaces and namespaces[prefix] != uri: raise ValueError('Rebound namespace.')
                namespaces[prefix] = uri
            elif event == 'start':
                depth += 1
                if depth > 128: raise ValueError('Filing nesting limit.')
            else:
                depth -= 1; count += 1
                if count > 200_000: raise ValueError('Filing size limit.')
        root = parser.root
    except ET.ParseError as error:
        raise ValueError('Unsupported original filing XML.') from error
    ids = [n.get('id') for n in root.iter() if n.get('id')]
    if len(ids) != len(set(ids)): raise ValueError('Duplicate original identifiers.')
    parents = {child: parent for parent in root.iter() for child in parent}
    units = {n.get('id') for n in root.iter('{'+XI+'}unit') if len(n) == 1 and
             n[0].tag == '{'+XI+'}measure' and qname(contents(n[0]), namespaces) == (ISO, 'USD')}
    contexts = {}
    for n in root.iter('{'+XI+'}context'):
        identifiers = list(n.iter('{'+XI+'}identifier'))
        if len(identifiers) != 1 or identifiers[0].get('scheme') != 'http://www.sec.gov/CIK' or contents(identifiers[0]).lstrip('0') != str(int(cik)): continue
        if list(n.iter('{'+XD+'}typedMember')): continue
        if any(x.tag != '{'+XD+'}explicitMember' for container in list(n.iter('{'+XI+'}segment'))+list(n.iter('{'+XI+'}scenario')) for x in container): continue
        period = n.find('{'+XI+'}period')
        if period is None: continue
        values = {x.tag.split('}')[-1]: contents(x) for x in period}
        start, end = values.get('startDate'), values.get('endDate') or values.get('instant')
        try:
            if not end or (start and not 1 <= (date.fromisoformat(end)-date.fromisoformat(start)).days+1 <= 380): continue
            date.fromisoformat(end)
        except ValueError: continue
        dimensions = [(x.get('dimension'), contents(x)) for x in n.iter('{'+XD+'}explicitMember')]
        if any(not qname(a, namespaces) or not qname(m, namespaces) for a,m in dimensions): continue
        contexts[n.get('id')] = dict(start=start, end=end, dimensions=dimensions)
    facts = []; by_element = {}
    for n in root.iter('{'+IX+'}nonFraction'):
        ctx = contexts.get(n.get('contextRef')); concept = qname(n.get('name'), namespaces)
        if not ctx or not concept: continue
        value, display, reason = value_of(n, namespaces, units)
        fact = dict(**ctx, concept=n.get('name'), value=value, display=display, reason=reason,
                    fact_id=n.get('id'), context_id=n.get('contextRef'), scale=n.get('scale','0'),
                    decimals=n.get('decimals'), unit='USD' if n.get('unitRef') in units else None,
                    standard=taxonomy(concept,'us-gaap'))
        facts.append(fact); by_element[n] = fact
    tables = []
    for ti, table in enumerate(root.iter(XH+'table')):
        ancestor = table; hidden = False
        while ancestor is not None:
            if ancestor.tag in ('{'+IX+'}hidden','{'+IX+'}header') or re.search(r'display\s*:\s*none|visibility\s*:\s*hidden',ancestor.get('style',''),re.I): hidden=True
            ancestor = parents.get(ancestor)
        if hidden: continue
        table_rows = []
        for tr in table.iter(XH+'tr'):
            nearest = parents.get(tr)
            while nearest is not None and nearest.tag != XH+'table': nearest=parents.get(nearest)
            if nearest is not table: continue
            cells = [x for x in tr if x.tag in (XH+'td',XH+'th')]
            if not cells: continue
            row_facts = [dict(by_element[x]) for td in cells for x in td.iter('{'+IX+'}nonFraction') if x in by_element]
            label = contents(cells[0]); text = ' | '.join(contents(td) for td in cells)
            for f in row_facts: f.update(row_label=label, table_id=table.get('id') or f'table-{ti}', row_text=text)
            table_rows.append(dict(label=label, text=text, facts=row_facts))
        if table_rows and len(table_rows) <= 600: tables.append(dict(id=table.get('id') or f'table-{ti}', rows=table_rows))
    return dict(facts=facts, tables=tables, namespaces=namespaces)


def same_period(facts):
    return len({(f['start'],f['end'],f['unit']) for f in facts}) == 1


def summed(facts):
    if not facts or not same_period(facts) or any(f['reason'] or f['value'] is None for f in facts): return None
    with localcontext() as ctx:
        ctx.prec=110
        return decimal_text(sum((Decimal(f['value']) for f in facts),Decimal(0)))


def statement_recoveries(parsed):
    """Recover explicit statement structures, retaining every input and label."""
    result = []
    for table in parsed['tables']:
        facts = [f for row in table['rows'] for f in row['facts']]
        # A complete primary balance sheet establishes the displayed borrowing
        # lines. This is a carrying-value scope, not undisclosed obligations.
        for end in {f['end'] for f in facts if f['start'] is None}:
            current = [f for f in facts if f['start'] is None and f['end']==end and not f['dimensions'] and f['standard']]
            by_tag = {}
            for f in current: by_tag.setdefault(f['concept'].split(':')[-1],[]).append(f)
            equity='StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest' if by_tag.get('StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest') else 'StockholdersEquity'
            required = ('Assets','Liabilities',equity)
            # Some balance sheets omit a liabilities subtotal. Read the entire
            # noncurrent section after current liabilities, then require the
            # full accounting equation. Never search for a matching subset.
            if not by_tag.get('Liabilities') and all(len(by_tag.get(t,[]))==1 for t in ('Assets','LiabilitiesCurrent','LiabilitiesAndStockholdersEquity',equity)):
                current_total=by_tag['LiabilitiesCurrent'][0];parts=[current_total];inside=False;finished=False;valid=True
                allowed={'LongTermDebtNoncurrent','OperatingLeaseLiabilityNoncurrent','FinanceLeaseLiabilityNoncurrent','DeferredIncomeTaxLiabilitiesNet','OtherLiabilitiesNoncurrent','PensionAndOtherPostretirementDefinedBenefitPlansLiabilitiesNoncurrent'}
                for row in table['rows']:
                    if any(f['fact_id']==current_total['fact_id'] for f in row['facts']):inside=True;continue
                    if not inside:continue
                    if re.fullmatch(r"(?:stockholders|shareholders)[’']? equity:?",row['label'].strip(),re.I):finished=True;break
                    rf=[f for f in row['facts'] if f['start'] is None and f['end']==end]
                    if rf and all(f['concept'].split(':')[-1]=='CommitmentsAndContingencies' and f['value'] in (None,'0') for f in rf):continue
                    if not rf:
                        if re.search(r'\d',row['text']) and not row['facts']:valid=False
                        continue
                    if any(not f['standard'] or f['dimensions'] or f['concept'].split(':')[-1] not in allowed for f in rf):valid=False
                    parts.extend(rf)
                if valid and finished and len(parts)>1 and len({f['concept'] for f in parts})==len(parts):
                    value=summed(parts);assets=by_tag['Assets'][0];eq=by_tag[equity][0];total=by_tag['LiabilitiesAndStockholdersEquity'][0]
                    if value is not None and all(Decimal(f['value'])>=0 for f in parts) and summed(parts+[eq])==assets['value']==total['value'] and not total['reason']:
                        result.append(dict(target='Liabilities',value=value,start=None,end=end,inputs=parts,
                            formula='Current liabilities + all separately reported noncurrent liabilities',
                            explanation='The complete liabilities section plus reported equity reconciles exactly to total assets in the same balance sheet.'))
            if not all(len(by_tag.get(t,[]))==1 and by_tag[t][0]['value'] is not None and not by_tag[t][0]['reason'] for t in required): continue
            a,l,e = [by_tag[t][0] for t in required]
            if summed([l,e]) != a['value']: continue
            debt = [f for f in current if f['concept'].split(':')[-1] in DEBT]
            tags = [f['concept'].split(':')[-1] for f in debt]
            if not {'LongTermDebtCurrent','LongTermDebtNoncurrent'}.issubset(tags):
                # A combined current-debt line plus a long-term line *after*
                # the current-liabilities subtotal proves separate balance-sheet
                # sections. The broad LongTermDebt tag alone does not.
                alternate=('DebtCurrent','LiabilitiesCurrent','LongTermDebt','Liabilities')
                if debt or not all(len(by_tag.get(t,[]))==1 for t in alternate):continue
                ds,lc,dl,lt=[by_tag[t][0] for t in alternate]
                positions={f['fact_id']:i for i,row in enumerate(table['rows']) for f in row['facts']}
                if not positions[ds['fact_id']]<positions[lc['fact_id']]<positions[dl['fact_id']]<positions[lt['fact_id']]:continue
                debt=[ds,dl];tags=['DebtCurrent','LongTermDebt']
            if len(tags)!=len(set(tags)):continue
            # Short-term totals may include commercial paper; never add both.
            if 'ShortTermBorrowings' in tags and 'CommercialPaper' in tags: continue
            value = summed(debt)
            if value is not None and all(Decimal(f['value'])>=0 for f in debt):
                result.append(dict(target='balance_sheet_borrowing',value=value,start=None,end=end,inputs=debt,
                    formula='Sum of the separately reported borrowing lines on the balance sheet',
                    explanation='Carrying amounts of borrowing separately shown on the consolidated balance sheet. Lease liabilities and obligations included in other lines are outside this scope.'))
        # Costs reported by product/service plus separately reported cost
        # amortization. Require a complete, disjoint revenue set and the same
        # categories for costs in the actual consolidated income statement.
        for start,end in {(f['start'],f['end']) for f in facts if f['start']}:
            current=[f for f in facts if (f['start'],f['end'])==(start,end) and f['standard']]
            whole=[f for f in current if not f['dimensions']]
            revenue=[f for f in whole if f['concept'].split(':')[-1] in REVENUE]
            operating=[f for f in whole if f['concept'].endswith(':OperatingIncomeLoss')]
            total_cost=[f for f in whole if f['concept'].endswith(':CostsAndExpenses')]
            if len(revenue)!=1 or len(operating)!=1 or len(total_cost)!=1 or summed(operating+total_cost)!=revenue[0]['value']: continue
            selling=[f for f in whole if f['concept'].endswith(':SellingAndMarketingExpense')]
            admin=[f for f in whole if f['concept'].endswith(':GeneralAndAdministrativeExpense')]
            if len(selling)==len(admin)==1 and summed(selling+admin) is not None:
                result.append(dict(target='SellingGeneralAndAdministrativeExpense',value=summed(selling+admin),start=start,end=end,
                    inputs=selling+admin,formula='Selling and marketing + general and administrative expenses',
                    explanation='Separate expense lines in the same consolidated income statement.'))
            def product(f):
                return len(f['dimensions'])==1 and f['dimensions'][0][0].split(':')[-1]=='ProductOrServiceAxis' and taxonomy(qname(f['dimensions'][0][0],parsed['namespaces']),'srt')
            sales=[f for f in current if product(f) and f['concept'].split(':')[-1] in REVENUE]
            costs=[f for f in current if product(f) and f['concept'].split(':')[-1] in ('CostOfRevenue','CostOfGoodsAndServicesSold')]
            members=lambda fs:[tuple(f['dimensions'][0]) for f in fs]
            if len(sales)<2 or len(set(members(sales)))!=len(sales) or sorted(members(sales))!=sorted(members(costs)) or summed(sales)!=revenue[0]['value']: continue
            amort=[f for f in whole if f['concept'].endswith(':CostOfGoodsAndServicesSoldAmortization')]
            if len(amort)!=1: continue  # absence does not establish zero
            inputs=costs+amort; value=summed(inputs)
            # Verify the complete labelled cost section. An extra custom cost
            # row must not disappear merely because its tag is unfamiliar.
            block=[];inside=False;finished=False
            for row in table['rows']:
                label=re.sub(r'[^a-z]','',row['label'].lower())
                if label in ('costofrevenue','costofsales') and not row['facts']:inside=True;continue
                if not inside:continue
                if not row['facts'] and re.search(r'\d',row['text']):break
                rf=[f for f in row['facts'] if (f['start'],f['end'])==(start,end)]
                if rf and all(f['concept'].split(':')[-1] in ('SellingAndMarketingExpense','SellingGeneralAndAdministrativeExpense','ResearchAndDevelopmentExpense','GeneralAndAdministrativeExpense','OperatingExpenses') for f in rf):finished=True;break
                block.extend(rf)
            if not finished or {f['fact_id'] for f in block}!={f['fact_id'] for f in inputs}:continue
            if value is not None and all(Decimal(f['value'])>=0 for f in inputs) and Decimal(value)<=Decimal(total_cost[0]['value']):
                result.append(dict(target='CostOfRevenue',value=value,start=start,end=end,inputs=inputs,
                    formula='Reported product/service costs + separately reported cost amortization',
                    explanation='The product/service categories reconcile to total revenue in this same income statement.'))
    return result


def attach(bundle, documents, cik, now):
    """Ephemeral research overlay; raw payloads and monitoring are unchanged."""
    filings={archive_url(cik,f['accessionNumber'],f['primaryDocument']):f for f in filing_rows(bundle['submissions'],now)}
    result=dict(bundle); recovered={}; borrowing={}; audit=[]
    for document in documents:
        filing=filings.get(document['url'])
        if not filing or document['form']!=filing['form']: continue
        raw=bytes(document['raw_html'])
        if hashlib.sha256(raw).hexdigest()!=document['content_hash']: continue
        try: parsed=read(raw,cik)
        except ValueError: parsed=None
        evidence=dict(document_id=str(document['id']),content_hash=document['content_hash'],filing_url=document['url'],
                      accession=filing['accessionNumber'],form=filing['form'],filed=filing['filingDate'],method=METHOD)
        from .cash_statements import tagged_recoveries, legacy_recoveries
        try:
            cash = tagged_recoveries(parsed,bundle,filing) if parsed else legacy_recoveries(raw,bundle,filing) if len(raw)<=20_000_000 and not re.search(br'<[\w:]*nonFraction\b',raw,re.I) else []
        except (ValueError, UnicodeError): cash=[]
        for f in parsed['facts'] if parsed else []:
            if not f['standard'] or f['dimensions'] or f['reason'] or f['value'] is None or f['end']>filing['end'].isoformat():continue
            tag=f['concept'].split(':')[-1]
            recovered.setdefault(tag,[]).append(dict(f,concept=tag,namespace='us-gaap',**evidence,
                recovery=dict(target=tag,value=f['value'],start=f['start'],end=f['end'],inputs=[dict(f,**evidence)],
                              formula=None,explanation='Read from the original tagged statement.')))
        for r in (statement_recoveries(parsed) if parsed else []) + cash:
            if r['end']>filing['end'].isoformat(): continue
            r=deepcopy(r);r['inputs']=[dict(f,**evidence) for f in r['inputs']]
            if r['target']=='balance_sheet_borrowing':
                borrowing.setdefault((filing['accessionNumber'],r['end']),[]).append(r)
            else:
                recovered.setdefault(r['target'],[]).append(dict(concept=r['target'],namespace='app-calculation',unit='USD',
                    value=r['value'],start=r['start'],end=r['end'],**evidence,recovery=r))
            audit.append(dict(target=r['target'],start=r['start'],end=r['end'],document_id=str(document['id'])))
    result['_original_facts']=recovered;result['_original_borrowing']=borrowing;result['_recovery_audit']=audit
    result['_recovery_basis']=hashlib.sha256((METHOD+'|'+ '|'.join(sorted(str(d['id'])+d['content_hash'] for d in documents))).encode()).hexdigest()
    return result


_overlays = OrderedDict()
_overlay_lock = threading.Lock()
_overlay_bytes = 0
_OVERLAY_LIMIT = 96 * 1024 * 1024


def fingerprint(document):
    """Hash of the actual saved bytes; the database can supply it without a transfer."""
    if document.get('raw_sha'):
        return bytes.fromhex(document['raw_sha'])
    return hashlib.sha256(bytes(document['raw_html'])).digest()


def cached_attach(bundle, documents, cik, now, load=None, bundle_key=None):
    """Cache only deterministic public extraction, never access or owner reviews.

    Fingerprint actual bytes as well as saved hashes so damaged/changed originals
    cannot reuse a previously verified reading. Documents may carry a database-
    computed `raw_sha` instead of `raw_html`; `load` then fetches the bytes only
    when extraction must run. Entries are pickled, so every hit returns an
    independent copy (downstream readers attach evidence to facts).
    """
    global _overlay_bytes
    # A saved payload's id names its exact, unchangeable content (source_payloads
    # rows are immutable), so it stands in for hashing megabytes of JSON on
    # every read. Without one, the bundle itself is hashed as before.
    digest = hashlib.sha256(
        ('saved-payload:' + str(bundle_key)).encode() if bundle_key is not None
        else json.dumps(bundle, sort_keys=True, separators=(',', ':')).encode())
    digest.update(str((METHOD, cik, now)).encode())
    for document in documents:
        digest.update(json.dumps({k: str(v) for k, v in document.items() if k not in ('raw_html', 'raw_sha')}, sort_keys=True).encode())
        digest.update(fingerprint(document))
    key = digest.digest()
    with _overlay_lock:
        blob = _overlays.get(key)
        if blob is not None:
            _overlays.move_to_end(key)
    if blob is None:
        if load and any('raw_html' not in d for d in documents):
            documents = load(documents)
        result = attach(bundle, documents, cik, now)
        blob = pickle.dumps({k: v for k, v in result.items() if k.startswith('_original_') or k.startswith('_recovery_')},
                            pickle.HIGHEST_PROTOCOL)
        if len(blob) <= _OVERLAY_LIMIT:
            with _overlay_lock:
                if key not in _overlays:
                    _overlays[key] = blob
                    _overlay_bytes += len(blob)
                    while len(_overlays) > 64 or _overlay_bytes > _OVERLAY_LIMIT:
                        _, removed = _overlays.popitem(last=False)
                        _overlay_bytes -= len(removed)
    return dict(bundle, **pickle.loads(blob))


def load_raw(conn):
    def load(documents):
        raw = {str(r['id']): r['raw_html'] for r in rows(conn, "SELECT id,raw_html FROM disclosure_documents WHERE id=ANY(%s)",
                                                       ([d['id'] for d in documents],))}
        return [dict(d, raw_html=raw[str(d['id'])]) for d in documents if str(d['id']) in raw]
    return load


def enrich(conn,iid,bundle,cik,now,payload_id=None):
    if not one(conn,"SELECT 1 FROM sources WHERE id='sec-disclosures' AND entitlement='sec-public'"): return bundle
    # Hash in the database: the originals are large and rarely need re-reading.
    documents=rows(conn,"SELECT DISTINCT ON (url) id,url,form,content_hash,encode(sha256(raw_html),'hex') raw_sha FROM disclosure_documents WHERE instrument_id=%s AND source_id='sec-disclosures' AND form IN ('10-K','10-Q','10-K/A','10-Q/A') ORDER BY url,available_at DESC",(iid,))
    result=cached_attach(bundle,documents,cik,now,load_raw(conn),bundle_key=payload_id)
    from .financial_recovery import apply_reviewed
    return apply_reviewed(conn,iid,result,documents)