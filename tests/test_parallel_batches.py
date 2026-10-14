"""Parallel sentiment batches: same requests and results, bounded concurrency,
and the same saved-work rules when a batch fails. Mocked transport only."""
import threading
import time
from unittest.mock import patch
import pytest
from thesis.providers import ledger
from thesis.research import parallel, sentiment as S, sentiment_batching as B
from test_sentiment import provider
from test_sentiment_batching import packet
from test_model_budget import clean_model_ledger  # noqa: F401  (autouse ledger reset)


def single_source_parts(p):
    return [B.part_for(p, [s]) for s in p["sources"]]


def test_limit_setting(monkeypatch):
    monkeypatch.delenv("THESIS_AI_CONCURRENCY", raising=False)
    assert parallel.limit() == 1  # offline tests stay sequential by default
    monkeypatch.setenv("THESIS_AI_CONCURRENCY", "4")
    assert parallel.limit() == 4
    monkeypatch.setenv("THESIS_AI_CONCURRENCY", "99")
    assert parallel.limit() == parallel.MAX_LIMIT
    monkeypatch.setenv("THESIS_AI_CONCURRENCY", "0")
    assert parallel.limit() == 1


def test_run_all_skips_unstarted_work_after_a_failure():
    started = []

    def task(n):
        def go():
            started.append(n)
            if n == 1:
                raise RuntimeError("boom")
            return n
        return go

    results, errors = parallel.run_all([task(n) for n in range(5)], workers=1)
    assert started == [0, 1] and list(errors) == [1]
    assert results[0] == 0 and all(r is parallel.SKIPPED for r in results[1:])


def test_batches_run_in_parallel_with_the_same_requests_and_result(owner, monkeypatch):
    p = packet(); good = provider("neutral"); parts = single_source_parts(p)
    lock = threading.Lock(); active = [0]; peak = [0]; bodies = []

    def slow(body):
        with lock:
            active[0] += 1; peak[0] = max(peak[0], active[0]); bodies.append(body)
        time.sleep(0.05)
        with lock:
            active[0] -= 1
        return good(body)

    monkeypatch.setenv("THESIS_AI_CONCURRENCY", "4")
    progress = []
    with patch.object(B, "plan", return_value=parts), patch.object(B, "check_access"):
        result, calls = B.run(p, transport=slow, progress=progress.append)
    assert 1 < peak[0] <= 4
    # Every batch sent exactly once, and calls are returned in batch order.
    assert sorted(ledger.canonical(b) for b in bodies) == sorted(ledger.canonical(S.request_for(x)) for x in parts)
    assert [c["request_body"] for c in calls] == [S.request_for(x) for x in parts]
    assert result["batching"]["completed"] == len(parts) and progress[-1]["completed"] == len(parts)
    # A sequential rerun reuses every saved batch and reads the same result.
    monkeypatch.setenv("THESIS_AI_CONCURRENCY", "1")
    with patch.object(B, "plan", return_value=parts), patch.object(B, "check_access"):
        again, _ = B.run(p, transport=lambda _: pytest.fail("a saved batch was sent again"))
    assert again["items"] == result["items"] and again["summary"] == result["summary"]


def test_parallel_failure_keeps_in_flight_work_and_skips_unstarted_batches(owner, monkeypatch):
    p = packet(); good = provider("neutral"); parts = single_source_parts(p)
    failing = ledger.canonical(S.request_for(parts[1]))
    sent = []

    def transport(body):
        sent.append(body)
        response = good(body)
        if ledger.canonical(body) == failing:
            response["status"] = "incomplete"; response["output"] = []
            return response
        time.sleep(0.1)  # the other batches in flight finish after the failure
        return response

    monkeypatch.setenv("THESIS_AI_CONCURRENCY", "4")
    with patch.object(B, "plan", return_value=parts), patch.object(B, "check_access"):
        with pytest.raises(ValueError, match=r"Batch 2 of 12 stopped.*3 completed batches are saved\. 8 later batches were not sent"):
            B.run(p, transport=transport)
        assert len(sent) == 4
        # The explicit retry resends only the failed batch and the unsent ones.
        sent.clear()
        result, _ = B.run(p, transport=lambda body: (sent.append(body), good(body))[1], retry_failed=True)
    assert len(sent) == 9 and result["batching"]["completed"] == 12


def test_a_stopped_watch_ends_parallel_work_with_its_own_error(owner, monkeypatch):
    p = packet(); good = provider("neutral"); parts = single_source_parts(p)

    class Stopped(Exception):
        pass

    def progress(value):
        if "reading batch 6" in value["message"]:
            raise Stopped()

    monkeypatch.setenv("THESIS_AI_CONCURRENCY", "4")
    with patch.object(B, "plan", return_value=parts), patch.object(B, "check_access"):
        with pytest.raises(Stopped):
            B.run(p, transport=good, progress=progress)
