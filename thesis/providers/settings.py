"""Read only this project's private settings, without shell evaluation or logging."""

import os
from decimal import Decimal, InvalidOperation
from pathlib import Path
from thesis.config import ROOT, DATA

OPENAI_MODEL = "gpt-5.4-mini-2026-03-17"
OPENAI_REASONING_MODEL = "gpt-5.4-2026-03-05"
# Optional cheaper model for sentiment readings only (owner choice, 18 Oct 2026).
# OpenAI lists no dated snapshot; responses must report exactly this name.
OPENAI_SENTIMENT_MODEL = "gpt-6-luna"
OPENAI_EXPLAINER_MODEL = "gpt-5.5-2026-04-23"
EXPLAINER_MODELS = (OPENAI_EXPLAINER_MODEL, "claude-opus-5-5")
# Prices in nano-USD per token: input, cache read, cache write, output.
# Anthropic: 5-minute cache write. Checked 2026-10-13.
ANTHROPIC_PRICES = {
    "claude-opus-5-5": (4000, 200, 5000, 20000),
    "claude-sonnet-5-5": (2000, 200, 2500, 10000),
    "claude-haiku-5-5": (100, 10, 125, 500),
}
# DeepSeek peak-hour rates (off-peak is half), so reservations and charges
# never understate the bill. No separate cache-write price. Checked 2026-10-13.
DEEPSEEK_PRICES = {
    "deepseek-flash": (300, 6, 300, 1200),
    "deepseek-v4-pro": (1320, 44, 1320, 3960),
}
ANTHROPIC_DEFAULT_MODEL = "claude-haiku-5-5"
ANTHROPIC_DEFAULT_REASONING_MODEL = "claude-opus-5-5"

# THESIS_MODEL_PROVIDER in .env is the one line to change; each provider brings
# its own quick-check and main-reading models. Anthropic and DeepSeek accept
# optional overrides (ANTHROPIC_MODEL, ANTHROPIC_REASONING_MODEL, DEEPSEEK_...)
# among their priced models. OpenAI's two models are fixed by its price profiles.
DEFAULT_MODELS = {
    "openai": (OPENAI_MODEL, OPENAI_REASONING_MODEL),
    "anthropic": (ANTHROPIC_DEFAULT_MODEL, ANTHROPIC_DEFAULT_REASONING_MODEL),
    "deepseek": ("deepseek-flash", "deepseek-v4-pro"),
}
TWIN_PRICES = {"anthropic": ANTHROPIC_PRICES, "deepseek": DEEPSEEK_PRICES}
API_KEYS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
}
SELECTION_KEYS = ("THESIS_MODEL_PROVIDER", "THESIS_MOVE_EXPLAINER_MODEL", "THESIS_SENTIMENT_MODEL") + tuple(
    f"{provider.upper()}_{role}"
    for provider in TWIN_PRICES
    for role in ("MODEL", "REASONING_MODEL")
)
# This authorization is for this existing installation and its cumulative ledger.
APPROVED_ROOT = Path("/Users/jiahuiwong/Documents/GitHub/Thesis")
# A separate test copy (another laptop or a cloud server) may opt in with its own
# key, its own database and cost record, and a total spending cap it must set.
TEST_COPY_MAX_CAP_USD = Decimal("100")


class ProviderConfigError(ValueError):
    """An app-authored provider setup problem; its text is safe to show."""


def settings(path=None):
    path = Path(path) if path else ROOT / ".env"
    values = {}
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, sep, value = line.partition("=")
            if sep:
                value = value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                    value = value[1:-1]
                else:
                    # Unquoted values may end in a "  # comment".
                    for mark in (" #", "\t#"):
                        value = value.split(mark, 1)[0]
                    value = value.rstrip()
                values[key.strip()] = value
    # Deliberately do not take arbitrary OpenAI base URLs or another project's keys.
    return values


def _configured():
    # Offline tests never read the private .env; they may opt into a provider
    # through the process environment to exercise its request contract.
    if os.environ.get("THESIS_TEST_OFFLINE") == "true":
        return {k: os.environ[k] for k in SELECTION_KEYS if k in os.environ}
    return settings()


def select(values):
    """(provider, quick-check model, main model) chosen by these settings."""
    provider = values.get("THESIS_MODEL_PROVIDER") or "openai"
    if provider not in DEFAULT_MODELS:
        raise ProviderConfigError(
            "THESIS_MODEL_PROVIDER must be one of: " + ", ".join(DEFAULT_MODELS)
        )
    model, reasoning = DEFAULT_MODELS[provider]
    prices = TWIN_PRICES.get(provider)
    if prices is None:
        return provider, model, reasoning
    prefix = provider.upper()
    model = values.get(f"{prefix}_MODEL") or model
    reasoning = values.get(f"{prefix}_REASONING_MODEL") or reasoning
    for name in (model, reasoning):
        if name not in prices:
            raise ProviderConfigError(
                f"{name} has no recorded {provider} price in thesis/providers/settings.py"
            )
    return provider, model, reasoning


def _models():
    return select(_configured())


# Chosen once at start-up; THESIS_MODEL is the quick check, REASONING_MODEL the main one.
PROVIDER, MODEL, REASONING_MODEL = _models()


def explainer_choice(values):
    model = values.get("THESIS_MOVE_EXPLAINER_MODEL") or None
    if model is not None and model not in EXPLAINER_MODELS:
        raise ProviderConfigError("Choose a priced move explainer model or leave it disabled")
    return model


# Independent role, disabled until the owner approves a live choice.
EXPLAINER_MODEL = explainer_choice(_configured())


def sentiment_choice(values, provider=None, reasoning=None):
    """Sentiment readings use the main model unless the owner picks a priced alternative."""
    provider, reasoning = provider or PROVIDER, reasoning or REASONING_MODEL
    model = values.get("THESIS_SENTIMENT_MODEL") or reasoning
    if model == reasoning:
        return model
    if provider != "openai" or model != OPENAI_SENTIMENT_MODEL:
        raise ProviderConfigError("THESIS_SENTIMENT_MODEL must be the main model or " + OPENAI_SENTIMENT_MODEL + " with OpenAI")
    return model


# Chosen once at start-up, like the main model; a later .env edit needs a restart.
SENTIMENT_MODEL = sentiment_choice(_configured())


def provider_for(model):
    for provider, prices in TWIN_PRICES.items():
        if model in prices:
            return provider
    return "openai"


def original_installation():
    return ROOT.resolve() == APPROVED_ROOT and DATA.resolve() == APPROVED_ROOT / ".local"


def test_copy_cap(values=None):
    """The spending cap (US$) of an opted-in test copy, or None for the original.

    A test copy never shares the original's database or cost record: it must not
    run from, or point its data at, the original folder. Its own .env says
    THESIS_TEST_COPY=true and THESIS_TEST_COPY_CAP_USD (above 0, at most 100).
    """
    if original_installation():
        return None
    values = settings() if values is None else values
    if values.get("THESIS_TEST_COPY") != "true":
        raise ProviderConfigError(
            "Live requests require the original persistent Fledge database. On your own "
            "copy, add THESIS_TEST_COPY=true and THESIS_TEST_COPY_CAP_USD to .env"
        )
    if ROOT.resolve().is_relative_to(APPROVED_ROOT) or DATA.resolve().is_relative_to(APPROVED_ROOT):
        raise ProviderConfigError("A test copy cannot use the original Fledge folder or database")
    try:
        cap = Decimal(values.get("THESIS_TEST_COPY_CAP_USD", ""))
    except InvalidOperation:
        cap = None
    if cap is None or not cap.is_finite() or not Decimal(0) < cap <= TEST_COPY_MAX_CAP_USD:
        raise ProviderConfigError(
            f"Set THESIS_TEST_COPY_CAP_USD in .env to a total spending cap above 0 and at most "
            f"{TEST_COPY_MAX_CAP_USD} US dollars"
        )
    return cap


def live_key(model=MODEL):
    test_copy_cap()  # The original passes; any other copy must opt in with a cap.
    if model not in (MODEL, REASONING_MODEL, SENTIMENT_MODEL) and (EXPLAINER_MODEL is None or model != EXPLAINER_MODEL):
        raise ProviderConfigError("The requested model has not been priced for this allowance")
    values = settings()
    if values.get("THESIS_LIVE_MODELS_ENABLED") != "true":
        raise ProviderConfigError("Live model requests are disabled")
    # The running app chose its provider at start-up; a later .env edit needs a restart.
    if select(values) != (PROVIDER, MODEL, REASONING_MODEL):
        raise ProviderConfigError(
            "The AI provider settings in .env changed; restart the app to use them"
        )
    if explainer_choice(values) != EXPLAINER_MODEL:
        raise ProviderConfigError("The explainer setting in .env changed; restart the app to use it")
    if sentiment_choice(values) != SENTIMENT_MODEL:
        raise ProviderConfigError("The sentiment model setting in .env changed; restart the app to use it")
    provider = provider_for(model)
    name = API_KEYS[provider]
    key = values.get(name, "")
    if not key:
        raise ProviderConfigError(f"Add the {provider} key ({name}) to the private .env file")
    return key
