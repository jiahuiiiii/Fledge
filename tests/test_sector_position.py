"""Competitor projections and explicit private peer edits; no live requests."""
from copy import deepcopy
from datetime import datetime,timezone
from uuid import uuid4
import pytest
from psycopg.types.json import Jsonb
from thesis.db import transaction,one
from thesis.research import sector_position,fmp
from thesis.research.sec.service import add_company
from test_performance import financial_bundle
from test_sec_fundamentals import apply


def directory():
    listings=[dict(symbol=s,name=s+' authored',cik=c,exchange='Nasdaq') for s,c in [('AVGO',1730168),('AMD',2488),('MRVL',1835632),('MU',723125),('QCOM',804328),('NVDA',1045810),('GOOG',1652044),('GOOGL',1652044)]]
    with transaction(admin=True) as conn:
        conn.execute('UPDATE company_directory SET listings=%s,retrieved_at=%s WHERE singleton',(Jsonb(listings),datetime.now(timezone.utc)))
        for _,source in fmp.DATASETS.values():conn.execute('INSERT INTO sources VALUES(%s,%s,%s) ON CONFLICT DO NOTHING',(source,'Authored FMP','fmp-local'))
    return listings


def test_five_default_peers_are_read_only_and_missing_companies_stay_unknown(owner):
    directory();iid=add_company('AVGO')['instrument_id'];add_company('NVDA')
    result=sector_position.context(owner,iid)
    assert result['peers']==['NVDA','AMD','MRVL','MU','QCOM'] and result['basis']=='suggested'
    assert [r['symbol'] for r in result['members']]==['AVGO','NVDA','AMD','MRVL','MU','QCOM']
    assert result['members'][2]['performance'] is None
    with transaction(owner) as conn:
        assert one(conn,'SELECT count(*) n FROM peer_selections')['n']==0
        assert one(conn,"SELECT count(*) n FROM instruments WHERE symbol='AMD'")['n']==0


def test_other_companies_default_to_vendor_similar_companies_without_same_issuer_shares(owner):
    directory();iid=add_company('NVDA')['instrument_id']
    first=sector_position.context(owner,iid)
    assert first['basis']=='unselected' and first['vendor_status']['status']=='empty' and first['vendor_status']['last_attempt_at'] is None
    rows=[dict(symbol=s,companyName=s+' authored',mktCap=cap) for s,cap in [('005930.KS',999),('AMD',300),('GOOG',900),('MU',200),('QCOM',250),('MRVL',100),('AVGO',800),('GOOGL',950)]]
    outcome=fmp.refresh_company(owner,iid,fetcher=lambda *_:rows,only='peers')
    assert [o['dataset'] for o in outcome['outcomes']]==['peers']
    result=sector_position.context(owner,iid)
    status=result['vendor_status']
    assert status['status']=='saved' and status['count']==7 and status['next_attempt_at']>status['last_attempt_at']
    # Largest first, five at most; saved private choices would still override them.
    assert result['basis']=='suggested' and result['suggestion_origin']=='fmp'
    assert result['peers']==result['vendor_suggestions']==['GOOGL','AVGO','AMD','QCOM','MU']
    with transaction(owner) as conn:
        assert one(conn,'SELECT count(*) n FROM peer_selections')['n']==0


def test_failed_peers_check_is_explained_and_retries_sooner_than_a_completed_one(owner):
    directory();iid=add_company('MU')['instrument_id']
    def refuse(*_):raise fmp.ProviderFailure('FMP endpoint requires a supported subscription or key.')
    first=fmp.refresh_company(owner,iid,fetcher=refuse,only='peers')['outcomes'][0]
    assert first['status']=='unavailable',first
    status=sector_position.context(owner,iid)['vendor_status']
    assert status['error'] and 'supported subscription' in status['error'] and status['status']=='empty',(first,status)
    assert (status['next_attempt_at']-status['last_attempt_at']).total_seconds()==300
    again=fmp.refresh_company(owner,iid,fetcher=refuse,only='peers')['outcomes'][0]
    assert 'failed' in again['message']


def test_saved_peers_override_default_and_are_private(owner):
    directory();iid=add_company('AVGO')['instrument_id']
    peers=[dict(symbol=s,rationale='Compare whole-company growth; business mix differs.') for s in ['NVDA','AMD','MRVL','MU','QCOM']]
    fmp.save_peers(owner,iid,peers)
    result=sector_position.context(owner,iid)
    assert result['basis']=='saved' and set(result['peers'])=={r['symbol'] for r in peers}
    viewed=sector_position.context(owner,iid,['MU'])
    assert viewed['basis']=='view' and viewed['peers']==['MU']
    assert len(sector_position.context(owner,iid)['peers'])==5
    other=str(uuid4())
    with transaction(admin=True) as conn:conn.execute('INSERT INTO accounts VALUES(%s,%s)',(other,'Other authored account'))
    assert sector_position.context(other,iid)['basis']=='suggested'
    fmp.save_peers(owner,iid,[])
    # Empty saved sets use the suggested group again; no implicit records written.
    assert sector_position.context(owner,iid,[])['members'][0]['symbol']=='AVGO'


@pytest.mark.parametrize('peers',[['AVGO'],['NONE'],['NVDA','NVDA'],['AMD']*9])
def test_invalid_view_choices_are_rejected_without_writes(owner,peers):
    directory();iid=add_company('AVGO')['instrument_id']
    with pytest.raises(ValueError):sector_position.context(owner,iid,peers)
    with transaction(owner) as conn:assert one(conn,'SELECT count(*) n FROM peer_selections')['n']==0


def test_same_issuer_share_class_is_rejected_in_view_and_save(owner):
    directory();iid=add_company('GOOGL')['instrument_id']
    with pytest.raises(ValueError):sector_position.context(owner,iid,['GOOG'])
    with pytest.raises(ValueError):fmp.save_peers(owner,iid,[dict(symbol='GOOG',rationale='Authored explicit comparison.')])


def test_exact_report_inputs_are_reused_and_source_withdrawal_withholds(owner):
    directory();iid=add_company('MSFT')['instrument_id'];apply(iid,financial_bundle())
    with transaction(owner) as conn:expected=sector_position.performance(conn,iid)
    result=sector_position.context(owner,iid,[])['members'][0]
    assert result['performance']==expected and result['consensus']['data'] is None
    with transaction(admin=True) as conn:conn.execute("UPDATE sources SET entitlement='fictional' WHERE id='sec-companyfacts'")
    hidden=sector_position.context(owner,iid,[])['members'][0]
    assert hidden['performance']['status']=='unavailable' and not hidden['performance'].get('reports')


def test_forecasts_keep_their_source_permissions_and_identity(owner):
    directory();iid=add_company('MSFT')['instrument_id']
    payload=[dict(symbol='MSFT',date='2027-09-30',currency='USD',revenueLow=100,revenueAvg=120,revenueHigh=140)]
    with transaction(source=True) as conn:fmp.commit(conn,'estimates','MSFT',payload,datetime.now(timezone.utc))
    result=sector_position.context(owner,iid,[])['members'][0]['consensus']
    assert result['data']['forecasts'][0]['metrics'][0]['average']=='120' and result['snapshot_id']
    with transaction(admin=True) as conn:conn.execute("UPDATE sources SET entitlement='fictional' WHERE id='fmp-estimates'")
    assert sector_position.context(owner,iid,[])['members'][0]['consensus']['data'] is None


def test_collection_status_distinguishes_missing_running_failed_and_checked_without_report(owner):
    directory();iid=add_company('NVDA')['instrument_id']
    def status():return sector_position.context(owner,iid,[])['members'][0]['filing_status']
    assert status()['status']=='not_collected' and status()['can_fetch']
    with transaction(admin=True) as conn:
        conn.execute('UPDATE sec_refresh_state SET last_attempt_at=now(),lease_until=now()+interval \'1 minute\' WHERE instrument_id=%s',(iid,))
    assert status()['status']=='loading' and not status()['can_fetch']
    with transaction(admin=True) as conn:
        conn.execute("UPDATE sec_refresh_state SET lease_until=NULL,last_error='Authored connection failure.' WHERE instrument_id=%s",(iid,))
    assert status()==dict(status='failed',message='Authored connection failure.',can_fetch=True)
    with transaction(admin=True) as conn:
        conn.execute('UPDATE sec_refresh_state SET last_error=NULL WHERE instrument_id=%s',(iid,))
    assert status()['status']=='no_report'
    with transaction(admin=True) as conn:
        conn.execute('UPDATE sec_refresh_state SET lease_until=now()-interval \'1 minute\' WHERE instrument_id=%s',(iid,))
    assert status()['status']=='failed' and 'did not finish' in status()['message']


def test_queued_filing_work_is_loading_without_an_active_transport_lease(owner):
    directory();iid=add_company('NVDA')['instrument_id']
    with transaction(owner) as conn:
        conn.execute('INSERT INTO research_loads(id,owner_id,instrument_id,lookback_days,steps) VALUES(%s,%s,%s,7,%s)',(uuid4(),owner,iid,Jsonb([dict(key='filings',status='queued')])))
    state=sector_position.context(owner,iid,[])['members'][0]['filing_status']
    assert state['status']=='loading' and not state['can_fetch']


def test_ready_annual_data_is_reused_and_withdrawn_access_is_never_fetchable(owner):
    directory();iid=add_company('MSFT')['instrument_id'];apply(iid,financial_bundle())
    member=sector_position.context(owner,iid,[])['members'][0]
    assert member['instrument_id']==iid and member['filing_status']['status']=='ready'
    assert not member['filing_status']['can_fetch']
    with transaction(admin=True) as conn:conn.execute("UPDATE sources SET entitlement='fictional' WHERE id='sec-companyfacts'")
    hidden=sector_position.context(owner,iid,['AMD'])['members']
    assert all(m['filing_status']['status']=='unavailable' and not m['filing_status']['can_fetch'] for m in hidden)
