"""Price-message formatting/outbox controls; Telegram and prices are authored."""
from copy import deepcopy
from datetime import timedelta
from uuid import uuid4
import pytest
import psycopg
from thesis.db import transaction,one,rows
from thesis.monitoring import move_alerts as A, telegram as T
from thesis.monitoring.telegram_message import render,visible_units
from test_move_alerts import stored
from test_price_moves import NOW
from test_telegram import bot,link,unpace  # noqa: F401


def detail(owner,eid):
    with transaction(owner,consistent=True) as c:return A.present(c,owner,eid,now=NOW)


def test_two_session_decline_stays_visible_beside_a_positive_daily_move():
    member=dict(symbol='EXMP',change_percent='1',reasons=['two_session_move'],
                two_sessions=dict(change_percent='-5.6'))
    assert A.numbers([member])=='EXMP +1.0% today · Over 2 sessions: EXMP −5.6%'


def test_preview_cannot_be_rendered_queued_or_sent_even_with_existing_telegram_on(owner,bot,monkeypatch):
    eid,event,ids=stored(owner,grouping=True)
    link(owner,bot);T.configure(owner,True)
    monkeypatch.setattr(T,'clock',lambda:NOW+timedelta(seconds=1))
    with transaction(owner) as c:c.execute('UPDATE telegram_settings SET enabled_at=%s WHERE owner_id=%s',(NOW-timedelta(minutes=1),owner))
    monkeypatch.setenv('THESIS_MOVE_TELEGRAM_ENABLED','true')
    assert not T.run_once(owner) and not bot.sent
    with pytest.raises(ValueError,match='Preview'):render(dict(kind='move',detail=detail(owner,eid),title='Authored move',created_at=NOW))
    with pytest.raises(psycopg.errors.RaiseException):
        with transaction(owner) as c:
            c.execute("INSERT INTO telegram_deliveries(id,owner_id,kind,event_id,event_at) VALUES(%s,%s,'move',%s,%s)",(uuid4(),owner,eid,NOW))


def live_copy(owner,eid):
    """A fresh authored publication, not an update of an immutable preview."""
    copy=uuid4()
    with transaction(admin=True) as c:
        c.execute('INSERT INTO move_events SELECT %s,owner_id,instrument_id,created_at,session_date,event_type,direction,false,policy,payload,headlines FROM move_events WHERE id=%s',(copy,eid))
        c.execute('INSERT INTO move_event_members SELECT owner_id,%s,instrument_id,quote_id,qqq_id,spy_id,sector_id,history_id,triggered,payload FROM move_event_members WHERE event_id=%s',(copy,eid))
    return str(copy)


@pytest.mark.parametrize('uncertain',[False,True])
def test_new_kind_delivery_requires_separate_switch_and_respects_uncertain_send(owner,bot,monkeypatch,uncertain):
    eid,event,ids=stored(owner);eid=live_copy(owner,eid)
    link(owner,bot);T.configure(owner,True)
    monkeypatch.setattr(T,'clock',lambda:NOW+timedelta(seconds=1))
    with transaction(owner) as c:c.execute('UPDATE telegram_settings SET enabled_at=%s WHERE owner_id=%s',(NOW-timedelta(minutes=1),owner))
    assert not T.run_once(owner) and not bot.sent
    monkeypatch.setenv('THESIS_MOVE_TELEGRAM_ENABLED','true')
    if uncertain:bot.failure=TimeoutError('Authored private transport diagnostic')
    assert T.run_once(owner) and len(bot.sent)==1
    assert 'MSFT −3.2% today' in bot.sent[0]['text']
    assert bot.sent[0]['text'].startswith('<b>MSFT −3.2% today')
    assert not T.run_once(owner) and len(bot.sent)==1
    with transaction(owner,consistent=True) as c:
        saved=one(c,'SELECT * FROM telegram_deliveries')
        assert saved['status']==('uncertain' if uncertain else 'sent')
        assert saved['attempts']==1 and 'private transport diagnostic' not in (saved['error'] or '')


def test_numbers_first_all_members_context_labels_exact_links_escaping_and_limit(owner):
    eid,event,ids=stored(owner,grouping=True)
    d=detail(owner,eid);d['preview']=False
    d['explanation']=dict(cause='market',text='Reported AI rotation may explain this move <script>.')
    d['sources']=[dict(id=f'a{i}',url=f'https://example.test/{i}?x=1&y=2',title=f'Headline <{i}>') for i in range(3)]
    message=render(dict(kind='move',title=d['title'],detail=d,created_at=NOW))
    assert message.startswith('<b>AAPL −3.1%')
    for symbol in ids:assert symbol in message
    assert 'Nasdaq −2.1%' in message and 'Market context only' in message
    assert '<script>' not in message and '&lt;script&gt;' in message
    assert message.count('<a href=')==2 and '&amp;y=2' in message
    assert visible_units(message)<=3800
    d['withheld']=True
    with pytest.raises(ValueError):render(dict(kind='move',title=d['title'],detail=d,created_at=NOW))
