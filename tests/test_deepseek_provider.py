"""DeepSeek chat translation and pricing. No keys are loaded and no HTTP is sent."""

import json
import pytest
from thesis.providers import deepseek as D, ledger, settings
from test_model_budget import clean_model_ledger  # noqa: F401  (autouse ledger reset)


def body(model="deepseek-v4-pro", *, effort="low", limit=ledger.SENTIMENT_LOW_MAX_OUTPUT,
         name="source_sentiment"):
    return dict(
        model=model,
        input=[
            {"role": "system", "content": "Only authored test evidence"},
            {"role": "user", "content": "Authored report"},
        ],
        max_output_tokens=limit,
        service_tier="default",
        store=False,
        reasoning={"effort": effort},
        text={"format": {"type": "json_schema", "name": name, "strict": True, "schema": {
            "type": "object",
            "properties": {"items": {"type": "array", "items": {"type": "string"}}},
            "required": ["items"],
            "additionalProperties": False,
        }}},
    )


def completion(text, *, finish="stop", model="deepseek-v4-pro", hit=300):
    return {
        "id": "chatcmpl-mock", "model": model,
        "choices": [{"index": 0, "finish_reason": finish,
                     "message": {"role": "assistant", "content": text, "reasoning_content": "…"}}],
        "usage": {"prompt_tokens": 1000, "prompt_cache_hit_tokens": hit,
                  "prompt_cache_miss_tokens": 1000 - hit, "completion_tokens": 500,
                  "completion_tokens_details": {"reasoning_tokens": 200}},
    }


def test_deepseek_models_are_priced_twins_of_each_request_family(monkeypatch):
    monkeypatch.setenv("THESIS_MODEL_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-v4-pro")
    assert settings._models() == ("deepseek", "deepseek-v4-pro", "deepseek-v4-pro")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-unpriced")
    with pytest.raises(ValueError, match="no recorded deepseek price"):
        settings._models()
    assert settings.provider_for("deepseek-flash") == "deepseek"
    profile = ledger.request_profile(body())
    assert profile.version == ledger.twin_version(
        "deepseek", "deepseek-v4-pro", ledger.SENTIMENT_LOW_PRICE_VERSION)
    assert (profile.input_price, profile.cached_price, profile.output_price) == (1320, 44, 3960)
    assert profile.max_output == ledger.SENTIMENT_LOW_MAX_OUTPUT and profile.effort == "low"
    quick = ledger.request_profile(body("deepseek-flash", effort="none",
                                        limit=ledger.MAX_OUTPUT, name="relevance_prefilter"))
    assert quick.version.endswith(":" + ledger.PRICE_VERSION) and quick.input_price == 300
    # Saved Anthropic price versions keep their original names.
    assert ledger.anthropic_version("claude-opus-5-5", "x") == "anthropic:claude-opus-5-5:x"


def test_request_translation_keeps_the_contract():
    chat = D.to_chat(body())
    assert chat["model"] == "deepseek-v4-pro" and chat["max_tokens"] == ledger.SENTIMENT_LOW_MAX_OUTPUT
    assert chat["response_format"] == {"type": "json_object"} and chat["stream"] is False
    assert chat["reasoning_effort"] == "low"
    system, user = chat["messages"]
    assert system["role"] == "system" and "json object" in system["content"]
    assert '"additionalProperties": false' in system["content"]
    assert user == {"role": "user", "content": "Authored report"}
    assert D.to_chat(body(effort="medium", limit=ledger.REASONING_MAX_OUTPUT,
                          name="other"))["reasoning_effort"] == "high"
    quick = D.to_chat(body("deepseek-flash", effort="none", limit=ledger.MAX_OUTPUT,
                           name="relevance_prefilter"))
    assert quick["reasoning_effort"] == "none"


def test_response_translation_and_cache_aware_charge():
    call = ledger.execute("deepseek-test", "test", body(),
                          transport=lambda _: D.from_completion(
                              completion('```json\n{"items": []}\n```'), "deepseek-v4-pro"))
    assert call["status"] == "settled"
    assert call["input_tokens"] == 1000 and call["cached_tokens"] == 300
    assert call["charged_nano_usd"] == 700 * 1320 + 300 * 44 + 500 * 3960
    assert json.loads(call["response_body"]["output"][0]["content"][0]["text"]) == {"items": []}


def test_truncated_empty_or_foreign_answers_are_not_accepted():
    capped = D.from_completion(completion('{"items": [', finish="length"), "deepseek-v4-pro")
    assert capped["status"] == "incomplete"
    assert capped["incomplete_details"] == {"reason": "max_output_tokens"}
    empty = D.from_completion(completion(""), "deepseek-v4-pro")
    assert empty["status"] == "incomplete" and empty["output"] == []
    assert empty["incomplete_details"] == {"reason": "empty_content"}
    dated = D.from_completion(completion("{}", model="deepseek-v4-pro-0813"), "deepseek-v4-pro")
    assert dated["model"] == "deepseek-v4-pro" and dated["provider_model"] == "deepseek-v4-pro-0813"
    foreign = D.from_completion(completion("{}", model="other-model"), "deepseek-v4-pro")
    assert foreign["model"] == "other-model"
