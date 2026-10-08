"""Direct Responses API with no retries, redirects, tools or credential logging."""

import httpx
from .settings import live_key, REASONING_MODEL


class ProviderFailure(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def request_timeout(body):
    from .ledger import request_profile, SENTIMENT_DEPTH_PRICE_VERSION

    # The isolated high-reasoning trial can take longer. App routes retain their
    # original limits; connect/write/pool waits stay bounded independently.
    standard = 180 if body.get("model") == REASONING_MODEL else 60
    read = (
        420
        if body.get("model") == REASONING_MODEL
        and request_profile(body).version == SENTIMENT_DEPTH_PRICE_VERSION
        else standard
    )
    return httpx.Timeout(standard, connect=15, read=read)


def send(body, call_id, *, owner=None):
    # Key and configuration are checked before the caller reserves a dispatch too.
    key = live_key(body.get("model"))
    from .ledger import authorize_dispatch

    authorize_dispatch(call_id, body, owner=owner)
    try:
        with httpx.Client(
            timeout=request_timeout(body),
            follow_redirects=False,
            transport=httpx.HTTPTransport(retries=0),
        ) as client:
            response = client.post(
                "https://api.openai.com/v1/responses",
                headers={
                    "Authorization": "Bearer " + key,
                    # This durable UUID is unique to one dispatch, not a retry key.
                    # Support can look it up even if no response ID reaches us.
                    "X-Client-Request-Id": str(call_id),
                },
                json=body,
            )
        if response.status_code != 200:
            # Do not print potentially sensitive provider bodies. Unknown charges
            # remain reserved even for explicit errors; no automatic retry.
            raise ProviderFailure(f"http_{response.status_code}")
        return response.json()
    except ProviderFailure:
        raise
    except httpx.TimeoutException:
        raise ProviderFailure("transport_timeout") from None
    except httpx.RequestError:
        raise ProviderFailure("transport_error") from None
    except Exception:
        raise ProviderFailure("transport_or_response_error") from None
