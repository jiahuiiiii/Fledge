"""Persistent, bounded company loading queue with independently committed steps.

Workers execute source calls concurrently without holding a transaction. AI waits
for acquisition and the existing cumulative ledger; uncertain calls never retry.
"""
from datetime import datetime, timezone
from copy import deepcopy
import json
from uuid import uuid4
from psycopg.types.json import Jsonb
from thesis.db import transaction, one, rows
from thesis.service import Conflict

LABELS = dict(market='Quote & news', filings='Filings & fundamentals', disclosures='Original filings & earnings releases', prices='Price chart',
              reddit='Reddit discussions', hackernews='Hacker News discussions',
              rss='Publisher RSS feeds', alpha_vantage='Alpha Vantage news', x='X / Twitter posts',
              targets='Analyst targets', multiples='Valuation ratios', analysis='Sentiment analysis')
TERMINAL = {'ready', 'partial', 'failed', 'blocked', 'cached', 'interrupted'}


def worker_lease():
    """Only one app process may recover/start this installation's workers."""
    import psycopg
    from thesis.config import dsn
    conn = psycopg.connect(dsn(), autocommit=True)
    if conn.execute("SELECT pg_try_advisory_lock(hashtextextended('research-loading-worker-process',0))").fetchone()[0]:
        return conn
    conn.close()
    return None


def latest(owner, iid):
    with transaction(owner) as conn:
        run = one(conn, 'SELECT * FROM research_loads WHERE instrument_id=%s ORDER BY created_at DESC,id DESC LIMIT 1', (iid,))
        return explain_saved_failure(conn, run)


def explain_saved_failure(conn, run):
    """Explain the old generic message on read; preserve the original journal."""
    if not run:
        return run
    from . import sentiment, sentiment_batching
    company = one(conn, 'SELECT symbol FROM instruments WHERE id=%s', (run['instrument_id'],))
    if not company:
        return run
    for index, step in enumerate(run['steps']):
        batches = step.get('batches') or {}
        failed, total = batches.get('failed'), batches.get('total')
        if (step['key'] != 'analysis' or step['status'] != 'blocked' or batches.get('failure')
                or not isinstance(failed, int) or not isinstance(total, int)
                or not step.get('started_at') or not step.get('finished_at')
                or not step.get('message', '').startswith(f'Batch {failed} of {total} did not pass validation.')):
            continue
        calls = rows(conn, """SELECT * FROM model_calls WHERE purpose=ANY(%s) AND status='settled'
                       AND created_at>=%s AND finished_at<=%s ORDER BY finished_at DESC,id DESC LIMIT 32""",
                     ([sentiment.PROMPT, 'thesis-source-sentiment-20', 'thesis-source-sentiment-21', 'thesis-source-sentiment-22'], step['started_at'], step['finished_at']))
        for call in calls:
            try:
                wire = json.loads(call['request_body']['input'][1]['content'])
                if wire['company']['symbol'] != company['symbol']:
                    continue
                # Only attribute the final matching response, never an earlier failure.
                if len(wire['sources']) != batches['source_counts'][failed - 1]:
                    break
                sentiment.response_text(call)
            except sentiment.IncompleteResponse as exc:
                details = sentiment_batching.failure_details(call, exc)
                message = sentiment_batching.failure_message(failed, total, batches['completed'], details)
                result = deepcopy(run)
                result['steps'][index].update(message=message, batches=dict(batches, message=message, failure=details))
                return result
            except (ValueError, KeyError, TypeError, IndexError):
                break
            break
    return run


def start(owner, iid, *, initial=False, analyze=False, lookback_days=7):
    if type(lookback_days) is not int or lookback_days not in (1,7,30):
        raise ValueError('Choose a discussion window of 1, 7 or 30 days.')
    with transaction(owner) as conn:
        conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", ('research-load:'+str(owner)+str(iid),))
        if not one(conn, 'SELECT 1 FROM sec_companies WHERE instrument_id=%s', (iid,)):
            raise ValueError('Choose a registered company for research.')
        old = one(conn, 'SELECT * FROM research_loads WHERE instrument_id=%s ORDER BY created_at DESC,id DESC LIMIT 1', (iid,))
        if old and (initial or old['active']):
            return old
        # Clicking again within a short interval cannot churn provider requests.
        if old and not analyze and (datetime.now(timezone.utc)-old['created_at']).total_seconds()<15:
            raise Conflict('The last refresh just finished. Its results are shown below.')
        keys = [k for k in LABELS if k != 'analysis'] if not analyze else ['market','rss','alpha_vantage','reddit','hackernews','x','analysis']
        steps = [dict(key=k,label=LABELS[k],status='queued',message='Waiting for a worker') for k in keys]
        return one(conn, 'INSERT INTO research_loads(id,owner_id,instrument_id,lookback_days,steps) VALUES(%s,%s,%s,%s,%s) RETURNING *',
                   (uuid4(),owner,iid,lookback_days,Jsonb(steps)))


def _write(conn, run, index, **fields):
    step = dict(run['steps'][index], **fields)
    conn.execute('UPDATE research_loads SET steps=jsonb_set(steps,%s,%s),updated_at=now() WHERE id=%s',
                 ([str(index)],Jsonb(step),run['id']))


def recover(owner):
    # A process restart is not evidence that an external request did not happen.
    with transaction(owner) as conn:
        for run in rows(conn, 'SELECT * FROM research_loads WHERE active FOR UPDATE'):
            for index, step in enumerate(run['steps']):
                if step['status']=='running':
                    _write(conn,run,index,status='interrupted',message='The app stopped during this step. Review the saved result before refreshing.')


def claim(owner):
    from thesis.providers.ledger import snapshot
    with transaction(owner) as conn:
        conn.execute("SELECT pg_advisory_xact_lock(hashtextextended('research-loading-claims',0))")
        active = rows(conn, 'SELECT * FROM research_loads WHERE active ORDER BY created_at FOR UPDATE')
        ai_running = any(s['key']=='analysis' and s['status']=='running' for r in active for s in r['steps'])
        for run in active:
            if all(s['status'] in TERMINAL for s in run['steps']):
                conn.execute('UPDATE research_loads SET active=false,updated_at=now() WHERE id=%s', (run['id'],))
                continue
            for index, step in enumerate(run['steps']):
                if step['status']!='queued':
                    continue
                if step['key']=='disclosures' and any(s['key']=='filings' and s['status'] not in TERMINAL for s in run['steps']):
                    continue
                if step['key']=='analysis':
                    if any(s['status'] not in TERMINAL for s in run['steps'] if s['key']!='analysis'):
                        _write(conn,run,index,message='Waiting for news and discussions')
                        continue
                    budget = snapshot(conn)
                    if budget['running'] or ai_running:
                        _write(conn,run,index,message='Queued behind the current AI request')
                        continue
                    if budget['needs_attention']:
                        _write(conn,run,index,status='blocked',message='An earlier AI request needs charge review. No automatic confirmation or retry is running.')
                        conn.execute('UPDATE research_loads SET active=false,updated_at=now() WHERE id=%s', (run['id'],))
                        continue
                fields = dict(status='running',started_at=datetime.now(timezone.utc).isoformat(),message='Fetching sources' if step['key']!='analysis' else 'Reading selected source passages')
                _write(conn,run,index,**fields)
                run['steps'][index].update(fields)
                return run,index
    return None


def analysis_progress(run, progress):
    """Persist counts only, fenced to the current load's claimed analysis step."""
    index = next(i for i, s in enumerate(run['steps']) if s['key']=='analysis')
    with transaction(run['owner_id']) as conn:
        current = one(conn, 'SELECT * FROM research_loads WHERE id=%s FOR UPDATE', (run['id'],))
        if not current or not current['active'] or current['steps'][index]['status'] != 'running' or current['steps'][index].get('started_at') != run['steps'][index].get('started_at'):
            raise Conflict('This analysis run is no longer active. Completed batches remain saved.')
        _write(conn, current, index, batches=progress, message=progress['message'])


def execute(run, key):
    from . import market, social, hackernews, price_history, analyst_targets, multiples, sentiment, reddit_research
    from .sec import service as sec, disclosures
    from . import source_hub,x_source
    iid = str(run['instrument_id'])
    days = run['lookback_days']
    actions = dict(market=lambda: market.refresh(iid), filings=lambda: sec.refresh(iid),
                   disclosures=lambda: disclosures.refresh(iid),
                   rss=lambda: source_hub.refresh_rss(iid),alpha_vantage=lambda: source_hub.refresh(iid,'alpha_vantage'),
                   x=lambda: x_source.refresh(iid,lookback_days=days),
                   prices=lambda: price_history.refresh(iid), reddit=lambda: reddit_research.refresh(iid,lookback_days=days),
                   hackernews=lambda: hackernews.refresh(iid,lookback_days=days,include_threads=True),
                   targets=lambda: analyst_targets.refresh(iid), multiples=lambda: multiples.refresh(iid),
                   analysis=lambda: sentiment.generate(iid,lookback_days=days,
                       progress=lambda value: analysis_progress(run, value), retry_failed=True))
    result = actions[key]()
    if key=='filings':
        from thesis import service
        service.queue_current(str(run['owner_id']))
    if key=='analysis' and days==7:
        from thesis.monitoring.news_watch import publish
        publish(str(run['owner_id']),iid,result['id'])
    return result


def outcome(key, result):
    if isinstance(result,dict):
        if result.get('status') in TERMINAL:
            return result['status'],result.get('message','Source check complete')
        if result.get('errors') or result.get('failures'):
            return 'partial',result.get('message') or 'Some sources could not be reached. Open source coverage for details; saved data is retained.'
        if result.get('error') or result.get('last_error'):
            return 'failed','The provider could not supply this data. Saved data is retained.'
    return 'ready', result.get('message') if isinstance(result,dict) and result.get('message') else 'Analysis saved' if key=='analysis' else 'Source check complete'


def work_once(owner, executor=None):
    task=claim(owner)
    if not task:
        return False
    run,index=task
    key=run['steps'][index]['key']
    try:
        result=(executor or execute)(run,key)
        status,message=outcome(key,result)
    except (ValueError,Conflict) as exc:
        # Domain errors contain bounded user-facing text, never transport URLs.
        message=str(exc)
        cooldown=any(t in message.lower() for t in ('recently','apart','between attempts','already running','already being checked','every 24 hours'))
        status='cached' if cooldown and key!='analysis' else 'blocked' if key=='analysis' else 'failed'
    except Exception:
        status,message='failed','This step could not finish. Saved results are retained; use Refresh research to try again.'
    with transaction(owner) as conn:
        current=one(conn,'SELECT * FROM research_loads WHERE id=%s FOR UPDATE',(run['id'],))
        if not current or current['steps'][index]['status'] != 'running' or current['steps'][index].get('started_at') != run['steps'][index].get('started_at'):
            return True
        _write(conn,current,index,status=status,message=message,finished_at=datetime.now(timezone.utc).isoformat())
        statuses=[status if i==index else s['status'] for i,s in enumerate(current['steps'])]
        if all(s in TERMINAL for s in statuses):
            conn.execute('UPDATE research_loads SET active=false,updated_at=now() WHERE id=%s',(run['id'],))
    return True
