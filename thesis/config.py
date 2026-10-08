import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("THESIS_DATA_DIR", str(ROOT / ".local"))).resolve()
OWNER = "11111111-1111-4111-8111-111111111111"
INSTRUMENT = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
PG_BIN = Path(os.environ.get("THESIS_PG_BIN", "/opt/homebrew/opt/postgresql@18/bin"))


def dsn(user="thesis_app"):
    return f"host={DATA / 'socket'} port=55439 dbname=thesis user={user}"
