"""Controlled FMP capability responses, immutable vintages and private peers."""
from copy import deepcopy
from datetime import datetime,timezone,timedelta
import json
from uuid import uuid4
import httpx
import pytest
import psycopg
from thesis.db import transaction,one
from thesis.research import fmp
from thesis.research.sec.service import add_company


@pytest.fixture(autouse=True)
def scopes(owner):
    with transaction(admin=True) as conn:
        conn.execute('TRUNCATE fmp_refresh_state')
        for dataset,(_,source) in fmp.DATASETS.items():conn.execute('INSERT INTO sources VALUES(%s,%s,%s) ON CONFLICT DO NOTHING',(source,'FMP controlled '+dataset,'fmp-local'))
        conn.execute("DELETE FROM provider_clocks WHERE provider LIKE 'fmp:%'")


def profile(symbol='MSFT',cik='789019'):
    return [dict(symbol=symbol,cik=cik,companyName='Authored company',sector='Technology',industry='Software',currency='USD',price=100,marketCap=200)]


def estimate(average=120):return [dict(symbol='MSFT',date='2027-09-30',revenueLow=100,revenueAvg=average,revenueHigh=140,epsLow=-2,epsAvg=-1,epsHigh=0,numAnalystsRevenue=5,numAnalystsEps=3)]


def reset(dataset,symbol):
    with transaction(admin=True) as conn:conn.execute('UPDATE fmp_refresh_state SET last_attempt_at=NULL WHERE dataset=%s AND symbol=%s',(dataset,symbol))


def test_forecasts_are_not_actuals_or_management_guidance():
    result=fmp.normalize('estimates',estimate(),'MSFT')
    assert result['forecasts'][0]['currency'] is None
    assert result['forecasts'][0]['metrics'][1]['average']=='-1'
    assert result['forecasts'][0]['metrics'][0]['analysts']==5
    assert 'distinct' in result['limitation']
    with pytest.raises(ValueError):fmp.normalize('estimates',estimate(999),'MSFT')
    with pytest.raises(ValueError):fmp.normalize('estimates',estimate(),'NVDA')


def test_immutable_vintages_and_a_b_a_current_pointer(owner):
    iid=add_company('MSFT')['instrument_id'];first=fmp.refresh('estimates','MSFT',fetcher=lambda *_:estimate())
    before=fmp.context(owner,iid)['consensus']['first_observed_at']
    reset('estimates','MSFT');second=fmp.refresh('estimates','MSFT',fetcher=lambda *_:estimate(121))
    assert first['snapshot_id']!=second['snapshot_id']
    reset('estimates','MSFT');restored=fmp.refresh('estimates','MSFT',fetcher=lambda *_:estimate())
    assert first['snapshot_id']==restored['snapshot_id']
    result=fmp.context(owner,iid)
    assert result['consensus']['first_observed_at']==before and len(result['consensus_history'])==2
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with transaction(source=True) as conn:conn.execute('UPDATE fmp_snapshots SET data=data')
    with pytest.raises(psycopg.errors.RaiseException):
        with transaction(admin=True) as conn:conn.execute('UPDATE fmp_snapshots SET data=data')


def test_provider_peers_require_private_review_and_other_users_do_not_inherit(owner):
    iid=add_company('MSFT')['instrument_id'];add_company('NVDA')
    fmp.refresh('peers','MSFT',fetcher=lambda *_:[dict(symbol='NVDA',companyName='NVIDIA',mktCap=100)])
    assert fmp.context(owner,iid)['selected']==[]
    fmp.save_peers(owner,iid,[dict(symbol='NVDA',rationale='Different products; compare capital intensity cautiously.')])
    other=str(uuid4())
    with transaction(admin=True) as conn:conn.execute('INSERT INTO accounts VALUES(%s,%s)',(other,'Other account'))
    assert fmp.context(other,iid)['selected']==[]
    assert len(fmp.context(owner,iid)['selected'])==1
    with pytest.raises(ValueError):fmp.save_peers(owner,iid,[dict(symbol='MSFT',rationale='This is the same issuer.')])
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with transaction(source=True) as conn:conn.execute('SELECT * FROM peer_selections')


def test_negative_pe_is_unavailable_and_ratios_stay_ttm():
    result=fmp.normalize('ratios',[dict(symbol='MSFT',priceToEarningsRatioTTM=-2,priceToSalesRatioTTM=5)],'MSFT')
    assert result['period']=='TTM'
    assert result['metrics'][0]['value'] is None and result['metrics'][1]['value']=='5'
    assert 'GAAP' in result['basis']


def test_endpoint_restriction_does_not_disable_profile_or_clear_on_restart(owner,monkeypatch):
    monkeypatch.setattr(fmp,'settings',lambda:{'FMP_API_KEY':'test-key'})
    monkeypatch.setattr(fmp.time,'sleep',lambda _:None)
    seen=[]
    def denied(request):seen.append(request.url.path);return httpx.Response(402,text='Premium endpoint')
    with pytest.raises(fmp.ProviderFailure):fmp.fetch('ratios','MSFT',transport=httpx.MockTransport(denied))
    with pytest.raises(fmp.ProviderFailure):fmp.fetch('ratios','MSFT',transport=httpx.MockTransport(lambda _:pytest.fail('Denial bypassed')))
    assert len(seen)==1
    assert fmp.fetch('profile','MSFT',transport=httpx.MockTransport(lambda _:httpx.Response(200,json=profile())))==profile()
    with transaction() as conn:assert one(conn,"SELECT denied FROM provider_clocks WHERE provider='fmp:ratios'")['denied']


def test_rate_limit_stops_global_requests_and_honors_longer_retry(owner,monkeypatch):
    monkeypatch.setattr(fmp,'settings',lambda:{'FMP_API_KEY':'test-key'})
    with pytest.raises(fmp.ProviderFailure):fmp.fetch('estimates','MSFT',transport=httpx.MockTransport(lambda _:httpx.Response(429,headers={'Retry-After':'3600'})))
    with transaction() as conn:assert one(conn,"SELECT blocked_until FROM provider_clocks WHERE provider='fmp:global'")['blocked_until']>datetime.now(timezone.utc)+timedelta(minutes=59)
    with pytest.raises(Exception):fmp.fetch('profile','MSFT',transport=httpx.MockTransport(lambda _:pytest.fail('Rate-limit bypassed')))


def test_permission_change_during_fetch_fences_commit_and_history(owner):
    iid=add_company('MSFT')['instrument_id'];fmp.refresh('profile','MSFT',fetcher=lambda *_:profile())
    reset('profile','MSFT')
    def withdraw(*_):
        with transaction(admin=True) as conn:conn.execute("UPDATE sources SET entitlement='fictional' WHERE id='fmp-profile'")
        return profile()
    result=fmp.refresh('profile','MSFT',fetcher=withdraw)
    assert result['status']=='unavailable'
    assert fmp.context(owner,iid)['profile']['data'] is None


def test_registered_cik_mismatch_is_rejected(owner):
    add_company('MSFT')
    result=fmp.refresh('profile','MSFT',fetcher=lambda *_:profile(cik='320193'))
    assert result['status']=='unavailable'
    with transaction() as conn:assert one(conn,'SELECT count(*) n FROM fmp_snapshots')['n']==0


def test_existing_finnhub_references_are_separate_and_permission_checked(owner):
    from psycopg.types.json import Jsonb
    iid=add_company('MSFT')['instrument_id']
    metrics={'earnings':{'value':'30','field':'peTTM','reason':None},'sales':{'value':'5','field':'psTTM','reason':None}}
    with transaction(admin=True) as conn:conn.execute("INSERT INTO sources VALUES('finnhub-financials','Authored Finnhub reference','finnhub-pitch') ON CONFLICT DO NOTHING")
    with transaction(source=True) as conn:conn.execute('INSERT INTO multiple_references VALUES(%s,%s,%s,%s,%s,%s)',(uuid4(),iid,'MSFT',Jsonb(metrics),Jsonb({}),datetime.now(timezone.utc)))
    member=fmp.context(owner,iid)['members'][0]
    assert member['saved_finnhub']['metrics']==metrics and member['ratios']['data'] is None
    with transaction(admin=True) as conn:conn.execute("UPDATE sources SET entitlement='fictional' WHERE id='finnhub-financials'")
    assert fmp.context(owner,iid)['members'][0]['saved_finnhub'] is None


def test_peer_annual_growth_reuses_exact_saved_calculation_and_permission(owner):
    from thesis.research.sec.performance import present as performance
    from test_performance import financial_bundle
    from test_sec_fundamentals import apply
    iid=add_company('MSFT')['instrument_id']
    apply(iid,financial_bundle())
    with transaction(owner) as conn: original=performance(conn,iid)
    growth=fmp.context(owner,iid)['members'][0]['annual_growth']
    expected=next(row for row in original['reports']['annual']['metrics'] if row['key']=='revenue_growth')
    from decimal import Decimal
    assert growth['metric']==expected and Decimal(growth['metric']['value'])==25
    assert growth['metric']['value']!=next(row for row in original['reports']['quarter']['metrics'] if row['key']=='revenue_growth')['value']
    for key in ('snapshot_id','payload_id','method','first_recorded_at','checked_at'):
        assert growth[key]==original[key]
    assert growth['report']['filing_url']==original['reports']['annual']['filing_url']
    assert len(growth['metric']['inputs'])==2
    with transaction(admin=True) as conn:
        conn.execute("UPDATE sources SET entitlement='fictional' WHERE id='sec-companyfacts'")
    withdrawn=fmp.context(owner,iid)['members'][0]['annual_growth']
    assert withdrawn['status']=='unavailable' and withdrawn['metric'] is None and withdrawn['report'] is None


@pytest.mark.parametrize('kind',['quarter_only','missing_prior','zero_prior'])
def test_peer_growth_never_substitutes_a_quarter_or_missing_denominator(owner,kind):
    from test_sec_fundamentals import apply,bundle,REVENUE
    iid=add_company('MSFT')['instrument_id']
    data=bundle(annual=kind!='quarter_only')
    facts=data['companyfacts']['facts']['us-gaap'][REVENUE[0]]['units']['USD']
    if kind=='missing_prior':facts.pop()
    if kind=='zero_prior':facts[-1]['val']=0
    apply(iid,data)
    growth=fmp.context(owner,iid)['members'][0]['annual_growth']
    if kind=='quarter_only':
        assert growth['status']=='empty' and growth['metric'] is None
    else:
        assert growth['metric']['value'] is None and growth['metric']['reason']
