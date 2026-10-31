"""Read and explain commands from the linked Telegram chat.

Off unless THESIS_TELEGRAM_COMMANDS is on (owner choice, 31 October 2026).
Updates arrive through the one bot cursor in telegram_updates.receive(); this
module only parses, records and answers them. Only the chat linked to an account
with the current bot may command, under the same private-sender guard as
linking; any other chat gets one "link first" reply and nothing is kept.

Each command is recorded (telegram_commands, one row per bot update) before any
reply, so a crash never repeats a reply or a paid explanation. Replies are
facts, saved evidence and uncertainty, never a recommendation. Fast commands
read saved data as the linked account; /watch turns on the same news watch as
the app; /explain is the app's "Explain my list" request, queued and finished
by a worker that saves the result and the command's state in one transaction.
The paid request goes through the spending ledger and is never retried
automatically. Only the command name and a validated ticker are stored.
"""
from datetime import datetime, timedelta, timezone
import logging
import re
import threading
from uuid import uuid4
from thesis.db import transaction, one, rows
from thesis.display_time import stamp
from . import telegram_transport as transport

COMMANDS = ("help", "today", "why", "world", "explain", "watch")
ALIASES = {"portfolio": "today", "start": "help"}
NEEDS_SYMBOL = {"why", "watch"}
SYMBOL = re.compile(r"[A-Z][A-Z0-9.\-]{0,11}")
COMMAND = re.compile(r"/([A-Za-z]{1,20})(?:@[A-Za-z0-9_]{5,32})?(?:\s+(.*))?", re.S)
LINK = re.compile(r"/start(?:@[A-Za-z0-9_]+)? ([A-Za-z0-9_-]{43})")
# Telegram keeps updates for a day; a command sent while the app was asleep or
# commands were off is not answered hours later.
MAX_AGE = timedelta(minutes=10)
RATE_LIMIT = 6
RATE_WINDOW = timedelta(minutes=1)
# A paid explanation left 'running' this long was cut off (app stopped).
STALE_RUN = timedelta(minutes=15)
# A queued explanation the worker never started is run only if still recent.
QUEUE_GRACE = timedelta(seconds=30)
QUEUE_EXPIRY = timedelta(minutes=10)
MESSAGE_LIMIT = 4000  # Telegram allows 4096 characters.

DISCLAIMER = "Facts and saved evidence only. Fledge never recommends buying or selling."
LINK_FIRST = ("This chat isn't connected to a Fledge account. In Fledge, open Account → Telegram "
              "and connect this chat first.")
TOO_MANY = "That's a lot of commands at once. Wait a minute, then try again."
HELP = "\n".join([
    "Fledge commands",
    "/today – how your list moved, from saved prices and news",
    "/why NVDA – the saved news, tone and filing next to one company's move",
    "/world – world headlines that might matter for your list",
    "/explain – a written explanation of your list (one AI request)",
    "/watch NVDA – turn on Fledge's news watch for a company",
    "/help – this list",
    "",
    "Results also appear in the app. " + DISCLAIMER,
])
TONE_WORDS = {"positive": "good", "negative": "bad", "mixed": "mixed", "neutral": "neutral"}
TONE_SHAPE = {"positive": "▲", "negative": "▼", "mixed": "◆", "neutral": "●"}
log = logging.getLogger("thesis.telegram")


def enabled():
    from .move_watch import option
    return str(option("THESIS_TELEGRAM_COMMANDS") or "false").lower() in {"true", "1", "on"}


def clock():
    return datetime.now(timezone.utc)


def parse(text):
    """'/why nvda' → {command: 'why', argument: 'NVDA', problem: None}.

    None for a message that is not a command (or is the link /start). Unknown
    commands become help with a short note; a bad ticker keeps the command
    with a problem to explain, and no argument is stored."""
    if not isinstance(text, str) or not text.startswith("/") or LINK.fullmatch(text):
        return None
    match = COMMAND.fullmatch(text.strip())
    name = ALIASES.get(match[1].lower(), match[1].lower()) if match else None
    if name not in COMMANDS:
        return dict(command="help", argument=None, problem="I don't know that command.")
    words = (match[2] or "").split()
    if name not in NEEDS_SYMBOL:
        return dict(command=name, argument=None, problem=None)
    symbol = words[0].upper().lstrip("$") if len(words) == 1 else ""
    if not SYMBOL.fullmatch(symbol):
        return dict(command=name, argument=None,
                    problem=f"Add a ticker, for example /{name} NVDA.")
    return dict(command=name, argument=symbol, problem=None)


def intake(conn, update, fingerprint, now):
    """Record one command inside receive()'s transaction; return what to answer.

    Runs as the bot's admin connection, before the cursor advances. Answering
    happens after commit (respond), never inside this transaction."""
    from .telegram_updates import private_sender
    message = update.get("message")
    if not isinstance(message, dict):
        return None
    parsed = parse(message.get("text"))
    sender = message.get("from") or {}
    if not parsed or not private_sender(message, sender):
        return None
    sent = message.get("date")
    if type(sent) is not int or abs(now - datetime.fromtimestamp(sent, timezone.utc)) > MAX_AGE:
        return None
    chat = sender["id"]
    cfg = one(conn, "SELECT owner_id FROM telegram_settings WHERE bot_fingerprint=%s AND chat_id=%s",
              (fingerprint, chat))
    if not cfg:
        return dict(chat=chat, text=LINK_FIRST)
    owner = str(cfg["owner_id"])
    recent = one(conn, "SELECT count(*) n FROM telegram_commands WHERE owner_id=%s AND received_at>%s",
                 (owner, now - RATE_WINDOW))["n"]
    status = "limited" if recent >= RATE_LIMIT else "received"
    row = one(conn, """INSERT INTO telegram_commands(id,owner_id,update_key,command,argument,status,received_at)
        VALUES(%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(update_key) DO NOTHING RETURNING id""",
              (uuid4(), owner, f"{fingerprint[:16]}:{update['update_id']}", parsed["command"],
               parsed["argument"], status, now))
    if not row:
        return None  # This update was already handled.
    if status == "limited":
        # One notice per flood; later commands in the window get no reply.
        return dict(chat=chat, text=TOO_MANY) if recent == RATE_LIMIT else None
    return dict(parsed, chat=chat, id=str(row["id"]), owner=owner)


def chunks(text):
    """Split at line breaks into messages Telegram accepts."""
    parts, current = [], ""
    for line in text.split("\n"):
        while len(line) > MESSAGE_LIMIT:
            if current:
                parts.append(current)
                current = ""
            parts.append(line[:MESSAGE_LIMIT])
            line = line[MESSAGE_LIMIT:]
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) > MESSAGE_LIMIT:
            parts.append(current)
            current = line
        else:
            current = candidate
    if current or not parts:
        parts.append(current)
    return parts


def send(key, chat, text):
    """Plain-text messages (no markup to escape); returns their message ids."""
    return [transport.call(key, "sendMessage", dict(chat_id=chat, text=part,
                                                    link_preview_options=dict(is_disabled=True)))["message_id"]
            for part in chunks(text)]


def _finish(owner, command_id, **fields):
    columns = ",".join(f"{name}=%s" for name in fields)
    with transaction(owner) as conn:
        conn.execute(f"UPDATE telegram_commands SET {columns} WHERE id=%s", (*fields.values(), command_id))


def reply(key, intent, text, *, status="answered"):
    """Send once: mark 'sending' first, so an unconfirmed send is never repeated."""
    owner, command_id = intent["owner"], intent["id"]
    with transaction(owner) as conn:
        claimed = one(conn, "UPDATE telegram_commands SET status='sending' WHERE id=%s AND status='received' "
                      "RETURNING id", (command_id,))
    if not claimed:
        return None
    try:
        ids = send(key, intent["chat"], text)
    except transport.TelegramError as failure:
        _finish(owner, command_id, status="uncertain" if failure.code == "uncertain" else "failed",
                error=str(failure)[:300], finished_at=clock())
        return None
    now = clock()
    _finish(owner, command_id, status=status, message_id=ids[0], delivered_at=now,
            finished_at=None if status == "queued" else now)
    return ids[0]


def respond(key, intent):
    """Answer one recorded intent after receive() committed. Never raises."""
    try:
        if "id" not in intent:
            send(key, intent["chat"], intent["text"])
            return
        if intent["problem"]:
            reply(key, intent, f"{intent['problem']}\n\n{HELP}")
            return
        if intent["command"] == "explain":
            start_explain(key, intent)
            return
        try:
            text = HANDLERS[intent["command"]](intent["owner"], intent["argument"], clock())
        except ValueError as failure:
            text = str(failure)
        except Exception:
            log.exception("Telegram command failed")
            text = "That didn't work this time. Try again in a moment."
        reply(key, intent, text)
    except Exception:
        # A failed reply keeps its recorded state; it is not sent again.
        log.exception("Telegram command reply failed")


# Handlers: each reads as the linked account and returns plain text.

def pct(value):
    return f"{value:+.1f}%".replace("-", "−")


def tone_counts(news):
    counts = news.get("counts") or {}
    if not counts:
        return "news not rated yet" if news.get("rated") is False else "no rated news"
    return " · ".join(f"{counts[t]} {TONE_WORDS[t]}" for t in ("positive", "negative", "mixed", "neutral")
                      if counts.get(t))


def company_for(conn, symbol):
    company = one(conn, "SELECT id,symbol,name FROM instruments WHERE upper(symbol)=%s ORDER BY symbol LIMIT 1",
                  (symbol,))
    if not company:
        raise ValueError(f"Fledge has no company saved as {symbol}. Add it in the app first.")
    return company


def today(owner, _argument, now):
    from thesis import portfolio
    page = portfolio.build(owner, now=now)
    listed = page["companies"]
    if not listed:
        return "Your list is empty. Add companies in Fledge to follow them here.\n\n" + DISCLAIMER
    lines = ["Your list today"]
    if page["prices_from"]:
        lines.append(f"Prices from {stamp(page['prices_from'])}"
                     + (" · these are a few days old" if page["prices_stale"] else ""))
    else:
        lines.append("No share prices saved yet.")
    lines += [page["move"]["text"], ""]
    moves = lambda c: (c["quote"] or {}).get("change_percent")
    for c in sorted(listed, key=lambda c: (moves(c) is None, moves(c) or 0)):
        move = pct(moves(c)) if moves(c) is not None else "no price saved"
        lines.append(f"• {c['symbol']}  {move}  ({tone_counts(c['news'])})")
    lines += ["", f"World: {page['world']['text']}"]
    if page["explanation"] and page["explanation"].get("headline"):
        lines.append(f"Saved explanation: {page['explanation']['headline']}")
    lines += ["", "Send /why SYMBOL for the evidence next to one company's move.", DISCLAIMER]
    return "\n".join(lines)


def why(owner, symbol, now):
    from thesis import portfolio
    with transaction(owner, consistent=True) as conn:
        company = company_for(conn, symbol)
        iid = str(company["id"])
        quote = portfolio.quote_for(conn, iid)
        news = portfolio.news_for(conn, iid)
        filing = one(conn, """SELECT d.form,d.published_at FROM disclosure_current c
            JOIN disclosure_documents d ON d.id=c.document_id AND d.instrument_id=c.instrument_id
            WHERE c.instrument_id=%s ORDER BY d.published_at DESC LIMIT 1""", (iid,))
    lines = [f"{company['symbol']} · {company['name']}"]
    if quote and quote.get("change_percent") is not None:
        lines.append(f"Price {quote['price']:.2f}, {pct(quote['change_percent'])} since the last close "
                     f"(saved {stamp(quote.get('quoted_at'))})")
    else:
        lines.append("No share price saved yet.")
    lines.append(f"News tone in the saved reading: {tone_counts(news)}")
    if news.get("items"):
        lines.append("Recent saved headlines:")
        for item in news["items"]:
            lines.append(f"{TONE_SHAPE.get(item['tone'], '●')} {item['title']} "
                         f"({item.get('publisher') or 'source'}, {stamp(item.get('published_at'))})")
            if item.get("url"):
                lines.append(f"  {item['url']}")
    if filing:
        lines.append(f"Latest saved filing: {filing['form']}, published {stamp(filing['published_at'])}")
    lines += ["", "These saved readings sit next to the move; they don't prove what caused it.", DISCLAIMER]
    return "\n".join(lines)


EFFECTS = {"could_help": "could help", "could_hurt": "could hurt", "mixed_or_unclear": "unclear effect on"}


def world(owner, _argument, now):
    from thesis.research import world_news
    page = world_news.view(owner, now=now)
    articles = page["articles"]
    if not articles:
        return "No recent world headlines are saved. Open World in Fledge to check.\n\n" + DISCLAIMER
    symbols = {c["id"]: c["symbol"] for c in page["companies"]}
    linked = [a for a in articles if any(l.get("company_id") in symbols for l in a["links"])]
    lines = ["World headlines and your list", f"Headlines checked {stamp(page['checked_at'])}"]
    if not page["check"]:
        lines.append("Not checked against your list yet; open World in Fledge to run that check.")
    elif not linked:
        lines.append("The last check found no headline with a clear link to your companies.")
    lines.append("")
    for a in (linked or articles)[:6]:
        lines.append(f"• {a['headline']} ({a['publisher']}, {stamp(a['published_at'])})")
        for l in a["links"][:4]:
            if l.get("company_id") in symbols:
                lines.append(f"  {EFFECTS.get(l['effect'], 'unclear effect on')} {symbols[l['company_id']]}: "
                             f"{l['reason']}")
        if a.get("url"):
            lines.append(f"  {a['url']}")
    lines += ["", "Possible channels of effect, not predictions.", DISCLAIMER]
    return "\n".join(lines)


def watch(owner, symbol, now):
    from thesis.monitoring import news_watch
    with transaction(owner, consistent=True) as conn:
        company = company_for(conn, symbol)
        old = one(conn, "SELECT enabled,interval_minutes FROM news_watches WHERE owner_id=%s AND instrument_id=%s",
                  (owner, company["id"]))
    every = lambda minutes: "hour" if minutes == 60 else "four hours"
    if old and old["enabled"]:
        return (f"{company['symbol']} is already watched every {every(old['interval_minutes'])}. "
                "Change or stop it on the company's News tab in Fledge.")
    interval = old["interval_minutes"] if old else 240
    news_watch.configure(owner, str(company["id"]), True, interval, now=now)
    return "\n".join([
        f"Watching {company['symbol']} · {company['name']} for news every {every(interval)} while Fledge is running.",
        "Each check uses the AI budget, the same as turning the watch on in the app.",
        "Stop it on the company's News tab in Fledge.",
    ])


def help_text(_owner, _argument, _now):
    return HELP


HANDLERS = dict(help=help_text, today=today, why=why, world=world, watch=watch)


# /explain: durable intent, worker, atomic publish, then the bot edits its note.

def start_explain(key, intent):
    from thesis import portfolio
    from thesis.providers import ledger
    owner = intent["owner"]
    try:
        _listed, _sources, body, request_key = portfolio.prepare(owner, clock())
        with transaction(owner, consistent=True) as conn:
            reused = ledger.find(conn, request_key)
        cost = ledger.estimate(body) / ledger.NANO
    except ValueError as failure:
        reply(key, intent, f"{failure}\n\n{DISCLAIMER}")
        return
    note = ("The same list and saved news were explained before, so this reuses that answer at no cost."
            if reused else
            f"This uses one AI request, at most about US${cost:.2f}, recorded in Fledge's AI spending.")
    message = reply(key, intent, f"Working on it: explaining your list from saved prices and news.\n{note}",
                    status="queued")
    if message is None:
        return  # Nobody would see the result in Telegram; nothing is spent.
    threading.Thread(target=run_explain, args=(owner, intent["id"]), daemon=True,
                     name="telegram-explain").start()


def explanation_text(page):
    e = page.get("explanation")
    if not e:
        return ("The explanation was saved, but prices moved since. Open Fledge to see it next to "
                "the prices it was written from.\n\n" + DISCLAIMER)
    symbols = {c["id"]: c["symbol"] for c in page["companies"]}
    lines = ["Your list, explained", e.get("headline") or ""]
    for d in e.get("drivers", []):
        cited = ", ".join(s.get("publisher") or s.get("title") or "source" for s in d["sources"])
        lines.append(f"• {d['text']} [{cited}]")
    for g in e.get("groups", []):
        members = ", ".join(symbols.get(i, "?") for i in g["company_ids"])
        lines.append(f"{g['label']} ({members}): {g['note']}")
    if e.get("takeaway"):
        lines += ["", e["takeaway"]]
    if e.get("dropped"):
        lines.append(f"{e['dropped']} uncited or advice-like part(s) were left out.")
    lines += ["", f"Saved in Fledge {stamp(e.get('created_at'))}; the app shows the same explanation.",
              DISCLAIMER]
    return "\n".join(line for line in lines if line is not None)


def run_explain(owner, command_id, *, model=None):
    """Claim a queued explanation once, run it, then deliver. Returns whether it ran."""
    from thesis import portfolio
    now = clock()
    with transaction(owner) as conn:
        row = one(conn, "UPDATE telegram_commands SET status='running',started_at=%s WHERE id=%s AND "
                  "status='queued' RETURNING *", (now, command_id))
    if not row:
        return False

    def saved(conn, read_id):
        conn.execute("UPDATE telegram_commands SET status='done',result_id=%s,finished_at=%s "
                     "WHERE id=%s AND status='running'", (read_id, clock(), command_id))

    try:
        text = explanation_text(portfolio.explain(owner, transport=model, now=now, on_saved=saved))
    except ValueError as failure:
        _finish(owner, command_id, status="failed", error=str(failure)[:300], finished_at=clock())
        text = f"Couldn't explain your list: {failure}\n\n{DISCLAIMER}"
    except Exception:
        log.exception("Telegram explanation failed")
        _finish(owner, command_id, status="failed", error="Unexpected failure.", finished_at=clock())
        text = ("Couldn't explain your list this time. Nothing is retried automatically; "
                "send /explain again later.\n\n" + DISCLAIMER)
    deliver(owner, command_id, row["message_id"], text)
    return True


def deliver(owner, command_id, message_id, text):
    """Replace the 'Working on it' note with the result (edits are safe to repeat)."""
    from . import telegram as T
    key = transport.token()
    if not key:
        return
    with transaction(owner) as conn:
        cfg = one(conn, "SELECT chat_id,bot_fingerprint FROM telegram_settings WHERE owner_id=%s", (owner,))
    if not cfg or not cfg["chat_id"] or cfg["bot_fingerprint"] != T.fingerprint(key):
        return
    first, *rest = chunks(text)
    try:
        try:
            transport.call(key, "editMessageText", dict(chat_id=cfg["chat_id"], message_id=message_id, text=first,
                                                         link_preview_options=dict(is_disabled=True)))
        except transport.TelegramError as failure:
            if failure.code != "rejected":
                raise
            # The note can no longer be edited (deleted or too old): send it new.
            send(key, cfg["chat_id"], first)
        for part in rest:
            send(key, cfg["chat_id"], part)
    except transport.TelegramError:
        return  # The result stays saved in the app; Telegram is not retried.
    _finish(owner, command_id, delivered_at=clock())


def sweep(*, now=None):
    """Tidy explanations a stopped app left behind. Never re-runs a started one."""
    now = now or clock()
    with transaction(admin=True) as conn:
        stuck = rows(conn, """UPDATE telegram_commands SET status='interrupted',finished_at=%s,
            error='Stopped before finishing; not retried automatically.'
            WHERE (status='running' AND started_at<%s) OR (status='queued' AND received_at<%s)
            RETURNING id,owner_id,message_id""", (now, now - STALE_RUN, now - QUEUE_EXPIRY))
        waiting = rows(conn, "SELECT id,owner_id FROM telegram_commands WHERE status='queued' AND received_at<%s "
                       "ORDER BY received_at LIMIT 3", (now - QUEUE_GRACE,))
    for row in stuck:
        try:
            deliver(str(row["owner_id"]), row["id"], row["message_id"],
                    "This explanation stopped before finishing (Fledge was closed or asleep). "
                    "Nothing is retried automatically; send /explain again.")
        except Exception:
            log.exception("Telegram interrupted notice failed")
    # Queued but never started (the app stopped right after the note was sent).
    for row in waiting:
        threading.Thread(target=run_explain, args=(str(row["owner_id"]), row["id"]), daemon=True,
                         name="telegram-explain").start()
    return len(stuck), len(waiting)


def latest(owner):
    """For the open app: the newest finished command that changed saved data."""
    if not enabled():
        return dict(enabled=False, latest=None)
    with transaction(owner, consistent=True) as conn:
        row = one(conn, """SELECT id,command,finished_at FROM telegram_commands WHERE owner_id=%s
            AND ((command='explain' AND status='done') OR (command='watch' AND status='answered'))
            ORDER BY finished_at DESC NULLS LAST LIMIT 1""", (owner,))
    return dict(enabled=True, latest=dict(id=str(row["id"]), command=row["command"],
                                          finished_at=row["finished_at"].isoformat()) if row else None)
