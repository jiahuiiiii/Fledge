# Smaller sentiment tasks, alert ratings and routing previews

Prepared 17 October 2026 on `codex/redesign-phase-5`; **not installed or enabled**.
This is part of phase 5, not its acceptance result. Existing prompt, saved
research, watch preferences and Telegram delivery remain unchanged.

## Separate requests, reusable evidence

`THESIS_SENTIMENT_TASKS` defaults off. When enabled, the existing quick relevance
check handles fresh sources, followed by separate tone/evidence, news-only
event/importance and candidate-only duplicate tasks. Instructions remain below
6,000 characters each; complete sources, required discussion context, eight-item
and 48kB request bounds remain. Optional sibling context can be omitted explicitly
when needed to fit; required parents cannot be silently dropped.

The runner uses the app's priced ledger and existing bounded concurrency. It
validates tone before paying for news importance, and importance before duplicate
comparisons. Saved settled answers are checked before new work in each stage.
Unsettled calls never dispatch again automatically. The existing explicit single
retry and terminal two-child split are supported; children cannot retry or split.
An interrupted split reuses settled children for free, and requires an explicit
continuation before sending unsent children. Failed paid answers remain retained.

The version bridge carries unchanged old tone labels when reliability reuse is
enabled, retaining each item's original prompt, model and call. Missing news
importance is a separate new task, so activation can still have a one-off cost;
this cost has not been measured. Old readings and raw responses are immutable.
Negative duplicate comparisons are cached by the exact source-pair content, not
by a rolling news-window timestamp. Source access, cancellation, duplicate IDs,
exact citations and earlier-source comparison guards remain enforced.

Code forces opinions, comparisons, price recaps, analyst/market commentary,
non-events and unrelated items to low importance. High/medium importance requires
own-source development evidence. Authored validator tests establish these rules,
not semantic accuracy. The blind owner-labelled 50-source and six-hard-case gates
are still required before activation; no new-prompt paid evaluation has run.

## Explicit private ratings

`THESIS_ALERT_FEEDBACK` defaults off. When enabled, Updates adds Useful / Not useful
beside each alert's evidence, for company, idea, condition and move records. A
selected choice is visible; errors preserve the last saved choice, and late
responses cannot affect another alert after navigation. Withheld details do not
show the controls. Viewing never saves a vote, calls AI or changes research.

New migration **061** adds private, forced-RLS, append-only `alert_feedback` and
a host-service-only `telegram_poll_state`. It is tested only in disposable
databases and is **not applied to the live database**. There is no enrollment or
backfill. The database checks that each rating names a published alert belonging
to its account. Repeated identical app clicks do not create another row; a changed
choice adds a row. The current rating is the latest retained row.

Telegram uses the same two choices on newly sent existing alert types when the
feature is enabled. This does not enable any new alert type or delivery route.
Callback data identifies the outbox delivery, not an account supplied by the
client. A vote requires the current bot, linked private sender/chat, exact sent
message ID and a confirmed sent delivery. Uncertain/failed messages cannot be
rated through callbacks. Test messages have no rating buttons.

One cross-process bot cursor handles both connection messages and ratings, so
connecting another account cannot consume and lose a pending rating. Callback
votes have durable idempotency keys; replay cannot undo a later app vote. Ratings
commit before advancing the cursor, and acknowledgement failure cannot repeat a
vote. Raw Telegram updates are not retained in the global cursor table.

The receiver requests both update types explicitly, bounds callback data to
Telegram's 64-byte limit, acknowledges clicks and handles randomized update IDs
after a week without updates. These transport constraints follow the official
[update API](https://core.telegram.org/bots/api#getupdates),
[callback query](https://core.telegram.org/bots/api#callbackquery),
[button](https://core.telegram.org/bots/api#inlinekeyboardbutton) and
[acknowledgement](https://core.telegram.org/bots/api#answercallbackquery) contracts.

## Verification and remaining work

### Routing preview follow-up — 17 October 2026

New migration062adds private append-only routing decisions and an explicit
preview marker for new importance-based company publications. It is **not applied
live**. `THESIS_ALERT_ROUTING_PREVIEW` defaults off; background capture also requires
an explicit `THESIS_ALERT_ROUTING_STARTED_AT` so historical alerts are not enrolled
silently. The channel is a proposal, not a transport instruction.

High importance proposes immediate Telegram, medium proposes a daily digest,
and low proposes app-only. Price events propose high; saved comparison changes
and older unscored alerts propose a daily review rather than an invented high
score. Saved-idea decisions use only the news sources actually matched to that
private idea, joined back to their immutable sentiment/importance evidence.
Withheld evidence stays app-only. Tone, a large amount or a positive/negative
label cannot promote an item. Code-owned low-value and own-citation checks remain.

Company watches can now prepare a new importance preview for a neutral or
favourable development, in addition to the old adverse-news path. This uses
fresh-source/observed-story guards, so backfilled importance on an old label or
a seen repeat cannot create an alert. Initial baselines stay quiet. Existing
saved-idea watch preferences are respected. All new importance publications are
previews, with a database constraint; both outbox selection and dispatch refuse
them. This does not alter ordinary delivery of existing alert types during shadow
comparison. A shadow calculation failure is isolated from ordinary Telegram work.
When old and new company publications cover the same source set, the routing
journal proposes only one immediate delivery and records which preview covers
the older publication. This preserves the original delivery log for comparison.

Updates shows the preview notice once, with importance and its supporting wording
inside the source card. Quotes already shown for tone are not repeated. The
proposed route and usefulness controls sit below the same evidence. All four
event kinds retain private routing journals; old records and model answers are
not rewritten. This is not yet live severity routing or a daily digest service.

Related post062backend suites263pass/2optional skips; final background-isolation
suite86pass; final duplicate-proposal/delivery/review suites99pass (overlap).
Frontend202tests/build/scopedformat and10isolated inbox/
price/company-routing browser groups1440/390/320pass,0HTTPcalls; screenshots
inspected. The initial browser check found a repeated preview notice in embedded
evidence; the duplicate was removed and the diagnostic retained. Earlier full
backend2398pass/93skips applies to the preceding pipeline/rating checkpoint.

Smaller-task integration and related suites: 164 offline tests pass. Initial
explicit-split continuation guard failure is retained and fixed. Rating/Telegram/
review/isolation suites initially pass 86 tests; the full suite also includes
later all-kind membership and failed-acknowledgement cases. Browser checks cover
eight rating behavior groups and nine price/inbox groups at 1440/390/320 with
zero HTTP requests. The first rating browser fixture failed because it did not
wait for React to render the intermediate navigation; this diagnostic is retained,
and the corrected fixture verifies the actual A → B → A transition.

Pipeline/rating full offline backend suite: **2,398 passed / 93 optional skips**. Final affected
164 tests pass after the last repair-provenance addition (overlapping suites).
Frontend:202tests, build and scoped formatting pass. The full-page browser capture
resized the artificial shell while taking a screenshot; final inspection uses
element/viewport captures with the expanded evidence and rating visible together.

| Phase5 acceptance item | Result | Evidence |
| --- | --- | --- |
| One-week replay has at most10%low-value Telegram-bound alerts | **Failed / unverified** | Actual routing and independent noise replay remain;0/7replay days |
| Owner-labelled quality remains at least80%, plus4/6hard cases | **Failed / unverified** |0/50owner labels;0/6new-prompt hard-case measurements |

Cost US$0; no paid call, real-source fetch, live migration, configuration change,
frontend installation or restart. No change to the user's `app.css` edits.

Still outstanding: owner annotations (0/50 received), new-prompt quality/cost
evaluation, live severity routing and daily digest, cost summary/alert, one-week noise
replay and live/shadow/outcome measurements. These changes do not mark phase 5
or the redesign done.

Follow-up17October: [daily recap/spending preparation](daily-updates.md) now adds
unapplied063and the optional read-only Updates panel. Private recap membership,
owner-only exact costs and preview threshold notices are tested, still off.
Telegram digest/cost transport and live activation remain outstanding. Final155
related/13integration/202frontend tests and22browser groups pass. Final stable full
offline2468pass/93optional skips. The earlier broad run's2464passes/93skipsand
checksum failure from overlapping unapplied-migration edits remain as diagnostics.
This is preparation, not acceptance.

Further follow-up17October: [daily Telegram transport](daily-updates.md#telegram-transport-follow-up--17-october-2026)
now prepares digest/cost outbox types and immutable mappings from sent numbered
buttons to original private alerts. Final166affected offline tests and6browser
groups pass; delivery is still off,064unapplied, normal records still previews.
Actual routing/record production and all quality/noise/live approval gates remain.

Actual-routing follow-up17October: [the default-off actual-mode connection](daily-updates.md#actual-routing-connection--17-october-2026-prepared)
now prepares new actual publications/routes/recaps/cost notices, separate start
and policy identities, and immediate-outbox filtering at selection and dispatch.
Old previews stay immutable; new importance records cannot escape through the
legacy path on rollback.065unapplied live; settings remain off.13new/257related
backend,202frontend/build and13isolated browser groups pass,0HTTPcalls,US$0.
Full offline2509pass/93optional skips.
Cross-publication24-hour story suppression, independent7-day noise replay,
owner quality0/50, hard cases0/6 and approval/live/shadow gates still remain.
