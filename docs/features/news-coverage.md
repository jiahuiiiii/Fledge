# Current comparison wording — phase 54

New comparisons show an AI relationship description written by code, followed by each report's exact selected excerpts and its original link. A detail from one report cannot be added by free prose to a claim about both reports. The relationship itself remains a model interpretation. Counts, grouping, repeated-story guards and review eligibility remain unchanged.

Historical free-text summaries remain intact and are labelled as earlier AI-written wording in the workspace, alerts and weekly export. Classifier v10/model requests remain unchanged; `sentiment-coverage-6` versions the new rendering, and `coverage-source-pair-1` marks new link descriptions. Already settled responses can be reused to append a new reading without a paid call. The raw provider explanation is retained only for audit/compatibility and is not published in new links.

[Verification, preservation and limits](../reviews/2026-10-03/coverage-wording-phase-review.md). The remaining sections record the original phase19 design; their model, policy and schema numbers are historical.

# Comparing repeated news coverage — phase 19

Different headlines can describe the same development. The sentiment analysis now compares selected news reports with one another and up to sixteen additional recent company-news snippets. These additional reports are comparison context, not extra sentiment votes. Social posts retain their separate sample and cannot be linked into a news group.

## What the user sees

Every selected report keeps its own tone, explanation and original source. A linked report has a **compare reports** disclosure containing both exact quotations, both source links and the model's explanation. The comparison is one of:

- **Repeated coverage:** the model found the same specific development without new substantive information. A watch may keep it quiet only when the referenced coverage has already been seen.
- **New detail on an earlier report:** additional information, changed numbers/dates, confirmation or a completed plan stays eligible for review.
- **Conflicting reports:** an explicit contradiction stays eligible for review; grouping does not decide which report is true.

For the news summary, related reports count as one coverage group. Different directions within a group become mixed, or unclear when any member is unclear. All original reports remain visible. This is a count of interpreted coverage groups, not independent witnesses or market consensus. The social calculation is unchanged.

## Model and code boundary

Prompt `thesis-source-sentiment-4` extends the existing Deus-derived batch classifier. It makes one metered request for labels and coverage links, using the same OpenAI profile and original ledger. Summary policy is `sentiment-coverage-4`. No second grouping provider, embeddings service or background process is introduced.

The selected sample remains at most eight news and eight social items, with the existing 16KB-per-channel bounds. Comparison context uses up to sixteen other current, permitted news snippets from the same seven-day window, bounded to 24KB. Selection follows the existing company-mention/date ordering. It cannot discover a repeat whose earlier report is outside that bounded context. It does not crawl whole articles or search all historical coverage.

Each link must point from a selected news item to an earlier supplied news report. Equal publication timestamps use a deterministic source-ID order. Code rejects self-links, cycles, duplicate links, foreign IDs, social links, unrelated selected items and citations that do not belong to the exact report. Both quoted sides are retained. Source withdrawal withholds an analysis that depends on that source, including comparison-only evidence. This verifies structure and quotations; whether two reports mean the same thing remains a model judgment.

Only `repeats` can suppress repeat delivery. A conservative code guard disables suppression when the newer supplied passages contain new numeric text, different explicit negation/status terms, or a selected member is opinion/uncertain reporting. It leaves the original model label and explains why the report remains reviewable. This guard is deliberately incomplete: it is not a semantic fact checker and may retain harmless wording changes. `adds_detail` and `contradicts` never inherit the earlier report's seen identity.

## Watch and history behavior

Company and saved-idea watches compare the current report's complete-content key and eligible repeat ancestors against that owner's existing seen content. Body equality alone is a counting rule: it cannot suppress a changed headline, which could contain a correction or denial. Exact baseline identities bridge the old body-only policy. A legacy body-only key cannot prove which headline was seen, so it alone cannot suppress a new report; this can retain extra coverage after an upgrade. Another owner's history cannot suppress an alert. Private checks still require their exact saved revision; a source-group comparison never changes conditions or research outcome. Explicit private checks do not suppress a report merely because an earlier watch saw it, although interchangeable duplicates within the selected sample are checked once.

Quiet private checks remember newly encountered repeats, so the next repetition can refer to them without creating a fresh interruption. Successfully checked samples also remember their complete selected coverage. New detail and contradictions keep their own content identity. Old analyses, classifications, alerts and review records are never rewritten. A new counting-policy version cannot itself produce a positive-to-negative sample-shift alert; the first comparison across the change is a new baseline for that rule. Newly eligible reporting remains reviewable.

No watch is enabled by installation. No paid request occurs when opening reports, comparisons or history. Models have no automatic paid retry. Existing immutable JSON records hold the new request context/results; schema remains 16.

## Reuse and verification

Deus's inspected aggregator only deduplicates source URLs, and its event tracker groups calendar entries by ticker/date/type. Neither establishes semantic equivalence of these news snippets. This comparison and delivery policy is new Thesis code around the reused Deus classifier and Kestrel-derived private review workflow; it is not claimed as upstream functionality.

See [the phase review](../reviews/2026-10-02/news-coverage-phase-review.md) for actual-source results, retained failures, software checks, budget and remaining gaps. A bounded development evaluation does not establish prospective alert recall, user usefulness or general grouping accuracy.
