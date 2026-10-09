"""Six-company catalogue and source identity; tests make no external calls."""

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import json, os
import httpx
import pytest
from thesis import service
from thesis.db import transaction, one, rows
from thesis.config import OWNER
from thesis.providers import ledger
from thesis.research import (
    catalogue,
    social,
    market,
    market_brief,
    sentiment,
    answers,
    price_history,
)
from thesis.research.sec.service import add_company, capabilities, refresh, stable
from test_sec_fundamentals import bundle
from test_market import news, quote
from test_sentiment import feed, provider, add_social
from test_price_history import payload as prices


@pytest.mark.parametrize(
    "symbol,text,expected",
    [
        ("NVDA", "NVIDIA announced a new chip.", True),
        ("NVDA", "$nvda demand is growing", True),
        ("NVDA", "An NVDAX fund update", False),
        ("NVDA", "Microsoft earnings update", False),
        ("AVGO", "I think avgo can keep growing", True),
        ("AVGO", "AVGO is in my portfolio", True),
        ("AVGO", "$avgo versus Broadcom suppliers", True),
        ("AVGO", "Broadcom reports results", True),
        ("AVGO", "An AVGON fund update", False),
        ("AVGO", "NotBroadcom or prefixed_AVGO", False),
        ("AMZN", "Amazon Web Services expands capacity", True),
        ("AMZN", "AMZN earnings", True),
        ("AMZN", "Amazon.com announced results", True),
        ("AMZN", "Amazon shares fell", True),
        ("AMZN", "The Amazon rainforest is in danger", False),
        ("AMZN", "Researchers explore the Amazon river", False),
        ("META", "Meta Platforms reports results", True),
        ("META", "Meta announced a model", True),
        ("META", "$meta outlook", True),
        ("META", "meta stock earnings", True),
        ("META", "Instagram launches a feature", True),
        ("META", "Facebook advertising", True),
        ("META", "WhatsApp policy changed", True),
        ("META", "A meta-analysis of education research", False),
        ("META", "Meta discussion about the subreddit", False),
        ("META", "META-analysis and metadata", False),
        ("META", "A metaverse project by another company", False),
        ("MSFT", "Microsoft Azure", True),
        ("AAPL", "AAPL results", True),
        ("GOOGL", "GOOG and Google", True),
    ],
)
def test_lexical_candidates_avoid_selected_ambiguous_words(symbol, text, expected):
    assert catalogue.mentions(text, symbol) is expected
    assert social.mentions(dict(title=text, body=""), symbol) is expected


def test_catalogue_additions_keep_old_identities_and_do_not_enrol_watches(
    owner, monkeypatch
):
    from thesis.research.sec import client

    monkeypatch.setattr(
        client, "fetch_bundle", lambda *_: pytest.fail("add made network request")
    )
    expected = {
        "MSFT": "c767e09f-35ea-5eaf-a626-ff5d3aa4709b",
        "AAPL": "4780d271-7c4a-5c18-80f8-74e164c21675",
        "GOOGL": "528be36b-8e44-57e9-a9fa-fbd2ee8bbdd1",
    }
    for symbol, iid in expected.items():
        assert add_company(symbol)["instrument_id"] == iid
    budget = ledger.snapshot()
    for symbol in ("NVDA", "AMZN", "META"):
        iid = add_company(symbol)["instrument_id"]
        assert add_company(symbol)["instrument_id"] == iid
        assert market_brief.company_for(iid)["symbol"] == symbol
        assert not service.state(owner, iid)["versions"]
    assert {c["symbol"] for c in capabilities()["companies"]} == set(
        catalogue.COMPANIES
    )
    with transaction(owner) as c:
        assert not rows(c, "SELECT * FROM news_watches")
    assert budget == ledger.snapshot()


@pytest.mark.parametrize("symbol", ["NVDA", "AMZN", "META"])
def test_each_company_reuses_filing_market_social_sentiment_question_and_chart_contract(
    owner, monkeypatch, symbol
):
    cik, name, _ = catalogue.COMPANIES[symbol]
    iid = add_company(symbol)["instrument_id"]
    b = bundle()
    b["companyfacts"].update(cik=cik, entityName=name)
    b["submissions"].update(cik=str(cik), name=name)
    refresh(iid, fetcher=lambda asked: b if asked == cik else pytest.fail("wrong CIK"))
    monkeypatch.setattr(market, "key", lambda: "authored-test-key")
    transport = httpx.MockTransport(
        lambda req: httpx.Response(
            200,
            json=(
                quote()
                if req.url.path.endswith("/quote")
                else [
                    news(
                        related=symbol,
                        headline=f"{name} reports results",
                        summary=f"{name} says operating margins grew.",
                    )
                ]
            ),
        )
    )
    result = market.refresh(iid, transport=transport)
    assert result["news_ok"] and result["quote_ok"]
    add_social(
        iid,
        feed(
            title=f"{name} earnings opinion",
            body=f"I am concerned about {name} margins.",
        ),
    )
    analysis = sentiment.generate(iid, transport=provider("mixed"))
    assert (
        analysis["summary"]["news"]["selected"] == 1
        and analysis["summary"]["social"]["selected"] == 1
    )
    with transaction(owner) as c:
        packet = answers.prepare(
            c,
            owner,
            iid,
            answers.Ask(
                question=f"What do the sources say about {name} margins?",
                include_social=True,
            ),
        )
    assert packet["company"]["symbol"] == symbol and any(
        s["channel"] == "news" for s in packet["sources"]
    )
    chart = price_history.normalize(
        prices(symbol=symbol), symbol, *price_history.window(datetime.now(timezone.utc))
    )
    assert chart["symbol"] == symbol
    with transaction(owner) as c:
        assert not rows(c, "SELECT * FROM news_watches")
        assert not rows(c, "SELECT * FROM thesis_versions WHERE owner_id=%s", (owner,))


@pytest.mark.parametrize("symbol", ["NVDA", "AMZN", "META"])
def test_actual_new_company_records_replay_with_original_filing_reconciliation(
    owner, symbol
):
    corpus = os.environ.get("THESIS_EXPANDED_CORPUS")
    if not corpus:
        pytest.skip("Opt-in expanded public SEC corpus; never fetch in tests")
    b = json.loads((Path(corpus) / (symbol + "-bundle.json")).read_text())
    proof = json.loads((Path(corpus) / "reconciliation.json").read_text())
    iid = add_company(symbol)["instrument_id"]
    refresh(iid, fetcher=lambda _: b)
    state = service.state(owner, iid)
    p = state["performance"]
    assert p["status"] == "available" and set(p["reports"]) == {"annual", "quarter"}
    for kind, report in p["reports"].items():
        verified = next(r for r in proof if (r["symbol"], r["kind"]) == (symbol, kind))
        assert verified["passed"] and verified["accession"] == report["accession"]
        for metric in report["metrics"]:
            for fact in metric["inputs"] + (
                [metric["prior"]] if metric["prior"] else []
            ):
                check = next(
                    c
                    for c in verified["checks"]
                    if (c["concept"], c["start"], c["end"])
                    == (fact["concept"], fact["start"], fact["end"])
                )
                assert check["passed"] and Decimal(check["expected"]) == Decimal(
                    fact["value"]
                )
        if kind == "quarter":
            revenue = next(m for m in report["metrics"] if m["key"] == "revenue")
            cash = next(m for m in report["metrics"] if m["key"] == "operating_cash")
            assert revenue["start"] > cash["start"] and revenue["end"] == cash["end"]
    # Preserve unknown cash capex instead of fabricating a free-cash-flow figure.
    if symbol in ("NVDA", "AMZN"):
        assert (
            next(
                m
                for m in p["reports"]["quarter"]["metrics"]
                if m["key"] == "free_cash_flow"
            )["value"]
            is None
        )


def test_api_accepts_catalogue_and_rejects_unknown_symbol_without_enrollment(owner):
    from fastapi.testclient import TestClient
    from thesis.app import app

    client = TestClient(app)
    client.get("/api/v1/session")
    headers = {"X-Thesis-Request": "local-ui"}
    for symbol in catalogue.COMPANIES:
        response = client.post(
            "/api/v1/sec/companies", json={"symbol": symbol}, headers=headers
        )
        assert response.status_code == 200, response.text
        assert response.json()["result"]["instrument_id"] == str(
            stable(str(catalogue.COMPANIES[symbol][0]))
        )
    assert (
        client.post(
            "/api/v1/sec/companies", json={"symbol": "UNKNOWN"}, headers=headers
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/sec/companies",
            json={"symbol": "NVDA", "enabled": True},
            headers=headers,
        ).status_code
        == 422
    )
    with transaction(OWNER) as c:
        assert not rows(c, "SELECT * FROM news_watches")
        assert not rows(c, "SELECT * FROM thesis_versions WHERE owner_id=%s", (OWNER,))
