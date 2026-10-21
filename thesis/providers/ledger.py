"""Durable global reservations; provider call identity is independent of job leases."""

import hashlib
import json
from dataclasses import dataclass
from uuid import uuid4
from psycopg.types.json import Jsonb
from thesis.db import transaction, one
from .settings import (
    OPENAI_MODEL as MODEL,
    OPENAI_REASONING_MODEL as REASONING_MODEL,
    TWIN_PRICES,
    provider_for,
    OPENAI_EXPLAINER_MODEL,
    EXPLAINER_MODELS,
    OPENAI_SENTIMENT_MODEL,
)

NANO = 1_000_000_000
# Official GPT-5.4 Mini standard pricing, checked 2026-10-01:
# $0.75 input / $0.075 cached / $4.50 output per million tokens.
PRICE_VERSION = "openai-gpt-5.4-mini-standard-20261001"
INPUT_PRICE, CACHED_PRICE, OUTPUT_PRICE = 750, 75, 4500
MAX_OUTPUT = 2000
REASONING_MAX_OUTPUT = 6000
SENTIMENT_MAX_OUTPUT = 9000
SENTIMENT_PRICE_VERSION = "openai-gpt-5.4-sentiment-9000-20261002"
SENTIMENT_LOW_MAX_OUTPUT = 12000
SENTIMENT_LOW_PRICE_VERSION = "openai-gpt-5.4-sentiment-low-12000-20261009"
SENTIMENT_DEPTH_MAX_OUTPUT = 12000
SENTIMENT_DEPTH_PRICE_VERSION = "openai-gpt-5.4-sentiment-depth-high-20261003"
FINDING_CHECK_MAX_OUTPUT = 9000
FINDING_CHECK_PRICE_VERSION = "openai-gpt-5.4-finding-check-high-20261003"
IDEA_EVIDENCE_MAX_OUTPUT = 9000
IDEA_EVIDENCE_PRICE_VERSION = "openai-gpt-5.4-idea-evidence-9000-20261003"
REASONING_PRICE_VERSION = "openai-gpt-5.4-standard-20261002"
MAX_REQUEST_BYTES = 64000
MOVE_EXPLAINER_PRICE_VERSION = "move-explainer-low-2000-20261017"
ARTICLE_BRIEF_MAX_OUTPUT = 4000


@dataclass(frozen=True)
class PriceProfile:
    model: str
    version: str
    input_price: int
    cached_price: int
    output_price: int
    max_output: int
    effort: str
    # Anthropic bills 5-minute cache writes above the input rate.
    cache_write_price: int | None = None


# Keep historical profiles unchanged: a saved charge or recovery uses the
# reservation's model and price version, never the currently selected route.
PROFILES = (
    PriceProfile(
        MODEL,
        PRICE_VERSION,
        INPUT_PRICE,
        CACHED_PRICE,
        OUTPUT_PRICE,
        MAX_OUTPUT,
        "none",
    ),
    # Official standard GPT-5.4 pricing checked 2026-10-02: $2.50/$0.25/$15 per 1M.
    # Output tokens already include reasoning tokens; never add that subset twice.
    PriceProfile(
        REASONING_MODEL,
        REASONING_PRICE_VERSION,
        2500,
        250,
        15000,
        REASONING_MAX_OUTPUT,
        "medium",
    ),
    # Separate bounded request profile; old reservations retain the 6000-token cap.
    PriceProfile(
        REASONING_MODEL,
        SENTIMENT_PRICE_VERSION,
        2500,
        250,
        15000,
        SENTIMENT_MAX_OUTPUT,
        "medium",
    ),
    # Explicit evaluation-only route. Existing app methods keep their profiles.
    # GPT-5.4 high effort uses the same standard token rates (checked 2026-10-03).
    PriceProfile(
        REASONING_MODEL,
        FINDING_CHECK_PRICE_VERSION,
        2500,
        250,
        15000,
        FINDING_CHECK_MAX_OUTPUT,
        "high",
    ),
    PriceProfile(
        REASONING_MODEL,
        IDEA_EVIDENCE_PRICE_VERSION,
        2500,
        250,
        15000,
        IDEA_EVIDENCE_MAX_OUTPUT,
        "medium",
    ),
    # Evaluation-only profile; no app request builder selects it.
    PriceProfile(
        REASONING_MODEL,
        SENTIMENT_DEPTH_PRICE_VERSION,
        2500,
        250,
        15000,
        SENTIMENT_DEPTH_MAX_OUTPUT,
        "high",
    ),
    # Owner-authorized classification tuning; old profiles/charges stay exact.
    PriceProfile(
        REASONING_MODEL,
        SENTIMENT_LOW_PRICE_VERSION,
        2500,
        250,
        15000,
        SENTIMENT_LOW_MAX_OUTPUT,
        "low",
    ),
)


OPENAI_PROFILES = PROFILES


def twin_version(provider, model, base):
    return f"{provider}:{model}:{base}"


def anthropic_version(model, base):
    return twin_version("anthropic", model, base)


# Each OpenAI request family has a twin per other priced model: same output
# allowance and effort, that provider's token prices. OpenAI profiles stay
# unchanged, and saved "anthropic:<model>:<family>" versions keep their names.
PROFILES = OPENAI_PROFILES + tuple(
    PriceProfile(
        model,
        twin_version(provider, model, base.version),
        prices[0],
        prices[1],
        prices[3],
        base.max_output,
        base.effort,
        prices[2],
    )
    for provider, table in TWIN_PRICES.items()
    for model, prices in table.items()
    for base in OPENAI_PROFILES
)

# Separate role/family: these profiles do not change any historical allowance.
# GPT-5.5 standard $5/$0.50/$30 per 1M, checked 2026-10-17:
# https://developers.openai.com/api/docs/models/gpt-5.5
PROFILES += (
    PriceProfile(OPENAI_EXPLAINER_MODEL, MOVE_EXPLAINER_PRICE_VERSION,
                 5000, 500, 30000, MAX_OUTPUT, "low"),
    PriceProfile("claude-opus-5-5", twin_version("anthropic", "claude-opus-5-5", MOVE_EXPLAINER_PRICE_VERSION),
                 4000, 200, 20000, MAX_OUTPUT, "low", 5000),
)


# Sentiment-only route. GPT-6 Luna standard $0.10 input / $0.01 cached /
# $0.125 cache write / $0.50 output per 1M, checked 2026-10-18:
# https://developers.openai.com/api/docs/models/gpt-6-luna
LUNA_SENTIMENT_PRICE_VERSION = "openai-gpt-6-luna-sentiment-low-12000-20261018"
PROFILES += (
    PriceProfile(OPENAI_SENTIMENT_MODEL, LUNA_SENTIMENT_PRICE_VERSION,
                 100, 10, 500, SENTIMENT_LOW_MAX_OUTPUT, "low", 125),
)

# Quoted brief of a fetched alert article (owner request 20 Oct 2026), same
# GPT-6 Luna rates; its own version so existing sentiment profiles stay exact.
LUNA_ARTICLE_BRIEF_PRICE_VERSION = "openai-gpt-6-luna-article-brief-low-4000-20261020"
PROFILES += (
    PriceProfile(OPENAI_SENTIMENT_MODEL, LUNA_ARTICLE_BRIEF_PRICE_VERSION,
                 100, 10, 500, ARTICLE_BRIEF_MAX_OUTPUT, "low", 125),
)


def price_profile(model, version=None):
    for profile in PROFILES:
        if profile.model == model and (version is None or profile.version == version):
            return profile
    raise ValueError("Unsupported model or price version")


def _family(body):
    """The OpenAI price version whose request contract this body follows."""
    text = body.get("text")
    fmt = text.get("format") if isinstance(text, dict) else None
    name = fmt.get("name") if isinstance(fmt, dict) else None
    limit, effort = body.get("max_output_tokens"), body.get("reasoning")
    if limit == MAX_OUTPUT and effort == {"effort": "low"} and name == "price_move_explainer":
        return MOVE_EXPLAINER_PRICE_VERSION
    if limit == SENTIMENT_LOW_MAX_OUTPUT and effort == {"effort": "low"} and name == "source_sentiment":
        return SENTIMENT_LOW_PRICE_VERSION
    if limit == ARTICLE_BRIEF_MAX_OUTPUT and effort == {"effort": "low"} and name == "alert_article_brief":
        return LUNA_ARTICLE_BRIEF_PRICE_VERSION
    if limit == SENTIMENT_DEPTH_MAX_OUTPUT and effort == {"effort": "high"} and name == "source_sentiment_reasoning_eval":
        return SENTIMENT_DEPTH_PRICE_VERSION
    if limit == IDEA_EVIDENCE_MAX_OUTPUT and effort == {"effort": "medium"} and name == "idea_answer_evidence":
        return IDEA_EVIDENCE_PRICE_VERSION
    if limit == FINDING_CHECK_MAX_OUTPUT and effort == {"effort": "high"} and name == "finding_evidence_check":
        return FINDING_CHECK_PRICE_VERSION
    # Only the named sentiment format opts into the larger finite output allowance.
    if limit == SENTIMENT_MAX_OUTPUT and name == "source_sentiment":
        return SENTIMENT_PRICE_VERSION
    return None


def request_profile(body):
    model = body.get("model")
    family = _family(body)
    provider = provider_for(model)
    if family == MOVE_EXPLAINER_PRICE_VERSION:
        if model not in EXPLAINER_MODELS:
            raise ValueError("Only a priced move-explainer model can use this request family")
        return price_profile(model, family if provider == "openai" else twin_version(provider, model, family))
    if model == OPENAI_EXPLAINER_MODEL:
        raise ValueError("This model is priced only for the bounded move explainer")
    if provider != "openai":
        if family is None:
            # Quick-check and other bounded routes keep their own allowance.
            family = (PRICE_VERSION if body.get("max_output_tokens") == MAX_OUTPUT
                      and body.get("reasoning") == {"effort": "none"} else REASONING_PRICE_VERSION)
        return price_profile(model, twin_version(provider, model, family))
    if family is not None and model == REASONING_MODEL:
        return price_profile(REASONING_MODEL, family)
    if model == OPENAI_SENTIMENT_MODEL:
        if family == LUNA_ARTICLE_BRIEF_PRICE_VERSION:
            return price_profile(model, family)
        if family != SENTIMENT_LOW_PRICE_VERSION:
            raise ValueError("This model is priced only for low-effort sentiment readings")
        return price_profile(model, LUNA_SENTIMENT_PRICE_VERSION)
    return price_profile(model)


class BudgetBlocked(ValueError):
    pass


class WakePaused(BudgetBlocked):
    """Nothing was reserved or sent: the computer woke from sleep moments ago."""


def canonical(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def estimate(body):
    # For text-only BPE input, UTF-8 bytes upper-bound tokens; the entire JSON
    # (including schema) plus 8192 tokens leaves a deliberately large framing margin.
    size = len(canonical(body).encode())
    profile = request_profile(body)
    if size > MAX_REQUEST_BYTES:
        raise ValueError("Unsupported model or oversized request")
    if (
        body.get("max_output_tokens") != profile.max_output
        or body.get("service_tier") != "default"
    ):
        raise ValueError("Output and pricing bounds are required")
    allowed = {
        "model",
        "store",
        "service_tier",
        "max_output_tokens",
        "reasoning",
        "input",
        "text",
    }
    if (
        set(body) != allowed
        or body["store"] is not False
        or body["reasoning"] != {"effort": profile.effort}
    ):
        raise ValueError("Only the priced stateless text request contract is allowed")
    messages = body["input"]
    if not isinstance(messages, list) or len(messages) != 2:
        raise ValueError("Exactly one system and one user text message are required")
    for message, role in zip(messages, ("system", "user")):
        if (
            not isinstance(message, dict)
            or set(message) != {"role", "content"}
            or message["role"] != role
            or not isinstance(message["content"], str)
        ):
            raise ValueError(
                "Images, files and remote conversation context are not permitted"
            )
    text = body["text"]
    if not isinstance(text, dict) or set(text) != {"format"}:
        raise ValueError("A bounded structured output format is required")
    fmt = text["format"]
    if (
        not isinstance(fmt, dict)
        or set(fmt) != {"type", "name", "strict", "schema"}
        or fmt["type"] != "json_schema"
        or fmt["strict"] is not True
        or not isinstance(fmt["name"], str)
        or not isinstance(fmt["schema"], dict)
    ):
        raise ValueError("A bounded JSON schema is required")
    return (
        size + 8192
    ) * profile.input_price + profile.max_output * profile.output_price


def snapshot(conn=None):
    if conn is None:
        with transaction() as c:
            return snapshot(c)
    budget = one(conn, "SELECT * FROM model_budget WHERE singleton")
    totals = one(
        conn,
        "SELECT * FROM model_global_totals()",
    )
    return dict(
        authorization=budget["approval_reference"],
        cap_usd=str(budget["cap_nano_usd"] / NANO),
        spent_usd=str(totals["spent"] / NANO),
        reserved_usd=str(totals["held"] / NANO),
        accounted_maximum_usd=str(
            one(conn, "SELECT model_accounted_maximum() n")["n"] / NANO
        ),
        remaining_usd=str(
            (budget["cap_nano_usd"] - totals["spent"] - totals["held"]) / NANO
        ),
        **one(conn, "SELECT * FROM model_activity()"),
        calls=totals["calls"],
        unresolved=totals["unresolved"],
    )


REDISPATCH = ":redispatch:"


def find(conn, request_key):
    """Return the saved result for this request, including a later resend of it."""
    return one(
        conn,
        """SELECT * FROM model_calls WHERE status='settled' AND
           (request_key=%s OR starts_with(request_key, %s)) ORDER BY created_at DESC LIMIT 1""",
        (request_key, request_key + REDISPATCH),
    )


def _test_copy_cap():
    """None on the original installation (no cap, by owner decision) and in
    offline tests; a test copy's own total cap otherwise."""
    import os
    from .settings import original_installation, test_copy_cap
    if os.environ.get("THESIS_TEST_OFFLINE") == "true" or original_installation():
        return None
    return test_copy_cap()


def reserve(request_key, purpose, body, *, owner=None):
    # Owner decision 13 Oct 2026: no spending cap and no charge-review block.
    # Every call is still recorded; a failed request can simply be sent again.
    maximum = estimate(body)
    profile = request_profile(body)
    digest = hashlib.sha256(canonical(body).encode()).hexdigest()
    with transaction(owner) as conn:
        conn.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended('thesis-model-budget',0))"
        )
        previous = one(
            conn, "SELECT * FROM model_calls WHERE request_key=%s", (request_key,)
        )
        key = request_key
        if previous:
            price_profile(previous["model"], previous["price_version"])
            if previous["model"] != profile.model:
                raise ValueError("Stored request does not match its priced model")
            if previous["request_hash"] != digest:
                raise ValueError(
                    "Request identity cannot be reused for different input"
                )
            saved = find(conn, request_key)
            if saved:
                return saved, False
            if one(
                conn,
                """SELECT 1 x FROM model_calls WHERE status='dispatched'
                   AND created_at>now()-interval '15 minutes'
                   AND (request_key=%s OR starts_with(request_key, %s))""",
                (request_key, request_key + REDISPATCH),
            ):
                raise BudgetBlocked("This AI request is already running")
            count = one(
                conn,
                "SELECT count(*) n FROM model_calls WHERE starts_with(request_key, %s)",
                (request_key + REDISPATCH,),
            )["n"]
            key = f"{request_key}{REDISPATCH}{count + 1}"
        cap = _test_copy_cap()
        if cap is not None:
            # A test copy stops before its total (spent + still held + this call's
            # maximum) could pass the cap it set for itself.
            totals = one(conn, "SELECT * FROM model_global_totals()")
            if totals["spent"] + totals["held"] + maximum > int(cap * NANO):
                raise BudgetBlocked(
                    f"This test copy reached its US${cap} AI spending cap. Raise "
                    "THESIS_TEST_COPY_CAP_USD in .env and restart to continue."
                )
        call = one(
            conn,
            """INSERT INTO model_calls(id,request_key,request_hash,purpose,model,price_version,
          request_body,reserved_nano_usd,status,owner_id) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,'dispatched',%s) RETURNING *""",
            (
                uuid4(),
                key,
                digest,
                purpose,
                profile.model,
                profile.version,
                Jsonb(body),
                maximum,
                owner,
            ),
        )
    return call, True


def integer(value):
    if type(value) is not int or value < 0:
        raise ValueError("Invalid provider usage")
    return value


def settle(call, response, *, owner=None):
    with transaction(owner) as conn:
        current = one(
            conn, "SELECT * FROM model_calls WHERE id=%s FOR UPDATE", (call["id"],)
        )
        if not current:
            raise ValueError("Provider reservation is unavailable")
        profile = price_profile(current["model"], current["price_version"])
        if current["request_body"].get("model") != profile.model:
            raise ValueError("Stored request does not match its priced model")
        usage = response.get("usage") or {}
        input_tokens = integer(usage.get("input_tokens"))
        output_tokens = integer(usage.get("output_tokens"))
        cached = integer(
            (usage.get("input_tokens_details") or {}).get("cached_tokens", 0)
        )
        reasoning = integer(
            (usage.get("output_tokens_details") or {}).get("reasoning_tokens", 0)
        )
        written = integer(
            (usage.get("input_tokens_details") or {}).get("cache_write_tokens", 0)
        )
        if (
            cached + written > input_tokens
            or output_tokens > profile.max_output
            or reasoning > output_tokens
        ):
            raise ValueError("Provider usage exceeded declared bounds")
        if (
            response.get("model") != profile.model
            or response.get("service_tier", "default") != "default"
        ):
            raise ValueError("Provider returned unpriced model or service tier")
        if not response.get("id"):
            raise ValueError("Provider response identity is missing")
        charge = (
            (input_tokens - cached - written) * profile.input_price
            + cached * profile.cached_price
            + written * (profile.cache_write_price or profile.input_price)
            + output_tokens * profile.output_price
        )
        if charge > current["reserved_nano_usd"]:
            raise ValueError("Provider usage exceeded its reservation")
        if current["status"] == "settled":
            if current["response_id"] != response["id"]:
                raise ValueError("A settled call cannot accept a different response")
            return current
        return one(
            conn,
            """UPDATE model_calls SET status='settled',response_id=%s,response_body=%s,
           input_tokens=%s,cached_tokens=%s,output_tokens=%s,charged_nano_usd=%s,finished_at=now(),error_code=NULL
           WHERE id=%s RETURNING *""",
            (
                response["id"],
                Jsonb(response),
                input_tokens,
                cached,
                output_tokens,
                charge,
                call["id"],
            ),
        )


def unresolved(call, code, *, owner=None):
    with transaction(owner) as conn:
        conn.execute(
            "UPDATE model_calls SET status='unresolved',error_code=%s WHERE id=%s AND status<>'settled'",
            (code, call["id"]),
        )


def execute(request_key, purpose, body, *, transport=None, owner=None):
    live = transport is None
    if live:
        from .settings import live_key

        provider = provider_for(body.get("model"))
        if provider == "anthropic":
            from .anthropic_messages import send
        elif provider == "deepseek":
            from .deepseek import send
        else:
            from .openai import send

        live_key(body.get("model"))  # Configuration failures never reserve a call.
        from thesis import wake
        # A request sent before the connection returns is cut off and can never be resent.
        if not wake.settled():
            raise WakePaused("The computer woke from sleep moments ago. Nothing was sent; "
                             "this check runs again once the connection is back.")
    call, dispatch = reserve(request_key, purpose, body, owner=owner)
    if not dispatch:
        return call
    try:
        response = send(body, call["id"], owner=owner) if live else transport(body)
        return settle(call, response, owner=owner)
    except BaseException as exc:
        # Even a keyboard interrupt is ambiguous after dispatch. Never release it
        # or retry automatically. A hard kill leaves 'dispatched' with the same block.
        code = getattr(exc, "code", "interrupted_or_invalid_usage")
        unresolved(call, code, owner=owner)
        raise BudgetBlocked(
            "The AI request failed before a result was saved. Try again."
        ) from None


def authorize_dispatch(call_id, body, *, owner=None):
    """Consume one durable network attempt; even direct HTTP use needs this proof."""
    digest = hashlib.sha256(canonical(body).encode()).hexdigest()
    with transaction(owner) as conn:
        call = one(conn, "SELECT * FROM model_calls WHERE id=%s FOR UPDATE", (call_id,))
        if not call or call["status"] != "dispatched" or call["request_hash"] != digest:
            raise BudgetBlocked(
                "No matching unused reservation for this provider request"
            )
        profile = price_profile(call["model"], call["price_version"])
        if (
            profile.model != body.get("model")
            or estimate(body) > call["reserved_nano_usd"]
        ):
            raise BudgetBlocked(
                "Reservation does not cover this priced provider request"
            )
        if one(
            conn, "SELECT call_id FROM model_dispatches WHERE call_id=%s", (call_id,)
        ):
            raise BudgetBlocked("This provider request was already dispatched")
        conn.execute("INSERT INTO model_dispatches(call_id) VALUES(%s)", (call_id,))
