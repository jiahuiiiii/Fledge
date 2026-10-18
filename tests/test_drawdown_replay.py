"""Drawdown candidates use saved closes only; all fixtures are authored."""
from contextlib import contextmanager
from copy import deepcopy
from datetime import date,timedelta
from decimal import Decimal as D
import pytest
from experiments.soclaas_replay import drawdown_replay as R
from thesis.research.price_history import BASIS
from thesis.db import transaction,one


def series(prices):
    day=date(2026,1,2);bars=[]
    for price in prices:
        while not R.session(day):day+=timedelta(days=1)
        bars.append(dict(date=day.isoformat(),close=str(price),provisional=False));day+=timedelta(days=1)
    return dict(symbol='MSFT',basis=BASIS,currency='USD',interval='1d',exchange_timezone='America/New_York',bars=bars)


def window(prices):return R.validated(series(prices))[-10:]


def test_slow_slide_is_caught_on_day3_without_faking_a_daily_or_two_session_trigger():
    result=R.replay(series([100]*62+[D('97.5'),D('95.0625'),D('92.6859375')]))
    days=result['days'][-3:]
    assert not any(d['baseline_price'] for d in days)
    assert [bool(d['episodes']['fixed7']) for d in days]==[False,False,True]
    assert D(days[-1]['episodes']['fixed7'][0]['excursion_percent'])==D('7.314062500')


def test_ten_session_anchor_still_misses_a_sufficiently_slow_long_slide():
    prices=[D(100)]*62
    for _ in range(30):prices.append(prices[-1]*D('.996'))
    days=R.replay(series(prices))['days']
    assert prices[-1]<D(89)
    assert not any(d['baseline_price'] or d['episodes']['fixed7'] for d in days)


def test_steps_are_inclusive_and_a_large_jump_is_one_alert_with_all_crossed_levels():
    state=R.Episodes('fixed7')
    assert state.tick(window([100,93]),D(1))[0]['crossed_levels']==['7']
    assert not state.tick(window([100,93,90]),D(1))
    assert state.tick(window([100,93,90,88]),D(1))[0]['crossed_levels']==['12']
    event=state.tick(window([100,93,90,88,77]),D(1))[0]
    assert event['crossed_levels']==['17','22'] and event['next_level']=='27'


def test_pinned_anchor_does_not_expire_or_repeat_when_old_high_leaves_rolling_window():
    state=R.Episodes('fixed7');state.tick(window([100,92]),D(1))
    bars=R.validated(series([100,92]+[90]*20+[88]))
    for index in range(2,len(bars)-1):assert not state.tick(bars[max(0,index-9):index+1],D(1))
    event=state.tick(bars[-10:],D(1))[0]
    assert event['kind']=='follow_up' and event['anchor']=='100' and event['excursion_percent']=='12.00'


def test_half_recovery_rearms_from_new_reference_not_same_old_high():
    state=R.Episodes('fixed7');bars=R.validated(series([100,80,90,89]))
    first=state.tick(bars[:2],D(1));assert first[0]['direction']=='down'
    rebound=state.tick(bars[:3],D(1))
    assert all(e['direction']=='up' for e in rebound)
    assert state.rearm['down']==bars[2]['date']
    event=state.tick(bars[:4],D(1));assert all(e['direction']!='down' for e in event)


def test_gradual_rally_is_symmetric_and_cannot_mask_a_subsequent_pullback():
    state=R.Episodes('fixed7')
    event=state.tick(window([100,102,104,108]),D(1))[0]
    assert event['direction']=='up' and D(event['excursion_percent'])==8
    state=R.Episodes('fixed7');state.tick(window([100,120]),D(1))
    events=state.tick(window([100,120,111]),D(1))
    assert any(e['direction']=='down' and e['kind']=='entry' for e in events)
    assert set(state.active)=={'down','up'}


def test_volatility_threshold_and_followup_freeze_during_an_episode():
    state=R.Episodes('scaled4_floor2')
    entry=state.tick(window([100,92]),D(2))[0];assert entry['threshold_percent']=='8'
    follow=state.tick(window([100,92,87]),D(10))[0]
    assert follow['threshold_percent']=='8' and follow['crossed_levels']==['13']
    assert R.Episodes('scaled4_floor2').threshold(D(0))==2
    assert R.Episodes('scaled4_floor7').threshold(D(0))==7


def test_typical_move_uses_exactly60_prior_returns_and_never_the_current_shock():
    result=R.replay(series([100]*61+[80,79]))
    assert result['days'][0]['typical']=='0' and result['days'][0]['scaled_daily_threshold']=='2'
    assert D(result['days'][1]['typical'])==D(20)/60


def test_future_prices_do_not_change_earlier_decisions():
    initial=[100]*62+[99,98,95,92]
    a=R.replay(series(initial));b=R.replay(series(initial+[50,150,20,200]))
    assert b['days'][:len(a['days'])]==a['days']


def test_missing_trading_session_resets_warmup_instead_of_joining_across_the_gap():
    values=series([100]*140);values['bars'].pop(70)
    result=R.replay(values)
    assert result['gaps']==1
    assert not any(values['bars'][70]['date']<=d['date']<values['bars'][131]['date'] for d in result['days'])


@pytest.mark.parametrize('change',[
    lambda s:s.update(basis='Unknown corporate action basis'),
    lambda s:s['bars'].append(deepcopy(s['bars'][0])),
    lambda s:s['bars'][0].update(close='NaN'),
    lambda s:s['bars'][0].update(close=True),
    lambda s:s['bars'][0].update(date='2026-01-03'),
])
def test_invalid_prices_vintage_duplicate_sessions_or_closed_days_are_rejected(change):
    value=series([100]*80);change(value)
    with pytest.raises(ValueError):R.replay(value)


def test_provisional_close_and_missing_qqq_are_not_fabricated():
    values=series([100]*62+[97]);values['bars'][-1]['provisional']=True
    result=R.replay(values);assert len(result['days'])==1
    assert not result['days'][0]['qqq_known']
    summary=R.summarize(result);assert summary['qqq_known_sessions']==0
    assert summary['baseline_partial_days']==summary['baseline_price_days']
    assert not R.session(date(2025,11,27)) and R.session(date(2025,11,28))
    with pytest.raises(ValueError):R.session(date(2025,9,30))


def test_same_date_qqq_comparison_is_optional_and_retains_its_exact_coverage():
    values=series([100]*62+[99]);days=R.validated(values)
    index={days[-2]['date'].isoformat():D(100),days[-1]['date'].isoformat():D(103)}
    result=R.replay(values,index)
    assert result['days'][-1]['baseline_partial'] and not result['days'][-1]['baseline_price']
    assert 'index_gap' in result['days'][-1]['reasons']
    assert R.summarize(result)['qqq_known_sessions']==1


def test_monthly_counts_union_modes_without_double_counting_and_separate_last60_sessions():
    value=series([100]*62+[90,88,87,86]+[90]*70)
    result=R.replay(value);summary=R.summarize(result)
    assert summary['holdout_sessions']==60
    for mode in R.MODES:
        m=summary['modes'][mode]
        assert sum(m['by_month'].values())==m['combined_days']
        assert m['train_combined']+m['holdout_combined']==m['combined_days']
        assert m['combined_days']>=summary['baseline_price_days']
    report=R.compare(dict(policy=R.POLICY,watched=['MSFT'],history=[dict(symbol='MSFT',series=value)]))
    assert report['ai_calls']==0 and report['live_changes'] is False
    assert 'QQQ coverage is partial' in R.markdown(report)


def test_capture_is_database_read_only_and_never_refreshes_sources(owner,monkeypatch,tmp_path):
    from test_price_history import setup,payload
    from thesis.research import price_history as ph
    from thesis.monitoring import news_watch
    from thesis import db
    iid=setup(owner,monkeypatch);ph.refresh(iid,fetcher=lambda *_:payload(count=6))
    news_watch.configure(owner,iid,True)
    original=db.transaction;observed=[]
    @contextmanager
    def read_only(*args,**kwargs):
        assert kwargs==dict(admin=True,consistent=True)
        with original(*args,**kwargs) as conn:
            observed.append(one(conn,'SHOW transaction_read_only')['transaction_read_only']);yield conn
    monkeypatch.setattr(db,'transaction',read_only)
    monkeypatch.setattr(ph,'refresh',lambda *_:pytest.fail('Capture refreshed prices'))
    output=tmp_path/'prices.json';frozen=R.capture(output)
    assert observed==['on'] and frozen['watched']==['MSFT'] and output.exists()
    assert 'owner_id' not in output.read_text()
    with pytest.raises(ValueError,match='new'):R.capture(output)


def test_duplicate_companies_wrong_symbols_and_wrong_index_cannot_create_a_comparison():
    h=dict(symbol='MSFT',series=series([100]*80));frozen=dict(policy=R.POLICY,watched=['MSFT'],history=[h,h])
    with pytest.raises(ValueError,match='Duplicate'):R.compare(frozen)
    frozen['history']=[dict(h,symbol='AAPL')]
    with pytest.raises(ValueError,match='another symbol'):R.compare(frozen)
    frozen['history']=[h]
    with pytest.raises(ValueError,match='QQQ'):R.compare(frozen,series([100]*80))
