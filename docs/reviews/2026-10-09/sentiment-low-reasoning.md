# Sentiment effort and response tuning — 9 October 2026

The owner explicitly authorized lower reasoning effort for classification while
retaining the smart sentiment model, and allowed increasing the 9,000-token
ceiling. This is a separate request change after the earlier
[feedback-only correction](sentiment-output-limit-feedback.md).

The initial candidate kept `gpt-5.4-2026-03-05`, changing only reasoning from medium to
low and the total output ceiling from 9,000 to 12,000. Source instructions, strict
JSON schema, evidence/relevance gates, saved parents, comparison context, eight
originals/48,000-byte request bounds and serial dispatch remained. Prompt v21 and
`sentiment-whole-source-batches-3` separate the new request/cache identity and
quiet watch baseline from historical methods. The exact new profile is restricted
to `source_sentiment`; unrelated AI routes keep their settings. The final v22 /
`sentiment-whole-source-batches-4` also clarifies the existing relevance requirement
for coverage links after the full-plan failure below; no validator is weakened.

[Official GPT-5.4 documentation](https://developers.openai.com/api/docs/models/gpt-5.4)
supports low effort and confirms the existing standard token prices.
[Reasoning guidance](https://developers.openai.com/api/docs/guides/reasoning)
explains that reasoning and visible output share the generated-token ceiling.
The larger ceiling permits additional output; it does not force consumption or
prove general accuracy. The old medium/9,000 price version, charges, responses,
held maxima and original cumulative US$30 allowance remain unchanged.

## Exact failed-batch test

The original AVGO packet was reconstructed using its saved 12:07 SGT cutoff. Its
second request exactly matched the immutable request for failed call
`5b203eb4-dfa4-4bb5-ab05-e13fce95dcbe`. The tuned request differs only in the two
authorized settings. It uses eight news originals and the same seven comparison
reports; no source was fetched or shortened for the test.

New call `a35e9e52-7cfe-4edc-b7ac-7e82d5148961` completed in 25.48 seconds and
passed strict format, source, citation and coverage checks for all eight originals.
It used 10,461 input tokens and 2,290 total output tokens, including 1,192 reasoning
tokens; actual cost was US$0.0605025. The old failed call used 9,000 output,
including 8,086 reasoning tokens, and cost US$0.1611525. This is an observed
matched-source/settings comparison, not a guarantee of a fixed token reduction.

The saved passages were inspected alongside their classifications. Financing
reports retained neutral descriptive labels; resilience commentary had a positive
evaluation; the valuation passage retained its qualifications. Exact quotation
checks do not by themselves establish semantic correctness. These selected checks
are developer inspection, not an independent accuracy evaluation. Historical
experiment disagreements remain evidence.

## First full-plan failure and coverage correction

The frozen pool contains 66 news candidates, with one exact duplicate excluded:
65 unique news originals. There are 50 Reddit candidates, with one exact duplicate
excluded, and six HN originals; no X text is saved. All 120 eligible originals fit
15 eight-source requests. Relevance is assessed by the model after eligibility;
being a feed candidate does not establish usefulness to Broadcom.

The first v21 full run, journal `0df82990-033f-4e10-9217-e47821ee9af2`, reused the
successful second-batch test and completed batches one through four. Batch five
returned complete JSON, but the unchanged validator rejected links originating
from sources the same response classified unrelated: “Unrelated news cannot form
a target-company coverage group.” Four completed requests and the failed attempt
remain saved. Ten later batches were not sent; no combined analysis was published.
That unsuccessful request cost US$0.0512025. This failure is preserved in
`batch5-call.json`, `batch5-validation-error.txt`, `full-error.json`, the original
run journal and the full-run log. It is distinct from output-limit exhaustion.

The existing coverage instruction did not explicitly tell the model that its
relevance labels restrict coverage linking. Prompt v22 now states that the linked
selected item and any selected reference must be relevant; comparison context
must concern the same target-company development. Matching stories about another
company still receive classifications but no target-company link. The strict
validator and whole-result publication condition remain unchanged.

Explicit corrected batch-five test `dda39cad-993e-4d59-8e13-d2140d6f0047` retained
the same eight originals and passed in 13.43 seconds. It classified seven unrelated
and one unclear, returned zero coverage links, and used 1,084 output/474 reasoning
tokens, costing US$0.0416925. Its full-plan conservative maximum US$4.7601675 fit
US$5.442573 available. This is a new changed-instruction test, not a retry of an
ambiguous charge. The failed v21 response is not edited or accepted.

The corrected method has new prompt/cache identities. Prior v21 successes remain
immutable but are not falsely reused as v22 responses. The successful v22 test is
reused by the corrected full reading. Its remaining 14 requests have a checked
maximum US$4.441045 against US$5.4008805 available.

## Verification and installation

Guarded focused suites passed 131 cases, covering the new exact profile, full
maximum reservation, usage settlement, historical pricing preservation, rejection
of unpriced settings/other formats, whole-corpus batching, saved failures and
loading. Related integration suites passed 98 cases for sentiment/evidence,
context, news grouping, watch history and private evidence budget behavior. These
are suite results, not additive claims of distinct cases. Both use disposable
databases with external requests blocked; an existing Starlette deprecation warning
remains.

The guarded browser journey passed sentiment, watch/history, exact sources,
full-coverage pages and preserved historical failure feedback at 320/390/1440px.
Inspected desktop failure and phone coverage screenshots use authored fixtures,
not the owner's actual AVGO result. No frontend change or build was required.

Idle app-only restart installed the verified four backend files, PID 68086 to
4407, leaving PostgreSQL running. Readiness/session and the actual legacy loading
API passed; the old failure still correctly reports its stored 9,000-token ceiling.
All 114 table fingerprints were exact across restart, schema 47, environment and
local-pitch mode unchanged. Served frontend index retained SHA-256
`1a8a243dbbf92c1715690334913102e6b7d1c1888156b444c20e6ade58312627`.

Initial accounting was US$23.3784015 confirmed plus US$0.9156025 historic holds,
US$5.705996 available, 397 calls/no blockers. One ordinary app call settled during
preparation. After the probe and before installation: US$23.4460755 confirmed,
US$0.9156025 holds, US$5.638322 available, 399 calls/no blockers. Installation
itself made no paid request and those values were exact across restart.

Preserve the harmless guessed experiment/script and backup/documentation paths,
missing migration glob, unsupported Markdown documentation fetches and all tool
diagnostics. No offline candidate test failure occurred before the first
installation. The paid v21 grouping failure and two documentation-patch context
mistakes remain separate evidence.

After the instruction correction, overlapping guarded suites passed 161 cases,
including four controls rejecting a link when either selected report has unrelated
or unclear relevance while allowing the classifications to remain unlinked.
Eight final legacy feedback checks pass, covering both v20/9,000-medium and
v21/12,000-low history after the new prompt version. No source permission changed.

The second idle app-only restart installed the paid-tested v22 instruction,
PID 4407 to 17776. Again, all 114 table fingerprints and schema 47 were exact,
database and environment unchanged, with the actual blocked batch-five feedback
preserved. Another chat installed frontend index `2eb63e79` between this task's
restarts; this task changed no frontend files/assets. Each restart preserved the
index present immediately before it. Budget was US$23.683517 confirmed plus
US$0.9156025 historical holds, US$5.4008805 available, 404 calls/no blockers,
unchanged across the second restart.

## Completed full saved sample

The corrected run `843bf1c1-3929-48e7-81f3-7050bfa81e87` finished at 13:01:12 SGT
in 272.98 seconds. All fifteen requests and the full merged result passed the
unchanged validators. One complete immutable analysis,
`f159bbba-bbc5-44fd-9c44-27d73af55c39`, is saved with every contributing call ID.
The latest loading journal is ready/inactive and reports “Analysis saved · 120
sources in 15 batches.” This is the full original 12:07 SGT sample, not a new
source collection. The task invoked no watch publication or Telegram dispatch.

The 65 unique news originals have 30 relevant, 33 unrelated and two unclear
company-relevance labels. Their relevant coverage forms 20 counted news groups;
all original item labels and quotations remain available. Reddit has 49 analysed,
44 relevant; HN has six analysed, all six relevant. Across the 120 originals:
80 relevant, 38 unrelated and two unclear. Company relevance and sentiment
uncertainty are distinct: six relevant Reddit texts have unclear sentiment. No
classification is silently removed because it is unrelated or unclear.

The fifteen contributing calls cost US$0.70617, including the reused v22 test.
They used 21,341 total output tokens, including 12,621 reasoning tokens; no single
response used more than 2,741 output or 1,659 reasoning tokens. This is one
successful real-source run, not proof every future batch will complete or every
interpretation is correct. The fourteen selected passage/label inspections in
`inspection-sample.json` include company-list irrelevance, vague-company teasers,
attributed evaluations, concerns about financing, qualification of long-term
praise and a quoted release without the poster's endorsement. The mixed label
on question `item_78` is borderline: positive selection/no regret and requests
for reassurance do not unambiguously establish opposing current attitudes.
Retain it as model interpretation and an accuracy-review candidate; no response
or label was edited to manufacture an accuracy result.

All ten historical v20/v21 call rows measured before the corrected run remained
exact, including the new failed grouping response. Both the original output-limit
journal and the v21 blocked journal stayed exact. Actual workspace/loading GETs
serve the new complete reading, with 120 source IDs matching the frozen pool,
current method/permission visibility, ready 15/15 progress and identical results
on repeated reads. The ledger remained exact across those reads: zero new calls.

The current raw pool now has 69 news candidates/68 eligible: three newer originals
were added after the frozen 12:07 sample. All 120 saved originals are retained,
and there are no parent/context differences. The current-input status correctly
says changed and shows the three additions; the completed result is not falsely
dated as a reading of those new texts. No additional source collection or model
request was made to chase the moving current pool.

This task made 20 settled model requests, costing **US$0.9624215** total, including
the unsuccessful v21 grouping attempt and preliminary successes that cannot be
reused under v22. The one ordinary concurrent app call cost US$0.0071715 and is
separate. Final ledger: US$24.3479945 confirmed, US$0.9156025 historical holds,
US$4.736403 available from the original US$30, 418 calls, zero running/new charge
review blockers. No allowance, held maximum, cooldown or provider denial was reset.
Broader forecast access and independent interpretation/participant validation
remain separate from this completed source-sample workflow.

Evidence: `.local/live-tests/sentiment-low-reasoning-20261009/`.
Backup: `.local/backups/sentiment-low-reasoning-20261009/`.
