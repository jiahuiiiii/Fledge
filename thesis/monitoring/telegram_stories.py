"""Account-private 24-hour suppression for actual routing and actual recaps.

Claims cover only displayed primary evidence, never a whole reading. Current
attempt/status decides whether an immutable claim reserves a story. No AI/HTTP.
"""
from copy import deepcopy
from datetime import timedelta
from hashlib import sha256
from urllib.parse import urlsplit,urlunsplit,parse_qsl,urlencode
from thesis.db import one,rows
from thesis.research import coverage
from . import alert_routing as R
from .telegram_message import safe_url,render

ALREADY='These stories were already sent or may have been delivered in the last 24 hours. Full evidence remains in Updates.'


class Suppressed(ValueError):pass


class Deferred(Exception):
    def __init__(self,when):self.when=when


def enabled(now):return R.live_active(now)


def key(kind,value):return kind+':'+sha256(str(value).encode()).hexdigest()


def article(url):
    """Strip only known tracking fields; retain article-identifying parameters."""
    if not safe_url(url):return None
    parsed=urlsplit(url)
    query=[(k,v) for k,v in parse_qsl(parsed.query,keep_blank_values=True)
           if not k.lower().startswith('utm_') and k.lower() not in {'fbclid','gclid'}]
    if parsed.path in ('','/') and not query:return None  # A publisher homepage is not an article.
    return urlunsplit(('https',parsed.hostname.lower(),parsed.path or '/',urlencode(sorted(query)),''))


def source_keys(analysis,source,*,for_claim=False):
    if source['channel']!='news':
        return {key('social',str(source.get('platform'))+':'+str(source.get('post_key') or source['id']))}
    keys=coverage.keys(analysis,source)
    url=article(source.get('url'))
    if url is None:keys={k for k in keys if not k.startswith('article:')}
    # A cited update/denial is a development, not another delivery of the old
    # story. Identical old excerpts cannot manufacture this exception.
    linked=next((l for l in analysis['result'].get('coverage_links',[]) if l['source_id']==source['id']),None)
    changed=bool(linked and coverage.change_for_review(linked))
    if not changed:
        item=next((i for i in analysis['result']['items'] if i['source_id']==source['id']),None)
        changed=bool(item and any(article(p.get('url'))==url and url
            and coverage._repeat_guard(source,p) and coverage.reporting_changed(item,p)
            for p in analysis['packet'].get('comparison_sources',[])))
    if changed:
        keys={k for k in keys if not k.startswith('article:')}
        if url:keys.add(key('update',url+'\n'+source['content_hash']))
        if url and for_claim:keys.add(key('url',url))
    elif url:keys.add(key('url',url))
    return keys


def analysis_for(conn,owner,record):
    if record['kind']=='company':
        return one(conn,'SELECT a.packet,a.result FROM research_alerts p JOIN sentiment_analyses a ON a.id=p.current_id '
            'WHERE p.owner_id=%s AND p.id=%s',(owner,record['id']))
    return one(conn,'SELECT a.packet,a.result FROM idea_alert_checks p JOIN sentiment_analyses a ON a.id=p.analysis_id '
        'WHERE p.owner_id=%s AND p.id=%s',(owner,record['id']))


def groups(conn,owner,record,*,for_claim=False):
    """Price/condition changes have their own identity; cited news is context."""
    kind=record['kind'];detail=record['detail']
    if kind not in {'company','idea'}:
        return {'__event':{key('event',kind+':'+str(record['id']))}}
    items=detail.get('payload',{}).get('items',[]) if kind=='company' else [
        i for i in detail['items'] if i.get('relation') in {'supports','challenges','risk','answers'}]
    if not items:return {'__event':{key('event',kind+':'+str(record['id']))}}
    analysis=analysis_for(conn,owner,record)
    if not analysis:raise ValueError('The original story evidence is unavailable.')
    sources={s['id']:s for s in analysis['packet']['sources']}
    return {i['source_id']:source_keys(analysis,sources[i['source_id']],for_claim=for_claim) for i in items}


def blockers(conn,owner,keys,delivery_id,now):
    if not keys:return []
    return rows(conn,"SELECT c.story_key,t.status,t.retry_at FROM telegram_story_claims c JOIN telegram_deliveries t "
        'ON t.owner_id=c.owner_id AND t.id=c.delivery_id AND t.attempts=c.attempt '
        'WHERE c.owner_id=%s AND c.story_key=ANY(%s) AND c.delivery_id<>%s '
        "AND t.status IN ('sent','uncertain','sending','queued') "
        "AND (CASE WHEN t.status='sent' THEN t.sent_at ELSE c.created_at END)>%s",
        (owner,list(keys),delivery_id,now-timedelta(hours=24)))


def legacy_keys(conn,owner,delivery_id,now):
    """Read old deliveries without backfilling claims or promoting previews.

    Old ordinary messages used the same bounded formatter. Current access and
    private revisions are rechecked; unavailable interpretations are not used.
    """
    from . import telegram as T
    old=rows(conn,"SELECT t.* FROM telegram_deliveries t WHERE t.owner_id=%s AND t.id<>%s "
        "AND t.kind IN ('company','idea','condition','move') AND t.status IN ('sent','uncertain') "
        "AND coalesce(t.sent_at,t.attempted_at,t.created_at)>%s "
        'AND NOT EXISTS(SELECT 1 FROM telegram_story_claims c WHERE c.owner_id=t.owner_id AND c.delivery_id=t.id AND c.attempt=t.attempts) '
        'ORDER BY t.created_at DESC LIMIT 1001',(owner,delivery_id,now-timedelta(hours=24)))
    if len(old)>1000:raise ValueError('Too many earlier deliveries to check safely.')
    result=set()
    for job in old:
        try:
            record=T.event(conn,owner,job['kind'],job['event_id'])
            if not record or record['detail'].get('withheld') or record['detail'].get('preview'):continue
            shown=[];render(record,shown=shown)
            mapping=groups(conn,owner,record,for_claim=True)
        except (ValueError,KeyError,TypeError,IndexError):continue
        result.update(k for sid in (shown or ['__event']) for k in mapping.get(sid,()))
    return result


def prepare(conn,owner,record,delivery_id,now,*,local=(),immediate=False,legacy=None,force=False):
    """Filter only the message copy. Saved publications and membership stay exact."""
    if not force and not enabled(now):return record
    if record['detail'].get('preview') or record['detail'].get('withheld'):
        raise ValueError('Preview or withheld evidence cannot acquire delivery claims.')
    record=deepcopy(record);mapping=groups(conn,owner,record)
    keys=set().union(*mapping.values())
    held=blockers(conn,owner,keys,delivery_id,now)
    done={r['story_key'] for r in held if r['status']!='queued'}|set(local)
    done.update(legacy_keys(conn,owner,delivery_id,now) if legacy is None else legacy)
    pending={r['story_key'] for r in held if r['status']=='queued'}
    detail=record['detail'];kind=record['kind']
    if immediate and kind in {'company','idea'} and '__event' not in mapping:
        analysis=analysis_for(conn,owner,record)
        high={i['source_id'] for i in analysis['result']['items'] if R.importance(i)=='high'}
        mapping={sid:v for sid,v in mapping.items() if sid in high}
        if not mapping:raise Suppressed('No high-importance evidence remains for immediate delivery. Review the alert in Updates.')
    claim_mapping=groups(conn,owner,record,for_claim=True)
    kept={};within=set()
    for sid,value in mapping.items():
        if not value&(done|pending|within):
            kept[sid]=value;within.update(claim_mapping[sid])
    if not kept:
        if any(v&pending and not v&done for v in mapping.values()):
            dates=[r['retry_at'] for r in held if r['status']=='queued' and r['retry_at']]
            raise Deferred(max(now+timedelta(seconds=5),min(dates)) if dates else now+timedelta(seconds=30))
        raise Suppressed(ALREADY)
    if kind=='company' and '__event' not in kept:
        detail['payload']['items']=[i for i in detail['payload']['items'] if i['source_id'] in kept]
    elif kind=='idea' and '__event' not in kept:
        detail['items']=[i for i in detail['items'] if i['source_id'] in kept]
    record['_story_groups']=kept
    record['_story_claim_groups']={sid:claim_mapping[sid] for sid in kept}
    return record


def shown_keys(record,shown):
    mapping=record.get('_story_claim_groups',{})
    if '__event' in mapping:return set(mapping['__event'])
    return {k for sid in shown for k in mapping.get(sid,())}


def save(conn,owner,job,keys,now):
    for story in sorted(keys):
        conn.execute('INSERT INTO telegram_story_claims VALUES(%s,%s,%s,%s,%s)',
            (owner,job['id'],job['attempts']+1,story,now))
