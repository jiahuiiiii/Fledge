import os
import tempfile
import subprocess
from pathlib import Path
from uuid import uuid4
import pytest

# A separate disposable PostgreSQL cluster, never the user's app database.
os.environ["THESIS_DATA_DIR"] = tempfile.mkdtemp(
    prefix="thesis-test-", dir="/private/tmp"
)
from run import database
from thesis.config import DATA, PG_BIN
from thesis.db import transaction


@pytest.fixture(scope="session", autouse=True)
def db():
    try:
        database()
        yield
    finally:
        subprocess.run(
            [
                str(PG_BIN / "pg_ctl"),
                "-D",
                str(DATA / "postgres"),
                "-m",
                "fast",
                "stop",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )


@pytest.fixture
def owner(db):
    from thesis.fixtures import seed

    # Shared company evidence is reset between integration cases, inside this
    # disposable cluster only. Historical rows from other tests cannot leak in.
    with transaction(admin=True) as conn:
        conn.execute("TRUNCATE accounts,instruments,sources,demo_state,hn_withdrawals,social_withdrawals CASCADE")
        conn.execute("INSERT INTO demo_state VALUES(true,0)")
    seed()
    value = str(uuid4())
    with transaction(admin=True) as conn:
        conn.execute(
            "INSERT INTO accounts VALUES(%s,%s)", (value, "Fictional test account")
        )
    return value
