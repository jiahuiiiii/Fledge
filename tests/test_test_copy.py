"""A separate test copy (another laptop or server) can use its own AI key, with
its own database and cost record and a total spending cap. No HTTP is sent."""
import importlib
from decimal import Decimal

import pytest

from thesis.providers import ledger
from test_model_budget import body, response, clean_model_ledger  # noqa: F401  (autouse ledger reset)

settings = importlib.import_module("thesis.providers.settings")


@pytest.fixture
def copy_install(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "ROOT", tmp_path)
    monkeypatch.setattr(settings, "DATA", tmp_path / ".local")
    return tmp_path


def opt_in(monkeypatch, **extra):
    values = {"THESIS_TEST_COPY": "true", "THESIS_TEST_COPY_CAP_USD": "2",
              "THESIS_LIVE_MODELS_ENABLED": "true", "THESIS_MODEL_PROVIDER": "deepseek",
              "DEEPSEEK_API_KEY": "fictional-deepseek-key"}
    values.update(extra)
    monkeypatch.setattr(settings, "settings", lambda *a: values)
    monkeypatch.setattr(settings, "PROVIDER", "deepseek")
    monkeypatch.setattr(settings, "MODEL", "deepseek-flash")
    monkeypatch.setattr(settings, "REASONING_MODEL", "deepseek-v4-pro")
    monkeypatch.setattr(settings, "SENTIMENT_MODEL", "deepseek-v4-pro")
    return values


def test_original_installation_needs_no_opt_in_and_has_no_cap(monkeypatch):
    monkeypatch.setattr(settings, "ROOT", settings.APPROVED_ROOT)
    monkeypatch.setattr(settings, "DATA", settings.APPROVED_ROOT / ".local")
    assert settings.original_installation() and settings.test_copy_cap() is None


def test_copy_must_opt_in_with_a_sensible_cap(copy_install, monkeypatch):
    with pytest.raises(ValueError, match="THESIS_TEST_COPY=true"):
        settings.test_copy_cap({})
    assert settings.test_copy_cap({"THESIS_TEST_COPY": "true", "THESIS_TEST_COPY_CAP_USD": "2.50"}) == Decimal("2.50")
    for cap in ("", "0", "-1", "25", "abc", "NaN", "inf"):
        with pytest.raises(ValueError, match="THESIS_TEST_COPY_CAP_USD"):
            settings.test_copy_cap({"THESIS_TEST_COPY": "true", "THESIS_TEST_COPY_CAP_USD": cap})


def test_copy_cannot_point_at_the_original_database(copy_install, monkeypatch):
    monkeypatch.setattr(settings, "DATA", settings.APPROVED_ROOT / ".local")
    with pytest.raises(ValueError, match="original Fledge folder or database"):
        settings.test_copy_cap({"THESIS_TEST_COPY": "true", "THESIS_TEST_COPY_CAP_USD": "2"})


def test_opted_in_copy_gets_its_own_deepseek_key(copy_install, monkeypatch):
    opt_in(monkeypatch)
    assert settings.live_key("deepseek-flash") == "fictional-deepseek-key"
    assert settings.live_key("deepseek-v4-pro") == "fictional-deepseek-key"
    # The other live checks still apply on a test copy.
    opt_in(monkeypatch, THESIS_LIVE_MODELS_ENABLED="false")
    with pytest.raises(ValueError, match="disabled"):
        settings.live_key("deepseek-flash")
    opt_in(monkeypatch, DEEPSEEK_API_KEY="")
    with pytest.raises(ValueError, match="DEEPSEEK_API_KEY"):
        settings.live_key("deepseek-flash")


def test_copy_stops_before_its_total_could_pass_the_cap(monkeypatch):
    maximum = ledger.estimate(body())
    # Room for one call's maximum plus one nano-dollar: the first call fits; once
    # it has been charged, a second maximum would pass the cap and is refused.
    cap = Decimal(maximum + 1) / ledger.NANO
    monkeypatch.setattr(ledger, "_test_copy_cap", lambda: cap)
    first = ledger.execute("copy-1", "test", body(), transport=lambda _: response())
    assert first["status"] == "settled" and first["charged_nano_usd"] > 1
    with pytest.raises(ledger.BudgetBlocked, match="spending cap"):
        ledger.execute("copy-2", "test", body(), transport=lambda _: response())
    assert ledger.snapshot()["calls"] == 1
    # A saved answer is still returned without counting against the cap again.
    assert ledger.execute("copy-1", "test", body(), transport=lambda _: response())["id"] == first["id"]


def test_copy_cap_counts_held_calls_too(monkeypatch):
    maximum = ledger.estimate(body())
    monkeypatch.setattr(ledger, "_test_copy_cap", lambda: Decimal(maximum - 1) / ledger.NANO)
    with pytest.raises(ledger.BudgetBlocked, match="spending cap"):
        ledger.execute("too-big", "test", body(), transport=lambda _: response())
    assert ledger.snapshot()["calls"] == 0


# --- Jia Hui's sentiment-only GPT-6 Luna (THESIS_SENTIMENT_MODEL) on a test copy ---

def test_test_copy_can_use_luna_for_sentiment_with_its_own_openai_key(copy_install, monkeypatch):
    opt_in(monkeypatch, THESIS_MODEL_PROVIDER="openai", THESIS_SENTIMENT_MODEL="gpt-6-luna",
           OPENAI_API_KEY="fictional-openai-key")
    monkeypatch.setattr(settings, "PROVIDER", "openai")
    monkeypatch.setattr(settings, "MODEL", settings.OPENAI_MODEL)
    monkeypatch.setattr(settings, "REASONING_MODEL", settings.OPENAI_REASONING_MODEL)
    monkeypatch.setattr(settings, "SENTIMENT_MODEL", "gpt-6-luna")
    assert settings.live_key("gpt-6-luna") == "fictional-openai-key"
    assert settings.live_key(settings.OPENAI_REASONING_MODEL) == "fictional-openai-key"
