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

At this checkpoint, outstanding work included Telegram digest/cost transport, actual severity routing,
owner approval of delivery and cost level, owner-labelled quality checks,
one-week noise replay and live/shadow/outcome measurements. Existing 061/062 and
new 063 remain unapplied; this does not mark any phase acceptance item passed.

## Telegram transport follow-up — 17 October 2026

Migration 064 prepares the `digest` and `cost` outbox kinds and a private,
append-only `telegram_digest_items` mapping. It is **unapplied live**. Existing
settings and preview rows are untouched; a preview publication cannot acquire a
live route, a real recap cannot include a shadow route, and preview/empty recaps
cannot enter the outbox. Migration 064 allows new actual route records without
promoting any old proposal. Normal record creation still produces previews;
connecting the approved live routing mode remains separate work.

`THESIS_DIGEST_TELEGRAM_ENABLED` and `THESIS_COST_TELEGRAM_ENABLED` both default
off. Delivery additionally requires daily reports enabled, an explicit
`THESIS_DAILY_TELEGRAM_STARTED_AT`, and the account's existing connected/enabled
chat. Cost notices require the installation owner and a currently matching,
explicit cost level. Records before the delivery start/account activation or
older than 24 hours are not newly queued. Missing/future/invalid delivery starts
keep delivery off. Turning a switch off after queuing is rechecked before send.
These settings do not authorize themselves: new alert types and severity routing
still need the owner's explicit live approval.

A recap rechecks each underlying publication's source permissions and current
private-idea revision. It includes up to five complete numbered updates, with
the excerpt and source link beside the relevant company, at most two links in
the message, and a count directing the reader to the remaining saved items.
Withheld/changed records are not forwarded; no eligible records means no message.
Grouped move member lists are never partially truncated to fit. HTML is escaped
and parsed text is limited to 3,800 UTF-16 units. Rendering calls neither AI nor
original sources, marks no alert reviewed and does not regenerate a recap.

Each displayed update can have its own Useful / Not useful buttons. Before HTTP,
send intent and the exact shown-member mapping commit together. The confirmed
message's send attempt determines which original alert a button rates. A known
rate-limit rejection may re-render after current access changes; it cannot
silently reuse the old mapping. Disabled ratings create neither buttons nor a
mapping. Current-bot/private-sender/exact-sent-message checks, durable callback
idempotency and acknowledgement handling remain; cost notices have no rating
buttons. A callback arriving before send acknowledgement waits without advancing
the shared cursor. Interrupted or uncertain sends are never retried automatically.

Owner cost messages show the exact saved confirmed charge, the chosen level,
Singapore dispatch date, and unresolved maximum separately. Changing the level
after queuing makes an obsolete notice ineligible. There is no new spending cap
or paid retry. Other accounts receive neither the cost type description nor
installation-wide figures. Delivery history uses plain labels for recap, cost
and price records; new-type descriptions appear only when those delivery switches
are active. Viewing history never enables delivery or sends a test.

New-queue errors roll back only their savepoint and log a fixed safe message;
ordinary alert delivery can continue. Existing account pause/disconnect, pacing,
bounded known-rejection retries and uncertain-send recovery remain in force.

Final affected suites: **166 pass**, including the final button-presence and
cross-account mapping guards. Frontend 202 tests/build/scoped format and six
isolated browser groups at 1440/390/320 pass, with zero HTTP requests; screenshots
inspected. The broad offline run passes **2,495 tests / 93 optional skips**; it
was collected before the final button-presence guard. The subsequent 166-test
affected run checks that final guard and cross-account mapping access. All
transport tests use an authored mock bot; no live delivery test has been
authorized or performed.

Cost US$0. No paid call, source refresh, environment/account-setting change,
live migration, app/DB restart or frontend installation. The user's `app.css`
remains exact. Private evidence is retained under
`.local/live-tests/redesign-phase-5-20261017/daily-telegram-prepared/`.

Phase 5 remains **not done**: actual routing/record production, independent
one-week noise replay, owner-labelled quality (0/50), new-prompt hard-case
evaluation and live/shadow/outcome gates remain outstanding. None of these
preparations supplies the owner's delivery or cost-level approval.
