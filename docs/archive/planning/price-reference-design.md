# Price references — proposed extension, 4 October 2026

The user wants sourced analyst price targets or prices derived from visible data/formulas, rather than an app-authored instruction to buy or sell. The formula-based per-share extension was implemented on 5 October 2026: see [the current contract](../../features/valuation-scenarios.md#conditional-share-price-references--5-october-2026). Projected shares and return are explicit user assumptions. Public analyst targets were added in phase 72 using Stock Analysis; see [the current source contract](../../features/analyst-targets.md). Automatic share-count/class conversion remains unavailable. The remaining design notes and provider findings below describe their dated scope.

## Proposed presentation

Put a **Price references** section in Valuation, with separate **Analyst targets** and **My scenarios** views. Show the current quote and its time, then the reference range and matching horizon. Keep target dates and currencies explicit. Use labels such as analyst median target, scenario price at the horizon and price implied by your required return. Do not call an analyst target a guaranteed sell price, use the lowest target as a consensus entry price, or present a model scenario as analyst consensus. A supplier's analyst sample is not the whole market.

Analyst data should expose mean/median, low/high, supplier, retrieval time and provider update date; expose contributor count and target horizon only when supplied reliably. A count of published target reports is not automatically a count of distinct analysts. Missing coverage, missing dates/horizons and disagreement remain visible. Do not fill gaps with an LLM, stale news snippets or dummy numbers labelled as real data.

## Available data

- [Finnhub price-target endpoint](https://finnhub.io/docs/api/price-target), also present in its [official Python client](https://github.com/Finnhub-Stock-API/finnhub-python/blob/master/finnhub/client.py). One bounded AAPL access probe with the existing key on 4 October 2026 returned HTTP 403. That verifies this key currently lacks access; it does not establish every Finnhub plan's price or availability. The request used the existing pacing clock and header credential, made no retry and retained only status/endpoint metadata, never the key.
- [FMP Price Target Consensus API](https://site.financialmodelingprep.com/developer/docs/stable/price-target-consensus) documents high, low, median and consensus targets. Its analyst [API catalogue](https://site.financialmodelingprep.com/developer/docs) also lists estimates and target-summary endpoints. A separate key and suitable endpoint access would need to be chosen; no account, subscription or purchase was made. The consensus response example does not by itself supply contributor count or a precise horizon.

## Reuse the current calculator

Extend the existing immutable valuation scenarios and source snapshots rather than create a second valuation engine. Current P/E and P/S cases produce **future total equity value**, not today's value or a share price. First add an explicitly sourced or user-assumed future diluted economic share count, currency/share-class/split compatibility, and a future horizon measured consistently from the valuation date. Do not divide by a stale arbitrary share count or silently label an already-ended scenario horizon as forward-looking.

A bounded earnings-multiple version can display:

- Scenario price at horizon = projected earnings per share at that horizon × assumed P/E.
- Price implied by a chosen annual return = scenario horizon price ÷ (1 + annual required return)^years from valuation date.
- Alternatively, an explicitly chosen buffer can be applied to a clearly identified **present** value estimate: reference entry = present estimate × (1 − chosen buffer).

These are conditional arithmetic, not forecasts or app-selected thresholds. Keep low/base/high assumptions visible and don't silently combine a discount rate with a margin-of-safety buffer. The simple terminal-price equation excludes dividends, taxes, fees and interim cash flows and is not a full DCF. Any later DCF would need coherent cash flows, reinvestment, discounting and an enterprise-to-equity bridge where applicable; see [NYU Stern's valuation introduction](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/background/valintro.htm).

Use code for arithmetic and validated units. No OpenAI call is needed to calculate prices. Save chosen assumptions with exact source versions and show source gaps. Test share splits/classes, dilution, negative earnings, missing inputs, stale data, already-ended horizons and sensitivity before installing a per-share extension. Existing valuation exports/history must remain unchanged.

Recommended first implementation: the transparent P/E scenario extension using existing fundamentals and explicit assumptions. Add sourced analyst consensus alongside it once endpoint access is available. The explicit per-share scenario extension is now installed; public analyst targets are now a separate sourced panel. No subscription was purchased.
