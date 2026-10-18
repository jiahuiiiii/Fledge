"""Shadow severity rules and publication; real disposable DB, no network."""
from copy import deepcopy
from datetime import datetime,timedelta,timezone
from uuid import uuid4
import pytest
import psycopg
from thesis import review_digest
from thesis.db import transaction,one,rows
from thesis.monitoring import alert_routing as R,news_watch as W,telegram as T
from thesis.monitoring.telegram_message import render
from thesis.providers import ledger
from thesis.research import sentiment as S,sentiment_tasks as TASK,reporting_basis
from test_model_budget import clean_model_ledger  # noqa:F401
from test_news_coverage import source,analyse,relation
from test_market import prepare,commit,news
from test_sentiment import provider as legacy
from test_sentiment_task_runner import provider
from test_telegram import bot,link  # noqa:F401
from test_move_alerts import stored


def scored(item,level='high',**extra):
    item=deepcopy(item);sid=item['source_id'];quote='A cited company development.'
    item['reporting_basis']=dict(policy=reporting_basis.POLICY,kind='reported_event',eligible=True,
        impact='not_stated',citations=[dict(source_id=sid,quote=quote,passage_id='p1')])
    item['importance']=dict(policy=TASK.POLICY,level=level,category='deal',form='event',
        low_by_rule=False,citations=[dict(source_id=sid,quote=quote,passage_id='p1')],**extra)
    return item


def record(item):return dict(kind='company',detail=dict(payload=dict(items=[item])))


@pytest.mark.parametrize('tone',['negative','neutral','positive','unclear'])
def test_importance_and_immediate_route_are_independent_of_tone(tone):
    item=scored(analyse([source('item_1','Microsoft announced a deal.')],[],tones={'item_1':tone})['result']['items'][0])
    assert R.importance(item)=='high' and R.classify(record(item))['channel']=='telegram'


@pytest.mark.parametrize('field,value',[
    ('form','opinion'),('form','comparison'),('form','price_recap'),('category','analyst_opinion'),
    ('category','market_commentary'),('policy','unknown'),('low_by_rule',True),
    ('citations',[]),('citations',[dict(source_id='foreign',quote='Not its own evidence')]),
    ('event_repair',['event_fields_inconsistent']),
])
def test_model_high_cannot_override_low_value_or_missing_own_evidence(field,value):
    item=scored(analyse([source('item_1','Microsoft announced a deal.')],[])['result']['items'][0])
    item['importance'][field]=value
    assert R.importance(item)=='low'
    # Unknown methods stay a daily review, never an immediate promotion.
    assert R.classify(record(item))['channel']!='telegram'


def test_missing_importance_is_unknown_not_high_and_withheld_details_stay_app_only():
    item=analyse([source('item_1','Microsoft announced a deal.')],[])['result']['items'][0]
    assert R.classify(record(item))['channel']=='digest'
    assert R.classify(dict(kind='move',detail=dict(withheld=True)))['channel']=='app'
    assert R.classify(dict(kind='condition',detail={}))['severity']=='medium'
    assert R.classify(dict(kind='move',detail={}))['severity']=='high'
    item=scored(item,'medium');assert R.classify(record(item))['channel']=='digest'


def test_new_favourable_or_neutral_development_can_preview_but_backfill_and_seen_repeats_cannot():
    earlier=source('item_1','Microsoft described its older service.',0)
    newer=source('item_2','Microsoft announced a new agreement.',1)
    previous=analyse([earlier],[])
    for tone in ('positive','neutral'):
        current=analyse([earlier,newer],[],tones={'item_2':tone})
        current['result']['items']=[scored(i) for i in current['result']['items']]
        proposals=R.important_reporting(previous,current)
        assert len(proposals)==1 and [i['source_id'] for i in proposals[0]['items']]==['item_2']
        assert not R.important_reporting(previous,current,{('news','content:item_2')})
        assert not R.important_reporting(current,current)
        assert not R.important_reporting(None,current)
        repeated=analyse([newer],[relation()],comparisons=[earlier],tones={'item_2':tone})
        repeated['result']['items']=[scored(i) for i in repeated['result']['items']]
        assert not R.important_reporting(previous,repeated)


def preview(owner,monkeypatch):
    iid=prepare(owner);S.generate(iid,transport=legacy('neutral'));W.configure(owner,iid,True)
    commit(iid,[news(id=901,url='https://example.test/new-deal',headline='Microsoft announces a new agreement',
        summary='Microsoft announced a supply agreement for its new products.')])
    monkeypatch.setenv('THESIS_SENTIMENT_TASKS','true')
    reading=S.generate(iid,transport=provider([]))
    monkeypatch.setenv('THESIS_ALERT_ROUTING_PREVIEW','true')
    monkeypatch.setenv('THESIS_ALERT_ROUTING_STARTED_AT',(datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat())
    assert W.publish(owner,iid,reading['id'])==1
    with transaction(owner,consistent=True) as c:
        alert=one(c,"SELECT * FROM research_alerts WHERE kind='important_reporting'")
        assert alert['preview']
        assert len(rows(c,'SELECT * FROM sentiment_analyses'))==2
    return alert


def test_append_only_preview_routes_are_private_idempotent_and_never_send(owner,bot,monkeypatch):
    link(owner,bot);T.configure(owner,True)
    alert=preview(owner,monkeypatch);before=ledger.snapshot()
    assert R.run_once(owner)==1 and R.run_once(owner)==0
    report=review_digest.prepare(owner);r=report['records'][0]
    assert r['detail']['preview'] and r['routing']['severity']=='high' and r['routing']['preview']
    assert r['detail']['payload']['items'][0]['sentiment']=='neutral'
    with pytest.raises(ValueError,match='Preview'):render(r)
    assert not T.run_once(owner) and not bot.sent and ledger.snapshot()==before
    other=uuid4()
    with transaction(admin=True) as c:c.execute("INSERT INTO accounts VALUES(%s,'Authored other account')",(other,))
    with transaction(other,consistent=True) as c:assert not rows(c,'SELECT * FROM alert_routing_decisions')
    with pytest.raises(psycopg.errors.RaiseException):
        with transaction(admin=True) as c:c.execute("UPDATE alert_routing_decisions SET reason='Changed'")
    with pytest.raises(psycopg.errors.RaiseException):
        with transaction(other) as c:
            R.save(c,other,dict(kind='company',id=alert['id'],created_at=alert['created_at'],detail={}),now=datetime.now(timezone.utc))


def test_default_off_and_missing_start_never_backfill_route_rows(owner,monkeypatch):
    stored(owner)
    assert not R.enabled() and R.run_once(owner)==0
    monkeypatch.setenv('THESIS_ALERT_ROUTING_PREVIEW','true')
    assert R.run_once(owner)==0
    with transaction(owner) as c:assert not rows(c,'SELECT * FROM alert_routing_decisions')


def test_shadow_move_decision_is_recorded_without_changing_saved_move_or_telegram(owner,monkeypatch):
    stored(owner);monkeypatch.setenv('THESIS_ALERT_ROUTING_PREVIEW','true')
    monkeypatch.setenv('THESIS_ALERT_ROUTING_STARTED_AT','2026-01-01T00:00:00Z')
    assert R.run_once(owner)==1
    with transaction(owner,consistent=True) as c:
        assert one(c,'SELECT * FROM move_events')['preview']
        decision=one(c,'SELECT * FROM alert_routing_decisions')
        assert decision['channel']=='telegram' and decision['preview']
        assert not rows(c,'SELECT * FROM telegram_deliveries')


def test_even_manually_queued_company_preview_is_rejected_before_transport(owner,bot,monkeypatch):
    link(owner,bot);T.configure(owner,True);alert=preview(owner,monkeypatch)
    with transaction(owner) as c:
        c.execute("INSERT INTO telegram_deliveries(id,owner_id,kind,event_id,event_at) VALUES(%s,%s,'company',%s,%s)",
                  (uuid4(),owner,alert['id'],alert['created_at']))
    assert T.run_once(owner) and not bot.sent
    with transaction(owner,consistent=True) as c:
        assert one(c,'SELECT status FROM telegram_deliveries')['status']=='skipped'


def test_background_preview_failure_cannot_block_delivery_or_log_source_text(owner,monkeypatch,caplog):
    def failure(*args,**kwargs):raise ValueError('Authored private source text must not be logged')
    monkeypatch.setattr(R,'run_once',failure)
    assert R.poll_preview(owner)==0
    assert 'existing delivery continues' in caplog.text
    assert 'private source text' not in caplog.text


def test_same_news_is_not_proposed_for_two_immediate_deliveries(owner,monkeypatch):
    import json
    preview(owner,monkeypatch)
    with transaction(owner) as c:iid=one(c,'SELECT instrument_id FROM news_watches')['instrument_id']
    commit(iid,[news(id=902,url='https://example.test/lower-outlook',headline='Microsoft cuts its annual revenue outlook',
        summary='Microsoft reduced its annual revenue outlook after a decline in demand.')])
    base=provider([])
    def adverse(body):
        response=base(body);value=json.loads(response['output'][0]['content'][0]['text'])
        for item in value.get('items',[]):
            if 'reporting' in item:item['reporting']['impact']='adverse'
            else:item.update(sentiment='negative',basis='stated_outcome')
        response['output'][0]['content'][0]['text']=json.dumps(value)
        return response
    current=S.generate(iid,transport=adverse)
    assert W.publish(owner,iid,current['id'])==2
    R.run_once(owner)
    with transaction(owner,consistent=True) as c:
        decisions=rows(c,'SELECT r.*,a.kind publication_kind FROM alert_routing_decisions r '
            'JOIN research_alerts a ON a.id=r.event_id AND a.owner_id=r.owner_id WHERE a.current_id=%s',(current['id'],))
    assert len(decisions)==2
    assert sum(d['channel']=='telegram' for d in decisions)==1
    old=next(d for d in decisions if d['publication_kind']=='new_reporting')
    assert old['channel']=='app' and old['manifest']['covered_by']
