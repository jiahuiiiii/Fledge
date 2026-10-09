"""Batches use mocked transport and the disposable original-ledger implementation."""
from copy import deepcopy
from unittest.mock import patch
import json
import pytest
from thesis.db import transaction, one
from thesis.providers import ledger
from thesis.research import sentiment as S, sentiment_batching as B, loading
from thesis.monitoring import news_watch
from experiments.sentiment_batching.controls import packet as controls
from test_sentiment import provider
from test_model_budget import clean_model_ledger
from test_market import prepare


def packet():
    p = controls()
    # These are transport/storage controls, not semantic model labels.
    for s in p['sources']:
        s.pop('conversation', None)
    return p


def test_plan_preserves_sources_context_and_all_news():
    p = controls(); old = deepcopy(p)
    parts = B.plan(p)
    assert [s for part in parts for s in part['sources']] == p['sources']
    assert p == old and [len(part['sources']) for part in parts] == [8,4]
    for part in parts:
        assert {s['id'] for s in part['sources'] + part['comparison_sources'] if s['channel']=='news'} == {s['id'] for s in p['sources'] if s['channel']=='news'}
        assert len(ledger.canonical(S.request_for(part)).encode()) <= B.MAX_BYTES


def test_size_limit_splits_before_count_limit_without_truncating():
    p=packet()
    size=lambda n:len(ledger.canonical(S.request_for(B.part_for(p,p['sources'][:n]))).encode())
    bound=size(4)
    assert size(8)>bound
    parts=B.plan(p,max_bytes=bound)
    assert len(parts)>2
    assert [s for part in parts for s in part['sources']]==p['sources']
    assert all(len(ledger.canonical(S.request_for(part)).encode())<=bound for part in parts)


def test_oversized_indivisible_context_blocks_before_any_dispatch():
    with patch.object(ledger,'execute') as execute:
        with pytest.raises(ValueError, match='No batch was sent'):
            B.plan(packet(),max_bytes=10)
        execute.assert_not_called()


def test_reporting_schema_only_allows_own_passage_ids():
    p=packet(); body=S.request_for(p)
    branches=body['text']['format']['schema']['properties']['items']['items']['anyOf']
    for source,branch in zip(p['sources'],branches):
        if source['channel']=='news':
            allowed=branch['properties']['reporting']['properties']['passages']['items']['enum']
            assert allowed==[v['id'] for v in source['passages']]
            assert not set(allowed)&{v['quote'] for v in source['passages']}
        else: assert 'reporting' not in branch['properties']


def test_partial_failure_saves_valid_batch_and_explicit_retry_only_resends_failed(owner):
    p=packet(); good=provider('neutral'); seen=[]; progress=[]
    def transport(body):
        seen.append(body)
        response=good(body)
        if len(seen)==2:response['status']='incomplete';response['output']=[]
        return response
    with patch.object(B,'check_access'):
        with pytest.raises(ValueError,match='Batch 2'):
            B.run(p,transport=transport,progress=progress.append)
        assert len(seen)==2 and progress[-1]['completed']==1
        with pytest.raises(ValueError,match='saved batch'):
            B.run(p,transport=lambda _:pytest.fail('automatic retry'))
        result,calls=B.run(p,transport=good,retry_failed=True,progress=progress.append)
        assert len(result['items'])==12 and result['batching']['completed']==2
        assert ledger.snapshot()['calls']==3
        result2,calls2=B.run(p,transport=lambda _:pytest.fail('duplicate call'),retry_failed=True)
        assert [c['id'] for c in calls]==[c['id'] for c in calls2]
        assert result2==result


def test_unknown_charge_cannot_be_retried_even_explicitly(owner):
    p=packet()
    def broken(body):raise TimeoutError()
    with patch.object(B,'check_access'):
        with pytest.raises(ledger.BudgetBlocked):B.run(p,transport=broken)
        with pytest.raises(ledger.BudgetBlocked):B.run(p,transport=lambda _:pytest.fail('retry'),retry_failed=True)
    assert ledger.snapshot()['calls']==1


def test_only_one_explicit_retry_of_settled_invalid_batch(owner):
    p=packet()
    def incomplete(body):
        r=provider()(body);r['status']='incomplete';r['output']=[];return r
    with patch.object(B,'check_access'):
        for explicit in (False,True,True):
            with pytest.raises(ValueError):B.run(p,transport=incomplete,retry_failed=explicit)
    assert ledger.snapshot()['calls']==2


def test_source_access_rechecked_between_calls_and_before_merge(owner):
    for fail_at,expected_calls in [(2,1),(3,2)]:
        # Fresh immutable wording for each subcase gives separate ledger keys.
        p=packet();p['sources'][0]['publisher']+=str(fail_at)
        states=[None]*(fail_at-1)+[ValueError('withdrawn')]
        before=ledger.snapshot()['calls']
        with patch.object(B,'check_access',side_effect=states):
            with pytest.raises(ValueError,match='withdrawn'):B.run(p,transport=provider('neutral'))
        assert ledger.snapshot()['calls']-before==expected_calls


def test_global_result_revalidates_cross_batch_constraints(owner):
    p=packet(); parts=B.plan(p)
    good=provider('neutral')
    calls=[{'response_body':good(S.request_for(part))} for part in parts]
    with patch.object(S,'render',side_effect=[{}, {}, ValueError('cross-batch inconsistency')]) as render:
        with pytest.raises(ValueError,match='cross-batch'):B.combine(p,parts,calls)
        assert render.call_count==3
    with pytest.raises(ValueError,match='All sentiment batches'):B.combine(p,parts,calls[:-1])


def test_failed_whole_analysis_is_not_saved(owner):
    iid=prepare(owner)
    p=packet();p['instrument_id']=iid
    def incomplete(body):
        r=provider()(body);r['status']='incomplete';return r
    with patch.object(S,'prepare',return_value=p),patch.object(B,'check_access'):
        with pytest.raises(ValueError):S.generate(iid,transport=incomplete)
    with transaction() as c:
        assert one(c,'SELECT count(*) n FROM sentiment_analyses')['n']==0


def test_company_lock_fences_concurrent_generation(owner):
    iid=prepare(owner)
    with B.company_lock(iid):
        with pytest.raises(ValueError,match='already running'):
            S.generate(iid,transport=lambda _:pytest.fail('concurrent dispatch'))


def test_progress_persists_counts_but_rejects_late_worker(owner):
    iid=prepare(owner);loading.start(owner,iid,analyze=True)
    for _ in range(6):loading.work_once(owner,lambda *_:{})
    run,index=loading.claim(owner)
    progress=dict(completed=1,total=2,source_counts=[8,4],failed=None,message='1 of 2 batches complete')
    loading.analysis_progress(run,progress)
    assert loading.latest(owner,iid)['steps'][index]['batches']==progress
    loading.recover(owner)
    with pytest.raises(ValueError,match='no longer active'):loading.analysis_progress(run,progress)


def test_method_change_cannot_publish_sentiment_or_news_alert():
    old={'result':{'prompt_version':'earlier','batching':{}},'packet':{'sources':[]}}
    current={'result':{'prompt_version':S.PROMPT,'batching':{'policy':B.POLICY}},'packet':{'sources':[]}}
    assert news_watch.changes(old,current)==[]


def test_cancelled_watch_stops_before_the_next_batch(owner):
    active=True
    def transport(body):
        nonlocal active
        active=False
        return provider('neutral')(body)
    def progress(_):
        if not active:raise news_watch.WatchStopped()
    with patch.object(B,'check_access'):
        with pytest.raises(news_watch.WatchStopped):B.run(packet(),transport=transport,progress=progress)
    assert ledger.snapshot()['calls']==1
