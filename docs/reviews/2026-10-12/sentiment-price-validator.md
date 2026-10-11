# Unsupported optional price extraction — 12 October 2026

The owner reported NVIDIA's batch 22 of 54 stopping after 21 completed batches.
Saved call `371c0d79-18d9-4551-87a8-37670000ca1e` finished at 00:56:59 SGT with
2,088 output tokens against its 12,000-token ceiling and cost US$0.057325.
It extracted `220s` from item_443's original wording, “nvidia in its 220s.”
`sentiment_guards.number` correctly rejected a non-dollar amount, but that
optional-field failure incorrectly discarded the complete batch. The owner's
follow-up explicitly requested a validator correction.

## Correction

`price_details` now separately returns supported comparisons and ignored
source-matching non-dollar extractions. It validates the cited own passage,
amount substring and direction wording before deciding whether optional amount
syntax is supported. Ignored syntax produces no numeric value or comparison.
`apply` removes it from derived `price_claims`, records a bounded original token
and fixed reason in `guard.ignored_price_claims`, and conservatively downgrades
an affected relevant non-unclear attitude. Already unclear attitudes remain
unchanged. The comment and its count remain; all other evidence checks still run.

Invented amounts/citations/direction and out-of-range exact dollars still fail.
No catch-all validation exception is suppressed. The parser, model request,
schema, prompt, request identities, budget, retry policy, source/watch controls and
published historical readings are unchanged. This preserves reuse of paid
unpublished responses without a new request. Historical failed loading messages
remain an accurate journal of the original run.

## Verification and installation

259 focused offline tests pass across sentiment guards, batching, source/context
evidence, failure feedback, low reasoning, all-source selection, quick relevance,
reporting evidence and the original ledger. New cases cover shorthand, absent
currency, unsupported ranges/units, mixed valid/ignored claims, conservative
labels, fabricated evidence and retained exact-dollar range errors. A disposable
database test recreates a rejection under the previous validator and proves the
corrected validator reuses both paid batches without a retry or ledger change.

The actual saved NVIDIA replay validates batches 1–22 without dispatch. All 21
previously valid rendered results remain exact; batch 22 now passes with its
other seven items exact, original own/parent citations retained, and item_443
still unclear with no price value. Stored requests and complete call records
remain exact. This is software replay, not independent semantic validation.
The initial investigation recovered 691 eligible sources, 277 quick skips and
414 full-reading sources over 54 batches. Later source aging changed the current
sample, so a future refresh is not promised to reuse every request.

Only this validator differed from the latest installed Microsoft-recovery
runtime. A backed-up app-only restart installed it: PID 20247 → 29025, worker
advisory lock confirmed. Admission locks and idle/lease checks protected the
restart. All 116 table fingerprints, schema 49, private settings, complete model
ledger and frontend index `4e9ff62d` remained exact across installation.
PostgreSQL was left running. No AI dispatch, retry, source refresh, watch-setting
change or combined NVIDIA publication was initiated by this task.

Evidence: `.local/live-tests/sentiment-price-validator-20261012/`; prior
investigation: `.local/live-tests/batch22-investigation-20261012/`; recoverable
backup: `.local/backups/sentiment-price-validator-20261012/`. Preserve the first
test's already-unclear-label assertion failure and corrected rerun, diagnostic
missing wire-only parent metadata, initial read-only query-column correction,
and documentation patch-context diagnostics. Syntax and diff checks pass.
