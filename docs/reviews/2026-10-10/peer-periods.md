# Micron growth and comparable peer charts

The owner reported MU256.3% stretching Broadcom's comparison while being excluded from the mean and verdict. The saved revenue inputs are correct: USD133.188bn in FY2026 versus37.378bn in FY2025 gives256.3272513243084167157151265%. Public read-only checks of [Micron's SEC annual filing](https://www.sec.gov/Archives/edgar/data/723125/000072312526000023/mu-20260903.htm) and [the issuer's30September2026 earnings release](https://investors.micron.com/news/press-release/2026/Micron-Technology-Inc--Reports-Record-Fiscal-Fourth-Quarter-and-Full-Year-2026-Results/default.aspx) confirm both inputs. The filing reports53weeks in FY2026 and52inFY2025; the application does not normalize that difference.

MU's fiscal end3September2026 is305days after Broadcom's2November2025. The existing120-day presentation rule already excluded it from the mean/verdict, but the bars and scatter plot used every available row to set their scales. The displayed relationship with AMD/MRVL/NVDA was therefore correct for eligible peers, while the visual comparison was inconsistent.

## Change

`comparisonExclusion` centralizes the existing date/provider eligibility and supplies exact reasons. `comparisonRows` applies it to the chart and scatter plot; `peerAverage` and `position` use the same rule. The chart retains the researched company, stable eligible order, signed zero baseline and continuous mean marker. Excluded/missing peers appear as unscaled, clickable rows with original figures, periods and reasons. All members remain in the shared evidence modal, with an explicit exclusion explanation. The verdict names valid out-of-window peers separately and uses a readable list of included symbols.

Actual AVGO now has five plotted companies: AVGO,AMD,MRVL,NVDA,QCOM. Four peers yield38.9% displayed mean; the growth scale ends65.5% instead of256.3%. MU remains separately visible at256.3% with its original filing and both calculation periods/inputs. Operating margin and revenue follow the same fiscal rule. P/E continues to use saved positive Finnhub references irrespective of differing saved dates. There is no price/source fallback, prior-year substitution, numeric clipping, fiscal-week adjustment, source refresh or saved-data mutation.

## Verification

- 119frontend checks pass, including the actual outlier/date arithmetic, exact retained row identity, signed/zero values, missing values/dates, both inclusive120-day boundaries,121-day exclusions, no eligible peer, multi-peer verdict and date-independent P/E. Existing strict annual/amendment/forecast cases pass.
- Build, touched-source formatting, browser-script syntax and diff checks pass. No backend implementation changed or backend suite was run.
- The existing offline competitor browser journey passes1440/980/390/320: positive/negative/zero/missing chart states, peer draft/save, shared evidence, P/E and separate forecasts. Its one peer save is confined to its disposable fictional database.
- Actual saved Broadcom candidate browser passes1440/980/390/320: five bars/map points,38.9%mean, excludedMU256.3%/305days, readable original calculation periods/values, correct SEC link, keyboard/Enter/Escape/focus,44pxexcluded-row target, other annual measures, unchanged P/E, no page errors or document overflow. Saved sector/valuation responses are exact before/after. Browser loading mutations and external images are blocked.
- Desktop chart, phone chart and phone evidence screenshots inspected. The excluded desktop row's initial centered layout was corrected and the final candidate browser rerun. A tall isolated phone chart capture includes the existing sticky header over its top; the normal viewport/evidence checks verify readable scrolling without page overflow.

Evidence: `.local/live-tests/peer-periods-20261010/`. Backup: `.local/backups/peer-periods-20261010/`, including original scoped sources and installed frontend assets. Retain the initial nonexistent-path/glob search, obsolete authored P/E/raw-forecast assertions, hidden nested-summary selector timeout, early browser request before session readiness and overstrict CSS serialization tolerance failure. Final corrected checks pass; those diagnostics are not hidden or attributed to product-data failures.

## Installation

The guarded frontend-only installation verified the full source/file set, prior index and environment hashes, then atomically replaced the index after copying candidate assets. Index7dffb51e and all49candidate files were checked over the local app endpoint; older assets are retained. The app stayed on PID86392 with no restart. All114table fingerprints, schema47, ledger and environment were exact across installation.

The installed saved-data browser passes the same1440/980/390/320checks, including original MU calculation inputs/filing link, exclusions, scale, other annual measures, P/E and modal focus. Installed desktop and phone screenshots inspected; saved sector/valuation responses remain identical before/after. These checks establish rendering and preservation of retained evidence, not independent validation of all financial data or the economic comparability of the peer group.

No AI, app source collection, private owner research/peer save, watch, email, Telegram or accounting operation is part of this repair; public source verification is separate from app collection.
