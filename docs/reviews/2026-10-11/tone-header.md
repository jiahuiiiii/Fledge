# Visible tone controls — 11 October 2026

The owner asked to expose the discussion window and watch status beside Refresh & analyse in the What’s the tone? header. The collapsed Reading settings row is removed. A compact select and Watch · on/off button now precede the existing refresh action, on the same desktop row as the title. Phones wrap these controls above the refresh button. A status dot supplements the explicit on/off text.

Only SentimentPanel markup and ReadingFlow styles changed. The same selected-window state, analysis callback, watch dialog and persistence handlers are used. Saved-reading metadata remains tied to the saved reading, with next-watch timing retained. Opening settings or choosing a window does not start a watch or analysis. Disabled-action explanations stay visible and programmatically linked.

## Verification

- All 123 existing frontend checks and the production build passed. Touched frontend files pass Prettier and diff checks. No backend implementation or tests were needed for this layout change.
- Candidate Chrome checks passed at 1440, 980, 390 and 320px: visible controls, desktop ordering/alignment, phone wrapping, 44px targets, no page/header overflow, watch dialog keyboard opening/Escape/focus return, all three window choices, and unchanged saved-reading metadata while selecting another window.
- Browser-only simulations covered watch-on, no saved reading/watch-off, and a running analysis with disabled controls and a linked reason. All browser writes and external requests were blocked; no monitoring toggle, source acquisition or paid analysis was performed.
- Desktop and 320px screenshots were visually inspected. Initial verification matched both native and custom dropdown options; scoping to the listbox fixed the test selector. A later run passed assertions but exposed pending-route teardown; waiting for routes fixed cleanup. Both diagnostic logs are retained.
- The first installation guard correctly stopped on concurrent Financials source changes. The exact already-tested bundle was subsequently installed, excluding those unfinished Financials edits without changing their source files. Candidate hashes and both header source hashes were checked. Existing assets were retained; all 28 candidate files served correctly. PID 6970 remained running without a restart; all database table fingerprints, schema, budget and private configuration were unchanged across installation.
- The installed app passed the same four viewport checks, with no browser errors. Installed desktop and phone screenshots were also inspected. Final index: `81b165a9`.

Evidence: `.local/live-tests/tone-header-20261011/`. Prior source/index backup: `.local/backups/tone-header-20261011/`.

## Review

Parent-authored product/UX/engineering/accessibility/operations review: important reading choices are visible before analysis; desktop hierarchy and mobile wrapping remain compact; callbacks and saved-state semantics are unchanged; labelled controls, explicit status text and keyboard focus remain usable; installation requires no backend restart or monitoring action. This is a layout verification, not an independent usability or alert-accuracy study. Complete seeded monitoring journeys were not rerun.
