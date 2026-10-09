"""Read-only income-statement flows over retained SEC facts.

Exact decimal reconciliation precedes visualization. This is a new presentation
method; existing financial calculations, snapshots and monitoring are unchanged.
"""
from decimal import Decimal, localcontext
from .normalize import REVENUE, filing_rows
from .performance import collect, select, decimal_text
from .financial_depth import trailing
from .disclosure_text import archive_url
from thesis.db import one

METHOD = 'sec-income-flow-1'
DEFINITIONS = {
    'revenue': ('Revenue', REVENUE),
    'cost': ('Cost of revenue', ('CostOfRevenue', 'CostOfGoodsAndServicesSold')),
    'gross': ('Gross profit', ('GrossProfit',)),
    'operating': ('Operating profit', ('OperatingIncomeLoss',)),
    'expenses': ('Operating expenses', ('OperatingExpenses',)),
    'net': ('Net result including non-controlling interests', ('ProfitLoss',)),
    'parent_net': ('Net income attributable to parent', ('NetIncomeLoss',)),
    'research': ('Research & development', ('ResearchAndDevelopmentExpense',)),
    'selling': ('Selling, general & administrative', ('SellingGeneralAndAdministrativeExpense',)),
}


def difference(key, label, left, right):
    inputs = left['inputs'] + right['inputs']
    valid = left['value'] is not None and right['value'] is not None and (left['start'], left['end']) == (right['start'], right['end'])
    with localcontext() as ctx:
        ctx.prec = 110
        value = decimal_text(Decimal(left['value']) - Decimal(right['value'])) if valid else None
    return dict(key=key, label=label, value=value, unit='USD', inputs=inputs,
                start=left['start'], end=left['end'], calculated=True,
                formula=f"{left['label']} − {right['label']}",
                reason=None if valid else 'Compatible figures for the same period are unavailable.')


def build_period(bundle, filings, current, kind, cik):
    metrics = {}
    for key, (label, tags) in DEFINITIONS.items():
        if kind == 'trailing':
            row = trailing(bundle, filings, current, tags)
        else:
            fact, reason = select(collect(bundle, current, tags), current, kind, 'Business performance', tags)
            row = dict(value=fact['value'] if fact else None, inputs=[fact] if fact else [],
                       reason=reason, start=fact['start'] if fact else None,
                       end=current['end'].isoformat(), calculated=False, formula=None)
        metrics[key] = dict(key=key, label=label, unit='USD', **row)
    revenue = metrics['revenue']
    for key, row in metrics.items():
        if key != 'revenue' and row['value'] is not None and (row['start'], row['end']) != (revenue['start'], revenue['end']):
            row.update(value=None, reason='This figure covers different dates from revenue.')
    # Only absent facts may be derived; conflicts/unsupported facts are not masked.
    for target, left, right in [('gross', 'revenue', 'cost'), ('cost', 'revenue', 'gross'), ('expenses', 'gross', 'operating')]:
        row = metrics[target]
        if row['value'] is None and not row['inputs'] and row['reason'] == 'No compatible whole-company USD fact in the selected filing.':
            metrics[target] = difference(target, row['label'], metrics[left], metrics[right])
    net = metrics['net'] if metrics['net']['value'] is not None else metrics['parent_net']
    # Do not hide an unusable consolidated result behind a parent-only result.
    if metrics['net']['reason'] and 'Conflicting' in metrics['net']['reason']:
        net = metrics['net']
    metrics['net_result'] = dict(net, key='net_result')
    metrics['net_items'] = difference('net_items', 'Tax & other net items', metrics['operating'], net)
    metrics['net_items']['explanation'] = 'The net difference from operating profit to the selected net result. It can include tax, interest, other gains/losses, discontinued operations and, for a parent-only result, non-controlling interests. It is not a reported expense category.'
    nodes = []; links = []; reason = None; notes = []
    core = [metrics[k] for k in ['revenue', 'cost', 'gross', 'operating', 'expenses']]
    if any(row['value'] is None for row in core):
        reason = 'Some compatible revenue, cost or profit figures are missing. Available figures remain below.'
    elif Decimal(revenue['value']) <= 0 or any(Decimal(row['value']) < 0 for row in core):
        reason = 'This period contains a loss, negative cost or non-positive revenue. Signed figures are shown below instead of positive-width flows.'
    else:
        with localcontext() as ctx:
            ctx.prec = 110
            if Decimal(revenue['value']) != Decimal(metrics['cost']['value']) + Decimal(metrics['gross']['value']) or Decimal(metrics['gross']['value']) != Decimal(metrics['expenses']['value']) + Decimal(metrics['operating']['value']):
                reason = 'The reported figures do not exactly reconcile. Flow widths are withheld; inspect the original figures below.'
    if not reason:
        nodes = [dict(metrics[k], column=column, tone=tone) for k, column, tone in [
            ('revenue', 0, 'revenue'), ('gross', 1, 'profit'), ('cost', 1, 'expense'),
            ('operating', 2, 'profit'), ('expenses', 2, 'expense')]]
        links = [dict(source=a, target=b, value=metrics[b]['value']) for a, b in [
            ('revenue', 'gross'), ('revenue', 'cost'), ('gross', 'operating'), ('gross', 'expenses')]]
        if net['value'] is not None and Decimal(net['value']) >= 0 and metrics['net_items']['value'] is not None and Decimal(metrics['net_items']['value']) >= 0:
            nodes += [dict(metrics[k], column=3, tone=tone) for k, tone in [('net_result', 'profit'), ('net_items', 'expense')]]
            links += [dict(source='operating', target=k, value=metrics[k]['value']) for k in ['net_result', 'net_items']]
        else:
            notes.append('The flow ends at operating profit: the net result is missing, a loss, or increased by net gains. Its available signed figures remain below.')
    expenses = metrics['expenses']; parts = [metrics['research'], metrics['selling']]
    expense_parts = []
    if expenses['value'] is not None and all(row['value'] is not None and Decimal(row['value']) >= 0 for row in parts):
        with localcontext() as ctx:
            ctx.prec = 110
            subtotal = sum((Decimal(row['value']) for row in parts), Decimal(0))
        if Decimal(expenses['value']) >= subtotal:
            part_total = dict(parts[0], label='Research & development + selling, general & administrative', value=decimal_text(subtotal), inputs=parts[0]['inputs'] + parts[1]['inputs'])
            rest = difference('remaining_expenses', 'Remaining operating expenses', expenses, part_total)
            rest['explanation'] = 'Calculated remainder; the original filing explains the individual categories. No missing category is assumed to be zero.'
            expense_parts = parts + [rest]
    urls = {}
    for filing in filings:
        accession = filing['accessionNumber']
        try: urls[accession] = archive_url(cik, accession, filing['primaryDocument'])
        except ValueError: urls[accession] = f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace("-", "")}/{accession}-index.html'
    for row in list(metrics.values()) + expense_parts:
        for fact in row['inputs']: fact['filing_url'] = urls.get(fact['accession'])
    return dict(id=f"{kind}:{current['accessionNumber']}", kind=kind, start=revenue['start'], end=revenue['end'],
                accession=current['accessionNumber'], form=current['form'], filed=current['filingDate'],
                accepted_at=current['accepted_at'], metrics=list(metrics.values()), nodes=nodes, links=links,
                chartable=not reason, reason=reason, notes=notes, expense_parts=expense_parts)


def normalize_flow(bundle, cik, now):
    if any(int(bundle[key].get('cik', 0)) != int(cik) for key in ['companyfacts', 'submissions']):
        raise ValueError('SEC evidence belongs to another company.')
    filings = filing_rows(bundle['submissions'], now)
    chosen = {}
    for filing in filings:
        kind = 'annual' if filing['form'].startswith('10-K') else 'quarter'
        chosen[(kind, filing['end'])] = filing
    periods = []
    for kind in ['annual', 'quarter']:
        selected = [(key, value) for key, value in chosen.items() if key[0] == kind][-5:]
        for _, filing in reversed(selected):
            periods.append(build_period(bundle, filings, filing, kind, cik))
    if filings[-1]['form'].startswith('10-Q'):
        periods.insert(0, build_period(bundle, filings, filings[-1], 'trailing', cik))
    periods.sort(key=lambda p: (p['end'], p['kind'] == 'trailing'), reverse=True)
    return dict(method=METHOD, periods=periods,
                limitations=['Income-statement revenue and profit are not cash receipts and payments.',
                             'All connected figures share explicit USD fiscal dates. Missing values are not zero; unreconciled or negative flows are withheld.',
                             'Trailing periods use the existing prior annual + current YTD − comparable prior YTD bridge. Original filing vintages and accounting-policy changes need review.',
                             'Tax & other net items and remaining operating expenses are calculated differences, not separately reported categories.'])


def present(conn, iid):
    if not one(conn, "SELECT 1 FROM sources WHERE id='sec-companyfacts' AND entitlement='sec-public'"):
        return dict(status='unavailable', periods=[], reason='Structured filing source access is unavailable.', method=METHOD)
    saved = one(conn, 'SELECT p.id,p.payload,p.retrieved_at,c.cik,k.checked_at FROM sec_payload_current k JOIN source_payloads p ON p.id=k.payload_id AND p.instrument_id=k.instrument_id JOIN sec_companies c ON c.instrument_id=k.instrument_id WHERE k.instrument_id=%s', (iid,))
    if not saved:
        return dict(status='empty', periods=[], reason='Collect company filings to see the revenue and expense flow.', method=METHOD)
    try: result = normalize_flow(saved['payload'], saved['cik'], saved['checked_at'])
    except (ValueError, KeyError):
        return dict(status='unavailable', periods=[], reason='The saved filing facts are unsupported for this flow. Existing financial reports remain available.', method=METHOD)
    return dict(status='available', payload_id=str(saved['id']), first_recorded_at=saved['retrieved_at'], checked_at=saved['checked_at'], **result)
