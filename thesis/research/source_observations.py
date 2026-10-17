"""Opt-in, append-only HTTP status observations for the lane rollout gates."""
from contextvars import ContextVar
from datetime import datetime, timezone
from functools import wraps
import os
from uuid import uuid4
from thesis.db import transaction

CHECK = ContextVar("source_check_id", default=None)


def enabled():
    from thesis.monitoring.watch_lanes import enabled as lanes_enabled
    if lanes_enabled():
        return True
    value = os.environ.get("THESIS_SOURCE_METRICS")
    if value is None and os.environ.get("THESIS_TEST_OFFLINE") != "true":
        from thesis.providers.settings import settings
        value = settings().get("THESIS_SOURCE_METRICS")
    return str(value or "false").lower() in {"true", "1", "on"}


def scoped(function):
    @wraps(function)
    def run(*args, **kwargs):
        token = CHECK.set(None)
        try:
            return function(*args, **kwargs)
        finally:
            CHECK.reset(token)
    return run


def record(provider, status):
    if not enabled():
        return
    with transaction(source=True) as conn:
        conn.execute("INSERT INTO source_request_events VALUES(%s,%s,%s,%s,%s)",
                     (uuid4(), CHECK.get(), provider, datetime.now(timezone.utc), status))
