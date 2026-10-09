"""Auditable trailing results and debt normalization over retained SEC facts.

These are research calculations, never new monitoring metrics. Missing concepts,
incompatible fiscal dates and incomplete borrowing components remain unknown.
"""
from datetime import date, timedelta
from decimal import Decimal,localcontext
from .normalize import filing_rows,REVENUE
from .performance import collect,unique,select,decimal_text,duration
from thesis.db import one
from .disclosure_text import archive_url

METHOD='sec-financial-depth-2'
FLOW={
 'revenue':('Revenue',REVENUE),
 'operating_income':('Operating income',('OperatingIncomeLoss',)),
 'net_income':('Net income',('NetIncomeLoss',)),
 'operating_cash':('Operating cash flow',('NetCashProvidedByUsedInOperatingActivities',)),
 'capital_spending':('Cash capital spending',('PaymentsToAcquirePropertyPlantAndEquipment',)),
}


def reported(bundle, filing, tags):
    """Any reported current-period input, including unusable currencies.

    Broader definitions must not conceal a conflicting or unsupported preferred
    fact. Missing comparative inputs also do not authorize a definition switch.
    """
    return any(row.get('accn') == filing['accessionNumber'] and row.get('form') == filing['form']
               and row.get('filed') == filing['filingDate'] and row.get('end') == filing['end'].isoformat()
               for tag in tags for values in bundle['companyfacts'].get('facts', {}).get('us-gaap', {}).get(tag, {}).get('units', {}).values() for row in values)


def common_concept(bundle, filings, inputs, tags):
    """Choose a common tag only when every exact input is also reported in it.

    This is not an alias across reporting definitions: the values, fiscal dates
    and filing vintages must already match for all three original inputs.
    """
    choices=[]
    for fact in inputs:
        filing=next((f for f in filings if f['accessionNumber']==fact['accession']),None)
        alternatives=collect(bundle,filing,tags) if filing else []
        choices.append({f['concept']:f for f in alternatives if all(f[k]==fact[k] for k in ('value','start','end','accession','form','filed','unit'))})
    for tag in tags:
        if all(tag in group for group in choices):return [group[tag] for group in choices]
    return inputs


def capital_spending(bundle, filings, current, resolver=None):
    if resolver and current['form'].endswith('/A'):
        raw=dict(key='capital_spending',**capital_spending(bundle,filings,current))
        values,_=resolver.resolve(current,[raw],lambda earlier:[dict(key='capital_spending',**capital_spending(bundle,filings,earlier))])
        result=values[0];result.pop('key',None)
        return result
    tags=('PaymentsToAcquirePropertyPlantAndEquipment',)
    broader=not reported(bundle,current,tags)
    if broader:tags=('PaymentsToAcquireProductiveAssets',)
    result=trailing(bundle,filings,current,tags,resolver)
    return dict(result,label='Cash spending on property, equipment, software & intangibles' if broader else 'Cash capital spending',
                spending_basis='productive_assets' if broader else 'property_plant_equipment',
                explanation='Cash purchases of property, plant, equipment, software and other intangible assets; this broader reported category is used in free cash flow.' if broader else 'Cash purchases of property, plant and equipment.')


def trailing(bundle,filings,current,tags, resolver=None):
    if resolver and current['form'].endswith('/A'):
        key=next((k for k,(_,concepts) in FLOW.items() if concepts==tags),tags[0])
        raw=dict(key=key,**trailing(bundle,filings,current,tags))
        resolved,_=resolver.resolve(current,[raw],lambda earlier:[dict(key=key,**trailing(bundle,filings,earlier,tags,resolver=None))])
        result=resolved[0];result.pop('key',None)
        return result
    facts=collect(bundle,current,tags)
    if current['form'].startswith('10-K'):
        value,error=select(facts,current,'annual','Business performance',tags)
        return dict(value=value['value'] if value else None,inputs=[value] if value else [],reason=error,
                    start=value['start'] if value else None,end=current['end'].isoformat(),formula='Reported fiscal-year value',calculated=False)
    candidates=[f for f in facts if f['start'] and f['end']==current['end'].isoformat() and 70<=duration(f)<=310]
    if candidates:
        longest=max(duration(f) for f in candidates)
        candidates=[f for f in candidates if duration(f)==longest]
    ytd,error=unique(candidates,tags)
    if not ytd:return dict(value=None,inputs=[],reason=error,start=None,end=current['end'].isoformat(),formula=None,calculated=True)
    annual_end=date.fromisoformat(ytd['start'])-timedelta(days=1)
    annuals=[f for f in filings if f['form'].startswith('10-K') and f['end']==annual_end and f['accepted_at']<=current['accepted_at']]
    annual=annuals[-1] if annuals else None
    base,error=select(collect(bundle,annual,tags),annual,'annual','Business performance',tags) if annual else (None,'The preceding fiscal-year filing is unavailable.')
    base_resolution={}
    if resolver and annual and annual['form'].endswith('/A'):
        resolved=trailing(bundle,filings,annual,tags,resolver)
        base=resolved['inputs'][0] if resolved['value'] is not None and len(resolved['inputs'])==1 else None
        error=resolved['reason']
        if resolved.get('filing_resolution'):base_resolution['filing_resolution']=resolved['filing_resolution']
    prior_candidates=[f for f in facts if base and f['start']==base['start'] and f['end']<ytd['end'] and
                      abs(duration(f)-duration(ytd))<=7 and 357<=(date.fromisoformat(ytd['end'])-date.fromisoformat(f['end'])).days<=373]
    prior,prior_error=unique(prior_candidates,tags)
    inputs=[f for f in [base,ytd,prior] if f]
    reason=error or prior_error
    value=None
    start=None
    if not reason:
        inputs=common_concept(bundle,filings,inputs,tags)
        # Dates remain known when the amount is withheld for a definition
        # change. Other measures must not inherit this measure's missing value.
        start=(date.fromisoformat(prior['end'])+timedelta(days=1)).isoformat()
        if not 350<=(current['end']-date.fromisoformat(start)).days+1<=380:
            reason='The annual/YTD bridge does not cover a compatible trailing fiscal year.'
        elif len({f['concept'] for f in inputs})!=1:
            reason='These filings use different reporting labels; a comparable past-12-month total has not been established.'
        else:
            with localcontext() as ctx:
                ctx.prec=28
                value=decimal_text(Decimal(base['value'])+Decimal(ytd['value'])-Decimal(prior['value']))
    return dict(value=value,inputs=inputs,reason=reason,start=start,end=current['end'].isoformat(),
                formula='Previous fiscal year + current fiscal year to date − comparable prior fiscal year to date',calculated=True,**base_resolution)


def total_debt(bundle,current):
    def instant(tags):return select(collect(bundle,current,tags),current,'quarter','Balance sheet',tags)[0]
    direct_facts=collect(bundle,current,('DebtLongtermAndShorttermCombinedAmount',))
    direct,direct_error=select(direct_facts,current,'quarter','Balance sheet',('DebtLongtermAndShorttermCombinedAmount',))
    reported_facts=[f for f in direct_facts if f['start'] is None and f['end']==current['end'].isoformat()]
    if reported_facts and (not direct or Decimal(direct['value'])<0):
        return dict(key='total_debt',label='Reported combined borrowing',value=None,unit='USD',inputs=reported_facts,end=current['end'].isoformat(),start=None,
                    formula=None,reason=direct_error or 'The reported borrowing total is negative; this debt convention is not applied.',calculated=False,explanation='An unusable reported total is not masked with a different component sum.')
    if direct and Decimal(direct['value'])>=0:
        return dict(key='total_debt',label='Reported combined borrowing',value=direct['value'],unit='USD',inputs=[direct],end=direct['end'],start=None,
                    formula=None,reason=None,calculated=False,explanation='Standard whole-company long- and short-term debt combined amount. Lease obligations and other liabilities are separate.')
    if reported(bundle,current,('DebtLongtermAndShorttermCombinedAmount',)):
        return dict(key='total_debt',label='Reported combined borrowing',value=None,unit='USD',inputs=direct_facts,end=current['end'].isoformat(),start=None,
                    formula=None,reason=direct_error,calculated=False,explanation='An unsupported reported total is not replaced by another definition.')
    # A reported total long-term debt already includes current maturities; do
    # not add its current/noncurrent portions to it again.
    long_total=instant(('LongTermDebt',))
    parts=[instant(('LongTermDebtCurrent',)),instant(('LongTermDebtNoncurrent',))]
    short=instant(('ShortTermBorrowings',))
    inputs=([long_total] if long_total else [p for p in parts if p])+([short] if short else [])
    valid=short is not None and (long_total is not None or all(parts))
    value=None;reason=None
    if not valid:
        combined=instant(('DebtAndCapitalLeaseObligations',))
        leases=instant(('FinanceLeaseLiability',))
        if combined and leases and Decimal(combined['value'])>=Decimal(leases['value'])>=0:
            with localcontext() as ctx:
                ctx.prec=110;value=decimal_text(Decimal(combined['value'])-Decimal(leases['value']))
            return dict(key='total_debt',label='Borrowing excluding finance leases (app calculation)',value=value,unit='USD',inputs=[combined,leases],start=None,end=current['end'].isoformat(),
                        formula='Reported debt and finance-lease obligations − reported finance-lease liability',reason=None,calculated=True,
                        explanation='Both complete balances come from the same filing and date. Finance leases are removed to preserve the borrowing definition; no missing component is assumed to be zero.')
        reason='A complete reported borrowing total or all compatible long-/short-term components are unavailable. Missing borrowing is not zero.'
    elif any(Decimal(f['value'])<0 for f in inputs):reason='A borrowing component is negative; this debt convention is not applied.'
    else:
        with localcontext() as ctx:
            ctx.prec=28;value=decimal_text(sum((Decimal(f['value']) for f in inputs),Decimal(0)))
    return dict(key='total_debt',label='Borrowing (app calculation)',value=value,unit='USD',inputs=inputs,end=current['end'].isoformat(),start=None,
                formula='Reported total long-term debt + short-term borrowings' if long_total else 'Long-term debt: current + noncurrent + short-term borrowings',reason=reason,calculated=True,
                explanation='Commercial paper is not added again to short-term borrowings. Debt including capital/finance leases is not silently substituted. Review issuer financial notes for obligations outside this definition.')


def normalize_depth(bundle,cik,now,resolver=None):
    if any(int(bundle[k].get('cik',0))!=int(cik) for k in ('companyfacts','submissions')):raise ValueError('SEC evidence belongs to another company.')
    filings=filing_rows(bundle['submissions'],now);current=filings[-1]
    flows=[dict(key=key,unit='USD',**(capital_spending(bundle,filings,current,resolver) if key=='capital_spending' else dict(label=label,**trailing(bundle,filings,current,tags,resolver)))) for key,(label,tags) in FLOW.items()]
    indexed={row['key']:row for row in flows}
    cash,capex=indexed['operating_cash'],indexed['capital_spending']
    fcf=dict(key='free_cash_flow',label='Free cash flow (app calculation)',unit='USD',value=None,inputs=cash['inputs']+capex['inputs'],
             start=cash['start'],end=cash['end'],formula='Trailing operating cash flow − trailing cash capital spending',reason='Compatible cash-flow and capital-spending inputs are unavailable.',calculated=True)
    fcf['explanation']=capex['explanation'];fcf['spending_basis']=capex['spending_basis']
    if cash['value'] is not None and capex['value'] is not None and (cash['start'],cash['end'])==(capex['start'],capex['end']) and Decimal(capex['value'])>=0:
        with localcontext() as ctx:
            ctx.prec=28;fcf.update(value=decimal_text(Decimal(cash['value'])-Decimal(capex['value'])),reason=None)
    flows.append(fcf)
    revenue,income=indexed['revenue'],indexed['operating_income']
    margin=dict(key='operating_margin',label='Operating margin (app calculation)',unit='percent',value=None,inputs=revenue['inputs']+income['inputs'],
                start=revenue['start'],end=revenue['end'],formula='Trailing operating income / trailing revenue × 100',reason='Compatible positive revenue and operating-income inputs are unavailable.',calculated=True)
    if revenue['value'] is not None and income['value'] is not None and (revenue['start'],revenue['end'])==(income['start'],income['end']) and Decimal(revenue['value'])>0:
        with localcontext() as ctx:
            ctx.prec=28;margin.update(value=decimal_text(Decimal(income['value'])/Decimal(revenue['value'])*100),reason=None)
    flows.append(margin)
    from .amendments import combined_evidence
    for derived,a,b in [(fcf,cash,capex),(margin,income,revenue)]:
        evidence=combined_evidence(a,b)
        if evidence and {f['accession'] for f in a['inputs']}!={f['accession'] for f in b['inputs']}:
            derived.update(value=None,reason='Inputs use different amended filing vintages.')
        elif derived['value'] is not None:derived.update(evidence)
    trend=[]
    for filing in filings:
        if not filing['form'].startswith('10-K'):continue
        projected=trailing(bundle,filings,filing,REVENUE,resolver)
        revenue=projected['inputs'][0] if projected['value'] is not None and len(projected['inputs'])==1 else None
        error=projected['reason']
        # Latest amendment for each period replaces the original, including a
        # gap when the amendment provides no compatible facts.
        row=dict(period_end=filing['end'].isoformat(),accession=filing['accessionNumber'],form=filing['form'],value=revenue['value'] if revenue else None,inputs=[revenue] if revenue else [],reason=error)
        if projected.get('filing_resolution'):row['filing_resolution']=projected['filing_resolution']
        trend=[r for r in trend if r['period_end']!=row['period_end']]+[row]
    debt=total_debt(bundle,current)
    if resolver:
        resolved,_=resolver.resolve(current,[debt],lambda earlier:[total_debt(bundle,earlier)])
        debt=resolved[0]
    urls={}
    for filing in filings:
        accession=filing['accessionNumber']
        try:urls[accession]=archive_url(cik,accession,filing['primaryDocument'])
        except ValueError:urls[accession]=f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace("-","")}/{accession}-index.html'
    for row in flows+[debt]+trend:
        for fact in row['inputs']:fact['filing_url']=urls.get(fact['accession'])
    return dict(method=METHOD,period_end=current['end'].isoformat(),trailing=flows,debt=debt,revenue_trend=trend[-5:],
                limitations=['Trailing values cover the explicit fiscal dates shown; a 52/53-week fiscal year is not a calendar-year estimate.',
                             'Annual/YTD bridges combine identified filing vintages. Restatement and accounting-policy consistency need the original notes; no price prediction is made.',
                             'Research calculations do not change saved monitoring definitions. Whole-company standard US-GAAP USD concepts only.'])


def present(conn,iid):
    if not one(conn,"SELECT 1 FROM sources WHERE id='sec-companyfacts' AND entitlement='sec-public'"):
        return dict(status='unavailable',reason='Structured filing source access is unavailable.')
    saved=one(conn,'SELECT p.id,p.payload,p.retrieved_at,c.cik,k.checked_at FROM sec_payload_current k JOIN source_payloads p ON p.id=k.payload_id AND p.instrument_id=k.instrument_id JOIN sec_companies c ON c.instrument_id=k.instrument_id WHERE k.instrument_id=%s',(iid,))
    if not saved:return dict(status='empty',reason='Refresh filings to prepare trailing results and borrowing information.')
    from .amendments import retained_resolver
    try:
        resolver=retained_resolver(conn,iid,saved['payload'],saved['cik'],saved['checked_at'])
        values=normalize_depth(saved['payload'],saved['cik'],saved['checked_at'],resolver)
    except ValueError:return dict(status='unavailable',reason='Retained SEC facts could not be normalized for these additional measures. The existing financial reports remain available.')
    return dict(status='available',payload_id=str(saved['id']),amendment_basis=resolver.basis_id,first_recorded_at=saved['retrieved_at'],checked_at=saved['checked_at'],**values)
