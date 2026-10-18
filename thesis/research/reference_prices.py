"""Bounded, shared ETF prices; no SEC companies, AI calls or account enrollment.

The adapters retain their existing global request clocks. Each reference and
resource has an independent lease and cooldown; concurrent watches reuse it.
Failure preserves the previous immutable snapshot, without an automatic retry.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from uuid import uuid4

from psycopg.types.json import Jsonb
from thesis.db import transaction, one, rows
from . import market, price_history
from .sec.service import collection_lock

INTERVALS = dict(quote=timedelta(minutes=5), history=timedelta(hours=1))
ERROR = 'Reference price check failed; saved prices are retained. No automatic retry.'


def allowed(conn, resource):
    if resource == 'history':
        return price_history.allowed(conn)
    return bool(one(conn, "SELECT id FROM sources WHERE id='finnhub-news' AND entitlement='finnhub-pitch'"))


def configured(resource):
    return price_history.configured() if resource == 'history' else market.configured()


def latest(conn, symbol, resource='quote'):
    if resource not in INTERVALS or not allowed(conn, resource):
        return None
    return one(conn,
        'SELECT p.* FROM reference_refresh_state s JOIN reference_price_snapshots p '
        'ON p.id=s.current_id AND p.symbol=s.symbol AND p.resource=s.resource '
        'WHERE s.symbol=%s AND s.resource=%s', (symbol, resource))


def refresh(symbol, resource='quote', *, fetcher=None, now=None):
    if resource not in INTERVALS:
        raise ValueError('Unsupported reference price resource.')
    started = now or datetime.now(timezone.utc)
    if started.tzinfo is None:
        raise ValueError('Reference checks need a timezone-aware clock.')
    attempt = uuid4()
    with transaction(source=True) as conn:
        collection_lock(conn)
        registered = one(conn, 'SELECT symbol FROM reference_instruments WHERE symbol=%s', (symbol,))
        if not registered or not allowed(conn, resource) or not configured(resource):
            raise ValueError('This price reference or data source is unavailable.')
        conn.execute('INSERT INTO reference_refresh_state(symbol,resource) VALUES(%s,%s) ON CONFLICT DO NOTHING',
                     (symbol, resource))
        state = one(conn, 'SELECT * FROM reference_refresh_state WHERE symbol=%s AND resource=%s FOR UPDATE',
                    (symbol, resource))
        if state['lease_until'] and state['lease_until'] > started:
            return dict(status='busy', snapshot_id=str(state['current_id']) if state['current_id'] else None)
        if state['last_attempt_at'] and started-state['last_attempt_at'] < INTERVALS[resource]:
            return dict(status='cached', snapshot_id=str(state['current_id']) if state['current_id'] else None)
        conn.execute('UPDATE reference_refresh_state SET attempt_id=%s,last_attempt_at=%s,lease_until=%s '
                     'WHERE symbol=%s AND resource=%s',
                     (attempt, started, started+timedelta(minutes=2), symbol, resource))
    try:
        if resource == 'quote':
            raw = (fetcher or market.fetch)('quote', dict(symbol=symbol))
            payload = market.normalize_quote(raw, now or datetime.now(timezone.utc))
        else:
            start, end = price_history.window(started)
            raw = (fetcher or price_history.fetch)(symbol, start, end)
            payload = price_history.normalize(raw, symbol, start, end,
                observed_at=now or datetime.now(timezone.utc), instrument_type='ETF')
        finished = now or datetime.now(timezone.utc)
        with transaction(source=True) as conn:
            collection_lock(conn)
            state = one(conn, 'SELECT * FROM reference_refresh_state WHERE symbol=%s AND resource=%s FOR UPDATE',
                        (symbol, resource))
            if (state['attempt_id'] != attempt or not state['lease_until']
                    or state['lease_until'] <= finished or not allowed(conn, resource)):
                raise ValueError('Reference claim expired or source access changed.')
            previous = latest(conn, symbol, resource)
            if previous:
                old = previous['payload']
                if resource == 'quote' and payload['quoted_at'] < old['quoted_at']:
                    raise ValueError('An older quote cannot replace the latest quote.')
                if resource == 'history':
                    dates = {b['date'] for b in payload['bars']}
                    if old['bars'][-1]['date'] > payload['bars'][-1]['date'] or any(
                        b['date'] >= payload['requested_start'] and b['date'] not in dates for b in old['bars']):
                        raise ValueError('The new history lost retained sessions.')
            sid = uuid4()
            digest = hashlib.sha256(json.dumps(raw, sort_keys=True, separators=(',', ':'),
                                               ensure_ascii=False).encode()).hexdigest()
            conn.execute('INSERT INTO reference_price_snapshots VALUES(%s,%s,%s,%s,%s,%s,%s)',
                         (sid, symbol, resource, Jsonb(raw), Jsonb(payload), digest, finished))
            conn.execute('UPDATE reference_refresh_state SET current_id=%s,completed_at=%s,lease_until=NULL,error=NULL '
                         'WHERE symbol=%s AND resource=%s', (sid, finished, symbol, resource))
        return dict(status='updated', snapshot_id=str(sid))
    except Exception:
        with transaction(source=True) as conn:
            conn.execute('UPDATE reference_refresh_state SET lease_until=NULL,error=%s '
                         'WHERE symbol=%s AND resource=%s AND attempt_id=%s', (ERROR, symbol, resource, attempt))
        return dict(status='failed', snapshot_id=None)


def sector(conn, owner, iid):
    override = one(conn, 'SELECT symbol FROM company_sector_references WHERE owner_id=%s AND instrument_id=%s',
                   (owner, iid))
    if override is not None:
        return dict(symbol=override['symbol'], origin='owner')
    company = one(conn, 'SELECT sector FROM instrument_state WHERE instrument_id=%s', (iid,))
    # Only an explicit classification establishes this default; never infer it
    # from a ticker, company name, price movement or generic technology sector.
    label = (company['sector'] or '').strip().casefold() if company else ''
    return dict(symbol='SOXX' if label in {'semiconductors', 'semiconductor'} else None,
                origin='classification' if label in {'semiconductors', 'semiconductor'} else 'unknown')


def set_sector(owner, iid, symbol):
    """Called only by an explicit owner edit; never by detection or migration."""
    with transaction(owner) as conn:
        if not one(conn, 'SELECT id FROM instruments WHERE id=%s', (iid,)):
            raise ValueError('Choose an existing company.')
        if symbol is not None and not one(conn, "SELECT symbol FROM reference_instruments WHERE symbol=%s AND role='sector'", (symbol,)):
            raise ValueError('Choose a supported sector reference or none.')
        conn.execute('INSERT INTO company_sector_references(owner_id,instrument_id,symbol,updated_at) VALUES(%s,%s,%s,%s) '
                     'ON CONFLICT(owner_id,instrument_id) DO UPDATE SET symbol=excluded.symbol,updated_at=excluded.updated_at',
                     (owner, iid, symbol, datetime.now(timezone.utc)))
        return sector(conn, owner, iid)


def present(conn, owner, iid):
    mapping = sector(conn, owner, iid)
    references=[]
    for symbol in ('QQQ','SPY',mapping['symbol']):
        if not symbol:continue
        snapshot=latest(conn,symbol)
        references.append(dict(symbol=symbol,snapshot=dict(id=str(snapshot['id']),quote=snapshot['payload'],
            retrieved_at=snapshot['retrieved_at']) if snapshot else None))
    return dict(sector=mapping, choices=rows(conn,
        "SELECT symbol,name FROM reference_instruments WHERE role='sector' ORDER BY symbol"),
        references=references)
