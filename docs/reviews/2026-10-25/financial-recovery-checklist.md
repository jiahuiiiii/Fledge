# Missing-figure checklist — 25 October 2026

Replaced the redundant all-reports action and single-report fetch selector in Financials with one collapsible checklist. Each report row names its date and missing figures, with the bounded AI sample, omissions and maximum cost. The header offers Select all / Clear selection. One Find selected with AI button shows the selected report count and combined cost. Nothing is selected initially; selection survives collapsing the panel and resets when the company changes.

Selection follows the existing report-level reading API. Saved suggestions remain available through a separate review selector. Unavailable reports stay visible and disabled. Requests run sequentially for selected reports only; a failure stops the batch without automatic retry. Completed suggestions remain saved, and the failure message survives the free preview reload. Accepting figures remains a separate reviewed action.

## Verification

- Production frontend build passed. Vite retains its existing large-chunk warning.
- Frontend library suite: 214 passed.
- Offline financial recovery backend suite: 23 passed, using a disposable database.
- Focused browser journey (`tests/run_browser.py --financial-recovery`) passed: keyboard disclosure/checkboxes, selection persistence, Select all/Clear selection, combined costs, selected-only sequential dispatch, busy/blocked controls, saved review, stop-on-failure, free preview reload and exactly one missing report. Layout checked at 1440, 390 and 320 pixels without page or panel horizontal overflow. AI responses were authored; no provider requests or live-workspace writes.
- Screenshots visually reviewed: [desktop](financial-recovery-screenshots/checklist-1440.png), [mobile](financial-recovery-screenshots/checklist-390.png), [320px](financial-recovery-screenshots/checklist-320.png).
- Diff whitespace check passed.

## Retained limitations and test setup failures

Initial offline backend/browser attempts could not initialize temporary PostgreSQL because restricted execution denied shared memory. The backend suite and focused journey passed when allowed to run their disposable databases outside that restriction. The first browser launch also lacked the expected bundled Chromium; the successful journey used installed Chrome.

The older broad Financials browser journey first stopped at its initial company selector because the newer onboarding flow appeared. With a test-only completed-onboarding response, it reached an unrelated existing assertion expecting “period ended in a loss”; the current chart displays the negative figure but no longer includes that sentence. That broad journey did not pass. Its assertions and product behavior were left unchanged; the focused recovery journey has its own test-only onboarding response.

No real app/database start, stop or restart, paid model call, schema/configuration change, account-preference change, commit, push or PR was performed. The rebuilt frontend includes the workspace's existing unrelated frontend work.
