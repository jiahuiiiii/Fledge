"""Read-only financial chart series and exact comparisons over retained SEC facts.

This presentation does not rewrite performance, monitoring or saved AI results.
"""
from decimal import Decimal, localcontext
from thesis.db import one
from .normalize import filing_rows, REVENUE
from .performance import collect, select, decimal_text
from .financial_depth import trailing, total_debt
from .disclosure_text import archive_url

METHOD = 'sec-financial-story-1'
MISSING = 'No compatible whole-company USD fact in the selected filing.'
BALANCES = {
    'assets': ('Total assets', ('Assets',)),
    'liabilities': ('Total liabilities', ('Liabilities',)),
    'current_assets': ('Current assets', ('AssetsCurrent',)),
    'current_liabilities': ('Current liabilities', ('LiabilitiesCurrent',)),
    'noncurrent_assets': ('Noncurrent assets', ('AssetsNoncurrent',)),
    'noncurrent_liabilities': ('Noncurrent liabilities', ('LiabilitiesNoncurrent',)),
    'cash': ('Cash & equivalents', ('CashAndCashEquivalentsAtCarryingValue',)),
    'receivables': ('Receivables', ('AccountsReceivableNetCurrent',)),
    'inventory': ('Inventory', ('InventoryNet',)),
    'property': ('Property, plant & equipment', ('PropertyPlantAndEquipmentNet',)),
    'goodwill': ('Goodwill', ('Goodwill',)),
    'intangibles': ('Finite-lived intangible assets', ('FiniteLivedIntangibleAssetsNet',)),
    'payables': ('Accounts payable', ('AccountsPayableCurrent',)),
}

def calculation(key, label, left, right, operator, formula, *, percent=False, nonnegative=False):
    from .amendments import combined_evidence
    evidence = combined_evidence(left,right)
    valid = (left['value'] is not None and right['value'] is not None
             and (left['start'], left['end']) == (right['start'], right['end'])
             and (not evidence or {f['accession'] for f in left['inputs']} == {f['accession'] for f in right['inputs']}))
    value = None
    reason = 'Matching, compatible inputs are unavailable.'
    if valid:
        a, b = Decimal(left['value']), Decimal(right['value'])
        if operator == 'ratio' and b <= 0:
            reason = 'A positive matching denominator is required; zero or negative values are not a usable ratio.'
        else:
            with localcontext() as ctx:
                ctx.prec = 28 if operator == 'ratio' else 110
                result = a - b if operator == 'subtract' else a / b * (100 if percent else 1)
                if nonnegative and result < 0:
                    reason = 'The reported parts exceed the total; this breakdown is withheld.'
                else:
                    try: value, reason = decimal_text(result), None
                    except ValueError: reason = 'The calculated amount exceeds supported decimal precision.'
    return dict(key=key, label=label, value=value, unit='percent' if percent else 'times' if operator == 'ratio' else 'USD',
                start=left['start'], end=left['end'], inputs=left['inputs'] + right['inputs'],
                formula=formula, calculated=True, reason=reason,**(evidence if value is not None else {}))


def income_period(bundle, filings, filing, kind, resolver=None):
    rows = {}
    for key, label, tags in [
        ('revenue', 'Revenue', REVENUE),
        ('operating_income', 'Operating profit', ('OperatingIncomeLoss',)),
        ('operating_cash', 'Operating cash flow', ('NetCashProvidedByUsedInOperatingActivities',)),
        ('capital_spending', 'Cash capital spending', ('PaymentsToAcquirePropertyPlantAndEquipment',)),
        ('net_consolidated', 'Net result including non-controlling interests', ('ProfitLoss',)),
        ('net_parent', 'Net income attributable to parent', ('NetIncomeLoss',)),
        ('interest', 'Reported non-operating interest expense', ('InterestExpenseNonOperating',)),
    ]:
        rows[key] = dict(key=key, label=label, unit='USD', **trailing(bundle, filings, filing, tags,resolver))
    revenue = rows['revenue']
    for key, row in rows.items():
        if key != 'revenue' and row['value'] is not None and (row['start'], row['end']) != (revenue['start'], revenue['end']):
            row.update(value=None, reason='This figure covers different dates from the selected revenue period.')
    # Match the existing income-flow policy: a conflicting consolidated result
    # cannot be concealed by a parent-only result. Definitions remain visible.
    consolidated = rows['net_consolidated']
    parent = rows['net_parent']
    net = consolidated if consolidated['value'] is not None or 'Conflicting' in (consolidated['reason'] or '') else parent
    rows['net_income'] = dict(net, key='net_income')
    cash, capex = rows['operating_cash'], rows['capital_spending']
    if capex['value'] is not None and Decimal(capex['value']) < 0:
        capex = dict(capex, value=None, reason='Negative capital spending is unsupported by this free-cash-flow convention.')
    rows['free_cash_flow'] = calculation('free_cash_flow', 'Free cash flow', cash, capex, 'subtract', 'Operating cash flow − cash capital spending')
    rows['net_margin'] = calculation('net_margin', 'Net result / revenue', rows['net_income'], rows['revenue'], 'ratio', 'Selected net result / matching revenue × 100', percent=True)
    rows['operating_margin'] = calculation('operating_margin', 'Operating margin', rows['operating_income'], rows['revenue'], 'ratio', 'Operating income / matching revenue × 100', percent=True)
    rows['interest_coverage'] = calculation('interest_coverage', 'Operating profit / non-operating interest expense', rows['operating_income'], rows['interest'], 'ratio', 'Operating profit / matching non-operating interest expense')
    return dict(id=f'{kind}:{filing["accessionNumber"]}', kind=kind, end=filing['end'].isoformat(),
                start=rows['revenue']['start'], accession=filing['accessionNumber'], form=filing['form'],
                filed=filing['filingDate'], accepted_at=filing['accepted_at'], metrics=list(rows.values()))


def balance_period(bundle, filing):
    metrics = {}
    for key, (label, tags) in BALANCES.items():
        fact, reason = select(collect(bundle, filing, tags), filing, 'quarter', 'Balance sheet', tags)
        metrics[key] = dict(key=key, label=label, value=fact['value'] if fact else None, unit='USD',
                            start=None, end=filing['end'].isoformat(), inputs=[fact] if fact else [], reason=reason, calculated=False)
    for target, left, right in [('noncurrent_assets', 'assets', 'current_assets'), ('noncurrent_liabilities', 'liabilities', 'current_liabilities')]:
        if metrics[target]['reason'] == MISSING:
            metrics[target] = calculation(target, metrics[target]['label'], metrics[left], metrics[right], 'subtract',
                                          f'{metrics[left]["label"]} − {metrics[right]["label"]}', nonnegative=True)
    metrics['equity'] = calculation('equity', 'Book equity including non-controlling interests', metrics['assets'], metrics['liabilities'], 'subtract', 'Total assets − total liabilities')
    metrics['debt'] = dict(total_debt(bundle, filing), key='debt')
    metrics['net_debt'] = calculation('net_debt', 'Borrowing less cash', metrics['debt'], metrics['cash'], 'subtract', 'Combined borrowing − cash & equivalents')
    metrics['debt_equity'] = calculation('debt_equity', 'Borrowing / book equity', metrics['debt'], metrics['equity'], 'ratio', 'Combined borrowing / (total assets − total liabilities) × 100', percent=True)
    metrics['working_capital'] = calculation('working_capital', 'Working capital', metrics['current_assets'], metrics['current_liabilities'], 'subtract', 'Current assets − current liabilities')
    for key, total_key, parts in [
        ('other_assets', 'assets', ['cash', 'receivables', 'inventory', 'property', 'goodwill', 'intangibles']),
        ('other_liabilities', 'liabilities', ['debt', 'payables']),
    ]:
        known = [metrics[p] for p in parts if metrics[p]['value'] is not None]
        valid = all(Decimal(row['value']) >= 0 for row in known)
        with localcontext() as ctx:
            ctx.prec = 110
            subtotal = dict(key='subtotal', label='Plotted reported categories', unit='USD', start=None,
                            end=filing['end'].isoformat(), value=str(sum((Decimal(row['value']) for row in known), Decimal(0))) if valid else None,
                            inputs=[fact for row in known for fact in row['inputs']])
        label = 'Other & unclassified assets' if total_key == 'assets' else 'Other & unclassified liabilities'
        metrics[key] = calculation(key, label, metrics[total_key], subtotal, 'subtract', 'Reported total − the plotted reported categories; includes missing or unclassified categories.', nonnegative=True)
    return dict(id=filing['accessionNumber'], end=filing['end'].isoformat(), accession=filing['accessionNumber'],
                form=filing['form'], filed=filing['filingDate'], accepted_at=filing['accepted_at'], metrics=list(metrics.values()))


def normalize_story(bundle, cik, now,resolver=None):
    if any(int(bundle[key].get('cik', 0)) != int(cik) for key in ('companyfacts', 'submissions')):
        raise ValueError('SEC evidence belongs to another company.')
    filings = filing_rows(bundle['submissions'], now)
    chosen = {}
    for filing in filings:
        chosen[filing['end']] = filing
    chosen = list(chosen.values())[-40:]
    annual_by_end = {}
    for filing in filings:
        if filing['form'].startswith('10-K'):
            annual_by_end[filing['end']] = filing
    annual = list(annual_by_end.values())[-12:]
    annual_rows = [income_period(bundle, filings, filing, 'annual',resolver) for filing in annual]
    trailing_rows = [income_period(bundle, filings, filing, 'trailing',resolver) for filing in chosen]
    balances = [balance_period(bundle, filing) for filing in chosen]
    if resolver:
        for period,filing in zip(balances,chosen):
            period['metrics'],resolution=resolver.resolve(filing,period['metrics'],lambda earlier:balance_period(bundle,earlier)['metrics'])
            if resolution:period['amendment_resolution']=resolution
    urls = {}
    for filing in filings:
        accession = filing['accessionNumber']
        try: urls[accession] = archive_url(cik, accession, filing['primaryDocument'])
        except ValueError: urls[accession] = f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace("-", "")}/{accession}-index.html'
    for period in annual_rows + trailing_rows + balances:
        period['filing_url'] = urls[period['accession']]
        for metric in period['metrics']:
            for fact in metric['inputs']: fact['filing_url'] = urls.get(fact['accession'])
    return dict(method=METHOD, annual=annual_rows, trailing=trailing_rows, balances=balances,
                limitations=['Saved recent filing coverage only; missing years and values stay unknown.',
                             'Annual and trailing periods remain separate. Trailing bridges follow the existing fiscal-date and same-concept checks.',
                             'Net results including non-controlling interests and parent-only income are different definitions.',
                             'Borrowing excludes lease obligations under the existing definition; liabilities are not debt.',
                             'Book equity is assets minus liabilities including non-controlling interests, not market value.',
                             'Ratios describe reported relationships, not credit ratings, earnings quality or investment recommendations.'])


def present(conn, iid):
    if not one(conn, "SELECT 1 FROM sources WHERE id='sec-companyfacts' AND entitlement='sec-public'"):
        return dict(status='unavailable', reason='Structured filing source access is unavailable.', method=METHOD)
    saved = one(conn, 'SELECT p.id,p.payload,p.retrieved_at,c.cik,k.checked_at FROM sec_payload_current k JOIN source_payloads p ON p.id=k.payload_id AND p.instrument_id=k.instrument_id JOIN sec_companies c ON c.instrument_id=k.instrument_id WHERE k.instrument_id=%s', (iid,))
    if not saved:
        return dict(status='empty', reason='Collect company filings to see financial history.', method=METHOD)
    from .amendments import retained_resolver
    try:
        resolver=retained_resolver(conn,iid,saved['payload'],saved['cik'],saved['checked_at'])
        result = normalize_story(saved['payload'], saved['cik'], saved['checked_at'],resolver)
    except (ValueError, KeyError, TypeError, OverflowError):
        return dict(status='unavailable', reason='The saved filing facts are unsupported for this financial view.', method=METHOD)
    return dict(status='available', payload_id=str(saved['id']), amendment_basis=resolver.basis_id, first_recorded_at=saved['retrieved_at'], checked_at=saved['checked_at'], **result)
