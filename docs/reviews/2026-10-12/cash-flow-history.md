# Historical free cash flow — 12 October 2026

The owner reported missing earlier Apple and Nvidia free-cash-flow readings and requested a general fix across companies. The missing readings are primarily annual and past-12-month amounts displayed at quarter-end dates. This repair does not introduce a separate three-month cash-flow calculation.

## Findings and solution

Apple’s older statements tag operating cash using `NetCashProvidedByUsedInOperatingActivitiesContinuingOperations`. The original cash-flow statement labels those amounts as its total operating cash flow. Fabrinet and Qualcomm use the same historical pattern. This tag cannot simply be treated as an alias: [XBRL US cash-flow guidance](https://xbrl.us/data-rule/guid-cashflows/) describes both historical usage for all operating cash and the distinction when discontinued operations are reported.

Nvidia’s older statements use a custom tag for “Purchases related to property and equipment and intangible assets.” Standard Company Facts omits that issuer-specific field. Its exact original tagged row establishes the broader productive-assets spending category already supported by the application. For example FY2022 operating cash of USD9.108bn minus USD0.976bn cash purchases gives USD8.132bn free cash flow.

`cash_statements.py` is issuer-independent. It recognises strict row descriptions in cash-flow statements containing operating, investing and financing sections and a net-income reconciliation. Custom purchases must occur in the investing section; noncash additions, debt principal, business acquisitions, net-of-proceeds values, dimensions and non-USD cells are not accepted. The operating-cash mapping requires an explicit total label and refuses reported nonzero discontinued cash/income. Pre-inline statements corroborate the existing structured amount using exact printed amount, scale and year. No amounts are guessed from positions. An invalid inline filing cannot fall back to the legacy HTML path.

`filing_facts` retains original evidence and source permissions. Reported facts, conflicts and currencies still block replacement. `capital_spending` respects an originally recovered PPE-only amount rather than switching to a broader category merely because the raw standard tag is absent. All financial calculations retain existing dates, concepts, amendment and precision checks. No source or monitoring record is rewritten.

`disclosures.cash_flow_history_plan` extends normal original-filing updates to the bounded historical cash-flow gaps and their preceding annual/dependency filings. Retrieval reuses saved documents and the normal source clock, denial, lease and failure controls. It does not move current disclosure pointers, run AI or collect data when opening a chart. No company-name or ticker override was introduced.

## Actual coverage

A source-only pass retrieved **36 older SEC originals** across six companies, with existing copies reused. The apparent Nvidia “partial” status came from its previously missing earnings release; all 11 requested historical filings were collected. Exact existing financial amounts were preserved across all nine saved companies.

| Company | Annual readings restored | Past-12-month readings restored | Remaining cash-flow gaps |
| --- | ---: | ---: | --- |
| AAPL | 2 | 4 | None in retained history |
| NVDA | 3 | 12 | 25 Oct 2020: preceding annual filing unavailable |
| FN | 3 | 7 | None in retained history |
| QCOM | 0 | 3 | 24 Jun 2018: preceding annual filing unavailable |
| AVGO | 0 | 0 | Two earliest rolling readings lack the preceding annual filing |
| MRVL | 0 | 0 | Three earliest rolling readings lack the preceding annual filing |
| AMD, INTU, MU | 0 | 0 | None in retained history |

Total: **34 restored chart readings** (8 annual, 26 rolling). The seven remaining points lack a required annual filing in the retained filing metadata. The repair does not replace that absent evidence with a later comparative, infer zero or claim universal coverage. Quarterly cash flow remains outside this change.

## Verification and operations

Evidence: `.local/live-tests/cash-flow-history-20261011/`; backup: `.local/backups/cash-flow-history-20261011/`. The work began on 11 October and continued after midnight. Source/database backups precede collection and installation. Public SEC originals are kept in the audit corpus.

- Focused financial tests: 117 pass, 9 optional skips. Full offline backend: **1,903 pass, 84 optional skips**. The final focused cash-flow suite passes **28 cases**, including nine actual-company corpora, conflicts, currencies, negative cash, dates/scale, discontinued operations, custom-label scope, history planning and the final invalid-inline/legacy safeguard. The full suite began before that final safeguard; the exact final safeguard is covered by the focused rerun. Syntax and diff checks pass. No frontend code/build change.
- Read-only nine-company replay preserves every previously available amount. Unrelated available metrics retain their exact source content after normal JSON date serialization and the recovery-method version update. Additional original documents can also improve previously missing noncash figures; no saved financial record changes.
- The collection audit showed changes to the four expected source-retention/clock tables and separate concurrent app loading/HN/feed activity. The AI ledger was exact across collection. Do not claim all tables were unchanged during that source pass, or attribute the concurrent app work to this task.

Preserved diagnostics: initial guessed file paths; a collection preflight that stopped before dispatch because the plan omitted already-cached AMD amendment dependencies; isolated PostgreSQL startup blocked by the sandbox before the approved test run; comparison harnesses initially treating the recovery-method version and Python-versus-JSON dates as figure changes; initial browser workspace timeout and selector correction. The first retained-file snapshot overlapped the last Qualcomm downloads; the completed snapshot is used for final tests. No automatic provider retry, AI dispatch or fee was introduced.

## Review

Correctness and evidence: strict original-statement corroboration avoids aliasing continuing and total operations indiscriminately, and keeps capex scope explicit. User experience: existing chart cards and evidence links show the recovered amounts without extra technical controls. Operations: bounded historical retrieval runs within the normal collector, and the install changes backend code only. Validation: nine saved companies and adversarial fixtures establish this tested scope; this is one agent’s review, not independent accounting assurance or complete historical filing coverage.

## Installed result

Candidate and installed Chrome checks each pass nine-company annual/rolling chart coverage and Apple/Nvidia 1440/390/320 layouts (**13 company/layout results** each), with no page errors or page overflow. The final installed check verifies every recovered selected-date card’s exact formatted amount, original SEC links, broader Nvidia spending caption, retained missing dates, keyboard operation and evidence-dialog focus return. All four API history arrays match the verified replay. Desktop and phone screenshots were inspected. Tall element screenshots include the pre-existing fixed navigation overlay; the final date check also moves the pointer clear of the graph so screenshot scrolling cannot change the hovered date.

Backend-only installation restarted idle app **36538 → 57871** and confirmed its research-loading advisory lease. PostgreSQL was not restarted. Frontend index **12b5aeb8** and all frontend files remain unchanged. All **116 table fingerprints**, schema **49**, environment and full AI ledger are exact across installation. No paid call was made. The earlier public-source collection and concurrent app source activity are separately recorded above.
