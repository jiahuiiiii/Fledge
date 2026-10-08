#!/usr/bin/env python3
"""Explicit local reset with an archive. Stop the app before using --apply."""
import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from thesis.config import DATA, PG_BIN, dsn
from thesis.db import transaction
from thesis.workspace_reset import clear_research, tables, KEEP


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if not args.apply:
        print("Preview only: clears companies, source data, ideas, analyses, alerts, watches, valuations and history. Keeps API configuration, the public listing directory and ALL provider accounting. Stop the app and use --apply to back up and reset.")
        return
    # Refuse a concurrent application connection before taking the backup.
    with transaction(admin=True) as conn:
        active = conn.execute("SELECT count(*) AS n FROM pg_stat_activity WHERE datname=current_database() AND usename IN ('thesis_app','thesis_source')").fetchone()["n"]
        if active:
            raise SystemExit("Stop the local app before resetting the workspace.")
    folder = DATA / "backups" / ("fresh-workspace-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    folder.mkdir(parents=True, exist_ok=False, mode=0o700)
    archive = folder / "database.dump"
    subprocess.run([str(PG_BIN / "pg_dump"), "--dbname", dsn("thesis_local"), "--format=custom", "--file", str(archive)], check=True)
    archive.chmod(0o600)
    subprocess.run([str(PG_BIN / "pg_restore"), "--list", str(archive)], check=True, stdout=subprocess.DEVNULL)
    with transaction(admin=True) as conn:
        result = clear_research(conn)
    (folder / "reset-result.json").write_text(json.dumps(result, indent=2))
    print("Fresh workspace ready. Restart the app. Backup:", archive)


if __name__ == "__main__":
    main()
