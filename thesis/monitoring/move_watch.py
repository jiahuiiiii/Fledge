"""Opt-in price detector, independent of slow social collectors and bulk AI.

Default off. Every event is a preview until a separate delivery approval. A
failed explainer cannot stop collection/detection or trigger an automatic retry.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import os
from uuid import uuid4

from thesis.db import transaction, one, rows
from thesis.providers import settings
from thesis.research import market, reference_prices, price_history
from . import move_alerts, price_moves
from .us_session import NEW_YORK, bounds


def option(key):
    value=os.environ.get(key)
    if value is None and os.environ.get('THESIS_TEST_OFFLINE')!='true':
        value=settings.settings().get(key)
    return value


def enabled():
    return str(option('THESIS_MOVE_ALERTS') or 'false').lower() in {'true','1','on'}


def thresholds():
    return price_moves.Thresholds(**{field:Decimal(option('THESIS_MOVE_'+key) or default)
        for field,key,default in (('session','SESSION_PERCENT','3'),('relative','INDEX_GAP_POINTS','2'),
                                  ('two_sessions','TWO_SESSION_PERCENT','5'))})


def regular_session(now):
    session=bounds(now.astimezone(NEW_YORK).date())
    return bool(session and session[0]<=now<=session[1]+timedelta(minutes=15))


def retained_history(conn,iid):
    if not price_history.allowed(conn):return None
    snapshot=one(conn,'SELECT p.* FROM price_history_state s JOIN price_history_snapshots p ON p.id=s.current_id '
        'WHERE s.instrument_id=%s',(iid,))
    return dict(snapshot['series'],snapshot_id=str(snapshot['id']),retrieved_at=snapshot['retrieved_at'].isoformat()) if snapshot else None


def snapshot(conn,owner,now):
    """No source/model requests: measure only current permitted saved prices."""
    if not reference_prices.allowed(conn,'quote'):return []
    refs={}
    for symbol in ('QQQ','SPY'):
        saved=reference_prices.latest(conn,symbol)
        if saved and saved['retrieved_at']<=now:refs[symbol]=dict(saved['payload'],id=str(saved['id']))
    result=[]
    companies=rows(conn,'SELECT i.id,i.symbol FROM news_watches w JOIN instruments i ON i.id=w.instrument_id '
        'JOIN sec_companies s ON s.instrument_id=i.id WHERE w.owner_id=%s AND w.enabled ORDER BY i.symbol',(owner,))
    for company in companies:
        iid=company['id']
        saved=one(conn,'SELECT * FROM market_quotes WHERE instrument_id=%s AND retrieved_at<=%s '
            'ORDER BY retrieved_at DESC,id DESC LIMIT 1',(iid,now))
        if not saved:continue
        mapping=reference_prices.sector(conn,owner,iid)
        sector=None
        if mapping['symbol']:
            ref=reference_prices.latest(conn,mapping['symbol'])
            if ref and ref['retrieved_at']<=now:sector=dict(symbol=mapping['symbol'],quote=dict(ref['payload'],id=str(ref['id'])))
        measured=price_moves.measure(company['symbol'],dict(saved['quote'],id=str(saved['id'])),indexes=refs,
            sector=sector,history=retained_history(conn,iid),now=now,thresholds=thresholds())
        if not measured:continue
        if one(conn,'SELECT event_id FROM move_trigger_claims WHERE owner_id=%s AND instrument_id=%s AND session_date=%s AND direction=%s',
               (owner,iid,measured['session'],measured.get('trigger_direction',measured['direction']))):
            continue
        result.append(measured)
    return result


def refresh_context(companies,now):
    # Existing fast watches collect company quotes/headlines. This worker only
    # supplies missing shared ETF quotes and the daily bars needed by rule three.
    for symbol in sorted({'QQQ','SPY'}|{c['sector'] for c in companies if c['sector']}):
        try:reference_prices.refresh(symbol)
        except ValueError:pass  # Unknown context remains unknown, never a fallback.
    for company in companies:
        with transaction(consistent=True) as conn:
            state=one(conn,'SELECT last_attempt_at FROM price_history_state WHERE instrument_id=%s',(company['id'],))
        if not state or not state['last_attempt_at'] or now-state['last_attempt_at']>=timedelta(hours=1):
            try:price_history.refresh(company['id'])
            except ValueError:pass


def run_once(owner, *, now=None, refresh=None, explainer=None):
    if not enabled():return False
    started=now or datetime.now(timezone.utc)
    if started.tzinfo is None:raise ValueError('Price checks need a timezone-aware clock.')
    recovered=move_alerts.recover_pending(owner,now=started)
    if not regular_session(started):return bool(recovered)
    token=uuid4()
    with transaction(owner) as conn:
        companies=rows(conn,'SELECT i.id,i.symbol FROM news_watches w JOIN instruments i ON i.id=w.instrument_id '
            'JOIN sec_companies s ON s.instrument_id=i.id WHERE w.owner_id=%s AND w.enabled ORDER BY i.symbol',(owner,))
        if not companies:return False
        conn.execute('INSERT INTO move_watch_state(owner_id,next_check_at) VALUES(%s,%s) ON CONFLICT DO NOTHING',(owner,started))
        state=one(conn,'SELECT * FROM move_watch_state WHERE owner_id=%s FOR UPDATE SKIP LOCKED',(owner,))
        if (not state or state['next_check_at']>started or (state['lease_until'] and state['lease_until']>started)):
            return False
        conn.execute('UPDATE move_watch_state SET claim_token=%s,lease_until=%s,next_check_at=%s WHERE owner_id=%s',
                     (token,started+timedelta(minutes=15),started+timedelta(minutes=15),owner))
        companies=[dict(c,sector=reference_prices.sector(conn,owner,c['id'])['symbol']) for c in companies]
    status='completed';error=None;created=0;checked=0
    try:
        (refresh or refresh_context)(companies,started)
        measured_at=now or datetime.now(timezone.utc)
        with transaction(owner,consistent=True) as conn:
            measured=snapshot(conn,owner,measured_at)
        checked=len(measured)
        for event in price_moves.group(measured):
            with transaction(owner,consistent=True) as conn:
                state=one(conn,'SELECT * FROM move_watch_state WHERE owner_id=%s',(owner,))
            at=now or datetime.now(timezone.utc)
            if not enabled() or state['claim_token']!=token or state['lease_until']<=at:
                status='stopped';break
            eid=move_alerts.record(owner,event,now=at)
            if not eid:continue
            created+=1
            # No model selected means no dispatch. A paid failure is contained
            # in the one-attempt journal and cannot stop later numeric events.
            if explainer or settings.EXPLAINER_MODEL:
                try:(explainer or move_alerts.explain)(owner,eid)
                except ValueError:pass
    except Exception:
        status='failed';error='Price check failed; saved alerts are retained. No automatic paid retry.'
    finally:
        finished=now or datetime.now(timezone.utc)
        with transaction(owner) as conn:
            conn.execute('INSERT INTO move_watch_runs VALUES(%s,%s,%s,%s,%s,%s,%s,%s)',
                         (token,owner,started,finished,status,checked,created,error))
            conn.execute('UPDATE move_watch_state SET lease_until=NULL,last_check_at=%s,error=%s '
                         'WHERE owner_id=%s AND claim_token=%s',(finished,error,owner,token))
    return True
