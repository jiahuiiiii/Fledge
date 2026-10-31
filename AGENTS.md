# Fledge — implementation guide

Updated 18 October 2026. Keep all Fledge work in this repository (`Thesis`), separate from Fork.

## Read first

Read [README.md](README.md), then the relevant feature contract and [sentiment/alert plan](docs/development/sentiment-alert-redesign-plan.md). This guide contains current rules; the plan contains requirements and a short status table. Put dated progress and verification in `docs/reviews/YYYY-MM-DD/`, not here.

Earlier checkpoints are preserved in [implementation history](docs/archive/status/2026-10-17-implementation-history.md) and [redesign progress](docs/archive/status/2026-10-17-sentiment-redesign-progress.md). Their old budgets, “unapplied” statements, model choices and permissions are historical, not current authority. Later direct owner instructions take precedence.

## Operating rules

- Never start, stop or restart the real app or database from an agent sandbox. An earlier sandbox restart broke outbound HTTPS and monitoring for about eight hours. Use the owner's Terminal for `.venv/bin/python run.py --port 8841` from this repository.
- Restart only after a fresh idle check: no watch lease, AI call, data update, evaluation, send or source action; nothing due in the next 90 seconds. A check is an observation, not a reservation. Recheck immediately before stopping the app.
- Back up `.env` before changing it. Never print secrets or add personal details to docs/commits. Do not change saved research, watch preferences or Telegram preferences without a direct request.
- Paid calls use the existing spending ledger. No automatic paid retries. Retain failures, raw responses, charges and unresolved reservations. Disclose expected cost before any paid test over US$2; a completed paid attempt does not authorize another attempt.
- Tests are offline and make no network calls. Use `LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8 .venv/bin/python -m pytest -q tests/<file>.py`. Test databases are disposable; never point them at the live workspace.
- Never edit an applied migration. Add a new numbered file when a schema change is required. Startup **automatically applies all pending migrations**; schema approval and feature activation are separate.
- The owner has approved additive migrations for the redesign: 065–067 (applied), on 20 October 068, which lets saved weekly reviews include price moves, and on 25 October 071, which stores each sentiment reading's cutoff in an indexed column, and 072, which saves finished filing figures per account and exact inputs, and on 29 October 073, which lets one watch check both its saved reasoning and its saved question, and on 31 October 074, which saves each account's overview/home widget layout (branch `feat/workspace-widgets`), and 075, which records Telegram command requests for slow commands (branch `feat/telegram-commands`). They apply at the next deliberate restart, not blocked by an approval guard. Any further schema change needs a new owner approval.
- `feat/sentiment-analysis-redesign` was merged (PR #9) and deleted on 20 October. Current work is on `feat/alert-briefs-weekly-review`, branched from it. Do not check out or restart from a branch that lacks the database's applied migration files. Do not merge, push or open a PR without the owner's request. Preserve unrelated work.
- `frontend/src/styles/app.css` is editable again: its leftover uncommitted banner fix was committed on 20 October at the owner's request. Leave `.claude/` alone.
- The owner authorized continuing the full redesign without phase-boundary stops. Still obtain the explicit live choices below; do not mark incomplete acceptance gates done.

## Current deployment checkpoint

Read-only observation, 17 October at 23:25 SGT. Recheck before operating; this table is not live telemetry.

| Area | Verified state |
| --- | --- |
| Branch | `feat/sentiment-analysis-redesign`, unmerged |
| App | Running since 15:54:29 SGT; exact startup source fingerprint was not recorded |
| Database | Schema 064; all applied file checksums match |
| Next startup | Automatically applies approved 068 (065–067 already applied) |
| Operating mode | Price previews: existing combined news/social watches plus price detection |
| Fast/slow lanes | Off; passive provider metrics on |
| Smaller sentiment tasks | Off |
| Severity routing and daily records | On from 20 October 07:16:59 SGT (owner approval; see below) |
| New move/digest/cost Telegram delivery | On from 20 October 07:16:59 SGT; account Telegram preferences unchanged |
| Restart | Not performed; recheck active work and due times immediately beforehand |

`price-move-rules-2` was saved at 14:03 and committed at 14:05, before the 15:54 restart. Do not claim that particular fix is definitely absent from the running app. Later phase 5 changes were made after startup. Without a matching startup manifest, report the exact running version as unknown.

The prepared [runtime status tool](thesis/runtime_status.py) is read-only: `.venv/bin/python -m thesis.runtime_status`. The next app startup records its source fingerprint and operating-mode summary before workers start. The tool compares that record with disk, checks schema compatibility and reports restart blockers. A missing or mismatched process record stays unknown. Named modes summarize existing gates; they add no settings and do not override account preferences.

## Approved choices and remaining gates

| Choice | Owner decision |
| --- | --- |
| Main / quick models | GPT-5.4 / GPT-5.4 mini; retain existing labels and provenance |
| Explainer | GPT-5.5, preview only |
| Move rules | ±3% session, 2 percentage points against QQQ, ±5% over two sessions |
| Fast hours | 08:30–17:00 New York, adjusted for early closes |
| Preview period | Ended early by the owner on 20 October at 07:16:59 SGT |
| Additive migrations | Approved; application remains automatic at startup |
| Actual severity/new Telegram routing | **Approved 20 October** by the owner; live from 07:16:59 SGT (`THESIS_ALERT_ROUTING_LIVE`). Urgent alerts and price moves go to Telegram; others go to the daily summary |
| Daily cost alert level and delivery | **Approved 20 October**: US$5 a day, sent by Telegram; daily summary also sent by Telegram from 07:16:59 SGT |

Fast cadence waits for the 24-hour passive baseline, started 17 October at 12:55:59 SGT. It cannot finish before 18 October at 12:55:59 SGT. Three-day lane timing/denial comparisons, five trading days of previews and ten trading days of outcomes remain unverified.

Latest core observation at 23:21 SGT: 43 completed, zero failed/stopped and two unfinished checks over 10.72 of 48 hours. Normal AI cost is US$2.352457, with no unresolved amount or closed daily window. The simple projected rate is about US$5.27/day, above the US$3 target; do not present a partial window as a passed daily-cost gate.

Phase 5's approved purpose replay completed 172/172 snapshots over seven input dates. Noise is **2/18 messages (11.11%)**, failing the ≤10% target: zero of 11 immediate messages and two of seven recaps. Additional cost US$1.87638250; cumulative news-test cost US$4.31477125, no unresolved holds. Same-history assistant review is not owner ground truth or an all-alert/live result. Coverage/usefulness remains uncertain. [Results](docs/testing/news-noise-replay.md).

Owner review **50/50 received on 18 October** from the supplied file path. Exact relevance-and-tone agreement is **24/50 (48%)**, failing the required 40/50; relevance 38/50, tone 29/50. Hard cases remain 4/6. All 50 review/AI evidence projections match, including 17 cases with saved context; 56 cached answers revalidate free. Preserve the labels and failed gate: disagreements include rubric/coverage ambiguity and are not automatically AI errors. Do not inspect browser storage, scan Downloads, supply labels or change them to match the AI. Raw exports stay private and ignored by Git. [Result and owner feedback](docs/reviews/2026-10-18/owner-sentiment-quality.md).

## Immediate priorities

Finish the first useful path before expanding optional features: reliable faster checks, a cited price-move preview, then explicitly approved Telegram delivery after the preview period. Ratings, daily recaps and optional discussion weighting remain behind their existing gates.

Price monitoring requires an awake Mac and running app. US regular hours in Singapore are 21:30–04:00 during US daylight time and 22:30–05:00 during US standard time; early closes differ. The current worker has **no durable missed-session catch-up**. A session missed during sleep can be lost even if the next day rebounds. Closing-price recovery must be dated as delayed, retain exact historical inputs and deduplicate against earlier alerts; it cannot recover an intraday excursion that reversed before close. See [operations review](docs/reviews/2026-10-17/redesign-operations.md).

## Engineering and evidence rules

- One React/Vite frontend, FastAPI app, durable worker boundary and PostgreSQL. Reuse the inspected code; do not introduce another framework, microservice or competing schema authority.
- Validate account context on the server. Restricted roles, RLS and current source permissions apply to live reads, saved history, downloads and background work. Shared research must not contain private reasoning.
- Keep semantic history append-only. Saving a definition requires its expected revision; late jobs cannot replace newer work. Publish complete results and their events atomically. External side effects use durable intent and must not run inside a retryable transaction.
- Numerical results use validated inputs and Decimal arithmetic. Keep financial periods, currencies, reported facts, management forecasts, analyst estimates, social samples and AI interpretations distinct. Missing data is unknown, never zero or neutral.
- Preserve source versions, publication/availability dates, original quotes, model/prompt/policy provenance and assessment cutoffs. Replays must declare availability and never claim later saved labels were available earlier. Valid quotations alone do not prove semantic accuracy.
- Treat retrieved content as untrusted evidence. Do not infer omitted text, parents, causal price explanations or unsupported company relationships. Preserve source withdrawal/access restrictions in every presentation path.
- Keep original failures and limited tests visible. Synthetic fixtures, same-history retests, actual provider calls and owner labels are different evidence; do not pool them into a stronger claim.
- Test each behavior change and related suites. Run a broad suite when scope/risk warrants it; do not keep repeating completed tests without new changes or unresolved concerns.

## Product and design rules

Fledge helps people investigate companies, inspect contrary evidence and revisit saved reasoning. It does not execute trades or recommend buying/selling. Prioritize alerts and sentiment; optional extra valuation breadth is lower priority. Production hosting, billing and outreach are not authorized by local implementation work.

Follow the existing compact market-workspace design: sans-serif, watchlists, charts and evidence cards. Use simple controls and plain language. Keep numbers, explanation, uncertainty and source evidence together; avoid scattered text, unexplained scores and implementation details in product flows. Support keyboard/focus, reduced motion, meaningful loading/error/empty states and widths from 320 px.

Beginner mode rewords saved evidence without inferring new conclusions; Pro retains detailed tabs. Financial reporting dates remain source dates; display timestamps use Singapore time in 24-hour form. Do not silently change calculations or saved values for presentation.

## Find the relevant contract

| Work | Read |
| --- | --- |
| Sentiment / recovery | [Batching](docs/features/sentiment-batching.md), [context](docs/features/context-aware-sentiment.md), [smaller tasks and ratings](docs/features/sentiment-tasks-and-alert-ratings.md) |
| Watches / price alerts | [Lanes](docs/features/watch-lanes.md), [price moves](docs/features/price-move-alerts.md), [Telegram](docs/features/telegram-alerts.md), [daily updates](docs/features/daily-updates.md), [story suppression](docs/features/telegram-story-suppression.md) |
| Evidence / sources | [SEC fundamentals](docs/features/sec-fundamentals.md), [original company research](docs/features/original-company-research.md), [source coverage](docs/features/multi-source-research.md), [reading journey](docs/features/reading-journey.md) |
| Financials / peers | [Financial reading](docs/features/financial-reading.md), [competitor position](docs/features/competitor-position.md), [public forecasts](docs/features/public-financial-forecasts.md) |
| Account / UI | [Managed login](docs/features/managed-login.md), [onboarding review](docs/reviews/2026-10-16/onboarding-friction-personas.md), [Beginner mode](docs/features/beginner-mode.md), [portfolio read](docs/features/portfolio-read.md) |
| General history | [Documentation index](docs/README.md), [provenance](PROVENANCE.md), [archived checkpoints](docs/archive/status/2026-10-17-implementation-history.md) |

## Latest maintenance — 18 October 2026

Owner quality fails at 24/50 exact matches. Rubric 2's paid run completed 56/56 for US$0.47429 with zero repairs/retries/unresolved cost: agreement stays 24/50, hard cases fall from 4/6 to 3/6. Three separate owner clarifications now inform [rubric 3](docs/testing/sentiment-tone-rubric.md): meaningful short replies use topic context; explicit wishes for gains are positive attitude; a past gain plus an open question alone is neutral. Eight teaching snippets, 23 separate development cases and 192 related offline tests; no candidate-3 model test. Original labels/scores stay exact; exposed labels are not unseen validation. Candidate stays off; no new paid attempt is authorized. No live setting change or restart was performed. [Owner follow-up](docs/reviews/2026-10-18/sentiment-owner-clarifications.md) · [original quality](docs/reviews/2026-10-18/owner-sentiment-quality.md) · [rubric-2 run](docs/reviews/2026-10-18/sentiment-rubric-candidate.md).
