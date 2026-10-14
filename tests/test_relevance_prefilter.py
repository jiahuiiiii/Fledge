"""Quick relevance check before the full reading. Mocked transport only."""
import json
from unittest.mock import patch
from uuid import uuid4
import pytest
from thesis.db import transaction, one
from thesis.providers import ledger
from thesis.research import relevance_prefilter as R, sentiment as S, sentiment_batching as B
from test_sentiment import provider, response
from test_sentiment_batching import packet
from test_model_budget import clean_model_ledger
from test_market import prepare
from thesis.research.citations import source_passages


def quick(labels=None, *, broken=False):
    """Answer the quick check with fixed labels; delegate full readings."""
    full = provider('neutral')
    seen = dict(quick=0, full=0, full_labels=[])

    def call(body):
        if body["text"]["format"]["name"] != "relevance_prefilter":
            seen["full"] += 1
            seen["full_labels"] += [s["label"] for s in json.loads(body["input"][1]["content"])["sources"]]
            return full(body)
        seen["quick"] += 1
        names = body["text"]["format"]["schema"]["properties"]["items"]["items"]["properties"]["label"]["enum"]
        items = [dict(label=n, relevance=(labels or {}).get(n, "relevant")) for n in names]
        text = "not json" if broken else json.dumps(dict(items=items))
        return response() | dict(model=body["model"], id="resp_" + str(uuid4()), output=[
            dict(type="message", content=[dict(type="output_text", text=text)])])
    return call, seen


def test_only_unrelated_is_skipped_and_stays_visible(owner):
    p = packet()
    first, second, third = (s["label"] for s in p["sources"][:3])
    transport, seen = quick({first: "unrelated", second: "unclear", third: "relevant"})
    with patch.object(B, "check_access"):
        result, calls = B.run(p, transport=transport, prefilter=True)
    assert first not in seen["full_labels"] and second in seen["full_labels"] and third in seen["full_labels"]
    assert len(result["items"]) == len(p["sources"])
    assert [i["source_id"] for i in result["items"]] == [s["id"] for s in p["sources"]]
    skipped = next(i for i in result["items"] if i["id"] == first)
    assert skipped["prefilter"] is True and skipped["relevance"] == "unrelated" and skipped["sentiment"] == "unclear"
    assert result["prefilter"]["skipped"] == 1 and result["prefilter"]["checked"] == len(p["sources"])
    assert len(calls) == seen["quick"] + seen["full"]
    # Recounted once over every source, so the skipped item is counted as not relevant.
    total = result["summary"]["news"]["selected"] + result["summary"]["social"]["selected"]
    assert total == len(p["sources"])


def test_unusable_quick_answer_skips_nothing(owner):
    p = packet()
    transport, seen = quick(broken=True)
    with patch.object(B, "check_access"):
        result, _ = B.run(p, transport=transport, prefilter=True)
    assert sorted(seen["full_labels"]) == sorted(s["label"] for s in p["sources"])
    assert result["prefilter"]["skipped"] == 0 and result["prefilter"]["usable_batches"] == 0
    assert not any(i.get("prefilter") for i in result["items"])


def test_all_skipped_makes_no_full_reading_call(owner):
    p = packet()
    transport, seen = quick({s["label"]: "unrelated" for s in p["sources"]})
    with patch.object(B, "check_access"):
        result, calls = B.run(p, transport=transport, prefilter=True)
    assert seen["full"] == 0 and len(calls) == seen["quick"] == 1
    assert all(i["prefilter"] for i in result["items"])
    assert result["summary"]["news"]["relevant"] == 0 and result["summary"]["news"]["tone"] == "thin sample"


def test_repeat_reuses_settled_quick_check_and_unknown_charge_blocks(owner):
    p = packet()
    transport, _ = quick({p["sources"][0]["label"]: "unrelated"})
    with patch.object(B, "check_access"):
        B.run(p, transport=transport, prefilter=True)
        result, _ = B.run(p, transport=lambda _: pytest.fail("duplicate call"), prefilter=True)
    assert result["prefilter"]["skipped"] == 1
    other = packet()
    other["sources"] = other["sources"][1:]

    def broken(body):
        raise TimeoutError()
    with patch.object(B, "check_access"):
        with pytest.raises(ledger.BudgetBlocked):
            B.run(other, transport=broken, prefilter=True)
        with pytest.raises(ledger.BudgetBlocked):
            B.run(other, transport=lambda _: pytest.fail("retry"), prefilter=True)


def leave_allowance(nano):
    """Represent earlier spending only in the disposable test ledger."""
    with transaction(admin=True) as c:
        cap = one(c, "SELECT cap_nano_usd FROM model_budget WHERE singleton")["cap_nano_usd"]
        spent = cap - nano
        c.execute(
            """INSERT INTO model_calls(id,request_key,request_hash,purpose,model,
            price_version,request_body,reserved_nano_usd,status,charged_nano_usd)
            VALUES(%s,%s,'test','test',%s,'test','{}',%s,'settled',%s)""",
            (uuid4(), 'earlier-spend-' + str(uuid4()), R.MODEL, spent, spent),
        )


@pytest.mark.parametrize("prefilter", [False, True])
def test_reading_can_finish_when_whole_plan_maximum_exceeds_allowance(owner, prefilter):
    p = packet()
    maxima = [ledger.estimate(S.request_for(part)) for part in B.plan(p)]
    remaining = max(maxima) + 1_000_000
    assert remaining < sum(maxima)
    leave_allowance(remaining)
    transport, seen = quick()
    with patch.object(B, "check_access"):
        result, calls = B.run(p, transport=transport, prefilter=prefilter)
    assert seen["quick"] == int(prefilter) and seen["full"] == len(maxima)
    assert len(result["items"]) == len(p["sources"])
    assert sum(c["charged_nano_usd"] for c in calls) < remaining
    assert float(ledger.snapshot()["remaining_usd"]) > 0


@pytest.mark.parametrize("prefilter", [False, True])
def test_reading_runs_past_the_old_allowance(owner, prefilter):
    # Owner removed the spending cap on 13 Oct 2026.
    p = packet()
    leave_allowance(1)
    normal, seen = quick()
    with patch.object(B, "check_access"):
        result, _ = B.run(p, transport=normal, prefilter=prefilter)
    assert len(result["items"]) == len(p["sources"])
    assert seen["quick"] == int(prefilter) and seen["full"] >= 1
    assert float(ledger.snapshot()["remaining_usd"]) < 0


def test_generate_saves_quick_check_and_reuses_earlier_full_reading(owner, monkeypatch):
    iid = prepare(owner)
    p = packet()
    p["instrument_id"] = iid
    with patch.object(S, "prepare", return_value=p), patch.object(B, "check_access"), \
         patch.object(S, "present", side_effect=lambda c, r: r):
        # A reading saved before this method exists: unchanged inputs reuse it.
        monkeypatch.setenv("THESIS_RELEVANCE_PREFILTER", "false")
        before = S.generate(iid, transport=provider("neutral"))
        monkeypatch.setenv("THESIS_RELEVANCE_PREFILTER", "true")
        again = S.generate(iid, transport=lambda _: pytest.fail("paid again"))
        assert again["id"] == before["id"]
    # Changed inputs get a new reading. Unchanged sources keep their saved
    # labels; only the changed source goes through the quick check.
    p2 = packet()
    p2["instrument_id"] = iid
    p2["sources"] = p2["sources"][1:]
    changed = p2["sources"][0]
    changed["text"] += " A later update says more."
    changed["passages"], _ = source_passages(changed["title"], changed["text"])
    with patch.object(S, "prepare", return_value=p2), patch.object(B, "check_access"), \
         patch.object(S, "present", side_effect=lambda c, r: r):
        transport, seen = quick({changed["label"]: "unrelated"})
        row = S.generate(iid, transport=transport)
    assert row["request_key"].endswith(":" + R.POLICY)
    assert row["result"]["prefilter"]["skipped"] == 1
    assert row["result"]["source_reuse"]["reused"] == len(p2["sources"]) - 1
    assert seen == dict(quick=1, full=0, full_labels=[])
    assert len(row["packet"]["batching"]["call_ids"]) == 1
    with transaction() as c:
        assert one(c, "SELECT count(*) n FROM model_calls WHERE purpose=%s", ("sentiment:" + R.POLICY,))["n"] == 1


def test_offline_tests_keep_single_stage_unless_asked(monkeypatch):
    monkeypatch.delenv("THESIS_RELEVANCE_PREFILTER", raising=False)
    monkeypatch.setenv("THESIS_TEST_OFFLINE", "true")
    assert R.enabled() is False
    monkeypatch.setenv("THESIS_TEST_OFFLINE", "false")
    assert R.enabled() is True
    monkeypatch.setenv("THESIS_RELEVANCE_PREFILTER", "false")
    assert R.enabled() is False
