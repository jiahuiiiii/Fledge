# Workspace controls and spacing — 8 October 2026

## Changes

- The progress strip has an up-chevron to collapse it completely. A compact **Progress** button beside Refresh restores it, shows ongoing work or attention, and keeps the keyboard focus position usable.
- Header icons independently toggle the company and idea sidebars. Preferences are three browser-local booleans only; no private research is stored there. Hidden sidebars stay mounted and surrender their layout columns. Company selection remains available through the existing picker on narrower screens.
- Quote metadata, chart controls/date labels/axis numbers and form text are larger. MiSans remains the typeface.
- The reasoning intro uses its full available width, removing the old 58ch cap. Event-editor content and action spacing is consistent. The reasoning heading has 20px below it before subsequent content/actions.
- Source-preview paragraphs have zero inherited margins and a shared 20px grid gap. Its label and select use a separate 10px gap. Article titles and source text have a clear reading hierarchy.

## Verification

27 existing frontend checks and the production build pass. Browser checks used the actual Broadcom workspace without saving/editing research, requesting new paid analysis, changing watches or resetting any data. Both sidebar toggles were checked separately and together; the main workspace expanded to the remaining width. Hidden settings survived Updates/History navigation and a reload. Progress can be reopened; Enter transfers focus to the replacement collapse/restore control.

At 320px, 390px and 980px there is no document horizontal overflow. At 980px, All companies occupies the full available width without an empty grid column. The narrow company picker remains usable. The reasoning intro has no maximum width; source-preview metadata has consistent 20px gaps and 14px type. The reasoning heading's computed bottom margin is 20px. The final desktop browser showed no console errors. Temporary viewport overrides were reset.

Evidence: `.local/live-tests/layout-controls-phase79/` contains build/test logs and screenshots. Source backup: `.local/backups/phase79-layout-20261008T013449Z/`. No database migration or backend changes; no new paid tests. The existing sentiment interpretation limitations remain open.

## Follow-up: one aligned research column

The owner's collapsed-sidebar screenshot exposed a width mismatch: only the lower research content was capped at 1160px, while the upper chart/question sections and research tabs filled the pane. `workspace-layout.css` now owns one shared width for the company header, quote, chart, question selector, research tabs, content and workspace skeleton. The question card is inset by the same gutters as the lower content cards. The selector uses the shared gutter instead of a separate fixed padding. Removed the lower-content-only cap from `polish.css`.

The production build passes. Browser inspection of the saved Broadcom answer confirms the question card, tab labels and lower content align. All four sidebar combinations align at the normal 1512px viewport. At 2048px, upper and lower containers share a 1160px width; at 980/390/320px they shrink to the pane without document or pane horizontal overflow. No browser console errors were recorded. Viewport overrides and sidebar preferences were restored. Evidence is `.local/live-tests/workspace-alignment-20261008/`.

Verification used a separate preview tab to preserve the user's existing form. No research was saved, no analysis or source refresh was manually requested, and existing watches were left unchanged. This was a CSS-only change; backend and model evaluations were not rerun. The documentation inventory found 54 top-level Markdown/SQL references, about 0.5 MB, covering feature contracts, testing/evaluations and historical plans. None was deleted or moved.

## Follow-up: unified questions and margins across pages

The owner's next screenshots showed the selector and investigation accordion repeating one task, plus secondary pages still using independent widths. A real-company workspace now presents one **Research question** card with the saved selector, Add/Edit controls, optional social input, explicit **Answer this question** button and saved history. Editing replaces the selector rather than repeating it. Cancelling restores the saved selection. Follow-ups focus the editor and keep their original parent; selecting another saved question clears it. Submission is disabled during selection saves and existing request work. Existing saved answers retain their own question, citations, exports and history; adding/selecting never submits an AI request. Fictional fixtures retain their existing selector-only behavior.

All secondary views now use a common `.workspace-page` container: the same 1160px maximum and responsive gutters as the company header. Both History sections align, and My ideas/Updates, the weekly review and all-company overview inherit the same container. The old narrower History cap and separate Updates cap no longer determine these page widths.

Verification: 27 existing frontend checks, production build, formatting and syntax checks for the two updated browser fixtures pass. Browser inspection covered all four desktop sidebar combinations on History/My ideas/Updates, plus 2048/980/390/320px layouts: 24 cases, no horizontal overflow and matching header/page geometry. All-company My ideas/Updates/History/Workspace are centred too. The initial all-company assertion incorrectly compared against its deliberately hidden company header; the corrected check measures centring in the pane. Both observations are retained in the evidence. The unified editor fits 320px, keyboard focus reaches the editor on edit/follow-up, an unsaved question survives tab navigation, cancellation restores the saved question, and the add dialog opens and cancels correctly. An existing answer remains labelled with its original question while a follow-up is edited. Reload restores the saved selector; the final browser has no console errors.

Checks used a separate preview tab and existing saved answers. No AI answer was submitted or new research saved. No backend, schema or model change; the full backend suite and isolated browser fixture scripts were not rerun. Updated the README, question contract and testing guide to remove the obsolete accordion instruction. Source backup: `.local/backups/unified-question-20261008T021929Z/`. Evidence: `.local/live-tests/unified-question-layout-20261008/` contains the layout observations and desktop screenshots.

## Follow-up: watch settings and phone layout

The sentiment panel now only renders **Watch settings** and **Check against my idea** while **Watch news + social changes** is checked. Hiding preserves saved context/event preferences and the manual check focus; it does not reset monitoring configuration, change manual API prerequisites or remove saved watch/sentiment history. The nested context/event explanations use separate bodies with 12px internal and 16px section gaps. Check focus is above its select, with the action alongside on desktop and below on small screens. The local-watch explanation now acknowledges optional Telegram delivery. The longer acquisition explanation moves into **Source window & limits**; its source limits remain inspectable.

Phone styles are collected in `mobile.css`: 12px page gutters, less nested card space, 14px body copy and 12px supporting copy, more compact headings/navigation/quote metadata, stacked controls and 8px dialog gutters. Text inputs and selects remain 16px to avoid iPhone focus zoom. The redundant daily-chart refresh hint is hidden on phones; source/provider attribution remains visible. Desktop typography is retained.

Verification: the 27 existing frontend tests, production build, formatting and syntax checks for the updated watch/layout browser fixtures pass. Browser checks exercised the actual Broadcom workspace across Workspace/My ideas/Updates/History at 320, 390, 430, 600, 768 and 1440px (24 combinations), with no document or pane horizontal overflow. The 390px reasoning dialog is 374px wide with 8px margins and 16px input text. Actual watch-off state has neither settings block. No error was recorded in the final app browser.

An isolated React fixture used the real SentimentPanel and styles with authored state and local callbacks, no proxy or provider/database connection. It verified off → on → off → on visibility, retained context/event preferences, readable history controls and zero analysis actions. Expanded controls were inspected at 320/390px and desktop; fixture console was clean. This validates UI state/spacing, not supplier, model or delivery behavior. The original viewport check initially targeted the still-active fixture instead of the app tab; after opening the app as the active preview, all 24 actual-app checks passed. No backend suite or full isolated browser scripts were rerun for this frontend change. Owner watch state was off at both start and finish; no owner watch or research was modified by the test sequence.

Updated the README, current private-check UI note and testing guide to match the conditional controls. Backup: `.local/backups/watch-mobile-20261008T023124Z/`. Evidence: `.local/live-tests/watch-mobile-20261008/` (screenshots and verification JSON). The isolated preview source is retained under `.local/ui-preview/watch-mobile/`; it is ignored by Git and excluded from the production build.

## Follow-up: shared company-row highlight

The owner's screenshot showed the selected company's cross outside the green outline with a red hover. The outline and green background now belong to the complete company row; the company and cross remain separate labelled buttons. Cross hover and keyboard focus use a darker green background and pale green icon. Existing selection, sidebar removal, notice and restore behavior are unchanged. The standalone All companies button retains its existing selection styling. No change was requested for the second supplied screenshot.

Verification: all 27 existing frontend checks, production build and formatting pass. Read-only browser checks against the compiled local app confirm both buttons are inside the selected outline, the inner company button has no duplicate border, the cross hover is darker green, and Tab reaches its visible keyboard focus. Desktop and narrow desktop screenshots were visually inspected. Document and main pane have no horizontal overflow at 320/390/600/980/1024/1440/1920px; the sidebar retains its existing hidden state at 980px and below. The phone screenshot was also inspected. The browser blocked all non-GET and external requests, including one automatic company-loading POST; no removal, saved-research edit, watch change or paid action was performed. No backend suite was repeated for this presentation change.

The initial sandboxed Chrome launch failed before navigation. Two initial hover observations sampled a moving control during asynchronous layout settlement; the final check waits for loading/font settlement and confirms the pointer is over the cross. Preserve these failures with the successful observations in `.local/live-tests/sidebar-highlight-20261008/`. The final browser has no page errors or external request attempts. This verifies sidebar presentation and keyboard access, not provider or model behavior.

Review lenses: the full outline makes selection clearer; darker green hover matches the selected row; separate buttons preserve accessible actions; the change does not alter evidence interpretation; no demand or retention claim follows.

## Follow-up: shared hover, truncation and panel motion

The owner's follow-up exposed the company's inner hover background still splitting the highlighted row into two surfaces. Hover and focus now darken the whole row, with transparent inner buttons and 8px right padding beside the cross. Long symbols/company names have single-line ellipses and full-text titles. Separate labelled actions, removal/restore behavior and selected-row border remain. Visual review caught an initial `company-label` class collision with header styling; the final `company-row-label` preserves the original text appearance.

Sidebars animate their grid columns over 300ms while their contents fade and slide slightly. Fixed-width inner bodies follow the existing responsive widths, keeping text from squeezing during collapse. The phone idea panel animates its height instead. Progress and its details use the same height/fade transition; hiding/reopening preserves expanded details. Hidden contents are immediately inert and excluded from accessibility navigation. The existing keyboard progress focus transfer and local preferences remain; reduced-motion settings disable these transitions.

Verification: all 27 frontend checks, production build, formatting and browser-script syntax pass. `tests/browser_workspace_motion.cjs` checks identical whole-row hover from either button, cross inset, authored long-label overflow/ellipsis, intermediate sizes while both sidebars and progress open/close, rapid reversal, retained DOM/search input/detail state, keyboard focus, instant reduced-motion controls, both panels collapsed together, All companies and reload persistence. Document/main pane have no horizontal overflow at 320/390/600/740/768/980/1024/1440/1920/2048px; inner body widths match their fully open desktop rails. Final desktop, narrow sidebar and phone screenshots were inspected. No page errors, external requests or unmocked app writes were recorded.

The browser reads the compiled local app and its saved data, but substitutes one authored long company label and three completed loading steps in intercepted responses. Loading GET/POST requests are mocked before reaching the server; this test does not acquire sources, enable watches, edit saved research, remove a company or request AI/Telegram delivery. It establishes UI behavior, not provider/model outcomes. Backend tests were not repeated. A later check found the progress wrapper absent after a separate file update; it was reintegrated with the existing batch status text preserved. The failure and final success are retained in `.local/live-tests/workspace-motion-20261008/`, along with screenshots and animation-size observations.

Review lenses: one surface communicates one selected company; spacing/truncation keeps the cross readable; mounted controls and inert hidden content preserve state/accessibility; animation does not alter source interpretation; no commercial validation claim follows.

## Five-perspective review

These are one implementer's review lenses, not independent reviewers.

- Product: users can focus on research while retaining access to company context and their saved idea.
- UX: collapse is reversible and discoverable through labelled header controls; text and action spacing address the supplied screenshots.
- Engineering: presentation state is independent of company data, and sidebar hiding avoids remounting research controls.
- Evidence: reducing visual clutter does not suppress source limitations or change source text/analysis.
- Commercial: this improves usability for testing; it establishes no new demand, retention or sentiment accuracy evidence.
