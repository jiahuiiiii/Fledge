"""Phase one: deterministic repairs, paid-retry boundaries and immutable reuse."""
from copy import deepcopy
import json
from unittest.mock import patch
from uuid import uuid4

import pytest

from thesis.db import one, transaction
from thesis.providers import ledger
from thesis.research import sentiment as S, sentiment_batching as B
from thesis.research import reporting_basis as R, sentiment_reliability as P, sentiment_reuse as U
from test_sentiment import provider
from test_sentiment_batching import packet
from test_model_budget import clean_model_ledger  # noqa: F401


def sample(n=8):
    p = packet()
    return B.part_for(p, p["sources"][:n])


def answer(p, mutate=lambda items: None):
    body = S.request_for(p)
    response = provider("neutral")(body)
    raw = json.loads(response["output"][0]["content"][0]["text"])
    mutate(raw["items"])
    response["output"][0]["content"][0]["text"] = json.dumps(raw)
    return dict(id=uuid4(), model=body["model"], request_body=body, response_body=response)


@pytest.mark.parametrize("fault,reason", [
    (dict(sentiment="positive"), "tone_basis_disagree"),
    (dict(relevance="unrelated", sentiment="negative", basis="stated_outcome"), "non_relevant_direction"),
    (dict(previous_passages=["p1"]), "previous_attitude_outside_relevant_social"),
    (dict(price_claims=[dict(passage_id="p1", amount_text="$42", kind="price_target", direction_text=None)]), "price_claims_on_news"),
    (dict(reporting=dict(kind="reported_event", passages=[], impact="adverse")), "event_fields_inconsistent"),
    (dict(reporting=dict(kind="opinion_only", passages=["p1"], impact="adverse")), "event_fields_inconsistent"),
    (dict(relevance="unclear", reporting=dict(kind="reported_event", passages=["p1"], impact="adverse")), "event_fields_inconsistent"),
])
def test_one_inconsistent_item_is_repaired_without_changing_the_raw_call(fault, reason):
    p = sample()
    call = answer(p, lambda items: items[0].update(fault))
    before = deepcopy(call)
    result = S.render(call, p)
    item = result["items"][0]
    assert call == before
    assert result["repairs"] == dict(policy=P.POLICY, repaired=1, total=8)
    assert reason in item["repair"]["reasons"]
    assert item["repair"]["original"] | fault == item["repair"]["original"]
    assert item["model"] == call["model"] and item["call_id"] == str(call["id"])
    if "reporting" in fault:
        assert not R.eligible(item) and not R.adverse(item)
        assert item["reporting_basis"]["citations"] == []
    if reason in {"non_relevant_direction", "tone_basis_disagree"}:
        assert item["sentiment"] == item["basis"] == "unclear"


def test_social_event_fields_and_nonrelevant_earlier_attitudes_are_removed():
    p = sample()
    p["sources"] = p["sources"][-2:]
    call = answer(p, lambda items: items[-1].update(
        relevance="unrelated", previous_passages=["p1"],
        reporting=dict(kind="reported_event", passages=["p1"], impact="adverse")))
    item = S.render(call, p)["items"][-1]
    assert set(item["repair"]["reasons"]) == {
        "non_relevant_direction", "reporting_on_social", "previous_attitude_outside_relevant_social"}
    assert "reporting_basis" not in item and item["previous_citations"] == []


@pytest.mark.parametrize("n,broken,passes", [(1,1,True),(3,1,True),(8,2,True),(8,3,False)])
def test_repair_cap_counts_items_once(n, broken, passes):
    p = sample(n)
    def mutate(items):
        for i in items[:broken]:
            i.update(sentiment="positive", previous_passages=["p1"])
    call = answer(p, mutate)
    if passes:
        assert S.render(call, p)["repairs"]["repaired"] == broken
    else:
        with pytest.raises(ValueError, match="Too many"):
            S.render(call, p)


@pytest.mark.parametrize("field,value", [
    ("passages",["invented"]), ("previous_passages",["invented"]),
    ("previous_passages",["p1","p1"]),
    ("reporting",dict(kind="opinion_only",passages=["invented"],impact="adverse")),
    ("price_claims",[dict(passage_id="invented",amount_text="$3",kind="other",direction_text=None)]),
    ("context_passages",["invented"]),
])
def test_foreign_or_duplicate_evidence_still_rejects_even_if_field_would_be_dropped(field,value):
    p = sample()
    with pytest.raises(ValueError):
        S.render(answer(p, lambda items: items[0].update({field:value})),p)


@pytest.mark.parametrize("fault", ["missing", "duplicate", "incomplete", "json", "missing_basis"])
def test_structural_errors_still_reject(fault):
    p = sample()
    call = answer(p)
    raw = json.loads(S.response_text(call))
    if fault == "missing": raw["items"].pop()
    if fault == "duplicate": raw["items"][1] = raw["items"][0]
    if fault == "missing_basis": raw["items"][0].pop("basis")
    call["response_body"]["output"][0]["content"][0]["text"] = "{" if fault == "json" else json.dumps(raw)
    if fault == "incomplete": call["response_body"]["status"] = "incomplete"
    with pytest.raises(ValueError): S.render(call,p)


def test_feature_rollback_rejects_old_consistency_error(monkeypatch):
    p = sample(); call = answer(p, lambda items: items[0].update(sentiment="positive"))
    monkeypatch.setenv("THESIS_SENTIMENT_RELIABILITY", "false")
    with pytest.raises(ValueError, match="disagree"): S.render(call,p)
    assert "repairs" not in S.render(answer(p),p)


def test_paid_failure_is_rechecked_for_free_with_original_ledger_row_preserved(owner, monkeypatch):
    p = sample(); call = answer(p, lambda items: items[0].update(sentiment="positive"))
    monkeypatch.setenv("THESIS_SENTIMENT_RELIABILITY", "false")
    with patch.object(B,"check_access"):
        with pytest.raises(ValueError): B.run(p,transport=lambda _: call["response_body"],prefilter=False)
        before = ledger.snapshot()
        with transaction() as c: saved = one(c,"SELECT * FROM model_calls WHERE request_key=%s",(B.part_identity(p),))
        monkeypatch.setenv("THESIS_SENTIMENT_RELIABILITY", "true")
        result, calls = B.run(p,transport=lambda _:pytest.fail("paid retry"),prefilter=False)
        assert result["repairs"]["repaired"] == 1 and calls[0]["id"] == saved["id"]
        assert result["items"][0]["call_id"] == str(saved["id"])
        with transaction() as c: assert one(c,"SELECT * FROM model_calls WHERE id=%s",(saved["id"],)) == saved
        assert ledger.snapshot() == before


def unfinished(body):
    r = provider()(body); r["status"] = "incomplete"; r["output"] = []
    return r


def test_two_terminal_half_batches_require_explicit_action_and_are_cached(owner):
    p = sample()
    with patch.object(B,"check_access"):
        for retry in (False,True):
            with pytest.raises(ValueError): B.run(p,transport=unfinished,retry_failed=retry,prefilter=False)
        assert ledger.snapshot()["calls"] == 2
        with pytest.raises(ValueError): B.run(p,transport=lambda _:pytest.fail("automatic split"),prefilter=False)
        sent=[]
        def send(body):
            sent.append(body)
            return provider("neutral")(body)
        result,calls=B.run(p,transport=send,retry_failed=True,split_failed=True,prefilter=False)
        assert [len(json.loads(b["input"][1]["content"])["sources"]) for b in sent] == [4,4]
        assert result["batching"]["split_batches"] == 2
        assert len(result["items"]) == 8 and len(calls) == 2
        snapshot=ledger.snapshot()
        again,_=B.run(p,transport=lambda _:pytest.fail("repeat split"),prefilter=False)
        assert again == result and snapshot == ledger.snapshot()


def test_failed_child_is_never_retried_or_split_again(owner):
    p=sample()
    with patch.object(B,"check_access"):
        for options in ({},{"retry_failed":True},{"split_failed":True}):
            with pytest.raises(ValueError): B.run(p,transport=unfinished,prefilter=False,**options)
        before=ledger.snapshot()
        with pytest.raises(ValueError): B.run(p,transport=lambda _:pytest.fail("child retry"),prefilter=False,retry_failed=True,split_failed=True)
        assert before == ledger.snapshot()


def test_uncertain_charge_is_not_automatically_redispatched(owner):
    p=sample()
    with patch.object(B,"check_access"):
        with pytest.raises(ledger.BudgetBlocked): B.run(p,transport=lambda _:(_ for _ in ()).throw(TimeoutError()),prefilter=False)
        before=ledger.snapshot()
        with pytest.raises(ledger.BudgetBlocked): B.run(p,transport=lambda _:pytest.fail("redispatch"),retry_failed=True,split_failed=True,prefilter=False)
        assert ledger.snapshot() == before


def test_carry_over_requires_matching_policies_and_whole_source_context(monkeypatch):
    p=sample(); result=S.render(answer(p),p)
    result["model"]="earlier-model"
    for item in result["items"]: item.pop("model")
    record=dict(id=str(uuid4()),call_id=str(uuid4()),packet=p,result=result)
    with patch.object(U,"rows",return_value=[record]):
        reused=U.find(None,p)
        assert len(reused) == 8
        assert all(s["item"]["model"] == "earlier-model" for s in reused.values())
        q=deepcopy(p); q["sources"][0]["thread_context_key"]="changed-context"
        assert len(U.find(None,q)) == 7
        for policy in ("reporting_policy","context_policy","reddit_thread_policy","guard_policy"):
            q=deepcopy(p);q[policy]="changed"
            assert not U.find(None,q)
        record["result"]["prompt_version"]="changed"
        assert not U.find(None,p)
        record["result"]["prompt_version"]=S.PROMPT
        monkeypatch.setenv("THESIS_SENTIMENT_RELIABILITY","false")
        assert not U.find(None,p)


def test_model_switch_sends_only_new_sources_and_preserves_each_original_model(owner):
    from test_sentiment_history import original, variant
    from test_market import commit, news
    iid, first = original(owner)
    def old_model(p, r):
        r["model"] = "earlier-model"
        for i in r["items"]:
            i["model"] = "earlier-model"
    variant(iid, first["id"], old_model)
    commit(iid,[news(id=2,url="https://example.test/second",headline="Microsoft reports an update",summary="Microsoft announced a new lab.")])
    sent=[]
    def transport(body):
        sent.append(body)
        return provider("neutral")(body)
    reading=S.generate(iid,transport=transport)
    assert len(sent) == 1
    assert len(json.loads(sent[0]["input"][1]["content"])["sources"]) == 1
    assert reading["source_reuse"]["reused"] == 2
    assert sum(i["model"] == "earlier-model" for i in reading["items"]) == 2
    assert sum(i["model"] == S.REASONING_MODEL for i in reading["items"]) == 1


def test_explicit_reread_bypasses_labels_and_paid_cache_but_same_run_is_idempotent(owner):
    from test_market import prepare
    iid=prepare(owner)
    first=S.generate(iid,transport=provider("neutral"))
    before=ledger.snapshot()["calls"]
    token=str(uuid4())
    second=S.generate(iid,transport=provider("negative"),reread_token=token)
    assert first["id"] != second["id"]
    assert ledger.snapshot()["calls"] == before + 1
    assert second["items"][0]["sentiment"] == "negative"
    assert S.generate(iid,reread_token=token,transport=lambda _:pytest.fail("duplicate explicit run"))["id"] == second["id"]
    assert S.generate(iid,transport=lambda _:pytest.fail("regular refresh discarded explicit re-read"))["id"] == second["id"]
    with transaction() as c:
        assert one(c,"SELECT result FROM sentiment_analyses WHERE id=%s",(first["id"],))["result"]["items"][0]["sentiment"] == "neutral"


def test_manual_recovery_options_are_durable_analysis_only_and_owner_scoped(owner):
    from thesis.research import loading
    from test_market import prepare
    from thesis.config import OWNER
    iid=prepare(owner)
    with pytest.raises(ValueError): loading.start(owner,iid,reread=True)
    with pytest.raises(ValueError): loading.start(owner,iid,analyze=True,reread=True,split_failed=True)
    run=loading.start(owner,iid,analyze=True,reread=True,lookback_days=30)
    assert len(run["steps"]) == 1 and run["steps"][0]["reread_token"] == str(run["id"])
    assert loading.latest(OWNER,iid) is None
    with patch.object(S,"generate",return_value={}) as generate:
        loading.execute(run,"analysis")
        assert generate.call_args.kwargs["reread_token"] == str(run["id"])
        assert generate.call_args.kwargs["retry_failed"] is True


def test_repaired_event_cannot_generate_an_adverse_alert():
    from thesis.monitoring.news_watch import changes
    p=sample()
    result=S.render(answer(p,lambda items:items[0].update(reporting=dict(kind="opinion_only",passages=["p1"],impact="adverse"))),p)
    result["batching"]={"policy":B.POLICY}
    prior=dict(packet=dict(p,sources=[]),result=dict(result,items=[]))
    assert changes(prior,dict(packet=p,result=result)) == []


def test_repair_totals_include_sources_skipped_by_the_quick_check():
    from thesis.research import relevance_prefilter
    p=sample()
    subset=dict(p,sources=p["sources"][:4])
    result=S.render(answer(subset,lambda items:items[0].update(sentiment="positive")),subset)
    result=relevance_prefilter.merge(p,result,dict(model="quick-model",call_ids=["authored-call"]))
    assert result["repairs"] == dict(policy=P.POLICY,repaired=1,total=8)
    assert all(i["model"] == "quick-model" for i in result["items"][4:])


def test_reused_quick_check_keeps_quick_model_and_calls_instead_of_bulk_call():
    from thesis.research import relevance_prefilter
    p=sample();result=S.render(answer(p),p)
    result["items"][0].update(prefilter=True)
    result["items"][0].pop("model"); result["items"][0].pop("call_id")
    result["prefilter"]=dict(policy=relevance_prefilter.POLICY,model="quick-model",call_ids=["quick-call"])
    record=dict(id=str(uuid4()),call_id="bulk-call",packet=p,result=result)
    with patch.object(U,"rows",return_value=[record]):
        saved=U.find(None,p)[p["sources"][0]["id"]]["item"]
    assert saved["model"] == "quick-model" and saved["call_ids"] == ["quick-call"]
    assert "call_id" not in saved


def test_cancelled_split_keeps_completed_child_and_requires_explicit_continuation(owner):
    p=sample()
    class Stopped(Exception):
        pass
    def progress(value):
        if value['completed'] == 1 and 'reading batch 2' in value['message']:
            raise Stopped()
    with patch.object(B,'check_access'):
        for retry in (False,True):
            with pytest.raises(ValueError): B.run(p,transport=unfinished,retry_failed=retry,prefilter=False)
        with pytest.raises(Stopped): B.run(p,transport=provider('neutral'),prefilter=False,split_failed=True,progress=progress)
        assert ledger.snapshot()['calls'] == 3
        with pytest.raises(ledger.BudgetBlocked,match='unfinished'):
            B.run(p,transport=lambda _:pytest.fail('automatic continuation'),prefilter=False)
        result,calls=B.run(p,transport=provider('neutral'),prefilter=False,split_failed=True)
        assert len(calls) == 2 and len(result['items']) == 8
        assert ledger.snapshot()['calls'] == 4


@pytest.mark.parametrize('prefilter',[False,True])
def test_stale_split_action_never_starts_a_fresh_paid_reading(owner,prefilter):
    with patch.object(B,'check_access'):
        with pytest.raises(ValueError):
            B.run(sample(),split_failed=True,prefilter=prefilter,transport=lambda _:pytest.fail('fresh paid work from stale recovery action'))
    assert ledger.snapshot()['calls'] == 0
