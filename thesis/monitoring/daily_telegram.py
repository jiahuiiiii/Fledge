"""Opt-in delivery of real daily records; previews can never be promoted.

All reads use existing private publications and current evidence access. The
outbox retains send intent and the shown-member mapping before any HTTP call.
No generation, model dispatch or account enrollment occurs here.
"""
from datetime import timedelta
from decimal import Decimal
from html import escape
import logging
from uuid import UUID,uuid4
from thesis.db import one,rows
from thesis import review_digest
from thesis.display_time import stamp
from . import daily_updates as D
from .telegram_message import plain,safe_url,visible_units

KINDS={'digest','cost'}
MAX_ITEMS=5


def start():
    value=D.option('THESIS_DAILY_TELEGRAM_STARTED_AT')
    return review_digest.clock(value) if value else None


def enabled(kind,*,now=None):
    if kind not in KINDS or not D.enabled():return False
    flag='THESIS_DIGEST_TELEGRAM_ENABLED' if kind=='digest' else 'THESIS_COST_TELEGRAM_ENABLED'
    if str(D.option(flag) or 'false').lower() not in {'true','1','on'}:return False
    try:
        since=start();now=now or D.clock()
        return since is not None and since<=now and (kind!='cost' or D.cost_threshold() is not None)
    except (ValueError,TypeError):return False


def enqueue(conn,owner,cfg,now):
    """Failure is isolated by a savepoint; ordinary delivery must continue."""
    try:
        with conn.transaction():
            since=start() if any(enabled(k,now=now) for k in KINDS) else None
            if since is None:return 0
            made=0
            for kind,table in (('digest','daily_digests'),('cost','daily_cost_notices')):
                if not enabled(kind,now=now) or (kind=='cost' and str(owner)!=str(D.OWNER)):continue
                eligible="AND EXISTS(SELECT 1 FROM daily_digest_members m WHERE m.owner_id=d.owner_id AND m.digest_id=d.id)" if kind=='digest' else 'AND threshold_nano_usd=%(threshold)s'
                candidates=rows(conn,f'SELECT d.id,d.created_at FROM {table} d WHERE d.owner_id=%(owner)s AND NOT d.preview '
                    'AND d.created_at>%(account_start)s AND d.created_at>=%(start)s AND d.created_at>%(fresh)s AND d.created_at<=%(now)s '
                    f'{eligible} AND NOT EXISTS(SELECT 1 FROM telegram_deliveries t WHERE t.owner_id=d.owner_id AND t.kind=%(kind)s AND t.event_id=d.id) '
                    'ORDER BY d.created_at,d.id LIMIT 100',dict(owner=owner,kind=kind,account_start=cfg['enabled_at'],
                    start=since,fresh=now-timedelta(hours=24),now=now,threshold=D.cost_threshold() if kind=='cost' else None))
                for item in candidates:
                    conn.execute('INSERT INTO telegram_deliveries(id,owner_id,kind,event_id,event_at) VALUES(%s,%s,%s,%s,%s) '
                        'ON CONFLICT(owner_id,kind,event_id) DO NOTHING',(uuid4(),owner,kind,item['id'],item['created_at']))
                    made+=1
            return made
    except Exception:
        logging.getLogger('thesis').warning('Daily Telegram preparation failed; existing alert delivery continues.')
        return 0


def usd(nano,*,exact=False):
    value=Decimal(nano)/D.NANO
    if exact:return 'US$'+format(value,'f')
    if 0<value<Decimal('.01'):return 'under US$0.01'
    return 'US$'+format(value,'.2f')


def summary(record,number,*,shown=None):
    """Short evidence stays beside its company; whole blocks are length checked."""
    detail=record['detail'];kind=record['kind']
    label={'company':'Company update','idea':'Saved idea','condition':'Monitored condition','move':'Price move'}[kind]
    parts=[f"<b>{number}. {escape(plain(detail.get('symbol'),18))} · {label}</b>"]
    source_ids=[]
    if detail.get('fictional'):parts.append('Fictional demo · not actual company news')
    if kind=='company':
        payload=detail['payload'];parts.append(escape(plain(record['title'],90)))
        items=payload.get('items',[])
        if items:
            item=items[0];source_ids.append(item['source_id'])
            basis=item.get('reporting_basis') or {};quotes=basis.get('citations') or item.get('citations') or []
            if quotes:
                label='Unconfirmed source report' if basis.get('kind')=='unconfirmed_event' else 'Source excerpt'
                parts.append(label+': “'+escape(plain(quotes[0].get('quote'),140))+'”')
        else:
            for change in payload.get('shifts',[])[:2]:
                parts.append(escape(plain(change.get('title'),45))+': '+escape(plain(change['before']['tone'],20))+' → '+escape(plain(change['after']['tone'],20)))
    elif kind=='idea':
        parts.append('Your question: '+escape(plain(detail.get('question'),70)))
        matched=[i for i in detail['items'] if i.get('relation') in {'supports','challenges','risk','answers'}]
        if matched:
            item=matched[0];source_ids.append(item['source_id'])
            from .telegram_message import RELATIONS
            parts.append(RELATIONS[item['relation']]+': '+escape(plain(item.get('explanation'),90)))
            quotes=item.get('citations') or []
            if quotes:parts.append('Source excerpt: “'+escape(plain(quotes[0].get('quote'),80))+'”')
    elif kind=='condition':
        parts.append(escape(plain(record['title'],90)))
        for item in detail.get('details',{}).get('affected_conditions',[])[:2]:
            before='Unknown' if item.get('before') is None else plain(item['before'],24)+'%'
            after='Unknown' if item.get('after') is None else plain(item['after'],24)+'%'
            parts.append(escape(plain(item.get('metric','Condition').replace('_',' '),40))+': '+escape(before)+' → '+escape(after))
        for item in detail.get('details',{}).get('affected_events',[])[:2]:
            parts.append(escape(plain(item.get('description'),70))+': '+escape(plain(item.get('before'),20))+' → '+escape(plain(item.get('after'),20)))
        source_ids.extend(s['id'] for s in detail.get('sources',[])[:2])
    else:
        from .move_alerts import numbers,percent
        values=numbers(detail['members'])  # Never truncate a grouped member list.
        index=detail['members'][0]['indexes'].get('QQQ')
        values+=f" · Nasdaq {percent(index['change_percent'])}" if index else ' · Nasdaq unavailable'
        parts.append(escape(values))
        parts.append(escape(plain((detail.get('explanation') or {}).get('text') or 'No verified explanation is saved.',120)))
        source_ids.extend(s['id'] for s in detail.get('sources',[])[:2])
    text='\n'.join(parts)
    if visible_units(text)>680:return None
    if shown is not None:shown.extend(source_ids)
    sources={str(s['id']):s for s in detail.get('sources',[])}
    links=[]
    for sid in dict.fromkeys(map(str,source_ids)):
        source=sources.get(sid,{});url=safe_url(source.get('url'))
        if url:links.append((url,plain(source.get('source') or source.get('title') or 'Read source',55)))
    return text,links


def digest_record(conn,owner,identity,now,*,delivery_id=None):
    from . import telegram as T
    from . import telegram_stories as G
    digest=one(conn,'SELECT * FROM daily_digests WHERE owner_id=%s AND id=%s',(owner,identity))
    if not digest or digest['preview']:return None
    members=rows(conn,'SELECT m.* FROM daily_digest_members m JOIN alert_routing_decisions r ON r.owner_id=m.owner_id AND r.id=m.route_id '
        'WHERE m.owner_id=%s AND m.digest_id=%s AND NOT r.preview ORDER BY m.position LIMIT 1001',(owner,identity))
    if not members or len(members)>1000:return None
    footer='Open Fledge on your Mac → Updates → Daily recaps for all saved updates and evidence.\nResearch alerts · not buy/sell instructions.'
    parts=['<b>Fledge · Daily recap</b>',escape(stamp(digest['window_start'])+'–'+stamp(digest['window_end']))]
    shown=[];linked=set();unavailable=0;remaining=0;duplicates=0;story_keys=set();deferred=[]
    guarded=delivery_id is not None and (G.enabled(now) or digest['policy']==D.LIVE_POLICY)
    legacy=G.legacy_keys(conn,owner,delivery_id,now) if guarded else set()
    for member in members:
        if len(shown)>=MAX_ITEMS:
            remaining+=1;continue
        record=T.event(conn,owner,member['kind'],member['event_id'])
        if not record or record['detail'].get('withheld') or record['detail'].get('preview'):
            unavailable+=1;continue
        if guarded:
            try:record=G.prepare(conn,owner,record,delivery_id,now,local=story_keys,legacy=legacy,force=True)
            except G.Suppressed:duplicates+=1;continue
            except G.Deferred as exc:deferred.append(exc.when);remaining+=1;continue
        primary=[]
        block=summary(record,len(shown)+1,shown=primary)
        if not block:
            remaining+=1;continue
        text=block[0];new_links=[]
        for url,name in block[1]:
            if url not in linked and url not in {u for u,_ in new_links} and len(linked)+len(new_links)<2:new_links.append((url,name))
        if new_links:text+='\n'+'\n'.join(f'<a href="{escape(url,quote=True)}">{escape(name)}</a>' for url,name in new_links)
        if visible_units('\n\n'.join(parts+[text,footer]))>3400:
            remaining+=1;continue
        parts.append(text);linked.update(url for url,_ in new_links)
        if guarded:story_keys.update(G.shown_keys(record,primary))
        shown.append(dict(position=len(shown),member_position=member['position']))
    if not shown:
        if deferred:raise G.Deferred(min(deferred))
        if duplicates:raise G.Suppressed(G.ALREADY)
        return None
    if unavailable:parts.append(f'{unavailable} saved updates could not be forwarded with current evidence or idea access.')
    if remaining:parts.append(f'{remaining} more saved updates are in this recap in Fledge.')
    if duplicates:
        noun='update is' if duplicates==1 else 'updates are'
        parts.append(f'{duplicates} repeated {noun} omitted here; the full recap remains in Fledge.')
    parts.append(footer);message='\n\n'.join(parts)
    if visible_units(message)>3800:raise ValueError('The complete recap exceeds the message bound.')
    return dict(kind='digest',id=str(identity),created_at=digest['created_at'],title='Daily recap',
                detail=dict(preview=False,withheld=False,message=message,shown=shown),_story_keys=story_keys,_story_guarded=guarded)


def cost_record(conn,owner,identity,now):
    if str(owner)!=str(D.OWNER):return None
    notice=one(conn,'SELECT * FROM daily_cost_notices WHERE owner_id=%s AND id=%s',(owner,identity))
    if not notice or notice['preview'] or notice['threshold_nano_usd']!=D.cost_threshold():return None
    text='\n\n'.join(['<b>Fledge · AI spending notice</b>',
        f"{notice['day'].isoformat()} in Singapore · all AI use in this installation, including tests.",
        f"Confirmed charges: <b>{usd(notice['charged_nano_usd'],exact=True)}</b> · above your {usd(notice['threshold_nano_usd'])} notification level.",
        f"Unresolved maximum, separate from confirmed charges: {usd(notice['pending_max_nano_usd'],exact=True)}.",
        'Checked '+stamp(notice['created_at'])+'. This notice does not pause spending or retry a paid call.',
        'Open Fledge on your Mac → Updates → Daily recaps for current spending and earlier observations.'])
    return dict(kind='cost',id=str(identity),created_at=notice['created_at'],title='AI spending notice',
                detail=dict(preview=False,withheld=False,message=text))


def record(conn,owner,kind,identity,now,*,delivery_id=None):
    if not enabled(kind,now=now):return None
    value=(digest_record(conn,owner,identity,now,delivery_id=delivery_id) if kind=='digest' else cost_record(conn,owner,identity,now))
    since=start()
    return value if value and since<=value['created_at']<=now else None


def render(record):
    detail=record['detail']
    if detail.get('preview') or detail.get('withheld'):raise ValueError('Preview or withheld daily records cannot be forwarded.')
    text=detail['message']
    if visible_units(text)>3800:raise ValueError('Daily message exceeds the message bound.')
    return text


def save_shown(conn,owner,delivery,record):
    for item in record['detail']['shown']:
        conn.execute('INSERT INTO telegram_digest_items VALUES(%s,%s,%s,%s,%s)',
            (owner,delivery['id'],delivery['attempts']+1,item['position'],item['member_position']))


def keyboard(delivery,items):
    if not items:return None
    token=UUID(str(delivery['id'])).hex
    return dict(inline_keyboard=[[
        dict(text=f"{i['position']+1} · Useful",callback_data=f"d:{token}:{i['position']}:u"),
        dict(text=f"{i['position']+1} · Not useful",callback_data=f"d:{token}:{i['position']}:n"),
    ] for i in items])
