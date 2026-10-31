"""Telegram commands: Telegram is mocked; real DB, cursor, guards and ledger path."""
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit, parse_qs
from uuid import uuid4
import json
import pytest
from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb
from thesis import portfolio, watchlist
from thesis.app import app
from thesis.db import transaction, one, rows
from thesis.monitoring import telegram as T, telegram_transport as HTTP
from thesis.monitoring import telegram_commands as C, telegram_updates as U
from thesis.providers.settings import MODEL

KEY = "123456789:" + "y" * 35
CHAT = 987654
NOW = datetime.now(timezone.utc).replace(microsecond=0)


class Bot:
    def __init__(self):
        self.calls, self.updates, self.next_id = [], [], 500
    def __call__(self, key, method, body):
        assert key == KEY
        self.calls.append((method, body))
        if method == "getMe": return dict(is_bot=True, username="FledgeTestBot")
        if method == "getWebhookInfo": return dict(url="")
        if method == "getUpdates": return [u for u in self.updates if u["update_id"] >= body["offset"]]
        if method == "sendMessage":
            self.next_id += 1
            return dict(message_id=self.next_id, chat=dict(id=body["chat_id"]))
        if method in {"editMessageText", "answerCallbackQuery", "setMyCommands", "deleteMyCommands"}: return True
        pytest.fail(f"Unexpected Telegram method {method}")
    def texts(self, method="sendMessage"):
        return [b["text"] for m, b in self.calls if m == method]


class NoThread:
    started = []
    def __init__(self, target, args, **kwargs):
        self.target, self.args = target, args
    def start(self):
        NoThread.started.append(self.args)


@pytest.fixture
def bot(monkeypatch):
    mock = Bot()
    monkeypatch.setattr(HTTP, "token", lambda: KEY)
    monkeypatch.setattr(HTTP, "call", mock)
    monkeypatch.setattr(C, "enabled", lambda: True)
    monkeypatch.setattr(C.threading, "Thread", NoThread)
    monkeypatch.setattr(C, "_menus", {})
    monkeypatch.setattr(C, "_strangers", {})
    NoThread.started = []
    # The cursor is keyed by bot, not account, so it outlives each test's accounts.
    with transaction(admin=True) as conn:
        conn.execute("TRUNCATE telegram_poll_state")
    return mock


@pytest.fixture
def linked(owner, bot):
    nonce = parse_qs(urlsplit(T.connect(owner)["url"]).query)["start"][0]
    bot.updates = [update(1, "/start " + nonce)]
    assert T.check_connection(owner)["linked"]
    bot.calls.clear()
    return owner


def update(uid, text, *, chat=CHAT, sender=None, age=timedelta(0), **patch):
    message = {"text": text, "date": int((datetime.now(timezone.utc) - age).timestamp()),
               "chat": dict(id=chat, type="private"),
               "from": dict(id=chat if sender is None else sender, is_bot=False, username="owner")} | patch
    return dict(update_id=uid, message=message)


def send(bot, *updates):
    bot.updates += list(updates)
    U.receive(force=True)


def commands(owner):
    with transaction(owner) as conn:
        return rows(conn, "SELECT * FROM telegram_commands WHERE owner_id=%s ORDER BY received_at,update_key", (owner,))


def company(symbol, name, change):
    iid = str(uuid4())
    with transaction(admin=True) as conn:
        conn.execute("INSERT INTO instruments VALUES(%s,%s,%s)", (iid, symbol, name))
        conn.execute("""INSERT INTO instrument_state(instrument_id,cutoff,period,label,sector)
                        VALUES(%s,'2025-07-24T12:00:00Z','2025-Q2','Q2 baseline','Semiconductors')""", (iid,))
        conn.execute("INSERT INTO market_quotes VALUES(%s,%s,%s,%s)",
                     (uuid4(), iid, Jsonb(dict(price=100.0, change_percent=change, quoted_at=NOW.isoformat())), NOW))
    return iid


@pytest.fixture
def listed(linked, monkeypatch):
    with transaction(admin=True) as conn:
        conn.execute("TRUNCATE world_news_articles, world_news_checks, portfolio_reads")
    ids = dict(NVDA=company("NVDA", "NVIDIA Corp", -3.16), AVGO=company("AVGO", "Broadcom Inc.", 1.2))
    for iid in ids.values():
        watchlist.add(linked, iid)
    news = {ids["NVDA"]: dict(counts={"negative": 1, "positive": 2}, items=[
        dict(title="Nvidia slips with AI peers", url="https://example.com/nvda1", publisher="Reuters",
             published_at=NOW.isoformat(), tone="negative")])}
    monkeypatch.setattr(portfolio, "news_for", lambda conn, iid: news.get(iid, dict(counts={}, items=[], rated=False)))
    return ids


def test_parse_commands_aliases_and_tickers():
    assert C.parse("/why nvda") == dict(command="why", argument="NVDA", problem=None)
    assert C.parse("/WHY@FledgeTestBot $brk.b") == dict(command="why", argument="BRK.B", problem=None)
    assert C.parse("/portfolio")["command"] == "today"
    assert C.parse("/start")["command"] == "help"
    assert C.parse("/start " + "a" * 43) is None  # chat linking, handled elsewhere
    assert C.parse("hello") is None and C.parse(None) is None
    assert C.parse("/buy NVDA") == dict(command="help", argument=None, problem="I don't know that command.")
    assert C.parse("/why")["problem"] == "Add a ticker, for example /why NVDA."
    assert C.parse("/watch ; drop table")["argument"] is None
    assert C.parse("/why NVDA please") == dict(command="why", argument=None,
                                               problem="Add a ticker, for example /why NVDA.")
    assert C.parse("/today please")["command"] == "today"


def test_long_replies_are_split_for_telegram():
    text = "\n".join(["x" * 900] * 10)
    parts = C.chunks(text)
    assert len(parts) == 3 and all(len(p) <= C.MESSAGE_LIMIT for p in parts)
    assert "\n".join(parts) == text
    assert C.chunks("y" * 9000) == ["y" * 4000, "y" * 4000, "y" * 1000]


def test_today_answers_the_linked_chat_and_records_the_command(linked, listed, bot):
    send(bot, update(10, "/today"))
    text, = bot.texts()
    assert text.startswith("Your list today")
    assert "• NVDA  −3.2%  (2 good · 1 bad)" in text and "• AVGO  +1.2%  (news not rated yet)" in text
    assert C.DISCLAIMER in text
    sent = [b for m, b in bot.calls if m == "sendMessage"][0]
    assert sent["chat_id"] == CHAT and "parse_mode" not in sent
    row, = commands(linked)
    assert (row["command"], row["status"], row["message_id"]) == ("today", "answered", 501)
    # Replaying the same update (a cursor reset) never answers twice.
    with transaction(admin=True) as conn:
        conn.execute("UPDATE telegram_poll_state SET update_offset=0")
    U.receive(force=True)
    assert len(bot.texts()) == 1 and len(commands(linked)) == 1


@pytest.mark.parametrize("patch", [
    dict(sender=111),                                    # someone else in the chat
    dict(chat=-100123),                                  # a group
    dict(forward_origin=dict(type="user")),              # forwarded from elsewhere
    dict(via_bot=dict(id=5, is_bot=True)),               # sent through an inline bot
    dict(age=timedelta(hours=2)),                        # sent while the app was off
])
def test_guard_ignores_spoofed_forwarded_and_old_messages(linked, bot, patch):
    message = update(20, "/today", **{k: v for k, v in patch.items() if k in ("sender", "chat", "age")},
                     **{k: v for k, v in patch.items() if k not in ("sender", "chat", "age")})
    if "chat" in patch:
        message["message"]["chat"]["type"] = "supergroup"
        message["message"]["from"]["id"] = CHAT
    send(bot, message)
    assert bot.texts() == [] and commands(linked) == []


def test_bot_senders_are_ignored(linked, bot):
    message = update(21, "/today")
    message["message"]["from"]["is_bot"] = True
    send(bot, message)
    assert bot.texts() == [] and commands(linked) == []


def test_unlinked_chat_is_told_to_link_and_nothing_is_kept(linked, bot):
    send(bot, update(30, "/today", chat=555))
    assert bot.texts() == [C.LINK_FIRST]
    assert [b["chat_id"] for m, b in bot.calls if m == "sendMessage"] == [555]
    with transaction(admin=True) as conn:
        assert one(conn, "SELECT count(*) n FROM telegram_commands")["n"] == 0


def test_commands_off_reads_nothing_new(linked, bot, monkeypatch):
    monkeypatch.setattr(C, "enabled", lambda: False)
    monkeypatch.setattr(U.alert_feedback, "enabled", lambda: False)
    assert U.poll_feedback() is False
    bot.updates.append(update(40, "/today"))
    U.receive(force=True)  # e.g. a linking check: the cursor moves, commands stay unanswered
    assert bot.texts() == [] and commands(linked) == []


def test_rate_limit_answers_one_notice_then_stays_quiet(linked, listed, bot):
    send(bot, *[update(50 + i, "/help") for i in range(8)])
    texts = bot.texts()
    assert texts.count(C.HELP) == 6 and texts.count(C.TOO_MANY) == 1 and len(texts) == 7
    assert [r["status"] for r in commands(linked)].count("limited") == 2


def test_why_shows_saved_evidence_without_claiming_a_cause(linked, listed, bot):
    send(bot, update(60, "/why nvda"), update(61, "/why ZZZZ"), update(62, "/why"))
    why, missing, empty = bot.texts()
    assert why.startswith("NVDA · NVIDIA Corp\nPrice 100.00, −3.2% since the last close (saved ")
    assert "▼ Nvidia slips with AI peers (Reuters, " in why and "https://example.com/nvda1" in why
    assert "don't prove what caused it" in why and C.DISCLAIMER in why
    assert missing == "Fledge has no company saved as ZZZZ. Add it in the app first."
    assert empty.startswith("Add a ticker, for example /why NVDA.")
    assert [r["argument"] for r in commands(linked)] == ["NVDA", "ZZZZ", None]


def test_world_lists_linked_headlines_as_possible_channels(linked, listed, bot, monkeypatch):
    from thesis.research import world_news
    article = dict(id="a1", headline="New export rules for advanced chips", publisher="Reuters",
                   url="https://example.com/chips", published_at=(NOW - timedelta(hours=1)).isoformat(),
                   links=[dict(article_id="a1", company_id=listed["NVDA"], effect="could_hurt",
                               reason="Export limits can cut overseas chip sales.")])
    quiet = dict(article, id="a2", headline="Central bank holds rates", links=[])
    page = dict(checked_at=NOW.isoformat(), check=dict(checked_at=NOW.isoformat()), articles=[article, quiet],
                companies=[dict(id=listed["NVDA"], symbol="NVDA"), dict(id=listed["AVGO"], symbol="AVGO")])
    monkeypatch.setattr(world_news, "view", lambda owner, now=None: page)
    send(bot, update(70, "/world"))
    text, = bot.texts()
    assert "• New export rules for advanced chips (Reuters, " in text
    assert "could hurt NVDA: Export limits can cut overseas chip sales." in text
    assert "Central bank holds rates" not in text and "not predictions" in text


def test_watch_turns_on_the_apps_news_watch(linked, listed, bot, monkeypatch):
    from thesis.monitoring import news_watch
    calls = []
    monkeypatch.setattr(news_watch, "configure", lambda owner, iid, on, interval, now=None: calls.append(
        (owner, iid, on, interval)))
    send(bot, update(80, "/watch NVDA"))
    assert calls == [(linked, listed["NVDA"], True, 240)]
    assert bot.texts()[0].startswith("Watching NVDA · NVIDIA Corp for news every four hours")
    with transaction(admin=True) as conn:
        conn.execute("INSERT INTO news_watches(owner_id,instrument_id,enabled,interval_minutes) VALUES(%s,%s,true,60)",
                     (linked, listed["AVGO"]))
    send(bot, update(81, "/watch avgo"))
    assert len(calls) == 1 and bot.texts()[1].startswith("AVGO is already watched every hour.")
    latest = C.latest(linked)["latest"]
    assert latest["command"] == "watch"


def fake_model(result):
    def transport(body):
        return dict(id="resp_1", model=MODEL, status="completed", service_tier="default",
                    usage=dict(input_tokens=1500, output_tokens=300),
                    output=[dict(type="message", content=[dict(type="output_text", text=json.dumps(result))])])
    return transport


EXPLAINED = dict(
    headline="Chipmakers split: Nvidia fell while Broadcom rose.",
    drivers=[dict(text="Nvidia slipped with other AI stocks.", source_ids=["n1_1"]),
             dict(text="Buy the dip now.", source_ids=["n1_1"])],
    groups=[dict(label="AI chips", company_ids=["c1"], note="Moved with AI peers.")],
    takeaway="Both are chipmakers, so they share one industry's risks.",
)


def test_explain_queues_then_publishes_the_same_saved_result_as_the_app(linked, listed, bot):
    send(bot, update(90, "/explain"))
    note, = bot.texts()
    assert note.startswith("Working on it") and "at most about US$" in note
    row, = commands(linked)
    assert row["status"] == "queued" and row["message_id"] == 501
    assert NoThread.started == [(linked, str(row["id"]))]
    # The worker: one ledger call, result and command state saved together.
    assert C.run_explain(linked, row["id"], model=fake_model(EXPLAINED)) is True
    assert C.run_explain(linked, row["id"], model=fake_model(EXPLAINED)) is False  # claimed once
    done, = commands(linked)
    with transaction(linked) as conn:
        saved = one(conn, "SELECT * FROM portfolio_reads WHERE owner_id=%s", (linked,))
    assert done["status"] == "done" and done["result_id"] == saved["id"] and done["delivered_at"]
    page = portfolio.build(linked)
    assert page["explanation"]["headline"] == EXPLAINED["headline"]
    edit, = [b for m, b in bot.calls if m == "editMessageText"]
    assert edit["message_id"] == 501 and edit["chat_id"] == CHAT
    assert EXPLAINED["headline"] in edit["text"] and "[Reuters]" in edit["text"]
    assert "Buy the dip" not in edit["text"] and "1 uncited or advice-like part(s) were left out." in edit["text"]
    assert C.latest(linked)["latest"]["id"] == str(done["id"])
    # Asking again with the same list and news reuses the saved answer for free.
    send(bot, update(91, "/explain"))
    assert "reuses that answer at no cost" in bot.texts()[-1]


def test_explain_failures_are_recorded_and_never_retried(linked, listed, bot):
    send(bot, update(100, "/explain"))
    row, = commands(linked)

    def broken(body):
        raise RuntimeError("connection reset")
    assert C.run_explain(linked, row["id"], model=broken)
    failed, = commands(linked)
    assert failed["status"] == "failed" and "failed before a result was saved" in failed["error"]
    edit, = [b for m, b in bot.calls if m == "editMessageText"]
    assert edit["text"].startswith("Couldn't explain your list:")
    with transaction(admin=True) as conn:
        assert one(conn, "SELECT count(*) n FROM portfolio_reads")["n"] == 0
        assert one(conn, "SELECT status FROM model_calls ORDER BY created_at DESC LIMIT 1")["status"] != "settled"


def test_explain_needs_a_list_and_spends_nothing_otherwise(linked, bot, monkeypatch):
    from thesis.providers import ledger
    monkeypatch.setattr(ledger, "execute", lambda *a, **k: pytest.fail("no AI call"))
    send(bot, update(110, "/explain"))
    assert bot.texts()[0].startswith("Add at least two companies to your list first.")
    row, = commands(linked)
    assert row["status"] == "answered" and NoThread.started == []


def test_sweep_marks_stopped_explanations_and_tells_the_chat(linked, listed, bot):
    send(bot, update(120, "/explain"))
    row, = commands(linked)
    with transaction(admin=True) as conn:
        conn.execute("UPDATE telegram_commands SET status='running',started_at=%s WHERE id=%s",
                     (NOW - timedelta(minutes=20), row["id"]))
    assert C.sweep() == (1, 0)
    stopped, = commands(linked)
    assert stopped["status"] == "interrupted"
    assert [b["text"] for m, b in bot.calls if m == "editMessageText"][0].startswith("This explanation stopped")
    # A queued one the worker never started is run once it is 30 seconds old.
    send(bot, update(121, "/explain"))
    queued = commands(linked)[-1]
    NoThread.started = []
    with transaction(admin=True) as conn:
        conn.execute("UPDATE telegram_commands SET received_at=%s WHERE id=%s",
                     (datetime.now(timezone.utc) - timedelta(minutes=1), queued["id"]))
    assert C.sweep() == (0, 1) and NoThread.started == [(linked, queued["id"])]


def test_latest_endpoint_reports_off(owner, monkeypatch):
    monkeypatch.setattr(C, "enabled", lambda: False)
    client = TestClient(app)
    client.get("/api/v1/session")
    assert client.get("/api/v1/telegram/commands/latest").json()["result"] == dict(enabled=False, latest=None)


def menu_calls(bot):
    return [(m, b) for m, b in bot.calls if m in ("setMyCommands", "deleteMyCommands")]


def test_command_menu_follows_the_switch_for_linked_chats_only(linked, bot, monkeypatch):
    U.poll_feedback()
    (method, body), = menu_calls(bot)
    assert method == "setMyCommands" and body["scope"] == dict(type="chat", chat_id=CHAT)
    assert [c["command"] for c in body["commands"]] == ["today", "why", "world", "explain", "watch", "help"]
    assert all(3 <= len(c["description"]) <= 256 for c in body["commands"])
    U.poll_feedback()
    assert len(menu_calls(bot)) == 1  # once per change, not every poll
    # Commands off while rating buttons still poll: the menu is removed once.
    monkeypatch.setattr(C, "enabled", lambda: False)
    monkeypatch.setattr(U.alert_feedback, "enabled", lambda: True)
    U.poll_feedback()
    U.poll_feedback()
    assert [m for m, _ in menu_calls(bot)] == ["setMyCommands", "deleteMyCommands"]


def test_a_failed_menu_update_waits_before_trying_again(linked, bot, monkeypatch):
    calls = []

    def refuse(key, method, body):
        calls.append(method)
        raise HTTP.TelegramError("unavailable", "Telegram could not be reached.")
    monkeypatch.setattr(HTTP, "call", refuse)
    now = datetime.now(timezone.utc)
    assert C.sync_menu(now=now) == 0 and calls == ["setMyCommands"]
    assert C.sync_menu(now=now + timedelta(minutes=5)) == 0 and len(calls) == 1
    monkeypatch.setattr(HTTP, "call", bot)
    assert C.sync_menu(now=now + timedelta(minutes=11)) == 1
    assert [m for m, _ in menu_calls(bot)] == ["setMyCommands"]



def second_account(bot, uid):
    other = str(uuid4())
    with transaction(admin=True) as conn:
        conn.execute("INSERT INTO accounts VALUES(%s,%s)", (other, "Second test account"))
    nonce = parse_qs(urlsplit(T.connect(other)["url"]).query)["start"][0]
    bot.updates.append(update(uid, "/start " + nonce))
    assert T.check_connection(other)["linked"]
    return other


def signed_in(account, username, at):
    with transaction(admin=True) as conn:
        conn.execute("INSERT INTO password_credentials(account_id,username,password_hash) VALUES(%s,%s,'x')",
                     (account, username))
        conn.execute("INSERT INTO password_sessions(token_hash,account_id,created_at,expires_at) VALUES(%s,%s,%s,%s)",
                     (uuid4().hex, account, at, at + timedelta(days=30)))


def test_a_chat_linked_to_several_accounts_answers_for_the_right_one(linked, bot):
    other = second_account(bot, 2)
    now = datetime.now(timezone.utc)
    signed_in(linked, "first.account", now - timedelta(days=2))
    signed_in(other, "second.account", now - timedelta(hours=1))
    bot.calls.clear()
    # No alerts on anywhere: the account signed into last answers, and says so.
    send(bot, update(3, "/help"))
    assert commands(other)[0]["command"] == "help" and commands(linked) == []
    assert bot.texts()[-1].endswith("connected to more than one account; it uses the one with "
                                    "Telegram alerts on that you signed into last.")
    assert "“second.account”" in bot.texts()[-1]
    # An account with Telegram alerts on wins over a later sign-in.
    with transaction(admin=True) as conn:
        conn.execute("UPDATE telegram_settings SET enabled=true,enabled_at=now() WHERE owner_id=%s", (linked,))
    send(bot, update(4, "/help"))
    assert len(commands(linked)) == 1 and "“first.account”" in bot.texts()[-1]


def test_an_unlinked_chat_is_told_once_not_every_message(linked, bot):
    send(bot, update(500, "/today", chat=555), update(501, "/help", chat=555), update(502, "/world", chat=556))
    assert bot.texts() == [C.LINK_FIRST, C.LINK_FIRST]
    assert [b["chat_id"] for m, b in bot.calls if m == "sendMessage"] == [555, 556]


def test_a_saved_explanation_is_never_reported_as_failed(linked, listed, bot, monkeypatch):
    send(bot, update(510, "/explain"))
    row, = commands(linked)

    def broken(page):
        raise RuntimeError("formatting failed after the save")
    monkeypatch.setattr(C, "explanation_text", broken)
    assert C.run_explain(linked, row["id"], model=fake_model(EXPLAINED))
    done, = commands(linked)
    assert done["status"] == "done" and done["result_id"] and done["error"] is None
    edit, = [b for m, b in bot.calls if m == "editMessageText"]
    assert edit["text"].startswith("Your list was explained and saved.")


def test_menu_comes_down_even_when_nothing_else_polls(linked, bot, monkeypatch):
    U.poll_feedback()
    monkeypatch.setattr(C, "enabled", lambda: False)
    monkeypatch.setattr(U.alert_feedback, "enabled", lambda: False)
    assert U.poll_feedback() is False
    assert [m for m, _ in menu_calls(bot)] == ["setMyCommands", "deleteMyCommands"]
    U.poll_feedback()
    assert len(menu_calls(bot)) == 2

