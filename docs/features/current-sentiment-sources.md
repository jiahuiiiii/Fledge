# Read current sources before another sentiment analysis

The news/social panel now compares the current bounded source selection with the last accessible saved sentiment reading. Expand **Read current sources** to inspect Company news, Reddit discussion or Hacker News without requesting a model call. This also works before the first analysis. The existing **AI interpretation** and **Original sources** controls continue to show the exact saved analysis sample.

Since phase77, a manual 1/7/30-day discussion window is recorded with the saved reading and used by its current-source preview; news and automatic watches stay at seven days. Opening a company now separately starts its idempotent source-loading job. Opening the source-preview disclosure itself remains read-only.

The preview is assembled from permitted locally stored sources, not a live supplier search. It uses the same eight-news/eight-social selection and byte limits as sentiment, with the same publication/availability cutoff and seven-day window. Provider/source failures remain visible in source coverage. Each selected text shows its original title/body, publisher, publication date, first local availability and source inspection action. Social authors and model labels are not added. A selected company-feed item can be irrelevant; selection does not establish target-company relevance or sentiment.

## What the comparison means

Per platform, the preview counts source versions newly selected, no longer selected and retained relative to the saved analysis. These are source-version differences, not new-event counts, materiality or market sentiment changes. A corrected version, ranking change or aged-out text can change membership. Comparison-only news remains a separate pool and is excluded from displayed selected counts and texts. Changed membership in that pool is disclosed separately.

Parent-context differences are checked only on retained sources and use the pinned semantic content identity. An identical parent recheck does not look like new input merely because its storage ID or check time changed. Different wording, withdrawal or expiry can change eligible parent context. No new context is added to an old analysis or label.

If a consumed source makes the earlier reading unavailable, its comparison counts and parent differences are withheld. The preview can still show other currently permitted texts, independently selected; it never retrieves a withdrawn body through the old analysis. Empty or unavailable coverage is not neutral sentiment. Matching source identities/context does not establish model quality, complete coverage or current prices; the existing earlier-method and analysis-age notices remain separate.

## Implementation and verification

`sentiment_inputs.current` is a read-only projection inside the existing repeatable-read workspace response. Source inspection reuses the existing modal and explicit original-parent action. `sentiment.prepare(..., allow_empty=True)` preserves candidate counts for preview-only empty selections; generation retains its existing no-source error. No migration, model prompt, acquisition, watch activation, alert publication or historical rewrite is caused by opening the preview.

Tests cover first reads, exact membership/version differences, independent parent/comparison changes, expired windows, incomplete passages, complete-packet withdrawal, future availability, selection limits and unchanged saved labels. The browser checks exact displayed texts, source inspection, first-reading/empty-platform states and responsive layouts. Actual-case retrieval and results are recorded separately in the [phase review](../reviews/2026-10-03/current-sources-phase-review.md).

This closes a visibility gap between collection and analysis. It does not classify the new texts or resolve the pending actual-model quality evaluation, wider source coverage or participant validation.
