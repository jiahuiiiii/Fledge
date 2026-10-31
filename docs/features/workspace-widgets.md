# Arrangeable overview and home

Added 31 October 2026 (plan: [draggable widgets and Telegram commands](../development/draggable-widgets-and-telegram-commands-plan.md), Feature A).

## What it does

The company summary (Beginner summary; also the Pro Business tab) and the home page are boards of widgets. Reading mode looks like the plain page and never moves anything. **Arrange** (top right of the board) turns on:

- dragging a widget by its top bar, and dragging its right edge to change width;
- per-widget keyboard buttons: move earlier/later (reading order), narrower/wider, hide;
- a list of hidden widgets to add back, and **Reset to default**.

Heights follow content, so evidence is never cut off; only width is chosen by hand. Boards narrower than 600 px, and windows under 768 px, show one stacked column (order from the `sm` layout; arrows and hide still work). Widget content is inert while arranging so a drag never opens a link.

## Where things are

| Piece | File |
| --- | --- |
| Registry (ids, titles, min width, default positions per `lg`/`md`/`sm`) — single source of defaults | `frontend/src/components/workspace/widgets.js` |
| Widgets read data and actions from context, not props | `workspace/WorkspaceContext.jsx`, `SummaryWidgets.jsx`, `HomeWidgets.jsx` |
| Board: edit mode, stack vs grid, debounced save, reset, keyboard | `workspace/WidgetBoard.jsx` |
| Grid (react-grid-layout 1.5.2, lazy chunk) | `workspace/WidgetGrid.jsx` |
| Pure merge/move/resize helpers + node tests | `frontend/src/lib/workspaceLayout.js` |
| Server allow-list, validation, reconcile | `thesis/workspace_layouts.py` |
| Table | `migrations/074_workspace_layouts.sql` (owner-approved 31 October) |

Breakpoints are on the board's width: `lg` ≥ 1100 px (12 columns), `md` ≥ 860 px (10), `sm` (6).

## API

`GET /api/v1/layouts/{page}` → `{lg, md, sm, hidden, saved}`; a width never arranged is `null` and the browser uses the registry default. `PUT` with `{lg?, md?, sm?, hidden}` saves only the widths the user arranged (one PUT 500 ms after a change settles). `DELETE` resets. `page` is `overview` or `home`; every `i` must be a known widget id; positions must fit the column count; `h` ≤ 400 rows.

Reconcile on read is mandatory: the server drops unknown ids and broken items; the browser adds widgets missing from a save at their default width below everything else. Adding a widget means adding it to **both** the registry and `WIDGETS` in `thesis/workspace_layouts.py`.

## Verification

- `node --test frontend/src/lib/workspaceLayout.test.js` — merge, fit, move, resize, save body.
- `tests/test_workspace_layouts.py` — validation, reconcile, round trip, account privacy, API.
- `tests/run_browser.py --workspace-widgets` — arrange, keyboard move with focus kept, drag, resize, hide/add, reload persistence, reset, 320 px stack.

## Not in this cut

Cross-page dashboards, shared layouts, new widget data. The Pro full-details blocks (chart, business summary, latest activity) are not widgets yet.
