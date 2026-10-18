"""Optional sentiment-only model: setting, price profile and request contract. Offline."""
import pytest
from thesis.providers import ledger, settings
from thesis.research import sentiment_tasks as T
from test_model_budget import clean_model_ledger  # noqa: F401  (autouse ledger reset)
from test_sentiment_quality_validation import threaded_packet


LUNA = settings.OPENAI_SENTIMENT_MODEL


def test_sentiment_model_defaults_to_the_main_model_and_accepts_only_luna_on_openai():
    main = settings.OPENAI_REASONING_MODEL
    assert settings.sentiment_choice({}, "openai", main) == main
    assert settings.sentiment_choice({"THESIS_SENTIMENT_MODEL": main}, "openai", main) == main
    assert settings.sentiment_choice({"THESIS_SENTIMENT_MODEL": LUNA}, "openai", main) == LUNA
    for values, provider in (({"THESIS_SENTIMENT_MODEL": LUNA}, "anthropic"),
                             ({"THESIS_SENTIMENT_MODEL": "gpt-5.4-mini-2026-03-17"}, "openai"),
                             ({"THESIS_SENTIMENT_MODEL": "deepseek-v4-pro"}, "openai")):
        with pytest.raises(settings.ProviderConfigError):
            settings.sentiment_choice(values, provider, main)


def test_luna_is_priced_only_for_low_effort_sentiment_at_official_rates(monkeypatch):
    monkeypatch.setattr(T, "SENTIMENT_MODEL", LUNA)
    body = T.request_for("tone", threaded_packet())
    assert body["model"] == LUNA
    profile = ledger.request_profile(body)
    assert profile.version == ledger.LUNA_SENTIMENT_PRICE_VERSION
    assert (profile.input_price, profile.cached_price, profile.output_price, profile.cache_write_price) == (100, 10, 500, 125)
    assert (profile.max_output, profile.effort) == (ledger.SENTIMENT_LOW_MAX_OUTPUT, "low")
    luna = ledger.estimate(body)
    monkeypatch.setattr(T, "SENTIMENT_MODEL", settings.OPENAI_REASONING_MODEL)
    main = ledger.estimate(T.request_for("tone", threaded_packet()))
    assert 0 < luna < main / 20
    other = dict(body, max_output_tokens=ledger.REASONING_MAX_OUTPUT, reasoning={"effort": "medium"})
    other["text"] = dict(body["text"], format=dict(body["text"]["format"], name="business_brief"))
    with pytest.raises(ValueError, match="only for low-effort sentiment"):
        ledger.request_profile(other)


def test_saved_luna_profile_is_found_by_its_recorded_version():
    assert ledger.price_profile(LUNA, ledger.LUNA_SENTIMENT_PRICE_VERSION).model == LUNA
    with pytest.raises(ValueError):
        ledger.price_profile(LUNA, ledger.SENTIMENT_LOW_PRICE_VERSION)


def test_luna_call_settles_at_luna_rates_including_cache_writes(monkeypatch):
    monkeypatch.setattr(T, "SENTIMENT_MODEL", LUNA)
    body = T.request_for("tone", threaded_packet())

    def provider(request):
        assert request["model"] == LUNA
        return dict(id="resp_luna", model=LUNA, service_tier="default", status="completed",
                    usage=dict(input_tokens=1000, output_tokens=200, total_tokens=1200,
                               input_tokens_details=dict(cached_tokens=300, cache_write_tokens=100),
                               output_tokens_details=dict(reasoning_tokens=50)),
                    output=[dict(type="message", content=[dict(type="output_text", text='{"items":[]}')])])
    result = ledger.execute("luna-settle", "test", body, transport=provider)
    assert result["charged_nano_usd"] == 600 * 100 + 300 * 10 + 100 * 125 + 200 * 500

    def other(request):
        return dict(provider(request), id="resp_other", model="gpt-6-luna-2026-11-01")
    with pytest.raises(Exception):
        ledger.execute("luna-unpriced", "test", body, transport=other)


def test_luna_sentiment_requests_get_the_main_model_time_limit(monkeypatch):
    from thesis.providers.openai import request_timeout
    monkeypatch.setattr(T, "SENTIMENT_MODEL", LUNA)
    luna = request_timeout(T.request_for("tone", threaded_packet()))
    monkeypatch.setattr(T, "SENTIMENT_MODEL", settings.OPENAI_REASONING_MODEL)
    main = request_timeout(T.request_for("tone", threaded_packet()))
    assert luna.read == main.read == 180
