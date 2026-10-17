"""Private append-only usefulness ratings; explicit clicks only, no AI calls."""
from uuid import UUID,uuid4
from datetime import datetime,timezone
from thesis.db import transaction,one
from thesis import service

KINDS={'company','idea','condition','move'}
VALUES={'useful','not_useful'}


def enabled():
    from .move_watch import option
    return str(option('THESIS_ALERT_FEEDBACK') or 'false').lower() in {'true','1','on'}


def latest(conn,owner,kind,event_id):
    row=one(conn,'SELECT value,source,created_at FROM alert_feedback WHERE owner_id=%s AND kind=%s AND event_id=%s '
            'ORDER BY created_at DESC,id DESC LIMIT 1',(owner,kind,event_id))
    return dict(value=row['value'],source=row['source'],rated_at=row['created_at']) if row else None


def rate(owner,kind,event_id,value,*,source='app',request_key=None):
    if not enabled():raise ValueError('Alert ratings are not enabled yet.')
    if kind not in KINDS or value not in VALUES or source not in {'app','telegram'}:
        raise ValueError('Choose useful or not useful for a saved alert.')
    event_id=str(UUID(str(event_id)))
    with transaction(owner) as conn:
        conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',
                     ('alert-feedback:'+str(owner)+':'+kind+':'+event_id,))
        if not one(conn,'SELECT alert_event_exists(%s,%s,%s) found',(owner,kind,event_id))['found']:
            raise service.Missing('This saved alert is not available in your account.')
        previous=latest(conn,owner,kind,event_id)
        if previous and previous['value']==value and request_key is None:return previous
        conn.execute('INSERT INTO alert_feedback VALUES(%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(owner_id,request_key) DO NOTHING',
                     (uuid4(),owner,kind,event_id,value,source,datetime.now(timezone.utc),request_key))
        return latest(conn,owner,kind,event_id)


def keyboard(delivery):
    if not enabled() or delivery['kind'] not in KINDS:return None
    token=UUID(str(delivery['id'])).hex
    return dict(inline_keyboard=[[
        dict(text='Useful',callback_data='f:'+token+':u'),
        dict(text='Not useful',callback_data='f:'+token+':n'),
    ]])
