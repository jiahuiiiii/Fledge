# Sentiment request limits and earlier-news references

The current sentiment pipeline fits complete selected sources to the existing 64,000-byte model request limit before reservation. It measures the whole canonical request, including structured output schema and supplied parent context.

Comparison-only reports are reduced first, keeping the longest ranked prefix that fits. If original texts alone are too large, remove the last original from the most populated channel and platform; ties use total serialized size. Selected text and its supplied parent are never shortened by this step. Earlier sampling/fragment rules still apply. Omitted originals and comparison reports are counted separately and disclosed in preview, saved readings, source inspection, history, alerts and exports. Omitted context can change a reading; the remaining sample is not full market coverage.

Already-fitting packets keep their request identity. Empty inputs construct no model schema; an impossible complete-source fit cannot reserve or dispatch a paid call. Cache identity uses the actual retained request. Coverage counts/omission notices belong to the saved packet and do not change past readings. Access withdrawal withholds dependent details.

Method `thesis-source-sentiment-14` restricts each selected news item's comparison reference IDs to earlier reports, using publication time and storage-ID tie order. Its own passage IDs are constrained too. The renderer separately validates references, chronology, uniqueness, relevance and original quotes. These checks cannot establish that a semantic relationship is correct or ensure the model returns every valid relationship. Exact-body grouping remains separate from permission to suppress a changed headline.

Policy `sentiment-coverage-7` prevents a method-only aggregate shift from alerting. Classification instructions retain v10 semantics; rejected v11–v13 and the evaluation-only checker remain uninstalled. No migration, new provider or extra model stage is added. Watches remain explicitly controlled and share the original ledger.

[Phase 59 real-source evaluation and limitations](../reviews/2026-10-04/source-limits-phase-review.md). Offline checks: `tests/test_sentiment_limits.py`; isolated browser journey: `tests/run_browser.py --sentiment-limits`.
