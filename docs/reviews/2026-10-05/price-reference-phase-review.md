# Conditional price references — 5 October 2026

## Implemented purpose

The user's outstanding price-reference request now has a formula-based path in Workspace → Valuation → Add entry and horizon price references. Existing P/E/P/S scenarios still determine total company equity at an explicit annual horizon. Optional projected diluted shares convert it to a horizon share price; a chosen annual return discounts that price to a separate entry reference. Inputs include a valuation date and a written share-count source/basis. No model, analyst consensus or broker trade decision supplies these numbers.

The common share count is an explicit future assumption across all cases. It must cover economically equivalent common classes and consistent split/dilution units; no automatic share feed, unequal-class allocation or ADR conversion is added. The form explains millions, dilution and the distinction from historical weighted-average shares. Annual returns start blank. Dividends, distributions, taxes and costs are excluded; this is a terminal-price-only model, not full DCF. Analyst targets remain unavailable from the connected source.

## Contracts and preservation

`thesis/price_reference.py` uses Decimal at 28 significant digits. Entry discounting uses actual days / 365.25 from the chosen date to the existing scenario horizon. Future valuation dates and dates before the base filing are rejected. A horizon at/before the valuation date or unusable equity produces no forward price reference. Sensitivity uses the same share/return assumptions in each cell.

The optional request field is omitted from legacy serialization when absent/null. Existing equity-multiples-1 results and idempotent save hashes stay exact. New results use equity-multiples-per-share-1 and retain all assumptions, formulas and unrounded results in immutable private records and escaped offline exports. Copying a saved comparison preserves its date/inputs for explicit review. Current source withdrawal withholds derived prices, as it does equity values. Schema 32 is unchanged.

## Verification

- 51 focused backend cases pass, including the prior valuation suite and six retained real-company filing bases. Independently recomputed horizon/entry prices match all 108 sensitivity cells across P/E and P/S; share counts, growth, margins and returns are authored testing assumptions, not actual forecasts.
- Unit/contract checks cover zero/invalid shares, nonfinite/bounded inputs, split/dilution scaling, zero return, fractional-year discounting, loss cases, expired horizons, future/pre-filing dates, old save hashes, immutable copies and withdrawn-source exports.
- 22 existing frontend checks, the production build and targeted formatting pass. The expanded disposable valuation browser journey covers pricing, save/export/reopen/copy, loss/elapsed cases, dilution and 320/390/768/1440px layouts. Desktop/phone screenshots were inspected.
- The initial withdrawal test used an invalid entitlement fixture; changing it to the established fictional value fixed the fixture without changing production access checks. An initial browser assertion matched both the case price and sensitivity center cell; it now targets the price-card values. Original failures are retained.

No full backend-suite rerun, Safari/assistive-technology audit or participant study is claimed. Valuation calculations and browser checks make no paid/source calls. Evidence: `.local/live-tests/price-references-20261005T011233Z/`; backup: `.local/backups/phase70-price-references-20261005T011233Z/`.

## Installed check

The main app on port 8841 serves the matching built assets and new calculation. A read-only browser preview using Microsoft's actual saved annual revenue and explicitly authored share/growth/margin/return assumptions matches independently calculated horizon and entry prices. It makes no saved comparison or external request. The existing legacy Microsoft comparison remains readable. Both phase-69 Amazon/Meta analysis IDs are visible through the installed workspace API.

Installed 320/390/768/1440/1920px widths have no horizontal overflow; desktop and phone screenshots were inspected. There are no browser errors or failed requests. The first installed check expected lowercase text where existing CSS displays title case; the check now ignores case. No app change was required. All protected table hashes, including saved valuations, remain unchanged from immediately before installation. All acquisition/review schedules remain off and the original budget is unchanged. Backups retain the prior source and built frontend; older hashed bundles are retained for open tabs.

## Five-perspective review

One agent applied these perspectives, not independent consultants or participant evidence.

| Perspective | Finding |
| --- | --- |
| Product | Provides the requested formula-based price references while consensus access remains separate. |
| UX | Optional inputs and paired readable price values keep the existing workflow; assumptions remain inspectable. Beginners still need usability testing. |
| Finance/method | Period, return and share units are explicit. The share assumption is not verified and the terminal-price model omits interim payouts. |
| Engineering/QA | Existing persistence/permissions are reused without migration; legacy hashes and negative/elapsed cases are covered. |
| Business | Calculating and saving needs no API credits. No price, conversion rate or paid-demand assumption is validated by this increment. |
