# Redesign outcome evidence — 17 October 2026

The prepared operator `experiments/soclaas_replay/redesign_outcomes.py` reads a
repeatable, database-enforced read-only snapshot. It neither installs nor changes
settings, research, delivery or spending. Aggregate output omits account and
company identities, message text and ledger request keys. Private alert, watch,
assessment and rating rows are explicitly scoped to the supplied account;
installation costs include all accounts and ordinary explainer requests.

Supply a timezone-aware confirmed **actual-delivery** rollout time with `--since`
and the local account identifier with `--owner`. `--actual-delivery-confirmed`
is operator evidence, not a deployment command. A preview installation cannot
pass this gate. `--no-model-switch-confirmed` records the deliberately retained
model pair; without this evidence, switch cost remains unknown. An actual future
switch needs a separately bound 24-hour ledger comparison.

The window contains the first ten whole US regular sessions after rollout;
mid-session activation begins with the next session. Weekends, holidays and
early closes use the app's verified 2026–2028 calendar. Unknown years fail
explicitly. The last 24-hour cost bucket must finish too. Partial windows and
zero denominators stay pending; they do not award a zero-failure pass.

## Price assessments

Unapplied migration **067** prepares private append-only `move_assessments`.
The worker records all watched-company assessments before attempting event
publication, including non-triggers, missing/stale quotes, withheld references
and already-claimed triggers. Each record retains exact quote, thresholds,
measurement policy, observation clock and worker run. The active matching
worker lease and watched-company/quote membership are enforced by the database.
There is deliberately no foreign key to a terminal run: observations survive a
later worker failure. Logging failure rolls back only its savepoint, continues
detection and leaves a fixed coverage-gap diagnostic in run history.

The outcome denominator counts first qualifying observations per company,
session, trigger direction and policy. Repeated polls do not add moves; grouped
market alerts can cover several triggering companies, but context-only members
cannot satisfy the denominator. Only confirmed sent actual move deliveries
match; previews, queued/uncertain sends, wrong directions/policies and earlier
events do not. Missing assessments, bad quotes, failed audit writes and orphan
runs leave coverage incomplete. A publication failure can therefore produce a
missed qualifying move instead of disappearing from the denominator.

Latency uses wall time from the first qualifying saved quote to confirmed send.
An overnight delay remains an overnight delay. The report cannot reconstruct
unobserved intraday prices or prove that missing scheduled checks ran.

## Other measurements

- Completion includes failed, stopped and unfinished attempts; a result after
  the observation cutoff is unfinished. Duration medians use completed fast and
  slow checks separately. Failure chains close only on a recorded success.
  These are recorded-attempt spans; historical disable/re-enable intervals and
  missing schedule slots are not reconstructed.
- Repair counts use distinct saved analysis IDs, including original totals and
  repaired-item counts. Unknown repair metadata stays unknown.
- Daily costs retain confirmed charges and unresolved maxima separately.
  Experimental charges are shown separately; ordinary explainers remain in
  the daily target. Unresolved charges cannot pass. Confirmed overspending can
  fail during a partial window.
- Duplicate delivery counts use current confirmed send-attempt story claims
  within a half-open rolling 24 hours. Missing claims stay unverifiable. This
  proves exact displayed-content/URL/verified-repeat identities, not arbitrary
  semantic paraphrases. A material update deliberately claims its URL after
  delivery; a later update sharing only that URL remains ambiguous in the flat
  claim journal, rather than becoming a false duplicate or a silent pass.
- Ratings use the latest explicit vote per alert in the window, rather than
  counting repeated clicks. No ratings means unknown usefulness.
- Independent low-value review and owner-labelled quality stay separate gates.
  Model importance cannot grade its own predictions; the deferred 50-source
  review and fixed hard-case results must accompany this report.

The four rollback flags expose the plan's recorded daily completion, confirmed
two-day cost, qualifying-move recall and weekly usefulness failures. They request
operator review and never change configuration or restore a setup automatically.

## Validation and installation status

The initial price-audit fixture used a non-preset company and was corrected to a
preset missing-quote company without fetching data. The corrected price-related
run passes **105 tests**. The outcome/assessment/worker/48-hour/lane readiness
final run passes **57 tests**, covering grouped moves, publication failure, access,
immutability, gaps, unresolved charges, repeated ratings, rolling expiry,
overnight latency, calendars and read-only collection. Counts overlap.

The broad backend run passes **2,656 tests with 93 optional skips**. Its collected
report tests precede the final missing-ledger/material-update guards; the final
57 focused checks verify those guards and the separate experimental holds.
Syntax and whitespace checks pass; the protected user CSS hash remains exact.

067 and the worker change remain uninstalled. Read-only verification at
19:30 SGT finds schema **064**, all 64 applied checksums exact, and the app
started at 15:54:29 SGT. New task/live-routing/daily-report flags are unset;
lanes/new move delivery remain false. This observation corrects the previously
recorded schema-060 assumption; no restart is repeated or attributed to this
work. 065–067 remain unapplied. The schema smoke check deliberately used a
nonexistent account, to test missing-table/preview handling without representing
any actual account outcome. No actual ten-session pass is claimed.
