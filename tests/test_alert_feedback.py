"""Private alert ratings and Telegram callbacks; all transports are mocked."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from uuid import uuid4
import psycopg
import pytest
from fastapi.testclient import TestClient
from thesis.db import transaction,one,rows
from thesis import service,review_digest
from thesis.monitoring import alert_feedback as F,telegram as T,telegram_updates as U,telegram_transport as HTTP
from thesis.providers import ledger
from test_move_alerts import stored
from test_model_budget import clean_model_ledger  # noqa: F401
from test_telegram import bot,link  # noqa: F401
from test_telegram import KEY,Response


@pytest.fixture(autouse=True)
def fresh_feedback(db,monkeypatch):
    monkeypatch.setenv('THESIS_ALERT_FEEDBACK','true')
    with transaction(admin=True) as c:c.execute('TRUNCATE alert_feedback,telegram_poll_state')


@pytest.fixture
def rating_bot(bot,monkeypatch):
    def transport(key,method,body):
        if method in ('answerCallbackQuery','editMessageReplyMarkup'):bot.calls.append((method,body));return True
        return bot(key,method,body)
    monkeypatch.setattr(HTTP,'call',transport)
    return bot


def sent_alert(owner,bot):
    from test_idea_alerts import setup,provider
    from thesis.research import idea_alerts
    iid,_,reading=setup(owner)
    link(owner,bot);T.configure(owner,True)
    idea_alerts.generate(owner,iid,reading['id'],transport=provider('risk'))
    assert T.run_once(owner)
    with transaction(owner,consistent=True) as c:return one(c,"SELECT * FROM telegram_deliveries WHERE status='sent'")


def callback(delivery,*,update_id=9,value='u'):
    return dict(update_id=update_id,callback_query=dict(id='authored-callback-'+str(update_id),
        data='f:'+delivery['id'].hex+':'+value,
        message=dict(message_id=delivery['message_id'],chat=dict(id=987654,type='private')),
        **{'from':dict(id=987654,is_bot=False)}))


def test_ratings_append_without_changing_research_and_same_app_vote_is_idempotent(owner):
    eid,_,_=stored(owner)
    before=ledger.snapshot()
    assert F.rate(owner,'move',eid,'useful')['value']=='useful'
    F.rate(owner,'move',eid,'useful')
    assert F.rate(owner,'move',eid,'not_useful')['value']=='not_useful'
    with transaction(owner,consistent=True) as c:
        assert len(rows(c,'SELECT * FROM alert_feedback'))==2
        assert len(rows(c,'SELECT * FROM move_events'))==1
        record=review_digest.prepare(owner,days=0)['records'][0]
        assert record['feedback_enabled'] and record['feedback']['value']=='not_useful'
    assert ledger.snapshot()==before
    with pytest.raises(psycopg.errors.RaiseException):
        with transaction(admin=True) as c:c.execute("UPDATE alert_feedback SET value='useful'")


def test_owner_membership_and_forced_rls_cannot_rate_a_foreign_or_missing_alert(owner):
    eid,_,_=stored(owner);other=uuid4()
    with transaction(admin=True) as c:c.execute("INSERT INTO accounts VALUES(%s,'Authored second account')",(other,))
    F.rate(owner,'move',eid,'useful')
    with transaction(other,consistent=True) as c:assert not rows(c,'SELECT * FROM alert_feedback')
    with pytest.raises(service.Missing):F.rate(other,'move',eid,'useful')
    with pytest.raises(service.Missing):F.rate(owner,'idea',eid,'useful')
    with pytest.raises(psycopg.errors.RaiseException):
        with transaction(other) as c:
            c.execute("INSERT INTO alert_feedback VALUES(%s,%s,'move',%s,'useful','app',now(),NULL)",(uuid4(),other,eid))


def test_disabled_feedback_does_not_write_fetch_or_add_buttons(owner,bot,monkeypatch):
    eid,_,_=stored(owner);monkeypatch.setenv('THESIS_ALERT_FEEDBACK','false')
    with pytest.raises(ValueError,match='not enabled'):F.rate(owner,'move',eid,'useful')
    assert F.keyboard(dict(kind='move',id=uuid4())) is None
    assert not U.poll_feedback() and not bot.calls


def test_rating_endpoint_has_auth_csrf_and_payload_guards(owner,monkeypatch):
    import thesis.app as module
    monkeypatch.setattr(module,'OWNER',owner)
    eid,_,_=stored(owner);client=TestClient(module.app,base_url='http://127.0.0.1')
    url='/api/v1/alerts/move/'+eid+'/rating'
    assert client.post(url,json=dict(value='useful')).status_code==401
    client.get('/api/v1/session')
    assert client.post(url,json=dict(value='useful')).status_code==403
    headers={'X-Thesis-Request':'local-ui'}
    assert client.post(url,json=dict(value='useful'),headers=headers).json()['result']['value']=='useful'
    assert client.post(url,json=dict(value='invented'),headers=headers).status_code==422
    assert client.post(url,json=dict(value='useful',owner_id='untrusted'),headers=headers).status_code==422


def test_sent_alert_has_bounded_buttons_and_callback_saves_once(owner,rating_bot):
    delivery=sent_alert(owner,rating_bot)
    markup=rating_bot.sent[-1]['reply_markup']
    assert [b['text'] for b in markup['inline_keyboard'][0]]==['Useful','Not useful']
    assert all(len(b['callback_data'].encode())<=64 for b in markup['inline_keyboard'][0])
    rating_bot.updates=[callback(delivery)]
    assert U.receive(force=True)
    with transaction(owner,consistent=True) as c:
        assert F.latest(c,owner,'idea',delivery['event_id'])['value']=='useful'
        assert len(rows(c,'SELECT * FROM alert_feedback'))==1
    U.receive(force=True)
    assert any(method=='answerCallbackQuery' for method,_ in rating_bot.calls)
    with transaction(owner,consistent=True) as c:assert len(rows(c,'SELECT * FROM alert_feedback'))==1


@pytest.mark.parametrize('change',[
    lambda c:c['callback_query']['from'].update(id=99),
    lambda c:c['callback_query']['from'].update(is_bot=True),
    lambda c:c['callback_query']['message']['chat'].update(type='group'),
    lambda c:c['callback_query']['message'].update(message_id=999),
    lambda c:c['callback_query'].update(data='f:'+uuid4().hex+':u'),
    lambda c:c['callback_query'].update(data='untrusted data'),
])
def test_callback_rejects_wrong_sender_chat_message_or_delivery(owner,rating_bot,change):
    delivery=sent_alert(owner,rating_bot);update=callback(delivery);change(update)
    rating_bot.updates=[update];U.receive(force=True)
    with transaction(owner,consistent=True) as c:assert not rows(c,'SELECT * FROM alert_feedback')


def test_replayed_callback_cannot_undo_a_later_app_vote(owner,rating_bot):
    delivery=sent_alert(owner,rating_bot);eid=delivery['event_id']
    F.rate(owner,'idea',eid,'useful')
    rating_bot.updates=[callback(delivery)];U.receive(force=True)
    F.rate(owner,'idea',eid,'not_useful')
    with transaction(admin=True) as c:c.execute('UPDATE telegram_poll_state SET update_offset=9')
    U.receive(force=True)
    with transaction(owner,consistent=True) as c:
        assert F.latest(c,owner,'idea',eid)['value']=='not_useful'
        assert len(rows(c,'SELECT * FROM alert_feedback'))==3


def test_week_idle_random_update_id_is_read_without_losing_rating(owner,rating_bot):
    delivery=sent_alert(owner,rating_bot)
    with transaction(admin=True) as c:
        c.execute("UPDATE telegram_poll_state SET update_offset=1000,last_update_at=now()-interval '8 days'")
    rating_bot.updates=[callback(delivery)];U.receive(force=True)
    assert next(body['offset'] for method,body in reversed(rating_bot.calls) if method=='getUpdates')==0
    with transaction(owner,consistent=True) as c:assert F.latest(c,owner,'idea',delivery['event_id'])


def test_transport_accepts_callback_ack_without_exposing_provider_text(monkeypatch):
    observed=[]
    class Opener:
        def open(self,request,timeout):
            observed.append(request)
            return Response(dict(ok=True,result=True))
    monkeypatch.setattr(HTTP,'build_opener',lambda *args:Opener())
    assert HTTP.call(KEY,'answerCallbackQuery',dict(callback_query_id='authored',text='Rating saved.',cache_time=0)) is True
    assert len(observed)==1


@pytest.mark.parametrize('status',['failed','uncertain','cancelled','queued','skipped'])
def test_unsent_or_uncertain_delivery_cannot_receive_a_rating(owner,rating_bot,status):
    delivery=sent_alert(owner,rating_bot)
    with transaction(admin=True) as c:
        c.execute('UPDATE telegram_deliveries SET status=%s,message_id=NULL,sent_at=NULL WHERE id=%s',(status,delivery['id']))
    rating_bot.updates=[callback(delivery)];U.receive(force=True)
    with transaction(owner,consistent=True) as c:assert not rows(c,'SELECT * FROM alert_feedback')


def test_pending_send_defers_the_cursor_until_acknowledgement(owner,rating_bot):
    delivery=sent_alert(owner,rating_bot)
    with transaction(admin=True) as c:
        c.execute("UPDATE telegram_deliveries SET status='sending',message_id=NULL,sent_at=NULL WHERE id=%s",(delivery['id'],))
    rating_bot.updates=[callback(delivery)]
    U.receive(force=True)
    with transaction(admin=True) as c:
        assert one(c,'SELECT update_offset FROM telegram_poll_state')['update_offset']==9
        assert not rows(c,'SELECT * FROM alert_feedback')
        c.execute("UPDATE telegram_deliveries SET status='sent',message_id=%s,sent_at=now() WHERE id=%s",(delivery['message_id'],delivery['id']))
    U.receive(force=True)
    with transaction(owner,consistent=True) as c:assert F.latest(c,owner,'idea',delivery['event_id'])


def test_connection_and_rating_share_cursor_without_losing_other_account_updates(owner,rating_bot):
    from urllib.parse import urlsplit,parse_qs
    delivery=sent_alert(owner,rating_bot);other=uuid4()
    with transaction(admin=True) as c:c.execute("INSERT INTO accounts VALUES(%s,'Authored other account')",(other,))
    nonce=parse_qs(urlsplit(T.connect(other)['url']).query)['start'][0]
    rating_bot.updates=[callback(delivery,update_id=10),dict(update_id=11,message=dict(
        text='/start '+nonce,chat=dict(id=543210,type='private'),**{'from':dict(id=543210,is_bot=False)}))]
    assert T.check_connection(other)['linked']
    with transaction(owner,consistent=True) as c:assert F.latest(c,owner,'idea',delivery['event_id'])
    with transaction(other,consistent=True) as c:assert not rows(c,'SELECT * FROM alert_feedback')
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with transaction(other) as c:c.execute('SELECT * FROM telegram_poll_state')


def test_pollers_share_one_lock_and_never_overwrite_concurrent_rating(owner,rating_bot,monkeypatch):
    delivery=sent_alert(owner,rating_bot);rating_bot.updates=[callback(delivery)]
    entered,release=Event(),Event();original=HTTP.call
    def slow(key,method,body):
        if method=='getUpdates':entered.set();assert release.wait(10)
        return original(key,method,body)
    monkeypatch.setattr(HTTP,'call',slow)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first=pool.submit(U.receive,force=True)
        assert entered.wait(10)
        assert pool.submit(U.receive,force=True).result(timeout=3) is False
        release.set();assert first.result(timeout=10)
    with transaction(owner,consistent=True) as c:assert len(rows(c,'SELECT * FROM alert_feedback'))==1


def test_token_change_and_forwarded_callback_do_not_record_votes(owner,rating_bot,monkeypatch):
    delivery=sent_alert(owner,rating_bot)
    update=callback(delivery);update['callback_query']['message']['forward_origin']=dict(type='user')
    rating_bot.updates=[update];U.receive(force=True)
    monkeypatch.setattr(HTTP,'token',lambda:'different-token')
    assert not U.receive(force=True)
    with transaction(owner,consistent=True) as c:assert not rows(c,'SELECT * FROM alert_feedback')


def test_all_published_alert_kinds_accept_explicit_ratings(owner):
    from test_idea_alerts import setup,provider
    from test_integration import payload,drain
    from test_market import commit,news
    from test_sentiment import provider as sentiment_provider
    from thesis.research import sentiment,idea_alerts
    from thesis.monitoring import news_watch
    iid,_,_=setup(owner,True)
    news_watch.configure(owner,iid,True)
    commit(iid,[news(id=900,url='https://example.test/cost-warning',headline='Microsoft reports a cost warning',
        summary='Microsoft reports cost pressure, with demand still uncertain.')])
    reading=sentiment.generate(iid,transport=sentiment_provider('negative'))
    news_watch.publish(owner,iid,reading['id'])
    idea_alerts.generate(owner,iid,reading['id'],transport=provider('risk'))
    service.save_idea(owner,payload());drain(owner);service.advance(owner,0);drain(owner)
    records=review_digest.prepare(owner)['records']
    assert {r['kind'] for r in records}=={'company','idea','condition'}
    for record in records:
        assert F.rate(owner,record['kind'],record['id'],'useful')['value']=='useful'
    with transaction(owner,consistent=True) as c:
        assert len(rows(c,'SELECT * FROM alert_feedback'))==3
        assert all(r['feedback']['value']=='useful' for r in review_digest.prepare(owner)['records'])


def test_failed_callback_acknowledgement_does_not_repeat_vote(owner,rating_bot,monkeypatch):
    delivery=sent_alert(owner,rating_bot);rating_bot.updates=[callback(delivery)]
    original=HTTP.call
    def fail_ack(key,method,body):
        if method=='answerCallbackQuery':raise HTTP.TelegramError('unavailable','Authored acknowledgement failure.')
        return original(key,method,body)
    monkeypatch.setattr(HTTP,'call',fail_ack)
    U.receive(force=True);U.receive(force=True)
    with transaction(owner,consistent=True) as c:
        assert len(rows(c,'SELECT * FROM alert_feedback'))==1


def edits(bot):
    return [body for method,body in bot.calls if method=='editMessageReplyMarkup']


def test_tap_shows_the_saved_choice_and_a_later_tap_can_change_it(owner,rating_bot):
    delivery=sent_alert(owner,rating_bot)
    rating_bot.updates=[callback(delivery)];U.receive(force=True)
    shown=edits(rating_bot)[-1]
    assert shown['chat_id']==987654 and shown['message_id']==delivery['message_id']
    buttons=shown['reply_markup']['inline_keyboard'][0]
    assert [b['text'] for b in buttons]==['✓ Useful','Not useful']
    # The ticked buttons still carry the same choices, so the rating stays changeable.
    original=rating_bot.sent[-1]['reply_markup']['inline_keyboard'][0]
    assert [b['callback_data'] for b in buttons]==[b['callback_data'] for b in original]
    rating_bot.updates=[callback(delivery,update_id=10,value='n')];U.receive(force=True)
    assert [b['text'] for b in edits(rating_bot)[-1]['reply_markup']['inline_keyboard'][0]]==['Useful','✓ Not useful']
    with transaction(owner,consistent=True) as c:
        assert F.latest(c,owner,'idea',delivery['event_id'])['value']=='not_useful'


def test_failed_button_edit_keeps_the_saved_vote(owner,bot,monkeypatch):
    def transport(key,method,body):
        if method=='editMessageReplyMarkup':raise HTTP.TelegramError('authored edit failure')
        if method=='answerCallbackQuery':return True
        return bot(key,method,body)
    monkeypatch.setattr(HTTP,'call',transport)
    delivery=sent_alert(owner,bot)
    bot.updates=[callback(delivery)]
    assert U.receive(force=True)
    with transaction(owner,consistent=True) as c:
        assert F.latest(c,owner,'idea',delivery['event_id'])['value']=='useful'


def test_rejected_tap_does_not_change_the_buttons(owner,rating_bot):
    delivery=sent_alert(owner,rating_bot);update=callback(delivery)
    update['callback_query']['from'].update(id=99)
    rating_bot.updates=[update];U.receive(force=True)
    assert not edits(rating_bot)


def test_taps_are_checked_again_within_two_seconds(owner,rating_bot):
    delivery=sent_alert(owner,rating_bot)
    rating_bot.updates=[callback(delivery)];U.receive(force=True)
    with transaction(admin=True) as c:
        state=one(c,'SELECT next_poll_at,now() AS checked FROM telegram_poll_state')
    assert U.POLL_SECONDS<=2 and (state['next_poll_at']-state['checked']).total_seconds()<=2


def test_digest_buttons_tick_each_items_latest_rating():
    from thesis.monitoring import daily_telegram as D
    delivery=dict(id=uuid4())
    markup=D.keyboard(delivery,[dict(position=0),dict(position=1)],{0:'not_useful'})
    assert [[b['text'] for b in row] for row in markup['inline_keyboard']]==[
        ['1 · Useful','1 · ✓ Not useful'],['2 · Useful','2 · Not useful']]
    assert D.keyboard(delivery,[dict(position=0)])['inline_keyboard'][0][0]['text']=='1 · Useful'
