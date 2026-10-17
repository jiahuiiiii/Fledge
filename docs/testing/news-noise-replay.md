# Saved-news replay readiness

17 October 2026, `codex/redesign-phase-5`. This is a read-only input and saved-
label inventory, **not a completed routing/noise replay**. Phase5remains unfinished.

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
