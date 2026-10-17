"""Decimal price-move rules and grouping. No model, source fetch or side effect.

Quotes must describe the same recent regular US session. Missing index/sector
context stays unknown. Two-session arithmetic uses one saved split-adjustment
vintage, with its previous close checked against the current quote's basis.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from .us_session import NEW_YORK, bounds

POLICY = "price-move-rules-1"
MAX_AGE = timedelta(minutes=30)
MAX_CLOCK_GAP = timedelta(minutes=15)


@dataclass(frozen=True)
class Thresholds:
    session: Decimal = Decimal("3")
    relative: Decimal = Decimal("2")
    two_sessions: Decimal = Decimal("5")

    def __post_init__(self):
        if any(not isinstance(v, Decimal) or not v.is_finite() or not Decimal(".25") <= v <= 100
               for v in (self.session, self.relative, self.two_sessions)):
            raise ValueError("Move thresholds must be finite percentages between 0.25 and 100.")

    def record(self):
        return dict(session=str(self.session),relative=str(self.relative),two_sessions=str(self.two_sessions))


def positive(value):
    if isinstance(value,bool):return None
    try:
        if len(str(value)) > 64:return None
        value=Decimal(str(value))
        return value if value.is_finite() and Decimal('1e-12')<=value<=Decimal('1e13') else None
    except (InvalidOperation,ValueError,TypeError):
        return None


def clock(value):
    try:
        result=value if isinstance(value,datetime) else datetime.fromisoformat(str(value).replace('Z','+00:00'))
        return result if result.tzinfo is not None else None
    except (ValueError,TypeError):
        return None


def checked_quote(quote,now):
    if not isinstance(quote,dict) or quote.get('currency')!='USD':return None
    price,previous=positive(quote.get('price')),positive(quote.get('previous_close'))
    dated=clock(quote.get('quoted_at'))
    if price is None or previous is None or dated is None or not timedelta(0)<=now-dated<=MAX_AGE:
        return None
    local=dated.astimezone(NEW_YORK)
    session=bounds(local.date())
    if not session or not session[0]<=dated<=session[1]+timedelta(minutes=1):return None
    return dict(price=price,previous=previous,dated=dated,session=local.date(),
                change=(price/previous-1)*100)


def prior_sessions(day):
    result=[]
    for offset in range(1,11):
        prior=day-timedelta(days=offset)
        if bounds(prior):result.append(prior)
        if len(result)==2:return result
    return None


def two_session_move(current,history,now):
    from thesis.research.price_history import BASIS
    if not isinstance(history,dict):return None
    if (history.get('currency')!='USD' or history.get('interval')!='1d'
            or history.get('exchange_timezone')!='America/New_York' or history.get('basis')!=BASIS):return None
    retrieved=clock(history.get('retrieved_at'))
    if retrieved is None or retrieved>now:return None
    days=prior_sessions(current['session'])
    if not days:return None
    bars=history.get('bars')
    if not isinstance(bars,list) or not 2<=len(bars)<=400 or not history.get('snapshot_id'):return None
    rows={}
    for bar in bars:
        if not isinstance(bar,dict) or not isinstance(bar.get('date'),str) or bar['date'] in rows:return None
        rows[bar.get('date')]=bar
    previous,base=(rows.get(day.isoformat()) for day in days)
    if not previous or not base or previous.get('provisional') is not False or base.get('provisional') is not False:return None
    previous_close,base_close=positive(previous.get('close')),positive(base.get('close'))
    if previous_close is None or base_close is None:return None
    # Mixing adjustment vintages can manufacture a large move around a split.
    if abs(previous_close/current['previous']-1)>Decimal('.005'):return None
    return dict(change_percent=str((current['price']/base_close-1)*100),
                from_session=days[1].isoformat(),through_session=current['session'].isoformat(),
                base_close=str(base_close),snapshot_id=history.get('snapshot_id'),
                basis=BASIS,retrieved_at=retrieved.isoformat())


def measure(symbol,quote,*,indexes,now,sector=None,history=None,thresholds=None):
    """Return measured context even when no threshold qualifies; bad quotes omit."""
    if not isinstance(now,datetime) or now.tzinfo is None:
        raise ValueError('The move detector needs a timezone-aware clock.')
    from thesis.research.directory import valid_symbol
    if not valid_symbol(symbol):return None
    current=checked_quote(quote,now)
    if current is None:return None
    thresholds=thresholds or Thresholds()
    index_values={}
    for ticker in ('QQQ','SPY'):
        source=indexes.get(ticker) if isinstance(indexes,dict) else None
        ref=checked_quote(source,now)
        if (ref and ref['session']==current['session']
                and abs(ref['dated']-current['dated'])<=MAX_CLOCK_GAP):
            index_values[ticker]=dict(change_percent=str(ref['change']),
                gap_points=str(current['change']-ref['change']),quoted_at=ref['dated'].isoformat(),
                quote_id=source.get('id'))
    sector_value=None
    if isinstance(sector,dict):
        ref=checked_quote(sector.get('quote'),now)
        if (ref and ref['session']==current['session']
                and abs(ref['dated']-current['dated'])<=MAX_CLOCK_GAP):
            sector_value=dict(symbol=sector.get('symbol'),change_percent=str(ref['change']),
                              gap_points=str(current['change']-ref['change']),quoted_at=ref['dated'].isoformat(),
                              quote_id=sector['quote'].get('id'))
    two=two_session_move(current,history,now)
    reasons=evaluate_thresholds(current['change'],index_values,two,thresholds)
    direction='up' if current['change']>0 else 'down' if current['change']<0 else 'flat'
    return dict(policy=POLICY,symbol=symbol,session=current['session'].isoformat(),
                quoted_at=current['dated'].isoformat(),price=str(current['price']),
                previous_close=str(current['previous']),change_percent=str(current['change']),
                direction=direction,indexes=index_values,sector=sector_value,two_sessions=two,
                reasons=reasons,triggered=bool(reasons),thresholds=thresholds.record(),quote_id=quote.get('id'))


def evaluate_thresholds(change,indexes,two,thresholds):
    """Shared numeric rules for live quotes and explicitly retrospective replay."""
    reasons=[]
    if abs(change)>=thresholds.session:reasons.append('session_move')
    # QQQ is the primary comparison; SPY remains separate context, never a
    # silent replacement when the Nasdaq quote is unavailable or stale.
    if 'QQQ' in indexes and abs(Decimal(indexes['QQQ']['gap_points']))>=thresholds.relative:
        reasons.append('index_gap')
    if two and abs(Decimal(two['change_percent']))>=thresholds.two_sessions:reasons.append('two_session_move')
    return reasons


def group(measures):
    """Group ≥2 qualifying stocks moving with QQQ; label other members context."""
    values=[v for v in measures if v is not None]
    by_symbol={v['symbol']:v for v in values}
    if len(by_symbol)!=len(values):raise ValueError('A company can occur only once in a move snapshot.')
    results=[];grouped=set()
    for session in sorted({v['session'] for v in values}):
        for direction,sign in (('up',1),('down',-1)):
            matching=[v for v in values if v['session']==session and v['direction']==direction
                      and v['indexes'].get('QQQ')
                      and Decimal(v['indexes']['QQQ']['change_percent'])*sign>0]
            # A common sign alone cannot join unrelated reference vintages.
            cohorts={}
            for value in matching:
                ref=value['indexes']['QQQ']
                key=(str(ref['quote_id']),ref['quoted_at'],ref['change_percent'])
                cohorts.setdefault(key,[]).append(value)
            for cohort in cohorts.values():
                triggers=[v for v in cohort if v['triggered']]
                if len(triggers)<2:continue
                members=[dict(v,context_only=not v['triggered']) for v in sorted(cohort,key=lambda v:v['symbol'])]
                results.append(dict(kind='market',session=session,direction=direction,members=members,
                                    triggered_symbols=sorted(v['symbol'] for v in triggers)))
                grouped.update(v['symbol'] for v in cohort)
    results.extend(dict(kind='company',session=v['session'],direction=v['direction'],
                        members=[dict(v,context_only=False)],triggered_symbols=[v['symbol']])
                   for v in sorted(values,key=lambda v:v['symbol']) if v['triggered'] and v['symbol'] not in grouped)
    return results
