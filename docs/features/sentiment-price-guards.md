# Sentiment evidence checks and historical price context

The 9 October 2026 owner request follows a saved Reddit comment, “AVGO to $340”,
classified positive under sentiment v19 and v22. The original model request
contained no reference price and no saved parent. Its timestamp is a Reddit feed
update, not a verified original publication time. The original responses and
published readings remain unchanged.

## Current method

Sentiment v23 / `sentiment-whole-source-batches-5` / `sentiment-coverage-9` retains
GPT-5.4 low reasoning, the existing 12,000-token output profile, eight-source and
48,000-byte request bounds, serial execution, exact evidence/access gates,
whole-sample publication, existing paid-action/retry controls and cumulative US$30
allowance. No second AI checker, local-model vote, automatic reclassification,
source request, schema migration or extra allowance is introduced.

The strict social-item schema extracts at most three price claims: own passage ID,
exact dollar amount token, target/option strike/historical/other kind, and exact
direction wording or null. News returns an empty list. Amounts/direction extracts
must exist in the same original passage. Decimal parsing and arithmetic are code
operations. The model never receives the historical price capture.

## Price comparison boundaries

Preparation reads retained Yahoo daily captures for the same company, only if
current source entitlement permits them. A comparison requires a verified post
timestamp and a capture **already retrieved on or before that timestamp**. This
is deliberately stricter than reading an older date out of today's chart:
later-adjusted price vintages cannot silently replace prices available at the time.
The most recent compatible capture is pinned; captures are never stitched together.

The selected USD, New York, daily bar must be explicitly completed, no later than
the source/capture date, and at most seven calendar days old. Same-day provisional
bars, future captures/bars, wrong companies/currencies, unsupported ranges/units,
option strikes and ambiguous issuer attribution are unavailable. A Reddit
feed-update time cannot stand in for the original post time. Missing context
does not cause a fetch or a fallback to today's price.

For a supported directly attributed point target, code calculates
`(target − saved close) / saved close × 100`. The app shows the dated close,
above/below/equal relationship, arithmetic, capture timestamp and provider basis.
Dollar notation is interpreted in this supported US-equity/USD context; no
currency conversion is performed. Yahoo's original split-adjustment caveat remains:
there is no independent corporate-action reconciliation. This is saved-close
context, not an intraday quote, forecast, or the author's attitude.

The selected capture/status is recorded in the immutable packet and analysis
identity. It does not change the AI extraction request/cache identity. Access is
rechecked between batches, at save and at read; withdrawal of a consumed price
source withholds the derived reading rather than leaking through labels/history.
Unavailable price context does not make unrelated source text unavailable.

## Conservative label rules

`sentiment-evidence-guards-1` only downgrades to unclear; it never promotes an AI
label or makes an investment recommendation. The code catches:

- Bare company/ticker/number evidence and simple bare price targets, even if AI
  extraction misses the amount.
- Evidence consisting entirely of questions, without a separately selected stance.
- Supported simple price-only wording with missing direction, missing historical
  reference, inconsistent explicit direction versus the saved close, or an AI
  label conflicting with that explicit direction.

A matched explicit upward/downward price-only view retains its original label
only when the historical comparison is compatible. Other separately selected
praise/criticism can establish an attitude without a price reference. Exact own
wording, actor, negation, conditionality, temporal views and conversation boundaries
remain governed by the existing classifier. These bounded grammar checks do not
prove arbitrary prose, sarcasm, multilingual meaning or quoted opinions correct.

A broad “no evaluative word found” downgrade was rejected during development:
it withheld genuine praise and criticism in the frozen real sample. Absence from
a vocabulary list is not proof that a view is absent. Do not reinstate it as a
general semantic validator.

The raw model response remains immutable. New items record its original label and
basis alongside the applied rule; the visible checked label and sample counts use
the checked result. Evidence explains the distinction. Old saved items retain
their exact labels/counts and are marked as an earlier method; they are not
silently reclassified. Changed method identities retain existing quiet-watch
baseline behavior.

## Small samples and evaluation

New summaries require at least **five interpretable counted groups** and a strict
majority to display a leaning. The UI shows majority/usable-group counts and the
separate unclear count. News/platform samples, duplicate grouping and popularity
rules remain. Old saved methods retain their recorded threshold and counts.

`experiments/sentiment_guards/broadcom-social-50.json` freezes the first fifty social
originals from saved analysis `f159bbba-bbc5-44fd-9c44-27d73af55c39`, including
eligible passages, saved parents, original classifications and developer reference
labels. The selection order and ambiguity notes are explicit. These labels await
owner review and are **not independent human ground truth**.

`python -m experiments.sentiment_guards.evaluate` produces confusion tables by
replaying the new code on the old v22 outputs, without a model or database call.
`--predictions path.json` scores an already-generated analysis against the same
frozen reference and reports missing cases. No live v23 output or broad accuracy
claim follows from an offline replay. Source-side changes to the sample and future
prompt/model evaluation must preserve this original dataset and failure evidence.
