# Workspace widgets and Telegram commands: implementation, 31 October 2026

Plan: [draggable widgets and Telegram commands](../../development/draggable-widgets-and-telegram-commands-plan.md).

## Owner decisions (31 October)

- Commit the earlier uncommitted work first (`afa3e6c` on `feat/idea-reasoning-confirm`, not pushed), then one branch per feature cut from it.
- Migrations **074** (`workspace_layouts`) and **075** (`telegram_commands`) approved. Both are additive and apply at the next deliberate restart.
- Telegram commands sit behind a new flag, `THESIS_TELEGRAM_COMMANDS`, which is off by default. `.env` was not changed.
- `react-grid-layout@1.5.2` was installed by the owner, because the agent sandbox cannot reach npm.

## Branches (local, not pushed)

| Feature | Branch | Contract |
| --- | --- | --- |
| A: arrangeable overview and home | `feat/workspace-widgets` | [workspace-widgets.md](../../features/workspace-widgets.md) |
| B: Telegram commands | `feat/telegram-commands` | [telegram-commands.md](../../features/telegram-commands.md) |

## Deviations from the plan

- **Heights follow content.** Widget heights are measured, not fixed grid rows, so evidence is never clipped, and the only resize handle is the width handle. Saved `h` is informational.
- **Arrange control location.** The Arrange control is in the board's own toolbar, not in `WorkspaceHeader`, so each arrangeable page owns its control.
- **Reconcile is split.** The server drops unknown ids and broken items. The browser adds missing widgets at registry defaults, because the registry, which is the single source of defaults, lives in the frontend. The id allow-list is duplicated in `thesis/workspace_layouts.py`.
- **`/why` makes no new AI call.** It reads saved price, news tone, headlines and filing.
- **App refresh uses `fledge:home-changed`, not `requestUpdate`.** `requestUpdate` would fetch from suppliers.
- **No daily spending cap.** The ledger has none, by the owner's decision of 13 October. `/explain` discloses its upper-bound cost and is never retried automatically.

## Verification

| Check | Result |
| --- | --- |
| `node --test` (frontend lib, incl. `workspaceLayout.test.js`, `telegramCommandSync.test.js`) | 251 pass on A; 247 pass on B |
| `vite build` to a scratch dir | passes on both branches; the grid is a separate lazy chunk (75 kB, 21 kB gzipped) |
| `workspace_layouts.validate/reconcile`, `telegram_commands.parse/chunks/explanation_text`, run directly | behave as specified |
| `tests/test_workspace_layouts.py`, `tests/test_telegram_commands.py` | First owner run failed on two test-file bugs (account id vs company-id dict; bot cursor shared between tests). After the fix: **39 passed** (owner Terminal, 31 October) |
| Related suites: `test_telegram`, `test_portfolio`, `test_profiles_watchlists`, `test_daily_telegram`, `test_move_telegram`, `test_telegram_stories` | **143 passed** (owner Terminal, 31 October) |
| Full offline suite (`pytest tests`) | **3,027 passed, 93 skipped** (owner Terminal, 31 October, before the review fixes below) |
| After review fixes: commands, layouts, alert feedback, Telegram, portfolio | **135 passed**; frontend `node --test` 255 passed; build passes |
| `tests/run_browser.py --workspace-widgets` | **not run** |
| Live browser check (drag → reload persists) | **owner to verify** after restart |

Run in the owner's Terminal:

```bash
LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8 .venv/bin/python -m pytest -q tests/test_workspace_layouts.py tests/test_profiles_watchlists.py
LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8 .venv/bin/python -m pytest -q tests/test_telegram_commands.py tests/test_telegram.py tests/test_portfolio.py
```

No live app or database was started, stopped or restarted, and no paid call was made.

## Independent review and fixes (31 October)

A separate reviewer read the diff without running anything. Fixed:

- **Account switch:** saved layouts were cached for the whole page, so a second account signing in on the same tab could see, and then save over, the first account's arrangement. The cache is now cleared per account.
- **`/explain` after a save:** it could be marked failed even though the result had already been saved. A saved explanation now stays `done`, and the chat is told it was saved.
- **Unlinked chats:** they get the "connect first" reply at most once per 10 minutes, so strangers can't keep the poll loop busy.
- **Command menu:** removed when commands are off even if alert ratings are off too.
- **Height and position limits:** raised to 2,000 rows (about 36,000 px) and row 20,000, so long widgets aren't cut short and long pages aren't refused. The browser and server limits match.
- **Breakpoints:** the board now picks its layout at exactly 860 or 1,100 px the same way react-grid-layout does.
- **Save order:** saves and resets go out one after another, and the first read never overwrites a newer change.
- **Stuck replies:** a reply that hits an unexpected error is closed as `uncertain` and never resent.

Still open: upgrade `react-grid-layout` 1.5.2 → **1.5.4**. Versions 1.5.0–1.5.3 shipped a stray `ip_fetcher` binary and its source, which look up the public IP address. Nothing runs it, and 1.5.4 is identical apart from removing those files. The owner runs the upgrade, because the sandbox cannot reach npm.

