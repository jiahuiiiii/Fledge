# Saved-news replay readiness

17 October 2026, `codex/redesign-phase-5`. The approved seven-day company-news
counterfactual is complete and **fails the noise target**. Historical inventory
and preparation checkpoints follow; the latest measurements are at the end.
Phase5remains unfinished.

## Inputs and exact matching

The frozen private input covers10–16October in Singapore time: five companies,
172source-availability frames,1,489source versions including the earlier baseline,
and1,066new news opportunities. Two first-observed company samples have no prior
baseline and stay quiet. The portfolio is the fixed current watchlist, not a
reconstruction of historical account preferences. Saved/provider coverage is
incomplete, particularly early in the window. Google News contributes its own
headline only; stored original documents are unchanged.

`experiments/soclaas_replay/noise_replay_readiness.py` checks the input fingerprint,
seven-day bounds, source/passages, company ownership, chronological frames,
publication/availability cutoffs and distinct source entry. It inventories earlier
saved analyses in a database-enforced read-only transaction. Candidate matches
require the exact production content key, consistent model-visible passages,
supported prompt/summary/evidence policies, own-source quotations and valid label
combinations. Current-policy quick-check skips retain their original quick model
and calls; they are never attributed to the bulk model. No labels appear in the
inventory output, and the owner's blind review is neither opened nor modified.

The earliest exact saved answer is retained independently of query order, with
original model, prompt, analysis and call provenance. Answers saved after a frame
are counted separately. They can inform later offline evaluation but cannot be
represented as knowledge the app already had at that time. Actual reuse still
requires fresh source-access checks and normal validation; this inventory does
not authorize live cache insertion, a paid call or a prompt-quality claim.

## Measured inventory

The read-only run examined145saved analyses. Of1,066opportunities,1,055have exact
saved-label candidates and11do not. All1,055were saved after the source-availability
frame; zero are claimed already available at its cutoff. Five unmatched sources
have changed model-visible evidence in a saved version. Existing Google cluster
bodies are not substituted for the headline-only projection.

These counts may reduce repeated tone work. They supply no new importance or
duplicate decisions, no independent usefulness labels and no Telegram noise
denominator. Do not route all unknown importance as low or use zero immediate
messages to claim success. Independent replay remains **0/7days**.

Verification:23new offline cases and128related tests pass. They cover altered
text/stale passage lists, publisher/company/policy changes, fabricated quotes,
Google projection, quick provenance, future evidence, ordering, repeated source
entry, initial quiet samples and read-only connection enforcement. The initial
sandbox test-database setup errors and the stale-passage regression failure are
retained; the corrected related run passes. Test fixtures are invented and make
no external calls.

Private input, result and logs live under
`.local/live-tests/redesign-phase-5-20261017/quality-campaign-prepared/`.
US$0, zero model/source calls, no saved-research/preference/environment/migration
change, installation or app/DB restart. User CSS remains exact.

## Complete-sample replay and bounded evaluator — 17 October 2026

`news_noise_replay.py` consumes complete evaluated baseline/frame readings.
It preserves production news rank/exact-content selection and rejects missing
frames, sources, importance and forged quotations/links. Production company
change/importance functions determine publications; covered ordinary alerts stay
app-only. Immediate messages contain high evidence only, use the actual formatter
and claim only displayed excerpts. Daily recaps use the actual summary formatter,
five-member/two-link/length bounds and account-wide24-hour story identities.
The exact expiry is half-open. Pending final news follows through to the next
07:00Singapore recap without reading later sources. A fixture compares the whole
daily message byte-for-byte with the live recap function.

This is a company-news counterfactual. It does not reconstruct historical watch
dispatch, HTTP outcomes, private ideas, conditions, social shifts or price/cost
messages, and cannot prove live timeliness. Missing input dates or zero messages
cannot pass the seven-day noise gate. A fingerprint-bound independent review
must label every displayed source as substantive/opinion/comparison/price recap/
unclear; any low-value excerpt makes its message low value. Classifier forced-low
fields cannot award a pass. Owner50-source quality stays separate.

`news_noise_campaign.py` freezes exact tone provenance and production file/model
contracts, retaining old models/calls and clearing future comparison caches. It
only executes under the selected GPT pair and an explicit plan/cap. It checks all
source permissions before payment, rechecks per request, uses folder-independent
body-hash ledger identities, a single campaign lock, a cumulative confirmed-plus-
unresolved budget and sequential calls. First failure stops; unsettled/redispatched
requests block continuation. An explicitly invoked identical-plan continuation
can recheck settled answers free and send only unattempted requests. Old charges
cannot disappear under another folder/cap. No app records/preferences or Telegram
calls are made; raw answers and partial cost records remain private.

Final266related offline tests pass, including37new campaign/replay cases and the
earlier23inventory cases (overlapping earlier178/58runs). Retain serialization,
malformed-patch and recap-boundary fixture diagnostics; corrected runs pass.
Real frozen input has1,489versions with1,434saved tone candidates.48missing
versions appear in later frames; seven additional missing versions occur only in
the baseline. New-news importance prepares162requests before new quick skips;
their independent reservation sumUS$35.4902475is not an approved spend. Expected
actual campaignUS$2–5, sequential combined capUS$6. Bounded duplicate work depends
on actual relevance, candidate pairs and negative-pair caching. No paid news-noise
campaign has run at this checkpoint; replay/noise acceptance remains0/7.

## First paid stop and source-bound schemas — 17 October 2026

The first one-pass campaign stopped after13paid requests,12validated answers
and5/172frames. ConfirmedUS$0.119564, zero unresolved holds. The failed event
answer put headline text where a passage ID was required; the own-source
validator rejected it. No automatic retry occurred. Noise acceptance remains
0/7days, with no percentage or success claim from the incomplete run.

`sentiment-task-schema-3` now groups news items by their identical supplied
passage-ID sets. Each event variant binds its allowed item labels and both
reporting/importance passage enums to that set. Different passage sets use
nested variants; equal sets share definitions. This preserves the same array
result format and event/tone instructions, while preventing quote strings or
other-source IDs from entering these fields under strict generation. Runtime
citation checks remain strict. The request remains bounded at48kB, including an
eight-distinct-variant test. Nested choices and definitions follow the
[official Structured Outputs subset](https://developers.openai.com/api/docs/guides/structured-outputs#supported-schemas).

The operator now supports a separately frozen schema revision with explicit
failed-request nomination. Original input/cached tones/models and other production
contracts cannot change. Reuse compares the complete request outside its schema,
then revalidates the old raw answer; valid answers stay free. Changed requests
beyond the schema cannot silently replay an old input. The old failed response
remains rejected; a new body is allowed only for the named failed request after
explicit owner approval. Cumulative costs include the original failure, and a
failed new attempt cannot automatically retry under the original authorization.
Saved-only mode forbids all new dispatches even when budget remains.

Final311affected offline tests pass. A real saved-only recheck validates all12
earlier successful answers (five under inherited event schemas), zero new calls
and the originalUS$0.119564retained. The56-case tone plan is byte-equivalent at
the request level and still validates its original fingerprint; its4/6hard-case
result remains separate from pending owner labels0/50. The review page is exact.

The proposed revised paid run reuses12good answers, retests only the one failed
request and sends only untouched requests thereafter. Expected additionalUS$2–5;
combined capUS$6including the initialUS$0.119564. Its event reservation sum
US$35.881205is not spending authorization. **No revised paid execution yet;
the no-automatic-paid-retry rule requires explicit owner approval.** No app
publication, source refresh, environment/preference/migration/install/restart
change or Telegram call. Preserve both stops and all free-check/test diagnostics.

## Completed approved revision and failed noise gate — 17 October 2026

The owner-approved revision completes **172/172 frames across seven input
dates**, producing71publications and23hypothetical messages:16immediate and7daily
recaps.278new paid requests plus12distinct earlier valid answers give290distinct
validated calls (293evaluations including free repetition). New calls include
the one explicitly approved failed-request retest; there are no automatic
retries. AdditionalUS$2.31882475, **combinedUS$2.43838875** including the original
failure, zero unresolved holds. No research/publication/settings changes or
Telegram HTTP requests. New calls use the selected GPT-5.4/mini pair; inherited
tones retain their original model/provenance. This is not live timeliness proof.

A separate coding-assistant review reads all53displayed titles and complete
saved excerpts before inspecting classifier importance fields. It labels30
substantive,18opinion,1comparison,1trading recap and3unclear. Any low-value source
makes its containing message low. **15/23messages (65.22%)** are flagged:
11/16immediate and4/7daily recaps. The≤10%gate **fails**. This is an independently
performed source-form judgment, not owner ground truth. Even restricting the
review to seven clear recommendation/valuation/comparison sources flags6/23
messages (26.09%); the failure does not depend on every borderline judgment.
The private fingerprint-bound excerpts, reasons and annotations remain beside
the frozen output, separate from the owner's blind50-source review.

The model often calls a source `event` because it contains a genuine product,
financing or legal fact, even when the article's purpose is valuation or
commentary. Separately, a daily recap could display a low-rated companion item
from a publication whose highest item deserved a higher route.

## Free diagnostic and prepared purpose revision — 17 October 2026

Prepared routing revision2filters scored-low companions before recap formatting
and claiming. Explicit investment wrappers (valuation, buy/sell advice, stock
comparisons, analyst upside and investor-thesis framing) cannot promote a story,
including when an older saved importance label says high. A legal `A vs B`,
cheap product, uncertain acquisition, management quote or question alone is not
automatically blocked. These are news guards; unscored private discussion
matches retain their prior daily-review handling. Carried-over labels are copied
and demoted locally, with a versioned reading identity; originals stay exact.

A file-only diagnostic recomputes the same frozen answers with those guards,
without dispatch:67publications,20messages (13immediate/7recaps). Four newly
displayed excerpts were separately read and classified substantive. **11/20
messages (55%)** remain low-value (7/13immediate,4/7recaps). This is a same-history
diagnostic after observing the failures, not a fresh acceptance sample; it still
fails. No percentage is substituted for the original failed gate.

Prepared `news-article-purpose-2` asks for article purpose before importance,
explicitly distinguishing background facts from the article's editorial form.
Reporting can acknowledge a real background event while importance stays low
for opinion/comparison; genuine announcements are not rejected for a question,
uncertainty or a price-reaction headline alone. Tone instructions/schema remain
exact. Event outputs gain a purpose-policy version; old importance must be
rechecked while unchanged tones stay saved. **No paid test of this prompt yet.**
The original56-tone plan still validates its exact fingerprint: hard cases4/6
remain, owner labels0/50pending. No owner answers were opened or inferred.

The operator's explicit post-completion mode binds the verified completed prior
campaign, exact captured sources/inherited tones/models and a new purpose
version. It reuses only exact cached requests, retains all previous campaign
costs and the global lock, stops at first failure and cannot automatically
retry. Saved-only mode cannot dispatch. This supports a separately approved
semantic test; it does not broaden the earlier schema-retry approval.

Proposed next test: same frozen history, cached quick/tone requests, revised
GPT-5.4importance and only changed/uncached comparison work. Expected additional
US$1.50–3, **combined cap staysUS$6includingUS$2.43838875already spent**. Not
executed; explicit owner approval is required. The new prompt/routing and
delivery remain off, no installation/restart or preferences changed.

Final **229 affected offline tests pass**. Earlier225and107runs overlap and
predate the final purpose-version/continuation changes. The broader2,656-pass/
93-skip backend result predates this follow-up. Preserve the initial nonexistent
suite selector, empty-baseline fixture and cached-event expectation diagnostics;
corrected authored tests pass, including legal-news counterexamples, news-only
scope, copied label demotions, event-only refresh, cumulative costs and explicit
completed-parent/saved-only guards.

Real saved-only preflight validates4cached requests, attempts0new calls and stops
at the first uncached request, retaining the fullUS$2.43838875prior charge and
zero unresolved holds. Tone56plan and blind-page/protected-CSS hashes stay
exact. Frozen purpose plan is private; only a new explicit approval can authorize
its paid execution. No paid inference result for the revised prompt is claimed.
