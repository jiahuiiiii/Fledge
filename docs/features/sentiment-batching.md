# Sentiment batching

Implemented after the [8 October comparison](../testing/sentiment-batching.md).
The app decides request size in code; no additional model classifies the task.
**9 October correction:** the owner clarified that batching must cover every
eligible saved source. Sentiment v20 / `sentiment-whole-source-batches-2` removes
the eight-news/eight-social and 16,000-byte per-channel selection ceilings.
Eight is now a per-request limit only. Date windows, access controls, acquisition
and the original cumulative model allowance remain in force.

The complete locally available candidate pool is considered. Exact duplicate text
within a source type is classified once; incomplete passages and thread-discovered
replies without required saved context are excluded with separate counts. Distinct
replies from one thread are all included. Every eligible text receives company
relevance and sentiment labels, including unrelated and unclear results. A mention
is not a prior judgement of usefulness. The immutable packet records per-platform
candidate/eligible/excluded counts under `sentiment-all-eligible-1`.
Old limited readings retain their exact inputs and results.

The later [NVIDIA wording correction](../reviews/2026-10-09/sentiment-own-wording.md)
excludes a comment when no complete body passage survives, even if a generic
comment title or saved parent is available. This happens before request planning,
with a separate platform exclusion count. A usable sentence beside omitted
fragments is kept. Genuine news headlines and authored top-level post titles
remain eligible. Original source records and the conservative ellipsis rule are
unchanged; source previews explain the exclusions without an AI request.

## How requests are divided

The planner uses at most **eight complete sources** and **48,000 serialized UTF-8
request bytes** per batch. The size includes instructions, response schema, source
passages, saved parents and news comparison context. This is a conservative
engineering starting point, not an exact token estimate or a guarantee of model
completion. Since the owner's 9 October effort/output authorization, each request
uses the same pinned **GPT-5.4** model with **low reasoning effort** and a
**12,000-token total response ceiling**, under sentiment v22 and
`sentiment-whole-source-batches-4`. The first v21 low-effort full-plan trial exposed
unrelated coverage links; v22 explicitly requires relevance before linking reports.
The validator still rejects those links. The previous medium/9,000 profile remains
available for exact historical settlement. The larger ceiling permits more output;
it does not force the model to consume it. Reasoning and visible output share it.

Sources stay in their original order with original labels. A child keeps its
exact saved parent. Every eligible parent is pinned before planning; each batch
respects the four-parent/8,000-byte total and 3,000-byte individual parent bounds by
splitting requests. Later parents are not dropped to fit the whole corpus.

Comparison context is separately bounded to at most 16 other news reports per
batch, ranked by deterministic wording overlap and date. News links may reference
only an earlier report. Comparison context is reduced first to fit the request;
every original still receives its own classification batch. Grouping is not an
exhaustive all-pairs comparison. Parents/comparison context are not extra votes.
An indivisible oversized original/context blocks the plan before any dispatch;
no original is silently removed to make the plan fit.

Sentiment v19 constrains each news reporting citation to that source's passage
IDs, closing the quotation-string failure exposed by the experiment. The runtime
validator still checks evidence, author/context boundaries and reporting contracts.

## Saved work and recovery

Every batch uses a deterministic request identity and the original durable model
ledger. Completed, valid responses can be reused across a later refresh or process
restart **when their exact request inputs are unchanged**. Sources refreshed in
between may change those inputs and require a new analysis; this is not a frozen
sample resume button. Saved output and failed attempts are never overwritten.

Scheduled watches never retry a settled invalid batch. An explicit **Refresh &
analyse** can retry a previously settled invalid request once with a separate
attempt identity. A failed new request is not retried within that same action.
Unknown/interrupted charges are never retried, even when a maximum hold has been
separately accounted. They retain the original ledger's review/continuation rules.
There is no separate allowance or new model provider. The low/12,000 setting has
a new immutable pricing-profile version with the same standard token rates;
historical request profiles and charges are not rewritten.
The complete plan's maximum new allowance is checked before new dispatch, excluding
valid cached requests. Insufficient budget blocks the full reading with an explicit
explanation and no substituted smaller sample. Per-call atomic reservations still
enforce the original cap when other work runs.

A per-company session lock serializes manual and scheduled sentiment generation
without holding a transaction over external calls. Source access is rechecked
between batches and before saving. A stopped/expired watch or superseded loading
worker is checked before subsequent dispatch. The loading record stores completed
and total counts, source counts per batch and failure feedback; it stores no raw
source passages in that progress field.

Output-limit failures are reported as unfinished responses, separately from
malformed output or evidence-check failures. Feedback includes completed work,
later batches not sent in that run, the settled unsuccessful call's charge and
the absence of a published combined reading or automatic retry. Unknown charges
retain billing-review feedback. The old generic blocked loading message can be
explained from the final matching company response within that step's time
window on read; the stored loading journal and model attempt remain immutable.
The earlier feedback-only correction changed no request, model profile, batch size
or retry policy. The later owner-authorized low/12,000 setting is separate from that
correction; the actual 9 October medium/9,000 failures remain failures. Old error
messages use their stored request's limit, rather than the current setting.

The existing saved reading remains visible while work is in progress. The progress
strip and sentiment panel report completed batches. A failed run retains its
progress after reload. A combined reading is saved only after every batch and the
full merged result pass validation. Counts and news groups are computed once over
the whole sample, never by averaging batch percentages. A cross-batch inconsistency
still blocks publication; valid individual outputs alone are insufficient.
The merged validator has no sixteen-item ceiling; request schemas still require
exactly the sources in each batch. Progress reports the whole eligible count.
Active watch workers renew their existing lease at batch progress boundaries only
while the matching claim is enabled and unexpired. Expired, stopped or replaced
claims cannot revive. Journal headers remain immutable; running status uses the
current claim lease. Watch settings/schedules are unchanged.

The redesigned **Source coverage** panel shows candidates, analysed, relevant,
unrelated and unclear counts, per-platform coverage, exclusions and batch totals.
Old readings explicitly say “Earlier limited reading”. Relevance filters and
12-item pages help browse the complete result; pagination does not limit analysis.
Current raw previews expose the full eligible pool without a model request.

The separate optional discussion-theme synthesis retains its original request
ceiling, output budget and two-stage paid contract. This change does not establish
scalable theme synthesis, broad source coverage or new semantic accuracy.

The final analysis retains every call ID in its immutable packet for audit, while
its existing `call_id` references the last contributing call. Repeated reads and
unchanged completed analyses make no model request. First use of the batching
policy establishes a quiet company-watch baseline; historical deterministic
rendering-policy changes retain their prior alert behavior. No watch is enrolled
or notification recipient changed by installing this feature.

## Verification and limitations

The implementation uses isolated database/model tests for partition completeness,
context preservation, byte bounds, citation schema, partial recovery, one explicit
retry, ambiguous-charge suppression, access withdrawal, global validation,
concurrent generation, stale progress workers, quiet method transition and watch
cancellation. Browser checks exercise progress, failure retention/reload and
320/390/1440px layouts, alongside the existing sentiment/alert journey.

The initial broad run passed 1,358 checks with 59 optional-corpus skips and exposed
one overly broad alert-baseline suppression. That was narrowed to the batching
policy; the final overlapping suites passed 112 checks/one optional skip and 58
checks, including an added watch-cancellation case. Across these runs, 1,360
distinct backend cases have passing results; these are not additive
suite totals. Frontend 27 checks/build pass. The first focused run's old
withdrawal assertion was updated to verify the stronger behavior: no combined
analysis is saved if its source is withdrawn during a request. Original failed
logs are retained.

One earlier live repeat of the formerly failing four-source fictional citation packet
passed validation, costing US$0.04323. This establishes format compatibility for
that response, not general sentiment accuracy. The later low-effort/larger-output
trial is documented in the [9 October review](../reviews/2026-10-09/sentiment-low-reasoning.md).
Parallel model dispatch and independent human accuracy evaluation remain untested.
The earlier experiment's semantic disagreements and provider-access limits remain.

## Actual AVGO web run — 8 October, final review 9 October 2026

One explicit **Refresh & analyse** in the owner's running app completed at
23:57:58 SGT. It selected eight news texts, four Reddit posts/replies and four
Hacker News comments. Both eight-source batches settled successfully, passed
individual and combined validation, and saved one complete analysis. Progress
recorded zero, one and two completed batches; the saved reading remained visible
after a browser reload with no additional model call. News, Reddit and Hacker News
results were inspected separately. Browser console inspection found no errors.

The model stage took about 117 seconds; collection and analysis together took
about 285 seconds. Reddit collection took about 167 seconds under the existing
source pacing and returned 26 matched posts plus six replies. The UI had 38 saved
Reddit candidates and nine HN candidates; these available/source-refresh counts
are distinct from the four-plus-four social texts actually analysed. The run
retained Alpha Vantage's prior cooldown, disabled X, and one unavailable publisher
feed as coverage gaps. The overall load therefore says **Research updated with
gaps**, while its sentiment step says **Analysis saved**.

The AVGO requests cost US$0.174; with the separate citation check this phase used
US$0.21723 over three settled requests. Cumulative confirmed cost is
US$20.0286415, with US$0.9156025 historical maximum holds and US$9.055756 available
from the original US$30 allowance, 359 calls and no new unresolved charge.

The audit retains 57 of 100 exact table fingerprints. Expected source, loading,
model and analysis records changed; the owner's concurrent addition of FN also
created company/source/fundamental records. Existing private research, watch,
notification and budget-configuration tables remain exact. No watch was enabled
or Telegram message dispatched by this task. Schema stays at 41. Preserve the
initial audit diagnostic that compared UUID objects with serialized strings; the
corrected comparison confirms unchanged watch settings.

This is a successful real-source workflow and persistence test, not an independent
semantic-accuracy test. Historical method failures and the experiment's disagreement
remain evidence. Partial recovery/retry behavior was verified with controlled
responses, not induced failures in the owner's live request.

Evidence: `.local/live-tests/sentiment-batching-app-20261008/`.
Backup: `.local/backups/sentiment-batching-app-20261008/before.dump`.
