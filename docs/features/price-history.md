# Daily price context — phase 18

Real-company workspaces can show a cached Yahoo Finance daily OHLCV chart alongside the separate Finnhub quote. This adapts the team's Deus `pipeline/price_feed.py` daily endpoint, array alignment and whole-watchlist cache concept into the existing Thesis API/database. The endpoint returned data without a new key; the one Finnhub candle preflight returned HTTP 403. No supplier plan was purchased and no denied endpoint was retried or bypassed.

## Workflow and meaning

Choose **Refresh daily history** to retrieve approximately one year for Microsoft, Apple or Alphabet. Reads, range changes, line/candle switches, session inspection and the source table use stored data. Refreshes are manual and at least one hour apart per company, sharing a separate two-second request clock. No model call or automatic watch is introduced.

1M/3M/6M show the latest 21/63/126 available sessions; 1Y shows the available requested year. Actual dates appear below the chart. The slider supports keyboard/touch inspection of opening/high/low/closing prices and volume. The table exposes every stored session. Display numbers are rounded; original decimal strings remain in the snapshot.

Yahoo's supplied OHLC series is treated as split-adjusted, without dividend adjustment, following the inspected Deus adapter. It is not independently reconciled for corporate actions. Changes shown are **price changes, not total investment returns**. Each refresh replaces the displayed window as one complete immutable snapshot; it never mixes older adjustment vintages. The parsed original payload and its hash are retained. No adjustment repair or inferred bars are applied.

The current New York calendar date is excluded even after the closing bell. Only prior dates are displayed, avoiding a running intraday bar labelled as a final daily close. The next local refresh can pick up that session after New York midnight. The window, source and retrieval time are visible. The Finnhub quote can be newer or differ from the historical series; they are separately attributed.

## Validation, storage and boundaries

Migration 016 adds shared immutable price snapshots, a fenced refresh state and a dedicated request clock. App connections are read-only on these tables; the restricted source role writes acquisitions. Private ideas, monitoring inputs, alerts and the paid ledger remain separate. No historical-price data is sent to a model or used to infer a news cause.

Responses must match the selected supported equity, USD, New York timezone and daily interval. Dates use the named timezone's historical daylight-saving rules, not today's fixed UTC offset. OHLC arrays stay index-aligned. Null/incomplete price rows are omitted with a count; null volume stays unknown. Invalid positive prices, nonintegral/negative volume, duplicate sessions, wrong high/low ranges, wrong metadata and empty responses are rejected. No missing date is filled. Lines connect supplied sessions and do not establish complete exchange-calendar coverage.

A refresh that drops retained dates in the new window or returns an older last date cannot replace current history. HTTP errors, rate limits, timeouts, oversized responses and malformed data preserve prior prices. Two-minute leases and attempt IDs fence late completions; there is no automatic HTTP retry or alternate-host fallback. Source withdrawal prevents refresh and withholds the API/UI series. Re-enabling a source is an operator decision, not an error fallback.

Source access for local testing does not establish a production data contract. The public endpoint may change or throttle; this is a bounded local pitch connection, not a promise of an entitled production feed. Yahoo history documentation/source access is linked from the chart. The existing live-data flag controls connection availability.

## Reuse references

- [Deus price feed at the inspected revision](https://github.com/c0vo/Deus/blob/74d5aea8b0acf72e1851dfc841f9f1408e9e6609/pipeline/price_feed.py): direct Yahoo chart endpoint, daily parsing and cached price history. User-authorized team code; existing provenance remains applicable.
- [Finnhub stock-candle documentation](https://finnhub.io/docs/api/stock-candles): endpoint checked once with the supplied free-tier key; current access was denied.
- [yfinance project](https://github.com/ranaroussi/yfinance): corroborates the public Yahoo chart approach and its research/personal-use limitations. No yfinance package or code was imported; the existing HTTP client is sufficient.

See [the five-perspective phase review](../reviews/2026-10-02/price-history-phase-review.md) for actual retrieved values, tests, preserved failures and remaining limitations.
