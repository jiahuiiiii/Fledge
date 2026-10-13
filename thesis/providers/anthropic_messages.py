"""Anthropic Messages transport for the same priced request contract as OpenAI.

Request builders keep producing the provider-neutral body that the ledger
prices and identifies (system + user text, a strict JSON schema, an output
allowance and an effort). This module translates it to the Messages API and
translates the answer back, so parsing, validation and accounting are shared.
No automatic retries, tools or credential logging.
"""

import json

import anthropic

from .settings import live_key

# Anthropic's structured-output compiler accepts at most this many fields with
# union types (anyOf or type lists). Larger schemas go in the instructions.
MAX_UNION_FIELDS = 16
# Answer formats Anthropic rejected because their compiled grammar is too large
# (e.g. per-source enums in big sentiment batches). Later requests in this
# process describe the schema in the instructions instead of a failed attempt.
GRAMMAR_TOO_LARGE = set()


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
    schema = anthropic.transform_schema(body["text"]["format"]["schema"])
    if structured is None:
        structured = (union_fields(schema) <= MAX_UNION_FIELDS
                      and body["text"]["format"]["name"] not in GRAMMAR_TOO_LARGE)
    blocks = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
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


def from_message(message, structured):
    """Shape the answer like a Responses API result for the shared parser/ledger."""
    text = "".join(b.text for b in message.content if b.type == "text")
    finished = message.stop_reason in ("end_turn", "stop_sequence")
    usage = message.usage
    read = usage.cache_read_input_tokens or 0
    written = usage.cache_creation_input_tokens or 0
    return dict(
        id=message.id,
        model=message.model,
        provider="anthropic",
        status="completed" if finished else "incomplete",
        incomplete_details=None if finished else dict(
            reason="max_output_tokens" if message.stop_reason == "max_tokens" else message.stop_reason),
        stop_reason=message.stop_reason,
        structured_output=structured,
        output=[dict(type="message", content=[
            dict(type="output_text", text=json_text(text, structured))])] if text else [],
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
            if not (structured and "grammar is too large" in str(exc.message)):
                raise
            GRAMMAR_TOO_LARGE.add(body["text"]["format"]["name"])
            params, structured = to_messages(body, structured=False)
            message = client.messages.create(**params, extra_headers=headers)
        return from_message(message, structured)
    except anthropic.APITimeoutError:
        raise ProviderFailure("transport_timeout") from None
    except anthropic.APIConnectionError:
        raise ProviderFailure("transport_error") from None
    except anthropic.APIStatusError as exc:
        # Do not print provider bodies. No automatic retry.
        raise ProviderFailure(f"http_{exc.status_code}") from None
    except Exception:
        raise ProviderFailure("transport_or_response_error") from None
