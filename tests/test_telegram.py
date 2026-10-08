"""Telegram is mocked; real owner-scoped DB, alert engine and outbox are exercised."""
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from urllib.parse import urlsplit, parse_qs
from uuid import uuid4
import json
import pytest
import psycopg
from fastapi.testclient import TestClient
from thesis.db import transaction, one, rows
from thesis.monitoring import telegram as T, telegram_transport as HTTP
from thesis.monitoring.telegram_message import render, visible_units, safe_url
from thesis import service
from thesis.providers import ledger
from test_idea_alerts import setup, provider, newer
from thesis.research import idea_alerts, sentiment
from thesis.monitoring import news_watch
from test_integration import payload, drain
from test_market import commit, news
from test_sentiment import provider as sentiment_provider

KEY = "123456789:" + "x" * 35


class Bot:
    def __init__(self):
        self.calls = []
        self.updates = []
        self.webhook = ""
        self.failure = None
    def __call__(self, key, method, body):
        assert key == KEY
        self.calls.append((method, body))
        if method == "getMe": return dict(is_bot=True, username="ThesisTestBot")
        if method == "getWebhookInfo": return dict(url=self.webhook)
        if method == "getUpdates": return self.updates
        if method == "sendMessage":
            if self.failure: raise self.failure
            return dict(message_id=123, chat=dict(id=body["chat_id"]))
        pytest.fail("Unexpected Telegram method")
    @property
    def sent(self): return [b for method, b in self.calls if method == "sendMessage"]


@pytest.fixture
def bot(monkeypatch):
    mock = Bot()
    monkeypatch.setattr(HTTP, "token", lambda: KEY)
    monkeypatch.setattr(HTTP, "call", mock)
    return mock


def link(owner, bot, **message_patch):
    value = T.connect(owner)
    nonce = parse_qs(urlsplit(value["url"]).query)["start"][0]
    bot.updates = [dict(update_id=8, message={"text": "/start " + nonce, "chat": dict(id=987654, type="private"), "from": dict(id=987654, username="owner", is_bot=False)} | message_patch)]
    return T.check_connection(owner)


def unpace(owner):
    with transaction(owner) as conn:
        conn.execute("UPDATE telegram_settings SET next_send_at=NULL WHERE owner_id=%s", (owner,))


def all_deliveries(owner):
    with transaction(owner) as conn:
        return rows(conn, "SELECT * FROM telegram_deliveries WHERE owner_id=%s ORDER BY created_at", (owner,))


def test_defaults_off_status_read_only_no_network(owner, bot):
    value = T.status(owner)
    assert value["configured"] and not value["linked"] and not value["enabled"]
    assert not T.run_once(owner)
    assert bot.calls == []
    with transaction(owner) as conn:
        assert not one(conn, "SELECT 1 FROM telegram_settings")


def test_private_pairing_one_time_hashed_and_expiring(owner, bot):
    value = T.connect(owner)
    nonce = parse_qs(urlsplit(value["url"]).query)["start"][0]
    assert len(nonce) <= 64
    with transaction(owner) as conn:
        cfg = T.config(conn, owner)
        assert cfg["link_hash"] == T.fingerprint(nonce) and nonce not in str(cfg)
    state = link(owner, bot)
    assert state["linked"] and not state["enabled"] and state["chat_label"] == "@owner"
    with transaction(owner) as conn:
        assert T.config(conn, owner)["link_hash"] is None
    T.disconnect(owner)
    with pytest.raises(ValueError, match="expired"):
        T.check_connection(owner)
    assert not T.status(owner)["linked"]
    T.connect(owner)
    with transaction(owner) as conn:
        conn.execute("UPDATE telegram_settings SET link_expires_at=now()-interval '1 minute'")
    with pytest.raises(ValueError, match="expired"):
        T.check_connection(owner)


@pytest.mark.parametrize("patch", [
    {"chat": dict(id=-123, type="group")},
    {"from": dict(id=222, is_bot=False)},
    {"from": dict(id=987654, is_bot=True)},
    {"forward_origin": dict(type="user")},
    {"via_bot": dict(id=1)},
    {"text": "/start " + "x"*43},
])
def test_pairing_rejects_unintended_targets(owner, bot, patch):
    assert not link(owner, bot, **patch)["linked"]
    assert not bot.sent


def test_dedicated_bot_webhook_never_modified(owner, bot):
    bot.webhook = "https://example.test/kestrel-hook"
    with pytest.raises(ValueError, match="webhook"):
        T.connect(owner)
    assert [method for method, _ in bot.calls] == ["getMe", "getWebhookInfo"]
    assert not T.status(owner)["pending"]


def test_pairing_refresh_invalidates_old_link(owner, bot):
    old = T.connect(owner)
    T.connect(owner)
    nonce = parse_qs(urlsplit(old["url"]).query)["start"][0]
    bot.updates = [dict(update_id=1, message={"text": "/start " + nonce, "chat": dict(id=987654, type="private"), "from": dict(id=987654)})]
    assert not T.check_connection(owner)["linked"]


def test_missing_or_changed_token_prevents_send(owner, bot, monkeypatch):
    link(owner, bot)
    T.configure(owner, True)
    T.test_message(owner)
    monkeypatch.setattr(HTTP, "token", lambda: "other-token")
    assert not T.run_once(owner)
    assert T.status(owner)["token_changed"] and not T.status(owner)["active"]
    assert not bot.sent
    monkeypatch.setattr(HTTP, "token", lambda: "")
    with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN"):
        T.connect(owner)
    T.configure(owner, False)  # Stopping never requires a valid token.
    assert not T.status(owner)["enabled"]


def test_test_message_can_send_while_alerts_off_and_is_paced(owner, bot):
    link(owner, bot)
    T.test_message(owner)
    with pytest.raises(ValueError, match="recently"):
        T.test_message(owner)
    assert T.run_once(owner)
    assert len(bot.sent) == 1
    assert "not a market event" in bot.sent[0]["text"]
    assert bot.sent[0]["protect_content"] and not bot.sent[0]["allow_paid_broadcast"]
    assert all_deliveries(owner)[0]["status"] == "sent"
    assert not T.run_once(owner) and len(bot.sent) == 1
    assert not T.status(owner)["enabled"]


def test_all_three_real_alert_paths_send_once_without_model_or_watch_changes(owner, bot, monkeypatch):
    iid, saved, analysis = setup(owner, True)
    news_watch.configure(owner, iid, True)
    link(owner, bot)
    T.configure(owner, True)
    commit(iid, [news(id=900, url="https://example.test/cost-warning", headline="Microsoft reports a cost warning", summary="Microsoft reports cost pressure, with demand still uncertain.")])
    change = sentiment.generate(iid, transport=sentiment_provider("negative"))
    news_watch.publish(owner, iid, change["id"])
    idea_alerts.generate(owner, iid, change["id"], transport=provider("risk"))
    service.save_idea(owner, payload())
    drain(owner)
    service.advance(owner, 0)
    drain(owner)
    budget = ledger.snapshot()
    monkeypatch.setattr(ledger, "execute", lambda *a, **k: pytest.fail("Telegram called a model"))
    for _ in range(5):
        unpace(owner)
        T.run_once(owner)
    deliveries = all_deliveries(owner)
    assert {d["kind"] for d in deliveries} == {"company", "idea", "condition"}
    assert all(d["status"] == "sent" for d in deliveries)
    assert len(bot.sent) == len(deliveries) == 3
    assert all("Updates →" in m["text"] for m in bot.sent)
    assert any("https://example.test/cost-warning" in m["text"] for m in bot.sent)
    assert any("A saved comparison changed" in m["text"] for m in bot.sent)
    assert any("Fictional demo" in m["text"] for m in bot.sent)
    assert all(visible_units(m["text"]) <= 3800 for m in bot.sent)
    assert ledger.snapshot() == budget
    assert T.status(owner)["watches"] == 1


def test_activation_and_reactivation_do_not_flood_old_updates(owner, bot):
    iid, _, reading = setup(owner)
    idea_alerts.generate(owner, iid, reading["id"], transport=provider("risk"))
    link(owner, bot)
    T.configure(owner, True)
    assert not T.run_once(owner) and not bot.sent
    T.configure(owner, False)
    change = newer(iid)
    idea_alerts.generate(owner, iid, change["id"], transport=provider("risk"))
    T.configure(owner, True)
    assert not T.run_once(owner) and not bot.sent


def test_pause_disconnect_cancel_queued_and_never_enroll_watches(owner, bot):
    link(owner, bot)
    T.configure(owner, True)
    T.test_message(owner)
    T.configure(owner, False)
    assert all_deliveries(owner)[0]["status"] == "cancelled"
    T.disconnect(owner)
    assert not T.status(owner)["linked"]
    assert not T.run_once(owner) and not bot.sent
    assert T.status(owner)["watches"] == 0


@pytest.mark.parametrize("failure,state", [
    (HTTP.TelegramError("uncertain", "Delivery unconfirmed."), "uncertain"),
    (HTTP.TelegramError("rejected", "Token rejected."), "failed"),
    (TimeoutError("private token must not leak"), "uncertain"),
])
def test_send_error_is_not_success_or_automatic_retry(owner, bot, failure, state):
    link(owner, bot)
    T.configure(owner, True)
    T.test_message(owner)
    bot.failure = failure
    assert T.run_once(owner)
    item = all_deliveries(owner)[0]
    assert item["status"] == state and item["message_id"] is None
    assert "private token" not in item["error"]
    unpace(owner)
    assert not T.run_once(owner) and len(bot.sent) == 1


def test_rate_limit_honors_wait_and_has_three_attempt_bound(owner, bot, monkeypatch):
    link(owner, bot)
    T.test_message(owner)
    bot.failure = HTTP.TelegramError("rate_limited", "Please wait.", 60)
    now = datetime.now(timezone.utc)
    for attempt in range(3):
        monkeypatch.setattr(T, "clock", lambda: now)
        assert T.run_once(owner)
        item = all_deliveries(owner)[0]
        assert item["attempts"] == attempt+1
        assert not T.run_once(owner)
        now += timedelta(seconds=61)
    assert item["status"] == "failed"
    assert len(bot.sent) == 3
    with transaction(owner) as conn:
        assert T.config(conn, owner)["next_send_at"] >= now-timedelta(seconds=1)


def test_crash_after_intent_is_uncertain_and_never_resent(owner, bot):
    link(owner, bot)
    T.test_message(owner)
    with transaction(owner) as conn:
        conn.execute("UPDATE telegram_deliveries SET status='sending',attempts=1")
    assert not T.run_once(owner)
    assert all_deliveries(owner)[0]["status"] == "uncertain"
    assert not bot.sent


def test_concurrent_workers_send_once_and_pause_waits_for_dispatch(owner, bot, monkeypatch):
    link(owner, bot)
    T.configure(owner, True)
    T.test_message(owner)
    entered, release = Event(), Event()
    def slow(key, method, body):
        if method == "sendMessage":
            entered.set()
            assert release.wait(10)
        return bot(key, method, body)
    monkeypatch.setattr(HTTP, "call", slow)
    with ThreadPoolExecutor(max_workers=3) as pool:
        first = pool.submit(T.run_once, owner)
        assert entered.wait(10)
        assert not pool.submit(T.run_once, owner).result(timeout=3)
        pause = pool.submit(T.configure, owner, False)
        assert not pause.done()
        release.set()
        assert first.result(timeout=10)
        assert not pause.result(timeout=10)["enabled"]
    assert len(bot.sent) == 1 and all_deliveries(owner)[0]["status"] == "sent"


def test_private_rls_and_membership(owner, bot):
    link(owner, bot)
    T.test_message(owner)
    other = str(uuid4())
    with transaction(admin=True) as conn:
        conn.execute("INSERT INTO accounts VALUES(%s,'Other')", (other,))
    assert not T.status(other)["linked"] and not T.status(other)["deliveries"]
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with transaction(other) as conn:
            conn.execute("INSERT INTO telegram_settings(owner_id) VALUES(%s)", (owner,))
    with pytest.raises(psycopg.errors.RaiseException):
        with transaction(other) as conn:
            conn.execute("INSERT INTO telegram_deliveries(id,owner_id,kind,event_id,event_at) VALUES(%s,%s,'company',%s,now())", (uuid4(), other, uuid4()))
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with transaction(source=True) as conn:
            conn.execute("SELECT chat_id FROM telegram_settings")


def test_withdrawal_rechecked_at_dispatch(owner, bot):
    iid, _, reading = setup(owner)
    link(owner, bot)
    T.configure(owner, True)
    idea_alerts.generate(owner, iid, reading["id"], transport=provider("risk"))
    with transaction(admin=True) as conn:
        conn.execute("UPDATE sources SET entitlement='local-stockanalysis-targets' WHERE id='finnhub-news'")
    assert T.run_once(owner)
    assert all_deliveries(owner)[0]["status"] == "skipped" and not bot.sent


def test_unrenderable_alert_does_not_block_following_delivery(owner, bot, monkeypatch):
    iid, _, reading = setup(owner)
    link(owner, bot)
    T.configure(owner, True)
    idea_alerts.generate(owner, iid, reading["id"], transport=provider("risk"))
    def bad(*args): raise KeyError("malformed field with private source body")
    monkeypatch.setattr(T, "render", bad)
    assert T.run_once(owner)
    assert all_deliveries(owner)[0]["status"] == "skipped"
    assert "private source body" not in all_deliveries(owner)[0]["error"]
    T.test_message(owner)
    assert T.run_once(owner) and len(bot.sent) == 1


def test_stale_pending_message_is_not_sent_after_long_downtime(owner, bot, monkeypatch):
    link(owner, bot)
    T.test_message(owner)
    future = datetime.now(timezone.utc)+timedelta(hours=25)
    monkeypatch.setattr(T, "clock", lambda: future)
    assert T.run_once(owner)
    assert all_deliveries(owner)[0]["status"] == "skipped" and not bot.sent


def test_condition_message_keeps_figures_and_unknown_separate():
    msg=render(dict(kind="condition",title="Figure changed",created_at="2026-10-05T00:00:00Z",detail=dict(symbol="DEMO",question="Margin?",details=dict(affected_conditions=[dict(metric="operating_margin",before="18.4",after=None)]))))
    assert "Operating margin: 18.4% → Unknown" in msg
    assert "0%" not in msg


def test_new_idea_revision_suppresses_old_pending_private_alert(owner, bot):
    iid, saved, reading = setup(owner)
    link(owner, bot)
    T.configure(owner, True)
    idea_alerts.generate(owner, iid, reading["id"], transport=provider("risk"))
    from thesis.models import SaveIdea
    service.save_idea(owner, SaveIdea(instrument_id=iid, expected_revision=1, question="A different question", reasoning="Other reasoning", status="draft", conditions=[]))
    assert T.run_once(owner)
    assert all_deliveries(owner)[0]["status"] == "skipped" and not bot.sent


def test_http_endpoints_require_local_session_and_strict_opt_in(owner, bot):
    from thesis.app import app
    client = TestClient(app)
    assert client.get("/api/v1/telegram").status_code == 401
    client.get("/api/v1/session")
    assert client.post("/api/v1/telegram/connect").status_code == 403
    assert client.get("/api/v1/telegram").status_code == 200
    assert client.post("/api/v1/telegram/delivery", headers={"x-thesis-request": "local-ui"}, json={"enabled":"true"}).status_code == 422
    assert not bot.calls


def test_formatter_is_bounded_escaped_and_preserves_uncertainty():
    detail = dict(symbol="<&>😀", payload=dict(reason="😀"*1000, cutoff="2026-10-05T00:00:00Z", shifts=[dict(title="😀"*200,before=dict(tone="negative leaning"),after=dict(tone="positive leaning"))]*3, items=[dict(source_id="1", reporting_basis=dict(kind="unconfirmed_event", citations=[dict(quote="<&>😀"*1000)]))]*2), sources=[dict(id="1",url="https://example.com/evidence?a=1&b=2",source="<bad>")])
    message = render(dict(kind="company", title="<script>alert(1)</script>",created_at="2026-10-05T00:00:00Z",detail=detail))
    assert visible_units(message) <= 3800
    assert "<script>" not in message and "&lt;script&gt;" in message
    assert "Unconfirmed report" in message
    assert "Updates →" in message


@pytest.mark.parametrize("url", ["javascript:alert(1)","https://user:secret@example.com/x","https://127.0.0.1/x","https://localhost/x","https://[::1]/","https://example.com:8080/x"])
def test_invalid_links_not_forwarded(url):
    assert safe_url(url) is None


class Response:
    def __init__(self, data): self.data = json.dumps(data).encode()
    def read(self, limit): return self.data[:limit]
    def __enter__(self): return self
    def __exit__(self, *args): pass


@pytest.mark.parametrize("data,code", [
    ({"ok":False,"error_code":403,"description":"SECRET"},"rejected"),
    ({"ok":False,"error_code":429,"parameters":{"retry_after":40}},"rate_limited"),
    ({"ok":False,"error_code":502},"uncertain"),
    ({"ok":True,"result":{}},"uncertain"),
    ({"ok":True,"result":{"message_id":1,"chat":{"id":888}}},"uncertain"),
])
def test_transport_validates_ack_and_sanitizes_errors(monkeypatch, data, code):
    class Opener:
        def open(self, request, timeout): return Response(data)
    monkeypatch.setattr(HTTP, "build_opener", lambda *args: Opener())
    with pytest.raises(HTTP.TelegramError) as exc:
        HTTP.call(KEY,"sendMessage",dict(chat_id=999,text="test"))
    assert exc.value.code == code and KEY not in str(exc.value) and "SECRET" not in str(exc.value)
