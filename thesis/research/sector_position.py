"""Read-only competitor view over retained, permission-checked sources.

View choices do not change private peers or collect any source data.
"""
from thesis.db import transaction, rows, one
from thesis.research import fmp
from thesis.research.sec.performance import present as performance
from thesis.research.sec.guidance import present as guidance
from thesis.research.public_forecasts import current as public_forecasts
from datetime import datetime, timedelta, timezone

METHOD = 'competitor-position-1'
SUGGESTED = {'AVGO': ['NVDA', 'AMD', 'MRVL', 'MU', 'QCOM']}
SUGGESTION_URL = 'https://investors.broadcom.com/static-files/5975d33d-73b9-4e5f-9ded-c00bdee38d6e'


def vendor_status(suggestions):
    """What the last FMP similar-companies check did, so a refused or empty check is explained."""
    state = suggestions.get('source_status') or {}
    attempt = state.get('last_attempt_at')
    return dict(
        status=suggestions.get('status'),
        checked_at=suggestions.get('checked_at'),
        last_attempt_at=attempt,
        error=state.get('error'),
        next_attempt_at=(attempt + (timedelta(minutes=5) if state.get('error') and not (state.get('last_success_at') and state['last_success_at'] >= attempt) else timedelta(hours=1))) if attempt else None,
        count=len((suggestions.get('data') or {}).get('candidates') or []),
    )


def filing_status(conn, iid, saved):
    """Explain collection independently of whether an annual metric is usable."""
    def result(status, message, can_fetch=False):
        return dict(status=status, message=message, can_fetch=can_fetch)
    if saved and saved['status']=='unavailable':
        return result('unavailable',saved['reason'])
    if not iid:
        if not one(conn,"SELECT 1 FROM sources WHERE id='sec-companyfacts' AND entitlement='sec-public'"):
            return result('unavailable','Structured filing source access is unavailable.')
        return result('not_collected','Financial data has not been collected.',True)
    state=one(conn,'SELECT last_attempt_at,lease_until,last_error FROM sec_refresh_state WHERE instrument_id=%s',(iid,))
    run=one(conn,'SELECT active,steps FROM research_loads WHERE instrument_id=%s ORDER BY created_at DESC,id DESC LIMIT 1',(iid,))
    pending=run and run['active'] and any(s['key']=='filings' and s['status'] in ('queued','running') for s in run['steps'])
    if pending or (state and state['lease_until'] and state['lease_until']>datetime.now(timezone.utc)):
        return result('loading','Fetching financial data…')
    annual=(saved or {}).get('reports',{}).get('annual')
    if annual:return result('ready','Saved annual financials available.')
    if state and state['last_error']:return result('failed',state['last_error'],True)
    if state and state['lease_until']:return result('failed','The last financial-data check did not finish.',True)
    if state and state['last_attempt_at']:return result('no_report','No supported annual report was found in the saved data.',True)
    return result('not_collected','Financial data has not been collected.',True)


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
        # Similar companies from the vendor (exchange, sector and size), largest first.
        # They are a starting point to review, never a statement about competition.
        def same_issuer(symbol):
            candidate = catalogue.get(symbol) or listings.get(symbol)
            profile = fmp.present(conn, 'profile', symbol).get('data')
            return bool((candidate and candidate.get('cik') == target['cik']) or (profile and profile['cik'] == str(target['cik'])))
        vendor_pool = sorted(((suggestions.get('data') or {}).get('candidates') or []), key=lambda r: -float(r.get('market_cap') or 0))
        vendor, issuers = [], set()
        for r in vendor_pool:
            if r['symbol'] == target['symbol'] or same_issuer(r['symbol']):
                continue
            known = catalogue.get(r['symbol']) or listings.get(r['symbol']) or {}
            if known.get('cik') in issuers:  # a second share class is not another competitor
                continue
            issuers.add(known.get('cik'))
            vendor.append(r['symbol'])
        vendor = vendor[:5]
        if peers is None:
            peers = [r['symbol'] for r in selected] or suggested or vendor
            basis = 'saved' if selected else 'suggested' if peers else 'unselected'
            origin = 'saved' if selected else 'curated' if suggested else 'fmp' if vendor else None
        else:
            basis = 'view'
            origin = None
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
            saved=performance(conn, company_id, resolve_amendments=True) if company_id else None
            members.append(dict(
                symbol=symbol, name=company['name'] if company else listings.get(symbol, {}).get('name', symbol),
                instrument_id=company_id, performance=saved, filing_status=filing_status(conn,company_id,saved),
                consensus=fmp.present(conn, 'estimates', symbol),
                public_forecasts=public_forecasts(conn, company_id) if company_id else None,
                management=guidance(conn, company_id) if company_id else None,
                rationale=next((r['rationale'] for r in selected if r['symbol'] == symbol), None),
            ))
        unique = {r['symbol']: dict(symbol=r['symbol'], name=r['name']) for r in candidates if r['symbol'] != target['symbol']}
        return dict(method=METHOD, symbol=target['symbol'], members=members,
                    peers=peers, basis=basis, suggestion_origin=origin, vendor_suggestions=vendor, vendor_status=vendor_status(suggestions), candidates=list(unique.values()),
                    suggestion_source=SUGGESTION_URL if target['symbol'] in SUGGESTED else None,
                    limitation='Chosen peers are a comparison group, not the whole sector. Whole-company business mix, fiscal dates and accounting definitions can differ. This read does not collect data or save private peer choices.')
