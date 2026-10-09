"""All provider traffic is mocked; these tests never load keys or send HTTP."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import hashlib
from threading import Event
from pathlib import Path
from uuid import uuid4
import pytest
import psycopg
from psycopg.types.json import Jsonb
from thesis.db import transaction, one
from thesis.providers import ledger
from thesis.providers.settings import MODEL, REASONING_MODEL, settings


@pytest.fixture(autouse=True)
def clean_model_ledger(db):
    with transaction(admin=True) as conn:
        conn.execute(
            "TRUNCATE discussion_theme_reviews,expectation_reviews,watch_check_results,watch_checks,research_answers,idea_alert_reviews,idea_alert_publications,idea_alert_checks,idea_watch_seen,idea_watch_state,research_alert_reviews,research_alerts,watch_seen_sources,news_watches,sentiment_analyses,proposal_decisions,idea_proposals,event_review_activations,event_results,event_evidence_reviews,model_accounting_decisions,idea_evidence_reviews,model_dispatches,business_briefs,model_calls"
        )
    yield
    with transaction(admin=True) as conn:
        conn.execute(
            "TRUNCATE discussion_theme_reviews,expectation_reviews,watch_check_results,watch_checks,research_answers,idea_alert_reviews,idea_alert_publications,idea_alert_checks,idea_watch_seen,idea_watch_state,research_alert_reviews,research_alerts,watch_seen_sources,news_watches,sentiment_analyses,proposal_decisions,idea_proposals,event_review_activations,event_results,event_evidence_reviews,model_accounting_decisions,idea_evidence_reviews,model_dispatches,business_briefs,model_calls"
        )


def body():
    return dict(
        model=MODEL,
        input=[
            {"role": "system", "content": "Only authored test evidence"},
            {"role": "user", "content": "Authored report"},
        ],
        max_output_tokens=2000,
        service_tier="default",
        store=False,
        reasoning={"effort": "none"},
        text={
            "format": {
                "type": "json_schema",
                "name": "test",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            }
        },
    )


def response():
    return dict(
        id="resp_mock",
        model=MODEL,
        service_tier="default",
        status="completed",
        usage=dict(
            input_tokens=100,
            cached_input_tokens=0,
            output_tokens=20,
            input_tokens_details=dict(cached_tokens=10),
        ),
        output=[],
    )


def reasoning_body():
    return body() | dict(
        model=REASONING_MODEL,
        reasoning={"effort": "medium"},
        max_output_tokens=ledger.REASONING_MAX_OUTPUT,
    )


def reasoning_response(**changes):
    return response() | dict(model=REASONING_MODEL, **changes)


def test_reservation_is_durable_before_dispatch_and_reconciled():
    def provider(request):
        state = ledger.snapshot()
        assert state["unresolved"] == 1 and float(state["reserved_usd"]) > 0
        return response()

    result = ledger.execute("test-one", "test", body(), transport=provider)
    assert result["charged_nano_usd"] == 90 * 750 + 10 * 75 + 20 * 4500
    assert ledger.snapshot()["unresolved"] == 0
    # A fresh connection and a repeated command use the durable response, no HTTP.
    cached = ledger.execute(
        "test-one",
        "test",
        body(),
        transport=lambda _: pytest.fail("duplicate paid call"),
    )
    assert result["id"] == cached["id"] and ledger.snapshot()["calls"] == 1
    with pytest.raises(ValueError, match="different input"):
        ledger.execute(
            "test-one",
            "test",
            body()
            | {
                "input": [
                    {"role": "system", "content": "test"},
                    {"role": "user", "content": "changed"},
                ]
            },
            transport=provider,
        )


def test_concurrent_requests_cannot_both_dispatch():
    entered, release = Event(), Event()

    def provider(_):
        entered.set()
        assert release.wait(5)
        return response()

    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(ledger.execute, "first", "test", body(), transport=provider)
        assert entered.wait(5)
        with pytest.raises(ledger.BudgetBlocked, match="reconciliation"):
            ledger.execute(
                "second",
                "test",
                body(),
                transport=lambda _: pytest.fail("concurrent call"),
            )
        release.set()
        first.result()
    assert ledger.snapshot()["calls"] == 1


@pytest.mark.parametrize("failure", [TimeoutError(), KeyboardInterrupt()])
def test_timeout_or_interrupt_keeps_reservation_and_blocks_new_requests(failure):
    def provider(_):
        raise failure

    with pytest.raises(ledger.BudgetBlocked):
        ledger.execute("ambiguous", "test", body(), transport=provider)
    state = ledger.snapshot()
    assert state["unresolved"] == 1 and float(state["reserved_usd"]) > 0
    with pytest.raises(ledger.BudgetBlocked):
        ledger.execute(
            "fresh-key",
            "test",
            body(),
            transport=lambda _: pytest.fail("automatic retry"),
        )


def test_process_loss_and_idempotency_survive_new_connections():
    call, new = ledger.reserve("killed-before-http", "test", body())
    assert new
    with pytest.raises(ledger.BudgetBlocked):
        ledger.reserve("killed-before-http", "test", body())
    with pytest.raises(ledger.BudgetBlocked):
        ledger.reserve("another-account-or-company", "test", body())
    assert ledger.snapshot()["unresolved"] == 1


def test_exhaustion_and_immutable_cap():
    with transaction(admin=True) as conn:
        conn.execute(
            "INSERT INTO model_calls(id,request_key,request_hash,purpose,model,price_version,request_body,reserved_nano_usd,status,charged_nano_usd) VALUES(%s,'earlier-work','x','test',%s,'test','{}',29999999999,'settled',29999999999)",
            (uuid4(), MODEL),
        )
    with pytest.raises(ledger.BudgetBlocked, match="allowance"):
        ledger.execute(
            "over-budget",
            "test",
            body(),
            transport=lambda _: pytest.fail("over budget"),
        )
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with transaction() as conn:
            conn.execute("UPDATE model_budget SET cap_nano_usd=30000000000")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with transaction() as conn:
            conn.execute("DELETE FROM model_calls")


def test_budget_extension_preserves_spent_calls_holds_and_dispatches():
    ledger.execute("prior-settled", "test", body(), transport=lambda _: response())
    held, _ = ledger.reserve("prior-timeout", "test", body())
    ledger.authorize_dispatch(held["id"], body())
    ledger.unresolved(held, "transport_timeout")

    class RollbackCheck(Exception):
        pass

    with transaction(admin=True) as conn:
        with pytest.raises(RollbackCheck):
            with conn.transaction():
                # Reconstruct only the pre-amendment budget contract in the
                # disposable cluster; actual prior requests are retained.
                conn.execute("DROP TABLE model_budget_amendments")
                conn.execute(
                    "ALTER TABLE model_budget DROP CONSTRAINT model_budget_cap_nano_usd_check"
                )
                conn.execute(
                    "UPDATE model_budget SET cap_nano_usd=10000000000,approval_reference='thesis-openai-build-20261001-usd10'"
                )
                conn.execute(
                    "ALTER TABLE model_budget ADD CONSTRAINT model_budget_cap_nano_usd_check CHECK(cap_nano_usd=10000000000)"
                )
                before = ledger.snapshot(conn)
                calls = conn.execute("SELECT * FROM model_calls ORDER BY id").fetchall()
                dispatches = conn.execute("SELECT * FROM model_dispatches").fetchall()
                migration = (
                    Path(__file__).resolve().parents[1]
                    / "migrations/027_build_budget_extension.sql"
                )
                conn.execute(migration.read_text())
                after = ledger.snapshot(conn)
                assert after["cap_usd"] == "20.0"
                assert float(after["remaining_usd"]) - float(
                    before["remaining_usd"]
                ) == pytest.approx(10)
                for field in ("spent_usd", "reserved_usd", "calls", "unresolved"):
                    assert after[field] == before[field]
                assert (
                    conn.execute("SELECT * FROM model_calls ORDER BY id").fetchall()
                    == calls
                )
                assert (
                    conn.execute("SELECT * FROM model_dispatches").fetchall()
                    == dispatches
                )
                assert (
                    after["unresolved"] == 1
                )  # Cap change alone does not settle a call.
                amendment = one(conn, "SELECT * FROM model_budget_amendments")
                assert amendment["previous_cap_nano_usd"] == 10 * ledger.NANO
                assert amendment["approved_cap_nano_usd"] == 20 * ledger.NANO
                conn.execute((migration.parent / "033_build_budget_extension.sql").read_text())
                current = ledger.snapshot(conn)
                assert current["cap_usd"] == "30.0"
                assert current["authorization"] == "thesis-openai-build-20261005-usd30"
                assert float(current["remaining_usd"]) - float(after["remaining_usd"]) == pytest.approx(10)
                for field in ("spent_usd", "reserved_usd", "calls", "unresolved"):
                    assert current[field] == before[field]
                assert conn.execute("SELECT * FROM model_calls ORDER BY id").fetchall() == calls
                assert conn.execute("SELECT * FROM model_dispatches").fetchall() == dispatches
                assert one(conn, "SELECT count(*) n FROM model_budget_amendments")["n"] == 2
                raise RollbackCheck()


def test_budget_amendment_cannot_be_rewritten_by_application_or_source():
    for options in ({}, {"source": True}):
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            with transaction(**options) as conn:
                conn.execute("DELETE FROM model_budget_amendments")
    with pytest.raises(psycopg.errors.RaiseException, match="immutable"):
        with transaction(admin=True) as conn:
            conn.execute("UPDATE model_budget_amendments SET evidence='replaced'")
    with pytest.raises(psycopg.errors.CheckViolation):
        with transaction(admin=True) as conn:
            conn.execute("UPDATE model_budget SET cap_nano_usd=21000000000")


@pytest.mark.parametrize(
    "bad",
    [
        dict(usage=None),
        dict(model="unpriced-model"),
        dict(usage=dict(input_tokens=1, output_tokens=2001)),
        dict(usage=dict(input_tokens=999999, output_tokens=0)),
        dict(
            usage=dict(
                input_tokens=1,
                output_tokens=0,
                input_tokens_details=dict(cached_tokens=2),
            )
        ),
    ],
)
def test_invalid_usage_or_unpriced_response_remains_blocked(bad):
    with pytest.raises(ledger.BudgetBlocked):
        ledger.execute("bad", "test", body(), transport=lambda _: response() | bad)
    assert ledger.snapshot()["unresolved"] == 1


def test_private_env_parser_does_not_evaluate_shell(tmp_path):
    path = tmp_path / ".env"
    path.write_text(
        '# comment\nOPENAI_API_KEY="never-a-real-key"\nIGNORE=$(touch unsafe)\n'
    )
    assert settings(path)["OPENAI_API_KEY"] == "never-a-real-key"
    assert settings(path)["IGNORE"] == "$(touch unsafe)"
    assert not (tmp_path / "unsafe").exists()


@pytest.mark.parametrize(
    "change",
    [
        {"previous_response_id": "resp_hidden"},
        {"conversation": "conv_hidden"},
        {"tools": [{"type": "web_search"}]},
        {
            "input": [
                {"role": "system", "content": "x"},
                {
                    "role": "user",
                    "content": [
                        {"type": "input_image", "image_url": "https://example.com/pic"}
                    ],
                },
            ]
        },
        {"reasoning": {"effort": "high"}},
    ],
)
def test_unbounded_request_shapes_never_reserve(change):
    with pytest.raises(ValueError):
        ledger.reserve("bad-shape", "test", body() | change)
    assert ledger.snapshot()["calls"] == 0


def test_copied_installation_cannot_start_another_live_allowance(monkeypatch, tmp_path):
    import importlib

    module = importlib.import_module("thesis.providers.settings")
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "DATA", tmp_path / ".local")
    monkeypatch.setattr(
        module,
        "settings",
        lambda: pytest.fail("Alternate installation must be rejected before keys"),
    )
    with pytest.raises(ValueError, match="original persistent"):
        module.live_key()


def test_settled_charge_cannot_be_reduced_or_redispatched():
    ledger.execute("immutable", "test", body(), transport=lambda _: response())
    for statement in (
        "UPDATE model_calls SET charged_nano_usd=0",
        "UPDATE model_calls SET status='dispatched',charged_nano_usd=NULL",
    ):
        with pytest.raises(psycopg.errors.RaiseException, match="immutable"):
            with transaction() as conn:
                conn.execute(statement)


def test_network_dispatch_requires_unused_matching_reservation():
    call, _ = ledger.reserve("network-once", "test", body())
    with pytest.raises(ledger.BudgetBlocked):
        ledger.authorize_dispatch(uuid4(), body())
    wrong = body() | {
        "input": [
            {"role": "system", "content": "x"},
            {"role": "user", "content": "different"},
        ]
    }
    with pytest.raises(ledger.BudgetBlocked):
        ledger.authorize_dispatch(call["id"], wrong)
    ledger.authorize_dispatch(call["id"], body())
    with pytest.raises(ledger.BudgetBlocked):
        ledger.authorize_dispatch(call["id"], body())


def test_authorized_maximum_is_still_counted_without_inventing_usage():
    call, _ = ledger.reserve("known-timeout", "test", body())
    ledger.authorize_dispatch(call["id"], body())
    ledger.unresolved(call, "transport_timeout")
    before = ledger.snapshot()
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with transaction() as conn:
            conn.execute(
                "INSERT INTO model_accounting_decisions(call_id,authority,evidence) VALUES(%s,'unauthorized','test')",
                (call["id"],),
            )
    with transaction(admin=True) as conn:
        conn.execute(
            "INSERT INTO model_accounting_decisions(call_id,authority,evidence) VALUES(%s,'explicit fictional test approval','Owner allows continuation with full maximum held')",
            (call["id"],),
        )
    after = ledger.snapshot()
    assert after["spent_usd"] == before["spent_usd"] == "0.0"
    assert (
        after["reserved_usd"]
        == before["reserved_usd"]
        == after["accounted_maximum_usd"]
    )
    assert (
        after["remaining_usd"] == before["remaining_usd"] and after["unresolved"] == 0
    )
    with transaction() as conn:
        row = one(conn, "SELECT * FROM model_calls WHERE id=%s", (call["id"],))
        assert (
            row["status"] == "unresolved"
            and row["input_tokens"] is None
            and row["response_id"] is None
        )
    with pytest.raises(ledger.BudgetBlocked):
        ledger.reserve("known-timeout", "test", body())
    with pytest.raises(ledger.BudgetBlocked):
        ledger.authorize_dispatch(call["id"], body())
    # A new explicit request can run, but the held maximum reduces its allowance.
    with transaction(admin=True) as conn:
        conn.execute(
            """INSERT INTO model_calls(id,request_key,request_hash,purpose,model,price_version,request_body,reserved_nano_usd,status,charged_nano_usd) VALUES(%s,'near-cap','x','test',%s,'test','{}',9999999999,'settled',%s)""",
            (uuid4(), MODEL, 30_000_000_000 - ledger.estimate(body())),
        )
    with pytest.raises(ledger.BudgetBlocked, match="allowance"):
        ledger.reserve("held-maximum-still-counts", "test", body())
    assert ledger.snapshot()["calls"] == 2
    with pytest.raises(psycopg.errors.RaiseException, match="immutable"):
        with transaction(admin=True) as conn:
            conn.execute("DELETE FROM model_accounting_decisions")


def test_verified_later_usage_replaces_only_its_held_maximum():
    call, _ = ledger.reserve("later-accounting", "test", body())
    ledger.authorize_dispatch(call["id"], body())
    ledger.unresolved(call, "transport_timeout")
    with transaction(admin=True) as conn:
        conn.execute(
            "INSERT INTO model_accounting_decisions(call_id,authority,evidence) VALUES(%s,'explicit test approval','Keep full maximum')",
            (call["id"],),
        )
    ledger.execute(
        "separate-explicit-work", "test", body(), transport=lambda _: response()
    )
    assert ledger.snapshot()["accounted_maximum_usd"] != "0.0"
    ledger.settle(call, response() | {"id": "resp_recovered"})
    final = ledger.snapshot()
    assert final["reserved_usd"] == final["accounted_maximum_usd"] == "0.0"
    assert final["unresolved"] == 0 and final["calls"] == 2


def test_profiles_share_totals_and_legacy_mini_cache_keeps_original_charge():
    mini = ledger.execute("legacy-mini", "test", body(), transport=lambda _: response())
    strong_reply = reasoning_response(
        usage=dict(
            input_tokens=200,
            output_tokens=6000,
            input_tokens_details=dict(cached_tokens=50),
            output_tokens_details=dict(reasoning_tokens=5000),
        )
    )
    strong = ledger.execute(
        "reasoned", "test", reasoning_body(), transport=lambda _: strong_reply
    )
    assert mini["price_version"] == "openai-gpt-5.4-mini-standard-20261001"
    assert mini["charged_nano_usd"] == 90 * 750 + 10 * 75 + 20 * 4500
    assert strong["model"] == REASONING_MODEL
    assert strong["price_version"] == ledger.REASONING_PRICE_VERSION
    assert strong["charged_nano_usd"] == 150 * 2500 + 50 * 250 + 6000 * 15000
    # Reasoning is a subset of total output, never an additional charge.
    assert ledger.snapshot()["calls"] == 2
    assert (
        float(ledger.snapshot()["spent_usd"])
        == (mini["charged_nano_usd"] + strong["charged_nano_usd"]) / ledger.NANO
    )
    cached = ledger.execute(
        "legacy-mini",
        "test",
        body(),
        transport=lambda _: pytest.fail("Legacy cache bypassed"),
    )
    assert cached == mini
    with pytest.raises(ValueError, match="priced model|different input"):
        ledger.reserve("legacy-mini", "test", reasoning_body())


@pytest.mark.parametrize(
    "reserved,new", [(body, reasoning_body), (reasoning_body, body)]
)
def test_unresolved_reservation_blocks_every_profile(reserved, new):
    ledger.reserve("first-profile", "test", reserved())
    with pytest.raises(ledger.BudgetBlocked, match="reconciliation"):
        ledger.execute(
            "other-profile",
            "test",
            new(),
            transport=lambda _: pytest.fail("Cross-profile retry"),
        )
    assert ledger.snapshot()["calls"] == 1 and ledger.snapshot()["unresolved"] == 1


def test_settlement_uses_stored_profile_not_caller_supplied_prices():
    call, _ = ledger.reserve("stored-profile", "test", reasoning_body())
    counterfeit = dict(
        call, model=MODEL, price_version=ledger.PRICE_VERSION, reserved_nano_usd=10**18
    )
    result = ledger.settle(counterfeit, reasoning_response())
    assert result["charged_nano_usd"] == 90 * 2500 + 10 * 250 + 20 * 15000
    assert result["model"] == REASONING_MODEL
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with transaction() as conn:
            conn.execute("UPDATE model_calls SET price_version='reprice'")


@pytest.mark.parametrize(
    "changed",
    [
        dict(model=MODEL),
        dict(model="unpriced-model"),
        dict(service_tier="priority"),
        dict(usage=dict(input_tokens=1, output_tokens=6001)),
        dict(
            usage=dict(
                input_tokens=1,
                output_tokens=100,
                output_tokens_details=dict(reasoning_tokens=101),
            )
        ),
    ],
)
def test_reasoning_usage_wrong_model_tier_or_bounds_keeps_hold(changed):
    reply = reasoning_response() | changed
    with pytest.raises(ledger.BudgetBlocked):
        ledger.execute(
            "bad-reasoning", "test", reasoning_body(), transport=lambda _: reply
        )
    assert ledger.snapshot()["unresolved"] == 1


def test_unknown_stored_price_version_cannot_dispatch_or_settle():
    request = reasoning_body()
    with transaction(admin=True) as conn:
        call = one(
            conn,
            """INSERT INTO model_calls(id,request_key,request_hash,purpose,model,price_version,
            request_body,reserved_nano_usd,status) VALUES(%s,'unknown-price',%s,'test',%s,'unknown',%s,%s,'dispatched') RETURNING *""",
            (
                uuid4(),
                hashlib.sha256(ledger.canonical(request).encode()).hexdigest(),
                REASONING_MODEL,
                Jsonb(request),
                ledger.estimate(request),
            ),
        )
    with pytest.raises(ValueError, match="price version"):
        ledger.authorize_dispatch(call["id"], request)
    with pytest.raises(ValueError, match="price version"):
        ledger.settle(call, reasoning_response())
    with pytest.raises(ValueError, match="price version"):
        ledger.reserve("unknown-price", "test", request)
    assert ledger.snapshot()["unresolved"] == 1


@pytest.mark.parametrize(
    "change",
    [
        dict(reasoning={"effort": "none"}),
        dict(reasoning={"effort": "high"}),
        dict(max_output_tokens=2000),
        dict(max_output_tokens=6001),
        dict(model="gpt-5.4"),
        dict(service_tier="auto"),
    ],
)
def test_reasoning_profile_has_one_bounded_request_contract(change):
    with pytest.raises(ValueError):
        ledger.reserve("wrong-reasoning-contract", "test", reasoning_body() | change)
    assert ledger.snapshot()["calls"] == 0


def test_both_models_require_explicit_config_in_original_installation(monkeypatch):
    import importlib

    module = importlib.import_module("thesis.providers.settings")
    monkeypatch.setattr(module, "ROOT", module.APPROVED_ROOT)
    monkeypatch.setattr(module, "DATA", module.APPROVED_ROOT / ".local")
    values = dict(
        THESIS_LIVE_MODELS_ENABLED="true",
        THESIS_MODEL_PROVIDER="openai",
        THESIS_MODEL=MODEL,
        THESIS_LIVE_TEST_BUDGET_USD="30",
        OPENAI_API_KEY="mock-only-key",
    )
    monkeypatch.setattr(module, "settings", lambda: deepcopy(values))
    assert module.live_key() == "mock-only-key"
    with pytest.raises(ValueError, match="priced"):
        module.live_key(REASONING_MODEL)
    values["THESIS_REASONING_MODEL"] = REASONING_MODEL
    assert module.live_key(REASONING_MODEL) == "mock-only-key"
    values["THESIS_MODEL"] = REASONING_MODEL
    with pytest.raises(ValueError, match="priced"):
        module.live_key()
    assert module.live_key(REASONING_MODEL) == "mock-only-key"
    values["THESIS_LIVE_TEST_BUDGET_USD"] = "10"
    with pytest.raises(ValueError, match="US\\$30"):
        module.live_key(REASONING_MODEL)
    monkeypatch.setattr(
        module, "settings", lambda: pytest.fail("Unknown model must not read keys")
    )
    with pytest.raises(ValueError, match="priced"):
        module.live_key("unpriced-model")


@pytest.mark.parametrize("model", [MODEL, REASONING_MODEL])
def test_copied_installation_blocks_both_profiles_before_reading_secrets(
    monkeypatch, tmp_path, model
):
    import importlib

    module = importlib.import_module("thesis.providers.settings")
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "DATA", tmp_path / ".local")
    monkeypatch.setattr(
        module, "settings", lambda: pytest.fail("Copied installation read secrets")
    )
    with pytest.raises(ValueError, match="original persistent"):
        module.live_key(model)


def test_disabled_reasoning_route_reserves_nothing(monkeypatch):
    import importlib

    module = importlib.import_module("thesis.providers.settings")
    selected = []

    def reject(model=MODEL):
        selected.append(model)
        raise ValueError("Reasoning profile disabled")

    monkeypatch.setattr(module, "live_key", reject)
    with pytest.raises(ValueError, match="disabled"):
        ledger.execute("disabled-reasoning", "test", reasoning_body())
    assert selected == [REASONING_MODEL]
    assert ledger.snapshot()["calls"] == 0


def test_stronger_profile_cannot_start_a_separate_allowance():
    remaining = ledger.estimate(reasoning_body()) - 1
    assert remaining > ledger.estimate(body())
    with transaction(admin=True) as conn:
        conn.execute(
            """INSERT INTO model_calls(id,request_key,request_hash,purpose,model,price_version,
          request_body,reserved_nano_usd,status,charged_nano_usd) VALUES(%s,'earlier-mini','x','test',%s,%s,%s,%s,'settled',%s)""",
            (
                uuid4(),
                MODEL,
                ledger.PRICE_VERSION,
                Jsonb(body()),
                30 * ledger.NANO - remaining,
                30 * ledger.NANO - remaining,
            ),
        )
    with pytest.raises(ledger.BudgetBlocked, match="allowance"):
        ledger.execute(
            "strong-over-cap",
            "test",
            reasoning_body(),
            transport=lambda _: pytest.fail("Strong model bypassed existing spending"),
        )
    ledger.execute("mini-within-cap", "test", body(), transport=lambda _: response())
    assert ledger.snapshot()["calls"] == 2
    assert 0 < float(ledger.snapshot()["remaining_usd"]) < remaining / ledger.NANO


@pytest.mark.parametrize(
    "request_factory,response_factory",
    [(body, response), (reasoning_body, reasoning_response)],
)
def test_http_adapter_gates_the_requested_model_and_dispatches_once(
    monkeypatch, request_factory, response_factory
):
    import importlib

    settings_module = importlib.import_module("thesis.providers.settings")
    adapter = importlib.import_module("thesis.providers.openai")
    selected, posts = [], []
    request_body = request_factory()

    def mock_key(model=MODEL):
        selected.append(model)
        return "mock-key-never-real"

    class MockClient:
        def __init__(self, **kwargs):
            assert kwargs["follow_redirects"] is False

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, *, headers, json):
            assert url == "https://api.openai.com/v1/responses"
            assert headers["Authorization"] == "Bearer mock-key-never-real"
            assert set(headers) == {"Authorization", "X-Client-Request-Id"}
            with transaction() as conn:
                assert one(
                    conn,
                    "SELECT call_id FROM model_dispatches WHERE call_id=%s",
                    (headers["X-Client-Request-Id"],),
                )
            posts.append(json)

            class MockResponse:
                status_code = 200

                def json(self):
                    return response_factory()

            return MockResponse()

    monkeypatch.setattr(settings_module, "live_key", mock_key)
    monkeypatch.setattr(adapter, "live_key", mock_key)
    monkeypatch.setattr(adapter.httpx, "Client", MockClient)
    result = ledger.execute("mock-http", "test", request_body)
    assert result["model"] == request_body["model"]
    assert selected == [request_body["model"], request_body["model"]]
    assert posts == [request_body]
    with transaction() as conn:
        assert one(conn, "SELECT count(*) n FROM model_dispatches")["n"] == 1


def sentiment_body():
    value = reasoning_body()
    value["max_output_tokens"] = ledger.SENTIMENT_MAX_OUTPUT
    value["text"]["format"]["name"] = "source_sentiment"
    return value


def test_sentiment_output_profile_retains_old_caps_and_reserves_full_amount(db):
    value = sentiment_body()
    assert ledger.request_profile(reasoning_body()).max_output == 6000
    assert ledger.request_profile(value).max_output == 9000
    old = sentiment_body()
    old["max_output_tokens"] = 6000
    assert ledger.estimate(value) - ledger.estimate(old) == 3000 * 15000
    call, fresh = ledger.reserve("extended-sentiment-allowance", "test", value)
    assert fresh and call["price_version"] == ledger.SENTIMENT_PRICE_VERSION
    reply = reasoning_response(
        usage=dict(
            input_tokens=100,
            output_tokens=8500,
            total_tokens=8600,
            input_tokens_details=dict(cached_tokens=0),
            output_tokens_details=dict(reasoning_tokens=6000),
        )
    )
    settled = ledger.settle(call, reply)
    assert settled["charged_nano_usd"] == 100 * 2500 + 8500 * 15000


@pytest.mark.parametrize(
    "change", [dict(max_output_tokens=9001), dict(reasoning={"effort": "high"})]
)
def test_extended_sentiment_profile_still_rejects_unpriced_bounds(change):
    with pytest.raises(ValueError):
        ledger.estimate(sentiment_body() | change)


def test_other_research_routes_cannot_use_sentiment_allowance():
    value = sentiment_body()
    value["text"]["format"]["name"] = "private_relevance"
    with pytest.raises(ValueError):
        ledger.estimate(value)


def finding_check_body():
    value = reasoning_body()
    value['max_output_tokens'] = ledger.FINDING_CHECK_MAX_OUTPUT
    value['reasoning'] = {'effort': 'high'}
    value['text']['format']['name'] = 'finding_evidence_check'
    return value


def test_finding_check_allowance_keeps_original_profiles_and_accounting():
    value = finding_check_body()
    assert ledger.request_profile(value).version == ledger.FINDING_CHECK_PRICE_VERSION
    assert ledger.request_profile(reasoning_body()).version == ledger.REASONING_PRICE_VERSION
    assert ledger.request_profile(sentiment_body()).version == ledger.SENTIMENT_PRICE_VERSION
    call, fresh = ledger.reserve('bounded-high-checker', 'test', value)
    assert fresh and call['reserved_nano_usd'] == ledger.estimate(value)
    reply = reasoning_response(usage=dict(input_tokens=100, output_tokens=8900,
        input_tokens_details=dict(cached_tokens=10),
        output_tokens_details=dict(reasoning_tokens=6000)))
    settled = ledger.settle(call, reply)
    assert settled['charged_nano_usd'] == 90*2500+10*250+8900*15000
    assert ledger.snapshot()['unresolved'] == 0


@pytest.mark.parametrize('change', [
    dict(max_output_tokens=9001), dict(reasoning={'effort':'xhigh'}),
    dict(service_tier='priority'), dict(model=MODEL),
])
def test_finding_check_profile_rejects_unpriced_variants(change):
    with pytest.raises(ValueError):ledger.estimate(finding_check_body() | change)


def test_high_reasoning_allowance_is_not_available_to_other_routes():
    value=finding_check_body()
    value['text']['format']['name']='source_sentiment'
    with pytest.raises(ValueError):ledger.estimate(value)


def sentiment_depth_body():
    value = sentiment_body()
    value['max_output_tokens'] = ledger.SENTIMENT_DEPTH_MAX_OUTPUT
    value['reasoning'] = {'effort': 'high'}
    value['text']['format']['name'] = 'source_sentiment_reasoning_eval'
    return value


def test_sentiment_depth_uses_global_ledger_and_retains_historical_profiles():
    value = sentiment_depth_body()
    profile = ledger.request_profile(value)
    assert profile.version == ledger.SENTIMENT_DEPTH_PRICE_VERSION
    assert profile.max_output == 12000 and profile.effort == 'high'
    assert ledger.request_profile(sentiment_body()).version == ledger.SENTIMENT_PRICE_VERSION
    assert ledger.request_profile(reasoning_body()).version == ledger.REASONING_PRICE_VERSION
    assert ledger.request_profile(finding_check_body()).version == ledger.FINDING_CHECK_PRICE_VERSION
    expected = (len(ledger.canonical(value).encode()) + 8192) * 2500 + 12000 * 15000
    call, fresh = ledger.reserve('sentiment-depth-trial', 'test', value)
    assert fresh and call['reserved_nano_usd'] == expected
    reply = reasoning_response(usage=dict(
        input_tokens=100, output_tokens=11500,
        input_tokens_details=dict(cached_tokens=10),
        output_tokens_details=dict(reasoning_tokens=9000),
    ))
    settled = ledger.settle(call, reply)
    assert settled['charged_nano_usd'] == 90 * 2500 + 10 * 250 + 11500 * 15000
    assert ledger.snapshot()['unresolved'] == 0
    repeated = ledger.execute('sentiment-depth-trial', 'test', value,
        transport=lambda _: pytest.fail('Settled trial was dispatched again'))
    assert repeated['id'] == call['id'] and ledger.snapshot()['calls'] == 1


@pytest.mark.parametrize('change', [
    dict(max_output_tokens=12001), dict(max_output_tokens=9000),
    dict(reasoning={'effort': 'medium'}), dict(reasoning={'effort': 'xhigh'}),
    dict(service_tier='priority'), dict(model=MODEL), dict(store=True),
])
def test_sentiment_depth_rejects_unpriced_variants(change):
    with pytest.raises(ValueError):
        ledger.reserve('invalid-depth', 'test', sentiment_depth_body() | change)
    assert ledger.snapshot()['calls'] == 0


@pytest.mark.parametrize('name', ['source_sentiment', 'idea_answer_evidence', 'finding_evidence_check'])
def test_depth_allowance_does_not_leak_to_app_routes(name):
    value = sentiment_depth_body()
    value['text']['format']['name'] = name
    with pytest.raises(ValueError):
        ledger.estimate(value)


@pytest.mark.parametrize('factory,read,other', [
    (body, 60, 60), (reasoning_body, 180, 180), (sentiment_body, 180, 180),
    (finding_check_body, 180, 180), (sentiment_depth_body, 420, 180),
])
def test_only_depth_trial_extends_http_read_timeout(factory, read, other):
    from thesis.providers.openai import request_timeout
    timeout = request_timeout(factory())
    assert timeout.connect == 15
    assert timeout.read == read
    assert timeout.write == timeout.pool == other


def test_depth_transport_timeout_keeps_full_hold_and_never_retries(monkeypatch):
    import importlib
    adapter = importlib.import_module('thesis.providers.openai')
    config = importlib.import_module('thesis.providers.settings')
    posts = []

    class TimeoutClient:
        def __init__(self, **kwargs):
            assert kwargs['timeout'].read == 420
            assert kwargs['follow_redirects'] is False

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, *args, **kwargs):
            posts.append(1)
            raise adapter.httpx.ReadTimeout('mock timeout')

    monkeypatch.setattr(config, 'live_key', lambda _: 'fictional-test-key')
    monkeypatch.setattr(adapter, 'live_key', lambda _: 'fictional-test-key')
    monkeypatch.setattr(adapter.httpx, 'Client', TimeoutClient)
    value = sentiment_depth_body()
    with pytest.raises(ledger.BudgetBlocked):
        ledger.execute('depth-timeout', 'test', value)
    with transaction() as conn:
        call = one(conn, "SELECT * FROM model_calls WHERE request_key='depth-timeout'")
        assert call['status'] == 'unresolved'
        assert call['reserved_nano_usd'] == ledger.estimate(value)
        assert call['charged_nano_usd'] is None
    with pytest.raises(ledger.BudgetBlocked):
        ledger.execute('depth-timeout', 'test', value)
    assert posts == [1] and ledger.snapshot()['unresolved'] == 1
