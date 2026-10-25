"""Light home-card reads, compression and cache headers; disposable database only."""
from datetime import datetime, timezone
from uuid import uuid4
import gzip

import pytest
from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb

from thesis import home_cards, service
from thesis.db import transaction
from thesis.research.sec.service import add_company
from test_sec_fundamentals import apply, bundle

NOW = datetime(2025, 7, 24, 15, 0, tzinfo=timezone.utc)


def quoted_company(symbol):
    iid = str(uuid4())
    with transaction(admin=True) as conn:
        conn.execute("INSERT INTO instruments VALUES(%s,%s,%s)", (iid, symbol, symbol + " Fictional"))
        conn.execute("""INSERT INTO instrument_state(instrument_id,cutoff,period,label,sector)
                        VALUES(%s,'2025-07-24T12:00:00Z','2025-Q2','Q2 baseline','Software')""", (iid,))
        conn.execute("INSERT INTO market_quotes VALUES(%s,%s,%s,%s)",
                     (uuid4(), iid, Jsonb(dict(price=101.5, change=1.5, change_percent=1.5,
                                               quoted_at=NOW.isoformat())), NOW))
    return iid


@pytest.fixture
def client(owner, monkeypatch):
    import thesis.app as module

    monkeypatch.setattr(module, "OWNER", owner)
    client = TestClient(module.app, base_url="http://127.0.0.1")
    client.get("/api/v1/session")
    return client


def test_quotes_cover_every_catalogue_company_in_one_read(owner):
    iid = quoted_company("QTE")
    rows = home_cards.quotes(owner)
    with transaction(owner) as conn:
        expected = [str(c["id"]) for c in service.catalogue(conn, owner)]
    assert [row["id"] for row in rows] == expected
    quote = next(row for row in rows if row["id"] == iid)["market"]["quote"]
    assert quote["quote"]["price"] == 101.5 and quote["retrieved_at"]
    assert all(set(row) == {"id", "market"} for row in rows)


def test_card_keeps_only_the_two_figures_and_the_tone_summary(owner, monkeypatch):
    iid = add_company("MSFT")["instrument_id"]
    apply(iid, bundle(annual=True))
    reading = dict(
        id="r1", withheld=False, created_at=NOW.isoformat(), stale=False,
        summary_policy="sentiment-coverage-1", items=[{"large": "x" * 5000}], sources=[{"id": "s"}],
        summary=dict(news=dict(tone="positive leaning", counts=dict(positive=2)), social=dict(tone="mixed"),
                     social_platforms=dict(reddit=dict(tone="mixed"))),
    )
    monkeypatch.setattr("thesis.research.sentiment.latest", lambda conn, i: reading)
    card = home_cards.card(owner, iid)
    assert card["id"] == iid and card["figures"] is True
    assert card["sentiment"] == dict(
        withheld=False, id="r1", created_at=NOW.isoformat(), stale=False,
        summary_policy="sentiment-coverage-1",
        summary=dict(news=reading["summary"]["news"], social_platforms=dict(reddit=dict(tone="mixed"))),
    )
    depth = card["financial_depth"]
    assert depth["status"] == "available"
    assert {row["key"] for row in depth["trailing"]} <= set(home_cards.FIGURES)
    assert any(row["key"] == "revenue" for row in depth["trailing"])


def test_card_skips_figures_when_asked_and_keeps_withheld_readings_withheld(owner, monkeypatch):
    iid = add_company("MSFT")["instrument_id"]
    monkeypatch.setattr("thesis.research.sec.financial_depth.present",
                        lambda *a: pytest.fail("figures were computed for a Beginner card"))
    monkeypatch.setattr("thesis.research.sentiment.latest",
                        lambda conn, i: dict(id="r", withheld=True, items=[], sources=[], summary={}))
    card = home_cards.card(owner, iid, figures=False)
    assert card == dict(id=iid, sentiment=dict(withheld=True), financial_depth=None, figures=False)


def test_unavailable_figures_keep_their_reason():
    assert home_cards.trailing_figures(dict(status="empty", reason="Refresh filings.")) == dict(
        status="empty", reason="Refresh filings.")
    assert home_cards.trailing_figures(None) is None


def test_endpoints_are_scoped_and_unknown_companies_are_404(client, owner):
    iid = quoted_company("QTE")
    assert any(row["id"] == iid for row in client.get("/api/v1/home-cards").json()["result"])
    assert client.get(f"/api/v1/companies/{iid}/home-card?figures=false").json()["result"]["id"] == iid
    assert client.get(f"/api/v1/companies/{uuid4()}/home-card").status_code == 404
    assert client.get(f"/api/v1/companies/{iid}/home-card", headers={"Origin": "http://evil.test"}).status_code == 403


def test_large_answers_are_compressed_and_never_stored(client):
    response = client.get("/api/v1/workspace", headers={"Accept-Encoding": "gzip"})
    assert response.headers["content-encoding"] == "gzip"
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["result"]["instrument"]
    raw = client.get("/api/v1/workspace", headers={"Accept-Encoding": "identity"})
    assert "content-encoding" not in raw.headers
    assert len(gzip.compress(raw.content)) < len(raw.content)


@pytest.mark.parametrize("path,status,policy", [
    ("/api/v1/workspace", 200, "no-store"),
    ("/auth/callback", 200, "no-store"),
    ("/assets/index-AbC123.js", 200, "public, max-age=31536000, immutable"),
    ("/assets/index-AbC123.js", 304, "public, max-age=31536000, immutable"),
    ("/assets/missing.js", 404, "no-cache"),
    ("/fonts/MiSansLatin-Regular.woff2", 200, "public, max-age=604800"),
    ("/", 200, "no-cache"),
    ("/terms", 200, "no-cache"),
])
def test_cache_policy_keeps_pages_fresh_and_hashed_files_cached(path, status, policy):
    from thesis.app import cache_policy

    assert cache_policy(path, status) == policy


def test_missing_built_file_is_not_cached(client):
    response = client.get("/assets/definitely-missing-file.js")
    assert response.status_code == 404 and response.headers["cache-control"] == "no-cache"


def test_built_files_are_compressed_and_cached_for_good(client):
    from thesis.app import dist

    built = sorted((dist / "assets").glob("*.js")) if (dist / "assets").exists() else []
    if not built:
        pytest.skip("no frontend build to serve")
    path = "/assets/" + max(built, key=lambda f: f.stat().st_size).name
    response = client.get(path, headers={"Accept-Encoding": "gzip"})
    assert response.status_code == 200
    assert response.headers["content-encoding"] == "gzip"
    assert response.headers["cache-control"] == "public, max-age=31536000, immutable"
