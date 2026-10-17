"""Actual routing is opt-in; all providers/Telegram are invented and offline."""
from datetime import datetime,timedelta,timezone
import json
from uuid import uuid4
import psycopg
import pytest
from thesis.db import transaction,one,rows
from thesis import review_digest
from thesis.monitoring import alert_routing as R,daily_updates as D,news_watch as W,telegram as T,move_alerts as A
from thesis.research import sentiment as S
from test_model_budget import clean_model_ledger  # noqa: F401
from test_telegram import bot,link,unpace,all_deliveries  # noqa: F401
from test_market import prepare,commit,news
from test_sentiment import provider as legacy
from test_sentiment_task_runner import provider
from test_move_alerts import setup as move_setup
from test_price_moves import NOW
from test_daily_updates import model_call


def activate(monkeypatch,at):
    monkeypatch.setenv('THESIS_ALERT_ROUTING_LIVE','true')
    monkeypatch.setenv('THESIS_ALERT_ROUTING_LIVE_STARTED_AT',at.isoformat())


def company(owner,monkeypatch,level='high',*,actual=True,adverse=False):
    iid=prepare(owner)
    if adverse:
        monkeypatch.setenv('THESIS_SENTIMENT_TASKS','true')
        S.generate(iid,transport=provider([]))
    else:S.generate(iid,transport=legacy('neutral'))
    W.configure(owner,iid,True)
    monkeypatch.setenv('THESIS_SENTIMENT_TASKS','true')
    start=datetime.now(timezone.utc)-timedelta(seconds=1)
    if actual:activate(monkeypatch,start)
    else:
        monkeypatch.setenv('THESIS_ALERT_ROUTING_PREVIEW','true')
        monkeypatch.setenv('THESIS_ALERT_ROUTING_STARTED_AT',start.isoformat())
    commit(iid,[news(id=901,url='https://example.test/new-deal',headline='Microsoft announces a new agreement',
        summary='Microsoft announced a supply agreement for its new products.')])
    base=provider([])
    def output(body):
        answer=base(body);value=json.loads(answer['output'][0]['content'][0]['text'])
        for item in value.get('items',[]):
            if 'importance' in item:item['importance']['level']=level
            if adverse:
                if 'reporting' in item:item['reporting']['impact']='adverse'
                else:item.update(sentiment='negative',basis='stated_outcome')
        answer['output'][0]['content'][0]['text']=json.dumps(value)
        return answer
    reading=S.generate(iid,transport=output)
    assert W.publish(owner,iid,reading['id'])==(2 if adverse and level!='low' else 1)
    with transaction(owner) as c:return one(c,"SELECT * FROM research_alerts WHERE kind=%s",
        ('new_reporting' if level=='low' else 'important_reporting',))


@pytest.mark.parametrize('value',[None,'not-a-date','2027-01-01T00:00:00Z'])
def test_missing_invalid_or_future_live_start_is_fail_closed(owner,monkeypatch,value):
    monkeypatch.setenv('THESIS_ALERT_ROUTING_LIVE','true')
    if value:monkeypatch.setenv('THESIS_ALERT_ROUTING_LIVE_STARTED_AT',value)
    now=datetime(2026,10,17,tzinfo=timezone.utc)
    assert not R.live_active(now) and R.run_once(owner,now=now)==0
    monkeypatch.setenv('THESIS_DAILY_REPORTS','true')
    monkeypatch.setenv('THESIS_DAILY_REPORTS_STARTED_AT','2026-10-01T00:00:00Z')
    assert D.run_once(owner,now=now)==0
    with transaction(owner) as c:assert not rows(c,'SELECT * FROM alert_routing_decisions')


def test_high_neutral_news_gets_actual_publication_route_and_one_mocked_delivery(owner,monkeypatch,bot):
    link(owner,bot);T.configure(owner,True)
    alert=company(owner,monkeypatch)
    assert not alert['preview']
    assert not T.run_once(owner)  # No route yet, so never assume high.
    assert R.run_once(owner)==1 and R.run_once(owner)==0
    assert T.run_once(owner) and len(bot.sent)==1 and not T.run_once(owner)
    with transaction(owner) as c:
        route=one(c,'SELECT * FROM alert_routing_decisions')
        assert not route['preview'] and route['policy']==R.LIVE_POLICY and route['channel']=='telegram'
    assert all_deliveries(owner)[0]['status']=='sent'
    assert 'Source excerpt' in bot.sent[0]['text']


def test_medium_news_only_enters_actual_daily_recap_and_preview_calendar_cannot_skip_it(owner,monkeypatch,bot):
    link(owner,bot);T.configure(owner,True)
    # A pre-existing preview window must not move the actual schedule forward.
    now=datetime.now(timezone.utc);start=now-timedelta(seconds=2)
    with transaction(owner) as c:
        c.execute('INSERT INTO daily_digests VALUES(%s,%s,%s,%s,%s,%s,true)',
            (uuid4(),owner,start-timedelta(days=1),start,start,D.POLICY))
    alert=company(owner,monkeypatch,'medium')
    assert R.run_once(owner)==1 and not T.run_once(owner) and not bot.sent
    monkeypatch.setenv('THESIS_DAILY_REPORTS','true')
    monkeypatch.setenv('THESIS_DAILY_REPORTS_STARTED_AT',start.isoformat())
    now=datetime.now(timezone.utc)
    end=D.occurrence(now.astimezone(D.SGT).date()+timedelta(days=1),420,D.SGT)
    assert D.run_once(owner,now=end)==1
    with transaction(owner) as c:
        digest=one(c,'SELECT * FROM daily_digests WHERE NOT preview')
        assert digest['policy']==D.LIVE_POLICY and digest['window_start']>=R.live_start()
        assert one(c,'SELECT event_id FROM daily_digest_members')['event_id']==alert['id']
        assert one(c,'SELECT count(*) n FROM daily_digests')['n']==2
    monkeypatch.setenv('THESIS_DIGEST_TELEGRAM_ENABLED','true')
    monkeypatch.setenv('THESIS_DAILY_TELEGRAM_STARTED_AT',start.isoformat())
    monkeypatch.setattr(T,'clock',lambda:end)
    monkeypatch.setattr(D,'clock',lambda:end)
    assert T.run_once(owner) and len(bot.sent)==1
    assert 'Daily recap' in bot.sent[0]['text'] and 'Source excerpt' in bot.sent[0]['text']
    assert all_deliveries(owner)[0]['kind']=='digest'


def test_low_scored_adverse_reporting_stays_in_app_without_a_digest_or_message(owner,monkeypatch,bot):
    link(owner,bot);T.configure(owner,True)
    company(owner,monkeypatch,'low',adverse=True)
    assert R.run_once(owner)==1 and not T.run_once(owner) and not bot.sent
    with transaction(owner) as c:
        r=one(c,'SELECT * FROM alert_routing_decisions')
        assert r['channel']=='app' and r['severity']=='low' and not r['preview']


def test_actual_old_and_new_publications_of_one_adverse_story_send_once(owner,monkeypatch,bot):
    link(owner,bot);T.configure(owner,True)
    company(owner,monkeypatch,adverse=True)
    assert R.run_once(owner)==2
    with transaction(owner) as c:
        r=rows(c,'SELECT * FROM alert_routing_decisions')
        assert sorted(d['channel'] for d in r)==['app','telegram']
        assert next(d for d in r if d['channel']=='app')['manifest']['covered_by']
    assert T.run_once(owner) and not T.run_once(owner) and len(bot.sent)==1


def test_shadow_publications_and_routes_stay_unchanged_after_live_activation(owner,monkeypatch,bot):
    link(owner,bot);T.configure(owner,True)
    alert=company(owner,monkeypatch,actual=False);R.run_once(owner)
    with transaction(owner) as c:before=one(c,'SELECT * FROM alert_routing_decisions')
    activate(monkeypatch,alert['created_at']-timedelta(seconds=1))
    assert R.run_once(owner)==0 and not T.run_once(owner)
    with transaction(owner) as c:
        assert one(c,'SELECT * FROM alert_routing_decisions')==before
        assert one(c,'SELECT preview FROM research_alerts')['preview']
    with pytest.raises(psycopg.errors.RaiseException):
        with transaction(owner) as c:
            R.save(c,owner,review_digest.prepare(owner)['records'][0],now=datetime.now(timezone.utc),preview=False)


def test_live_start_does_not_backfill_even_recent_ordinary_publications(owner,monkeypatch,bot):
    link(owner,bot);T.configure(owner,True)
    company(owner,monkeypatch)
    activate(monkeypatch,datetime.now(timezone.utc))
    assert R.run_once(owner)==0 and not T.run_once(owner) and not bot.sent


def test_queued_high_is_checked_again_if_start_changes_before_dispatch(owner,monkeypatch,bot):
    link(owner,bot);T.configure(owner,True)
    alert=company(owner,monkeypatch);R.run_once(owner)
    with transaction(owner) as c:
        c.execute("INSERT INTO telegram_deliveries(id,owner_id,kind,event_id,event_at) VALUES(%s,%s,'company',%s,%s)",
            (uuid4(),owner,alert['id'],alert['created_at']))
    activate(monkeypatch,datetime.now(timezone.utc))
    assert T.run_once(owner) and not bot.sent
    assert all_deliveries(owner)[0]['status']=='skipped'


def test_new_importance_delivery_cannot_escape_through_legacy_path_on_rollback(owner,monkeypatch,bot):
    link(owner,bot);T.configure(owner,True)
    alert=company(owner,monkeypatch);R.run_once(owner)
    with transaction(owner) as c:
        c.execute("INSERT INTO telegram_deliveries(id,owner_id,kind,event_id,event_at) VALUES(%s,%s,'company',%s,%s)",
            (uuid4(),owner,alert['id'],alert['created_at']))
    monkeypatch.setenv('THESIS_ALERT_ROUTING_LIVE','false')
    assert T.run_once(owner) and not bot.sent
    assert 'importance delivery is off' in all_deliveries(owner)[0]['error']


def test_new_moves_are_actual_only_after_activation_and_delivery_switch_is_still_required(owner,monkeypatch,bot):
    event,_=move_setup(owner);activate(monkeypatch,NOW-timedelta(seconds=1))
    eid=A.record(owner,event,now=NOW)
    assert R.run_once(owner,now=NOW)==1
    monkeypatch.setattr(T,'clock',lambda:NOW+timedelta(seconds=1))
    link(owner,bot);T.configure(owner,True)
    with transaction(owner) as c:
        c.execute('UPDATE telegram_settings SET enabled_at=%s WHERE owner_id=%s',(NOW-timedelta(seconds=1),owner))
        assert not one(c,'SELECT preview FROM move_events')['preview']
    assert not T.run_once(owner) and not bot.sent
    monkeypatch.setenv('THESIS_MOVE_TELEGRAM_ENABLED','true')
    assert T.run_once(owner) and len(bot.sent)==1


def test_cost_notice_activation_keeps_preview_immutable_and_requires_explicit_level(owner,monkeypatch):
    monkeypatch.setattr(D,'OWNER',owner)
    start=datetime(2026,10,17,1,tzinfo=timezone.utc)
    now=start+timedelta(minutes=1)
    monkeypatch.setenv('THESIS_DAILY_REPORTS','true')
    monkeypatch.setenv('THESIS_DAILY_REPORTS_STARTED_AT',start.isoformat())
    monkeypatch.setenv('THESIS_DAILY_COST_ALERT_USD','5')
    model_call(created=start,charged=6_000_000_000,finished=start)
    D.run_once(owner,now=now)
    with transaction(owner) as c:preview=one(c,'SELECT * FROM daily_cost_notices')
    activate(monkeypatch,now)
    D.run_once(owner,now=now)
    with transaction(owner) as c:
        notices=rows(c,'SELECT * FROM daily_cost_notices ORDER BY preview')
        assert len(notices)==2 and not notices[0]['preview'] and notices[1]==preview
        assert notices[0]['policy']==D.LIVE_POLICY
