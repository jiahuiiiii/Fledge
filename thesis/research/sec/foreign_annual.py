"""Bounded standard-taxonomy, single-currency inputs for 20-F annual ratios.

No issuer rules, conversion, custom tags or quarterly interpretation of 6-Ks.
"""
from datetime import date
from decimal import Decimal

METHOD = 'sec-foreign-annual-1'
CURRENCIES = frozenset('USD CNY EUR GBP JPY HKD TWD KRW INR CAD CHF AUD NZD SGD SEK NOK DKK BRL MXN ZAR ILS PLN CZK HUF TRY IDR MYR THB PHP VND AED SAR CLP COP PEN ARS'.split())
TAXONOMIES = {
    'us-gaap': (('RevenueFromContractWithCustomerExcludingAssessedTax', 'Revenues', 'SalesRevenueNet'), ('OperatingIncomeLoss',)),
    'ifrs-full': (('Revenue',), ('ProfitLossFromOperatingActivities',)),
}


def basis(companyfacts, filing):
    """A unique same-filing revenue pair identifies a usable ratio basis.

    Convenience translations with only the current year cannot replace the
    currency containing the complete annual pair. Multiple complete bases stay
    ambiguous; a conflict never falls back to a less complete currency.
    """
    pools = {}
    for namespace, (revenue, income) in TAXONOMIES.items():
        for concept in revenue + income:
            for currency, values in companyfacts.get('facts', {}).get(namespace, {}).get(concept, {}).get('units', {}).items():
                if currency not in CURRENCIES: continue
                for row in values:
                    if (row.get('accn'), row.get('form'), row.get('filed')) != (filing['accessionNumber'], filing['form'], filing['filingDate']): continue
                    if not row.get('start') or not row.get('end'): continue
                    start, end = date.fromisoformat(row['start']), date.fromisoformat(row['end'])
                    value = Decimal(str(row['val']))
                    if not value.is_finite() or end < start or end > filing['filed'] or abs(value.adjusted()) > 100 or len(value.as_tuple().digits) > 100:
                        raise ValueError('Invalid foreign annual financial fact')
                    text = format(value, 'f')
                    if '.' in text: text = text.rstrip('0').rstrip('.')
                    pools.setdefault((namespace, currency), []).append(dict(namespace=namespace, concept=concept, unit=currency, value=text, start=start.isoformat(), end=end.isoformat(), accession=row['accn'], form=row['form'], filed=row['filed'], fy=row.get('fy'), fp=row.get('fp'), frame=row.get('frame')))
    pairs, currents = [], []
    for key, facts in pools.items():
        revenue = TAXONOMIES[key[0]][0]
        annual = [f for f in facts if f['concept'] in revenue and 350 <= (date.fromisoformat(f['end']) - date.fromisoformat(f['start'])).days + 1 <= 380]
        current = [f for f in annual if f['end'] == filing['end'].isoformat()]
        if not current: continue
        currents.append(key)
        # Conflicting annual totals still count as a complete candidate so they
        # cannot silently switch the calculation to another currency/taxonomy.
        if any(357 <= (date.fromisoformat(c['end']) - date.fromisoformat(p['end'])).days <= 373 and p['end'] < c['start'] and abs((date.fromisoformat(c['end']) - date.fromisoformat(c['start'])).days - (date.fromisoformat(p['end']) - date.fromisoformat(p['start'])).days) <= 7 for c in current for p in annual):
            pairs.append(key)
    choices = pairs or currents
    if len(choices) != 1:
        reason = 'Multiple currencies or accounting bases contain annual revenue; a unique comparison basis is unavailable.' if choices else 'No supported standard-taxonomy annual revenue currency is available.'
        return dict(method=METHOD, namespace=None, currency=None, facts=[], reason=reason)
    namespace, currency = choices[0]
    return dict(method=METHOD, namespace=namespace, currency=currency, facts=pools[choices[0]], reason=None)
