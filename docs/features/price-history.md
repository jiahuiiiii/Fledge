# Daily price context — phase 18

Real-company workspaces can show a cached Yahoo Finance daily OHLCV chart alongside the separate Finnhub quote. This adapts the team's Deus `pipeline/price_feed.py` daily endpoint, array alignment and whole-watchlist cache concept into the existing Thesis API/database. The endpoint returned data without a new key; the one Finnhub candle preflight returned HTTP 403. No supplier plan was purchased and no denied endpoint was retried or bypassed.

## Workflow and meaning

Open **Price chart · past year** to show approximately one year plus the latest session Yahoo supplies for a registered supported company. The visible, open chart checks prices at most once per minute; closed charts, other research tabs and hidden browser pages stop source checks. **Refresh prices** makes a separate price-only check and shares the same one-minute company interval and original two-second request clock. Reads, range changes, line/candle switches, session inspection and the source table use stored data. These checks make no model call and do not enable a monitoring watch. A failed check pauses automatic updates; an explicit Refresh prices can try again after the interval.

1M/3M/6M show the latest 21/63/126 available sessions; 1Y shows the available requested year. Actual dates appear below the chart. The slider supports keyboard/touch inspection of opening/high/low/closing prices and volume. The table exposes every stored session. Display numbers are rounded; original decimal strings remain in the snapshot.

Yahoo's supplied OHLC series is treated as split-adjusted, without dividend adjustment, following the inspected Deus adapter. It is not independently reconciled for corporate actions. Changes shown are **price changes, not total investment returns**. Each refresh replaces the displayed window as one complete immutable snapshot; it never mixes older adjustment vintages. The parsed original payload and its hash are retained. No adjustment repair or inferred bars are applied.

Following the owner’s 9 October 2026 request, the requested window ends at the current instant rather than New York midnight. Include today’s supplied OHLCV row, labelled **latest session price · provisional** until a matching provider-supplied regular-session end has passed. Missing session metadata keeps a same-day row provisional; no fixed closing time or exchange calendar is invented. Future bars/quotes stay excluded. Quote timestamps received during the bounded fetch are checked against receipt time. The latest valid regular/pre-market/after-hours quote in the payload is retained separately from OHLCV; the company header uses it when it is at least as recent as its separately attributed Finnhub quote. Never replace the daily candle with an after-hours quote. Older immutable snapshots retain their original meaning.

The latest session date, retrieval time and any provider-reported delay are visible beside the chart; source delay can still apply. This is one-minute polling of supplied daily bars and quotes, not tick streaming or a minute-candle chart. [Yahoo’s exchange and data-delay information](https://help.yahoo.com/kb/finance/article-exchanges-data-delays-sln2310.html). The source window and exact price records remain inspectable. Current in-flight checks remain fenced, and older reads cannot replace newer prices. Source withdrawal hides the series and stops acquisition. Shared tabs reuse recent checks rather than independently polling a provider within the minute.

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
