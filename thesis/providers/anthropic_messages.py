"""Anthropic Messages transport for the same priced request contract as OpenAI.

Request builders keep producing the provider-neutral body that the ledger
prices and identifies (system + user text, a strict JSON schema, an output
allowance and an effort). This module translates it to the Messages API and
translates the answer back, so parsing, validation and accounting are shared.
No automatic retries, tools or credential logging.
"""

import json
import hashlib
from copy import deepcopy

import anthropic

from .settings import live_key

# Anthropic's structured-output compiler accepts at most this many fields with
# union types (anyOf or type lists). Larger schemas go in the instructions.
MAX_UNION_FIELDS = 16
# Answer formats Anthropic rejected because their compiled grammar is too large
# (e.g. per-source enums in big sentiment batches). Later requests in this
# process describe the schema in the instructions instead of a failed attempt.
GRAMMAR_TOO_LARGE = set()
SENTIMENT_WIRE = "source-sentiment-keyed-2"
NON_EVENT_KINDS = {"opinion_only", "conditional_only", "question_only", "insufficient_detail", "not_applicable"}


def shared_sentiment_schema(schema):
    """Share repeated field types; exact source membership stays runtime-validated.

    Hundreds of repeated per-source passage enums can exceed the provider's
    internal grammar limit even with zero optional fields or union parameters.
    The prompt still supplies the original IDs; render enforces them unchanged.
    """
    evidence_fields = {"passages", "previous_passages", "context_passages",
                       "item_passages", "reference_passages"}
    def normalize(value):
        if isinstance(value, dict):
            result = {}
            for k,v in value.items():
                if k == "properties":
                    result[k] = {}
                    for field, prop in v.items():
                        prop = normalize(prop)
                        if field in evidence_fields:
                            prop["items"] = {"type": "string"}
                        if field in {"passage_id", "reference_id"}:
                            prop.pop("enum", None)
                        result[k][field] = prop
                else:
                    result[k] = normalize(v)
            return result
        if isinstance(value, list):
            return [normalize(v) for v in value]
        return value
    definitions, identities = {}, {}
    for field in ("items", "coverage_links"):
        for label,value in schema["properties"][field]["properties"].items():
            value = normalize(value)
            identity = json.dumps(value, sort_keys=True)
            if identity not in identities:
                name = "SentimentSlot" + str(len(identities))
                identities[identity] = name
                definitions[name] = value
            schema["properties"][field]["properties"][label] = {"$ref": "#/$defs/"+identities[identity]}
    schema["$defs"] = definitions
    return schema


def sentiment_schema(body):
    """Fixed slots avoid the combinatorial grammar of an array of source unions.

    This is a transport encoding of the existing output, not a new classifier.
    Source IDs and empty non-event evidence are code-owned on this wire.
    """
    original = body["text"]["format"]["schema"]
    branches = original.get("properties", {}).get("items", {}).get("items", {}).get("anyOf")
    if body["text"]["format"]["name"] != "source_sentiment" or not branches:
        return original, None
    from thesis.research.sentiment_reliability import enabled
    if not enabled():
        return original, None
    schema = deepcopy(original)
    objects = {}
    for branch in branches:
        item = deepcopy(branch)
        labels = item.get("properties", {}).get("id", {}).get("enum", [])
        if len(labels) != 1 or labels[0] in objects:
            return original, None
        label = labels[0]
        item["properties"].pop("id")
        item["required"] = [k for k in item["required"] if k != "id"]
        claims = item["properties"].get("price_claims", {}).get("items", {}).get("properties", {})
        if "direction_text" in claims:
            claims["direction_text"] = dict(type="string", description=
                "Exact explicit direction words, or an empty string when no direction is stated.")
        reporting = item["properties"].get("reporting")
        if reporting:
            event, non_event = deepcopy(reporting), deepcopy(reporting)
            event["properties"]["kind"]["enum"] = ["reported_event", "unconfirmed_event"]
            non_event["properties"]["kind"]["enum"] = sorted(NON_EVENT_KINDS)
            non_event["properties"]["impact"]["enum"] = ["not_stated"]
            non_event["properties"].pop("passages")
            non_event["required"] = [k for k in non_event["required"] if k != "passages"]
            item["properties"]["reporting"] = {"anyOf": [event, non_event]}
        objects[label] = item
    schema["properties"]["items"] = dict(type="object", properties=objects,
        required=list(objects), additionalProperties=False)
    links = {}
    for branch in original["properties"]["coverage_links"].get("items", {}).get("anyOf", []):
        link = deepcopy(branch)
        label = link["properties"]["item_id"]["enum"][0]
        link["properties"].pop("item_id")
        link["required"] = [k for k in link["required"] if k != "item_id"]
        links[label] = {"anyOf": [link, {"type": "null"}]}
    schema["properties"]["coverage_links"] = dict(type="object", properties=links,
        required=list(links), additionalProperties=False)
    return shared_sentiment_schema(schema), dict(items=list(objects), links=list(links))


def sentiment_text(text, layout):
    """Decode only an exact keyed result. Invalid output stays invalid and settled."""
    try:
        value = json.loads(text)
        items, links = value["items"], value["coverage_links"]
        if (set(value) != {"items", "coverage_links"}
                or not isinstance(items, dict) or set(items) != set(layout["items"])
                or not isinstance(links, dict) or set(links) != set(layout["links"])
                or any(not isinstance(v, dict) or "id" in v for v in items.values())
                or any(v is not None and (not isinstance(v, dict) or "item_id" in v) for v in links.values())):
            return text
        labels = []
        for key in layout["items"]:
            item = dict(items[key], id=key)
            claims = item.get("price_claims")
            if isinstance(claims, list):
                item["price_claims"] = [dict(c, direction_text=None)
                    if isinstance(c, dict) and c.get("direction_text") == "" else c for c in claims]
            reporting = item.get("reporting")
            if isinstance(reporting, dict) and reporting.get("kind") in NON_EVENT_KINDS:
                item["reporting"] = dict(reporting, passages=reporting.get("passages", []))
            labels.append(item)
        return json.dumps(dict(items=labels, coverage_links=[dict(v, item_id=k)
                          for k, v in links.items() if v is not None]), ensure_ascii=False)
    except (ValueError, TypeError, KeyError, RecursionError):
        return text


class ProviderFailure(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def union_fields(schema):
    count = 0
    stack = [schema]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            if "anyOf" in node or isinstance(node.get("type"), list):
                count += 1
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    return count


def thinking_for(model, effort):
    """Map the contract's effort to Anthropic thinking + effort settings."""
    if effort != "none":
        return None, effort  # Adaptive thinking is the default on these models.
    # 'none' was the OpenAI quick check without reasoning: keep it minimal.
    if model.startswith("claude-haiku"):
        return {"type": "disabled"}, "low"
    if model.startswith("claude-sonnet"):
        return {"type": "between_tools"}, "low"
    return None, "low"  # Opus 5.5 cannot disable thinking; low effort keeps it short.


def to_messages(body, *, structured=None):
    from .ledger import request_profile

    system, user = (m["content"] for m in body["input"])
    wire_schema, layout = sentiment_schema(body)
    schema = anthropic.transform_schema(wire_schema)
    grammar_key = (body["model"], hashlib.sha256(json.dumps(schema, sort_keys=True).encode()).hexdigest())
    if structured is None:
        structured = (union_fields(schema) <= MAX_UNION_FIELDS
                      and grammar_key not in GRAMMAR_TOO_LARGE)
    blocks = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
    if layout:
        blocks.append({"type": "text", "text": (
            "Transport output format: items and coverage_links are keyed objects, not arrays. "
            "Use exactly the source-label keys in the schema. Item keys supply id; omit id inside items. "
            "Coverage keys supply item_id; use null for no link. Social items have no reporting field. "
            "News non-event reporting omits passages; code supplies the empty list. "
            "Price direction_text uses an empty string for no stated direction; code restores null. "
            "All evidence still uses only the exact permitted passage IDs. "
            "The supplied JSON schema defines the output shape.")})
    if not structured:
        blocks.append({"type": "text", "text": (
            "Return only one JSON object, with no other text or code fences, that "
            "validates against this JSON schema:\n" + json.dumps(schema, sort_keys=True))})
    thinking, effort = thinking_for(body["model"], request_profile(body).effort)
    params = dict(
        model=body["model"],
        max_tokens=body["max_output_tokens"],
        system=blocks,
        messages=[{"role": "user", "content": user}],
        output_config={"effort": effort, **(
            {"format": {"type": "json_schema", "schema": schema}} if structured else {})},
    )
    if thinking:
        params["thinking"] = thinking
    return params, structured


def json_text(text, structured):
    if structured:
        return text
    # Instruction-only JSON: keep the single object, drop any surrounding fence.
    start, end = text.find("{"), text.rfind("}")
    return text[start:end + 1] if start != -1 and end > start else text


def from_message(message, structured, *, layout=None):
    """Shape the answer like a Responses API result for the shared parser/ledger."""
    text = "".join(b.text for b in message.content if b.type == "text")
    finished = message.stop_reason in ("end_turn", "stop_sequence")
    usage = message.usage
    read = usage.cache_read_input_tokens or 0
    written = usage.cache_creation_input_tokens or 0
    original = json_text(text, structured)
    output_text = sentiment_text(original, layout) if layout else original
    return dict(
        id=message.id,
        model=message.model,
        provider="anthropic",
        status="completed" if finished else "incomplete",
        incomplete_details=None if finished else dict(
            reason="max_output_tokens" if message.stop_reason == "max_tokens" else message.stop_reason),
        stop_reason=message.stop_reason,
        structured_output=structured,
        **(dict(wire_format=SENTIMENT_WIRE, wire_text=text) if layout else {}),
        output=[dict(type="message", content=[
            dict(type="output_text", text=output_text)])] if text else [],
        usage=dict(
            input_tokens=usage.input_tokens + read + written,
            input_tokens_details=dict(cached_tokens=read, cache_write_tokens=written),
            output_tokens=usage.output_tokens,
        ),
        service_tier="default",
    )


def send(body, call_id, *, owner=None):
    key = live_key(body.get("model"))
    from .ledger import authorize_dispatch, PRICE_VERSION, request_profile

    authorize_dispatch(call_id, body, owner=owner)
    params, structured = to_messages(body)
    schema, layout = sentiment_schema(body)
    schema = anthropic.transform_schema(schema)
    grammar_key = (body["model"], hashlib.sha256(json.dumps(schema, sort_keys=True).encode()).hexdigest())
    quick = request_profile(body).version.endswith(":" + PRICE_VERSION)
    try:
        client = anthropic.Anthropic(
            api_key=key, max_retries=0, timeout=300.0 if quick else 600.0)  # each new answer format is compiled first
        headers = {"X-Client-Request-Id": str(call_id)}  # one dispatch, not a retry key
        try:
            message = client.messages.create(**params, extra_headers=headers)
        except anthropic.BadRequestError as exc:
            # A 400 is rejected before any generation, so nothing is charged.
            # Only this specific rejection is re-sent, once, without the grammar.
            complexity_rejection = any(reason in str(exc.message).lower() for reason in (
                "grammar is too large", "schema is too complex for compilation"))
            if not (structured and complexity_rejection):
                raise
            GRAMMAR_TOO_LARGE.add(grammar_key)
            params, structured = to_messages(body, structured=False)
            message = client.messages.create(**params, extra_headers=headers)
        return from_message(message, structured, layout=layout)
    except anthropic.APITimeoutError:
        raise ProviderFailure("transport_timeout") from None
    except anthropic.APIConnectionError:
        raise ProviderFailure("transport_error") from None
    except anthropic.APIStatusError as exc:
        # Do not print provider bodies. No automatic retry.
        raise ProviderFailure(f"http_{exc.status_code}") from None
    except Exception:
        raise ProviderFailure("transport_or_response_error") from None
