# Daily recap and AI spending previews

Prepared 17 October 2026 on `codex/redesign-phase-5`. **Not installed or enabled;
phase 5 is not done.** Migration 063 is unapplied live. This preparation creates
private preview records and a read-only Updates panel; it does not send a new
Telegram message, enroll accounts or change existing preferences/research.

## Daily membership

`THESIS_DAILY_REPORTS` defaults off and also requires an explicit
`THESIS_DAILY_REPORTS_STARTED_AT`. The prepared schedule is 07:00 Singapore time,
still part of the eventual activation review. The first window starts at feature
activation; later windows are contiguous and half-open. Recovery prepares one
missed window per poll rather than silently skipping days.

Only medium/digest routing decisions qualify. Membership uses route creation
time, so a route prepared after an event's day is considered in its actual routing
window. The latest routing decision is checked before selecting medium; a newer
high/app-only decision cannot accidentally leave its older medium proposal in a
new recap. A publication belongs to at most one recap across policies. More than
1,000 members rejects the whole recap explicitly rather than truncating it.

Migration 063 adds forced-RLS `daily_digests`, `daily_digest_members`,
`daily_spend_reports`, `daily_cost_notices` and private runtime state. Membership
must reference that account's actual medium route inside the saved window.
Research/recap/spending/notice records are append-only; runtime pacing and safe
failure status can change. There is no backfill or data replacement.

Opening a recap checks current source access, ratings and review status, with
20 records per page. It uses the existing alert evidence components and explicit
usefulness buttons. Viewing never marks reviewed, generates AI, fetches original
sources or queues delivery. Closing and reopening checks access again; late
responses after navigation cannot restore removed evidence.

## Exact spending, separate unresolved amounts

Only the installation owner receives installation-wide aggregate costs, including
shared/private calls and experiments. Other accounts receive no spending totals,
notices or account identities. Aggregate ledger reads are database-enforced
repeatable-read/read-only; no prompt or personal detail is exposed.

Daily cost uses the call's dispatch date in Singapore, midnight-to-midnight.
Confirmed charges and unresolved reserved maxima are separate integer nano-dollar
amounts. A settlement later than the observation remains pending at that
observation. Experiment charges are included in the total and shown separately.
Closed-day snapshots remain immutable; their current aggregate is read alongside
them so later settlements do not remain displayed permanently as unresolved.
UI amounts show cents, with exact totals available beside them.

`THESIS_DAILY_COST_ALERT_USD` has **no implicit approved level**. A configured level
must be positive, finite whole cents. A notice requires confirmed charges strictly
above that level, once per day/policy; unresolved maxima alone cannot trigger it.
Late settlements revisit their original dispatch day, including after preparation
failure/backoff. The successful observation cursor is separate from retry timing.
All notices currently created are previews. This is a notification threshold,
not a spending cap or a reason to retry a paid call.

## Isolation and rollback

One cross-process owner lock and one-minute pacing prevent duplicate preparation.
Failure leaves existing updates and ordinary Telegram delivery available, records
a safe status and backs off one hour. No raw exception reaches the UI or logs.
Turning the feature off hides the panel and stops new preparation without erasing
saved records. Source access is checked again when it is turned back on/opened.

## Verification and remaining gates

Final related offline suites: 155 pass, including concurrency, exact boundaries,
private membership, pagination, withdrawal, safe failures and settlement during
backoff. Final database integration: 13 pass. Frontend 202 tests/build/scoped format
pass; 10 daily-panel and 12 existing inbox/browser groups pass at 1440/390/320 with
zero browser HTTP requests; screenshots inspected.

The final stable full offline run passes **2,468 tests, with 93 optional skips**.
The earlier broad run overlapped edits to this unapplied migration: 2,464 pass/93
optional skips and 1 integration failure on the checksum guard. Its diagnostic is
retained alongside the clean rerun and final affected-suite evidence. Initial
SQL/test-fixture and browser-selector diagnostics are retained too.

Cost US$0, zero paid/provider calls, no real database migration, environment change,
app/DB restart or frontend install. User `app.css` preserved. Private evidence:
`.local/live-tests/redesign-phase-5-20261017/daily-updates-prepared/`.

Still outstanding: Telegram digest/cost transport, actual severity routing,
owner approval of delivery and cost level, owner-labelled quality checks,
one-week noise replay and live/shadow/outcome measurements. Existing 061/062 and
new 063 remain unapplied; this does not mark any phase acceptance item passed.
