# Reading and checking a sentiment sample

Phase 24, 2 October 2026. This extends the existing news/social workspace and local watch; schema remains 18.

## User workflow

Open a company with a saved sentiment analysis. Under **What's the tone?**, choose Company news or Reddit discussion, then switch between **AI interpretation** and **Original sources**. Both use the same selected packet. Original sources show the supplied headline/body, publisher, publication time and source inspection action, newest first. They include texts that the AI considered unrelated and exclude comparison-only reports. The view does not apply AI relevance, tone or grouping labels.

These are stored provider snippets and selected Reddit posts, not full articles, comments or the whole available feed. No saved analysis means there is no paired original-sample view yet; the existing recent-news view remains available. Reading, changing channels and opening a source make no source or model request. Current saved reasoning remains in the idea panel; on narrow screens it follows the research pane.

Complete-packet access still applies: withdrawal of any consumed source, including a comparison-only source, withholds the analysis and its original-sample view. Historical records are not rewritten. The existing source modal remains the path to the original publisher.

## Classification boundary

Prompt `thesis-source-sentiment-5` classifies the framing actually supplied about the target company. A financing arrangement, asset sale, lease, contract or executive succession is not inherently favourable or adverse. Direction requires an expressed evaluation, a clearly reported outcome or an explicitly described benefit/harm. A supplier's gain is not automatically the customer's gain. Intelligible descriptive reporting may be neutral; genuinely ambiguous target or meaning remains unclear. Explicit bullish/bearish opinions and actual reported gains/losses remain directional and attributed.

The model, structured schema, coverage policy and original cumulative ledger are unchanged. Exact passage validation checks that quotes came from the source; it cannot establish that the interpretation is correct. News and social aggregates remain separate bounded samples.

## Changes of analysis method

The workspace warns when a saved result's prompt, model or summary policy differs from the installed method. It does not automatically rerun old samples. A watch only produces a comparative sentiment-reversal alert when both results have the same nonempty prompt, model and summary policy, plus the existing fresh-content requirement. Method changes alone must not masquerade as a market change. New adverse-report alerts retain their existing independent eligibility rules.

## Verification

See [phase review](../reviews/2026-10-02/sentiment-calibration-phase-review.md) for the frozen actual-source and authored-contrast evaluation, original-source baseline comparison, spending and remaining disagreements. `tests/run_browser.py --original-sources` exercises exact text/order, retained unrelated texts, channel separation, hidden AI labels, source inspection, withdrawn access, earlier-method warning and phone/desktop layout. Routine checks make no provider calls.

The comparison supports scrutiny of the AI reading; it is not evidence that students understand the results faster or make better investment decisions. Those questions need participants.
