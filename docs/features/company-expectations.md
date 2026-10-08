# Dated expectations — phase 27

Open a real company and choose **Expectations**. This view separates **reported management outlook** from **attributed analyst views**. It uses up to twelve complete company-mention news snippets from the existing seven-day Finnhub sample, ranked by expectation-related words and publication time. It adds no source provider or API key.

**Extract from saved news** is an explicit metered action. The model identifies an attributed outlook, selects exact passages and retains original wording for attribution, numerical values, target periods and any stated revision. Missing amounts and horizons stay absent. Fiscal and calendar wording is preserved without date conversion. An article's publication date is not inferred to be the date management spoke. Company plans, journalist speculation, realised results, counterparty forecasts and standalone share-price targets do not qualify as management guidance.

These are readings of secondary reporting, not original-company verification. Named analysts and research firms remain individual attributed views, never independent consensus. Broad management ambitions are labelled expectations rather than achieved adoption or numerical financial guidance. The page links separately to reported performance, news/social samples and the user's valuation assumptions.

## Research and history

Each extraction preserves its exact source packet, model, prompt, rendered result and original call. Opening history or sources does not make a provider request. Unchanged requests reuse the original reading and its original date. If an earlier source set becomes current again, that matching cached reading remains distinguishable from the reading with the latest source cutoff. Late completion cannot redefine the latest source cutoff. Older readings remain selectable even beyond the first twenty-row history page.

**Draft a research question** opens the existing editor for user review. It does not save reasoning, create conditions or enable monitoring. This phase does not automatically compare forecast amounts with reported results, publish expectation-specific alerts or revise a user's idea. Existing source-linked saved-reasoning checks can investigate a question the user explicitly saves.

The selected reading can be downloaded as an inert, escaped HTML document containing exact quoted evidence, attribution, dates, gaps and limitations. Current source access governs the page, history and download. Loss of access to a consumed source withholds the whole reading's derived content. Counts and saved-record identity remain available.

## Implementation and checks

Migration 019 adds immutable shared `expectation_reviews`. The source collector cannot read generated expectations; packets contain no private reasoning. The app reuses Deus-derived source/evidence handling, Kestrel-derived source/dialog/draft conventions, current restricted database roles and the original cumulative OpenAI ledger. No automatic paid retry, new provider, watch enrollment or historical reclassification is introduced.

The integrated suite passes 559 checks with both retained public SEC corpora. Final request/display/history refinements pass 65 focused checks; these include two tests added after the integrated run. Ten frontend checks/build pass. Expectations, question research and sentiment browser journeys pass; the final expectations run checks cache reuse, exact sources, downloads, draft-without-save, missing amounts/horizons, history beyond a page, failure preservation and 320/390/1440px layouts. Phone/desktop screenshots were visually inspected. An initial narrow-screen overflow was corrected with horizontally scrollable research tabs.

Twelve paid development requests retain initial semantic errors and a rejected citation ID. Five final packets—four actual retained news samples and one authored contrast packet—match 17 selected criteria and 29 exact quote associations. These are corrective development checks, not an independent accuracy benchmark or exhaustive guidance coverage. See [the phase review](../reviews/2026-10-02/expectations-phase-review.md).

Broader original-company guidance collection, normalized forecast-versus-actual series, entitled analyst consensus, expectation-specific change alerts and participant comprehension remain incomplete. No result here establishes investment usefulness or subscription demand.
