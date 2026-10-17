"""One durable bot update cursor for connection and private alert-rating clicks.

Only the cursor/times are global. Raw Telegram messages, names and identifiers
are not retained here. Rating rows remain private to their alert's account.
No source or AI calls; feedback polling is off until explicitly enabled.
"""
from datetime import timedelta
import re
from uuid import UUID
from thesis.db import transaction,one,rows
from . import telegram_transport as transport,alert_feedback


def private_sender(message,sender):
    if not isinstance(message,dict) or not isinstance(sender,dict):return False
    chat=message.get('chat') or {}
    if not isinstance(chat,dict):return False
    return (chat.get('type')=='private' and type(chat.get('id')) is int and chat['id']>0
        and type(sender.get('id')) is int and sender['id']==chat['id']
        and sender.get('is_bot') is False and not message.get('forward_origin') and not message.get('via_bot'))


def connect_message(conn,message,fingerprint,now):
    from . import telegram as T
    if not isinstance(message,dict):return
    sender=message.get('from') or {};text=message.get('text') or ''
    match=re.fullmatch(r'/start(?:@[A-Za-z0-9_]+)? ([A-Za-z0-9_-]{43})',text) if isinstance(text,str) else None
    if not match or not private_sender(message,sender):return
    cfg=one(conn,'SELECT owner_id,link_hash FROM telegram_settings WHERE bot_fingerprint=%s AND link_hash=%s '
        'AND link_expires_at>%s AND chat_id IS NULL',(fingerprint,T.fingerprint(match[1]),now))
    if not cfg:return
    label=T.plain(('@'+sender['username']) if sender.get('username') else sender.get('first_name','Private chat'),80)
    conn.execute('UPDATE telegram_settings SET chat_id=%s,chat_label=%s,link_hash=NULL,link_expires_at=NULL,enabled=false '
        'WHERE owner_id=%s AND link_hash=%s AND link_expires_at>%s AND chat_id IS NULL',
        (sender['id'],label,cfg['owner_id'],cfg['link_hash'],now))


def rating_callback(conn,callback,fingerprint,update_id):
    if not isinstance(callback,dict):return 'unavailable'
    if not alert_feedback.enabled():return 'paused'
    data=callback.get('data');message=callback.get('message') or {};sender=callback.get('from') or {}
    match=re.fullmatch(r'f:([0-9a-f]{32}):([un])',data) if isinstance(data,str) else None
    if not match or not isinstance(message,dict) or not isinstance(sender,dict) or not private_sender(message,sender):
        return 'unavailable'
    delivery=one(conn,'SELECT d.*,s.chat_id,s.bot_fingerprint FROM telegram_deliveries d '
        'JOIN telegram_settings s ON s.owner_id=d.owner_id WHERE d.id=%s',(str(UUID(match[1])),))
    if (not delivery or delivery['kind'] not in alert_feedback.KINDS
            or delivery['bot_fingerprint']!=fingerprint or delivery['chat_id']!=sender['id']):
        return 'unavailable'
    if delivery['status']=='sending':return 'pending'
    if (delivery['status']!='sent' or type(message.get('message_id')) is not int
            or delivery['message_id']!=message['message_id']):
        return 'unavailable'
    from thesis import service
    try:
        alert_feedback.rate(delivery['owner_id'],delivery['kind'],str(delivery['event_id']),
            'useful' if match[2]=='u' else 'not_useful',source='telegram',
            request_key='telegram:'+fingerprint+':'+str(update_id))
    except service.Missing:return 'unavailable'
    return 'saved'


def receive(*,force=False):
    """Poll one bot under a cross-process lock; commit ratings before advancing."""
    from . import telegram as T
    key=transport.token()
    if not key:return False
    fingerprint=T.fingerprint(key);now=T.clock();acknowledgements=[]
    with transaction(admin=True) as conn:
        if not one(conn,'SELECT pg_try_advisory_xact_lock(hashtextextended(%s,0)) locked',
                   ('telegram-updates:'+fingerprint,))['locked']:return False
        if not one(conn,'SELECT owner_id FROM telegram_settings WHERE bot_fingerprint=%s AND '
                   '(chat_id IS NOT NULL OR link_expires_at>%s) LIMIT 1',(fingerprint,now)):return False
        conn.execute('INSERT INTO telegram_poll_state(bot_fingerprint) VALUES(%s) ON CONFLICT DO NOTHING',(fingerprint,))
        state=one(conn,'SELECT * FROM telegram_poll_state WHERE bot_fingerprint=%s FOR UPDATE',(fingerprint,))
        if not force and state['next_poll_at'] and state['next_poll_at']>now:return False
        # Telegram may choose a random update ID after a week without updates.
        # Its queue retains only24hours; resetting the query cannot restore
        # already acknowledged updates. Durable rating keys remain idempotent.
        reset=state['last_update_at'] and now-state['last_update_at']>=timedelta(days=7)
        offset=0 if reset else state['update_offset']
        updates=transport.call(key,'getUpdates',dict(offset=offset,limit=100,timeout=5 if force else 0,
                                                    allowed_updates=['message','callback_query']))
        if not isinstance(updates,list) or len(updates)>100:
            raise ValueError('Telegram did not return bounded connection/rating updates.')
        valid=sorted((u for u in updates if isinstance(u,dict) and type(u.get('update_id')) is int
                      and 0<=u['update_id']<2**63-1 and u['update_id']>=offset),key=lambda u:u['update_id'])
        seen=set();new_offset=offset
        for update in valid:
            if update['update_id'] in seen:continue
            seen.add(update['update_id'])
            connect_message(conn,update.get('message'),fingerprint,now)
            callback=update.get('callback_query')
            if callback:
                result=rating_callback(conn,callback,fingerprint,update['update_id'])
                if result=='pending':break  # Wait for the original send acknowledgement.
                query_id=callback.get('id') if isinstance(callback,dict) else None
                if isinstance(query_id,str) and 1<=len(query_id)<=256:
                    acknowledgements.append((query_id,{'saved':'Rating saved.','paused':'Alert ratings are paused.'}.get(result,'This alert is unavailable.')))
            new_offset=update['update_id']+1
        conn.execute('UPDATE telegram_poll_state SET update_offset=%s,next_poll_at=%s,last_update_at=%s WHERE bot_fingerprint=%s',
            (new_offset,now+timedelta(seconds=5),now if new_offset!=offset else state['last_update_at'],fingerprint))
        conn.execute('UPDATE telegram_settings SET update_offset=greatest(update_offset,%s) WHERE bot_fingerprint=%s',
                     (new_offset,fingerprint))
    # A failed callback acknowledgement does not undo or repeat a saved vote.
    for query_id,text in acknowledgements:
        try:transport.call(key,'answerCallbackQuery',dict(callback_query_id=query_id,text=text,cache_time=0))
        except Exception:pass
    return bool(valid)


def poll_feedback():
    if not alert_feedback.enabled():return False
    return receive()
