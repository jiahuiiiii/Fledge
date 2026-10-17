"""Daily outbox and callbacks use authored records and mocked Telegram only."""
from datetime import datetime,timedelta,timezone
from uuid import uuid4
import pytest
import psycopg
from psycopg.types.json import Jsonb
from thesis.db import transaction,one,rows
from thesis import service,review_digest
from thesis.monitoring import daily_telegram as DT,daily_updates as D,telegram as T,telegram_updates as U,alert_feedback as F
from thesis.monitoring import telegram_transport as HTTP
from thesis.monitoring.telegram_message import render,visible_units
from thesis.providers import ledger
from thesis.research import idea_alerts
from test_idea_alerts import setup,provider
from test_telegram import bot,link,unpace,KEY  # noqa:F401
from test_alert_feedback import rating_bot,callback  # noqa:F401
from test_model_budget import clean_model_ledger  # noqa:F401


@pytest.fixture(autouse=True)
def feedback(db,monkeypatch):
    monkeypatch.setenv('THESIS_ALERT_FEEDBACK','true')
    with transaction(admin=True) as c:c.execute('TRUNCATE telegram_poll_state')


def enable(monkeypatch,now,kind='digest'):
    monkeypatch.setenv('THESIS_DAILY_REPORTS','true')
    monkeypatch.setenv('THESIS_DAILY_REPORTS_STARTED_AT',(now-timedelta(days=2)).isoformat())
    monkeypatch.setenv('THESIS_DAILY_TELEGRAM_STARTED_AT',(now-timedelta(minutes=1)).isoformat())
    monkeypatch.setenv('THESIS_'+('DIGEST' if kind=='digest' else 'COST')+'_TELEGRAM_ENABLED','true')
    monkeypatch.setenv('THESIS_DAILY_COST_ALERT_USD','5')
    monkeypatch.setattr(T,'clock',lambda:now+timedelta(seconds=2))


def digest(owner,rating_bot,monkeypatch,*,count=1,preview=False):
    iid,_,reading=setup(owner)
    checked=idea_alerts.generate(owner,iid,reading['id'],transport=provider('risk'))
    original=checked['id'];ids=[original]
    # Authored copies force a multi-item recap while retaining the same current
    # private revision and permitted evidence. They are not additional AI calls.
    with transaction(owner) as c:
        for _ in range(count-1):
            identity=uuid4();ids.append(str(identity))
            c.execute('INSERT INTO idea_alert_checks SELECT %s,owner_id,instrument_id,version_id,analysis_id,call_id,%s,packet,result,created_at '
                'FROM idea_alert_checks WHERE id=%s',(identity,'authored-daily:'+str(identity),original))
            c.execute("INSERT INTO idea_alert_publications VALUES(%s,%s,'manual',clock_timestamp())",(owner,identity))
    now=datetime.now(timezone.utc);enable(monkeypatch,now)
    link(owner,rating_bot);T.configure(owner,True)
    identity=uuid4()
    with transaction(owner) as c:
        c.execute('UPDATE telegram_settings SET enabled_at=%s WHERE owner_id=%s',(now+timedelta(microseconds=1),owner))
        c.execute('INSERT INTO daily_digests VALUES(%s,%s,%s,%s,%s,%s,%s)',
            (identity,owner,now-timedelta(minutes=1),now+timedelta(seconds=1),now+timedelta(seconds=1),'authored-daily',preview))
        for position,event in enumerate(ids):
            route=uuid4()
            c.execute("INSERT INTO alert_routing_decisions VALUES(%s,%s,'idea',%s,'authored-route','medium','digest',%s,'Authored medium route',%s,%s)",
                (route,owner,event,preview,Jsonb({}),now))
            c.execute("INSERT INTO daily_digest_members VALUES(%s,%s,%s,%s,'idea',%s)",(owner,identity,position,route,event))
    return str(identity),ids,now


def cost(owner,rating_bot,monkeypatch,*,preview=False):
    now=datetime.now(timezone.utc);enable(monkeypatch,now,'cost');monkeypatch.setattr(D,'OWNER',owner)
    link(owner,rating_bot);T.configure(owner,True);identity=uuid4()
    with transaction(owner) as c:
        c.execute('INSERT INTO daily_cost_notices VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)',
            (identity,owner,now.astimezone(D.SGT).date(),5_000_000_000,5_000_000_001,700_000_000,now+timedelta(seconds=1),'authored-cost',preview))
    return str(identity),now


def delivery(owner,kind='digest'):
    with transaction(owner,consistent=True) as c:return one(c,'SELECT * FROM telegram_deliveries WHERE kind=%s',(kind,))


def digest_callback(job,position=0,*,update_id=10,value='u'):
    result=callback(job,update_id=update_id,value=value)
    result['callback_query']['data']=f"d:{job['id'].hex}:{position}:{value}"
    return result


def test_defaults_and_missing_explicit_start_do_not_queue_or_send(owner,rating_bot,monkeypatch):
    identity,_,now=digest(owner,rating_bot,monkeypatch)
    monkeypatch.delenv('THESIS_DIGEST_TELEGRAM_ENABLED')
    assert not DT.enabled('digest') and not T.run_once(owner) and not rating_bot.sent
    monkeypatch.setenv('THESIS_DIGEST_TELEGRAM_ENABLED','true')
    monkeypatch.delenv('THESIS_DAILY_TELEGRAM_STARTED_AT')
    assert not T.run_once(owner) and delivery(owner) is None
    monkeypatch.setenv('THESIS_DAILY_TELEGRAM_STARTED_AT',(now+timedelta(days=1)).isoformat())
    assert not T.run_once(owner) and not rating_bot.sent
    monkeypatch.setenv('THESIS_DAILY_TELEGRAM_STARTED_AT','invalid')
    assert not T.run_once(owner) and not rating_bot.sent


@pytest.mark.parametrize('kind',['digest','cost'])
def test_preview_cannot_queue_or_render_even_when_new_delivery_flags_are_on(owner,rating_bot,monkeypatch,kind):
    if kind=='digest':identity,_,_=digest(owner,rating_bot,monkeypatch,preview=True)
    else:identity,_=cost(owner,rating_bot,monkeypatch,preview=True)
    with transaction(owner) as c:
        assert T.event(c,owner,kind,identity) is None
        row=one(c,'SELECT created_at FROM '+('daily_digests' if kind=='digest' else 'daily_cost_notices')+' WHERE id=%s',(identity,))
    assert not T.run_once(owner) and not rating_bot.sent
    with pytest.raises(psycopg.errors.RaiseException):
        with transaction(owner) as c:
            c.execute('INSERT INTO telegram_deliveries(id,owner_id,kind,event_id,event_at) VALUES(%s,%s,%s,%s,%s)',
                (uuid4(),owner,kind,identity,row['created_at']))
    with pytest.raises(ValueError,match='Preview'):
        render(dict(kind=kind,detail=dict(preview=True,message='must never forward')))


def test_real_recap_sends_once_with_pinned_numbered_ratings_before_http_and_no_ai_or_reviews(owner,rating_bot,monkeypatch):
    identity,ids,now=digest(owner,rating_bot,monkeypatch,count=2);before=ledger.snapshot();original=HTTP.call
    def checked(key,method,body):
        if method=='sendMessage':
            with transaction(owner,consistent=True) as c:
                job=one(c,"SELECT * FROM telegram_deliveries WHERE kind='digest'")
                assert job['status']=='sending' and job['attempts']==1
                assert len(rows(c,'SELECT * FROM telegram_digest_items'))==2
        return original(key,method,body)
    monkeypatch.setattr(HTTP,'call',checked)
    monkeypatch.setattr(ledger,'execute',lambda *_a,**_k:pytest.fail('Delivery called AI'))
    assert T.run_once(owner) and not T.run_once(owner)
    text=rating_bot.sent[0]['text'];markup=rating_bot.sent[0]['reply_markup']
    assert '<b>Fledge · Daily recap</b>' in text and 'Your question:' in text
    assert 'Source excerpt:' in text and text.count('<a href=')<=2 and visible_units(text)<=3800
    assert text.index('<a href=')<text.index('<b>2.')
    assert len(markup['inline_keyboard'])==2 and markup['inline_keyboard'][1][0]['text']=='2 · Useful'
    assert all(len(b['callback_data'].encode())<=64 for r in markup['inline_keyboard'] for b in r)
    with transaction(owner) as c:
        assert not rows(c,'SELECT * FROM idea_alert_reviews')
        assert len(rows(c,'SELECT * FROM daily_digest_members'))==2
    assert ledger.snapshot()==before and len(rating_bot.sent)==1 and delivery(owner)['status']=='sent'


def test_digest_rating_targets_exact_original_alert_and_replay_cannot_undo_later_app_vote(owner,rating_bot,monkeypatch):
    _,ids,_=digest(owner,rating_bot,monkeypatch,count=2);T.run_once(owner);job=delivery(owner)
    rating_bot.updates=[digest_callback(job,1)];U.receive(force=True)
    with transaction(owner) as c:
        assert F.latest(c,owner,'idea',ids[0]) is None
        assert F.latest(c,owner,'idea',ids[1])['value']=='useful'
    F.rate(owner,'idea',ids[1],'not_useful')
    with transaction(admin=True) as c:c.execute('UPDATE telegram_poll_state SET update_offset=10')
    U.receive(force=True)
    with transaction(owner) as c:
        assert F.latest(c,owner,'idea',ids[1])['value']=='not_useful'
        assert len(rows(c,'SELECT * FROM alert_feedback'))==2


@pytest.mark.parametrize('change',[
    lambda u:u['callback_query']['from'].update(id=42),
    lambda u:u['callback_query']['message']['chat'].update(type='group'),
    lambda u:u['callback_query']['message'].update(message_id=999),
    lambda u:u['callback_query']['message'].update(forward_origin=dict(type='user')),
    lambda u:u['callback_query'].update(data='d:'+uuid4().hex+':0:u'),
    lambda u:u['callback_query'].update(data=u['callback_query']['data'].replace(':0:',':4:')),
    lambda u:u['callback_query'].update(data='f:'+u['callback_query']['data'].split(':')[1]+':u'),
])
def test_digest_callback_rejects_wrong_sender_message_or_unshown_button(owner,rating_bot,monkeypatch,change):
    digest(owner,rating_bot,monkeypatch);T.run_once(owner);update=digest_callback(delivery(owner));change(update)
    rating_bot.updates=[update];U.receive(force=True)
    with transaction(owner) as c:assert not rows(c,'SELECT * FROM alert_feedback')


def test_rate_limited_retry_rechecks_members_and_callback_uses_confirmed_attempt(owner,rating_bot,monkeypatch):
    _,ids,now=digest(owner,rating_bot,monkeypatch,count=2)
    rating_bot.failure=HTTP.TelegramError('rate_limited','Authored known rejection.',60)
    assert T.run_once(owner) and delivery(owner)['status']=='queued'
    original=T.event
    def changed(c,o,k,i,**kwargs):
        if k=='idea' and str(i)==str(ids[0]):return None
        return original(c,o,k,i,**kwargs)
    monkeypatch.setattr(T,'event',changed);monkeypatch.setattr(T,'clock',lambda:now+timedelta(seconds=63))
    rating_bot.failure=None;assert T.run_once(owner)
    job=delivery(owner);assert job['attempts']==2
    with transaction(owner) as c:
        assert one(c,'SELECT member_position FROM telegram_digest_items WHERE attempt=2 AND position=0')['member_position']==1
        assert len(rows(c,'SELECT * FROM telegram_digest_items WHERE attempt=1'))==2
    rating_bot.updates=[digest_callback(job)];U.receive(force=True)
    with transaction(owner) as c:
        assert F.latest(c,owner,'idea',ids[0]) is None and F.latest(c,owner,'idea',ids[1])['value']=='useful'


def test_uncertain_send_never_retries_and_its_buttons_cannot_receive_votes(owner,rating_bot,monkeypatch):
    digest(owner,rating_bot,monkeypatch);rating_bot.failure=TimeoutError('Private diagnostic')
    assert T.run_once(owner);job=delivery(owner);assert job['status']=='uncertain'
    rating_bot.failure=None;unpace(owner);assert not T.run_once(owner) and len(rating_bot.sent)==1
    assert 'Private diagnostic' not in job['error']
    rating_bot.updates=[digest_callback(job)];U.receive(force=True)
    with transaction(owner) as c:assert not rows(c,'SELECT * FROM alert_feedback')


@pytest.mark.parametrize('withdrawal',[True,False])
def test_withdrawal_or_changed_idea_prevents_forwarding_without_rewriting_recap(owner,rating_bot,monkeypatch,withdrawal):
    identity,_,_=digest(owner,rating_bot,monkeypatch)
    if withdrawal:
        with transaction(admin=True) as c:c.execute("UPDATE sources SET entitlement='local-stockanalysis-targets' WHERE id='finnhub-news'")
    else:
        from thesis.models import SaveIdea
        with transaction(owner) as c:iid=one(c,'SELECT instrument_id FROM theses')['instrument_id']
        service.save_idea(owner,SaveIdea(instrument_id=str(iid),expected_revision=1,
            question='An authored changed question?',reasoning='Authored changed reasoning.',status='draft',conditions=[]))
    assert T.run_once(owner) and not rating_bot.sent and delivery(owner)['status']=='skipped'
    with transaction(owner) as c:assert one(c,'SELECT count(*) n FROM daily_digest_members WHERE digest_id=%s',(identity,))['n']==1


def test_recap_keeps_five_complete_items_and_reports_remaining_without_rating_hidden_members(owner,rating_bot,monkeypatch):
    digest(owner,rating_bot,monkeypatch,count=7);assert T.run_once(owner)
    sent=rating_bot.sent[0];assert len(sent['reply_markup']['inline_keyboard'])==5
    assert '2 more saved updates' in sent['text'] and visible_units(sent['text'])<=3800
    with transaction(owner) as c:
        assert len(rows(c,'SELECT * FROM telegram_digest_items'))==5
        assert len(rows(c,'SELECT * FROM daily_digest_members'))==7
    with pytest.raises(psycopg.errors.RaiseException):
        with transaction(admin=True) as c:c.execute('UPDATE telegram_digest_items SET member_position=0')


def test_cost_notice_is_owner_only_exact_and_cannot_send_until_separate_switch(owner,rating_bot,monkeypatch):
    identity,_=cost(owner,rating_bot,monkeypatch);monkeypatch.setenv('THESIS_COST_TELEGRAM_ENABLED','false')
    assert not T.run_once(owner)
    monkeypatch.setenv('THESIS_COST_TELEGRAM_ENABLED','true')
    before=ledger.snapshot();assert T.run_once(owner)
    message=rating_bot.sent[-1]
    assert 'US$5.000000001' in message['text'] and 'Unresolved maximum' in message['text']
    assert 'including tests' in message['text'] and 'does not pause spending' in message['text']
    assert 'reply_markup' not in message and delivery(owner,'cost')['status']=='sent'
    assert ledger.snapshot()==before
    assert T.status(owner)['cost_notices_enabled']
    monkeypatch.setattr(D,'OWNER',str(uuid4()))
    with transaction(owner) as c:assert T.event(c,owner,'cost',identity) is None
    assert not T.status(owner)['cost_notices_enabled']


def test_cost_level_change_or_pause_after_queue_prevents_dispatch(owner,rating_bot,monkeypatch):
    identity,now=cost(owner,rating_bot,monkeypatch)
    with transaction(owner) as c:
        cfg=T.config(c,owner);assert DT.enqueue(c,owner,cfg,now+timedelta(seconds=2))==1
    monkeypatch.setenv('THESIS_DAILY_COST_ALERT_USD','6')
    assert T.run_once(owner) and not rating_bot.sent and delivery(owner,'cost')['status']=='skipped'


def test_foreign_digest_and_wrong_button_attempt_are_rejected(owner,rating_bot,monkeypatch):
    identity,_,_=digest(owner,rating_bot,monkeypatch)
    other=uuid4()
    with transaction(admin=True) as c:c.execute("INSERT INTO accounts VALUES(%s,'Authored other account')",(other,))
    with transaction(other) as c:
        assert not rows(c,'SELECT * FROM daily_digests') and T.event(c,other,'digest',identity) is None
    with pytest.raises(psycopg.errors.RaiseException):
        with transaction(other) as c:
            c.execute("INSERT INTO telegram_deliveries(id,owner_id,kind,event_id,event_at) SELECT %s,%s,'digest',id,created_at FROM daily_digests WHERE id=%s",(uuid4(),other,identity))
            # Forced RLS returns no rows, so use its actual timestamp explicitly.
            c.execute("INSERT INTO telegram_deliveries(id,owner_id,kind,event_id,event_at) VALUES(%s,%s,'digest',%s,now())",(uuid4(),other,identity))
    T.run_once(owner);job=delivery(owner)
    with transaction(other) as c:assert not rows(c,'SELECT * FROM telegram_digest_items')
    with pytest.raises(psycopg.errors.RaiseException):
        with transaction(other) as c:c.execute('INSERT INTO telegram_digest_items VALUES(%s,%s,1,0,0)',(other,job['id']))
    with pytest.raises(psycopg.errors.RaiseException):
        with transaction(owner) as c:c.execute('INSERT INTO telegram_digest_items VALUES(%s,%s,2,0,0)',(owner,job['id']))


def test_live_recap_membership_rejects_shadow_route_without_promoting_saved_rows(owner,rating_bot,monkeypatch):
    identity,ids,now=digest(owner,rating_bot,monkeypatch,preview=True)
    with pytest.raises(psycopg.errors.RaiseException):
        with transaction(owner) as c:
            real=uuid4();c.execute('INSERT INTO daily_digests SELECT %s,owner_id,window_start,window_end,created_at,%s,false FROM daily_digests WHERE id=%s',(real,'authored-other-policy',identity))
            c.execute('INSERT INTO daily_digest_members SELECT owner_id,%s,position,route_id,kind,event_id FROM daily_digest_members WHERE digest_id=%s',(real,identity))


def test_empty_recap_cannot_queue_and_live_route_cannot_promote_a_price_preview(owner,rating_bot,monkeypatch):
    from test_move_alerts import stored
    eid,_,_=stored(owner);now=datetime.now(timezone.utc);identity=uuid4()
    with transaction(owner) as c:
        c.execute('INSERT INTO daily_digests VALUES(%s,%s,%s,%s,%s,%s,false)',
            (identity,owner,now-timedelta(hours=1),now,now,'authored-empty'))
    with pytest.raises(psycopg.errors.RaiseException):
        with transaction(owner) as c:
            c.execute("INSERT INTO telegram_deliveries(id,owner_id,kind,event_id,event_at) VALUES(%s,%s,'digest',%s,%s)",(uuid4(),owner,identity,now))
    with pytest.raises(psycopg.errors.RaiseException,match='preview publication'):
        with transaction(owner) as c:
            c.execute("INSERT INTO alert_routing_decisions VALUES(%s,%s,'move',%s,'authored-live','high','telegram',false,'Authored',%s,%s)",
                (uuid4(),owner,eid,Jsonb({}),now))


def test_callback_arriving_before_send_ack_waits_for_the_confirmed_message(owner,rating_bot,monkeypatch):
    _,ids,_=digest(owner,rating_bot,monkeypatch);original=HTTP.call
    def early_callback(key,method,body):
        if method=='sendMessage':
            job=delivery(owner);job=dict(job,message_id=123)
            rating_bot.updates=[digest_callback(job)]
            U.receive(force=True)
            with transaction(owner) as c:assert not rows(c,'SELECT * FROM alert_feedback')
        return original(key,method,body)
    monkeypatch.setattr(HTTP,'call',early_callback)
    assert T.run_once(owner);U.receive(force=True)
    with transaction(owner) as c:assert F.latest(c,owner,'idea',ids[0])['value']=='useful'


def test_separate_daily_switch_is_rechecked_after_queuing(owner,rating_bot,monkeypatch):
    _,_,now=digest(owner,rating_bot,monkeypatch)
    with transaction(owner) as c:assert DT.enqueue(c,owner,T.config(c,owner),now+timedelta(seconds=2))==1
    monkeypatch.setenv('THESIS_DIGEST_TELEGRAM_ENABLED','false')
    assert T.run_once(owner) and delivery(owner)['status']=='skipped' and not rating_bot.sent


def test_interrupted_send_retains_mapping_but_is_never_retried(owner,rating_bot,monkeypatch):
    identity,_,now=digest(owner,rating_bot,monkeypatch)
    with transaction(owner) as c:
        DT.enqueue(c,owner,T.config(c,owner),now+timedelta(seconds=2))
        job=one(c,"SELECT * FROM telegram_deliveries WHERE kind='digest'")
        record=T.event(c,owner,'digest',identity)
        c.execute("UPDATE telegram_deliveries SET status='sending',attempts=1 WHERE id=%s",(job['id'],))
        DT.save_shown(c,owner,job,record)
    assert not T.run_once(owner) and not rating_bot.sent and delivery(owner)['status']=='uncertain'
    with transaction(owner) as c:assert len(rows(c,'SELECT * FROM telegram_digest_items'))==1


def test_disabled_ratings_do_not_record_buttons_that_were_never_sent(owner,rating_bot,monkeypatch):
    digest(owner,rating_bot,monkeypatch);monkeypatch.setenv('THESIS_ALERT_FEEDBACK','false')
    assert T.run_once(owner) and 'reply_markup' not in rating_bot.sent[0]
    with transaction(owner) as c:assert not rows(c,'SELECT * FROM telegram_digest_items')
    monkeypatch.setenv('THESIS_ALERT_FEEDBACK','true')
    rating_bot.updates=[digest_callback(delivery(owner))];U.receive(force=True)
    with transaction(owner) as c:assert not rows(c,'SELECT * FROM alert_feedback')


def test_new_queue_failure_is_sanitized_and_cannot_abort_existing_outbox(owner,rating_bot,monkeypatch,caplog):
    digest(owner,rating_bot,monkeypatch)
    def broken(*_a,**_k):raise ValueError('Private source text')
    monkeypatch.setattr(DT,'rows',broken)
    T.test_message(owner)
    assert T.run_once(owner) and len(rating_bot.sent)==1 and 'Connection test' in rating_bot.sent[0]['text']
    assert 'existing alert delivery continues' in caplog.text and 'Private source text' not in caplog.text


def test_summary_escapes_source_text_keeps_links_beside_it_and_bounds_whole_blocks():
    record=dict(kind='company',title='A <script> company development',detail=dict(symbol='EXMP',
        payload=dict(items=[dict(source_id='a',citations=[dict(quote='Reported <img> & company evidence.')])]),
        sources=[dict(id='a',source='Authored Wire',url='https://example.test/a?x=1&y=2')]))
    block,links=DT.summary(record,1)
    assert '<script>' not in block and '<img>' not in block and '&lt;img&gt;' in block and '&amp;' in block
    assert links==[('https://example.test/a?x=1&y=2','Authored Wire')]
    record['detail']['payload']['items'][0]['citations'][0]['quote']='😀'*1000
    assert visible_units(DT.summary(record,1)[0])<=680
