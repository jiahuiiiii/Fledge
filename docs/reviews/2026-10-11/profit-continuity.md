# Consistent profit histories — 11 October 2026

The owner correctly identified an unfixed Micron gap between 1 September 2022 and 31 August 2023 after the earlier graph repair. The previous review classified the scope switch as intentional but missed a complete, consistent alternative already present in the saved facts. This follow-up corrects that omission; it does not infer that whole-group and parent income are equivalent.

## Cause and repair

The backend’s existing displayed net result preferred whole-group `ProfitLoss` separately at each date, falling back to parent `NetIncomeLoss`. The chart then deliberately stopped a line whenever the chosen definition changed. MU has the parent figure for both dates: USD8,687,000,000 profit in FY2022 and USD−5,833,000,000 loss in FY2023. Losing whole-group coverage in FY2023 therefore caused an avoidable visual break, although both parent values were already saved. Negative values are valid chart points; crossing zero does not cause a break.

`profitHistory.js` chooses one available ownership scope across the full company history. Coverage is counted over all retained annual, quarterly and trailing rows; equal coverage prefers the parent share. `RevenueHistory` uses exact values and original inputs from that scope for every point, selected-value card and evidence dialog. No source amount is recalculated. The visible **Profit shown** definition has a selector if both scopes have usable data. Explicit selection survives period-tab changes and cannot carry over to another company. Existing withheld consolidated conflicts cannot be concealed by choosing parent income; missing chosen-scope points never borrow another scope’s figure.

This chart projection does not alter backend responses, saved statements, ratios, monitoring or income-flow calculations. Annual revenue continuity and original Q4 extraction remain in place. Missing periods, unsupported rolling-year arithmetic, different cash-spending definitions and different borrowing scopes still interrupt paths and retain their evidence. The saved QCOM borrowing transition (a sum of separately reported balance-sheet lines versus a reported combined total) remains distinct; this repair does not assert those scopes are equivalent.

## Verification

Evidence: `.local/live-tests/profit-continuity-20261011/`. Backup: `.local/backups/profit-continuity-20261011/` includes the prior sources, built frontend and existing diff. No source acquisition, model calls, private writes, watch changes or external messages were requested by the checks.

- **147 frontend tests pass**, including seven new cases for MU’s positive-to-negative transition, whole-history scope choice, whole-group coverage, explicit missing scope, conflicts, older/withdrawn data, invalid amounts and currencies. The build, touched-file formatting, script syntax and diff checks pass. No backend changes; the backend suite was not repeated.
- Actual read-only responses from **AAPL, AMD, AVGO, FN, INTU, MRVL, MU, NVDA and QCOM** were replayed. Parent-only income is the most complete default for eight; AVGO uses whole-group income. The repair removes **five MU and seven QCOM scope-switch breaks** over annual, quarterly and rolling-year views. There are no remaining profit-definition transitions in these selected histories. Other missing values remain explicit.
- Candidate Chrome checks cover all nine companies and three period types, exact selected values and input identity, SVG points/segments, MU’s two reported figures and original SEC links, whole-group selection with missing FY2023, selection across tabs, keyboard operation, Escape/focus return and layouts at 1440/980/390/320. No page errors or page overflow. Original API histories remain exact; browser mutations and all nonlocal requests are blocked. Desktop and 320px screenshots were inspected. Tall element captures include the existing fixed navigation overlay.

Preserved diagnostics: the first test-file command used a doubled frontend path; the corrected file and final 147-test run supersede it. The initial browser assertion expected the technical net-income label where the product correctly displays “Parent company’s share”; the corrected check passes. No product fix was needed for that test expectation. The initial candidate build preceded the new test file but contains the exact final runtime sources; only the test was added afterward.

## Review and limits

Correctness: one explicit ownership scope avoids combining differing financial measures. Evidence: selected values retain their own immutable filing inputs and links. Usability: the chosen definition is visible and can be changed without editing data. Operations: the installation changes frontend assets only. Evaluation: this is one agent’s review and a nine-company saved-data/browser audit, not independent accounting assurance or proof of universal filing coverage. Real missing or incompatible facts are still displayed as gaps.

## Installed result

The frontend was installed atomically as index **12b5aeb8**, with all **28 assets** verified over HTTP and older assets retained. PID **36538** is unchanged; neither app nor database was restarted. All **116 table fingerprints**, schema **49**, environment fingerprint and full budget ledger are exact across installation.

The installed browser passes the same nine-company/three-period checks and MU desktop/phone checks, with **12 company/layout results**, no page errors and no overflow. Installed API histories match the candidate’s actual saved responses exactly. MU’s positive-to-negative annual line has one continuous path; whole-group selection still exposes its missing FY2023 value. Original SEC evidence, scope choices, keyboard operation and focus return pass. Installed desktop and 320px screenshots were inspected.
