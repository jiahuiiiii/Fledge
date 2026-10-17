"""Retrospective arithmetic never claims a contemporaneous ETF quote or sends."""
from datetime import datetime, timedelta
import pytest
from experiments.soclaas_replay.price_move_replay import replay


def inputs():
    start=datetime.fromisoformat('2026-10-12T13:30:00+00:00')
    index=dict(usable=True,retrieved_at='2026-10-17T04:00:00+00:00',raw={'chart':dict(error=None,result=[dict(
        meta=dict(symbol='QQQ',currency='USD',instrumentType='ETF',exchangeTimezoneName='America/New_York',dataGranularity='1d'),
        timestamp=[int((start+timedelta(days=d)).timestamp()) for d in range(5)],
        indicators=dict(quote=[dict(open=[100]*5,high=[110]*5,low=[90]*5,close=[100,100,98,98,97],volume=[1]*5)]))])})
    prices=dict(history=[],quotes=[dict(symbol=s,session='2026-10-14',retrieved_at='2026-10-15T00:00:00Z',
        quote=dict(currency='USD',price=p,previous_close=100,quoted_at='2026-10-14T20:00:00Z'))
        for s,p in [('NVDA',96.8),('AAPL',96.9),('AMZN',98.3),('GOOGL',98.3)]])
    headlines=[dict(id='authored',symbol='NVDA',headline='Authored demand report',published_at='2026-10-14T19:00:00Z',
                    available_at='2026-10-15T01:00:00Z')]
    return prices,index,headlines


def test_retrospective_market_group_covers_context_members_without_fake_quote_times():
    result=replay(*inputs(),symbols={'NVDA','AAPL','AMZN','GOOGL'})
    assert result['october14_required_members_covered'] and not result['timing_verified']
    event=result['sessions'][0]['events'][0]
    assert event['kind']=='market' and event['headlines_saved_after_move']==1
    for member in event['members']:
        assert not member['timing_eligible']
        assert member['indexes']['QQQ']['quoted_at'] is None
        assert member['indexes']['QQQ']['daily_snapshot_sha256']
    assert [m['symbol'] for m in event['members'] if m['context_only']]==['AMZN','GOOGL']


def test_missing_or_wrong_etf_data_is_not_fabricated():
    prices,index,headlines=inputs();index['usable']=False
    with pytest.raises(ValueError):replay(prices,index,headlines,symbols={'NVDA'})
    index['usable']=True;index['raw']['chart']['result'][0]['meta']['instrumentType']='EQUITY'
    with pytest.raises(ValueError):replay(prices,index,headlines,symbols={'NVDA'})


def test_sources_outside_window_and_unknown_companies_are_excluded():
    prices,index,headlines=inputs()
    headlines += [dict(headlines[0],id='old',published_at='2026-10-12T12:00:00Z'),
                  dict(headlines[0],id='future',published_at='2026-10-15T12:00:00Z'),
                  dict(headlines[0],id='other',symbol='ZZZZ')]
    result=replay(prices,index,headlines,symbols={'NVDA'})
    assert [s['id'] for s in result['sessions'][0]['events'][0]['saved_headlines']]==['authored']
    assert not result['october14_required_members_covered']
