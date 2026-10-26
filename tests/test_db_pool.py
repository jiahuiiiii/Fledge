"""Kept database connections: reused, clean between owners, timed per request."""
import psycopg
import pytest
from thesis import db
from thesis.db import transaction, one


def counted(work):
    stats = dict(db_ms=0.0, db_open_ms=0.0, transactions=0, new_connections=0)
    token = db.request_stats.set(stats)
    try:
        work()
    finally:
        db.request_stats.reset(token)
    return stats


def test_connections_are_reused_and_owner_setting_does_not_leak(owner):
    db.reset_pool()

    def work():
        with transaction(owner) as conn:
            assert one(conn, "SELECT current_setting('app.user_id') v")["v"] == str(owner)
        with transaction() as conn:
            assert one(conn, "SELECT current_setting('app.user_id', true) v")["v"] in ("", None)
        with transaction(owner) as conn:
            one(conn, "SELECT 1")

    stats = counted(work)
    assert stats["transactions"] == 3
    assert stats["new_connections"] == 1


def test_failed_transaction_is_rolled_back_before_reuse(owner):
    db.reset_pool()
    with pytest.raises(psycopg.errors.UndefinedTable):
        with transaction(owner) as conn:
            conn.execute("SELECT * FROM no_such_table")
    with transaction(owner) as conn:
        assert one(conn, "SELECT 1 ok")["ok"] == 1
    with pytest.raises(RuntimeError):
        with transaction(admin=True) as conn:
            conn.execute("CREATE TEMP TABLE pool_probe(x int)")
            raise RuntimeError("stop")
    with transaction(admin=True) as conn:
        assert one(conn, "SELECT to_regclass('pg_temp.pool_probe') t")["t"] is None


def test_closed_kept_connection_is_replaced(owner):
    db.reset_pool()
    with transaction(owner) as conn:
        pid = one(conn, "SELECT pg_backend_pid() p")["p"]
    with transaction(admin=True) as conn:
        conn.execute("SELECT pg_terminate_backend(%s)", (pid,))
    with transaction(owner) as conn:
        assert one(conn, "SELECT pg_backend_pid() p")["p"] != pid


def test_api_answers_carry_server_timing():
    from fastapi.testclient import TestClient
    import thesis.app as module
    client = TestClient(module.app, base_url="http://127.0.0.1")
    header = client.get("/api/v1/session").headers["server-timing"]
    assert header.startswith("total;dur=") and "db;dur=" in header


def test_idle_worker_pass_skips_accounts_without_work(owner, monkeypatch):
    from thesis import service
    touched = []
    monkeypatch.setattr(service, "queue_current", lambda o: touched.append(("queue", o)))
    monkeypatch.setattr(service, "claim_job", lambda o: touched.append(("claim", o)))
    assert service.work_all(["00000000-0000-4000-8000-000000000999"]) is False
    assert touched == []
