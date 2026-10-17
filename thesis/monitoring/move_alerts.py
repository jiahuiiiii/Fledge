"""Private immutable price events and one-attempt explanations, initially previews.

Read/display/review never fetch sources or invoke AI. Collection and scheduling
are separate; the optional explainer consumes a bounded saved source snapshot.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
from uuid import uuid4
from psycopg.types.json import Jsonb
from thesis.db import transaction, one, rows
from thesis.providers import ledger
from thesis.research import reference_prices, price_history, move_explainer
from . import price_moves


def source_version(article):
    return hashlib.sha256(ledger.canonical({k:article[k] for k in
        ('headline','summary','publisher','url','published_at')}).encode()).hexdigest()


def world_source(article):
    article=dict(article,published_at=article['published_at'].isoformat())
    return dict(kind='world',id=str(article['id']),version=source_version(article),
                headline=article['headline'],excerpt=article['summary'][:400],
                publisher=article['publisher'],url=article['url'],published_at=article['published_at'])


def headlines(conn, companies, now):
    """At most twenty company and eight world headlines, all from the past day."""
    from thesis import service
    from thesis.research import market_brief
    from thesis.research.sec.checkpoint import current_documents
    news={}
    for company in companies:
        docs=service.permitted_documents(conn,now,company['instrument_id'])
        for document in market_brief.ordered_news(current_documents(docs,None),company['instrument_id'],now):
            if not now-timedelta(days=1)<=document['published_at']<=now:
                continue
            key=str(document['id'])
            if key not in news:
                news[key]=dict(kind='news',id=key,instrument_id=str(company['instrument_id']),
                    version=document['content_hash'],headline=document['headline'],excerpt=document['body'][:400],
                    publisher=document['source_name'],url=document['url'],published_at=document['published_at'].isoformat())
    company_news=sorted(news.values(),key=lambda v:(v['published_at'],v['id']),reverse=True)[:20]
    world=[]
    if reference_prices.allowed(conn,'quote'):
        world=[world_source(a) for a in rows(conn,
            'SELECT * FROM world_news_articles WHERE published_at>=%s AND published_at<=%s AND retrieved_at<=%s '
            'ORDER BY published_at DESC,id LIMIT 8',(now-timedelta(days=1),now,now))]
    selected=company_news+world
    return dict(sources={f'a{i+1}':v for i,v in enumerate(selected)},
                omitted_company_headlines=max(0,len(news)-len(company_news)),
                window_start=(now-timedelta(days=1)).isoformat(),window_end=now.isoformat(),
                limit_notice='Bounded saved headline excerpts; not full articles or complete coverage.')


def sources_permitted(conn, event, now):
    if not reference_prices.allowed(conn,'quote'):
        return False
    if any(m.get('two_sessions') for m in event['payload']['members']) and not price_history.allowed(conn):
        return False
    from thesis import service
    permitted={}
    for source in event['headlines']['sources'].values():
        if source['kind']=='world':
            current=one(conn,'SELECT * FROM world_news_articles WHERE id=%s',(source['id'],))
            if not current or world_source(current)['version']!=source['version']:
                return False
        else:
            iid=source['instrument_id']
            if iid not in permitted:
                permitted[iid]={str(d['id']):d for d in service.permitted_documents(conn,now,iid)
                                if d['entitlement'] in ('finnhub-pitch','public-news')}
            current=permitted[iid].get(source['id'])
            if not current or current['content_hash']!=source['version']:
                return False
    return True


def record(owner, event, *, now=None):
    """Persist code-derived numbers only for this account's enabled watches."""
    now=now or datetime.now(timezone.utc)
    with transaction(owner) as conn:
        conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))",('move-events:'+str(owner),))
        members=event['members']
        if not members or not any(m['triggered'] for m in members):
            return None
        companies=rows(conn,
            'SELECT i.id instrument_id,i.symbol FROM instruments i JOIN news_watches w ON w.instrument_id=i.id '
            'WHERE w.owner_id=%s AND w.enabled AND i.symbol=ANY(%s) ORDER BY i.id FOR UPDATE OF w',
            (owner,[m['symbol'] for m in members]))
        by_symbol={c['symbol']:c for c in companies}
        if len(by_symbol)!=len(members):
            return None
        for member in members:
            saved=one(conn,'SELECT quote FROM market_quotes WHERE id=%s AND instrument_id=%s',
                      (member['quote_id'],by_symbol[member['symbol']]['instrument_id']))
            if not saved:
                raise ValueError('Move quote belongs to another company or is unavailable.')
            checked=price_moves.checked_quote(saved['quote'],now)
            if checked is None:return None
            if (Decimal(member['price'])!=checked['price'] or Decimal(member['previous_close'])!=checked['previous']
                    or Decimal(member['change_percent'])!=checked['change']
                    or price_moves.clock(member['quoted_at'])!=checked['dated']):
                raise ValueError('Move numbers do not match their saved quote.')
            if member['triggered'] and one(conn,
                'SELECT event_id FROM move_trigger_claims WHERE owner_id=%s AND instrument_id=%s AND session_date=%s AND direction=%s',
                (owner,by_symbol[member['symbol']]['instrument_id'],event['session'],event['direction'])):
                return None
        evidence=headlines(conn,companies,now)
        eid=uuid4()
        primary=by_symbol[event['triggered_symbols'][0]]['instrument_id']
        conn.execute('INSERT INTO move_events VALUES(%s,%s,%s,%s,%s,%s,%s,true,%s,%s,%s)',
                     (eid,owner,primary,now,event['session'],event['kind'],event['direction'],price_moves.POLICY,Jsonb(event),Jsonb(evidence)))
        for member in members:
            iid=by_symbol[member['symbol']]['instrument_id']
            indexes=member['indexes'];sector=member.get('sector');history=member.get('two_sessions')
            conn.execute('INSERT INTO move_event_members VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                (owner,eid,iid,member['quote_id'],indexes.get('QQQ',{}).get('quote_id'),
                 indexes.get('SPY',{}).get('quote_id'),sector.get('quote_id') if sector else None,
                 history.get('snapshot_id') if history else None,member['triggered'],Jsonb(member)))
            if member['triggered']:
                conn.execute('INSERT INTO move_trigger_claims VALUES(%s,%s,%s,%s,%s)',
                             (owner,iid,event['session'],event['direction'],eid))
        return str(eid)


def request_content(event):
    return dict(move=event['payload'],headline_window={k:v for k,v in event['headlines'].items() if k!='sources'},
                headlines=[dict(source_id=k,**v) for k,v in event['headlines']['sources'].items()])


def explain(owner, eid, *, transport=None, model=None, now=None, allow_new_attempt=True):
    """Journal one paid attempt before dispatch; never automatically redispatch."""
    now=now or datetime.now(timezone.utc)
    with transaction(owner) as conn:
        event=one(conn,'SELECT * FROM move_events WHERE owner_id=%s AND id=%s',(owner,eid))
        if not event or not sources_permitted(conn,event,now):
            return False
        if one(conn,'SELECT event_id FROM move_explanations WHERE owner_id=%s AND event_id=%s',(owner,eid)):
            return False
        key=f'move-explanation:{owner}:{eid}'
        previous=one(conn,'SELECT event_id FROM move_explainer_attempts WHERE owner_id=%s AND event_id=%s',(owner,eid))
        attempt=None
        if not previous:
            if not allow_new_attempt:return False
            # A role not yet selected may be enabled later without spending now.
            body=move_explainer.request_for(request_content(event),model=model)
            attempt=one(conn,'INSERT INTO move_explainer_attempts VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING RETURNING event_id',
                        (owner,eid,key,now))
    call=None
    try:
        if attempt:
            call=ledger.execute(key,move_explainer.POLICY,body,owner=owner,transport=transport)
        else:
            with transaction(owner,consistent=True) as conn:
                call=one(conn,'SELECT * FROM model_calls WHERE owner_id=%s AND request_key=%s',(owner,key))
            if not call or call['status']=='dispatched':
                return False
            if call['status']!='settled':
                raise ValueError('The original attempt is unresolved; never automatically retry it.')
        result=move_explainer.parse(call,event['headlines']['sources'])
        status='no_clear' if result['cause']=='no_clear' else 'valid'
    except ValueError:
        result=dict(policy=move_explainer.POLICY,cause='no_clear',text=move_explainer.NO_CAUSE,
                    sentences=[],sources=[],notice='The explanation could not be verified. No automatic paid retry.')
        status='failed'
        if call is None:
            with transaction(owner,consistent=True) as conn:
                call=one(conn,'SELECT * FROM model_calls WHERE owner_id=%s AND request_key=%s',(owner,key))
    with transaction(owner) as conn:
        conn.execute('INSERT INTO move_explanations VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                     (owner,eid,call['id'] if call else None,now,status,Jsonb(result)))
    return True


def recover_pending(owner, *, now=None):
    """Recover at most ten saved settled/unresolved outcomes; never dispatch."""
    with transaction(owner,consistent=True) as conn:
        pending=rows(conn,'SELECT a.event_id FROM move_explainer_attempts a JOIN model_calls c ON c.request_key=a.request_key AND c.owner_id=a.owner_id '
            "WHERE a.owner_id=%s AND c.status IN ('settled','unresolved') AND NOT EXISTS("
            'SELECT 1 FROM move_explanations e WHERE e.owner_id=a.owner_id AND e.event_id=a.event_id) '
            'ORDER BY a.created_at LIMIT 10',(owner,))
    return sum(bool(explain(owner,p['event_id'],now=now,allow_new_attempt=False)) for p in pending)


def percent(value):
    number=Decimal(str(value))
    return f'{number:+.1f}%'.replace('-','−')


def title(event):
    members=event['payload']['members']
    start=' · '.join(f"{m['symbol']} {percent(m['change_percent'])}" for m in members)
    primary=members[0]['indexes'].get('QQQ')
    return start+(f" today · Nasdaq {percent(primary['change_percent'])}" if primary else ' today · Nasdaq unavailable')


def present(conn, owner, eid, *, now=None):
    now=now or datetime.now(timezone.utc)
    event=one(conn,'SELECT * FROM move_events WHERE owner_id=%s AND id=%s',(owner,eid))
    if not event:
        return None
    review=one(conn,'SELECT action,created_at FROM move_event_reviews WHERE owner_id=%s AND event_id=%s',(owner,eid))
    base=dict(id=str(eid),preview=event['preview'],created_at=event['created_at'],
              instrument_id=str(event['instrument_id']),review_action=review['action'] if review else None,
              symbol=', '.join(m['symbol'] for m in event['payload']['members']),
              event_type=event['event_type'],session_date=event['session_date'])
    if not sources_permitted(conn,event,now):
        return dict(base,withheld=True,title='Source access changed — details withheld',members=[],sources=[],explanation=None)
    explanation=one(conn,'SELECT * FROM move_explanations WHERE owner_id=%s AND event_id=%s',(owner,eid))
    attempted=bool(one(conn,'SELECT event_id FROM move_explainer_attempts WHERE owner_id=%s AND event_id=%s',(owner,eid)))
    result=explanation['result'] if explanation else None
    sources=[dict(s,id=s['source_id'],title=s['headline'],source=s['publisher']) for s in result['sources']] if result else []
    membership={m['payload']['symbol']:str(m['instrument_id']) for m in rows(conn,
        'SELECT instrument_id,payload FROM move_event_members WHERE owner_id=%s AND event_id=%s',(owner,eid))}
    members=[dict(m,instrument_id=membership[m['symbol']]) for m in event['payload']['members']]
    return dict(base,withheld=False,title=title(event),members=members,sources=sources,
                explanation=result,explanation_status=explanation['status'] if explanation else 'unfinished' if attempted else 'not_requested',
                limitation=event['headlines']['limit_notice'],headline_window={k:v for k,v in event['headlines'].items() if k!='sources'})


def review(owner, eid, action):
    if action not in ('reviewed','unresolved'):
        raise ValueError('Choose reviewed or unresolved.')
    with transaction(owner) as conn:
        if not one(conn,'SELECT id FROM move_events WHERE owner_id=%s AND id=%s',(owner,eid)):
            from thesis.service import Missing
            raise Missing('Price alert not found.')
        conn.execute('INSERT INTO move_event_reviews VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING',
                     (owner,eid,action,datetime.now(timezone.utc)))
        return present(conn,owner,eid)
