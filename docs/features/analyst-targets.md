# Public analyst targets — 5 October 2026

Workspace → Valuation shows **Analyst price targets** separately from **Explore the assumptions**. Average, median, low and high targets are USD 12-month forecasts. The source is [Stock Analysis](https://stockanalysis.com/stocks/aapl/forecast/), which [attributes consensus targets to S&P Global](https://stockanalysis.com/data-sources/). The existing Finnhub target endpoint denied this key; it is not retried. This connection needs no additional key, AI call or subscription.

## Source meaning

The parser consumes only the visible public summary/table, with a fixed URL for each of the six supported companies. It verifies symbol, exchange, currency, poll size, positive ordered ranges and narrative/table agreement. Script content is ignored. Missing/changed format or an inconsistent range fails explicitly. It never fills missing targets with a model or another company's numbers.

The source's displayed page-update date is retained when available. It is not asserted to be the date of each underlying target. The target-specific vintage and target contributor count remain unknown; the displayed count is the number of analysts in the published poll. Fetching again does not make the underlying opinions newer. Analyst targets are neither a consensus entry price nor a promised future quote, and the low target is not a suggested buying price. No return/upside is computed by mixing this range with an unrelated quote vintage.

## Acquisition and persistence

Opening Valuation reads saved data. Refresh is a deliberate same-origin action, at most once per company every 24 hours, under a global two-second request clock and a two-minute attempt lease. One public HTTPS page is read with an identifying User-Agent, a 25-second timeout, a 2 MB size limit and no redirects, automatic retries or alternative-provider fallback. Access denial/rate limits remain errors. The initial public robots check allowed the forecast path.

Migration 034 adds immutable shared snapshots, separate mutable check state and a request clock. The stored evidence contains the selected public text and whole-page hash; full pages from development acquisition are retained locally for audit. Failed refreshes preserve earlier data and expose the error; interrupted/expired leases do not claim success. Snapshots fetched over 24 hours ago are marked old. A replaced attempt or source withdrawal cannot publish an in-flight result. Current withdrawal also withholds cached target values. No private research, saved scenario, alert/watch or model record is changed.

The HTML page is not a contractual API and may change. This is a bounded local pitch connection; production delivery and durable supplier arrangements remain future decisions. FMP and Alpha Vantage are documented alternatives requiring separate endpoint/key choices, not automatically configured backups. [FMP API](https://site.financialmodelingprep.com/developer/docs/stable/price-target-consensus) · [Alpha Vantage documentation](https://www.alphavantage.co/documentation/).

## Verification

See [the phase review](../reviews/2026-10-05/analyst-targets-phase-review.md) for actual retrieval, automated checks and limitations. Calculating, refreshing and reading these targets require no model spending.
