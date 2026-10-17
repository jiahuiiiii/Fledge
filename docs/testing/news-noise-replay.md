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
