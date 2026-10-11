# Revenue forecasts in Financials — 11 October 2026

The owner requested dotted future revenue on the Financials chart, clearly distinguishing analyst forecasts from management guidance. `RevenueHistory` now combines the existing saved-source projections with the extracted `FinancialHistory` chart. Annual, quarterly and rolling-year views remain separate; no backend data, calculation, acquisition or accounting contract changes.

## Data and presentation decisions

- Solid reported revenue, blue dotted analyst estimates and gold dotted management guidance share the dollar scale, with named legend, exact fiscal-end labels, low–high ranges, source links and distinct circle/diamond markers. Financial history, selected-date figures, legend toggles and original evidence remain available.
- Forecasts extend only a matching period. Missing reported quarters and non-adjacent future years break lines. Historical net-result scope remains exact; no quarterly cash flow is invented from YTD.
- Source access, current management release, dates, amounts/ranges, currency and matching history control eligibility. Different forecast providers remain selectable sources, not an averaged consensus. A read refresh removes withdrawn estimates and invalidates their open dialog.
- Missing currency remains unknown. A local unchecked USD-assumption control permits an explicit chart comparison and marks the point/readings/dialog. It is scoped to source, horizon, amounts and observation vintage. A source explicitly using another currency cannot be overridden. Unknown accounting basis does not generate a growth or beat/miss verdict.
- Evidence retains original guidance quotation/context and links, forecast average/range, source/collection dates, contributor-count limitations and reported comparator. Text stays at normal CSS-pixel size; the chart is 322px high and phones scroll internally toward the forecast end. Interactive SVG points expose keyboard names, 44px targets and modal focus return.

## Verification

137 frontend helper checks pass, including 14 new cases covering period matching, explicit currency assumptions, other-currency refusal, permission withdrawal, current-release-only guidance, malformed/range/duplicate input refusal, missing-period line breaks, chosen quarterly net scope, and qualified comparative wording. Frontend build and targeted formatting checks pass. No backend suite was run for this frontend-only change; concurrent backend tests belong to their task.

Read-only local browser checks use saved Broadcom data at 1440, 980, 390 and 320px. Actual saved quarterly guidance is approximately 34.8bn for 1 November 2026; its release does not establish currency. It remains an unplotted reading until the local USD choice is made, then joins the matching reported 29.591bn quarter. Broadcom has no saved analyst revenue estimate. Actual saved Qualcomm analyst data was also exercised, including its source dialog; no public website number was copied into product data.

Browser-only authored cases cover annual analyst and management lines together, two analyst providers, estimate ranges, unknown currency, provider selection and source withdrawal. Both actual and authored layouts retain 12px axis text, 322px height, no page overflow, revenue-series toggles and keyboard/Escape/focus behavior. Desktop and phone screenshots were inspected. Authored numbers are not saved or promoted into user research. Browser writes (automatic loading attempts) and all external requests were blocked; cached API responses were reused for repeat viewport checks.

An initial sandboxed Chrome launch was unavailable; authorized browser execution succeeded. The first saved-data check used an insufficient 15-second timeout; the 60-second rerun passed. Keep these logs and pre-polish screenshots. Capture-position refinements prevent sticky navigation obscuring the chart heading; they are test-only changes.

## Review lenses

- Reader: a connected, labelled future period gives the standalone forecast context; annual and quarter controls are explicit. Missing analyst data stays visible.
- Accounting: exact saved values and ownership scopes survive. Unknown currency requires a visible user assumption; absence is never zero. Estimate ranges are not confidence intervals.
- Source integrity: current-release-only guidance, source access gates and withdrawal checks remain; stock-price currency is not promoted into forecast currency.
- Interaction: source details are one click away, keyboard operable, and contained on small screens. History remains selectable independently of future estimates.
- Maintenance: chart geometry is extracted once, forecast eligibility has pure tests, and no provider, schema, model or watch work is introduced. These are one agent’s review lenses, not independent reviewers or user validation.

## Installation scope

Candidate artifacts and reports: `.local/live-tests/revenue-forecasts-20261011/`. Backup: `.local/backups/revenue-forecasts-20261011/`.

The first browser-verified candidate excluded then-unfinished concurrent financial recovery controls. Before installation, that task completed its own source/backend/schema-049 installation (index `99ea9fa6`, PID 79983). The old candidate was not installed. Its reports and assets are retained under `before-recovery-integration` names. The final candidate incorporates the complete installed recovery frontend plus this task’s changes; every other source byte was checked against that task’s frozen source. This task does not apply migrations or restart the app. Atomic installation retains old assets and verifies the served candidate, source guards, process identity, environment, database table hashes, schema and ledger. See the installation report and appended outcome below for actual final results.


Final outcome: installed frontend **e572f9d5**, all 28 candidate assets verified over HTTP, old assets retained, PID **79983** unchanged/no restart. All **116 tables**, schema 49, budget ledger and environment fingerprints are exact across this frontend installation. The installed saved-Broadcom browser passes all four widths, including optional currency choice, quarterly guidance connection, original source dialog, keyboard/focus, Revenue toggling and rolling/annual separation. Desktop and phone viewport screenshots were inspected after correcting the test capture scroll container. Candidate-only authored provider/withdrawal cases and actual saved Qualcomm forecast checks are separately listed in the structured report; the older generic installed-console success sentence mentions those candidate cases too broadly. No source collection, AI call, private-research/watch change or external message by this task.
