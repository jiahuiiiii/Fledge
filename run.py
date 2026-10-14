#!/usr/bin/env python3
"""Start a private PostgreSQL cluster and the local Fledge app. No live APIs."""
import argparse
import os
from pathlib import Path
import socket
import subprocess
import sys
import webbrowser
import threading

ROOT = Path(__file__).resolve().parent


def database():
    from thesis.config import DATA, PG_BIN, dsn
    import psycopg

    DATA.mkdir(mode=0o700, parents=True, exist_ok=True)
    DATA.chmod(0o700)
    cluster = DATA / "postgres"
    sock = DATA / "socket"
    sock.mkdir(mode=0o700, exist_ok=True)
    if not (PG_BIN / "initdb").exists():
        raise SystemExit(
            "PostgreSQL 18 is required. Set THESIS_PG_BIN to its bin directory. See README.md."
        )
    if not (cluster / "PG_VERSION").exists():
        subprocess.run(
            [
                str(PG_BIN / "initdb"),
                "-D",
                str(cluster),
                "-U",
                "thesis_local",
                "--auth-local=trust",
                "--auth-host=reject",
                "--encoding=UTF8",
                "--locale=C",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
    active = (
        subprocess.run(
            [str(PG_BIN / "pg_ctl"), "-D", str(cluster), "status"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode
        == 0
    )
    if not active:
        # Unix socket only. The 0700 parent restricts access to this OS account.
        options = (
            f"-k {sock} -p 55439 -c listen_addresses='' -c unix_socket_permissions=0700"
        )
        subprocess.run(
            [
                str(PG_BIN / "pg_ctl"),
                "-D",
                str(cluster),
                "-l",
                str(DATA / "postgres.log"),
                "-o",
                options,
                "-w",
                "start",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
    with psycopg.connect(
        dsn("thesis_local").replace("dbname=thesis ", "dbname=postgres "),
        autocommit=True,
    ) as conn:
        if not conn.execute(
            "SELECT 1 FROM pg_database WHERE datname='thesis'"
        ).fetchone():
            conn.execute("CREATE DATABASE thesis")
    from thesis.migrations import apply_migrations

    with psycopg.connect(dsn("thesis_local")) as conn:
        apply_migrations(conn)
    from thesis.fixtures import seed

    seed()


def running(port):
    """Return 'fledge' if Fledge already serves the port, 'other' if something else does."""
    try:
        socket.create_connection(("127.0.0.1", port), timeout=1).close()
    except OSError:
        return None
    from urllib.request import urlopen

    try:
        with urlopen(f"http://127.0.0.1:{port}/", timeout=3) as response:
            return "fledge" if b"Fledge" in response.read(65536) else "other"
    except OSError:
        return "other"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--open", action="store_true")
    parser.add_argument("--port", type=int, default=8841)
    parser.add_argument("--init-only", action="store_true")
    parser.add_argument("--stop-db", action="store_true")
    args = parser.parse_args()
    if args.stop_db:
        from thesis.config import DATA, PG_BIN

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
        )
        return
    url = f"http://127.0.0.1:{args.port}"
    if not args.init_only:
        state = running(args.port)
        if state == "fledge":
            print(f"Fledge is already running at {url}")
            if args.open:
                webbrowser.open(url)
            return
        if state == "other":
            raise SystemExit(
                f"Port {args.port} is in use, but not by a working Fledge (another program, or an "
                f"older Fledge that stopped responding). Stop it (lsof -nP -iTCP:{args.port}) "
                "or start with --port <number>."
            )
    database()
    if args.init_only:
        print("Fledge database ready. Saved workspace preferences are preserved.")
        return
    if not (ROOT / "frontend/dist/index.html").exists():
        raise SystemExit(
            "Build the frontend first: cd frontend && npm ci && npm run build"
        )
    import uvicorn

    if args.open:
        threading.Timer(
            1.5, lambda: webbrowser.open(f"http://127.0.0.1:{args.port}")
        ).start()
    print(f"Fledge is available at http://127.0.0.1:{args.port} (local research workspace)")
    uvicorn.run("thesis.app:app", host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
