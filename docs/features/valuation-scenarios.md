# Valuation scenarios — current contract and historical phase 15

The **Valuation** tab supports one to three explicit cases for the supported SEC operating-company workspaces. The user chooses annual growth, a one-to-five-year horizon, a multiple and a written rationale. P/E cases also require an assumed net margin attributable to common equity after interest and tax. Inputs start blank; **Try illustrative assumptions** loads a clearly labelled generic worked example only when chosen.

## Deterministic method

The base is positive annual revenue from the selected immutable financial snapshot. Quarterly revenue is never annualised. Code computes:

- Annual revenue at the horizon = reported annual revenue × (1 + annual growth / 100)^years.
- P/E: annual revenue at horizon × assumed net margin / 100 × P/E.
- P/S: annual revenue at horizon × P/S.

The original output is **total company equity value at the scenario horizon**, in USD, undiscounted. The optional per-share extension below supersedes the original no-conversion boundary only when explicitly enabled. It is not a present fair-value estimate, expected return or share-price target. Dividends are excluded. There is no enterprise-to-equity bridge, share count, dilution or share-class conversion. The date is the calendar anniversary of the base reporting end, with leap-day clipping, not an inferred future fiscal reporting date; a scenario may cover a period already ended when an old base is used. Base dates and the chosen horizon remain visible.

Nonpositive projected earnings make a P/E result undefined, with an explanation; they do not create a negative price. Nonpositive revenue makes P/S undefined. Missing annual facts, incompatible source/company IDs, nonfinite numbers, extra fields and out-of-range assumptions are rejected. Arithmetic uses Decimal at 28 significant digits before presentation rounding. P/E and P/S are equity multiples; their definitions and limits follow the primary [NYU Stern pricing material](https://pages.stern.nyu.edu/~adamodar/pdfiles/eqnotes/Pricing.pdf), not a generated trade recommendation.

Sensitivity tables vary growth and net margin around each P/E case while holding horizon/multiple fixed. Growth/margin steps are explicit percentage-point inputs (initially 5). P/S tables vary growth and use 75%, 100%, 125% of the chosen multiple. Values are bounded to the same allowed ranges; duplicate edge columns/rows collapse. Each center cell agrees with the case calculation. The table is a deterministic what-if exercise, not a probability distribution.

## Optional reference multiples

Manual Finnhub `stock/metric?metric=all` requests supply `peTTM` and `psTTM` for companies already in the supported catalogue. The endpoint is verified against the [official Finnhub client](https://github.com/Finnhub-Stock-API/finnhub-python/blob/master/finnhub/client.py) and [API documentation](https://finnhub.io/docs/api/company-basic-financials). The existing header-based credential, bounded transport and shared request clock are reused. Wire-level decimals are retained for this endpoint. No new dependency, credential or model is needed.

A new immutable reference records the raw response, selected metrics and retrieval time. The provider response supplies no precise timestamp for the ratio. Missing, invalid or nonpositive values remain unavailable; values are not reconstructed from a current quote and stale annual earnings. The table is labelled a supported-company comparison, not an automatically justified peer group. TTM references and projected annual scenarios use different periods. The user may explicitly select a reference; editing that multiple clears the source selection. Refreshing the reference table never silently changes a chosen assumption.

Requests are manual, per-company checks are one hour apart, and HTTP happens outside the collection transaction. A two-minute attempt lease fences late responses. Errors retain prior references and do not retry automatically. Interrupted attempts are visible as coverage errors after their lease. Opening or calculating scenarios makes no provider request. Reference refresh is independent of news, sentiment, existing watches and monitoring.

## Private persistence and exports

Migration 015 adds immutable `multiple_references`, acquisition status and private immutable `valuation_scenarios`. The actual restricted app role uses forced owner policies. Scenario rows bind the company to the exact financial snapshot and retain assumptions, optional reference records, source base, formulas, results, sensitivity and method `equity-multiples-1`.

Preview is read-only. **Save this comparison** recomputes on the server and rejects a changed financial base rather than rebasing silently. The visible form can load the latest base while preserving typed assumptions. A request UUID plus canonical payload hash makes identical concurrent saves idempotent and rejects reuse for different assumptions. Saved comparisons keep old source values after later corrections. **Use these assumptions in a new comparison** explicitly copies them against the current financial snapshot; it does not overwrite the old record or saved investment reasoning.

Downloads are inert escaped HTML with the exact source record, private assumptions, cases, formulas and full sensitivity grids. Owner/source checks apply to listing, reading and export. Withdrawn sources hide the source packet and derived results, while retaining the user's recorded assumptions. The broader historical assessment API source-withdrawal concern from earlier phases remains separate.

## Verification and remaining scope

Integrated backend suite: **368 passed** with the saved real SEC corpus. The final formula-only refinement also passes all 23 focused valuation checks. Five frontend checks, build, valuation browser and prior financial browser pass. The browser covers reference adoption/editing, positive/loss cases, sensitivity, save/export/reopen/copy, P/S, retained input after conflict, and 320/390/768/1440 layouts. Automated providers are mocked.

An initial test-fixture failure was caused by the shared reset removing the new source row; the fixture now restores the expected source. An initial browser assertion mismatched CSS title-case text; the case-insensitive assertion preserves the same behavioral check. Those logs remain retained. Installed company/reference tests are documented in the phase review: three actual supplier checks, 150 independently matched case/grid outcomes, six QA saves and one labelled main-account example, with actual browser download verification. Reference API results are provider data, not independently recalculated market multiples.

Reverse valuation, DCF, present-value discounting, EV multiples, automatic peer selection, share-price conversions, and calibrated assumption proposals are not implemented. The first multiples/sensitivity workflow is complete within the stated boundary; usefulness and beginner comprehension still require participants.

## Conditional share price references — 5 October 2026

Enable **Add entry and horizon price references** in Valuation. Enter total projected diluted common shares in millions, an annual return assumption, a valuation date and a written share-count source/basis. These fields start blank except the current UTC date. The same share/return assumption applies to all cases; growth, margin and multiple still vary by case.

- Horizon price = projected total equity / (projected diluted shares in millions × 1,000,000).
- Remaining years = actual days from valuation date to the scenario horizon / 365.25.
- Entry reference = horizon price / (1 + annual return / 100)^remaining years.

This terminal-price calculation excludes dividends, other interim distributions, fees and taxes. It is not full DCF or a claim of expected returns. Equity-multiple definitions and transparent assumptions follow [NYU Stern's pricing material](https://pages.stern.nyu.edu/~adamodar/pdfiles/eqnotes/Pricing.pdf) and [valuation introduction](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/background/valintro.htm), checked 5 October 2026. The formula is calculated locally; no AI, new price subscription or additional key is needed.

Use all economically equivalent common classes and a consistent split/dilution basis. Do not substitute a single class count, ADR units or unequal economic rights. A historical weighted-average count is not a forecast of horizon shares. Automatic share acquisition/verification, class conversion and subsequent split adjustment remain unimplemented. Source and assumptions are user-recorded. This is the formula-based branch of the price request; [analyst targets](analyst-targets.md) are displayed separately and never select these assumptions.

Input shares must be positive and finite; the annual return is explicitly chosen between 0 and 100%. Dates cannot be future or precede the annual base filing. If the scenario has already ended, or equity is undefined, there is no forward price reference. Decimal precision is 28 digits; UI prices round to cents while saved/exported results retain precision. Sensitivity cells use the same count and return, and exports include both horizon and entry values.

Saving and copying retain exact dates, inputs and source versions; old records remain unchanged. Withdrawing the source hides derived prices. Without this option, legacy serialization and save hashes remain exact. Method `equity-multiples-per-share-1` distinguishes new optional results from `equity-multiples-1`. [Verification and limits](../reviews/2026-10-05/price-reference-phase-review.md).
