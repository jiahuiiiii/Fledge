"""Pure move arithmetic and grouping; all prices are authored, no HTTP calls."""
from copy import deepcopy
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from thesis.monitoring import price_moves as M
from thesis.research.price_history import BASIS

NOW = datetime.fromisoformat('2026-10-15T18:00:00+00:00')


def quote(price='100', previous='100', *, stamp=NOW, identity='authored-stock'):
    return dict(id=identity, price=price, previous_close=previous,
                currency='USD', quoted_at=stamp.isoformat())


def measure(price, *, index='100', spy='100', **kwargs):
    return M.measure('NVDA', quote(price), now=NOW,
                     indexes=dict(QQQ=quote(index, identity='authored-qqq'),
                                  SPY=quote(spy, identity='authored-spy')), **kwargs)


def history():
    return dict(currency='USD', interval='1d', exchange_timezone='America/New_York',
                basis=BASIS, retrieved_at=(NOW-timedelta(hours=1)).isoformat(),
                snapshot_id='authored-history', bars=[
                    dict(date='2026-10-13', close='100', provisional=False),
                    dict(date='2026-10-14', close='100', provisional=False)])


@pytest.mark.parametrize('price,trigger', [('103', True), ('97', True),
    ('102.999999', False), ('97.000001', False), ('100', False)])
def test_session_threshold_inclusive_in_both_directions(price, trigger):
    value=measure(price, index=price)
    assert ('session_move' in value['reasons']) is trigger
    assert value['triggered'] is trigger


@pytest.mark.parametrize('price,index,trigger', [
    ('101','99',True), ('99','101',True), ('100.999999','99',False),
    ('99.000001','101',False), ('98','97',False)])
def test_relative_threshold_is_percentage_points_not_relative_percent(price,index,trigger):
    value=measure(price,index=index)
    assert ('index_gap' in value['reasons']) is trigger
    assert Decimal(value['indexes']['QQQ']['gap_points']) == Decimal(price)-Decimal(index)


def test_spy_is_context_and_cannot_silently_replace_missing_nasdaq():
    value=M.measure('NVDA',quote('99'),indexes={'SPY':quote('103')},now=NOW)
    assert value['indexes']['SPY']['gap_points']=='-4.00'
    assert not value['triggered'] and 'QQQ' not in value['indexes']


@pytest.mark.parametrize('price,base,want', [('97','102.1052631578947368421052632',True),
    ('103','98',True), ('99','100',False)])
def test_two_session_threshold(price,base,want):
    saved=history();saved['bars'][0]['close']=base
    value=measure(price,index=price,history=saved)
    assert ('two_session_move' in value['reasons']) is want
    assert value['two_sessions']['snapshot_id']=='authored-history'


def test_exact_two_session_boundary():
    current=M.checked_quote(quote('95','99'),NOW)
    saved=history();saved['bars'][1]['close']='99'
    two=M.two_session_move(current,saved,NOW)
    assert Decimal(two['change_percent']) == -5
    value=M.measure('NVDA',quote('95','99'),indexes={},now=NOW,history=saved)
    assert value['reasons']==['session_move','two_session_move']


def test_gradual_three_day_slide_is_a_documented_limit_not_rounded_into_a_trigger():
    daily=Decimal('-2.5');two=(Decimal('.975')**2-1)*100
    assert two==Decimal('-4.937500')
    assert (Decimal('.975')**3-1)*100 < -7
    assert M.evaluate_thresholds(daily,{'QQQ':dict(gap_points='0')},
                                 dict(change_percent=str(two)),M.Thresholds())==[]


@pytest.mark.parametrize('price,base,direction',[('101','107','down'),('99','94','up')])
def test_rebound_cannot_reverse_two_session_trigger_or_join_opposite_market(price,base,direction):
    saved=history();saved['bars'][0]['close']=base
    a=measure(price,index=price,history=saved);b=deepcopy(a);b['symbol']='AVGO'
    assert a['reasons']==['two_session_move']
    assert a['trigger_direction']==direction and a['direction']!=direction
    events=M.group([a,b])
    assert len(events)==2 and all(e['kind']=='company' and e['direction']==direction for e in events)


@pytest.mark.parametrize('change', [
    lambda h:h.update(currency='SGD'),lambda h:h.update(interval='1wk'),
    lambda h:h.update(exchange_timezone='UTC'),lambda h:h.update(basis='adjusted close'),
    lambda h:h.update(retrieved_at=(NOW+timedelta(seconds=1)).isoformat()),
    lambda h:h.update(bars=None),lambda h:h.update(snapshot_id=None),
    lambda h:h['bars'][0].update(provisional=True),
    lambda h:h['bars'][0].pop('provisional'),
    lambda h:h['bars'][0].update(date='2026-10-12'),
    lambda h:h['bars'].append(deepcopy(h['bars'][0])),
    lambda h:h['bars'][1].update(close='50'),
    lambda h:h['bars'][0].update(close='NaN'),
])
def test_missing_provisional_wrong_vintage_split_or_malformed_history_cannot_trigger(change):
    saved=history();change(saved)
    value=measure('99',index='99',history=saved)
    assert value['two_sessions'] is None and not value['triggered']


@pytest.mark.parametrize('price', [None,True,0,-1,'NaN','Infinity','1e999999999','1e-9999999',[],{}])
def test_invalid_prices_do_not_create_moves(price):
    assert M.measure('NVDA',quote(price),indexes={},now=NOW) is None


@pytest.mark.parametrize('stamp', [NOW-timedelta(minutes=30,seconds=1),NOW+timedelta(seconds=1),
    datetime.fromisoformat('2026-10-15T12:00:00+00:00'),
    datetime.fromisoformat('2026-10-17T18:00:00+00:00'),
    datetime.fromisoformat('2026-11-26T18:00:00+00:00')])
def test_old_future_premarket_weekend_and_holiday_quotes_are_omitted(stamp):
    now=stamp if stamp.date()!=NOW.date() else NOW
    assert M.measure('NVDA',quote('95',stamp=stamp),indexes={},now=now) is None


def test_reference_clocks_and_sector_are_independent_context():
    refs=dict(QQQ=quote('98',stamp=NOW-timedelta(minutes=16)),SPY=quote('99'))
    sector=dict(symbol='SOXX',quote=quote('97',identity='authored-soxx'))
    value=M.measure('NVDA',quote('96'),indexes=refs,sector=sector,now=NOW)
    assert list(value['indexes'])==['SPY']
    assert Decimal(value['sector']['gap_points'])==-1
    assert value['reasons']==['session_move']
    sector['quote']['quoted_at']=(NOW-timedelta(minutes=16)).isoformat()
    assert M.measure('NVDA',quote(),indexes={},sector=sector,now=NOW)['sector'] is None


def test_quote_currency_aware_clock_symbol_and_custom_thresholds():
    q=quote('104');q['currency']='EUR'
    assert M.measure('NVDA',q,indexes={},now=NOW) is None
    q=quote();q['quoted_at']='2026-10-15T18:00:00'
    assert M.measure('NVDA',q,indexes={},now=NOW) is None
    assert M.measure('../NVDA',quote(),indexes={},now=NOW) is None
    with pytest.raises(ValueError):M.measure('NVDA',quote(),indexes={},now=NOW.replace(tzinfo=None))
    with pytest.raises(ValueError):M.Thresholds(session=Decimal('NaN'))
    with pytest.raises(ValueError):M.Thresholds(relative=2)
    value=measure('104',index='104',thresholds=M.Thresholds(session=Decimal('5')))
    assert not value['triggered'] and value['thresholds']['session']=='5'


def test_prior_sessions_cross_weekends_holidays_and_unknown_calendar():
    day=datetime.fromisoformat('2026-11-30').date()
    assert [d.isoformat() for d in M.prior_sessions(day)]==['2026-11-27','2026-11-25']
    assert M.prior_sessions(datetime.fromisoformat('2030-01-01').date()) is None


def values():
    result=[]
    for symbol,price in [('NVDA','96.8'),('AVGO','96.9'),('AMZN','98.3'),('GOOGL','98.3')]:
        value=measure(price,index='97.9');value['symbol']=symbol;result.append(value)
    return result


def test_market_group_is_one_event_and_context_members_do_not_invent_threshold_passes():
    result=M.group(values())
    assert len(result)==1 and result[0]['kind']=='market'
    assert result[0]['triggered_symbols']==['AVGO','NVDA']
    members={v['symbol']:v for v in result[0]['members']}
    assert members['AMZN']['context_only'] and not members['AMZN']['triggered']
    assert members['GOOGL']['context_only'] and not members['NVDA']['context_only']


def test_one_qualifier_cannot_become_market_event_or_promote_context_to_alert():
    result=M.group(values()[::2])
    assert len(result)==1 and result[0]['kind']=='company'
    assert result[0]['triggered_symbols']==['NVDA'] and len(result[0]['members'])==1


def test_opposite_direction_different_reference_or_missing_index_remain_individual():
    a,b=values()[:2]
    a['indexes']['QQQ']['change_percent']='2.1'
    assert [v['kind'] for v in M.group([a,b])]==['company','company']
    a,b=values()[:2];b['indexes']['QQQ']['quote_id']='different-vintage'
    assert [v['kind'] for v in M.group([a,b])]==['company','company']
    a,b=values()[:2];b['indexes']={}
    assert [v['kind'] for v in M.group([a,b])]==['company','company']
    with pytest.raises(ValueError):M.group([a,a])
    assert M.group([None])==[]


def test_early_close_accepts_regular_close_but_not_afternoon_price():
    closing=datetime.fromisoformat('2026-11-27T18:00:00+00:00')
    assert M.measure('NVDA',quote('96',stamp=closing),indexes={},now=closing)
    late=closing+timedelta(minutes=2)
    assert M.measure('NVDA',quote('96',stamp=late),indexes={},now=late) is None
