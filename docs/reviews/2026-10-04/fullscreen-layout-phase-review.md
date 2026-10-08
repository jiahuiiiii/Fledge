# Full-screen workspace review — 4 October 2026

## Decision and result

The user reported an unfixed header, a footer inside the side panel, an awkward company list and cramped/uneven spacing below the stock chart. Phase 61 corrects the desktop frame while preserving the selected Terminal structure and Radar research panels.

Above 740px, the app fills the viewport. Navigation, source context and the full-width bottom status bar stay in place; company, research and saved-idea panes scroll independently when necessary. The company list now uses compact rows with one consistent gap. The centre uses shared gutters across the company header, quote, chart, question and research sections, with greater separation for the question workbench and evidence cards. Above 2000px the side panels widen moderately. Updates uses the same left rail with a bounded reading width. Phones retain normal page flow, a sticky header and the existing company picker.

`frontend/src/workspace-layout.css` owns shell geometry and is loaded after component styling. The old footer is moved out of the idea sidebar into a semantic app footer. Focusable, labelled panes retain visible keyboard focus. Existing view/company remounting resets the pane's scroll position; no new state or API contract is needed.

## Verification

- Production frontend build and 22 existing frontend checks pass; changed frontend files pass formatting.
- Installed, read-only browser checks pass at 2560×1440, 1920×1080, 1440×900, 1280×800, 1024×768, 800×900, 740×900, 390×900 and 320×900. These check viewport containment, pane boundaries, full-width footer placement, fixed desktop navigation, keyboard PageDown, access to pane bottoms and the mobile sticky header.
- Company filtering, research-tab keyboard movement, source dialog/Escape and all four navigation destinations pass. The browser blocks and records non-GET requests and external origins; neither occurs. Actual saved Alphabet data supplies the layout content; no source refresh or analysis is triggered.
- The existing disposable fictional browser journey passes: draft persistence, explicit approval, mixed outcomes, review, outage/restatement, exact history, concurrent-edit conflicts, phone switching and missing-source states. This tests UI behavior, not investment accuracy.
- Before/after screenshots were visually reviewed at desktop and phone sizes. Evidence is in `.local/live-tests/fullscreen-layout-20261004T014240Z/`; source/build backup is `.local/backups/phase61-fullscreen-20261004T014240Z/`.

The first layout test had a keyboard-scroll timeout. A diagnostic confirmed native PageDown scrolling; the final test waits for its animation before resetting or resizing the pane. The installed run passes. Initial build-command/config permission errors were corrected before the successful production build. No runtime backend, schema, model, watch or saved-research changes are made, and no paid request is used. The full backend suite was not rerun for this presentation change.

Run the read-only layout check against an already running local app with `node tests/browser_layout.cjs`, supplying `PLAYWRIGHT_MODULE`, `CHROMIUM_PATH` and optionally `THESIS_TEST_URL` as in the existing browser setup. `THESIS_LAYOUT_SCREENSHOTS` selects a screenshot directory; by default it uses the system temporary directory. This check assumes the local pitch catalogue includes Alphabet and its saved source citation.

## Five-perspective review

This is one agent's structured review, not five independent consultants or participant validation.

| Perspective | Assessment | Remaining limit |
| --- | --- | --- |
| Product | Companies, saved reasoning and navigation remain available during long research sessions. | User acceptance of the revised density is still to be established. |
| UX | The company list is grouped; research sections share gutters and clearer spacing; the footer belongs to the app. | The many research controls still require longer-form usability testing. |
| Engineering | A dedicated shell stylesheet and small markup changes keep behavior intact. | Existing component styling remains large; this pass does not rewrite it. |
| Accessibility and QA | Keyboard scrolling, tab keys, native dialogs, phone layouts and pane boundaries pass in Chrome. | This is not a complete assistive-technology or cross-browser audit. |
| Evidence and cost | Source timestamps/limitations remain available; saved research and backend behavior are untouched. | This visual pass does not resolve known sentiment accuracy or broader product-validation gaps. |
