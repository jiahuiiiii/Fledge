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

## Five-perspective review

These are one implementer's review lenses, not independent reviewers.

- Product: users can focus on research while retaining access to company context and their saved idea.
- UX: collapse is reversible and discoverable through labelled header controls; text and action spacing address the supplied screenshots.
- Engineering: presentation state is independent of company data, and sidebar hiding avoids remounting research controls.
- Evidence: reducing visual clutter does not suppress source limitations or change source text/analysis.
- Commercial: this improves usability for testing; it establishes no new demand, retention or sentiment accuracy evidence.
