"""Explicit investment wrappers and mixed recaps use no paid/source requests."""
from copy import deepcopy
from datetime import datetime,timezone
from uuid import uuid4
import pytest
from thesis.research import sentiment_tasks as T,sentiment_task_runner as RUN
from thesis.monitoring import alert_routing as R,telegram_stories as G,daily_telegram as DT
from experiments.soclaas_replay import news_noise_replay as E
from test_news_coverage import source,analyse
from test_alert_routing import scored


@pytest.mark.parametrize('title',[
    'Is Example Stock Cheap After Its New Product Launch?',
    'Example Could Be 25% Undervalued After AI Gains Traction',
    'Does New Model Launch Change The Bull Case For Example Stock?',
    'Example Has A Cloud Customer. Why Is It Still Priced Like A Phone Stock?',
    "Example Reports Tomorrow. I'd Consider Buying the Stock Before It Does.",
    "Example Is Financing Two Labs. Here's What It Means for Investors.",
    'Example Gets Bullish Call: Why The Analyst Sees 25% Upside',
    'How A Legal Win Could Reshape The Long-Term Thesis For Investors',
    'Example vs Rival: Which Stock Is The Better Buy?',
    'Three AI Stocks to Watch After New Research Funding',
    'Should You Buy Example Stock After Its $2 Billion Buyback?',
    'Example Stock Could Be Undervalued After Its Board Approves A Buyback',
    'Is Example (EX) Cheap Following Its New Product Launch?',
    'Example Stock Looks Cheap After Its Dividend Increase',
])
def test_clear_editorial_wrappers_are_low_despite_factual_background(title):
    assert T.editorial_headline(title)
    s=source('item_1','Example announced a real operating agreement.');s['title']=title
    reading=analyse([s],[]);item=scored(reading['result']['items'][0])
    record=dict(kind='company',detail=dict(payload=dict(items=[item]),sources=[s]))
    assert R.importance(item,s)=='low' and R.classify(record)['channel']=='app'
    reading['result']['items']=[item]
    assert not R.important_reporting(dict(packet=dict(sources=[])),reading)


@pytest.mark.parametrize('title',[
    'Jury Rules For Example vs Rival In A Licensing Dispute',
    'Example vs Rival: Court Awards Damages As Shares Fall',
    'Example Introduces A Cheap New AI Device',
    'Example Weighs Buying A Model Startup',
    'Why Is Example Recalling Its New Device?',
    'Example CEO Raises Revenue Guidance And Criticises AI Investors',
    'Example Announces A New Product At An Investor Event',
    'Example Board Approves $2 Billion Buyback; CEO Says Shares Are Undervalued',
    'Example Raises Dividend After Analysts Call Shares Undervalued',
    'Example Launches A Cheap New AI Device; Shares Rise',
    'Example CEO Says Shares Are Undervalued',
    'Example Introduces An Expensive New Device As Shares Fall',
])
def test_real_or_uncertain_developments_are_not_rejected_by_keyword_alone(title):
    assert not T.editorial_headline(title)
    s=source('item_1','Example announced its new company development.');s['title']=title
    reading=analyse([s],[]);item=scored(reading['result']['items'][0])
    record=dict(kind='company',detail=dict(payload=dict(items=[item]),sources=[s]))
    assert R.importance(item,s)=='high' and R.classify(record)['channel']=='telegram'


def fixture(monkeypatch,*,low_level='low',editorial=False):
    sources=[source('item_1','First company announcement.'),source('item_2','Second company announcement.',1)]
    if editorial:sources[0]['title']='Is Example Stock Undervalued After Its Product Launch?'
    reading=analyse(sources,[])
    reading['result']['items']=[scored(i,low_level if n==0 else 'medium') for n,i in enumerate(reading['result']['items'])]
    record=dict(id=str(uuid4()),kind='company',title='New company developments',
        detail=dict(symbol='MSFT',preview=False,withheld=False,sources=sources,
                    payload=dict(kind='important_reporting',items=deepcopy(reading['result']['items']))))
    monkeypatch.setattr(G,'analysis_for',lambda *a:reading)
    monkeypatch.setattr(G,'blockers',lambda *a:[])
    monkeypatch.setattr(G,'legacy_keys',lambda *a:set())
    return reading,record


@pytest.mark.parametrize('editorial',[False,True])
def test_daily_send_and_replay_drop_low_companions_before_formatting_and_claiming(monkeypatch,editorial):
    reading,record=fixture(monkeypatch,low_level='high' if editorial else 'low',editorial=editorial)
    now=datetime.now(timezone.utc)
    kept=G.prepare(None,None,record,uuid4(),now,force=True)
    assert [i['source_id'] for i in kept['detail']['payload']['items']]==['item_2']
    shown=[];assert DT.summary(kept,1,shown=shown)
    assert shown==['item_2'] and G.shown_keys(kept,shown)==G.source_keys(reading,reading['packet']['sources'][1],for_claim=True)
    replay=E.filtered(record,reading,[],now)
    assert replay and replay[0]['detail']['payload']['items']==kept['detail']['payload']['items']
    assert len(record['detail']['payload']['items'])==2


def test_all_low_recaps_are_suppressed_but_old_unscored_non_editorial_evidence_is_retained(monkeypatch):
    reading,record=fixture(monkeypatch)
    reading['result']['items'][1]['importance']['level']='low'
    with pytest.raises(G.Suppressed,match='qualifying'):G.prepare(None,None,record,uuid4(),datetime.now(timezone.utc),force=True)
    for i in reading['result']['items']:i.pop('importance')
    kept=G.prepare(None,None,record,uuid4(),datetime.now(timezone.utc),force=True)
    assert len(kept['detail']['payload']['items'])==2


def test_guard_version_changes_reading_identity_without_changing_paid_request_body(monkeypatch):
    from test_sentiment_tasks import packet
    p=packet();body=T.request_for('event',p);key=RUN.identity(p)
    monkeypatch.setattr(T,'HEADLINE_POLICY','authored-next-guard')
    assert RUN.identity(p)!=key and T.request_for('event',p)==body


def test_carried_importance_is_demoted_without_repaying_or_mutating_saved_labels(monkeypatch):
    from test_sentiment_tasks import packet
    from test_sentiment_task_runner import provider,reuse
    from thesis.research import sentiment_batching as B
    p=packet();monkeypatch.setattr(B,'check_access',lambda *a:None)
    p['sources'][0]['title']='Is Example Stock Undervalued After Its New Product?'
    guard=T.editorial_headline
    monkeypatch.setattr(T,'editorial_headline',lambda title:False)
    original=RUN.run(p,transport=provider([]),prefilter=False)[0]
    monkeypatch.setattr(T,'editorial_headline',guard)
    before=deepcopy(original);saved=reuse(original)
    result,calls=RUN.run(p,saved,transport=lambda *a:pytest.fail('Unchanged evidence was repaid'),prefilter=False)
    assert not calls and original==before
    assert result['items'][0]['importance']['level']=='low'
    assert result['items'][0]['importance']['headline_policy']==T.HEADLINE_POLICY
    assert result['items'][0]['sentiment']==original['items'][0]['sentiment']


def test_news_headline_guard_does_not_remove_unscored_private_discussion_matches(monkeypatch):
    reading,record=fixture(monkeypatch,editorial=True)
    for s in reading['packet']['sources']:s['channel']='social'
    for i in reading['result']['items']:i['channel']='social';i.pop('importance')
    record['detail']['payload']['items']=deepcopy(reading['result']['items'])
    assert R.classify(record)['channel']=='digest'
    kept=G.prepare(None,None,record,uuid4(),datetime.now(timezone.utc),force=True)
    assert len(kept['detail']['payload']['items'])==2


def test_prior_event_interpretation_is_rechecked_while_unchanged_tones_stay_saved(monkeypatch):
    from test_sentiment_tasks import packet
    from test_sentiment_task_runner import provider,reuse
    from thesis.research import sentiment_batching as B
    p=packet();monkeypatch.setattr(B,'check_access',lambda *a:None)
    with monkeypatch.context() as prior:
        prior.setattr(T,'EVENT_POLICY','authored-prior-purpose')
        prior.setattr(T,'EVENT_INSTRUCTION',T.EVENT_INSTRUCTION+'\nAuthored prior instruction.')
        prior.setitem(T.INSTRUCTIONS,'event',T.EVENT_INSTRUCTION)
        original=RUN.run(p,transport=provider([]),prefilter=False)[0]
    old=deepcopy(original)
    seen=[];result,calls=RUN.run(p,reuse(old),transport=provider(seen),prefilter=False)
    assert seen==['event'] and len(calls)==1
    assert [i['sentiment'] for i in result['items']]==[i['sentiment'] for i in old['items']]
    assert all(i['importance']['event_policy']==T.EVENT_POLICY for i in result['items'] if i.get('importance'))
