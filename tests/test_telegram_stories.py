"""Story claims use real disposable RLS/outbox storage and invented providers."""
from copy import deepcopy
from datetime import datetime,timedelta,timezone
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import hashlib
import psycopg
from psycopg.types.json import Jsonb
import pytest
from thesis.db import transaction,one,rows
from thesis.monitoring import telegram as T,telegram_transport as HTTP,telegram_stories as G,alert_routing as R,daily_telegram as DT,daily_updates as D
from thesis.monitoring.telegram_message import render,visible_units
from test_model_budget import clean_model_ledger  # noqa:F401
from test_actual_alert_routing import company
from test_telegram import bot,link,unpace,all_deliveries  # noqa:F401
from test_alert_feedback import rating_bot  # noqa:F401


def setup(owner,bot,monkeypatch):
    link(owner,bot);T.configure(owner,True)
    alert=company(owner,monkeypatch);assert R.run_once(owner)==1
    return alert


def clone(owner,alert,*,items=None):
    """A second immutable publication with the same saved evidence, no AI call."""
    aid,eid=uuid4(),uuid4()
    payload=deepcopy(alert['payload'])
    if items is not None:payload['items']=items
    with transaction(owner) as c:
        c.execute("INSERT INTO sentiment_analyses SELECT %s,instrument_id,%s,call_id,packet,result,clock_timestamp() "
            'FROM sentiment_analyses WHERE id=%s',(aid,'authored-story:'+str(aid),alert['current_id']))
        c.execute('INSERT INTO research_alerts VALUES(%s,%s,%s,%s,%s,%s,NULL,%s,clock_timestamp(),false)',
            (eid,owner,alert['instrument_id'],'important_reporting',aid,alert['previous_id'],Jsonb(payload)))
        value=one(c,'SELECT * FROM research_alerts WHERE id=%s',(eid,))
    return value


def read(owner,alert):
    with transaction(owner) as c:return T.event(c,owner,'company',alert['id'])


def claims(owner):
    with transaction(owner) as c:return rows(c,'SELECT * FROM telegram_story_claims ORDER BY attempt,story_key')


def test_default_off_does_not_query_or_change_comparison_delivery(monkeypatch):
    now=datetime.now(timezone.utc);value=dict(kind='company',detail={})
    assert not G.enabled(now) and G.prepare(None,None,value,None,now) is value


def test_second_publication_does_not_deliver_the_same_article_twice(owner,bot,monkeypatch):
    alert=setup(owner,bot,monkeypatch)
    assert T.run_once(owner) and len(bot.sent)==1
    second=clone(owner,alert);R.run_once(owner);unpace(owner)
    assert T.run_once(owner) and len(bot.sent)==1
    assert all_deliveries(owner)[-1]['status']=='skipped'
    assert 'last 24 hours' in all_deliveries(owner)[-1]['error']
    assert claims(owner)
    with transaction(owner) as c:
        assert one(c,'SELECT count(*) n FROM research_alerts')['n']==2
        assert one(c,'SELECT payload FROM research_alerts WHERE id=%s',(second['id'],))['payload']==alert['payload']


@pytest.mark.parametrize('state,blocked',[
    ('sent',True),('uncertain',True),('failed',False),('skipped',False),('cancelled',False),
])
def test_only_confirmed_or_ambiguous_current_attempts_block_a_story(owner,bot,monkeypatch,state,blocked):
    alert=setup(owner,bot,monkeypatch);T.run_once(owner)
    job=all_deliveries(owner)[0]
    with transaction(owner) as c:c.execute('UPDATE telegram_deliveries SET status=%s WHERE id=%s',(state,job['id']))
    record=read(owner,clone(owner,alert))
    with transaction(owner) as c:
        if blocked:
            with pytest.raises(G.Suppressed):G.prepare(c,owner,record,uuid4(),datetime.now(timezone.utc))
        else:assert G.prepare(c,owner,record,uuid4(),datetime.now(timezone.utc))['_story_groups']


def test_known_rate_limit_waits_for_reserved_story_then_allows_it_after_failure(owner,bot,monkeypatch):
    alert=setup(owner,bot,monkeypatch)
    bot.failure=HTTP.TelegramError('rate_limited','Authored rejection',retry_after=60)
    assert T.run_once(owner)
    record=read(owner,clone(owner,alert));now=datetime.now(timezone.utc)
    with transaction(owner) as c:
        with pytest.raises(G.Deferred) as exc:G.prepare(c,owner,record,uuid4(),now)
        assert exc.value.when>now
        c.execute("UPDATE telegram_deliveries SET status='failed'")
        assert G.prepare(c,owner,record,uuid4(),now)['_story_groups']


def test_24_hours_is_measured_from_confirmed_send_and_exact_boundary_expires(owner,bot,monkeypatch):
    alert=setup(owner,bot,monkeypatch);T.run_once(owner)
    job=all_deliveries(owner)[0];record=read(owner,clone(owner,alert))
    with transaction(owner) as c:
        with pytest.raises(G.Suppressed):G.prepare(c,owner,record,uuid4(),job['sent_at']+timedelta(hours=24,microseconds=-1))
        assert G.prepare(c,owner,record,uuid4(),job['sent_at']+timedelta(hours=24))['_story_groups']


def test_partial_repeat_keeps_fresh_evidence_without_claiming_omitted_source(owner,bot,monkeypatch):
    alert=setup(owner,bot,monkeypatch);T.run_once(owner)
    with transaction(owner) as c:
        result=one(c,'SELECT result FROM sentiment_analyses WHERE id=%s',(alert['current_id'],))['result']
    old=alert['payload']['items'][0]
    fresh=next(i for i in result['items'] if i['channel']=='news' and i['source_id']!=old['source_id'])
    second=clone(owner,alert,items=[old,fresh]);record=read(owner,second)
    with transaction(owner) as c:
        value=G.prepare(c,owner,record,uuid4(),datetime.now(timezone.utc))
        assert [i['source_id'] for i in value['detail']['payload']['items']]==[fresh['source_id']]
    shown=[];message=render(value,shown=shown)
    assert shown==[fresh['source_id']] and G.shown_keys(value,shown)
    assert record['detail']['payload']['items']==[old,fresh] and visible_units(message)<=3800


def test_claims_are_private_append_only_and_must_match_sending_attempt(owner,bot,monkeypatch):
    setup(owner,bot,monkeypatch);T.run_once(owner)
    values=claims(owner);assert values
    other=uuid4()
    with transaction(admin=True) as c:c.execute("INSERT INTO accounts VALUES(%s,'Authored other account')",(other,))
    with transaction(other) as c:assert not rows(c,'SELECT * FROM telegram_story_claims')
    with pytest.raises(psycopg.errors.RaiseException):
        with transaction(admin=True) as c:c.execute("UPDATE telegram_story_claims SET story_key=%s",('url:'+'0'*64,))
    with pytest.raises(psycopg.errors.RaiseException):
        with transaction(owner) as c:
            item=values[0];c.execute('INSERT INTO telegram_story_claims VALUES(%s,%s,2,%s,%s)',
                (owner,item['delivery_id'],'url:'+'0'*64,item['created_at']))
    with pytest.raises(psycopg.errors.RaiseException,match='Story claims must belong'):
        with transaction(other) as c:
            item=values[0];c.execute('INSERT INTO telegram_story_claims VALUES(%s,%s,1,%s,%s)',
                (owner,item['delivery_id'],'url:'+'0'*64,item['created_at']))


def test_one_accounts_history_does_not_suppress_another_accounts_story(owner,bot,monkeypatch):
    alert=setup(owner,bot,monkeypatch);T.run_once(owner)
    other=uuid4()
    with transaction(admin=True) as c:c.execute("INSERT INTO accounts VALUES(%s,'Authored other account')",(other,))
    record=read(other,clone(other,alert))
    with transaction(other) as c:
        assert G.prepare(c,other,record,uuid4(),datetime.now(timezone.utc))['_story_groups']


@pytest.mark.parametrize('changes,should_match',[
    ('https://EXAMPLE.test/report?id=7&utm_source=x#section',True),
    ('https://example.test/report?utm_campaign=y&id=7',True),
    ('https://example.test/report?id=8',False),
])
def test_url_identity_drops_tracking_but_preserves_article_ids(changes,should_match):
    assert (G.article(changes)==G.article('https://example.test/report?id=7'))==should_match


@pytest.mark.parametrize('url',['javascript:bad','https://private:secret@example.test/x','https://127.0.0.1/x','https://example.test:8080/x'])
def test_invalid_url_is_not_used_as_a_delivery_identity(url):assert G.article(url) is None


def authored_source(text,*,identity='new',url='https://example.test/report'):
    return dict(id=identity,channel='news',url=url,title=text,text=text,content_hash=hashlib.sha256(text.encode()).hexdigest(),
        passages=[dict(id='p1',quote=text)],published_at='2026-10-16T10:00:00Z')


def test_cited_numeric_or_status_update_keeps_its_own_identity_but_claims_url_for_later_cosmetic_repeats():
    old=authored_source('Microsoft announced a 10 million dollar deal.',identity='old')
    new=authored_source('Microsoft confirmed a 20 million dollar deal.')
    item=dict(source_id='new',reporting_basis=dict(citations=[dict(quote=new['text'])]))
    analysis=dict(packet=dict(sources=[new],comparison_sources=[old]),result=dict(items=[item],coverage_links=[]))
    normal=G.source_keys(analysis,new);claim=G.source_keys(analysis,new,for_claim=True)
    url=G.key('url',G.article(new['url']))
    assert url not in normal and url in claim
    assert 'content:'+new['content_hash'] in normal and any(k.startswith('update:') for k in normal)
    item['reporting_basis']['citations']=[dict(quote=old['text'])]
    assert url in G.source_keys(analysis,new)  # A stale quote cannot establish an update.


def test_validated_repeat_ancestors_link_different_outlets_but_added_details_do_not():
    old=authored_source('An earlier stated development.',identity='old',url='https://example.test/earlier')
    new=authored_source('Another report of that development.')
    link=dict(source_id='new',reference_source_id='old',relation='repeats',repeat_suppression_allowed=True)
    analysis=dict(packet=dict(sources=[new],comparison_sources=[old]),result=dict(items=[],coverage_links=[link]))
    assert 'content:'+old['content_hash'] in G.source_keys(analysis,new)
    link.update(relation='adds_detail',repeat_suppression_allowed=False,change_evidence='distinct_excerpts')
    assert 'content:'+old['content_hash'] not in G.source_keys(analysis,new)


def test_social_authors_with_the_same_words_are_not_merged_as_one_opinion():
    first=authored_source('I like this service.');first.update(channel='social',platform='reddit',post_key='comment-a')
    second=deepcopy(first);second.update(id='other',post_key='comment-b')
    assert G.source_keys({},first).isdisjoint(G.source_keys({},second))


def test_legacy_sent_story_is_checked_read_only_without_backfilling_claims(owner,bot,monkeypatch):
    alert=setup(owner,bot,monkeypatch)
    monkeypatch.setenv('THESIS_ALERT_ROUTING_LIVE','false')
    # Use the legacy kind for an old ordinary message, never a new importance type.
    with transaction(owner) as c:
        c.execute("INSERT INTO research_alerts SELECT %s,owner_id,instrument_id,'new_reporting',current_id,previous_id,version_id,payload||'{\"kind\":\"new_reporting\"}'::jsonb,created_at,false FROM research_alerts WHERE id=%s",
            (uuid4(),alert['id']))
    assert T.run_once(owner) and len(bot.sent)==1 and not claims(owner)
    monkeypatch.setenv('THESIS_ALERT_ROUTING_LIVE','true')
    before=all_deliveries(owner);record=read(owner,clone(owner,alert))
    with transaction(owner,consistent=True) as c:
        with pytest.raises(G.Suppressed):G.prepare(c,owner,record,uuid4(),datetime.now(timezone.utc))
    assert not claims(owner) and all_deliveries(owner)==before


def recap(owner,alerts,monkeypatch,*,policy='authored-story-recap'):
    now=datetime.now(timezone.utc);identity=uuid4()
    monkeypatch.setenv('THESIS_DAILY_REPORTS','true')
    monkeypatch.setenv('THESIS_DAILY_REPORTS_STARTED_AT',(now-timedelta(days=1)).isoformat())
    monkeypatch.setenv('THESIS_DAILY_TELEGRAM_STARTED_AT',(now-timedelta(minutes=1)).isoformat())
    monkeypatch.setenv('THESIS_DIGEST_TELEGRAM_ENABLED','true')
    monkeypatch.setenv('THESIS_ALERT_FEEDBACK','true')
    monkeypatch.setattr(T,'clock',lambda:now+timedelta(seconds=2))
    with transaction(owner) as c:
        c.execute('INSERT INTO daily_digests VALUES(%s,%s,%s,%s,%s,%s,false)',
            (identity,owner,now-timedelta(minutes=1),now+timedelta(seconds=1),now+timedelta(seconds=1),policy))
        for pos,alert in enumerate(alerts):
            route=uuid4()
            c.execute("INSERT INTO alert_routing_decisions VALUES(%s,%s,'company',%s,'authored-recap-route','medium','digest',false,'Authored medium route',%s,%s)",
                (route,owner,alert['id'],Jsonb({}),now))
            c.execute("INSERT INTO daily_digest_members VALUES(%s,%s,%s,%s,'company',%s)",(owner,identity,pos,route,alert['id']))
    unpace(owner)
    return identity


def test_immediate_and_recap_do_not_forward_the_same_story_twice(owner,bot,monkeypatch):
    alert=setup(owner,bot,monkeypatch);T.run_once(owner)
    second=clone(owner,alert);recap(owner,[second],monkeypatch)
    assert T.run_once(owner) and len(bot.sent)==1
    assert all_deliveries(owner)[-1]['kind']=='digest' and all_deliveries(owner)[-1]['status']=='skipped'


def test_recap_claim_also_blocks_a_later_immediate_publication(owner,bot,monkeypatch):
    alert=setup(owner,bot,monkeypatch)
    with transaction(owner) as c:
        c.execute("INSERT INTO telegram_deliveries(id,owner_id,kind,event_id,event_at,status) VALUES(%s,%s,'company',%s,%s,'cancelled')",
            (uuid4(),owner,alert['id'],alert['created_at']))
    recap(owner,[alert],monkeypatch)
    assert T.run_once(owner) and len(bot.sent)==1 and 'Daily recap' in bot.sent[0]['text']
    clone(owner,alert);R.run_once(owner);unpace(owner)
    assert T.run_once(owner) and len(bot.sent)==1 and all_deliveries(owner)[-1]['status']=='skipped'


def test_repeated_members_inside_one_recap_are_shown_and_claimed_once(owner,bot,monkeypatch):
    alert=setup(owner,bot,monkeypatch);second=clone(owner,alert)
    with transaction(owner) as c:
        c.execute("INSERT INTO telegram_deliveries(id,owner_id,kind,event_id,event_at,status) VALUES(%s,%s,'company',%s,%s,'cancelled')",
            (uuid4(),owner,alert['id'],alert['created_at']))
    identity=recap(owner,[alert,second],monkeypatch)
    assert T.run_once(owner) and len(bot.sent)==1
    assert '1 repeated update is omitted' in bot.sent[0]['text']
    job=next(j for j in all_deliveries(owner) if j['kind']=='digest')
    with transaction(owner) as c:
        shown=rows(c,'SELECT * FROM telegram_digest_items WHERE delivery_id=%s',(job['id'],))
        assert len(shown)==1 and shown[0]['member_position']==0
        assert one(c,'SELECT count(*) n FROM daily_digest_members WHERE digest_id=%s',(identity,))['n']==2


def test_rate_limit_retry_can_reuse_its_own_claims_and_only_confirmed_attempt_blocks(owner,bot,monkeypatch):
    alert=setup(owner,bot,monkeypatch)
    bot.failure=HTTP.TelegramError('rate_limited','Authored rate limit',retry_after=1)
    assert T.run_once(owner);job=all_deliveries(owner)[0]
    with transaction(owner) as c:
        c.execute('UPDATE telegram_deliveries SET retry_at=NULL WHERE id=%s',(job['id'],))
    unpace(owner);bot.failure=None
    assert T.run_once(owner) and all_deliveries(owner)[0]['attempts']==2
    assert {c['attempt'] for c in claims(owner)}=={1,2} and len(bot.sent)==2
    record=read(owner,clone(owner,alert))
    with transaction(owner) as c:
        with pytest.raises(G.Suppressed):G.prepare(c,owner,record,uuid4(),datetime.now(timezone.utc))


def test_claims_commit_before_http_and_concurrent_workers_send_one_copy(owner,bot,monkeypatch):
    setup(owner,bot,monkeypatch);entered,release=Event(),Event();original=HTTP.call
    def paused(key,method,body):
        if method=='sendMessage':
            assert claims(owner)
            assert all_deliveries(owner)[0]['status']=='sending'
            entered.set();assert release.wait(10)
        return original(key,method,body)
    monkeypatch.setattr(HTTP,'call',paused)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first=pool.submit(T.run_once,owner);assert entered.wait(10)
        assert not pool.submit(T.run_once,owner).result(timeout=3)
        release.set();assert first.result(timeout=10)
    assert len(bot.sent)==1


def test_renderer_reports_only_primary_evidence_that_survives_the_message_bound():
    items=[dict(source_id=str(i),reporting_basis=dict(citations=[dict(quote='😀'*320)])) for i in range(3)]
    record=dict(kind='company',title='😀'*180,created_at=datetime.now(timezone.utc),
        detail=dict(symbol='😀'*18,payload=dict(reason='😀'*450,items=items,
            shifts=[dict(title='😀'*120,before=dict(tone='😀'*30),after=dict(tone='😀'*30))]*3),sources=[]))
    shown=[];message=render(record,shown=shown)
    # Since 20 Oct 2026 the rule paragraph is gone, so both bounded excerpts fit;
    # shown must still name exactly the excerpts present, never the third item.
    assert shown==['0','1'] and message.count('😀'*320)==2 and visible_units(message)<=3800


def test_new_price_or_condition_event_is_not_suppressed_by_its_shared_news_context():
    event=dict(kind='move',id=uuid4(),detail=dict(sources=[dict(url='https://example.test/report')]))
    other=deepcopy(event);other['id']=uuid4()
    assert G.groups(None,None,event)['__event'].isdisjoint(G.groups(None,None,other)['__event'])
    condition=dict(kind='condition',id=event['id'],detail=event['detail'])
    assert G.groups(None,None,event)['__event'].isdisjoint(G.groups(None,None,condition)['__event'])


def test_rejected_attempts_do_not_mark_their_omitted_stories_as_sent_after_a_changed_retry(owner,bot,monkeypatch):
    alert=setup(owner,bot,monkeypatch)
    with transaction(owner) as c:
        result=one(c,'SELECT result FROM sentiment_analyses WHERE id=%s',(alert['current_id'],))['result']
        c.execute("INSERT INTO telegram_deliveries(id,owner_id,kind,event_id,event_at,status) VALUES(%s,%s,'company',%s,%s,'cancelled')",
            (uuid4(),owner,alert['id'],alert['created_at']))
    first=alert['payload']['items'][0]
    other=next(i for i in result['items'] if i['channel']=='news' and i['source_id']!=first['source_id'])
    sending=clone(owner,alert,items=[first,other]);R.run_once(owner)
    bot.failure=HTTP.TelegramError('rate_limited','Authored rejection',retry_after=1)
    assert T.run_once(owner)
    original=T.event
    def changed(c,o,k,i,**kwargs):
        record=original(c,o,k,i,**kwargs)
        if k=='company' and str(i)==str(sending['id']):
            record['detail']['payload']['items']=[other]
        return record
    monkeypatch.setattr(T,'event',changed);bot.failure=None
    with transaction(owner) as c:c.execute("UPDATE telegram_deliveries SET retry_at=NULL WHERE status='queued'")
    unpace(owner);assert T.run_once(owner)
    job=next(j for j in all_deliveries(owner) if j['event_id']==sending['id'])
    assert job['attempts']==2 and job['status']=='sent'
    repeated=clone(owner,alert,items=[first]);R.run_once(owner);unpace(owner)
    assert T.run_once(owner) and all_deliveries(owner)[-1]['status']=='sent'
    assert len(bot.sent)==3
    with transaction(owner) as c:
        record=original(c,owner,'company',repeated['id'])
        keys=next(iter(G.groups(c,owner,record).values()))
        confirmed={r['story_key'] for r in rows(c,'SELECT story_key FROM telegram_story_claims WHERE delivery_id=%s AND attempt=2',(job['id'],))}
    assert not keys&confirmed


def test_comparison_source_links_do_not_replace_a_price_or_condition_event_identity():
    own={G.key('event','condition:authored')}
    record={'_story_claim_groups':{'__event':own}}
    assert G.shown_keys(record,['some-cited-filing'])==own
    assert not G.shown_keys({'_story_claim_groups':{'visible':{'content:'+'0'*64}}},[])


def test_database_rejects_claims_even_for_a_manually_marked_preview_send(owner,monkeypatch):
    alert=company(owner,monkeypatch,actual=False);identity=uuid4();now=datetime.now(timezone.utc)
    with transaction(owner) as c:
        c.execute("INSERT INTO telegram_deliveries(id,owner_id,kind,event_id,event_at,status,attempts,attempted_at) VALUES(%s,%s,'company',%s,%s,'sending',1,%s)",
            (identity,owner,alert['id'],alert['created_at'],now))
    with pytest.raises(psycopg.errors.RaiseException,match='Story claims must belong'):
        with transaction(owner) as c:G.save(c,owner,dict(id=identity,attempts=0),{'url:'+'0'*64},now)


def test_preview_and_withheld_details_never_enter_story_preparation(monkeypatch):
    now=datetime.now(timezone.utc)
    monkeypatch.setenv('THESIS_ALERT_ROUTING_LIVE','true')
    monkeypatch.setenv('THESIS_ALERT_ROUTING_LIVE_STARTED_AT',(now-timedelta(seconds=1)).isoformat())
    for field in ('preview','withheld'):
        with pytest.raises(ValueError,match='Preview or withheld'):
            G.prepare(None,None,dict(kind='company',detail={field:True}),uuid4(),now)


def test_publisher_homepage_does_not_merge_unrelated_stories():
    assert G.article('https://example.test/?utm_source=feed') is None
    assert G.article('https://example.test/') is None
    assert G.article('https://example.test/?article=7') is not None


def test_same_article_reaching_two_watched_companies_is_delivered_once(owner,bot,monkeypatch):
    from thesis.research.sec.service import add_company
    from thesis.research import sentiment as S
    from thesis.monitoring import news_watch as W
    from test_market import commit,news
    from test_sentiment_task_runner import provider
    alert=setup(owner,bot,monkeypatch);assert T.run_once(owner)
    iid=add_company('NVDA')['instrument_id']
    commit(iid,[news(id=902,url='https://example.test/new-deal',headline='Nvidia joins the Microsoft supply agreement',
        summary='Nvidia joined the Microsoft supply agreement for its new products.')])
    reading=S.generate(iid,transport=provider([]));W.configure(owner,iid,True)
    with transaction(owner) as c:
        analysis=one(c,'SELECT * FROM sentiment_analyses WHERE id=%s',(reading['id'],))
        payload=deepcopy(alert['payload']);payload['items']=[i for i in analysis['result']['items'] if i['channel']=='news']
        c.execute("INSERT INTO research_alerts VALUES(%s,%s,%s,'important_reporting',%s,%s,NULL,%s,clock_timestamp(),false)",
            (uuid4(),owner,iid,reading['id'],reading['id'],Jsonb(payload)))
    assert R.run_once(owner)==1
    unpace(owner);assert T.run_once(owner)
    assert len(bot.sent)==1 and all_deliveries(owner)[-1]['status']=='skipped'


def test_pending_actual_recap_keeps_its_duplicate_guard_after_routing_is_rolled_back(owner,bot,monkeypatch):
    alert=setup(owner,bot,monkeypatch);assert T.run_once(owner)
    recap(owner,[clone(owner,alert)],monkeypatch,policy=D.LIVE_POLICY)
    monkeypatch.setenv('THESIS_ALERT_ROUTING_LIVE','false')
    assert T.run_once(owner) and len(bot.sent)==1 and all_deliveries(owner)[-1]['status']=='skipped'


def test_actual_recap_claims_are_saved_even_if_ordinary_routing_was_rolled_back(owner,bot,monkeypatch):
    alert=setup(owner,bot,monkeypatch)
    with transaction(owner) as c:
        c.execute("INSERT INTO telegram_deliveries(id,owner_id,kind,event_id,event_at,status) VALUES(%s,%s,'company',%s,%s,'cancelled')",
            (uuid4(),owner,alert['id'],alert['created_at']))
    recap(owner,[alert],monkeypatch,policy=D.LIVE_POLICY)
    monkeypatch.setenv('THESIS_ALERT_ROUTING_LIVE','false')
    assert T.run_once(owner) and len(bot.sent)==1 and claims(owner)


def test_repeated_high_evidence_cannot_promote_remaining_medium_news_to_immediate(owner,bot,monkeypatch):
    alert=setup(owner,bot,monkeypatch);T.run_once(owner)
    with transaction(owner) as c:
        analysis=one(c,'SELECT packet,result FROM sentiment_analyses WHERE id=%s',(alert['current_id'],))
    high=alert['payload']['items'][0]
    medium=next(i for i in analysis['result']['items'] if i['channel']=='news' and i['source_id']!=high['source_id'])
    record=read(owner,clone(owner,alert,items=[high,medium]))
    medium['importance']['level']='medium'
    monkeypatch.setattr(G,'analysis_for',lambda *_:analysis)
    with transaction(owner) as c:
        with pytest.raises(G.Suppressed):G.prepare(c,owner,record,uuid4(),datetime.now(timezone.utc),immediate=True)
    assert len(bot.sent)==1


def test_unverifiable_legacy_formatter_cannot_block_every_new_message(owner,bot,monkeypatch):
    alert=setup(owner,bot,monkeypatch)
    monkeypatch.setenv('THESIS_ALERT_ROUTING_LIVE','false')
    with transaction(owner) as c:
        c.execute("INSERT INTO research_alerts SELECT %s,owner_id,instrument_id,'new_reporting',current_id,previous_id,version_id,payload||'{\"kind\":\"new_reporting\"}'::jsonb,created_at,false FROM research_alerts WHERE id=%s",
            (uuid4(),alert['id']))
    assert T.run_once(owner) and len(bot.sent)==1
    monkeypatch.setenv('THESIS_ALERT_ROUTING_LIVE','true')
    record=read(owner,clone(owner,alert))
    def malformed(*_a,**_k):raise ValueError('Authored inaccessible old interpretation')
    monkeypatch.setattr(G,'render',malformed)
    with transaction(owner) as c:
        assert G.prepare(c,owner,record,uuid4(),datetime.now(timezone.utc))['_story_groups']


def test_legacy_google_news_identity_cannot_turn_a_homepage_into_one_shared_story():
    first=authored_source('One company announces a deal.',url='https://news.google.com/')
    second=authored_source('Another company reports earnings.',identity='other',url='https://news.google.com/')
    analysis=dict(packet=dict(sources=[first,second],comparison_sources=[]),result=dict(items=[],coverage_links=[]))
    assert G.source_keys(analysis,first).isdisjoint(G.source_keys(analysis,second))
