from pathlib import Path
from uuid import uuid4
import shutil
import psycopg
import pytest
from thesis import service
from thesis.db import transaction, one
from thesis.config import dsn, INSTRUMENT
from thesis.migrations import apply_migrations, DIRECTORY
from thesis.research.facts import fundamentals, resolve_fact, coverage
from test_integration import saved, drain


def test_committed_condition_membership_is_sealed(owner):
    version = saved(owner)["version_id"]
    drain(owner)
    before = service.state(owner)["versions"][0]["evaluations"][0]
    with pytest.raises(psycopg.errors.RaiseException, match="sealed"):
        with transaction(owner) as conn:
            conn.execute(
                "INSERT INTO version_conditions VALUES(%s,%s,%s,'revenue_growth','>=',3,'percent','reported','quarter')",
                (owner, version, uuid4()),
            )
    after = service.state(owner)["versions"][0]["evaluations"][0]
    assert before == after and len(after["results"]) == 2


def test_reclaimed_attempt_cannot_complete_or_fail_new_claim(owner):
    saved(owner)
    old = service.claim_job(owner)
    with transaction(owner) as conn:
        conn.execute(
            "UPDATE jobs SET lease_until=now()-interval '1 second' WHERE id=%s",
            (old["id"],),
        )
    current = service.claim_job(owner)
    assert old["claim_token"] != current["claim_token"]
    assert service.finish_job(owner, old) is False
    assert service.fail_job(owner, old) is False
    service.finish_job(owner, current)
    assert service.fail_job(owner, old) is False
    data = service.state(owner)
    assert (
        data["jobs"][0]["status"] == "done"
        and len(data["versions"][0]["evaluations"]) == 1
    )


def test_fundamental_selection_ignores_late_prior_period_and_abstains():
    base = dict(
        metric="revenue_growth",
        value="12",
        period="2025-Q3",
        basis="reported",
        unit="percent",
        available_at="2025-10-24",
        document_version_id="q3",
        id="1",
    )
    late = dict(
        base,
        period="2025-Q2",
        value="19",
        available_at="2025-10-28",
        document_version_id="q2-correction",
        id="2",
    )
    result = fundamentals([base, late], "2025-Q3")
    assert str(result[0]["value"]) == "12" and result[0]["document_version_id"] == "q3"
    assert (
        result[1]["status"] == "unavailable"
        and result[1]["document_version_id"] is None
    )
    conflicting = dict(base, id="3", value="14", document_version_id="other-q3")
    assert fundamentals([base, conflicting], "2025-Q3")[0]["status"] == "conflicting"
    assert (
        resolve_fact([base, conflicting], "revenue_growth", "2025-Q3")["observation"]
        is None
    )


def test_missing_source_checks_do_not_become_fresh():
    expected = {"company", "wire"}
    assert coverage([], expected) == "unknown"
    assert (
        coverage([dict(source_id="company", outcome="success")], expected) == "unknown"
    )
    assert (
        coverage([dict(source_id=s, outcome="success") for s in expected], expected)
        == "fresh"
    )
    assert coverage([dict(source_id="company", outcome="failed")], expected) == "stale"


@pytest.fixture
def legacy_database(db):
    name = "legacy_" + uuid4().hex
    with psycopg.connect(dsn("thesis_local"), autocommit=True) as conn:
        conn.execute(f"CREATE DATABASE {name}")
    target = dsn("thesis_local").replace("dbname=thesis ", f"dbname={name} ")
    with psycopg.connect(target) as conn:
        # This isolated database shares the test cluster's already-created login.
        original = (
            (DIRECTORY / "001_initial.sql")
            .read_text()
            .replace("CREATE ROLE thesis_app LOGIN NOSUPERUSER NOBYPASSRLS;", "")
        )
        conn.execute(original)
        owner, thesis, version, condition = [uuid4() for _ in range(4)]
        conn.execute(
            "INSERT INTO accounts VALUES(%s,%s)", (owner, "Legacy fictional owner")
        )
        conn.execute(
            "INSERT INTO instruments VALUES(%s,%s,%s)",
            (INSTRUMENT, "NSTR", "Northstar Software"),
        )
        conn.execute(
            "INSERT INTO theses(id,owner_id,instrument_id,revision,status) VALUES(%s,%s,%s,1,'draft')",
            (thesis, owner, INSTRUMENT),
        )
        conn.execute(
            "INSERT INTO thesis_versions(id,owner_id,thesis_id,revision,question,reasoning,status) VALUES(%s,%s,%s,1,'Legacy question','Original reasoning','draft')",
            (version, owner, thesis),
        )
        conn.execute(
            "INSERT INTO version_conditions VALUES(%s,%s,%s,'revenue_growth','>=',15,'percent','reported','quarter')",
            (owner, version, condition),
        )
        monitored, evaluation = uuid4(), uuid4()
        conn.execute(
            "UPDATE theses SET revision=2,status='monitoring' WHERE id=%s", (thesis,)
        )
        conn.execute(
            "INSERT INTO thesis_versions(id,owner_id,thesis_id,revision,question,reasoning,status) VALUES(%s,%s,%s,2,'Monitoring question','Original monitoring reasoning','monitoring')",
            (monitored, owner, thesis),
        )
        conn.execute(
            "INSERT INTO version_conditions VALUES(%s,%s,%s,'revenue_growth','>=',15,'percent','reported','quarter')",
            (owner, monitored, condition),
        )
        conn.execute(
            "INSERT INTO evaluations(id,owner_id,version_id,fingerprint,manifest,outcome,availability,freshness,disagreement) VALUES(%s,%s,%s,'legacy-assessment','{}','unknown','missing','unknown',false)",
            (evaluation, owner, monitored),
        )
        conn.execute(
            "INSERT INTO condition_results VALUES(%s,%s,%s,%s,'unknown',NULL,NULL,'No recorded matching observation')",
            (owner, evaluation, monitored, condition),
        )
        conn.execute(
            "INSERT INTO review_events(id,owner_id,evaluation_id,version_id,action) VALUES(%s,%s,%s,%s,'unresolved')",
            (uuid4(), owner, evaluation, monitored),
        )
        for state in ("pending", "running"):
            conn.execute(
                "INSERT INTO jobs(id,owner_id,version_id,fingerprint,manifest,status,attempts,lease_until) VALUES(%s,%s,%s,%s,'{}',%s,1,now()+interval '1 minute')",
                (uuid4(), owner, monitored, "legacy-" + state, state),
            )
    yield target, owner, version
    with psycopg.connect(dsn("thesis_local"), autocommit=True) as conn:
        conn.execute(f"DROP DATABASE {name}")


def test_populated_v1_upgrade_preserves_records_and_is_repeatable(legacy_database):
    target, owner, version = legacy_database
    with psycopg.connect(target) as conn:
        before = conn.execute(
            "SELECT id,question,reasoning,status FROM thesis_versions"
        ).fetchall()
        conditions = conn.execute("SELECT * FROM version_conditions").fetchall()
        workflow = {
            table: conn.execute(
                f"SELECT row_to_json(t)::text FROM {table} t ORDER BY 1"
            ).fetchall()
            for table in ("evaluations", "condition_results", "review_events")
        }
        jobs = conn.execute(
            "SELECT id,status,attempts,lease_until FROM jobs ORDER BY id"
        ).fetchall()
        assert apply_migrations(conn) == len(list(DIRECTORY.glob("*.sql")))
    with psycopg.connect(target) as conn:
        assert apply_migrations(conn) == len(list(DIRECTORY.glob("*.sql")))
        for table, records in workflow.items():
            assert (
                conn.execute(
                    f"SELECT row_to_json(t)::text FROM {table} t ORDER BY 1"
                ).fetchall()
                == records
            )
        assert (
            conn.execute(
                "SELECT id,status,attempts,lease_until FROM jobs ORDER BY id"
            ).fetchall()
            == jobs
        )
        assert (
            conn.execute(
                "SELECT id,question,reasoning,status FROM thesis_versions"
            ).fetchall()
            == before
        )
        upgraded = conn.execute("SELECT * FROM version_conditions").fetchall()
        assert [r[: len(conditions[0])] for r in upgraded] == conditions
        assert all(r[-4:] == (None, "required", None, None) for r in upgraded)
        assert conn.execute(
            "SELECT count(*) FROM schema_migrations WHERE checksum IS NOT NULL"
        ).fetchone()[0] == len(list(DIRECTORY.glob("*.sql")))
    with pytest.raises(psycopg.errors.RaiseException, match="sealed"):
        with psycopg.connect(
            target.replace("user=thesis_local", "user=thesis_app")
        ) as conn:
            conn.execute("SELECT set_config('app.user_id',%s,true)", (str(owner),))
            conn.execute(
                "INSERT INTO version_conditions VALUES(%s,%s,%s,'operating_margin','>=',10,'percent','reported','quarter')",
                (owner, version, uuid4()),
            )


def test_migration_checksum_and_failure_rollback(legacy_database, tmp_path):
    target, _, _ = legacy_database
    for path in DIRECTORY.glob("*.sql"):
        shutil.copy(path, tmp_path / path.name)
    with psycopg.connect(target) as conn:
        apply_migrations(conn)
    second = tmp_path / "002_revision_seals_and_worker_claims.sql"
    second.write_text(second.read_text() + "\n-- changed after application\n")
    with pytest.raises(ValueError, match="checksum"):
        with psycopg.connect(target) as conn:
            apply_migrations(conn, tmp_path)
    shutil.copy(DIRECTORY / second.name, second)
    (
        tmp_path / f"{len(list(DIRECTORY.glob('*.sql')))+1:03d}_rollback_probe.sql"
    ).write_text("CREATE TABLE must_rollback(id integer); SELECT 1/0;")
    with pytest.raises(psycopg.errors.DivisionByZero):
        with psycopg.connect(target) as conn:
            apply_migrations(conn, tmp_path)
    with psycopg.connect(target) as conn:
        assert conn.execute("SELECT to_regclass('must_rollback')").fetchone()[0] is None
        assert conn.execute("SELECT max(version) FROM schema_migrations").fetchone()[
            0
        ] == len(list(DIRECTORY.glob("*.sql")))


def test_migration_history_gap_is_rejected(legacy_database, tmp_path):
    target, _, _ = legacy_database
    for path in DIRECTORY.glob("*.sql"):
        shutil.copy(path, tmp_path / path.name)

    with psycopg.connect(target) as conn:
        conn.execute("INSERT INTO schema_migrations(version) VALUES(3)")
    with pytest.raises(ValueError, match="contiguous prefix"):
        with psycopg.connect(target) as conn:
            apply_migrations(conn, tmp_path)
    with psycopg.connect(target) as conn:
        assert conn.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).fetchall() == [(1,), (3,)]
