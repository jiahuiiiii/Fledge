"""Read only this project's private settings, without shell evaluation or logging."""

import os
from pathlib import Path
from thesis.config import ROOT, DATA

MODEL = "gpt-5.4-mini-2026-03-17"
REASONING_MODEL = "gpt-5.4-2026-03-05"
# This authorization is for this existing installation and its cumulative ledger.
APPROVED_ROOT = Path("/Users/jiahuiwong/Documents/GitHub/Thesis")


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
                values[key.strip()] = value
    # Deliberately do not take arbitrary OpenAI base URLs or another project's keys.
    return values


def live_key(model=MODEL):
    if ROOT.resolve() != APPROVED_ROOT or DATA.resolve() != APPROVED_ROOT / ".local":
        raise ValueError(
            "Live requests require the original persistent Fledge database"
        )
    model_setting = {
        MODEL: "THESIS_MODEL",
        REASONING_MODEL: "THESIS_REASONING_MODEL",
    }.get(model)
    if model_setting is None:
        raise ValueError("The requested model has not been priced for this allowance")
    values = settings()
    if values.get("THESIS_LIVE_MODELS_ENABLED") != "true":
        raise ValueError("Live model requests are disabled")
    if (
        values.get("THESIS_MODEL_PROVIDER") != "openai"
        or values.get(model_setting) != model
    ):
        raise ValueError(
            "The configured provider/model has not been priced for this allowance"
        )
    if values.get("THESIS_LIVE_TEST_BUDGET_USD") != "30":
        raise ValueError("The configured allowance must match the approved US$30 total")
    key = values.get("OPENAI_API_KEY", "")
    if not key:
        raise ValueError("Add the OpenAI key to the private .env file")
    return key
