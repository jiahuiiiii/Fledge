# Sentiment batching experiment

Evaluation only: nothing here is imported by the app. These helpers do not refresh
sources, publish analyses, change watches, or send alerts. The explicit live runner
uses the original installation's provider settings and cumulative ledger.

Read the [completed findings and limitations](../../docs/testing/sentiment-batching.md).
Batching helped the large real-source case finish; it did not establish equivalent
interpretations or universally better accuracy. The app is not switched to batching.

The 8 October 2026 experiment is retained at
`.local/live-tests/sentiment-batching-20261008/`. Its frozen protocol compares the
same GPT-5.4 snapshot, medium effort and 9,000-output-token profile using full
requests, four-source batches and eight-source batches, with two new replicates.
The eight-source NVIDIA cohort omits a redundant eight-source arm. Historical
calls are preserved as context, not counted as new replicate results.

Each batch retains whole sources, original labels and their own saved immediate
parents. All other selected news remains available as comparison-only evidence,
alongside historical references. Results merge only after complete per-batch
validation, then undergo the full original validator and global grouping/counts.
Never average per-batch sentiment percentages or count parents as sources.

The real Broadcom/NVIDIA packets exactly reproduce their original request bodies.
Twelve separate authored controls test attribution, changing views, ambiguity,
event impact and news relationships across batch boundaries. Criteria were frozen
before new responses. These are developer expectations, not independent human
labels or verified financial claims. Raw real-source captures stay outside Git.

Commands exercised from the project root:

```sh
.venv/bin/python -m unittest discover -s experiments/sentiment_batching -p 'test_*.py' -v
.venv/bin/python -m experiments.sentiment_batching.score --folder .local/live-tests/sentiment-batching-20261008
```

Paid dispatch requires an existing frozen protocol/packet/criteria set and explicit
`--live`. Never call it from a test. The dated run uses the owner's authorization;
the command is not a new spending allowance:

```sh
.venv/bin/python -u -m experiments.sentiment_batching.experiment --folder .local/live-tests/sentiment-batching-20261008 --live
```

Requests run serially. The seven-dollar incremental ceiling includes the next
request's conservative maximum, while the original thirty-dollar ledger remains
authoritative. Any unknown charge stops dispatch. Trial identities intentionally
distinguish the predeclared replicates; the app's normal cache identity is never
used or invalidated. Existing records and output artifacts are not overwritten.

One timed-out request stopped this run. Explicit owner continuation retained its
whole maximum in the original ledger and permitted the remaining planned calls.
Its trial is marked interrupted and is never retried on resume. Retaining a hold
does not reconcile its actual charge. Derived offline score reports may be
regenerated; original requests, responses, failures and metrics remain append-only.

Quality is reported separately from completion, exact label agreement, summary
agreement, event/coverage decisions, actual charges, token usage and serial wall
time. Batching permits a larger aggregate output allowance and repeats input;
this is not a fixed-total-compute comparison. Parallel latency is unmeasured.
