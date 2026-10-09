"""Bounded vendor consensus and reviewed comparison peers, without AI calls."""
from datetime import date,datetime,timedelta,timezone
from decimal import Decimal,InvalidOperation
import hashlib,json,re,time
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit
from uuid import uuid4,uuid5,NAMESPACE_URL
import httpx
from psycopg.types.json import Jsonb
from thesis.config import DATA,ROOT
from thesis.db import transaction,one,rows
from thesis.providers.settings import settings
from thesis.service import Conflict

DATASETS={'profile':('profile','fmp-profile'),'peers':('stock-peers','fmp-peers'),'estimates':('analyst-estimates','fmp-estimates'),'ratios':('ratios-ttm','fmp-ratios')}
METHOD='fmp-research-1'


class ProviderFailure(ValueError):pass


def number(raw,*,positive=False):
    try:
        value=Decimal(str(raw))
        if isinstance(raw,bool) or not value.is_finite() or abs(value.adjusted())>30 or (positive and value<=0):return None
        text=format(value,'f');return text.rstrip('0').rstrip('.') if '.' in text else text
    except (ValueError,InvalidOperation):return None


def symbol_value(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Z][A-Z0-9.-]{0,14}',value):raise ValueError('Unsupported company symbol.')
    return value


def allowed(conn,dataset):
    return bool(one(conn,"SELECT 1 FROM sources WHERE id=%s AND entitlement='fmp-local'",(DATASETS[dataset][1],)))


def normalize(dataset,payload,symbol):
    if not isinstance(payload,list) or len(payload)>100:raise ProviderFailure('FMP did not return a supported dataset.')
    if dataset=='peers':
        result=[];seen={symbol}
        for row in payload:
            peer=symbol_value(row.get('symbol'))
            if peer in seen:continue
            seen.add(peer)
            result.append(dict(symbol=peer,name=str(row.get('companyName',''))[:200],market_cap=number(row.get('mktCap'),positive=True),currency=None))
        return dict(candidates=result[:20],basis='FMP groups companies by exchange, sector and market size. These are suggestions to review; product competition is not established.',method=METHOD)
    if any(not isinstance(row,dict) or row.get('symbol')!=symbol for row in payload):raise ProviderFailure('FMP returned another company.')
    if dataset=='profile':
        if len(payload)!=1:raise ProviderFailure('FMP company identity is missing or ambiguous.')
        r=payload[0];cik=str(r.get('cik','')).lstrip('0')
        if not cik.isdigit():raise ProviderFailure('FMP did not provide an issuer identity.')
        return dict(symbol=symbol,name=str(r.get('companyName',''))[:200],cik=cik,sector=str(r.get('sector',''))[:120],industry=str(r.get('industry',''))[:150],currency=r.get('currency') if re.fullmatch('[A-Z]{3}',str(r.get('currency',''))) else None,
                    price=number(r.get('price'),positive=True),market_cap=number(r.get('marketCap'),positive=True),method=METHOD,
                    limitation='Vendor classification and values, first observed at retrieval. Provider quote time is not supplied; the description is not used as original-company evidence.')
    if dataset=='ratios':
        if len(payload)!=1:raise ProviderFailure('FMP trailing ratios are missing or ambiguous.')
        r=payload[0]
        return dict(symbol=symbol,period='TTM',basis='FMP vendor convention; GAAP/adjusted earnings convention is not established by this response.',metrics=[dict(key=key,label=label,value=number(r.get(field),positive=True),field=field,reason=None if number(r.get(field),positive=True) else 'No positive usable vendor ratio. Negative/zero P/E is not ranked.') for key,label,field in [('pe','P/E (TTM)','priceToEarningsRatioTTM'),('ps','P/S (TTM)','priceToSalesRatioTTM')]],method=METHOD)
    forecasts=[];periods=set()
    for r in payload:
        end=date.fromisoformat(r.get('date',''))
        if end in periods:raise ProviderFailure('FMP supplied duplicate forecast periods.')
        periods.add(end);metrics=[]
        for key,prefix in [('revenue','revenue'),('eps','eps')]:
            low,average,high=(number(r.get(prefix+suffix)) for suffix in ('Low','Avg','High'))
            if all(v is not None for v in (low,average,high)) and not Decimal(low)<=Decimal(average)<=Decimal(high):raise ProviderFailure('FMP forecast range is inconsistent.')
            count=r.get('numAnalystsRevenue' if key=='revenue' else 'numAnalystsEps')
            if isinstance(count,bool) or not isinstance(count,int) or count<1:count=None
            metrics.append(dict(key=key,low=low,average=average,high=high,analysts=count))
        forecasts.append(dict(period_end=end.isoformat(),period_type='annual',currency=r.get('currency') if re.fullmatch('[A-Z]{3}',str(r.get('currency',''))) else None,metrics=metrics))
    return dict(forecasts=sorted(forecasts,key=lambda r:r['period_end']),method=METHOD,
                limitation='Analyst consensus is distinct from management guidance and price targets. Forecast vintage is first observed at collection, not a historical pre-release forecast. Missing currency or earnings convention prevents a comparable actual-results verdict.')


def fetch(dataset,symbol,*,transport=None):
    endpoint,_=DATASETS[dataset];values=settings()
    if transport is None and (DATA!=ROOT/'.local' or values.get('THESIS_LIVE_DATA_ENABLED')!='true'):raise ProviderFailure('FMP loading is disabled in this installation.')
    key=values.get('FMP_API_KEY','')
    if not key and transport is None:raise ProviderFailure('Add an FMP API key to check endpoint access.')
    provider='fmp:'+dataset;now=datetime.now(timezone.utc)
    with transaction(source=True) as conn:
        for name in ('fmp:global',provider):conn.execute('INSERT INTO provider_clocks(provider) VALUES(%s) ON CONFLICT DO NOTHING',(name,))
        clocks=rows(conn,'SELECT * FROM provider_clocks WHERE provider=ANY(%s) ORDER BY provider FOR UPDATE',(['fmp:global',provider],))
        if any(c['denied'] for c in clocks):raise ProviderFailure('FMP access to this capability is restricted. Saved data remains; no automatic retry.')
        if any(c['blocked_until'] and c['blocked_until']>now for c in clocks):raise Conflict('FMP is paused after an access or rate-limit response.')
        clock=next(c for c in clocks if c['provider']=='fmp:global');used=clock['requests'] if clock['usage_date']==now.date() else 0
        if used>=40:raise Conflict('The local FMP limit of 40 requests per day is reached.')
        delay=max(0,(clock['next_at']-now).total_seconds())
        if delay>10:raise Conflict('An FMP request is already waiting; try later.')
        conn.execute('UPDATE provider_clocks SET next_at=%s,usage_date=%s,requests=%s WHERE provider=%s',(now+timedelta(seconds=delay+2),now.date(),used+1,'fmp:global'))
    if delay:time.sleep(delay)
    # Recheck persistent denial after another worker may have changed it.
    with transaction(source=True) as conn:
        if not allowed(conn,dataset) or one(conn,'SELECT 1 FROM provider_clocks WHERE provider=ANY(%s) AND (denied OR blocked_until>now())',(['fmp:global',provider],)):raise ProviderFailure('FMP source access changed before dispatch.')
    params={'symbol':symbol,'apikey':key}
    if dataset=='estimates':params.update(period='annual',page=0,limit=6)
    try:
        with httpx.Client(timeout=20,follow_redirects=False,transport=transport) as client:
            with client.stream('GET','https://financialmodelingprep.com/stable/'+endpoint,params=params) as response:
                if response.status_code in (401,402,403,429):
                    retry=response.headers.get('Retry-After','900');pause=900
                    try:pause=max(pause,int(retry) if retry.isdigit() else (parsedate_to_datetime(retry)-datetime.now(timezone.utc)).total_seconds())
                    except (ValueError,TypeError,OverflowError):pass
                    which='fmp:global' if response.status_code in (401,429) else provider
                    with transaction(source=True) as conn:
                        conn.execute('UPDATE provider_clocks SET denied=denied OR %s,blocked_until=greatest(blocked_until,%s) WHERE provider=%s',(response.status_code in (401,402,403),datetime.now(timezone.utc)+timedelta(seconds=pause),which))
                    raise ProviderFailure('FMP endpoint requires a supported subscription or key.' if response.status_code in (401,402,403) else 'FMP rate limit reached; requests are paused.')
                if response.status_code!=200:raise ProviderFailure('FMP did not return this dataset; no retry was made.')
                raw=bytearray()
                for chunk in response.iter_bytes():
                    raw.extend(chunk)
                    if len(raw)>1_000_000:raise ProviderFailure('FMP response exceeded the bounded size.')
                payload=json.loads(raw)
                if isinstance(payload,dict):raise ProviderFailure('FMP returned a service message instead of data; no retry was made.')
                return payload
    except (httpx.HTTPError,json.JSONDecodeError):raise ProviderFailure('FMP could not be read; saved data is retained.') from None


def commit(conn,dataset,symbol,payload,now):
    data=normalize(dataset,payload,symbol)
    if dataset=='profile':
        company=one(conn,'SELECT c.cik FROM sec_companies c JOIN instruments i ON i.id=c.instrument_id WHERE i.symbol=%s',(symbol,))
        if company and str(company['cik'])!=data['cik']:raise ProviderFailure('FMP issuer identity differs from the registered company.')
    raw=json.dumps(payload,sort_keys=True,separators=(',',':'));content_hash=hashlib.sha256((METHOD+raw).encode()).hexdigest()
    sid=uuid5(NAMESPACE_URL,f'thesis:fmp:{dataset}:{symbol}:{content_hash}')
    conn.execute('INSERT INTO fmp_snapshots VALUES(%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',(sid,dataset,symbol,DATASETS[dataset][1],content_hash,Jsonb(payload),Jsonb(data),now))
    conn.execute('INSERT INTO fmp_current VALUES(%s,%s,%s,%s) ON CONFLICT(dataset,symbol) DO UPDATE SET snapshot_id=excluded.snapshot_id,checked_at=excluded.checked_at',(dataset,symbol,sid,now))
    return str(sid)


def refresh(dataset,symbol,*,fetcher=None):
    symbol=symbol_value(symbol);attempt=uuid4();now=datetime.now(timezone.utc)
    if dataset not in DATASETS:raise ValueError('Unknown FMP dataset.')
    with transaction(source=True) as conn:
        if not allowed(conn,dataset):raise ValueError('FMP source permission is unavailable.')
        conn.execute('INSERT INTO fmp_refresh_state(dataset,symbol) VALUES(%s,%s) ON CONFLICT DO NOTHING',(dataset,symbol))
        state=one(conn,'SELECT * FROM fmp_refresh_state WHERE dataset=%s AND symbol=%s FOR UPDATE',(dataset,symbol))
        if state['lease_until'] and state['lease_until']>now:raise Conflict('This FMP dataset is being checked.')
        if state['last_attempt_at'] and now-state['last_attempt_at']<timedelta(hours=1):raise Conflict('FMP checks for this company/dataset are one hour apart.')
        conn.execute('UPDATE fmp_refresh_state SET attempt_id=%s,last_attempt_at=%s,lease_until=%s WHERE dataset=%s AND symbol=%s',(attempt,now,now+timedelta(minutes=2),dataset,symbol))
    try:
        payload=(fetcher or fetch)(dataset,symbol)
        with transaction(source=True) as conn:
            state=one(conn,'SELECT * FROM fmp_refresh_state WHERE dataset=%s AND symbol=%s FOR UPDATE',(dataset,symbol));checked=datetime.now(timezone.utc)
            if state['attempt_id']!=attempt or not state['lease_until'] or state['lease_until']<checked or not allowed(conn,dataset):raise ProviderFailure('FMP attempt expired or permission changed.')
            sid=commit(conn,dataset,symbol,payload,checked)
            conn.execute('UPDATE fmp_refresh_state SET lease_until=NULL,last_success_at=%s,error=NULL WHERE dataset=%s AND symbol=%s',(checked,dataset,symbol))
        return dict(status='ready',snapshot_id=sid)
    except (ValueError,Conflict) as failure:
        with transaction(source=True) as conn:conn.execute('UPDATE fmp_refresh_state SET lease_until=NULL,error=%s WHERE dataset=%s AND symbol=%s AND attempt_id=%s',(str(failure),dataset,symbol,attempt))
        return dict(status='unavailable',message=str(failure))


def present(conn,dataset,symbol):
    if not allowed(conn,dataset):return dict(status='withheld',data=None,message='FMP source permission is unavailable.')
    record=one(conn,'SELECT s.*,c.checked_at FROM fmp_current c JOIN fmp_snapshots s ON s.id=c.snapshot_id WHERE c.dataset=%s AND c.symbol=%s',(dataset,symbol))
    state=one(conn,'SELECT * FROM fmp_refresh_state WHERE dataset=%s AND symbol=%s',(dataset,symbol))
    return dict(status='saved' if record else 'empty',data=record['data'] if record else None,snapshot_id=str(record['id']) if record else None,
                first_observed_at=record['available_at'] if record else None,checked_at=record['checked_at'] if record else None,source_status=state,
                message=state['error'] if state else 'Check FMP endpoint access to collect this dataset.')


def company(conn,iid):
    row=one(conn,'SELECT i.symbol,c.cik FROM instruments i JOIN sec_companies c ON c.instrument_id=i.id WHERE i.id=%s',(iid,))
    if not row:raise ValueError('Choose a registered company.')
    return row


def save_peers(owner,iid,selections):
    with transaction(owner) as conn:
        target=company(conn,iid);suggested=present(conn,'peers',target['symbol'])['data']
        symbols={r['symbol'] for r in suggested['candidates']} if suggested else set()
        symbols.update(r['symbol'] for r in rows(conn,'SELECT symbol FROM instruments WHERE id<>%s',(iid,)))
        if len(selections)>3 or len({r['symbol'] for r in selections})!=len(selections):raise ValueError('Choose up to three different comparison companies.')
        for item in selections:
            if item['symbol'] not in symbols or item['symbol']==target['symbol']:raise ValueError('Choose a saved suggestion or a registered comparison company.')
            profile=present(conn,'profile',item['symbol'])['data']
            if profile and profile['cik']==str(target['cik']):raise ValueError('Another share class of the same issuer is not an independent peer.')
        conn.execute('DELETE FROM peer_selections WHERE owner_id=%s AND instrument_id=%s',(owner,iid))
        for item in selections:conn.execute('INSERT INTO peer_selections(owner_id,instrument_id,symbol,rationale) VALUES(%s,%s,%s,%s)',(owner,iid,item['symbol'],item['rationale']))
    return context(owner,iid)


def annual_growth(conn, iid):
    """Project one existing annual calculation; never substitute quarterly/TTM data."""
    from .sec.performance import present as performance
    source = performance(conn, iid)
    report = source.get('reports', {}).get('annual')
    result = {key: source.get(key) for key in (
        'status', 'reason', 'method', 'snapshot_id', 'payload_id',
        'first_recorded_at', 'checked_at', 'source_status')}
    result.update(report=None, metric=None)
    if source['status'] != 'available':
        return result
    if not report or report.get('period_type') != 'annual':
        result.update(status='empty', reason='A saved annual report is not available. Quarterly growth is not substituted.')
        return result
    result['report'] = {key: report.get(key) for key in (
        'period_type', 'accession', 'form', 'period_end', 'published_at',
        'filed_on', 'filing_url')}
    result['metric'] = next((row for row in report['metrics'] if row['key'] == 'revenue_growth'), None)
    return result


def context(owner,iid):
    from .public_forecasts import current as public_forecasts
    from .multiples import catalogue as saved_multiples
    from .sec.financial_depth import present as financial_depth
    with transaction(owner,consistent=True) as conn:
        target=company(conn,iid);selected=rows(conn,'SELECT symbol,rationale FROM peer_selections WHERE owner_id=%s AND instrument_id=%s ORDER BY symbol',(owner,iid))
        members=[];references={r['symbol']:r for r in saved_multiples(conn)}
        for symbol in [target['symbol']]+[r['symbol'] for r in selected]:
            registered=references.get(symbol)
            members.append(dict(symbol=symbol,profile=present(conn,'profile',symbol),ratios=present(conn,'ratios',symbol),saved_finnhub=registered['reference'] if registered else None,financials=financial_depth(conn,str(registered['id'])) if registered else None,annual_growth=annual_growth(conn,str(registered['id'])) if registered else None,rationale=next((r['rationale'] for r in selected if r['symbol']==symbol),None)))
        registered=rows(conn,'SELECT symbol,name FROM instruments WHERE id<>%s AND id IN (SELECT instrument_id FROM sec_companies)',(iid,))
        consensus_history=rows(conn,"SELECT id,data,available_at FROM fmp_snapshots WHERE dataset='estimates' AND symbol=%s ORDER BY available_at DESC,id DESC LIMIT 20",(target['symbol'],)) if allowed(conn,'estimates') else []
        return dict(symbol=target['symbol'],profile=present(conn,'profile',target['symbol']),consensus=present(conn,'estimates',target['symbol']),consensus_history=consensus_history,public_forecasts=public_forecasts(conn,iid),suggestions=present(conn,'peers',target['symbol']),selected=selected,members=members,registered=registered,
                    limitation='Review the business/product overlap and accounting conventions before comparing. Vendor TTM P/E and P/S remain separate from code-calculated SEC financials. Missing ratios, dates or estimates are unknown; this is not an investment ranking.')


def refresh_company(owner,iid,*,fetcher=None):
    with transaction(owner) as conn:
        target=company(conn,iid);selected=rows(conn,'SELECT symbol FROM peer_selections WHERE owner_id=%s AND instrument_id=%s',(owner,iid))
    outcomes=[]
    for dataset,symbol in [('profile',target['symbol']),('peers',target['symbol']),('estimates',target['symbol']),('ratios',target['symbol'])]+[(dataset,r['symbol']) for r in selected for dataset in ('profile','ratios')]:
        try:outcomes.append(dict(dataset=dataset,symbol=symbol,**refresh(dataset,symbol,fetcher=fetcher)))
        except (ValueError,Conflict) as failure:outcomes.append(dict(dataset=dataset,symbol=symbol,status='unavailable',message=str(failure)))
        with transaction() as conn:
            if one(conn,"SELECT 1 FROM provider_clocks WHERE provider='fmp:global' AND (denied OR blocked_until>now())"):break
    return dict(outcomes=outcomes,context=context(owner,iid))
