"""Anthropic Messages translation and pricing. No keys are loaded and no HTTP is sent."""

import json
from types import SimpleNamespace
import pytest
from thesis.providers import anthropic_messages as A, ledger, settings
from test_model_budget import clean_model_ledger  # noqa: F401  (autouse ledger reset)


def body(model="claude-opus-5-5", *, effort="low", limit=ledger.SENTIMENT_LOW_MAX_OUTPUT,
         name="source_sentiment", schema=None):
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
        text={"format": {"type": "json_schema", "name": name, "strict": True, "schema": schema or {
            "type": "object",
            "properties": {"items": {"type": "array", "items": {"type": "string", "enum": ["a"]},
                                     "minItems": 2, "maxItems": 0}},
            "required": ["items"],
            "additionalProperties": False,
        }}},
    )


def message(text, *, stop="end_turn", model="claude-opus-5-5", read=0, written=0):
    return SimpleNamespace(
        id="msg_mock", model=model, stop_reason=stop,
        content=[SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(input_tokens=1000, cache_read_input_tokens=read,
                              cache_creation_input_tokens=written, output_tokens=500),
    )


def test_provider_and_models_come_from_settings(monkeypatch):
    monkeypatch.setenv("THESIS_MODEL_PROVIDER", "anthropic")
    monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
    monkeypatch.delenv("ANTHROPIC_REASONING_MODEL", raising=False)
    assert settings._models() == ("anthropic", "claude-haiku-5-5", "claude-opus-5-5")
    monkeypatch.setenv("ANTHROPIC_REASONING_MODEL", "claude-sonnet-5-5")
    assert settings._models()[2] == "claude-sonnet-5-5"
    monkeypatch.setenv("ANTHROPIC_REASONING_MODEL", "claude-unpriced")
    with pytest.raises(ValueError, match="no recorded anthropic price"):
        settings._models()
    monkeypatch.setenv("THESIS_MODEL_PROVIDER", "openai")
    assert settings._models() == ("openai", settings.OPENAI_MODEL, settings.OPENAI_REASONING_MODEL)


def test_each_request_family_has_an_anthropic_price_and_the_same_allowance():
    profile = ledger.request_profile(body())
    assert profile.version == ledger.anthropic_version(
        "claude-opus-5-5", ledger.SENTIMENT_LOW_PRICE_VERSION)
    assert (profile.input_price, profile.cached_price, profile.cache_write_price,
            profile.output_price) == (4000, 200, 5000, 20000)
    assert profile.max_output == ledger.SENTIMENT_LOW_MAX_OUTPUT and profile.effort == "low"
    quick = ledger.request_profile(body("claude-haiku-5-5", effort="none",
                                        limit=ledger.MAX_OUTPUT, name="relevance_prefilter"))
    assert quick.version.endswith(":" + ledger.PRICE_VERSION) and quick.input_price == 100
    # OpenAI pricing is unchanged.
    openai = ledger.request_profile(dict(body(settings.OPENAI_REASONING_MODEL)))
    assert openai.version == ledger.SENTIMENT_LOW_PRICE_VERSION


def test_request_translation_keeps_the_contract():
    params, structured = A.to_messages(body())
    assert structured
    assert params["model"] == "claude-opus-5-5" and params["max_tokens"] == ledger.SENTIMENT_LOW_MAX_OUTPUT
    assert params["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert params["messages"] == [{"role": "user", "content": "Authored report"}]
    assert params["output_config"]["effort"] == "low" and "thinking" not in params
    items = params["output_config"]["format"]["schema"]["properties"]["items"]
    # Unsupported array limits move into a description; app code still validates.
    assert "maxItems" not in items and "minItems" not in items
    # The quick check runs without thinking where the model allows it.
    params, _ = A.to_messages(body("claude-haiku-5-5", effort="none",
                                   limit=ledger.MAX_OUTPUT, name="relevance_prefilter"))
    assert params["thinking"] == {"type": "disabled"} and params["output_config"]["effort"] == "low"


def test_large_union_schemas_fall_back_to_instructions():
    branches = [{"type": "string", "enum": [str(n)]} for n in range(2)]
    schema = {"type": "object", "additionalProperties": False, "required": [f"f{n}" for n in range(17)],
              "properties": {f"f{n}": {"anyOf": branches} for n in range(17)}}
    params, structured = A.to_messages(body(schema=schema))
    assert not structured and "format" not in params["output_config"]
    assert "JSON schema" in params["system"][1]["text"]
    reply = A.from_message(message('```json\n{"f0": "1"}\n```'), structured)
    assert reply["output"][0]["content"][0]["text"] == '{"f0": "1"}'


def test_response_translation_and_cache_aware_charge():
    request = body()
    call = ledger.execute("anthropic-test", "test", request,
                          transport=lambda _: A.from_message(message('{"items": []}', read=300, written=200), True))
    assert call["status"] == "settled"
    assert call["input_tokens"] == 1500 and call["cached_tokens"] == 300
    # 1000 uncached input + 300 cache reads + 200 cache writes + 500 output.
    assert call["charged_nano_usd"] == 1000 * 4000 + 300 * 200 + 200 * 5000 + 500 * 20000
    assert json.loads(call["response_body"]["output"][0]["content"][0]["text"]) == {"items": []}


def test_truncated_or_refused_answers_are_incomplete():
    capped = A.from_message(message('{"items": [', stop="max_tokens"), True)
    assert capped["status"] == "incomplete"
    assert capped["incomplete_details"] == {"reason": "max_output_tokens"}
    refused = A.from_message(message("", stop="refusal"), True)
    assert refused["status"] == "incomplete" and refused["output"] == []


@pytest.mark.parametrize("reason", ["grammar is too large", "Schema is too complex for compilation."])
def test_too_large_grammar_is_resent_once_with_instruction_json(monkeypatch, reason):
    import anthropic
    import httpx2

    sent = []

    def rejection():
        request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
        response = httpx2.Response(400, request=request)
        return anthropic.BadRequestError(
            reason,
            response=response, body=None)

    class Messages:
        def create(self, **params):
            sent.append(params)
            if "format" in params["output_config"]:
                raise rejection()
            return message('{"items": []}')

    class Client:
        def __init__(self, **_):
            self.messages = Messages()

    monkeypatch.setattr(A, "live_key", lambda _: "fictional-key")
    monkeypatch.setattr(ledger, "authorize_dispatch", lambda *a, **k: None)
    monkeypatch.setattr(A.anthropic, "Anthropic", Client)
    monkeypatch.setattr(A, "GRAMMAR_TOO_LARGE", set())
    reply = A.send(body(), "call-1")
    assert len(sent) == 2 and "format" in sent[0]["output_config"]
    assert "format" not in sent[1]["output_config"] and "JSON schema" in sent[1]["system"][1]["text"]
    assert reply["structured_output"] is False and reply["status"] == "completed"
    # The same answer format now goes straight to instructions; other 400s are not re-sent.
    sent.clear()
    A.send(body(), "call-2")
    assert len(sent) == 1 and "format" not in sent[0]["output_config"]

    class Refusing(Messages):
        def create(self, **params):
            sent.append(params)
            raise anthropic.BadRequestError("Other problem", response=rejection().response, body=None)

    class Client2:
        def __init__(self, **_):
            self.messages = Refusing()

    monkeypatch.setattr(A.anthropic, "Anthropic", Client2)
    sent.clear()
    with pytest.raises(A.ProviderFailure, match="http_400"):
        A.send(body(name="other_format"), "call-3")
    assert len(sent) == 1


def sentiment_case():
    from test_sentiment_reliability import sample, answer
    from thesis.research import sentiment
    packet = sample()
    request = sentiment.request_for(packet)
    request["model"] = "claude-haiku-5-5"
    raw = json.loads(sentiment.response_text(answer(packet)))
    return packet, request, raw


def wire_answer(raw, layout):
    from copy import deepcopy
    value = deepcopy(raw)
    items = {}
    for item in value["items"]:
        key = item.pop("id")
        for claim in item.get("price_claims", []):
            if claim["direction_text"] is None:
                claim["direction_text"] = ""
        reporting = item.get("reporting")
        if reporting and reporting["kind"] in A.NON_EVENT_KINDS and reporting["passages"] == []:
            reporting.pop("passages")
        items[key] = item
    links = {k: None for k in layout["links"]}
    for link in value["coverage_links"]:
        links[link.pop("item_id")] = link
    return dict(items=items, coverage_links=links)


def test_fixed_source_slots_preserve_request_and_prevent_wrong_channel_fields():
    from copy import deepcopy
    packet, request, raw = sentiment_case()
    before = deepcopy(request)
    params, structured = A.to_messages(request)
    assert request == before and structured
    schema, layout = A.sentiment_schema(request)
    assert layout["items"] == [s["label"] for s in packet["sources"]]
    assert schema["properties"]["items"]["required"] == layout["items"]
    for source in packet["sources"]:
        slot = schema["properties"]["items"]["properties"][source["label"]]
        slot = schema["$defs"][slot["$ref"].split("/")[-1]]
        assert slot["additionalProperties"] is False and "id" not in slot["properties"]
        if source["channel"] == "social":
            assert "reporting" not in slot["properties"]
        else:
            event, non_event = slot["properties"]["reporting"]["anyOf"]
            assert "passages" in event["required"]
            assert "passages" not in non_event["properties"]
            assert non_event["properties"]["impact"]["enum"] == ["not_stated"]
    assert A.union_fields(params["output_config"]["format"]["schema"]) <= A.MAX_UNION_FIELDS
    assert len(json.dumps(schema)) < len(json.dumps(request["text"]["format"]["schema"])) / 2


def test_keyed_transport_round_trip_preserves_labels_links_prices_and_raw_provider_text():
    from thesis.research import sentiment
    packet, request, raw = sentiment_case()
    social = next(i for i,s in zip(raw["items"],packet["sources"]) if s["channel"] == "social")
    social["price_claims"] = [dict(passage_id="p1", amount_text="$42", kind="other", direction_text=None)]
    news = next(i for i,s in zip(raw["items"],packet["sources"]) if s["channel"] == "news")
    news["reporting"] = dict(kind="opinion_only", impact="not_stated", passages=[])
    _, layout = A.sentiment_schema(request)
    link_key = layout["links"][0]
    raw["coverage_links"] = [dict(item_id=link_key, reference_id="item_1", relation="adds_detail",
                                 explanation="Authored relation", item_passages=["p1"], reference_passages=["p1"])]
    text = json.dumps(wire_answer(raw, layout))
    translated = A.from_message(message(text,model="claude-haiku-5-5"), True, layout=layout)
    assert json.loads(sentiment.response_text(dict(response_body=translated))) == raw
    assert translated["wire_text"] == text and translated["wire_format"] == A.SENTIMENT_WIRE
    assert translated["usage"]["output_tokens"] == 500  # Never recalculate usage from converted text.


@pytest.mark.parametrize("fault", ["missing", "unknown", "id_inside", "link_unknown", "broken", "event_missing_passages"])
def test_keyed_decoder_does_not_repair_structural_failures(fault):
    from thesis.research import sentiment
    packet, request, raw = sentiment_case()
    _, layout = A.sentiment_schema(request)
    wire = wire_answer(raw,layout)
    first = layout["items"][0]
    if fault == "missing": wire["items"].pop(first)
    if fault == "unknown": wire["items"]["invented"] = wire["items"].pop(first)
    if fault == "id_inside": wire["items"][first]["id"] = "invented"
    if fault == "link_unknown": wire["coverage_links"]["invented"] = None
    if fault == "event_missing_passages":
        wire["items"][first]["reporting"] = dict(kind="reported_event",impact="adverse")
    text = "{" if fault == "broken" else json.dumps(wire)
    translated = A.from_message(message(text),True,layout=layout)
    assert translated["status"] == "completed"  # A paid invalid response remains settled, not an uncertain charge.
    with pytest.raises(ValueError): sentiment.render(dict(response_body=translated),packet)


def test_keyed_decoder_keeps_fabricated_evidence_for_the_real_validator_to_reject():
    from thesis.research import sentiment
    packet, request, raw = sentiment_case()
    raw["items"][0]["passages"] = ["invented"]
    _, layout=A.sentiment_schema(request)
    text=json.dumps(wire_answer(raw,layout))
    translated=A.from_message(message(text),True,layout=layout)
    with pytest.raises(ValueError,match="original source"):
        sentiment.render(dict(response_body=translated),packet)


def test_grammar_failure_cache_is_specific_to_model_and_schema(monkeypatch):
    import hashlib
    import anthropic
    _, request, _ = sentiment_case()
    schema,_=A.sentiment_schema(request)
    digest=hashlib.sha256(json.dumps(anthropic.transform_schema(schema),sort_keys=True).encode()).hexdigest()
    monkeypatch.setattr(A,"GRAMMAR_TOO_LARGE",{(request["model"],digest)})
    assert not A.to_messages(request)[1]
    assert A.to_messages(dict(request,model="claude-sonnet-5-5"))[1]
    changed=json.loads(json.dumps(request))
    changed["text"]["format"]["schema"]["properties"]["items"]["items"]["anyOf"][0]["properties"]["topic"]["enum"] = ["general"]
    assert A.to_messages(changed)[1]


def test_phase_one_rollback_keeps_the_legacy_anthropic_wire(monkeypatch):
    _, request, _ = sentiment_case()
    monkeypatch.setenv("THESIS_SENTIMENT_RELIABILITY","false")
    schema,layout=A.sentiment_schema(request)
    assert layout is None and schema == request["text"]["format"]["schema"]
