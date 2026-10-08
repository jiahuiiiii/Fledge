from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
import json
import subprocess
import psycopg
import pytest
from psycopg.types.json import Jsonb
from fastapi.testclient import TestClient
from thesis import service
from thesis.config import OWNER, INSTRUMENT, dsn, DATA, PG_BIN
from thesis.db import transaction, one
from thesis.fixtures import ingest, uid
from thesis.models import SaveIdea, ResearchAction


def payload(revision=0, threshold="15", conditions=True, status="monitoring", ids=None):
    ids = ids or [str(uuid4()), str(uuid4())]
    return SaveIdea(
        expected_revision=revision,
        question="Can growth hold up?",
        reasoning="Demand may stay resilient; slower growth would challenge this idea.",
        status=status,
        conditions=(
            [
                dict(condition_id=ids[i], metric=metric, operator=">=", threshold=value)
                for i, (metric, value) in enumerate(
                    [("revenue_growth", threshold), ("operating_margin", "20")]
                )
            ]
            if conditions
            else []
        ),
    )


def saved(owner, **kw):
    return service.save_idea(owner, payload(**kw))


def drain(owner):
    while service.work_once(owner):
        pass


def test_draft_then_approval_complete_history_and_review(owner):
    saved(owner, status="draft", conditions=False)
    assert not service.state(owner)["jobs"]
    with pytest.raises(ValueError):
        saved(owner, revision=1, conditions=False)
    saved(owner, revision=1)
    drain(owner)
    data = service.state(owner)
    e = data["versions"][0]["evaluations"][0]
    assert e["outcome"] == "met" and len(e["results"]) == 2
    service.review(owner, e["id"], "reviewed")
    service.review(owner, e["id"], "unresolved")
    again = service.state(owner)["versions"][0]["evaluations"][0]
    assert again["review_action"] == "reviewed" and again["outcome"] == "met"
    assert len(data["versions"]) == 2


def test_concurrent_edits_only_one_commits(owner):
    saved(owner, status="draft", conditions=False)

    def edit():
        try:
            return saved(owner, revision=1)
        except service.Conflict:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: edit(), range(2)))
    assert results.count("conflict") == 1
    assert service.state(owner)["thesis"]["revision"] == 2


def test_restricted_role_and_connection_context(owner):
    saved(owner)
    with transaction(owner) as conn:
        role = one(
            conn,
            "SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user",
        )
        assert role == dict(rolsuper=False, rolbypassrls=False)
        assert one(conn, "SELECT count(*) n FROM theses")["n"] == 1
    with transaction() as conn:
        assert one(conn, "SELECT count(*) n FROM theses")["n"] == 0
    other = str(uuid4())
    with transaction(admin=True) as conn:
        conn.execute("INSERT INTO accounts VALUES(%s,%s)", (other, "Other test"))
    # Reusing one physical connection must not retain the previous account context.
    with psycopg.connect(dsn()) as conn:
        with conn.transaction():
            conn.execute("SELECT set_config('app.user_id',%s,true)", (owner,))
            assert conn.execute("SELECT count(*) FROM theses").fetchone()[0] == 1
        with conn.transaction():
            conn.execute("SELECT set_config('app.user_id',%s,true)", (other,))
            assert conn.execute("SELECT count(*) FROM theses").fetchone()[0] == 0
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with transaction(other) as conn:
            conn.execute(
                "INSERT INTO theses(id,owner_id,instrument_id,status) VALUES(%s,%s,%s,%s)",
                (uuid4(), owner, INSTRUMENT, "draft"),
            )
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with transaction(owner) as conn:
            conn.execute("UPDATE thesis_versions SET reasoning='changed'")
    with pytest.raises(psycopg.errors.RaiseException):
        with transaction(admin=True) as conn:
            conn.execute(
                "UPDATE thesis_versions SET reasoning='changed' WHERE owner_id=%s",
                (owner,),
            )


def test_incomplete_and_wrong_version_results_rejected(owner):
    v = saved(owner)["version_id"]
    with pytest.raises(psycopg.errors.RaiseException):
        with transaction(owner) as conn:
            conn.execute(
                "INSERT INTO evaluations(id,owner_id,version_id,fingerprint,manifest,outcome,availability,freshness,disagreement) VALUES(%s,%s,%s,%s,%s,'met','available','fresh',false)",
                (uuid4(), owner, v, "incomplete", Jsonb({})),
            )
    with transaction(owner) as conn:
        assert one(conn, "SELECT count(*) n FROM evaluations")["n"] == 0


def test_old_job_cannot_replace_edited_revision(owner):
    first = saved(owner)
    old = service.claim_job(owner)
    saved(owner, revision=1, threshold="25")
    new = service.claim_job(owner)
    service.finish_job(owner, new)
    service.finish_job(owner, old)
    service.finish_job(owner, old)
    versions = service.state(owner)["versions"]
    assert versions[0]["evaluations"][0]["outcome"] == "not_met"
    assert versions[1]["evaluations"][0]["outcome"] == "met"
    assert len(versions[1]["evaluations"]) == 1


def test_sources_cutoffs_outage_restatements_and_stable_identity(owner):
    ids = [str(uuid4()), str(uuid4())]
    saved(owner, ids=ids)
    drain(owner)
    service.advance(owner, 0)
    drain(owner)
    data = service.state(owner)
    assert len(data["documents"]) == 2 and len(data["observations"]) == 2
    assert data["versions"][0]["evaluations"][0]["outcome"] == "met"
    service.advance(owner, 1)
    drain(owner)
    q3 = service.state(owner)["versions"][0]["evaluations"][0]
    assert q3["outcome"] == "not_met"
    assert sorted(str(r["observed_value"]) for r in q3["results"]) == ["12", "22"]
    service.advance(owner, 2)
    drain(owner)
    stale = service.state(owner)["versions"][0]["evaluations"][0]
    assert stale["freshness"] == "stale" and stale["availability"] == "available"
    service.advance(owner, 3)
    drain(owner)
    versions = service.state(owner)["versions"]
    latest = versions[0]["evaluations"][0]
    assert sorted(str(r["observed_value"]) for r in latest["results"]) == ["13", "22"]
    assert q3["manifest"]["observation_ids"] != latest["manifest"]["observation_ids"]
    assert (
        next(e for e in versions[0]["evaluations"] if e["id"] == q3["id"])["results"]
        == q3["results"]
    )
    saved(owner, revision=1, threshold="12", ids=ids)
    drain(owner)
    now = service.state(owner)["versions"]
    assert (
        now[0]["evaluations"][0]["outcome"] == "met"
        and now[1]["evaluations"][0]["outcome"] == "not_met"
    )
    assert {str(c["condition_id"]) for c in now[0]["conditions"]} == set(ids)


def test_ingestion_and_queued_work_idempotent(owner):
    first = saved(owner)
    with transaction(admin=True) as conn:
        before = one(conn, "SELECT count(*) n FROM document_versions")["n"]
        ingest(conn, 0)
        ingest(conn, 0)
        assert one(conn, "SELECT count(*) n FROM document_versions")["n"] == before
    with transaction(owner) as conn:
        one_job = service.queue_version(conn, owner, first["version_id"])
        another = service.queue_version(conn, owner, first["version_id"])
        assert one_job["id"] == another["id"]
    drain(owner)
    assert len(service.state(owner)["versions"][0]["evaluations"]) == 1


def test_expired_lease_recovery_and_retry_bound(owner):
    saved(owner)
    claimed = service.claim_job(owner)
    with transaction(owner) as conn:
        conn.execute(
            "UPDATE jobs SET lease_until=now()-interval '1 second' WHERE id=%s",
            (claimed["id"],),
        )
    recovered = service.claim_job(owner)
    assert recovered["id"] == claimed["id"]
    service.finish_job(owner, recovered)
    saved(owner, revision=1)
    claimed = service.claim_job(owner)
    with transaction(owner) as conn:
        conn.execute(
            "UPDATE jobs SET attempts=3,lease_until=now()-interval '1 second' WHERE id=%s",
            (claimed["id"],),
        )
    assert service.claim_job(owner) is None
    assert service.state(owner)["jobs"][0]["status"] == "failed"


def test_future_inputs_and_wrong_sources_rejected(owner):
    saved(owner)
    job = service.claim_job(owner)
    with transaction(owner) as conn:
        manifest = job["manifest"]
        manifest["document_ids"].append(str(uuid4()))
        import hashlib

        fingerprint = hashlib.sha256(service.canonical(manifest).encode()).hexdigest()
        conn.execute(
            "UPDATE jobs SET manifest=%s,fingerprint=%s WHERE id=%s",
            (Jsonb(manifest), fingerprint, job["id"]),
        )
    with pytest.raises(ValueError, match="Source access"):
        service.finish_job(owner, job)


def test_api_local_session_csrf_and_strict_owner_schema(owner):
    from thesis.app import app

    with TestClient(app) as client:
        assert client.get("/api/v1/workspace").status_code == 401
        assert (
            client.get(
                "/api/v1/session", headers={"Origin": "https://evil.example"}
            ).status_code
            == 403
        )
        assert client.get("/api/v1/session").status_code == 200
        assert client.get("/api/v1/workspace").status_code == 200
        body = dict(question="Question", action="unresolved")
        assert client.post("/api/v1/research-actions", json=body).status_code == 403
        headers = {"X-Thesis-Request": "local-ui"}
        assert (
            client.post(
                "/api/v1/research-actions",
                headers=headers,
                json=body | {"owner_id": owner},
            ).status_code
            == 422
        )
        assert (
            client.post(
                "/api/v1/research-actions", headers=headers, json=body
            ).status_code
            == 200
        )
        assert (
            client.get(
                "/api/v1/workspace", headers={"Host": "evil.example"}
            ).status_code
            == 400
        )
        assert (
            client.get(
                "/api/v1/workspace", headers={"Sec-Fetch-Site": "cross-site"}
            ).status_code
            == 403
        )


def test_backup_restore_and_persistent_history(owner):
    saved(owner)
    drain(owner)
    dump = DATA / "backup.sql"
    base = [
        str(PG_BIN / "pg_dump"),
        "-h",
        str(DATA / "socket"),
        "-p",
        "55439",
        "-U",
        "thesis_local",
        "-d",
        "thesis",
        "-f",
        str(dump),
    ]
    subprocess.run(base, check=True)
    with psycopg.connect(dsn("thesis_local"), autocommit=True) as conn:
        conn.execute("CREATE DATABASE thesis_restored")
    subprocess.run(
        [
            str(PG_BIN / "psql"),
            "-h",
            str(DATA / "socket"),
            "-p",
            "55439",
            "-U",
            "thesis_local",
            "-d",
            "thesis_restored",
            "-v",
            "ON_ERROR_STOP=1",
            "-f",
            str(dump),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    with psycopg.connect(
        dsn().replace("dbname=thesis ", "dbname=thesis_restored ")
    ) as conn:
        conn.execute("SELECT set_config('app.user_id',%s,true)", (owner,))
        assert conn.execute("SELECT outcome FROM evaluations").fetchone()[0] == "met"
        assert conn.execute("SELECT count(*) FROM condition_results").fetchone()[0] == 2


def test_concurrent_review_requests_return_one_record(owner):
    saved(owner)
    drain(owner)
    evaluation = service.state(owner)["versions"][0]["evaluations"][0]
    with ThreadPoolExecutor(max_workers=2) as pool:
        reviews = list(
            pool.map(
                lambda action: service.review(owner, evaluation["id"], action),
                ["reviewed", "unresolved"],
            )
        )
    assert reviews[0]["id"] == reviews[1]["id"]
    with transaction(owner) as conn:
        assert one(conn, "SELECT count(*) n FROM review_events")["n"] == 1


def test_actual_database_restart_preserves_history_and_pending_work(owner):
    from run import database

    saved(owner)
    drain(owner)
    previous = service.state(owner)["versions"][0]["evaluations"][0]
    saved(owner, revision=1, threshold="25")
    subprocess.run(
        [str(PG_BIN / "pg_ctl"), "-D", str(DATA / "postgres"), "-m", "fast", "stop"],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    database()
    assert service.state(owner)["jobs"][0]["status"] == "pending"
    drain(owner)
    versions = service.state(owner)["versions"]
    assert versions[0]["evaluations"][0]["outcome"] == "not_met"
    assert versions[1]["evaluations"][0] == previous
