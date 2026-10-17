# Smaller sentiment tasks and alert ratings

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

Smaller-task integration and related suites: 164 offline tests pass. Initial
explicit-split continuation guard failure is retained and fixed. Rating/Telegram/
review/isolation suites initially pass 86 tests; the full suite also includes
later all-kind membership and failed-acknowledgement cases. Browser checks cover
eight rating behavior groups and nine price/inbox groups at 1440/390/320 with
zero HTTP requests. The first rating browser fixture failed because it did not
wait for React to render the intermediate navigation; this diagnostic is retained,
and the corrected fixture verifies the actual A → B → A transition.

Full offline backend suite: **2,398 passed / 93 optional skips**. Final affected
164 tests pass after the last repair-provenance addition (overlapping suites).
Frontend:202tests, build and scoped formatting pass. The full-page browser capture
resized the artificial shell while taking a screenshot; final inspection uses
element/viewport captures with the expanded evidence and rating visible together.

| Phase5 acceptance item | Result | Evidence |
| --- | --- | --- |
| One-week replay has at most10%low-value Telegram-bound alerts | **Failed / unverified** | Routing/replay not implemented;0/7replay days |
| Owner-labelled quality remains at least80%, plus4/6hard cases | **Failed / unverified** |0/50owner labels;0/6new-prompt hard-case measurements |

Cost US$0; no paid call, real-source fetch, live migration, configuration change,
frontend installation or restart. No change to the user's `app.css` edits.

Still outstanding: owner annotations (0/50 received), new-prompt quality/cost
evaluation, severity routing and daily digest, cost summary/alert, one-week noise
replay and live/shadow/outcome measurements. These changes do not mark phase 5
or the redesign done.
