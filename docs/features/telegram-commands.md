# Telegram commands

Added 31 October 2026 (plan: [draggable widgets and Telegram commands](../development/draggable-widgets-and-telegram-commands-plan.md), Feature B). **Off by default**: `THESIS_TELEGRAM_COMMANDS=true` in `.env` turns it on. The setting is read on each poll, so once this version is running it applies without a restart. Back up `.env` first.

## Commands

| Command | Answer | Reads / writes | Cost |
| --- | --- | --- | --- |
| `/today` (`/portfolio`) | Each company's saved move and news tone, the world line, any saved explanation headline | `portfolio.build` | none |
| `/why NVDA` | Saved price move, news tone, newest saved headlines with links, latest saved filing; says these don't prove a cause | `portfolio.quote_for/news_for`, `disclosure_current` | none (no new AI) |
| `/world` | Recent world headlines, with the account's saved check of which could help/hurt which company | `world_news.view` | none |
| `/explain` | The app's "Explain my list": cited headline, drivers, groups, takeaway | `portfolio.explain` → `portfolio_reads` | one AI request via the ledger; reused free when list and material are unchanged |
| `/watch NVDA` | Turns on the company's news watch (existing interval, else every four hours) | `news_watch.configure` | each later watch check uses the AI budget, as in the app |
| `/help` (`/start`) | The list above | — | none |

Every reply is plain text (no markup), ends with "Facts and saved evidence only. Fledge never recommends buying or selling." and uses Singapore 24-hour timestamps. Long replies are split under Telegram's 4,096-character limit.

## Safety

- **One cursor.** Commands come from `telegram_updates.receive()`, the same `getUpdates` consumer used for linking and rating taps. The quick poll loop runs when ratings **or** commands are on, and the linking check goes through `receive()` in either case, so the offset has a single owner.
- **Guard.** Only private chats where the sender is the chat, not a bot, not forwarded and not sent via a bot (`private_sender`), and only the `chat_id` linked to an account with the current bot fingerprint. Other private chats get one "connect this chat first" reply and nothing is stored. Messages older than 10 minutes, for example sent while the Mac slept or commands were off, are ignored.
- **Durable intent.** Each command is written to `telegram_commands` (migration 075, owner-approved 31 October) in `receive()`'s transaction, keyed by bot update, before the cursor advances. Replies are sent only after commit, marked `sending` first, and never repeated: an unconfirmed send ends as `uncertain`. A replayed update is ignored. Only the command name and a validated ticker are stored, never the message text.
- **Rate limit.** Six commands per account per minute. The seventh gets one notice and later ones get nothing, though they are still recorded as `limited`.
- **/explain.** The bot sends "Working on it…" with the cost (an upper bound from `ledger.estimate`, or "no cost" when the ledger already has the answer), then a worker claims the queued row once. `portfolio.explain(on_saved=…)` saves the result and marks the command `done` in **one transaction**. The bot then edits its note into the result. A failed request is recorded (`failed`, ledger keeps the unresolved charge) and **never retried**. `sweep()` marks a run left `running` for 15 minutes, or a note queued more than 10 minutes, as `interrupted` and tells the chat. A queued note the worker never started (the app stopped right after sending it) is started once it is 30 seconds old.

## Both surfaces

`/explain` writes the same `portfolio_reads` row the app's button writes, so "Your list today" shows the identical explanation. The open app polls `GET /api/v1/telegram/commands/latest` every 20 s while visible, and stops for the visit if commands are off. When a newer `/explain` or `/watch` finishes, it fires the existing `fledge:home-changed` event. The home page and "Your list today" re-read saved data, and the company page's own 30-second refresh shows a new watch. It does not trigger "Update data", which would fetch from suppliers.

## Files

`thesis/monitoring/telegram_commands.py` (parse, intake, respond, handlers, explain worker, sweep, latest) · hooks in `telegram_updates.py` and `telegram.check_connection` · `editMessageText` added to `telegram_transport` · `portfolio.prepare` / `explain(on_saved=)` · `frontend/src/lib/telegramCommandSync.js` (+ test), `useTelegramCommandSync.js`.

## Verification

`tests/test_telegram_commands.py` (offline, mocked Telegram, fake model) covers parsing, chunking, `/today` text and replay, guard rejections (other sender, group, forwarded, via bot, bot sender, old), unlinked chats, the off switch, the rate limit, `/why`, `/world`, `/watch`, the `/explain` intent → worker → atomic publish → edit, failure without retry, no spend without a list, sweep, and the `latest` endpoint.
