"""Run a reading's independent AI requests a few at a time.

Each request is already self-contained (whole sources, its own comparison
context, its own ledger reservation), so only the waiting is parallel; results
are combined in their original order afterwards. After the first failure, any
request that has not started yet is skipped rather than sent. Requests already
in flight finish and stay saved in the ledger for the next run.
"""
from concurrent.futures import ThreadPoolExecutor
import contextvars
import os
import threading

SKIPPED = object()
DEFAULT_LIMIT = 4
MAX_LIMIT = 8


def limit():
    """Requests of one reading allowed in flight at once (THESIS_AI_CONCURRENCY).

    Offline tests stay sequential unless they ask otherwise, so mocked
    transports see requests in a stable order.
    """
    offline = os.environ.get("THESIS_TEST_OFFLINE") == "true"
    value = os.environ.get("THESIS_AI_CONCURRENCY")
    if value is None and not offline:
        from thesis.providers.settings import settings
        value = settings().get("THESIS_AI_CONCURRENCY")
    try:
        n = int(value) if value else (1 if offline else DEFAULT_LIMIT)
    except ValueError:
        n = DEFAULT_LIMIT
    return max(1, min(MAX_LIMIT, n))


def run_all(tasks, workers=None):
    """Run zero-argument callables; return (results, errors) in task order.

    results[i] is the task's return value, or SKIPPED if it never started.
    errors maps a task index to the exception it raised.
    """
    workers = limit() if workers is None else max(1, workers)
    stop = threading.Event()
    results = [SKIPPED] * len(tasks)
    errors = {}

    def attempt(index, task):
        if stop.is_set():
            return
        try:
            results[index] = task()
        except BaseException as exc:  # noqa: BLE001 - reported to the caller in order
            errors[index] = exc
            stop.set()

    if workers == 1 or len(tasks) <= 1:
        for index, task in enumerate(tasks):
            attempt(index, task)
            if stop.is_set():
                break
    else:
        with ThreadPoolExecutor(max_workers=min(workers, len(tasks))) as pool:
            # Each task gets its own copy of the caller's context (e.g. the
            # signed-in account), which worker threads would not inherit.
            futures = [pool.submit(contextvars.copy_context().run, attempt, index, task)
                       for index, task in enumerate(tasks)]
            for future in futures:
                future.result()
    return results, errors
