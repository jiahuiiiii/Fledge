"""Read-only competitor view over retained, permission-checked sources.

View choices do not change private peers or collect any source data.
"""
from thesis.db import transaction, rows, one
from thesis.research import fmp
from thesis.research.sec.performance import present as performance
from thesis.research.sec.guidance import present as guidance
from thesis.research.public_forecasts import current as public_forecasts

METHOD = 'competitor-position-1'
SUGGESTED = {'AVGO': ['NVDA', 'AMD', 'MRVL', 'MU', 'QCOM']}
SUGGESTION_URL = 'https://investors.broadcom.com/static-files/5975d33d-73b9-4e5f-9ded-c00bdee38d6e'


def context(owner, iid, peers=None):
    with transaction(owner, consistent=True) as conn:
        target = fmp.company(conn, iid)
        registered = rows(conn, 'SELECT i.id,i.symbol,i.name,c.cik FROM instruments i JOIN sec_companies c ON c.instrument_id=i.id ORDER BY i.symbol')
        catalogue = {r['symbol']: r for r in registered}
        directory = one(conn, 'SELECT listings FROM company_directory WHERE singleton')
        listings = {r['symbol']: r for r in (directory['listings'] or [])}
        selected = rows(conn, 'SELECT symbol,rationale FROM peer_selections WHERE owner_id=%s AND instrument_id=%s ORDER BY symbol', (owner, iid))
        suggestions = fmp.present(conn, 'peers', target['symbol'])
        candidates = list(catalogue.values()) + (suggestions.get('data') or {}).get('candidates', [])
        for symbol in SUGGESTED.get(target['symbol'], []):
            if symbol in listings and symbol not in catalogue:
                candidates.append(listings[symbol])
        permitted = {r['symbol'] for r in candidates} | {s for s in listings if s.isalpha() and s.isupper() and len(s) <= 5}
        suggested = [s for s in SUGGESTED.get(target['symbol'], []) if s in permitted]
        if peers is None:
            peers = [r['symbol'] for r in selected] or suggested
            basis = 'saved' if selected else 'suggested' if suggested else 'unselected'
        else:
            basis = 'view'
        if len(peers) > 8 or len(set(peers)) != len(peers):
            raise ValueError('Choose up to eight different comparison companies.')
        for symbol in peers:
            fmp.symbol_value(symbol)
            if symbol not in permitted or symbol == target['symbol']:
                raise ValueError('Choose a registered company or a saved FMP suggestion.')
            candidate = catalogue.get(symbol) or listings.get(symbol)
            profile = fmp.present(conn, 'profile', symbol).get('data')
            if (candidate and candidate['cik'] == target['cik']) or (profile and profile['cik'] == str(target['cik'])):
                raise ValueError('Another share class of the same issuer is not an independent competitor.')
        members = []
        for symbol in [target['symbol']] + peers:
            company = catalogue.get(symbol)
            company_id = str(company['id']) if company else None
            members.append(dict(
                symbol=symbol, name=company['name'] if company else listings.get(symbol, {}).get('name', symbol),
                performance=performance(conn, company_id) if company_id else None,
                consensus=fmp.present(conn, 'estimates', symbol),
                public_forecasts=public_forecasts(conn, company_id) if company_id else None,
                management=guidance(conn, company_id) if company_id else None,
                rationale=next((r['rationale'] for r in selected if r['symbol'] == symbol), None),
            ))
        unique = {r['symbol']: dict(symbol=r['symbol'], name=r['name']) for r in candidates if r['symbol'] != target['symbol']}
        return dict(method=METHOD, symbol=target['symbol'], members=members,
                    peers=peers, basis=basis, candidates=list(unique.values()),
                    suggestion_source=SUGGESTION_URL if target['symbol'] in SUGGESTED else None,
                    limitation='Chosen peers are a comparison group, not the whole sector. Whole-company business mix, fiscal dates and accounting definitions can differ. This read does not collect data or save private peer choices.')
