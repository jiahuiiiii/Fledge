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
| Owner agreement | Original **24/50 (48%)**; revised same-set **24/50 (48%)**, both below 40/50 |
| Fixed hard cases | Original **4/6 pass**; candidate **3/6 fail** against the unchanged 4/6 minimum |
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

## Approved paid comparison completed

After explicit owner approval, the existing ledger-backed runner completed
**56/56 new requests**, with **zero failures, repairs or automatic retries**.
Actual cost is **US$0.47429**, with **US$0 unresolved**, below the approved
US$2 cap. The earlier quality campaign cost remains US$0.445405; combined
quality-experiment cost is US$0.919695. The approval covers this completed run
only and does not authorize another test or retry.

All 56 saved raw answers revalidate for free and reproduce the scored results.
All source/context payloads and response schemas match the original campaign.
The execution runner read no owner labels; separate offline scoring afterward
used the original export. Private frozen inputs and output are in
`.local/live-tests/redesign-phase-5-20261018/rubric-v2-prepared/` and
`rubric-v2-run1/`. The latter retains raw requests/responses, ledger call IDs,
approval, development score, eight changed predictions and a free change review.

| Metric | Original | Revised candidate |
| --- | --- | --- |
| Exact relevance + tone | 24/50 (48%) | 24/50 (48%) |
| Relevance alone | 38/50 (76%) | 38/50 (76%) |
| Tone alone | 29/50 (58%) | 29/50 (58%) |
| News exact | 14/25 | 15/25 |
| Discussion exact | 10/25 | 9/25 |
| Fixed hard cases | 4/6 | 3/6 |

Eight of 50 predictions changed. Two gained exact owner agreement and two lost
it; four changed without matching the owner. A single run cannot separate prompt
effects from generation variability. It demonstrates no net improvement in
agreement and does not support activation.

The free review finds a useful abstention on unnamed comparison claims, but the
explicit product question still receives unclear tone. Some short replies become
overly cautious; the sarcasm hard case becomes literal positive and loses its
reference match. Agreement gained on a quotation-plus-reply example is not proof
of a better speaker interpretation. The future-price and valuation-question
examples also expose reference/rubric boundaries that deserve adjudication;
neither owner labels nor fixed hard-case references are silently corrected.

Do not continue paid prompt tweaking automatically or ask the owner to redo all
50 labels. First stabilize the disputed boundaries using a small separate review
of the already identified examples. Preserve both runs as failures. No further
prompt revision or model test is performed as part of this completed attempt.

Results are **same-set development agreement**, not new blind acceptance.
Teaching/development cases are exposed and assistant-authored; they cannot
replace independent owner labels. A release claim needs a stable rubric and
a separately held-out owner review. None is fabricated or prefilled here.

Incremental actual cost **US$0.47429**. The original owner export, predictions, frozen
blind page and protected CSS remain hash-identical. No real app/DB restart,
source refresh, saved-research/preference change, new Telegram delivery or
activation occurs. The candidate needs a later deliberate deployment and explicit
quality gates before use. Phase 5 and the redesign remain unfinished.
