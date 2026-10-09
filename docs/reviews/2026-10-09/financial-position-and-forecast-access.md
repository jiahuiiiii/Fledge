# Financial-position visuals and forecast access — phase 90

9 October 2026. This phase continues the original four-part implementation goal and the requested visual Fundamentals experience. It does not mark that goal or the wider roadmap complete.

## Forecast route check

Alpha Vantage's [official documentation](https://www.alphavantage.co/documentation/#earnings-estimates) lists `EARNINGS_ESTIMATES` for annual and quarterly revenue/EPS estimates, analyst counts and revisions. Its section is not labelled Premium; the separate NEWS_SENTIMENT designation cannot establish this endpoint's access. The [provider's standard allowance](https://www.alphavantage.co/premium/) is 25 requests/day for its free tier, subject to endpoint access.

The existing key is present, but the shared `alpha_vantage` clock is blocked until **9 October 2026, 13:00:28 SGT (05:00:28 UTC)** following the original news response. The clock has one recorded request, `denied=false`, and its prior next-at/usage date are retained. No request using the owner's key was sent, no independent forecast clock was created and no pause or denial was cleared. The linked official demo example returned only a demo-key notice, not forecast data or proof of owner-key access. There is no Alpha forecast adapter or imported estimate from this phase. FMP restrictions remain unchanged.

The first read-only clock inspection had an incorrectly parameterized SQL wildcard and failed before returning records; the corrected parameterized query succeeded. This did not change a provider clock or send a request. A guessed SEC guide URL returned 404; the canonical official guide below was then located. These metadata/documentation failures do not establish a source-data outcome.

## Installed financial-position view

**What it owns and owes** in Fundamentals brings already-saved assets, liabilities, cash and complete borrowing into two visual comparisons. Assets/liabilities share one scale; cash/borrowing share another. The descriptions explain that cash is part of assets and borrowing is part of liabilities, so the four amounts cannot be added together. They distinguish accounting values from resale values and point readers to maturities, restrictions and cash flow when considering repayment. No proprietary score, new solvency verdict or automatic investment ranking is introduced.

The selected annual/quarter report supplies the balance date, filing date, accession and original link. Every plotted row and source input must match that date, accession and USD unit and have no duration. An unavailable or differently dated total stays unknown; neither a debt component nor a newer borrowing balance fills an older report. Known zero remains a valid zero. Exact decimal values and original evidence are reused through the existing evidence control; new chart geometry is display-only.

The view consumes existing `performance` and `financial_depth.debt` data. There is no backend/schema/calculation-method/prompt/provider/watch change, no source request on selection, and no AI or Telegram request. Category/period controls elsewhere retain their behavior. Keyboard date selection, source controls, responsive layout and reduced-motion handling remain available.

## Actual saved input check

Read-only inspection of Broadcom's retained quarter, ending **2 August 2026**, found:

| Figure | Saved amount | Definition/source |
| --- | ---: | --- |
| Assets | US$188.148bn | Whole-company `Assets` |
| Liabilities | US$88.458bn | Whole-company `Liabilities`; includes obligations beyond borrowing |
| Cash and equivalents | US$23.975bn | `CashAndCashEquivalentsAtCarryingValue` |
| Borrowing | US$61.079bn | Reported `DebtLongtermAndShorttermCombinedAmount`, not a new sum |

All use the selected `0001730168-26-000080` filing and balance date. The retained annual report has assets US$171.092bn, liabilities US$89.800bn and cash US$16.178bn at 2 November 2025. The current borrowing projection is dated August 2026, so it is withheld when that earlier annual report is selected. This is an input/date check, not an independent comprehensive assessment of Broadcom's financial condition.

## Verification and preservation

All **28 frontend tests**, production build, targeted formatting and diff checks pass. The guarded isolated business browser journey passes with new financial-position assertions at **1440/980/390/320px**, plus existing business, source, peer, revenue, public-forecast and login checks. New cases assert common chart scales, exact evidence, same-filing/date withholding, explicit zero cash, a missing compatible borrowing total, keyboard selection and reduced motion. Desktop/320px screenshots were visually inspected. Screenshots use authored Microsoft-shaped fixtures, not real Microsoft results. The final copy edit removed a redundant sentence; no behavioral code changed after the passing browser run.

The full backend suite was not repeated for this presentation-only phase; phase89's 1,470-pass/65-optional-skip run remains its own result. No new backend checks are claimed here. A context mismatch rejected the first attempt at the final copy edit; reading the formatted lines allowed the exact patch. There was no failed application build or browser case in this phase.

Backup `.local/backups/phase90-financial-position-20261008T193526Z/` preserves prior touched files and the installed frontend. Evidence is `.local/live-tests/financial-position-20261009/`: read-only source values, before/after fingerprints, clock, budget, test/build logs, screenshots and installed-index hash. All **114 database table fingerprints remain identical** through installation; original research, account mappings, watches, notifications, source denials and allowance are retained. Frontend assets were copied before atomic index replacement, with previous assets preserved. No server/database restart was needed. The local server returns the installed index and all referenced bundles. Existing expired owner sessions mean no final signed-in main-browser visual claim.

Ledger remained **US$20.850354 confirmed + US$0.9156025 historical holds**, **US$8.2340435 available** from the original US$30, 369 calls and zero active/attention/unresolved requests. The Alpha Vantage clock remains byte-for-byte equivalent to the initial read.

## Remaining requirements

Quarterly/multi-year forecast access still needs an eligible actual source check after the existing cooldown. FMP consensus/ratios remain restricted. General custom/IFRS/non-USD financial coverage, peer comparability and independent beginner comprehension/usefulness remain separate limitations; this interface work does not solve them.

The definitions follow the [SEC beginner's guide to financial statements](https://www.sec.gov/about/reports-publications/beginners-guide-financial-statements). The implementation contract is [original company research](../../features/original-company-research.md#financial-depth).
