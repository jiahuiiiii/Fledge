# Implementation plan — draggable/resizable workspace & Telegram commands

Drafted 31 October 2026. **Self-contained**: written so an engineer or agent with no
prior context can execute it. Read §0–§2 before touching code. Two independent features
(§3, §4); ship them separately, each on its own branch.

---

## 0. How to use this document

1. Read §1 (orientation) and §2 (hard rules) fully — they stop you breaking a live system.
2. Pick one feature (§3 or §4). Do its phases in order; each phase has an **acceptance
   check** you must pass before the next.
3. Use §5 (patterns) for copy-able endpoint/fetch/migration/verify snippets.
4. Confirm facts against the real files before relying on them — this repo changes.

---

## 1. Orientation — what Fledge is and where things are

Fledge is a research workspace for investigating companies (news, sentiment, filings,
alerts). It does **not** trade or give advice. Stack:

- **Frontend**: React 18 + Vite, in `frontend/`. Entry `frontend/src/App.jsx`. API client
  `frontend/src/api/client.js`. Components in `frontend/src/components/`, shared primitives
  in `frontend/src/components/ui/` (barrel `ui/index.js`). Deliberately lean deps
  (react, react-dom, react-toastify) — justify any new one.
- **Backend**: FastAPI in `thesis/`. HTTP routes in `thesis/app.py`. Business logic in
  `thesis/service.py` and `thesis/research/*`, monitoring/alerts in `thesis/monitoring/*`.
  DB helpers in `thesis/db.py`. Config in `thesis/config.py`.
- **Database**: PostgreSQL. Migrations in `migrations/NNN_name.sql`, applied in order.
  **Latest is `073`**; a new migration is `074+`. The app **auto-applies pending
  migrations on startup**.
- **How it runs** (the owner does this, not you — see §2): `.venv/bin/python run.py
  --port 8841` from the repo root. It serves the API and the built frontend from
  `frontend/dist`. DB listens on a unix socket `./.local/socket` port `55439`, db `thesis`.
- **Read first**: `AGENTS.md` (operating rules — authoritative), `README.md`, and the
  feature contracts in `docs/features/` relevant to what you touch (e.g.
  `docs/features/telegram-alerts.md`).

Key existing pieces these features build on (verify before use):
- **UI primitives**: `frontend/src/components/ui/` — `Button`, `Select`, `Card`,
  `Modal`, `Field`, `Toggle`, etc. Reuse these; don't reinvent chrome.
- **Summary/overview is already componentised**: `BeginnerSummary.jsx`,
  `CompanyOverview.jsx` (lazy-loaded in App.jsx), `OverviewSections.jsx`,
  `OverviewReadCard.jsx`, `OverviewShared.jsx`, `FinancialOverview.jsx`, `PriceChart.jsx`,
  `SentimentPanel.jsx`; home is `PersonalHome.jsx`. These are the blocks Feature A turns
  into widgets.
- **Telegram inbound already exists**: `thesis/monitoring/telegram.py` links a chat and
  polls `getUpdates` (tracks `update_offset`); `thesis/monitoring/telegram_updates.py`
  has `receive()` (line ~94) which polls `getUpdates` with
  `allowed_updates=['message','callback_query']`, `connect_message()` (chat linking),
  `rating_callback()` (feedback buttons), and `private_sender()` (sender guards). Chat↔
  account mapping lives in the `telegram_settings` table (`owner_id`, `chat_id`,
  `update_offset`, `enabled`, bot fingerprint). Outbound uses `sendMessage` /
  `telegram_deliveries`. Feature B extends `receive()`.

---

## 2. Hard rules (from AGENTS.md — do not violate)

- **Never start, stop, or restart the real app or database yourself.** A past sandbox
  restart broke outbound HTTPS for ~8 hours. You edit code; the **owner** restarts the
  app to load backend changes. Frontend static changes take effect on page reload (no
  restart), once deployed to `frontend/dist` (see §5).
- **Tests are offline, no network.** Run: `LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
  .venv/bin/python -m pytest -q tests/<file>.py`. The suite (`tests/conftest.py`) spins up
  its **own disposable PostgreSQL** in a temp dir — never the live DB. Add tests for every
  behaviour change.
- **Migrations**: never edit an applied migration; add a new numbered file (`074+`).
  **Any new schema change needs explicit owner approval** before it's added. Startup
  applies it automatically; approval and activation are separate.
- **Do not commit, push, merge, or open a PR without the owner's explicit request.** Work
  on a feature branch; preserve unrelated uncommitted work.
- **Secrets**: the Telegram bot token and others live in `.env`. Back up `.env` before
  changing it. Never print secrets or put personal data in docs/commits.
- **Frontend build**: the live app serves `frontend/dist`. **Never run plain
  `npm run build` into it** (it wipes hashed assets other open tabs still use). Build to a
  scratch dir and copy (see §5.5).
- **Product rules**: no buy/sell actions or advice — explain/evidence only. Validate
  account context server-side (RLS applies as the acting owner). Money uses Decimal.
  Display timestamps in Singapore time, 24-hour; reporting dates stay source dates.
  External side effects use durable intent and never run inside a retryable transaction.
  Missing data is "unknown", never 0/neutral.

### How to verify without restarting the live app
- **Backend logic** → offline pytest (disposable DB), above.
- **Backend performance / behaviour on real data** → a **read-only** script that imports
  `thesis.service` / `thesis.db` and calls functions against the live DB. Safe only for
  read-only paths (e.g. functions that open `transaction(owner, consistent=True)` =
  `REPEATABLE READ READ ONLY`). Do **not** set `THESIS_DATA_DIR` (that points at the test
  cluster). See §5.4.
- **Frontend** → `npx vite build --outDir <scratch>` to confirm it compiles; deploy with
  the safe copy (§5.5); reload the page. You cannot log into the in-app browser preview as
  the user, so hand final UI verification to the owner.

---

## 3. Feature A — draggable, resizable workspace & home

Let a user rearrange/resize the blocks on the **overview/summary** and **home** pages,
per breakpoint, persisted per account. Foundation for "every block is a widget."

### Goals / non-goals
- In: drag + resize existing blocks; save per account per breakpoint; explicit edit mode;
  reset-to-default; add/remove widgets; works at 320 px (stacks), keyboard-operable.
- Out (first cut): no cross-page dashboards, no sharing layouts, no new widget data.

### Library
- `react-grid-layout` pinned to an exact version (e.g. `react-grid-layout@1.5.2`), with its
  two stylesheets. **Lazy-load** it (`React.lazy` + `Suspense`) only on pages that use it,
  so other pages and first paint don't pay the bundle cost.
- **< 768 px**: do not render the grid — render the same widgets in a fixed single-column
  stack. Decide from the breakpoint.

### Widget registry (do this first)
Create `frontend/src/components/workspace/widgets.js`: a registry mapping widget id →
`{ component, title, minW, minH, default: { lg:{x,y,w,h}, md:{...}, sm:{...} } }`. Seed it
with the blocks listed in §1. The default layout is derived from this registry — it is the
single source of truth.

Make each block **self-contained**: it must take its data and raise its actions through
React context (add a `WorkspaceContext` providing the workspace `data` and the action
callbacks App.jsx currently passes as props), not via App.jsx prop-drilling, so the grid
can place it anywhere. This is a pure refactor — the app must look identical after it.

### Persistence
- Migration `074_workspace_layouts.sql` (**get owner approval first**):
  ```sql
  CREATE TABLE workspace_layouts(
    owner_id uuid NOT NULL REFERENCES accounts,
    page text NOT NULL,          -- 'overview' | 'home'
    breakpoint text NOT NULL,    -- 'lg' | 'md' | 'sm'
    layout jsonb NOT NULL,       -- [{i,x,y,w,h}, ...]
    hidden jsonb NOT NULL DEFAULT '[]',
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY(owner_id, page, breakpoint));
  ```
- Endpoints in `thesis/app.py` (pattern in §5.1): `GET /api/v1/layouts/{page}` →
  `{lg, md, sm, hidden}`; `PUT /api/v1/layouts/{page}` with the same body. **Validate
  server-side**: `page`/`breakpoint` from an allow-list, every `i` a known widget id,
  numeric bounds sane.
- **Reconcile on read** (mandatory): merge the saved layout with the current registry —
  unknown ids dropped, new widgets added at their registry default. This is what keeps a
  saved layout from breaking when widgets are added/renamed later.
- Client: add `api.layout(page)` / `api.saveLayout(page, body)` in `client.js` (pattern
  §5.2). Save **debounced ~500 ms on drag/resize _stop_**, one PUT per settle.

### UI
- Edit-mode toggle in `WorkspaceControls.jsx` / `WorkspaceHeader.jsx`. Drag/resize handles
  and the add/remove catalog appear only in edit mode; otherwise the grid is static
  (`isDraggable`/`isResizable` false).
- Reset-to-default (DELETE the row or PUT the registry default). Add/remove widgets via a
  small catalog; removing appends the id to `hidden`.

### Accessibility
- RGL drag is pointer-only — add a per-widget keyboard control in edit mode (move up/down,
  grow/shrink) that mutates the same layout state. Honour `prefers-reduced-motion`. Keep
  focus on the moved widget. Each widget needs loading/empty/error states.

### Phases & acceptance checks
1. **Registry + self-contained blocks** (no grid). *Accept*: overview & home render
   identically to before at lg/md/sm; no prop-drilling warnings; `vite build` passes.
2. **Static RGL from registry defaults** (drag disabled). *Accept*: visual parity at each
   breakpoint; < 768 px shows the stack.
3. **Persistence** (migration + endpoints + debounced save + reconcile). *Accept*: offline
   API tests pass (validation, reconcile add/remove, round-trip); drag → reload → layout
   persists (owner verifies in browser).
4. **Edit mode** (handles, reset, add/remove, keyboard). *Accept*: reading mode never
   moves widgets; reset restores defaults; keyboard reorder works.

### Tests
- Offline (`tests/test_workspace_layouts.py`): reject bad page/widget id; reconcile logic;
  save/read round-trip. Use the `owner` fixture pattern from existing tests.
- Browser journey via `tests/run_browser.py` conventions: edit → drag → reload → assert;
  resize; reset; 320 px stack.

### Risks
RGL bundle weight (lazy-load, measure before/after) · touch devices (stack, don't grid) ·
layout drift (reconcile is mandatory) · accidental moves (edit-mode gate).

---

## 4. Feature B — control the app from Telegram

A linked Telegram chat runs **read/explain** commands; results go to Telegram **and** the
open app. Never buy/sell, never advice.

### Reuse, don't rebuild
Inbound polling, chat linking, the `chat_id`↔owner mapping (`telegram_settings`), and
outbound `sendMessage` already exist (§1). Commands are a **router + handlers** added to
`thesis/monitoring/telegram_updates.py`'s `receive()`.

### Architecture
- **Intake**: in `receive()`, add a branch for text messages beginning with `/`. Accept
  **only** from `telegram_settings.chat_id` for that owner, reusing the existing guards
  (`private_sender()`: private chat, sender == chat, not a bot, not forwarded/via_bot).
  Unknown/unlinked chats → a short "link your account first", nothing else. Keep
  **long-polling** `getUpdates` (the app runs locally; no public webhook). One consumer
  advances `update_offset`, or updates are lost.
- **Router**: `thesis/monitoring/telegram_commands.py` — parse `/cmd args` → dispatch
  table; unknown → help text.
- **Handlers reuse existing service code** (server-side account context / RLS as the
  mapped owner; no duplicated logic):

  | Command | Does | Reuse |
  |---|---|---|
  | `/today` (`/portfolio`) | today's watchlist moves & status | portfolio read / home summary |
  | `/why SYMBOL` | news + sentiment + filing evidence behind a move | `thesis/research/sentiment.py`, market brief |
  | `/world` | world events that could affect holdings | WorldNews source |
  | `/explain` | plain-English read of the whole list | the "explain my list" job |
  | `/watch SYMBOL` | set up a watch | watch-lanes service |

- **Explain-only guardrail**: every reply is facts/evidence/uncertainty, never a
  recommendation. Put a shared disclaimer in the formatter.

### Sync vs async — and "both surfaces update"
- Fast reads (`/today`, `/why`, `/world`) answer inline.
- Slow (`/explain`): **durable intent** — write the intent, reply "Working on it…", a
  worker runs the job, then **publish the result and its events atomically**; the bot edits
  its message and the **open app refreshes via the existing update mechanism** (frontend
  `UPDATE_EVENT` / `requestUpdate` in `frontend/src/lib/updateRequest.js` and App.jsx).
  Same action the UI button triggers → one saved result → both surfaces show it. The
  Telegram send is an external side effect: durable intent, never inside a retryable
  transaction.

### Cost & safety
- `/explain`, `/why` may trigger **paid** model calls → go through the existing spending
  ledger, respect the daily cap, **no automatic paid retries**, retain failures/charges,
  disclose cost on expensive ones.
- Per-chat rate limit; command allow-list; ignore non-linked chats. Bot token in `.env`
  (back it up; never print it). Reply timestamps in SGT 24-hour.

### Phases & acceptance checks
1. **Read-only sync**: `/today`, `/why`, `/world`. *Accept*: offline router/handler tests
   pass with a fake transport; the chat-guard rejects spoofed/unlinked/forwarded messages.
2. **`/watch`** (a write): *Accept*: validates input, reports back, offline test passes.
3. **`/explain` async**: durable intent + worker + atomic publish + app refresh. *Accept*:
   offline test drives the intent path without real sends; the saved result is what the UI
   read returns.
4. **Help & polish**: `/help`, rate limiting, error messages.

### Tests (offline, no network)
`receive()` already takes an injectable `transport`. In `tests/test_telegram_commands.py`,
feed crafted `getUpdates` payloads, assert dispatch, assert the guard rejects
spoofed/unlinked/forwarded senders, and assert handler text from fixtures. Test `/explain`
via the durable-intent path with no real send.

### Risks
Security (only the verified `chat_id` may command — replicate every link-flow guard) ·
paid cost (ledger + cap + no auto-retry) · Telegram message size (chunk long explains) and
send rate · offset ownership (one consumer).

---

## 5. Reference patterns (copy-able)

### 5.1 Backend endpoint (`thesis/app.py`)
```python
@app.get("/api/v1/layouts/{page}")
def get_layout(page: str):
    from .db import transaction
    owner = auth.current_owner()
    with transaction(owner, consistent=True) as conn:
        return {"result": layouts.read(conn, owner, page)}  # layouts.* = new module
```
`auth.current_owner()` gives the acting account. Reads use `transaction(owner,
consistent=True)`; writes use `transaction(owner)`. Query helpers: `one(conn, sql,
params)`, `rows(conn, sql, params)` from `thesis.db` (parameterise — `%s` only).

### 5.2 Frontend API method (`frontend/src/api/client.js`)
`BASE = "/api/v1"`; `request(path, {method, body, signal})` sends cookies
(`credentials: "include"`) and unwraps `{result}`. Add:
```js
layout: (page, { signal } = {}) => request(`/layouts/${page}`, { signal }),
saveLayout: (page, body) => request(`/layouts/${page}`, { method: "PUT", body }),
```

### 5.3 Frontend lazy-fetch + merge (mirror the proven pattern in App.jsx)
```jsx
useEffect(() => {
  if (!data || data.layout) return;
  const controller = new AbortController();
  api.layout("overview", { signal: controller.signal })
     .then((result) => setData((old) => (old ? { ...old, layout: result } : old)))
     .catch(() => {});
  return () => controller.abort();
}, [scope, data]);
```

### 5.4 Read-only live timing (no restart; backend verification)
```python
import sys, time
sys.path.insert(0, "/absolute/path/to/repo")   # the Thesis repo root
import thesis.db as db
from thesis import service
with db.transaction(admin=True) as c:            # pick an owner/instrument to test
    owner = str(db.one(c, "SELECT id FROM accounts LIMIT 1")["id"])
s = time.perf_counter(); service.state(owner, "<iid>"); print((time.perf_counter()-s)*1000)
```
Run `.venv/bin/python that_script.py` from the repo root. Only time read-only paths. Do
not set `THESIS_DATA_DIR`.

### 5.5 Safe frontend deploy (never wipe `frontend/dist`)
```bash
cd frontend
npx vite build --outDir /tmp/dist-new --emptyOutDir        # build to scratch
cp -n /tmp/dist-new/assets/* dist/assets/                  # add new hashed assets, keep old
[ -d /tmp/dist-new/fonts ] && cp -n /tmp/dist-new/fonts/* dist/fonts/
cp /tmp/dist-new/index.html dist/index.html                # swap index LAST (atomic cutover)
```
Static frontend changes take effect on the next page reload. **Backend code changes need
the owner to restart the app** (you don't restart it).

### 5.6 Migration
Add `migrations/074_<name>.sql` with a comment explaining it and the approval date. It
applies on the next startup. Never edit an already-applied migration.

---

## 6. Sequencing
Feature A phase 1 (registry + self-contained blocks) is the enabling refactor and is
low-risk — do it first. Feature B phase 1 (read-only commands) is independent and can run
in parallel. Each phase on its own branch; nothing merges/pushes without the owner's
request.
