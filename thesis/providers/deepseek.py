"""DeepSeek Chat Completions transport for the same priced request contract.

Request builders keep producing the provider-neutral body that the ledger
prices and identifies. This module translates it to DeepSeek's chat API and
the answer back to the Responses shape, so parsing, validation and accounting
are shared. DeepSeek's JSON mode guarantees a JSON object but not a schema, so
the schema goes in the instructions and app code still validates every answer.
Fixed host, no automatic retries, redirects, tools or credential logging.
"""

import json

import httpx

from .settings import live_key, MODEL

URL = "https://api.deepseek.com/chat/completions"
# DeepSeek's reasoning_effort has none/low/high/max; it treats medium as high.
EFFORTS = {"none": "none", "low": "low", "medium": "high", "high": "high"}


class ProviderFailure(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def to_chat(body):
    from .ledger import request_profile

    system, user = (m["content"] for m in body["input"])
    schema = body["text"]["format"]["schema"]
    # JSON mode requires the word "json" in the prompt.
    instructions = (
        system + "\n\nReturn only one json object, with no other text or code "
        "fences, that validates against this JSON schema:\n"
        + json.dumps(schema, sort_keys=True)
    )
    return dict(
        model=body["model"],
        messages=[
            {"role": "system", "content": instructions},
            {"role": "user", "content": user},
        ],
        max_tokens=body["max_output_tokens"],
        reasoning_effort=EFFORTS[request_profile(body).effort],
        response_format={"type": "json_object"},
        stream=False,
    )


def json_text(text):
    # Keep the single object, dropping any surrounding fence or stray text.
    start, end = text.find("{"), text.rfind("}")
    return text[start:end + 1] if start != -1 and end > start else text


def from_completion(data, model):
    """Shape the answer like a Responses API result for the shared parser/ledger."""
    choice = (data.get("choices") or [{}])[0]
    text = (choice.get("message") or {}).get("content") or ""
    finish = choice.get("finish_reason")
    # DeepSeek documents occasional empty JSON-mode answers; treat them as unfinished.
    finished = finish == "stop" and bool(text.strip())
    reason = None if finished else (
        "max_output_tokens" if finish == "length"
        else "empty_content" if finish in ("stop", None) else finish)
    usage = data.get("usage") or {}
    reported = data.get("model") or ""
    return dict(
        id=data.get("id"),
        # Version-labelled names (e.g. a dated Flash build) are still the priced
        # model; anything that is not DeepSeek keeps its name and fails settlement.
        model=model if reported.startswith("deepseek") else reported,
        provider="deepseek",
        provider_model=reported,
        status="completed" if finished else "incomplete",
        incomplete_details=reason and dict(reason=reason),
        stop_reason=finish,
        structured_output=False,
        output=[dict(type="message", content=[
            dict(type="output_text", text=json_text(text))])] if text else [],
        usage=dict(
            input_tokens=usage.get("prompt_tokens"),
            input_tokens_details=dict(cached_tokens=usage.get("prompt_cache_hit_tokens", 0)),
            output_tokens=usage.get("completion_tokens"),
            output_tokens_details=dict(reasoning_tokens=(
                usage.get("completion_tokens_details") or {}).get("reasoning_tokens", 0)),
        ),
        service_tier="default",
    )


def send(body, call_id, *, owner=None):
    key = live_key(body.get("model"))
    from .ledger import authorize_dispatch

    authorize_dispatch(call_id, body, owner=owner)
    quick = body.get("model") == MODEL
    try:
        with httpx.Client(
            timeout=httpx.Timeout(120 if quick else 600, connect=15),
            follow_redirects=False,
            transport=httpx.HTTPTransport(retries=0),
        ) as client:
            response = client.post(
                URL,
                headers={
                    "Authorization": "Bearer " + key,
                    # This durable UUID is unique to one dispatch, not a retry key.
                    "X-Client-Request-Id": str(call_id),
                },
                json=to_chat(body),
            )
        if response.status_code != 200:
            # Do not print provider bodies. No automatic retry.
            raise ProviderFailure(f"http_{response.status_code}")
        return from_completion(response.json(), body["model"])
    except ProviderFailure:
        raise
    except httpx.TimeoutException:
        raise ProviderFailure("transport_timeout") from None
    except httpx.RequestError:
        raise ProviderFailure("transport_error") from None
    except Exception:
        raise ProviderFailure("transport_or_response_error") from None
