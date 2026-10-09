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
