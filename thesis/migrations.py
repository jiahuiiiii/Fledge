"""Ordered, checksummed upgrades under one transaction and database lock."""

from hashlib import sha256
from pathlib import Path

DIRECTORY = Path(__file__).resolve().parents[1] / "migrations"
# Set from the unchanged phase-1 migration. Legacy installs did not store checksums.
BASELINE_V1 = "b3396cda9e4b098d9b1b06e3cefc715cea7e88a05a14591592f4ed20b3f5d379"


def apply_migrations(conn, directory=DIRECTORY):
    files = sorted(directory.glob("[0-9][0-9][0-9]_*.sql"))
    versions = [int(path.name.split("_")[0]) for path in files]
    if not versions or versions != list(range(1, len(files) + 1)):
        raise ValueError("Migration files must form a unique sequence starting at 001")
    with conn.transaction():
        conn.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended('thesis-schema-upgrade',0))"
        )
        if (
            conn.execute("SELECT to_regclass('public.schema_migrations')").fetchone()[0]
            is None
        ):
            first = files[0].read_text()
            if sha256(first.encode()).hexdigest() != BASELINE_V1:
                raise ValueError(
                    "The baseline migration changed; restore its original source"
                )
            conn.execute(first)
        conn.execute(
            "ALTER TABLE schema_migrations ADD COLUMN IF NOT EXISTS checksum text"
        )
        conn.execute(
            "ALTER TABLE schema_migrations ADD COLUMN IF NOT EXISTS filename text"
        )
        applied = {
            row[0]: row[1:]
            for row in conn.execute(
                "SELECT version,checksum,filename FROM schema_migrations"
            ).fetchall()
        }
        if set(applied) - set(versions):
            raise ValueError(
                "Database has migrations missing from this source checkout"
            )
        if not applied or sorted(applied) != list(range(1, max(applied) + 1)):
            raise ValueError("Applied migrations must be a contiguous prefix starting at 001")
        for path, version in zip(files, versions):
            sql = path.read_text()
            digest = sha256(sql.encode()).hexdigest()
            if version in applied:
                stored, filename = applied[version]
                if stored is None:
                    if version != 1 or digest != BASELINE_V1:
                        raise ValueError("Cannot adopt an unverified legacy migration")
                    conn.execute(
                        "UPDATE schema_migrations SET checksum=%s,filename=%s WHERE version=%s",
                        (digest, path.name, version),
                    )
                elif stored != digest or filename != path.name:
                    raise ValueError(
                        f"Applied migration {version:03} differs from its saved checksum"
                    )
                continue
            conn.execute(sql)
            conn.execute(
                "INSERT INTO schema_migrations(version,checksum,filename) VALUES(%s,%s,%s)",
                (version, digest, path.name),
            )
        return versions[-1]
