# Apple historical income and cash-flow gaps — 9 October 2026

The owner supplied Apple Financials at 30 March 2019 with Revenue, Net result and Free cash flow all unavailable. This is a historical past-12-month selection, not Apple's latest filing.

## Diagnosis and correction

The retained 2018 annual revenue uses `Revenues`; the 2019 quarterly current/comparative values use `RevenueFromContractWithCustomerExcludingAssessedTax`. The existing same-concept rule withholds the annual/YTD revenue bridge. It also discarded the otherwise known bridge start date. Financial history then compared every other measure against that absent start and erased valid net income, operating profit and cash flows.

`financial_depth.trailing` now retains the explicit fiscal window when reporting labels differ, while withholding the amount. Financial history compares other measures with revenue dates only when those dates exist. Independently valid measures retain their own exact dates and inputs. Known mismatches, consolidated-result conflicts, unsupported capex, missing inputs and incompatible ratios still remain unavailable. History cards display a missing measure's own explanation beside its amount.

Actual saved Apple at 30 March 2019, for 1 April 2018–30 March 2019:

| Measure | Exact USD calculation | Result |
| --- | --- | --- |
| Net income attributable to parent | 59,531,000,000 + 31,526,000,000 − 33,887,000,000 | 57,170,000,000 |
| Operating cash flow | 77,434,000,000 + 37,845,000,000 − 43,423,000,000 | 71,856,000,000 |
| Cash capital spending | 13,313,000,000 + 5,718,000,000 − 7,005,000,000 | 12,026,000,000 |
| Free cash flow | 71,856,000,000 − 12,026,000,000 | 59,830,000,000 |

Original annual accession `0000320193-18-000145` and quarterly accession `0000320193-19-000066` remain attached. Only the trailing periods ending 29 December 2018, 30 March 2019 and 29 June 2019 change in the saved Apple replay. All other annual/trailing/balance periods, including latest values, remain exact.

## Remaining revenue limitation

Revenue is still withheld across these three reporting-label transitions; no generic alias or later-filing fallback is introduced. The saved amounts alone do not establish accounting comparability. Public review of [Apple's Q2 2019 report, Note 1](https://www.sec.gov/Archives/edgar/data/320193/000032019319000066/a10-qq220193302019.htm) found full retrospective Topic 606 adoption, no material impact on previously reported total net sales and changed product/service classification. This supports further accounting-basis resolution but is not silently converted into a retained, machine-validated bridge or a hard-coded Apple exception. This task fixes the unrelated measures being erased and makes the remaining limitation visible; it does not claim full historical revenue coverage.

## Verification

- 31 focused financial-depth/story checks pass, including new concept-transition, missing annual/trailing revenue, date-mismatch, consolidated conflict and read-only coverage.
- 53 overlapping performance/peer/amendment checks pass; three optional skips. Existing missing-data, permissions and immutable original evidence remain covered. This is not a fresh full backend suite.
- 103 frontend checks, production build, touched frontend formatting and scoped diff checks pass.
- Existing disposable Financials browser passes 1440/980/390/320: shared scales, exact evidence, negative/missing values, selections, source withdrawal, keyboard and zero app writes/external requests.
- Actual retained Apple candidate browser passes the same widths: restored values, explicit revenue reason, exact fiscal windows, rounded evidence with original annual/quarter report links, Escape/focus return, latest-date selection and no page overflow/errors. Desktop and phone screenshots inspected. Candidate uses a read-only calculated story response over the retained actual payload, not a new provider result.

Evidence: `.local/live-tests/aapl-history-20261009/`. Backup: `.local/backups/aapl-history-20261009/` (touched sources and earlier frontend).

Preserved diagnostic failures: first guessed amendment-test filename did not exist; the corrected test paths pass. First replay compared in-memory datetimes against serialized strings and falsely flagged otherwise identical period metadata; canonical serialized comparison confirms only the three expected periods change. First browser assertion expected three decimal places while the existing intended presentation rounds to two; corrected display assertion passes, exact inputs separately verified. No product changes were made to accommodate those diagnostics.

Idle app-only restart69431→9766 left the database running. The first readiness guard stopped frontend publication because API timestamps use `T` while the saved Python comparison used a space. Exact differences were retained in `install-differences.json`; canonical timestamp comparison passes with every financial value/input/identity unchanged. Installation resumed without a second restart after all114table fingerprints and the ledger matched the original pre-install audit. Full source/file-set/prior-index guards pass; atomic index `c551d8c2`, all33assets, local-pitch session, schema47 and environment verified. Older assets retained. All114tables remain exact across the complete installation.

Installed live Apple browser passes1440/980/390/320px with the actual API response:57.17bn/59.83bn, explicit remaining revenue reason, fiscal windows, original report links, keyboard/focus and latest-date selection. Zero page errors; only automatic loading attempts were intercepted, and all external requests were blocked. Installed screenshot inspected.

No source collector, model, email, Telegram, watch, private research, allowance or charge-review action is part of this correction. The original419-call ledger and unresolved FN hold remain separate and unchanged.
