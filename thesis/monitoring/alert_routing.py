"""Immutable severity decisions; actual routing requires an explicit opt-in/start.

Preview records are never promoted. No transport, source fetch or model call.
"""
from datetime import datetime,timezone
import logging
from uuid import uuid4
from psycopg.types.json import Jsonb
from thesis.db import transaction,one,rows
from thesis.research import coverage,reporting_basis,sentiment_tasks

POLICY='alert-severity-preview-3'
LIVE_POLICY='alert-severity-live-3'
CHANNELS={'high':'telegram','medium':'digest','low':'app'}
RANK={'low':0,'medium':1,'high':2}


def live_requested():
    from .move_watch import option
    return str(option('THESIS_ALERT_ROUTING_LIVE') or 'false').lower() in {'true','1','on'}


def live_start():
    from .move_watch import option
    from thesis import review_digest
    try:
        value=option('THESIS_ALERT_ROUTING_LIVE_STARTED_AT')
        return review_digest.clock(value) if value else None
    except (ValueError,TypeError):return None


def live_active(now=None):
    start=live_start()
    return live_requested() and start is not None and start<=(now or datetime.now(timezone.utc))


def enabled():
    from .move_watch import option
    return live_active() or str(option('THESIS_ALERT_ROUTING_PREVIEW') or 'false').lower() in {'true','1','on'}


def delivery_reason(conn,owner,record,*,now):
    """Recheck a queued publication against current mode; absent routes fail closed."""
    is_new=record['kind']=='company' and record['detail'].get('payload',{}).get('kind')=='important_reporting'
    if not live_requested():
        return 'New importance delivery is off. Review it in Updates.' if is_new else None
    if not live_active(now) or record['created_at']<live_start():
        return 'This alert predates the active severity-routing start, or routing is unavailable.'
    route=one(conn,'SELECT channel FROM alert_routing_decisions WHERE owner_id=%s AND kind=%s AND event_id=%s '
        'AND policy=%s AND NOT preview',(owner,record['kind'],record['id'],LIVE_POLICY))
    if not route or route['channel']!='telegram':
        return 'This update belongs in the daily recap or app, or has no actual severity decision.'
    return None


def importance(item,source=None):
    """Never promote from tone, a money amount or an unvalidated model field."""
    if item.get('channel')=='news' and source and sentiment_tasks.editorial_headline(source.get('title')):return 'low'
    value=item.get('importance') or {};basis=item.get('reporting_basis') or {}
    citations=value.get('citations') or []
    if (item.get('channel')!='news' or item.get('relevance')!='relevant'
            or value.get('policy')!=sentiment_tasks.POLICY or value.get('event_repair')
            or value.get('form')!='event' or value.get('low_by_rule')
            or value.get('category') in {'analyst_opinion','market_commentary'}
            or not reporting_basis.eligible(item)):
        return 'low'
    if (value.get('level') not in {'high','medium'} or not citations
            or any(c.get('source_id')!=item.get('source_id') or not c.get('quote') for c in citations)
            or any(c.get('source_id')!=item.get('source_id') or not c.get('quote') for c in basis.get('citations',[]))):
        return 'low'
    return value['level']


def important_reporting(previous,current,seen=None):
    """New substantive news independent of tone; unchanged/backfilled news is quiet."""
    if not previous:return []
    observed=set(seen or ())
    for source in previous['packet']['sources']:
        observed.update((source['channel'],key) for key in coverage.observed_keys(previous,source))
    sources={s['id']:s for s in current['packet']['sources']}
    selected=[]
    for item in current['result']['items']:
        source=sources[item['source_id']]
        if importance(item,source)=='low':continue
        if any(('news',key) in observed for key in coverage.keys(current,source)):continue
        selected.append(item)
    if not selected:return []
    return [dict(kind='important_reporting',title='New company developments to review',items=selected,
        coverage_links=[link for link in current['result'].get('coverage_links',[])
                        if link['source_id'] in {i['source_id'] for i in selected}],
        reason='Newly analysed news states a company development with saved importance evidence. '
               'Importance is separate from favourable or adverse tone; unconfirmed claims remain unconfirmed.')]


def classify(record,*,idea_items=None):
    detail=record['detail'];kind=record['kind']
    if detail.get('withheld'):
        return dict(severity='low',channel='app',reason='Source access changed; details are withheld.',items=[])
    if kind=='move':
        return dict(severity='high',channel='telegram',reason='A code-owned price-move threshold was crossed.',items=[])
    if kind=='condition':
        return dict(severity='medium',channel='digest',reason='A saved comparison changed; no importance score is inferred.',items=[])
    items=detail.get('payload',{}).get('items',[]) if kind=='company' else list(idea_items or [])
    sources={s['id']:s for s in detail.get('sources',[])}
    levels=[dict(source_id=i['source_id'],level=importance(i,sources.get(i['source_id'])),
                 category=(i.get('importance') or {}).get('category')) for i in items]
    if not items or not any((i.get('importance') or {}).get('policy')==sentiment_tasks.POLICY for i in items):
        editorial=bool(items) and all(i.get('channel')=='news' and sentiment_tasks.editorial_headline(sources.get(i['source_id'],{}).get('title')) for i in items)
        level='low' if editorial else 'medium'
        reason='Explicit investment commentary stays in the app.' if editorial else 'Importance has not been scored; include in the daily review rather than assume high.'
    else:
        level=max((i['level'] for i in levels),key=RANK.get)
        reason={'high':'At least one cited company development has high importance.',
                'medium':'Cited company developments have medium importance.',
                'low':'No qualifying high/medium development; keep this update in the app.'}[level]
    return dict(severity=level,channel=CHANNELS[level],reason=reason,items=levels)


def save(conn,owner,record,*,now,preview=True):
    idea_items=None
    if record['kind']=='idea' and not record['detail'].get('withheld'):
        check=one(conn,'SELECT analysis_id FROM idea_alert_checks WHERE owner_id=%s AND id=%s',(owner,record['id']))
        analysis=one(conn,'SELECT result FROM sentiment_analyses WHERE id=%s',(check['analysis_id'],))
        matched={i['source_id'] for i in record['detail']['items']
                 if i.get('relation') in {'supports','challenges','risk','answers'}}
        idea_items=[i for i in analysis['result']['items'] if i['source_id'] in matched]
    decision=classify(record,idea_items=idea_items)
    covered_by=None
    if record['kind']=='company':
        publication=one(conn,'SELECT current_id,kind FROM research_alerts WHERE owner_id=%s AND id=%s',(owner,record['id']))
        if publication and publication['kind']!='important_reporting':
            proposal=one(conn,"SELECT id,payload FROM research_alerts WHERE owner_id=%s AND current_id=%s "
                "AND kind='important_reporting' AND preview=%s",(owner,publication['current_id'],preview))
            own_ids={i['source_id'] for i in record['detail'].get('payload',{}).get('items',[])}
            proposed_ids={i['source_id'] for i in proposal['payload']['items']} if proposal else set()
            if own_ids and own_ids<=proposed_ids:
                covered_by=str(proposal['id'])
                decision=dict(severity='low',channel='app',items=decision['items'],
                    reason='These sources are already covered by the company importance update; keep one delivery.')
    return one(conn,'INSERT INTO alert_routing_decisions VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) '
        'ON CONFLICT(owner_id,kind,event_id,policy) DO NOTHING RETURNING id',
        (uuid4(),owner,record['kind'],record['id'],POLICY if preview else LIVE_POLICY,decision['severity'],decision['channel'],preview,
         decision['reason'],Jsonb(dict(items=decision['items'],event_created_at=record['created_at'].isoformat(),covered_by=covered_by)),now))


def latest(conn,owner,kind,event_id):
    return one(conn,'SELECT severity,channel,preview,reason,created_at FROM alert_routing_decisions '
        'WHERE owner_id=%s AND kind=%s AND event_id=%s AND policy=%s',(owner,kind,event_id,LIVE_POLICY if live_active() else POLICY))


def run_once(owner,*,now=None):
    from .move_watch import option
    from thesis import review_digest
    now=review_digest.clock(now or datetime.now(timezone.utc))
    actual=live_active(now)
    if live_requested() and not actual:return 0
    if not actual and str(option('THESIS_ALERT_ROUTING_PREVIEW') or 'false').lower() not in {'true','1','on'}:return 0
    # An explicit installation start prevents a historical alert flood/backfill.
    start=live_start() if actual else option('THESIS_ALERT_ROUTING_STARTED_AT')
    if not start:return 0
    start=review_digest.clock(start)
    with transaction(owner) as conn:
        if not one(conn,'SELECT pg_try_advisory_xact_lock(hashtextextended(%s,0)) locked',
                   ('alert-routing:'+str(owner),))['locked']:return 0
        events=rows(conn,review_digest.EVENTS+'SELECT e.* FROM events e WHERE e.created_at>=%(start)s '
            "AND (NOT %(actual)s OR ((e.kind<>'company' OR EXISTS(SELECT 1 FROM research_alerts a WHERE a.owner_id=e.owner_id AND a.id=e.id AND NOT a.preview)) "
            "AND (e.kind<>'move' OR EXISTS(SELECT 1 FROM move_events m WHERE m.owner_id=e.owner_id AND m.id=e.id AND NOT m.preview)))) "
            'AND e.created_at<=%(now)s AND NOT EXISTS(SELECT 1 FROM alert_routing_decisions r WHERE '
            'r.owner_id=e.owner_id AND r.kind=e.kind AND r.event_id=e.id AND r.policy=%(policy)s) '
            'ORDER BY e.created_at,e.id LIMIT 100',dict(owner=owner,start=start,now=now,actual=actual,policy=LIVE_POLICY if actual else POLICY))
        return sum(bool(save(conn,owner,r,now=now,preview=not actual)) for r in review_digest.details(conn,owner,events))


def poll_preview(owner):
    """Shadow failures preserve ordinary delivery; live routing fails closed."""
    try:return run_once(owner)
    except Exception:
        message=('Alert routing could not be recorded; unrouted alerts remain in Fledge.' if live_requested() else
                 'Alert routing preview could not be recorded; existing delivery continues.')
        logging.getLogger('thesis').warning(message)
        return 0
