"""Private move previews and durable one-attempt AI behavior; no live calls."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import timedelta
from threading import Event
from uuid import uuid4
import hashlib
import json
import psycopg
import pytest
from psycopg.types.json import Jsonb
from thesis import review_digest
from thesis.db import transaction, one, rows
from thesis.monitoring import move_alerts as A, news_watch as W, price_moves as M
from thesis.providers import ledger, settings
from thesis.research import market
from thesis.research.sec.service import add_company
from test_model_budget import clean_model_ledger  # noqa: F401
from test_move_explainer import call, answer
from test_price_moves import NOW, quote


def setup(owner, *, grouping=False):
    members=[]
    with transaction(admin=True) as c:
        c.execute('TRUNCATE world_news_articles')
        c.execute("INSERT INTO sources VALUES('finnhub-news','Authored market news','finnhub-pitch') ON CONFLICT DO NOTHING")
    rid=uuid4();ref=quote('97.9',identity=str(rid))
    with transaction(source=True) as c:
        c.execute('INSERT INTO reference_price_snapshots VALUES(%s,%s,%s,%s,%s,%s,%s)',
                  (rid,'QQQ','quote',Jsonb({}),Jsonb(ref),'0'*64,NOW))
        c.execute("INSERT INTO reference_refresh_state(symbol,resource,current_id) VALUES('QQQ','quote',%s) "
                  "ON CONFLICT(symbol,resource) DO UPDATE SET current_id=excluded.current_id",(rid,))
    symbols=[('NVDA','96.8'),('AAPL','96.9'),('AMZN','98.3'),('GOOGL','98.3')] if grouping else [('MSFT','96.8')]
    ids={}
    for symbol,price in symbols:
        iid=add_company(symbol)['instrument_id'];ids[symbol]=iid
        W.configure(owner,iid,True,now=NOW)
        qid=uuid4();q=quote(price,identity=str(qid))
        with transaction(source=True) as c:
            # This authored replay fixture predates company registration today.
            c.execute('UPDATE instrument_state SET cutoff=%s WHERE instrument_id=%s',(NOW-timedelta(minutes=2),iid))
            c.execute('INSERT INTO market_quotes VALUES(%s,%s,%s,%s)',(qid,iid,Jsonb(q),NOW))
            market.commit_news(c,iid,[dict(url=f'https://example.test/{symbol}',
                headline=f'{symbol} cuts its annual revenue outlook',body='The earlier outlook no longer applies.',
                publisher='Authored Wire',provider_id='authored',published_at=NOW-timedelta(minutes=1))],0,NOW)
        value=M.measure(symbol,q,indexes={'QQQ':ref},now=NOW)
        members.append(value)
    return M.group(members)[0],ids


def stored(owner, *, grouping=False):
    event,ids=setup(owner,grouping=grouping)
    eid=A.record(owner,event,now=NOW)
    assert eid
    return eid,event,ids


def response(request):
    content=json.loads(request['input'][1]['content'])
    article=content['headlines'][0]
    return call(answer(source_id=article['source_id']))['response_body']


def test_one_group_private_membership_deduplication_and_immutable_records(owner):
    eid,event,ids=stored(owner,grouping=True)
    assert A.record(owner,event,now=NOW+timedelta(minutes=15)) is None
    with transaction(owner,consistent=True) as c:
        assert len(rows(c,'SELECT * FROM move_events'))==1
        assert len(rows(c,'SELECT * FROM move_event_members'))==4
        assert len(rows(c,'SELECT * FROM move_trigger_claims'))==2
        detail=A.present(c,owner,eid,now=NOW)
        assert detail['preview'] and not detail['withheld']
        assert 'AMZN −1.7%' in detail['title'] and 'Nasdaq −2.1%' in detail['title']
        assert [m['symbol'] for m in detail['members'] if m['context_only']]==['AMZN','GOOGL']
    with transaction(str(uuid4()),consistent=True) as c:
        assert not A.present(c,owner,eid,now=NOW)
        for table in ('move_events','move_event_members','move_trigger_claims'):
            assert not rows(c,'SELECT * FROM '+table)
    with pytest.raises(psycopg.errors.RaiseException):
        with transaction(admin=True) as c:c.execute('UPDATE move_events SET preview=false WHERE id=%s',(eid,))


def test_stopped_or_missing_watch_cannot_record_move(owner):
    event,ids=setup(owner,grouping=True)
    W.configure(owner,ids['GOOGL'],False,now=NOW)
    assert A.record(owner,event,now=NOW) is None
    with transaction(owner,consistent=True) as c:assert not rows(c,'SELECT * FROM move_events')


def test_two_workers_publish_only_one_event(owner):
    event,ids=setup(owner)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:A.record(owner,event,now=NOW),range(2)))
    assert sum(r is not None for r in results)==1


def test_wrong_company_quote_cannot_record_a_move(owner):
    event,ids=setup(owner,grouping=True)
    event['members'][0]['quote_id']=event['members'][-1]['quote_id']
    with pytest.raises(ValueError,match='another company'):A.record(owner,event,now=NOW)
    with transaction(owner,consistent=True) as c:assert not rows(c,'SELECT * FROM move_events')


def test_stale_or_modified_numbers_cannot_be_saved_even_after_a_fresh_measurement(owner):
    event,ids=setup(owner)
    assert A.record(owner,event,now=NOW+timedelta(minutes=31)) is None
    event['members'][0]['change_percent']='-90'
    with pytest.raises(ValueError,match='numbers'):A.record(owner,event,now=NOW)


def test_database_membership_rejects_wrong_company_quote_even_without_code_guard(owner):
    eid,event,ids=stored(owner,grouping=True)
    with pytest.raises(psycopg.errors.RaiseException,match='another company'):
        with transaction(owner) as c:
            c.execute('INSERT INTO move_event_members SELECT m.owner_id,m.event_id,m.instrument_id,n.quote_id,m.qqq_id,m.spy_id,m.sector_id,m.history_id,m.triggered,m.payload '
                      'FROM move_event_members m JOIN move_event_members n ON m.event_id=n.event_id AND m.instrument_id<>n.instrument_id WHERE m.event_id=%s LIMIT 1',(eid,))


def test_one_explainer_call_reused_and_pinned_to_original_headline_versions(owner):
    eid,event,ids=stored(owner);calls=[]
    def transport(body):calls.append(body);return response(body)
    assert A.explain(owner,eid,transport=transport,model=settings.OPENAI_EXPLAINER_MODEL,now=NOW)
    assert not A.explain(owner,eid,transport=transport,model=settings.OPENAI_EXPLAINER_MODEL,now=NOW)
    assert len(calls)==1
    with transaction(owner,consistent=True) as c:
        detail=A.present(c,owner,eid,now=NOW)
        assert detail['explanation_status']=='valid'
        assert detail['sources'][0]['version']
        assert 'outlook cut' in detail['explanation']['text']
        saved=one(c,'SELECT * FROM move_explanations WHERE event_id=%s',(eid,))
        paid=one(c,'SELECT * FROM model_calls WHERE id=%s',(saved['call_id'],))
        assert paid['status']=='settled' and str(paid['owner_id'])==owner


def test_paid_invalid_response_is_recorded_once_without_retry(owner):
    eid,event,ids=stored(owner);calls=[]
    def bad(body):calls.append(True);return call(answer(quote='invented quote without support'))['response_body']
    assert A.explain(owner,eid,transport=bad,model=settings.OPENAI_EXPLAINER_MODEL,now=NOW)
    assert not A.explain(owner,eid,transport=bad,model=settings.OPENAI_EXPLAINER_MODEL,now=NOW)
    with transaction(owner,consistent=True) as c:
        detail=A.present(c,owner,eid,now=NOW)
        assert detail['explanation_status']=='failed' and 'No automatic paid retry' in detail['explanation']['notice']
        assert detail['members'] and not detail['sources']
    assert calls==[True]


def test_paid_transport_failure_keeps_hold_and_never_redispatches(owner):
    eid,event,ids=stored(owner);calls=[]
    def failed(body):calls.append(True);raise TimeoutError('Authored private diagnostic')
    assert A.explain(owner,eid,transport=failed,model=settings.OPENAI_EXPLAINER_MODEL,now=NOW)
    assert not A.explain(owner,eid,transport=failed,model=settings.OPENAI_EXPLAINER_MODEL,now=NOW+timedelta(days=1))
    with transaction(owner,consistent=True) as c:
        record=one(c,'SELECT * FROM model_calls WHERE owner_id=%s',(owner,))
        assert record['status']=='unresolved' and record['reserved_nano_usd']>0
        assert not rows(c,"SELECT * FROM model_calls WHERE request_key LIKE '%%:redispatch:%%'")
    assert calls==[True]


def test_concurrent_explanation_does_not_dispatch_again(owner):
    eid,event,ids=stored(owner);waiting,release=Event(),Event();calls=[]
    def transport(body):
        calls.append(True);waiting.set();assert release.wait(10)
        return response(body)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first=pool.submit(A.explain,owner,eid,transport=transport,model=settings.OPENAI_EXPLAINER_MODEL,now=NOW)
        try:
            assert waiting.wait(5)
            assert not A.explain(owner,eid,transport=transport,model=settings.OPENAI_EXPLAINER_MODEL,now=NOW)
        finally:release.set()
        assert first.result(timeout=5)
    assert calls==[True]


def test_interrupted_attempt_before_dispatch_does_not_create_a_new_paid_attempt(owner):
    eid,event,ids=stored(owner)
    with transaction(owner) as c:
        c.execute('INSERT INTO move_explainer_attempts VALUES(%s,%s,%s,%s)',(owner,eid,f'move-explanation:{owner}:{eid}',NOW))
    assert not A.explain(owner,eid,transport=lambda _:pytest.fail('Interrupted journal resent'),model=settings.OPENAI_EXPLAINER_MODEL,now=NOW)


def test_saved_settlement_can_be_recovered_free_after_model_is_disabled(owner,monkeypatch):
    eid,event,ids=stored(owner)
    with transaction(owner,consistent=True) as c:
        saved=one(c,'SELECT * FROM move_events WHERE id=%s',(eid,))
    key=f'move-explanation:{owner}:{eid}'
    with transaction(owner) as c:c.execute('INSERT INTO move_explainer_attempts VALUES(%s,%s,%s,%s)',(owner,eid,key,NOW))
    request=A.move_explainer.request_for(A.request_content(saved),model=settings.OPENAI_EXPLAINER_MODEL)
    ledger.execute(key,'authored recovery fixture',request,owner=owner,transport=response)
    monkeypatch.setattr(settings,'EXPLAINER_MODEL',None)
    monkeypatch.setattr(ledger,'execute',lambda *a,**k:pytest.fail('Free recovery dispatched AI'))
    with transaction(owner,consistent=True) as c:assert A.present(c,owner,eid,now=NOW)['explanation_status']=='unfinished'
    assert A.recover_pending(owner,now=NOW)==1
    assert A.recover_pending(owner,now=NOW)==0
    with transaction(owner,consistent=True) as c:assert A.present(c,owner,eid,now=NOW)['explanation_status']=='valid'
    fresh,_,_=stored(owner,grouping=True)
    assert not A.explain(owner,fresh,now=NOW,allow_new_attempt=False)


def test_source_withdrawal_blocks_explaining_and_withholds_saved_details(owner):
    eid,event,ids=stored(owner)
    assert A.explain(owner,eid,transport=response,model=settings.OPENAI_EXPLAINER_MODEL,now=NOW)
    with transaction(admin=True) as c:c.execute("UPDATE sources SET entitlement='fictional' WHERE id='finnhub-news'")
    with transaction(owner,consistent=True) as c:
        detail=A.present(c,owner,eid,now=NOW)
        assert detail['withheld'] and detail['members']==[] and detail['explanation'] is None
    assert not A.explain(owner,eid,transport=lambda _:pytest.fail('Withdrawn evidence reached AI'),model=settings.OPENAI_EXPLAINER_MODEL,now=NOW)


def test_world_article_correction_withholds_explanation_without_rewriting_snapshot(owner):
    event,ids=setup(owner);wid=uuid4()
    with transaction(admin=True) as c:
        c.execute('INSERT INTO world_news_articles VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
            (wid,'https://example.test/world','Authored market-wide inflation report','Prices rose in the reported month.',
             'Authored Wire','general','authored',NOW-timedelta(minutes=5),NOW,[]))
    eid=A.record(owner,event,now=NOW)
    with transaction(owner,consistent=True) as c:
        assert not A.present(c,owner,eid,now=NOW)['withheld']
        original=one(c,'SELECT headlines FROM move_events WHERE id=%s',(eid,))['headlines']
    with transaction(admin=True) as c:c.execute("UPDATE world_news_articles SET headline='Corrected authored headline' WHERE id=%s",(wid,))
    with transaction(owner,consistent=True) as c:
        assert A.present(c,owner,eid,now=NOW)['withheld']
        assert one(c,'SELECT headlines FROM move_events WHERE id=%s',(eid,))['headlines']==original


def test_past_day_bounds_exclude_future_sources_and_reads_never_fetch_or_call_ai(owner,monkeypatch):
    event,ids=setup(owner)
    with transaction(admin=True) as c:
        for label,published in [('future',NOW+timedelta(minutes=1)),('old',NOW-timedelta(hours=25))]:
            c.execute('INSERT INTO world_news_articles VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                (uuid4(),'https://example.test/'+label,'Authored '+label+' headline','','Authored Wire','general',label,published,NOW,[]))
    eid=A.record(owner,event,now=NOW)
    with transaction(owner,consistent=True) as c:
        sources=one(c,'SELECT headlines FROM move_events WHERE id=%s',(eid,))['headlines']['sources']
        assert len(sources)==1
    monkeypatch.setattr(market,'fetch',lambda *a:pytest.fail('Read fetched prices'))
    monkeypatch.setattr(ledger,'execute',lambda *a,**k:pytest.fail('Read called AI'))
    with transaction(owner,consistent=True) as c:assert A.present(c,owner,eid,now=NOW)


def test_grouped_updates_filters_counts_review_and_export(owner):
    eid,event,ids=stored(owner,grouping=True)
    whole=review_digest.prepare(owner,days=0,now=NOW+timedelta(seconds=1))
    assert whole['total']==whole['totals']['new_count']==whole['totals']['pending_count']==1
    assert len(whole['records'])==1 and whole['records'][0]['kind']=='move'
    assert all(c['new_count']==1 for c in whole['companies'])
    google=review_digest.prepare(owner,days=0,instrument_id=ids['GOOGL'],now=NOW+timedelta(seconds=1))
    assert google['total']==google['totals']['pending_count']==1
    _,html=review_digest.render_report(google)
    assert 'market context only' in html and 'Preview' in html and 'GOOGL' in html
    assert A.review(owner,eid,'reviewed')['review_action']=='reviewed'
    later=review_digest.prepare(owner,days=0,instrument_id=ids['GOOGL'],review='pending')
    assert later['total']==0 and later['totals']['pending_count']==0
    with pytest.raises(ValueError):A.review(owner,eid,'delete')
    with pytest.raises(ValueError):A.review(str(uuid4()),eid,'reviewed')
