"""Directory identity, fresh-start and budget preservation; no external calls."""
from datetime import datetime, timezone, timedelta
import pytest
from psycopg.types.json import Jsonb
from thesis.db import transaction, one, rows
from thesis.research import directory, catalogue, market_brief
from thesis.research.sec.service import add_company
from thesis import service
from thesis.fixtures import seed
from thesis.workspace_reset import clear_research, accounting_hash


def listing():
    return dict(fields=["cik", "name", "ticker", "exchange"], data=[
        [2488, "ADVANCED MICRO DEVICES INC", "AMD", "Nasdaq"],
        [1318605, "Tesla, Inc.", "TSLA", "Nasdaq"],
        [1652044, "Alphabet Inc.", "GOOG", "Nasdaq"],
        [1067983, "Berkshire Hathaway", "BRK-B", "NYSE"],
    ])


@pytest.fixture
def directory_state(owner):
    with transaction(admin=True) as conn:
        conn.execute("UPDATE company_directory SET listings='[]',retrieved_at=NULL,attempted_at=NULL,lease_until=NULL,error=NULL")
    return owner


def test_search_registration_identity_and_source_scope(directory_state):
    owner = directory_state
    directory.refresh(fetcher=listing)
    assert directory.search("advanced micro")["companies"][0]["symbol"] == "AMD"
    amd = add_company("AMD")["instrument_id"]
    assert add_company("AMD")["instrument_id"] == amd
    assert directory.search("amd")["companies"][0]["instrument_id"] == amd
    assert market_brief.company_for(amd)["symbol"] == "AMD"
    state = service.state(owner, amd)
    assert state["versions"] == [] and state["instrument"]["symbol"] == "AMD"
    with transaction() as conn:
        assert not rows(conn, "SELECT * FROM news_watches")
    with pytest.raises(ValueError): add_company("XXXXX")
    assert not directory.search("BRK-B")["companies"][0]["available"]
    alphabet = add_company("GOOGL")["instrument_id"]
    assert not directory.search("GOOG")["companies"][0]["available"]
    with pytest.raises(ValueError): add_company("GOOG")
    assert service.state(owner, alphabet)["instrument"]["symbol"] == "GOOGL"


def test_failure_preserves_directory_and_paces_retries(directory_state):
    directory.refresh(fetcher=listing)
    with pytest.raises(ValueError, match="five minutes"):
        directory.refresh(fetcher=lambda: pytest.fail("should not fetch twice"))
    with transaction(admin=True) as conn:
        conn.execute("UPDATE company_directory SET attempted_at=now()-interval '6 minutes'")
    with pytest.raises(ValueError, match="retained"):
        directory.refresh(fetcher=lambda: dict(data=[]))
    assert directory.search("Tesla")["companies"][0]["symbol"] == "TSLA"
    with transaction(admin=True) as conn:
        conn.execute("UPDATE company_directory SET retrieved_at=now()-interval '8 days'")
    with pytest.raises(ValueError, match="Update"):
        add_company("AMD")
    assert directory.search("AMD")["stale"]


@pytest.mark.parametrize("symbol,text,wanted", [("ON","turn it on",False),("IT","IT shares are down",True),("AMD","$AMD is expensive",True),("AMD","my AMDX fund",False),("TSLA","NASDAQ: TSLA",True),("IT","it stock footage",False)])
def test_new_tickers_require_explicit_financial_context(symbol,text,wanted):
    assert catalogue.mentions(text,symbol) is wanted


def test_fresh_workspace_stays_empty_after_restart_and_keeps_ledger(directory_state):
    owner = directory_state
    add_company("AAPL")
    with transaction(admin=True) as conn:
        conn.execute("INSERT INTO model_calls(id,request_key,request_hash,purpose,model,price_version,request_body,reserved_nano_usd,status,charged_nano_usd,owner_id) VALUES(gen_random_uuid(),'reset-accounting-test','test','test','test','test','{}',1000,'settled',750,%s)", (owner,))
        before = accounting_hash(conn)
        result = clear_research(conn)
        assert result["cleared"]["instruments"] > 0
        assert accounting_hash(conn) == before
    seed()
    assert service.state(owner)["empty"]
    assert service.state(owner, "4780d271-7c4a-5c18-80f8-74e164c21675")["empty"]
    add_company("MSFT")
    assert service.state(owner)["instrument"]["symbol"] == "MSFT"
    with transaction(admin=True) as conn:
        # Restore normal fixture bootstrap for later tests in this disposable DB.
        conn.execute("UPDATE workspace_settings SET seed_demo=true,reset_at=NULL")
