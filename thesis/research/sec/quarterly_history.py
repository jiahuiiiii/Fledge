"""Quarterly chart readings, including fourth quarters in annual reports.

No new acquisition or mutation. A missing Q4 may use an exact annual-minus-nine-
month calculation; currencies, concepts, fiscal dates and vintages must agree.
"""
from datetime import timedelta
from decimal import Decimal, localcontext

from .normalize import REVENUE
from .performance import collect, select, unique, duration, decimal_text
from .financial_depth import common_concept

DEFINITIONS = {
    'revenue': ('Revenue', REVENUE),
    'operating_income': ('Operating profit', ('OperatingIncomeLoss',)),
    'net_consolidated': ('Net result including non-controlling interests', ('ProfitLoss',)),
    'net_parent': ('Net income attributable to parent', ('NetIncomeLoss',)),
}
MISSING = 'No compatible whole-company USD fact in the selected filing.'


def reported_quarter(bundle, filing, tags):
    # Any reported quarter, including a non-USD fact, blocks a replacement.
    return any(r.get('accn') == filing['accessionNumber'] and r.get('form') == filing['form']
               and r.get('filed') == filing['filingDate'] and r.get('end') == filing['end'].isoformat()
               and r.get('start') and 70 <= duration(r) <= 110
               for tag in tags for values in bundle['companyfacts'].get('facts', {}).get('us-gaap', {}).get(tag, {}).get('units', {}).values() for r in values)


def quarter_metric(bundle, filings, current, tags):
    facts = collect(bundle, current, tags)
    fact, reason = select(facts, current, 'quarter', 'Business performance', tags)
    result = dict(value=fact['value'] if fact else None, inputs=[fact] if fact else [],
                  reason=reason, start=fact['start'] if fact else None,
                  end=current['end'].isoformat(), calculated=False, formula=None)
    if fact or reason != MISSING or reported_quarter(bundle, current, tags) or not current['form'].startswith('10-K'):
        return result
    # Amendment inheritance is handled by the existing resolver, not by mixing
    # a revised annual result with an earlier quarterly statement.
    if current['form'].endswith('/A'):
        return result
    annual, error = select(facts, current, 'annual', 'Business performance', tags)
    if not annual:
        return dict(result, reason=error)
    prior_filings = [f for f in filings if f['form'].startswith('10-Q')
                     and 70 <= (current['end'] - f['end']).days <= 110
                     and f['accepted_at'] <= current['accepted_at']]
    prior = prior_filings[-1] if prior_filings else None
    if not prior:
        return dict(result, reason='The matching first-nine-months filing is not saved.')
    if prior['form'].endswith('/A'):
        return dict(result, reason='The first-nine-months filing was amended; compatible fourth-quarter inputs are not established.')
    candidates = [f for f in collect(bundle, prior, tags) if f['start'] == annual['start']
                  and f['end'] == prior['end'].isoformat() and 240 <= duration(f) <= 300]
    ytd, error = unique(candidates, tags)
    inputs = [annual] + ([ytd] if ytd else [])
    if not ytd:
        return dict(result, inputs=inputs, reason=error)
    start = (prior['end'] + timedelta(days=1)).isoformat()
    inputs = common_concept(bundle, filings, inputs, tags)
    if len({f['concept'] for f in inputs}) != 1:
        return dict(result, inputs=inputs, start=start, reason='The annual and first-nine-months figures use different reporting labels; a fourth-quarter total has not been established.')
    # Both original inputs are retained, never replaced with a later comparative.
    with localcontext() as ctx:
        ctx.prec = 110
        value = decimal_text(Decimal(annual['value']) - Decimal(ytd['value']))
    return dict(value=value, inputs=inputs, reason=None, start=start, end=result['end'], calculated=True,
                formula='Reported fiscal year − reported first nine months',
                explanation='Fourth quarter calculated from the annual total and the first nine months of that same fiscal year. Both original reported figures are linked below.')


def period(bundle, filings, filing, resolver=None):
    metrics = {key: dict(key=key, label=label, unit='USD', **quarter_metric(bundle, filings, filing, tags))
               for key, (label, tags) in DEFINITIONS.items()}
    resolution = None
    if resolver and filing['form'].endswith('/A'):
        resolved, resolution = resolver.resolve(filing, list(metrics.values()), lambda earlier: period(bundle, filings, earlier)['metrics'])
        metrics = {m['key']: m for m in resolved}
    revenue = metrics['revenue']
    for key, metric in metrics.items():
        if key != 'revenue' and revenue['start'] and metric['value'] is not None and metric['start'] != revenue['start']:
            metric.update(value=None, reason='This figure covers different dates from the selected revenue quarter.')
    whole, parent = metrics['net_consolidated'], metrics['net_parent']
    net = whole if whole['value'] is not None or 'Conflicting' in (whole['reason'] or '') else parent
    metrics['net_income'] = dict(net, key='net_income')
    return dict(id=f'quarter:{filing["accessionNumber"]}', kind='quarter', start=revenue['start'],
                end=filing['end'].isoformat(), accession=filing['accessionNumber'], form=filing['form'],
                filed=filing['filingDate'], accepted_at=filing['accepted_at'], metrics=list(metrics.values()),
                **(dict(amendment_resolution=resolution) if resolution else {}))
