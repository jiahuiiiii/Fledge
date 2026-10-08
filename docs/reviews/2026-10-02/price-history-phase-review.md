# Phase 18 — real daily price context

Parent-authored review through five professional perspectives. This is not an independent consultant panel or participant validation; independent agents remain unavailable under the previously recorded account limit. Alerts and separate news/social sentiment remain the product's main selling points. This phase closes the missing actual-company chart in the selected market workspace.

| Perspective | Finding | Implementation / remaining work |
| --- | --- | --- |
| Product | A real quote beside an empty historical chart left the accepted workspace incomplete. | MSFT, AAPL and GOOGL now have daily price context with visible dates. Price movement is separate from evidence, sentiment, monitoring and valuation; it cannot validate a saved idea. |
| UX | A chart needs inspectable values and usable controls on phones. | Line/candlestick views, 1M/3M/6M/1Y ranges, keyboard/touch session inspection and a full daily table are implemented. A responsive SVG width fixes tiny mobile axes. Provider, retrieval time and excluded current day remain visible. Participant comprehension is untested. |
| Data | Finnhub candle access returned HTTP 403 with the supplied free-tier key. Deus already has a suitable direct Yahoo daily adapter. | Adapt the team's existing endpoint/aligned-array approach. Three actual acquisitions return 252 sessions each; all 3,780 stored OHLCV fields match the raw responses. This is not independent corporate-action or historical market-price verification. |
| Engineering | Mixing snapshots can mix price-adjustment vintages; failed refreshes must retain usable history. | Store immutable whole windows with exact decimal strings and a fenced current pointer. Validate metadata, dates and OHLCV; reject regressions, retain prior data on failures and make all chart reads local. Schema 16 and the restricted source role preserve the existing app boundary. |
| Commercial | Price context completes the demonstration but is widely available elsewhere. | Treat charts as supporting functionality. Recurring value still depends on useful, low-noise evidence alerts and reassessment; willingness to pay and student benefit remain unmeasured. |

## Actual retrieval and reconciliation

One Finnhub candle preflight was denied with HTTP 403. No retry, bypass or subscription followed. A public Yahoo preflight succeeded, then three installed-adapter acquisitions populated the app. No new API key, dependency or model request was needed. Reuse is recorded in [provenance](../../../PROVENANCE.md); the [contract](../../features/price-history.md) records exact data and refresh semantics.

| Company | Retained sessions | First / last session | Last close, displayed USD | Raw fields matched |
| --- | ---: | --- | ---: | ---: |
| Apple | 252 | 2025-10-01 / 2026-10-01 | 330.32 | 1,260 |
| Alphabet | 252 | 2025-10-01 / 2026-10-01 | 338.24 | 1,260 |
| Microsoft | 252 | 2025-10-01 / 2026-10-01 | 512.80 | 1,260 |

The independent-from-parser checker aligns raw timestamps using America/New_York and compares all five OHLCV fields with exact Decimal values. These responses have no omitted price rows, missing volume, partial-window flag or old-last-session flag. That does not prove every expected exchange session is present; no exchange calendar was added. The latest closes also match the retained Finnhub quotes for 1 October at 20:00 UTC to the displayed cent. Other OHLC fields can differ between providers and were not asserted equal.

Evidence is retained at `.local/live-tests/price-history-20261002T051421Z/`: three raw parsed payload/series snapshots, the reconciliation report, preflight metadata, main-record comparison and budget before/after. The helper and software logs accompany this evidence. The actual installed Microsoft browser shows the 63-session range ending 1 October, the last daily close and the separately attributed Finnhub quote.

## Software and installation

- **424 integrated backend checks** pass with the saved actual SEC corpus, including 23 new price-history checks. One existing dependency deprecation warning remains. No test makes a paid request.
- **Five frontend checks and production build** pass. The dedicated fictional-price browser journey covers cached bars, range/style controls, keyboard dates, the source table, missing volume, an empty company and 320/390/1440-pixel layouts without supplier/model requests.
- The prior recorded end-to-end research, approval, change/review, history/archive, conflict and source-permission journey passes. Its first run failed only because an assertion retained the old empty-chart wording; the assertion now matches “No price history available,” and the full journey passes.
- Focused tests cover exact/aligned data, daylight-saving dates, malformed metadata and values, response size, no retry, cooldown, concurrent refresh, expired/late attempts, access withdrawal, regressions, whole-window corrections and A→B→A history. These are software checks, not provider service guarantees.
- Before installation, source and database were backed up at `.local/backups/phase18-price-history-20261002T051205Z/`. Migration 016 was applied. All preexisting rows and private configuration were preserved; actual acquisition left main-account ideas, watches, publications and monitoring state unchanged. Main watches remain off.

## Accounting and limits

No additional OpenAI request or spending in this phase. The original shared ledger remains **US$3.222376 confirmed + US$0.13926 original maximum hold**, **117 calls**, **US$6.638364 remaining** under the US$10 software ceiling. The original interrupted charge is still unsettled.

This is a manual, approximately one-year daily window for three equities, excluding the current New York date. It is not intraday streaming, a total-return series, a complete technical-analysis product or an entitled production feed. Corporate actions are not independently reconciled. The whole implementation plan remains incomplete: social-risk calibration and repeated-story noise, wider source/issuer coverage, structured expectations, prospective alert timing and participant usefulness remain open. Preserve the phase-17 model disagreements; this chart phase does not resolve them.
