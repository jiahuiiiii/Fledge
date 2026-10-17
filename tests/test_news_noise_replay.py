"""Company-news counterfactual uses complete authored readings, never a provider."""
from copy import deepcopy
from datetime import datetime,timedelta,timezone
import hashlib
import pytest
from experiments.soclaas_replay import news_noise_replay as E
from thesis.research import sentiment_task_runner as TR
from thesis.research.citations import source_passages

START=datetime(2026,10,9,16,tzinfo=timezone.utc)


def reading(capture,company,sources,at,levels):
    packet=dict(E.N.POLICIES,instrument_id=company['instrument_id'],
        company={k:company[k] for k in ('symbol','name')},cutoff=at.isoformat(),
        sources=sources,comparison_sources=[])
    raw=[]
    for source in sources:
        level=levels.get(source['id'],'low')
        raw.append(dict(id=source['label'],relevance='relevant',sentiment='neutral',
            statement='reported_development',topic='general',basis='descriptive',passages=['p1'],
            previous_passages=[],context_passages=[],price_claims=[],
            reporting=dict(kind='reported_event',impact='not_stated',passages=['p1'])))
    result=E.S.render(TR.response(raw),packet)
    result.update(prompt_version=E.T.PROMPT,batching=dict(policy=E.T.POLICY))
    for item in result['items']:
        item['importance']=dict(policy=E.T.POLICY,event_policy=E.T.EVENT_POLICY,level=levels.get(item['source_id'],'low'),
            proposed_level=levels.get(item['source_id'],'low'),category='product',form='event',
            low_by_rule=False,citations=deepcopy(item['citations']))
    return dict(packet=packet,result=result)


def dataset(levels=None,*,same_day=False,baseline=True):
    levels=levels or ['high']*7
    company=dict(instrument_id='company-1',symbol='EX',name='Example Company')
    sources={};frames=[];by_level={}
    def source(sid,at):
        title='Example Company announces service '+sid
        text='Example Company announced a service named '+sid+'.'
        passages,_=source_passages(title,text)
        return dict(id=sid,instrument_id=company['instrument_id'],label='pending',channel='news',title=title,text=text,
            passages=passages,content_hash=hashlib.sha256((title+text).encode()).hexdigest(),
            available_at=at.isoformat(),published_at=at.isoformat(),publisher='Authored example',url='https://example.test/'+sid)
    if baseline:sources['baseline']=source('baseline',START-timedelta(hours=1))
    for index,level in enumerate(levels):
        at=START+(timedelta(hours=1,minutes=index*15) if same_day else timedelta(hours=index*24+1))
        sid='source-'+str(index+1);sources[sid]=source(sid,at);by_level[sid]=level
        frames.append(dict(instrument_id=company['instrument_id'],symbol=company['symbol'],cutoff=at.isoformat(),
            initial_baseline=not baseline and index==0,source_ids=[sid],
            comparison_source_ids=[p for p,s in sources.items() if p!=sid and E.N.instant(s['published_at'])>=at-timedelta(days=7)]))
    capture=dict(policy='saved-news-noise-inputs-1',window_start=START.isoformat(),window_end=(START+timedelta(days=7)).isoformat(),
        companies=[company],sources=sources,frames=frames,baseline_counts={'EX':int(baseline)})
    capture['fingerprint']=E.N.digest(capture)
    evaluated=dict(input_fingerprint=capture['fingerprint'],baselines={},frames={})
    if baseline:
        evaluated['baselines']['company-1']=reading(capture,company,E.baseline_sources(capture,company),START,by_level)
    for frame in frames:
        selected=E.canonical_sources(capture,company,frame['source_ids']+frame['comparison_source_ids'])
        evaluated['frames'][E.frame_key(frame)]=reading(capture,company,selected,E.N.instant(frame['cutoff']),by_level)
    return capture,evaluated


def annotations(report,value='substantive'):
    return dict(report_fingerprint=report['fingerprint'],independent_excerpt_review=True,
        labels={sid:value for message in report['messages'] for event in message['shown'] for sid in event['source_ids']})


def test_seven_complete_days_use_real_routing_formatter_and_separate_independent_review():
    c,v=dataset();before=deepcopy((c,v));r=E.replay(c,v)
    assert r['completed_input_days']==7 and r['counts']['immediate']==7 and r['counts']['daily_recaps']==0
    assert r['noise_gate']=='pending_independent_review'
    assert r['paid_calls']==r['telegram_http_calls']==r['app_writes']==0
    assert all(E.M.visible_units(m['message'])<=3800 and 'Source excerpt' in m['message'] for m in r['messages'])
    assert before==(c,v) and E.audit(r,annotations(r))['passed']


def test_medium_uses_actual_daily_summary_and_low_remains_in_the_app():
    c,v=dataset(['medium','low','medium','low','medium','low','medium']);r=E.replay(c,v)
    assert r['counts']['immediate']==0 and r['counts']['daily_recaps']==4
    assert all(m['kind']=='digest' and 'Daily recap' in m['message'] for m in r['messages'])
    assert all('source-2' not in event['source_ids'] for m in r['messages'] for event in m['shown'])


@pytest.mark.parametrize('change',['missing_frame','missing_item','missing_importance','missing_baseline',
    'wrong_sample','future_source','forged_importance_quote','forged_source_url','missing_visible_source','wrong_policy'])
def test_missing_or_changed_evidence_is_never_treated_as_a_quiet_day(change):
    c,v=dataset();first=v['frames'][E.frame_key(c['frames'][0])]
    if change=='missing_frame':v['frames'].pop(E.frame_key(c['frames'][0]))
    elif change=='missing_item':first['result']['items'].pop()
    elif change=='missing_importance':next(i for i in first['result']['items'] if i['source_id']=='source-1').pop('importance')
    elif change=='missing_baseline':v['baselines'].clear()
    elif change=='wrong_sample':v['input_fingerprint']='different'
    elif change=='future_source':first['packet']['sources'][0]['available_at']=(START+timedelta(days=8)).isoformat()
    elif change=='forged_importance_quote':next(i for i in first['result']['items'] if i['source_id']=='source-1')['importance']['citations'][0]['quote']='Invented'
    elif change=='forged_source_url':first['packet']['sources'][0]['url']='https://example.test/forged'
    elif change=='missing_visible_source':
        first['packet']['sources']=[s for s in first['packet']['sources'] if s['id']!='baseline']
        first['result']['items']=[i for i in first['result']['items'] if i['source_id']!='baseline']
    else:first['packet']['guard_policy']='old-policy'
    with pytest.raises(ValueError):E.replay(c,v)


def test_no_baseline_first_sample_stays_quiet_without_losing_later_events():
    c,v=dataset(baseline=False);r=E.replay(c,v)
    assert r['counts']['immediate']==6
    assert all('source-1' not in event['source_ids'] for m in r['messages'] for event in m['shown'])


def test_no_messages_cannot_pass_noise_by_using_a_zero_denominator():
    c,v=dataset(['low']*7);r=E.replay(c,v);score=E.audit(r,annotations(r))
    assert r['counts']['messages']==0 and score['low_value_percent'] is None and not score['passed']


def test_only_one_day_of_frames_cannot_pass_the_seven_day_gate():
    c,v=dataset(['high']*3,same_day=True);r=E.replay(c,v)
    assert r['completed_input_days']==1 and not E.audit(r,annotations(r))['passed']


def test_recap_tail_follows_pending_news_to_the_next_0700_without_more_inputs():
    c,v=dataset(['medium']*7)
    # Move the final source to the final hour after the last in-window recap.
    last=c['frames'][-1];old=E.frame_key(last);at=START+timedelta(days=7,hours=-1)
    last['cutoff']=at.isoformat();source=c['sources']['source-7'];source.update(available_at=at.isoformat(),published_at=at.isoformat())
    c['fingerprint']=E.N.digest({k:x for k,x in c.items() if k!='fingerprint'});v['input_fingerprint']=c['fingerprint']
    company=c['companies'][0];v['frames'].pop(old)
    v['frames'][E.frame_key(last)]=reading(c,company,E.canonical_sources(c,company,last['source_ids']+last['comparison_source_ids']),at,{s:'medium' for s in c['sources']})
    r=E.replay(c,v)
    assert E.N.instant(r['digest_follow_through_until'])>E.N.instant(c['window_end'])
    assert r['messages'][-1]['at']==r['digest_follow_through_until']
    assert any('source-7' in e['source_ids'] for e in r['messages'][-1]['shown'])


def test_daily_recap_shows_at_most_five_members_and_claims_only_those_shown():
    c,v=dataset(['medium']*7,same_day=True);r=E.replay(c,v)
    assert r['counts']['daily_recaps']==1 and len(r['messages'][0]['shown'])==5
    assert '2 more saved updates' in r['messages'][0]['message']
    assert len(annotations(r)['labels'])==5


def test_shared_article_suppression_is_half_open_at_24_hours():
    c,v=dataset(['high']*7)
    # Change URLs in both frozen and evaluated sources without changing text.
    for source in c['sources'].values():source['url']='https://example.test/shared-article'
    for r in [*v['baselines'].values(),*v['frames'].values()]:
        for source in r['packet']['sources']:source['url']='https://example.test/shared-article'
    c['fingerprint']=E.N.digest({k:x for k,x in c.items() if k!='fingerprint'});v['input_fingerprint']=c['fingerprint']
    r=E.replay(c,v)
    # Exactly24h is outside the prior claim; all seven may be shown.
    assert r['counts']['immediate']==7
    frames=list(v['frames'].values());one=frames[0];record=E.publication(E.R.important_reporting(v['baselines']['company-1'],one)[0],one,'authored')
    at=E.N.instant(record['created_at']);source=next(s for s in one['packet']['sources'] if s['id']=='source-1')
    claims=[(at,E.G.source_keys(one,source,for_claim=True))]
    assert E.filtered(record,one,claims,at+timedelta(hours=23),immediate=True) is None
    assert E.filtered(record,one,claims,at+timedelta(hours=24),immediate=True)


def test_audit_is_bound_complete_independent_and_counts_any_low_evidence_in_a_message():
    c,v=dataset();r=E.replay(c,v)
    for change in ('fingerprint','missing','confirmation','category'):
        a=annotations(r)
        if change=='fingerprint':a['report_fingerprint']='different'
        elif change=='missing':a['labels'].pop(next(iter(a['labels'])))
        elif change=='confirmation':a['independent_excerpt_review']=False
        else:a['labels'][next(iter(a['labels']))]='invented'
        with pytest.raises(ValueError):E.audit(r,a)
    a=annotations(r);a['labels']['source-1']='comparison';score=E.audit(r,a)
    assert score['low_value_messages']==1 and not score['passed']
    r['counts']['messages']=0
    with pytest.raises(ValueError,match='changed'):E.audit(r,a)


def test_daily_message_exactly_matches_the_live_digest_formatter_for_the_same_members(monkeypatch):
    from thesis.monitoring import telegram as TG
    c,v=dataset(['medium']*7,same_day=True);r=E.replay(c,v)
    records={record['id']:dict(record,created_at=E.N.instant(record['created_at'])) for record in r['publications']}
    members=[dict(kind='company',event_id=record['id'],position=index) for index,record in enumerate(records.values())]
    at=E.N.instant(r['messages'][0]['at'])
    digest=dict(id='digest-id',preview=False,window_start=START,window_end=at,created_at=at,policy=E.DT.D.LIVE_POLICY)
    monkeypatch.setattr(E.DT,'one',lambda *args:digest)
    monkeypatch.setattr(E.DT,'rows',lambda *args:members)
    monkeypatch.setattr(TG,'event',lambda conn,owner,kind,identity:deepcopy(records[identity]))
    monkeypatch.setattr(E.G,'analysis_for',lambda conn,owner,record:v['frames'][record['analysis_index']])
    monkeypatch.setattr(E.G,'blockers',lambda *args:[])
    monkeypatch.setattr(E.G,'legacy_keys',lambda *args:set())
    actual=E.DT.digest_record(None,'authored-owner','digest-id',at,delivery_id='authored-delivery')
    assert actual['detail']['message']==r['messages'][0]['message']
    assert [m['member_position'] for m in actual['detail']['shown']]==list(range(5))


def test_json_round_trip_keeps_auditable_report_identity():
    import json
    c,v=dataset();r=E.replay(c,v)
    restored=json.loads(json.dumps(r))
    assert E.audit(restored,annotations(restored))['passed']
