"""Isolated browser integration; the Telegram API is mocked by Playwright."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen

root = Path(__file__).resolve().parents[1]
env = dict(
    os.environ,
    THESIS_DATA_DIR=tempfile.mkdtemp(prefix="thesis-browser-telegram-", dir="/private/tmp"),
    THESIS_TEST_URL="http://127.0.0.1:8844",
    THESIS_TEST_OFFLINE="true",
    PYTHONPATH=str(root / "tests/offline_runtime") + os.pathsep + str(root),
)
server = subprocess.Popen([sys.executable,"run.py","--port","8844"],cwd=root,env=env)
try:
    for _ in range(80):
        if server.poll() is not None: raise RuntimeError("Browser server exited")
        try:
            urlopen(env["THESIS_TEST_URL"]+"/api/v1/session",timeout=1).close()
            break
        except OSError: time.sleep(.2)
    else: raise RuntimeError("Browser server did not start")
    result = subprocess.run([env.get("NODE","node"),"tests/browser_telegram.cjs"],cwd=root,env=env)
    raise SystemExit(result.returncode)
finally:
    server.terminate()
    server.wait(timeout=20)
    subprocess.run([sys.executable,"run.py","--stop-db"],cwd=root,env=env,check=True)
