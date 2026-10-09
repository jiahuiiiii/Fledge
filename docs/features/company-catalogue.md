# Supported company catalogue

The local pitch catalogue is Microsoft (MSFT), Apple (AAPL), Alphabet (GOOGL), NVIDIA (NVDA), Amazon (AMZN) and Meta Platforms (META). These are examples for testing the research workflow, not investment recommendations or general stock-market coverage. Expansion is an implementation choice under the ongoing full-plan work; the user did not select these three additional tickers individually.

`thesis/research/catalogue.py` is the single source of company identity and lexical matching. The established SEC-derived IDs stay unchanged. All six use the same filing, Finnhub news/quote, daily-chart, separate news/social sentiment, private research and optional watch contracts. Adding a company registers a shared workspace; it makes no source/model call and creates no saved idea or watch.

A textual mention admits a candidate into a bounded sample; it does not prove relevance. NVIDIA/NVDA, Amazon/AMZN and selected Meta brand/ticker names are recognized. The matcher excludes selected obvious false matches, including “Amazon rainforest” and “meta-analysis”. It is not comprehensive entity resolution. Sentiment classification must still distinguish target-company tone from unrelated text, reports about other businesses and investor opinions. Reddit feed failure and thin/no samples remain visible; no alternative platform is silently substituted.

Actual SEC identities and selected financial inputs were checked before enabling the additions. Six original annual/quarter filings reconcile 122 selected current/prior inputs exactly. NVIDIA uses a different fiscal calendar; the interface preserves its dates. NVIDIA and Amazon cash capital spending and free cash flow remain unavailable under the current supported tags. Amazon liabilities and some debt components are also unavailable. Missing is not zero. Quarterly cash-flow dates can span the fiscal year to date and must not be described as direct-quarter cash generation.

The phase review records actual retrieval, model checks, browser evidence and limitations. No schema or model/prompt change is needed. No existing private state is migrated or auto-enrolled.

For offline replay, set `THESIS_EXPANDED_CORPUS` to the saved public directory containing `NVDA-bundle.json`, `AMZN-bundle.json`, `META-bundle.json` and `reconciliation.json`. The backend replay and `tests/run_browser.py --catalogue` consume those files without external requests. This is a replay of actual data; it is not a fresh supplier check at test time.

## Company logos — 9 October 2026

The company list and header share `CompanyAvatar.jsx`. Actual Broadcom, NVIDIA and Fabrinet images are bundled from Financial Modeling Prep's public company-image route; [source URLs and original file hashes](../../frontend/src/assets/company-logos/SOURCES.md) are retained. Other registered SEC companies use the same HTTPS route when displayed, without credentials or a referrer. Pending or unavailable logos retain initials, and fictional recorded companies make no image request. The content security policy allows the provider's image host while retaining same-origin script and application-request rules. Logo retrieval does not register a company, acquire research sources or initiate analysis. [UI verification and provider limitation](../reviews/2026-10-09/workspace-panels-and-company-logos.md).

## Distinct evidence inside a repeated story

The first real NVIDIA private check exposed a selection problem: a newer short roundup and an older fuller buyback report were in one semantic-repeat group. In-request deduplication kept the teaser, omitting the actual authorisation and remaining-capacity passages. Private checks now retain distinct unseen full-content identities within a repeat group, up to the existing sixteen-source cap. Only previously seen semantic keys suppress repeat delivery; exact duplicate text identity is still deduplicated inside a request. One private check still creates one grouped publication. This preserves richer evidence without rewriting historical results, changing the model prompt or enabling a watch. The retest and original incomplete answer remain in the phase evidence.
