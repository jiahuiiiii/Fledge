"""Owner-linked Telegram outbox adapted from Kestrel's connection/alert workflow.

Local polling replaces its public webhook. A durable sending state plus a shared
database advisory lock prevents concurrent sends; ambiguous sends are not retried.
"""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import secrets
import re
from uuid import uuid4
from thesis.db import transaction, one, rows
from thesis import review_digest
from . import telegram_transport as transport
from .telegram_message import render, TEST_MESSAGE, plain


def clock():
    return datetime.now(timezone.utc)


def fingerprint(key):
    return sha256(key.encode()).hexdigest()


@contextmanager
def serial(owner, *, wait=True):
    # Lock lives on its own connection so send intent can commit BEFORE the HTTP
    # call. A process crash releases the lock without losing that intent.
    with transaction(owner) as conn:
        fn = "pg_advisory_xact_lock" if wait else "pg_try_advisory_xact_lock"
        result = one(conn, f"SELECT {fn}(hashtextextended(%s,0)) AS locked", ("telegram:" + str(owner),))
        yield wait or result["locked"]


def config(conn, owner):
    return one(conn, "SELECT * FROM telegram_settings WHERE owner_id=%s", (owner,)) or {}


def status(owner):
    key = transport.token()
    with transaction(owner) as conn:
        cfg = config(conn, owner)
        linked = bool(cfg.get("chat_id"))
        matches = bool(key and cfg.get("bot_fingerprint") == fingerprint(key))
        history = rows(conn, review_digest.EVENTS + """SELECT d.id,d.kind,d.status,d.created_at,d.attempted_at,d.sent_at,d.attempts,d.error,d.retry_at,i.symbol
          FROM telegram_deliveries d LEFT JOIN events e ON e.owner_id=d.owner_id AND e.kind=d.kind AND e.id=d.event_id
          LEFT JOIN instruments i ON i.id=e.instrument_id
          WHERE d.owner_id=%(owner)s ORDER BY d.created_at DESC,d.id DESC LIMIT 15""", dict(owner=owner))
        return dict(configured=bool(key), linked=linked, token_changed=linked and not matches,
                    enabled=bool(cfg.get("enabled")), active=bool(cfg.get("enabled") and matches),
                    chat_label=cfg.get("chat_label"), bot_username=cfg.get("bot_username"),
                    pending=bool(cfg.get("link_hash") and cfg["link_expires_at"] > clock()),
                    deliveries=history,
                    watches=one(conn, "SELECT count(*) AS n FROM news_watches WHERE owner_id=%s AND enabled", (owner,))["n"])


def key_required():
    key = transport.token()
    if not key:
        raise ValueError("Add TELEGRAM_BOT_TOKEN to this project’s .env file, then try again.")
    return key


def linked_required(cfg, key):
    if not cfg.get("chat_id") or cfg.get("bot_fingerprint") != fingerprint(key):
        raise ValueError("Connect your Telegram chat with the current bot token first.")


def connect(owner):
    key = key_required()
    with serial(owner):
        with transaction(owner) as conn:
            if config(conn, owner).get("chat_id"):
                raise ValueError("Disconnect the current chat before connecting another.")
        bot = transport.call(key, "getMe", {})
        if not isinstance(bot, dict) or not bot.get("is_bot") or not re.fullmatch(r"[A-Za-z0-9_]{5,32}", bot.get("username", "")):
            raise ValueError("Telegram did not return a valid bot identity.")
        webhook = transport.call(key, "getWebhookInfo", {})
        if not isinstance(webhook, dict) or webhook.get("url") != "":
            raise ValueError("This bot has a webhook for another app. Create a dedicated Thesis bot; its webhook has not been changed.")
        nonce = secrets.token_urlsafe(32)
        expires = clock() + timedelta(minutes=10)
        with transaction(owner) as conn:
            old = config(conn, owner)
            offset = old.get("update_offset", 0) if old.get("bot_fingerprint") == fingerprint(key) else 0
            conn.execute("""INSERT INTO telegram_settings(owner_id,bot_fingerprint,bot_username,link_hash,link_expires_at,update_offset)
              VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT(owner_id) DO UPDATE SET
              bot_fingerprint=EXCLUDED.bot_fingerprint,bot_username=EXCLUDED.bot_username,
              link_hash=EXCLUDED.link_hash,link_expires_at=EXCLUDED.link_expires_at,update_offset=EXCLUDED.update_offset""",
              (owner, fingerprint(key), bot["username"], fingerprint(nonce), expires, offset))
        return dict(url=f"https://t.me/{bot['username']}?start={nonce}", expires_at=expires, bot_username=bot["username"])


def check_connection(owner):
    key = key_required()
    with serial(owner):
        with transaction(owner) as conn:
            cfg = config(conn, owner)
        if cfg.get("chat_id"):
            linked_required(cfg, key)
            return status(owner)
        if not cfg.get("link_hash") or cfg["link_expires_at"] <= clock() or cfg.get("bot_fingerprint") != fingerprint(key):
            raise ValueError("The connection link expired. Create a new link and press Start in Telegram.")
        updates = transport.call(key, "getUpdates", dict(offset=cfg["update_offset"], limit=100, timeout=5, allowed_updates=["message"]))
        if not isinstance(updates, list):
            raise ValueError("Telegram did not return connection updates. Try again.")
        offset = cfg["update_offset"]
        target = None
        for update in updates:
            if not isinstance(update, dict) or type(update.get("update_id")) is not int:
                continue
            offset = max(offset, update["update_id"] + 1)
            message = update.get("message") or {}
            chat, sender = message.get("chat") or {}, message.get("from") or {}
            text = message.get("text") or ""
            match = re.fullmatch(r"/start(?:@[A-Za-z0-9_]+)? ([A-Za-z0-9_-]{43})", text) if isinstance(text, str) else None
            if (match and target is None and chat.get("type") == "private"
                and type(chat.get("id")) is int and chat["id"] > 0 and sender.get("id") == chat["id"]
                and not sender.get("is_bot") and not message.get("forward_origin") and not message.get("via_bot")
                and secrets.compare_digest(fingerprint(match[1]), cfg["link_hash"])):
                target = dict(id=chat["id"], label=plain(("@" + sender["username"]) if sender.get("username") else sender.get("first_name", "Private chat"), 80))
        with transaction(owner) as conn:
            conn.execute("UPDATE telegram_settings SET update_offset=%s WHERE owner_id=%s", (offset, owner))
            if target and cfg["link_expires_at"] > clock():
                conn.execute("UPDATE telegram_settings SET chat_id=%s,chat_label=%s,link_hash=NULL,link_expires_at=NULL,enabled=false WHERE owner_id=%s", (target["id"], target["label"], owner))
    return status(owner)


def configure(owner, enabled):
    if type(enabled) is not bool:
        raise ValueError("Choose whether Telegram delivery is on or off.")
    with serial(owner):
        with transaction(owner) as conn:
            cfg = config(conn, owner)
            if enabled:
                linked_required(cfg, key_required())
            if cfg and bool(cfg.get("enabled")) != enabled:
                conn.execute("UPDATE telegram_settings SET enabled=%s,enabled_at=CASE WHEN %s THEN clock_timestamp() ELSE NULL END WHERE owner_id=%s", (enabled, enabled, owner))
            if not enabled:
                conn.execute("UPDATE telegram_deliveries SET status='cancelled',error='Delivery paused before sending.' WHERE owner_id=%s AND status='queued'", (owner,))
    return status(owner)


def disconnect(owner):
    with serial(owner):
        with transaction(owner) as conn:
            conn.execute("UPDATE telegram_settings SET enabled=false,enabled_at=NULL,chat_id=NULL,chat_label=NULL,link_hash=NULL,link_expires_at=NULL WHERE owner_id=%s", (owner,))
            conn.execute("UPDATE telegram_deliveries SET status='cancelled',error='Chat disconnected before sending.' WHERE owner_id=%s AND status='queued'", (owner,))
    return status(owner)


def test_message(owner):
    with serial(owner):
        with transaction(owner) as conn:
            linked_required(config(conn, owner), key_required())
            recent = one(conn, "SELECT id FROM telegram_deliveries WHERE owner_id=%s AND kind='test' AND created_at>clock_timestamp()-interval '1 minute'", (owner,))
            if recent:
                raise ValueError("A connection test was requested recently. Check its delivery status before trying again.")
            conn.execute("INSERT INTO telegram_deliveries(id,owner_id,kind,event_id,event_at) VALUES(%s,%s,'test',%s,clock_timestamp())", (uuid4(), owner, uuid4()))
    return status(owner)


def event(conn, owner, kind, identity):
    row = one(conn, review_digest.EVENTS + "SELECT * FROM events WHERE kind=%(kind)s AND id=%(id)s", dict(owner=owner, kind=kind, id=identity))
    if not row:
        return None
    detail = review_digest.details(conn, owner, [row])[0]
    state = one(conn, "SELECT mode FROM instrument_state WHERE instrument_id=%s", (row["instrument_id"],))
    detail["detail"]["fictional"] = bool(state and state["mode"] == "recorded")
    if kind == "condition" and not detail["detail"].get("withheld"):
        from thesis import service
        manifest = one(conn, "SELECT manifest FROM evaluations WHERE owner_id=%s AND id=%s", (owner, detail["detail"]["evaluation_id"]))
        ids = {str(i) for i in manifest["manifest"].get("document_ids", [])} if manifest else set()
        detail["detail"]["sources"] = [dict(id=str(d["id"]), url=d["url"], source=d["source_name"]) for d in service.permitted_documents(conn, clock(), row["instrument_id"]) if str(d["id"]) in ids]
    if row.get("version_id") and kind in {"idea", "condition"}:
        current = one(conn, "SELECT 1 FROM thesis_versions v JOIN theses t ON t.id=v.thesis_id AND t.owner_id=v.owner_id WHERE v.owner_id=%s AND v.id=%s AND v.revision=t.revision AND t.status<>'archived'", (owner, row["version_id"]))
        if not current:
            return None
    return detail


def run_once(owner):
    with serial(owner, wait=False) as acquired:
        if not acquired:
            return False
        now = clock()
        # A previous process may have died after HTTP dispatch but before saving
        # Telegram's acknowledgement. Never automatically resend that message.
        with transaction(owner) as conn:
            conn.execute("UPDATE telegram_deliveries SET status='uncertain',error='The app stopped before confirming delivery. Check Telegram; this message will not be resent.' WHERE owner_id=%s AND status='sending'", (owner,))
            cfg = config(conn, owner)
            key = transport.token()
            if not cfg.get("chat_id") or not key or cfg.get("bot_fingerprint") != fingerprint(key):
                return False
            if cfg.get("enabled"):
                candidates = rows(conn, review_digest.EVENTS + """SELECT e.* FROM events e WHERE created_at>%(start)s AND created_at>%(fresh)s
                  AND NOT EXISTS(SELECT 1 FROM telegram_deliveries d WHERE d.owner_id=e.owner_id AND d.kind=e.kind AND d.event_id=e.id)
                  ORDER BY created_at,id LIMIT 100""", dict(owner=owner, start=cfg["enabled_at"], fresh=now-timedelta(hours=24)))
                for item in candidates:
                    conn.execute("INSERT INTO telegram_deliveries(id,owner_id,kind,event_id,event_at) VALUES(%s,%s,%s,%s,%s) ON CONFLICT(owner_id,kind,event_id) DO NOTHING", (uuid4(), owner, item["kind"], item["id"], item["created_at"]))
            if cfg.get("next_send_at") and cfg["next_send_at"] > now:
                return False
            job = one(conn, "SELECT * FROM telegram_deliveries WHERE owner_id=%s AND status='queued' AND (retry_at IS NULL OR retry_at<=%s) ORDER BY created_at,id LIMIT 1", (owner, now))
            if not job:
                return False
            why = None
            if job["event_at"] < now-timedelta(hours=24):
                why = "Alert is older than 24 hours; review it in Updates."
            elif job["kind"] != "test" and not cfg["enabled"]:
                why = "Telegram delivery is paused."
            elif job["kind"] != "test":
                try:
                    record = event(conn, owner, job["kind"], job["event_id"])
                    if not record:
                        why = "The saved idea changed or the original alert is unavailable."
                    elif record["detail"].get("withheld"):
                        why = "Source access changed; alert details were not forwarded."
                    else:
                        message = render(record)
                except (ValueError, KeyError, TypeError, IndexError):
                    why = "This alert could not be prepared safely. Review its evidence in Updates."
            else:
                message = TEST_MESSAGE
            if why:
                conn.execute("UPDATE telegram_deliveries SET status='skipped',error=%s WHERE id=%s AND owner_id=%s", (why, job["id"], owner))
                return True
            conn.execute("UPDATE telegram_deliveries SET status='sending',attempts=attempts+1,attempted_at=%s,retry_at=NULL,error=NULL WHERE id=%s AND owner_id=%s", (now, job["id"], owner))
            conn.execute("UPDATE telegram_settings SET next_send_at=%s WHERE owner_id=%s", (now+timedelta(seconds=5), owner))
        # Intent is committed, while serial() still fences pause/disconnect and
        # other workers. No message body or destination is stored in the outbox.
        try:
            result = transport.call(key, "sendMessage", dict(chat_id=cfg["chat_id"], text=message, parse_mode="HTML", link_preview_options=dict(is_disabled=True), protect_content=True, allow_paid_broadcast=False))
            if not isinstance(result, dict) or type(result.get("message_id")) is not int or result.get("chat", {}).get("id") != cfg["chat_id"]:
                raise transport.TelegramError("uncertain", "Telegram did not confirm delivery. Check your chat; no automatic retry.")
        except Exception as exc:
            known = isinstance(exc, transport.TelegramError)
            retry = known and exc.code == "rate_limited" and job["attempts"] < 2
            state = "queued" if retry else ("failed" if known and exc.code in {"rejected", "rate_limited"} else "uncertain")
            reason = str(exc) if known else "Delivery could not be confirmed. Check Telegram; no automatic retry."
            with transaction(owner) as conn:
                limited = known and exc.code == "rate_limited"
                due = clock()+timedelta(seconds=exc.retry_after) if limited else None
                conn.execute("UPDATE telegram_deliveries SET status=%s,error=%s,retry_at=%s WHERE id=%s AND owner_id=%s", (state, reason, due if retry else None, job["id"], owner))
                if limited:
                    conn.execute("UPDATE telegram_settings SET next_send_at=%s WHERE owner_id=%s", (due, owner))
                elif known and exc.code == "rejected":
                    conn.execute("UPDATE telegram_settings SET enabled=false,enabled_at=NULL WHERE owner_id=%s", (owner,))
                    conn.execute("UPDATE telegram_deliveries SET status='cancelled',error='Delivery paused after Telegram rejected a request.' WHERE owner_id=%s AND status='queued'", (owner,))
            return True
        with transaction(owner) as conn:
            conn.execute("UPDATE telegram_deliveries SET status='sent',message_id=%s,sent_at=clock_timestamp() WHERE id=%s AND owner_id=%s", (result["message_id"], job["id"], owner))
        return True
