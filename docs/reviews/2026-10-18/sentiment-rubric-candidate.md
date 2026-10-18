# Smaller-task rubric candidate — 18 October 2026

The owner requested the next steps after discussing ambiguous labels. Candidate
`thesis-source-sentiment-tasks-2` clarifies neutral/unclear/mixed, explicit product
questions, unnamed comparison attribution, missing image/remark evidence,
reply-versus-topic stance and conditional entry-price wording. Five fictional
teaching snippets are in the AI instructions. Sixteen different authored
development cases stay outside those instructions and source payloads.
[Rubric](../../testing/sentiment-tone-rubric.md).

The new prompt is versioned. Under the existing reliability bridge, earlier
compatible task labels remain reusable with their original model, prompt and
call IDs. A disposable-database integration test verifies zero reread dispatches
and an unchanged historical result across the revision. Event instruction/schema
and source/context payloads are unchanged; the legacy live prompt is untouched.
No schema, settings or UI change is included.

## Verification

| Check | Result |
| --- | --- |
| Instruction bound | **Pass 3/3**: tone 5,101, event 4,350, duplicate 2,497 characters; each ≤6,000 |
| Authored development cases | **16/16** keep complete own-source text and supplied required parents; expected answers/rationales stay outside source input |
| Reference response/citation contracts | **16/16** accept authored reference shapes without repair and reject an invented citation; this does not measure model judgment |
| Related offline suites | **177 passed**, including 35 new checks |
| Prepared historical request projections | **56/56** preserve exact earlier source/context payloads and response schemas; all receive revised instructions |
| Original owner quality | **Failed: 24/50 (48%)**, unchanged; new candidate quality unmeasured |
| Fixed hard cases | Original **4/6 pass**; candidate not model-tested |
| Separate news-noise gate | **Failed: 2/18 (11.11%)**, unchanged |

Test command used the required locale and `.venv/bin/python -m pytest -q` with
`test_sentiment_rubric`, `test_sentiment_tasks`, `test_sentiment_task_runner`,
`test_sentiment_reliability`, `test_sentiment_basis`,
`test_sentiment_quality_validation`, `test_owner_quality_set`,
`test_reddit_thread_context` and `test_sentiment_batching` under `tests/`.
All tests used the isolated temporary database and invented provider output,
with no network. The initial focused run had eight fixture whitespace assertion
failures and 60 passes: passages separate sentences with newlines. The assertion
now joins the body passages as sentences; the final 177-test run passes. This
was a test assertion error, not evidence of missing source text.

## Prepared paid comparison, not executed

Private output:
`.local/live-tests/redesign-phase-5-20261018/rubric-v2-prepared/`.
The existing ledger-backed runner validates a new frozen 56-request plan: the
same 50 exposed sources and six fixed hard cases, with unchanged evidence and
schemas. It contains no owner answers. No paid execution or retry has occurred.

The proposed one-pass GPT-5.4 test is expected to cost **US$0.50–1.00**, with a
**US$2 cap** across settled cost and unresolved reservations. That estimate uses
the prior 56-case campaign (US$0.445405) plus extra instruction text; output length
can vary. The sum of per-request worst-case ledger reservations is US$12.4708825,
not expected expenditure. The runner checks the cap before each dispatch and may
stop early. It stops at the first failure, keeps raw answers/charges, performs
current source-access checks and never retries automatically. A completed earlier
attempt does not authorize this new one; fresh explicit approval is pending.

Results would be **same-set development agreement**, not new blind acceptance.
Teaching/development cases are exposed and assistant-authored; they cannot
replace independent owner labels. A release claim needs a stable rubric and
a separately held-out owner review. None is fabricated or prefilled here.

Incremental actual cost **US$0**. The original owner export, predictions, frozen
blind page and protected CSS remain hash-identical. No real app/DB restart,
source refresh, saved-research/preference change, new Telegram delivery or
activation occurs. The candidate needs a later deliberate deployment and explicit
quality gates before use. Phase 5 and the redesign remain unfinished.
