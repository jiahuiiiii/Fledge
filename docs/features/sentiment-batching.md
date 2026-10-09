# Sentiment batching

Implemented after the [8 October comparison](../testing/sentiment-batching.md).
The app decides request size in code; no additional model classifies the task.
The selected sample remains bounded to eight news and eight social texts by the
existing selection policy. This change does not increase source coverage.

## How requests are divided

The planner uses at most **eight complete sources** and **48,000 serialized UTF-8
request bytes** per batch. The size includes instructions, response schema, source
passages, saved parents and news comparison context. This is a conservative
engineering starting point, not an exact token estimate or a guarantee of model
completion. Each request retains the existing GPT-5.4 medium/9,000-output profile.

Sources stay in their original order with original labels. A child stays with its
own saved parent. All selected news outside a batch remains comparison-only
context, alongside the original comparison reports. Parents and comparison-only
reports are not extra sentiment votes. An indivisible source plus this context
that exceeds the bound is rejected before any batch is sent; it is not silently
truncated. Existing complete-input selection/omission disclosures still apply
before the planner.

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
There is no separate allowance and no new model provider or pricing profile.

A per-company session lock serializes manual and scheduled sentiment generation
without holding a transaction over external calls. Source access is rechecked
between batches and before saving. A stopped/expired watch or superseded loading
worker is checked before subsequent dispatch. The loading record stores completed
and total counts, source counts per batch and failure feedback; it stores no raw
source passages in that progress field.

The existing saved reading remains visible while work is in progress. The progress
strip and sentiment panel report completed batches. A failed run retains its
progress after reload. A combined reading is saved only after every batch and the
full merged result pass validation. Counts and news groups are computed once over
the whole sample, never by averaging batch percentages. A cross-batch inconsistency
still blocks publication; valid individual outputs alone are insufficient.

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

One live repeat of the formerly failing four-source fictional citation packet
passed validation, costing US$0.04323. This establishes format compatibility for
that response, not general sentiment accuracy. Larger full-request output budgets,
parallel model dispatch and independent human accuracy evaluation remain untested.
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
