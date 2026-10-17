"""Daily medium-route membership and exact spending observations; no AI/HTTP.

Records are previews in this preparation. Reading never generates a digest or
notifies anyone. Source access is rechecked when frozen membership is opened.
"""
from datetime import datetime,date,time,timedelta,timezone
from decimal import Decimal,InvalidOperation
import logging
from uuid import UUID,uuid4
from zoneinfo import ZoneInfo
from thesis.config import OWNER
from thesis.db import transaction,one,rows
from thesis import service,review_digest
from .review_schedule import occurrence
from .move_watch import option

POLICY='daily-updates-1'
NANO=Decimal(1_000_000_000)
SGT=ZoneInfo('Asia/Singapore')
PAGE_SIZE=20
TOO_MANY='This daily recap exceeds 1,000 updates; no partial recap was saved.'
ERRORS={
    'preparation_failed':'The daily recap could not be prepared. Your existing updates remain available below.',
    'too_many_records':'More than 1,000 updates need a recap. Open the individual updates below; none were marked reviewed.',
}


def enabled():return str(option('THESIS_DAILY_REPORTS') or 'false').lower() in {'true','1','on'}


def started():
    value=option('THESIS_DAILY_REPORTS_STARTED_AT')
    return review_digest.clock(value) if value else None


def clock():return datetime.now(timezone.utc)


def cost_threshold():
    value=option('THESIS_DAILY_COST_ALERT_USD')
    if value in (None,''):return None  # No unapproved live default.
    try:
        result=Decimal(str(value))
        if not result.is_finite() or not Decimal('.01')<=result<=1_000_000:raise ValueError()
        if result*100!=(result*100).to_integral_value():raise ValueError()
        return int(result*NANO)
    except (InvalidOperation,ValueError):raise ValueError('Choose a finite daily cost level in whole cents from US$0.01toUS$1,000,000.') from None


def day_bounds(day):
    return (datetime.combine(day,time(),SGT).astimezone(timezone.utc),
            datetime.combine(day+timedelta(days=1),time(),SGT).astimezone(timezone.utc))


def spend(owner,day,*,now=None):
    """Installation aggregates only, never another account's prompts/identities."""
    if str(owner)!=str(OWNER):return None
    now=review_digest.clock(now or clock());start,end=day_bounds(day)
    with transaction(admin=True,consistent=True) as conn:
        value=one(conn,"SELECT coalesce(sum(charged_nano_usd) FILTER(WHERE status='settled' AND finished_at<=%(now)s),0)::bigint charged,"
            "coalesce(sum(reserved_nano_usd) FILTER(WHERE status<>'settled' OR finished_at IS NULL OR finished_at>%(now)s),0)::bigint pending,"
            "count(*) FILTER(WHERE status='settled' AND finished_at<=%(now)s) settled_calls,"
            "count(*) FILTER(WHERE status<>'settled' OR finished_at IS NULL OR finished_at>%(now)s) pending_calls,"
            "coalesce(sum(charged_nano_usd) FILTER(WHERE status='settled' AND finished_at<=%(now)s AND starts_with(request_key,'experiment:')),0)::bigint experiments "
            'FROM model_calls WHERE created_at>=%(start)s AND created_at<%(end)s AND created_at<=%(now)s',
            dict(start=start,end=end,now=now))
    return dict(day=day.isoformat(),window_start=start,window_end=end,observed_at=now,scope='installation',
        charged_nano_usd=value['charged'],pending_max_nano_usd=value['pending'],
        charged_usd=str(Decimal(value['charged'])/NANO),pending_max_usd=str(Decimal(value['pending'])/NANO),
        experiment_charged_nano_usd=value['experiments'],experiment_charged_usd=str(Decimal(value['experiments'])/NANO),
        settled_calls=value['settled_calls'],pending_calls=value['pending_calls'])


def next_digest(conn,owner,since,now):
    last=one(conn,'SELECT window_end FROM daily_digests WHERE owner_id=%s AND policy=%s ORDER BY window_end DESC LIMIT 1',(owner,POLICY))
    if last:
        start=last['window_end'];end=occurrence(start.astimezone(SGT).date()+timedelta(days=1),420,SGT)
    else:
        local=since.astimezone(SGT);end=occurrence(local.date(),420,SGT)
        if end<=since:end=occurrence(local.date()+timedelta(days=1),420,SGT)
        start=max(since,occurrence(end.astimezone(SGT).date()-timedelta(days=1),420,SGT))
    return (start,end) if end<=now else None


def make_digest(conn,owner,start,end,now):
    candidates=rows(conn,"SELECT r.* FROM (SELECT DISTINCT ON(kind,event_id) * FROM alert_routing_decisions WHERE owner_id=%s "
        "ORDER BY kind,event_id,created_at DESC,id DESC) r WHERE r.channel='digest' "
        'AND r.created_at>=%s AND r.created_at<%s AND NOT EXISTS(SELECT 1 FROM daily_digest_members m '
        'WHERE m.owner_id=r.owner_id AND m.kind=r.kind AND m.event_id=r.event_id) ORDER BY r.created_at,r.id LIMIT 1001',(owner,start,end))
    if len(candidates)>1000:raise ValueError(TOO_MANY)
    identity=uuid4()
    conn.execute('INSERT INTO daily_digests VALUES(%s,%s,%s,%s,%s,%s,true)',(identity,owner,start,end,now,POLICY))
    for position,r in enumerate(candidates):
        conn.execute('INSERT INTO daily_digest_members VALUES(%s,%s,%s,%s,%s,%s)',
            (owner,identity,position,r['id'],r['kind'],r['event_id']))
    return identity


def save_spend(conn,owner,day,now):
    value=spend(owner,day,now=now)
    if value is None:return None
    conn.execute('INSERT INTO daily_spend_reports VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) '
        'ON CONFLICT(owner_id,day,policy) DO NOTHING',
        (uuid4(),owner,day,value['window_start'],value['window_end'],now,POLICY,
         value['charged_nano_usd'],value['pending_max_nano_usd'],value['settled_calls'],value['pending_calls'],value['experiment_charged_nano_usd']))
    return value


def notice(conn,owner,day,now,threshold):
    value=spend(owner,day,now=now)
    if value is None or threshold is None or value['charged_nano_usd']<=threshold:return None
    return one(conn,'INSERT INTO daily_cost_notices VALUES(%s,%s,%s,%s,%s,%s,%s,%s,true) '
        'ON CONFLICT(owner_id,day,policy) DO NOTHING RETURNING id',
        (uuid4(),owner,day,threshold,value['charged_nano_usd'],value['pending_max_nano_usd'],now,POLICY))


def run_once(owner,*,now=None):
    if not enabled():return 0
    now=review_digest.clock(now or clock());since=started()
    if since is None or since>now:return 0
    with transaction(owner) as conn:
        if not one(conn,'SELECT pg_try_advisory_xact_lock(hashtextextended(%s,0)) locked',('daily-updates:'+str(owner),))['locked']:return 0
        state=one(conn,'SELECT next_check_at,last_success_at FROM daily_updates_state WHERE owner_id=%s',(owner,))
        if state and state['next_check_at']>now:return 0
        created=0;window=next_digest(conn,owner,since,now)
        if window:make_digest(conn,owner,*window,now);created+=1
        if str(owner)==str(OWNER):
            today=now.astimezone(SGT).date();first=since.astimezone(SGT).date()
            last=one(conn,'SELECT max(day) AS report_day FROM daily_spend_reports WHERE owner_id=%s AND policy=%s',(owner,POLICY))['report_day']
            report_day=last+timedelta(days=1) if last else first
            if report_day<today:save_spend(conn,owner,report_day,now);created+=1
            threshold=cost_threshold()
            if threshold is not None:
                # Only settlements changed since the previous observation need
                # another day-level check; today's total is always current.
                changed=max(since,state['last_success_at']) if state and state['last_success_at'] else since
                with transaction(admin=True,consistent=True) as costs:
                    days=rows(costs,"SELECT DISTINCT (created_at AT TIME ZONE 'Asia/Singapore')::date AS report_day FROM model_calls "
                        "WHERE finished_at>=%s AND finished_at<=%s AND status='settled' AND created_at>=%s",
                        (changed,now,day_bounds(first)[0]))
                for day in {today}|{r['report_day'] for r in days}:
                    created+=bool(notice(conn,owner,day,now,threshold))
        conn.execute('INSERT INTO daily_updates_state VALUES(%s,%s,%s,%s,NULL) ON CONFLICT(owner_id) '
            'DO UPDATE SET next_check_at=excluded.next_check_at,last_attempt_at=excluded.last_attempt_at,last_success_at=excluded.last_success_at,error=NULL',
            (owner,now+timedelta(minutes=1),now,now))
        return created


def poll(owner):
    try:return run_once(owner)
    except Exception as exc:
        logging.getLogger('thesis').warning('Daily recap preparation failed; existing alerts and delivery continue.')
        if enabled():
            try:
                now=clock();error='too_many_records' if isinstance(exc,ValueError) and str(exc)==TOO_MANY else 'preparation_failed'
                with transaction(owner) as conn:
                    conn.execute('INSERT INTO daily_updates_state VALUES(%s,%s,%s,NULL,%s) ON CONFLICT(owner_id) '
                        'DO UPDATE SET next_check_at=excluded.next_check_at,last_attempt_at=excluded.last_attempt_at,error=excluded.error',
                        (owner,now+timedelta(hours=1),now,error))
            except Exception:pass  # Status-storage failure cannot block ordinary delivery either.
        return 0


def digest_rows(conn,owner):
    return rows(conn,'SELECT d.*,count(m.position) total FROM daily_digests d LEFT JOIN daily_digest_members m '
        'ON m.owner_id=d.owner_id AND m.digest_id=d.id WHERE d.owner_id=%s GROUP BY d.id '
        'ORDER BY d.window_end DESC,d.id DESC LIMIT 7',(owner,))


def history(owner,*,now=None):
    if not enabled():return dict(enabled=False,digests=[],spending=[],notices=[],today_spend=None)
    now=review_digest.clock(now or clock())
    with transaction(owner,consistent=True) as conn:
        digests=digest_rows(conn,owner)
        spending=rows(conn,'SELECT * FROM daily_spend_reports WHERE owner_id=%s ORDER BY day DESC LIMIT 7',(owner,)) if str(owner)==str(OWNER) else []
        notices=rows(conn,'SELECT * FROM daily_cost_notices WHERE owner_id=%s ORDER BY created_at DESC LIMIT 7',(owner,)) if str(owner)==str(OWNER) else []
        state=one(conn,'SELECT last_attempt_at,next_check_at,error FROM daily_updates_state WHERE owner_id=%s',(owner,))
    spending=[dict(value,current=spend(owner,value['day'],now=now)) for value in spending]
    return dict(enabled=True,digests=digests,spending=spending,notices=notices,
                preparation=dict(state,error_message=ERRORS.get(state['error'])) if state else None,
                today_spend=spend(owner,now.astimezone(SGT).date(),now=now))


def read(owner,identity,*,page=0):
    if not enabled():raise service.Missing('Daily recaps are not enabled.')
    if type(page) is not int or not 0<=page<=100000:raise ValueError('Choose a valid daily recap page.')
    identity=str(UUID(str(identity)))
    with transaction(owner,consistent=True) as conn:
        digest=one(conn,'SELECT * FROM daily_digests WHERE owner_id=%s AND id=%s',(owner,identity))
        if not digest:raise service.Missing('This daily recap is unavailable in your account.')
        total=one(conn,'SELECT count(*) n FROM daily_digest_members WHERE owner_id=%s AND digest_id=%s',(owner,identity))['n']
        events=rows(conn,review_digest.EVENTS+'SELECT e.* FROM events e JOIN daily_digest_members m '
            'ON m.owner_id=e.owner_id AND m.kind=e.kind AND m.event_id=e.id '
            'WHERE m.owner_id=%(owner)s AND m.digest_id=%(digest)s ORDER BY m.position LIMIT %(limit)s OFFSET %(offset)s',
            dict(owner=owner,digest=identity,limit=PAGE_SIZE,offset=page*PAGE_SIZE))
        records=review_digest.details(conn,owner,events)
        return dict(digest,records=records,total=total,page=page,page_size=PAGE_SIZE,
            access_checked_at=clock(),limitation='Saved membership; source access, ratings and review status are checked now. Opening does not mark any alert reviewed.')
