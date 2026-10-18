# Review guide: sentiment and alert redesign (branch `feat/sentiment-analysis-redesign`)

18 October 2026. For a teammate reviewing the branch before it is merged. Plan to spend about two hours on the first pass; you do not need to read everything.

## What this branch is

Two problems prompted it. The 14–15 October tech sell-off produced no useful alert, and the alerts that did arrive were slow, repeated and often low-value (opinion pieces, "X vs Y" listicles). The experiments that led to the redesign are in the [model comparison record](../../testing/sentiment-model-comparison.md). The [plan](../../development/sentiment-alert-redesign-plan.md) has the design, the phases and a status table.

**Size:** 36 commits, about 183 files, roughly 22,000 lines added. About a third is tests and a quarter is docs and experiments. The application code is about 3,700 lines in `thesis/`, 1,300 in `frontend/src/` and 12 new migrations (056–067).

**What is live versus built:**

| Phase | What it does | State |
| --- | --- | --- |
| 0 | Google News de-duplication | Live |
| 1 | One bad AI label no longer rejects a whole batch; labels survive model switches | Live |
| 2 | Keep GPT-5.4 + GPT-5.4 mini | Live (configuration only) |
| 3 | Fast lane every 15 min (price + news) separate from slow Reddit/HN lane | Built, switched off |
| 4 | Price-move detector (±3% day, 2 pts vs QQQ, ±5% over two days) + cited "why is it moving" explanation | Preview only, no Telegram |
| 5 | Smaller single-job prompts, importance, severity routing, daily recap, ratings, story de-duplication | Built, switched off; quality gates failing |

Most new behaviour sits behind settings that default to off. `.venv/bin/python -m thesis.runtime_status` prints the current mode and every switch.

## What we would like from you

1. **Correctness of the risky paths**: the files in the reading order below.
2. **Design pushback**: is this too much machinery for what it does? Where would you simplify?
3. **Anything that could send a wrong, duplicate or unwanted Telegram message.** This matters most.

You do **not** need to check prompt wording, experiment scripts, archived docs or the CSS.

## Reading order

### 1. Reliability (phase 1) — live, highest priority

- [`thesis/research/sentiment_reliability.py`](../../../thesis/research/sentiment_reliability.py): the item-repair rules.
- [`thesis/research/sentiment.py`](../../../thesis/research/sentiment.py) `render()`: where repair is applied. Note the cap: a batch needing more than a quarter of its items repaired is still rejected.
- [`thesis/research/sentiment_reuse.py`](../../../thesis/research/sentiment_reuse.py): label reuse across model changes.
- [`thesis/research/sentiment_batching.py`](../../../thesis/research/sentiment_batching.py): saved failed batches rechecked for free; one explicit split recovery.

Questions: can a repaired item ever trigger an alert? Can reuse attach an old label to changed source text?

### 2. Price moves (phase 4) — preview live

- [`thesis/monitoring/price_moves.py`](../../../thesis/monitoring/price_moves.py): rules and grouping (Decimal arithmetic, quote freshness, session dates).
- [`thesis/monitoring/move_watch.py`](../../../thesis/monitoring/move_watch.py) and [`us_session.py`](../../../thesis/monitoring/us_session.py): when checks run (US hours, holidays, early closes, DST).
- [`thesis/research/reference_prices.py`](../../../thesis/research/reference_prices.py): QQQ/SPY/SOXX as price-only references, not companies.
- [`thesis/research/move_explainer.py`](../../../thesis/research/move_explainer.py): the explanation must quote real headlines.
- [`frontend/src/components/MoveAlertCard.jsx`](../../../frontend/src/components/MoveAlertCard.jsx): how a move is shown.

Questions: timezone and session edge cases; grouping a two-day fall with a one-day rebound; whether an explanation can claim a cause it can't support.

Known gap: no catch-up for sessions missed while the Mac sleeps; see the [operations review](../2026-10-17/redesign-operations.md#sleeping-mac-and-missed-sessions).

### 3. Telegram safety (phase 5) — off, but review before it is switched on

- [`thesis/monitoring/alert_routing.py`](../../../thesis/monitoring/alert_routing.py): high goes to Telegram, medium to the daily recap, low stays in the app. Previews must never be promoted to real sends.
- [`thesis/monitoring/telegram_stories.py`](../../../thesis/monitoring/telegram_stories.py): one story at most once per account per 24 hours, across alerts and recaps.
- [`thesis/monitoring/daily_telegram.py`](../../../thesis/monitoring/daily_telegram.py) and [`daily_updates.py`](../../../thesis/monitoring/daily_updates.py): recap and cost-notice delivery.
- [`thesis/monitoring/telegram.py`](../../../thesis/monitoring/telegram.py): existing sender; check the changes only.

Questions: any path to a duplicate, to a send after the owner switched delivery off, or to a resend after an uncertain delivery?

### 4. Collection lanes (phase 3) — off

- [`thesis/monitoring/watch_lanes.py`](../../../thesis/monitoring/watch_lanes.py) and the changes in [`news_watch.py`](../../../thesis/monitoring/news_watch.py): two independent leases per company.
- Changes in [`reddit_rss.py`](../../../thesis/research/reddit_rss.py) and [`hackernews.py`](../../../thesis/research/hackernews.py): incremental fetching.

Question: can the fast and slow lanes race and publish the same reading twice?

### 5. Smaller prompts (phase 5) — off

- [`thesis/research/sentiment_tasks.py`](../../../thesis/research/sentiment_tasks.py) and [`sentiment_task_runner.py`](../../../thesis/research/sentiment_task_runner.py).

Skim only. These fail their quality gate (24/50 agreement with owner labels against a target of 40/50), so they will change.

### 6. Migrations 056–067

[`migrations/`](../../../migrations/). All are additive. **056–064 are already applied to the owner's live database and must not be edited.** 065–067 apply automatically on the next app start. Look for missing indexes, constraints that could block a later change, and row-level security on new private tables.

## Running it

```bash
LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8 .venv/bin/python -m pytest -q
```

The suite uses its own throwaway database and makes no network calls. It takes about 8½ minutes; the locale setting is required or the test database will not start. Last run on 18 October at 15:57 SGT: **2,784 passed, 93 optional skips**; frontend **202 passed**.

**Known failing test:** `tests/test_daily_updates.py::test_daily_schedule_catches_up_one_window_at_a_time_and_keeps_boundary_routes_in_next_day` fails only when run between 00:00 and 07:00 Singapore time. The test assumes the next 07:00 recap is always tomorrow; the code is correct.

```bash
cd frontend && npm test
```

```bash
.venv/bin/python -m thesis.runtime_status
```

The last command needs the owner's local database; skip it on another machine.

## Please do not

- **Start the app from `main` against an existing database at schema 064+.** `main` lacks these migration files and startup will refuse.
- **Merge or push to this branch** without checking with the owner first; it is the live app's source.
- **Treat failed gates as passed.** Phase 1–4 acceptance needs several days of live observation, and phase 5 quality and noise currently fail. Those are recorded honestly; don't relabel them.

## Known open issues

- Phase 5 quality: 24/50 owner-label agreement and 11.1% noise in the replay (targets 40/50 and ≤10%). The old pipeline has not been scored on the same 50 labels yet.
- Missed-session catch-up for price alerts is not built.
- AI cost is about US$3.90/day against a US$3 target (not yet a full closed day).
- The running app predates the startup fingerprint, so its exact running version is unknown until the next deliberate restart.
- Overnight sleep on 18 October stopped or failed 20 checks; the three-day completion gate needs the Mac kept awake.
