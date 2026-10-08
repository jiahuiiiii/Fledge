"""Small Telegram Bot API boundary. Never log URLs, credentials or provider bodies."""
import json
import re
from urllib.error import HTTPError
from urllib.request import Request, build_opener, HTTPRedirectHandler
from thesis.providers.settings import settings


class TelegramError(ValueError):
    def __init__(self, code, message, retry_after=None):
        super().__init__(message)
        self.code = code
        self.retry_after = retry_after


def token():
    value = settings().get("TELEGRAM_BOT_TOKEN", "").strip()
    if not re.fullmatch(r"[0-9]{5,20}:[A-Za-z0-9_-]{20,100}", value):
        return ""
    return value


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def call(key, method, payload):
    if method not in {"getMe", "getWebhookInfo", "getUpdates", "sendMessage"}:
        raise ValueError("Unsupported Telegram operation.")
    sending = method == "sendMessage"
    fallback = "uncertain" if sending else "unavailable"
    code = None
    try:
        request = Request(
            f"https://api.telegram.org/bot{key}/{method}",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"}, method="POST",
        )
        try:
            response = build_opener(NoRedirect()).open(request, timeout=12)
        except HTTPError as exc:
            code = exc.code
            response = exc
        with response:
            raw = response.read(1_000_001)
        if len(raw) > 1_000_000:
            raise ValueError("Response too large")
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("Invalid response")
        if data.get("ok") is True and code is None:
            result = data.get("result")
            if sending and (
                not isinstance(result, dict)
                or type(result.get("message_id")) is not int
                or result.get("chat", {}).get("id") != payload["chat_id"]
            ):
                raise ValueError("Missing delivery acknowledgement")
            return result
        code = data.get("error_code", code)
        if code == 429:
            delay = data.get("parameters", {}).get("retry_after")
            if type(delay) is int and 1 <= delay <= 86400:
                raise TelegramError("rate_limited", "Telegram asked us to wait before sending again.", delay)
        if code in {400, 401, 403, 404, 409, 429}:
            messages = {
                401: "Telegram rejected the bot token. Check .env and reconnect.",
                403: "Telegram blocked delivery. Open your bot chat and unblock it, then reconnect.",
                409: "Another app is receiving this bot’s updates. Use a dedicated Thesis bot.",
            }
            raise TelegramError("rejected", messages.get(code, "Telegram rejected this request. Check the connection before trying again."))
        raise ValueError("Unconfirmed response")
    except TelegramError:
        raise
    except Exception:
        raise TelegramError(fallback, "Telegram could not confirm this request. Delivery will not be repeated automatically." if sending else "Telegram could not be reached. Try checking the connection again.") from None
