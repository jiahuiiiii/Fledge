"""Preview-only severity decisions; no transport, source fetch or model call.

The channel is a proposal, never a delivery instruction. Live severity routing
and new delivery types require a separate approved rollout.
"""
from datetime import datetime,timezone
import logging
from uuid import uuid4
from psycopg.types.json import Jsonb
from thesis.db import transaction,one,rows
from thesis.research import coverage,reporting_basis,sentiment_tasks

POLICY='alert-severity-preview-1'
CHANNELS={'high':'telegram','medium':'digest','low':'app'}
RANK={'low':0,'medium':1,'high':2}


def enabled():
    from .move_watch import option
    return str(option('THESIS_ALERT_ROUTING_PREVIEW') or 'false').lower() in {'true','1','on'}


def importance(item):
    """Never promote from tone, a money amount or an unvalidated model field."""
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
        if importance(item)=='low':continue
        source=sources[item['source_id']]
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
    levels=[dict(source_id=i['source_id'],level=importance(i),
                 category=(i.get('importance') or {}).get('category')) for i in items]
    if not items or not any((i.get('importance') or {}).get('policy')==sentiment_tasks.POLICY for i in items):
        level='medium';reason='Importance has not been scored; include in the daily review rather than assume high.'
    else:
        level=max((i['level'] for i in levels),key=RANK.get)
        reason={'high':'At least one cited company development has high importance.',
                'medium':'Cited company developments have medium importance.',
                'low':'No qualifying high/medium development; keep this update in the app.'}[level]
    return dict(severity=level,channel=CHANNELS[level],reason=reason,items=levels)


def save(conn,owner,record,*,now):
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
                "AND kind='important_reporting' AND preview",(owner,publication['current_id']))
            own_ids={i['source_id'] for i in record['detail'].get('payload',{}).get('items',[])}
            proposed_ids={i['source_id'] for i in proposal['payload']['items']} if proposal else set()
            if own_ids and own_ids<=proposed_ids:
                covered_by=str(proposal['id'])
                decision=dict(severity='low',channel='app',items=decision['items'],
                    reason='These sources are already covered by the company importance preview; do not propose a second delivery.')
    return one(conn,'INSERT INTO alert_routing_decisions VALUES(%s,%s,%s,%s,%s,%s,%s,true,%s,%s,%s) '
        'ON CONFLICT(owner_id,kind,event_id,policy) DO NOTHING RETURNING id',
        (uuid4(),owner,record['kind'],record['id'],POLICY,decision['severity'],decision['channel'],
         decision['reason'],Jsonb(dict(items=decision['items'],event_created_at=record['created_at'].isoformat(),covered_by=covered_by)),now))


def latest(conn,owner,kind,event_id):
    return one(conn,'SELECT severity,channel,preview,reason,created_at FROM alert_routing_decisions '
        'WHERE owner_id=%s AND kind=%s AND event_id=%s AND policy=%s',(owner,kind,event_id,POLICY))


def run_once(owner,*,now=None):
    if not enabled():return 0
    from .move_watch import option
    from thesis import review_digest
    # An explicit installation start prevents a historical alert flood/backfill.
    start=option('THESIS_ALERT_ROUTING_STARTED_AT')
    if not start:return 0
    start=review_digest.clock(start);now=review_digest.clock(now or datetime.now(timezone.utc))
    with transaction(owner) as conn:
        if not one(conn,'SELECT pg_try_advisory_xact_lock(hashtextextended(%s,0)) locked',
                   ('alert-routing:'+str(owner),))['locked']:return 0
        events=rows(conn,review_digest.EVENTS+'SELECT e.* FROM events e WHERE e.created_at>=%(start)s '
            'AND e.created_at<=%(now)s AND NOT EXISTS(SELECT 1 FROM alert_routing_decisions r WHERE '
            'r.owner_id=e.owner_id AND r.kind=e.kind AND r.event_id=e.id AND r.policy=%(policy)s) '
            'ORDER BY e.created_at,e.id LIMIT 100',dict(owner=owner,start=start,now=now,policy=POLICY))
        return sum(bool(save(conn,owner,r,now=now)) for r in review_digest.details(conn,owner,events))


def poll_preview(owner):
    """A failed shadow calculation must not block ordinary Telegram delivery."""
    try:return run_once(owner)
    except Exception:
        logging.getLogger('thesis').warning('Alert routing preview could not be recorded; existing delivery continues.')
        return 0
