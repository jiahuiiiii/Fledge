# Sentiment batching experiment — 8 October 2026

**Implementation follow-up, 9 October:** the owner subsequently approved bounded
batching, citation constraints and saved progress. See [the implementation and
actual AVGO web verification](../features/sentiment-batching.md). Statements below
about unchanged production describe this original experiment's checkpoint.

This is an evaluation of source batching, not a production change or the OpenAI
Batch API. The owner asked whether smaller requests complete more reliably and
produce the same, better or worse interpretations. App sentiment v18, its prompt,
pricing profile, schema, watches and publication behaviour remain unchanged.

## Findings

**Batching helped the large Broadcom request finish, but is not an equivalent
transformation and did not establish a general accuracy improvement.** Eight
sources per request is the stronger candidate for a further implementation trial:
on this real sixteen-source sample it completed twice, with lower time and cost
than four-source batches. A citation-format weakness must also be addressed before
treating batching as a reliable production fix. Production remains unchanged.

All 32 planned dispatches were attempted. There were 16 whole-sample trials:
11 produced usable, fully validated results; one exhausted its output allowance;
one timed out locally with unknown provider outcome; and three completed their
responses but failed citation validation. The following denominators count whole
samples, not individual API calls.

| Cohort / strategy | Usable trials | Serial duration per trial | Confirmed charge per trial |
| --- | ---: | ---: | ---: |
| Broadcom, full 16 | 0/2 | 131s for the token-cap failure; other call timed out | $0.138928 for the cap failure; other charge unknown |
| Broadcom, batches of 4 | 2/2 | 193–290s | $0.224462–$0.297548 |
| Broadcom, batches of 8 | 2/2 | 108–186s | $0.176348–$0.203819 |
| NVIDIA, full 8 | 2/2 | 52–72s | $0.080253–$0.101283 |
| NVIDIA, batches of 4 | 2/2 | 59–75s | $0.090658–$0.102328 |
| Authored controls, full 12 | 2/2 | 58–66s | $0.084423–$0.091458 |
| Authored controls, batches of 4 | 1/2 | 91–92s | $0.120451–$0.138685 |
| Authored controls, batches of 8 then 4 | 0/2 | 75–85s | $0.103664–$0.118133 |

Charges and times include rejected outputs. The local timeout is not evidence that
the provider exhausted its token allowance or never completed; no complete result
was received. It was not retried. Totals across different cohorts must not be read
as a controlled overall success-rate ranking: NVIDIA has no separate batch-eight
arm, and the samples differ substantially.

### Do the interpretations match?

- **Broadcom:** four- versus eight-source strategies agreed on 14/16 tone labels
  in both repeats. The two differences were neutral versus unclear; both fit the
  predeclared acceptable sets. Every valid run matched 11/11 strict and 5/5
  multiple-acceptable tone criteria. Both batch sizes repeated all 16 tone labels,
  but relevance, reported-event versus rumour classification and news relationships
  were not identical. Four-source runs counted four news groups; eight-source runs
  counted three. These grouping differences have not been independently adjudicated.
  There is no complete new full-request output to compare against these batches.
- **NVIDIA:** full versus four-source requests agreed on 7/8 tones in each paired
  repeat. All runs matched the three strict criteria. Full requests matched 3/5
  then 5/5 multiple-acceptable criteria; batches matched 4/5 both times. Batches
  repeated 8/8 tones while full requests repeated 6/8, but the stable batch label
  for one generic market-cap discussion still missed its frozen acceptable set.
  Greater repeatability is therefore not proof of greater correctness.
- **Authored controls:** valid full requests matched 10/12 tones, 15/17 additional
  fields and all three news relationships in both repeats. The one valid
  four-source trial matched 11/12 tones, 16/17 fields and all three relationships.
  It avoided assigning unstated favourable impact to an unconfirmed contract.
  That improvement did not consistently repeat.

A separate **post-hoc raw-output diagnostic** includes the three structurally
invalid control trials instead of silently dropping them from the quality
discussion. Their tone labels each matched 10/12 frozen criteria and agreed with
the corresponding full request on 12/12 tones. Additional field matches were
16/17 and 15/17 for the two batch-eight trials, and 15/17 for batch-four repeat two.
These raw labels are diagnostic observations only: their results are still
unusable, their references were not repaired, and no product summaries were
computed from them. See `raw-control-diagnostics.json` and its retained script.

### Why three completed trials were rejected

For certain news items, the model placed exact quotation text into
`reporting.passages`, where the app requires passage IDs such as `p1`. The existing
validator correctly rejected those responses. The quotations themselves matched
the source text; the problem was the response contract, not invented quotations.

The final four-source control request has the **identical request hash** in both
the four- and eight-source strategies. It passed once and failed three times.
Batch-four repeat two also returned this format error for two news items in an
earlier batch. This is evidence of a shared response-schema weakness and variable
model output, not proof that an eight-source request itself causes the failure.
The current reporting-evidence schema accepts generic strings; ordinary source
passage citations already have tighter source-specific choices.

Before a production trial, constrain reporting passage IDs to each source's
allowed IDs, retain the final validator, and rerun these exact failure cases.
Then use bounded batches for larger samples, keep parents and all news comparison
context, and combine results only after every required batch passes. Progress can
show completed batches without publishing a partial sentiment total. Any recovery
must reuse completed work and preserve the existing ambiguous-charge rules.

Changes to news grouping/relevance may affect downstream alerts, even where tone
labels match. Production integration therefore also needs method/cache identity,
quiet watch-baseline migration and alert-regression checks. None is implemented or
validated by this experiment. Four-source batches are not justified as a universal
default by these results.

## Design

The frozen protocol and raw evidence are in
`.local/live-tests/sentiment-batching-20261008/`. The recovery backup is
`.local/backups/phase85-sentiment-batching/before.dump`.

- **Broadcom:** the exact failed request from 17:06 SGT, with eight news and eight
  social sources, seven older news references and three saved immediate parents.
- **NVIDIA:** the exact earlier successful eight-source Reddit request.
- **Authored controls:** twelve clearly fictional items testing an unconfirmed
  contract, denial, repeated financing report, subsequent loss, changed personal
  opinion, quoted praise, a parent/child distinction, conflicting views and ambiguity.

Both actual packets reproduce their historical request bodies exactly. Source
texts are observations of retrieved wording, not verification of their financial
claims. Historical calls are excluded from the primary experimental denominators.

Each applicable strategy is run twice with new, predeclared request identities:
one full request, batches of four and batches of eight. An eight-item batch would
duplicate NVIDIA's full arm, so that redundant arm is omitted. There are 16
whole-sample trials comprising 32 API requests. Second-replicate arm order is
reversed. The model remains `gpt-5.4-2026-03-05`, medium reasoning, standard tier,
9,000 maximum output tokens per request. No prompt or model tuning is performed
after seeing the results. The experiment is bounded to seven additional dollars
inside the owner's original cumulative thirty-dollar ledger.

Batching retains whole sources, their order, original labels and their own saved
parents. Selected news outside a batch remains comparison-only context, along
with the older references. This prevents silently losing cross-batch news
relationships. Parents are not additional votes. Each response must pass the
existing validator; merged output is validated again against the full packet and
counted/grouped globally. Partial outputs are not published or averaged.

## What the measurements mean

Completion requires a complete, valid result for the entire source sample. A
successful HTTP response or individually completed batches alone do not qualify.
The comparison separately records tone, relevance, basis, statement type, event
impact, news links and the actual global summaries.

Tone criteria were frozen before new outputs. Broadcom has 11 strict and five
multiple-acceptable cases; NVIDIA has three strict and five multiple-acceptable
cases. The controls have 12 strict tone expectations, 17 additional field checks
and three news-link checks. These are one developer-agent's criteria, not
independent human labels or general accuracy measurements. Earlier evaluations
were known. Neutral versus unclear can be debatable, particularly when an author
explicitly has no opinion; the original criterion remains unchanged and such
disagreement must not automatically be called a factual error.

The request-size comparison intentionally permits more aggregate output capacity
when split. It does not hold total computation fixed. Requests are serial;
parallel latency is unmeasured. Actual charges include prompt-cache savings;
`scores.json` also reports costs recalculated without those savings. Cache state
and variable provider time limit conclusions from two repeats.

## Mechanism and remaining scope

OpenAI counts reasoning within the output allowance and can return a billed
incomplete response when it is exhausted. [Official reasoning documentation](https://developers.openai.com/api/docs/guides/reasoning).
This explains the original failure; it does not establish that batching is always
preferable to increasing the full-request allowance. A larger full-request limit
is not tested here.

This experiment assesses per-source sentiment, reporting evidence and news
grouping. It does not test cross-source theme synthesis, prospective alert
accuracy, Telegram delivery, investment usefulness or participant comprehension.
Experimental outputs never enter saved product analyses, watch baselines or the
notification outbox. No source refresh or new source access is performed.

The reusable evaluation-only helpers and offline checks are in
[`experiments/sentiment_batching`](../../experiments/sentiment_batching/README.md).

## Verification, preservation and spending

The 12 focused offline checks pass. They cover intact source/parent partitions,
cross-batch news context, unchanged model instructions/profile, rejection of
missing/duplicate results, final global validation and comparison semantics.
All 32 frozen request hashes still match after the run, both historical calls are
unchanged, and the production sentiment file's hash is unchanged from the start.
No production code, dependency, schema or UI was changed by this experiment, so a
full application or browser suite was not repeated.

The final read-only database comparison found **95 of 100 tables identical**.
Expected experiment changes were 32 appended model calls/dispatches and one owner
accounting decision. Two additional tables changed during the interval: Telegram
was connected/enabled and one test message was acknowledged at 23:16 SGT. The
experiment has no Telegram setup/dispatch path and performed neither action;
these are concurrent app activity, not an experiment result or delivery validation.
No claim is made that all notification state stayed identical. Research, sources,
analyses, watches, provider pacing and schema tables were unchanged. Preserve the
concurrent connection and test record.

The experiment cost **US$2.0724345 confirmed** over 31 settled calls, with one
additional **US$0.3131125 maximum hold** for the timed-out request. Dispatch stopped
at that ambiguity. The owner's explicit “just run bro, you only used 20 usd so
far” reply authorized retaining its whole maximum and finishing the nine remaining
planned requests inside the existing US$30 cap. Their approximate usage report
was not treated as a per-request charge receipt. The timeout remains unresolved;
its maximum is separately accounted and the call was never retried.

Final original-ledger checkpoint: **US$19.8114115 confirmed**, **US$0.9156025 total
historical/experiment maximum holds**, **US$9.272986 available**, 356 lifetime calls,
no running calls or unaccounted blocker. Initial failures, interrupted output,
original responses, frozen criteria and owner continuation are retained. This is
not a new allowance or evidence that sentiment/alerts are generally validated.
