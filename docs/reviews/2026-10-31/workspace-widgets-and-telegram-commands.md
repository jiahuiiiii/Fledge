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
| `tests/test_workspace_layouts.py`, `tests/test_telegram_commands.py` | **not run**: the agent sandbox blocks PostgreSQL shared memory, so the disposable test cluster cannot start |
| `tests/run_browser.py --workspace-widgets` | **not run**, for the same reason |
| Live browser check (drag → reload persists) | **owner to verify** after restart |

Run in the owner's Terminal:

```bash
LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8 .venv/bin/python -m pytest -q tests/test_workspace_layouts.py tests/test_profiles_watchlists.py
LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8 .venv/bin/python -m pytest -q tests/test_telegram_commands.py tests/test_telegram.py tests/test_portfolio.py
```

No live app or database was started, stopped or restarted, and no paid call was made.
