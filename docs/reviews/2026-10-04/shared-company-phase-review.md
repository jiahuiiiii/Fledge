# Shared company selection — 4 October 2026

## Implementation

The selected company now belongs to the root navigation state and URL. Sidebar and mobile selectors keep the current tab; the Updates dropdown changes that same selection. Workspace, My ideas, Updates and History inherit it, as does the current weekly review. My ideas filters its cards, company History retains its own exact records, and Updates preserves review-status selection while company changes reset pagination/cutoff. Explicit links may still intentionally open another view or a saved record.

No selection, or **All companies**, produces a company overview in Workspace, all saved ideas, an unfiltered inbox, and an all-company history index. The app no longer silently selects the last preferred/sample company on landing. The index combines saved definitions, numerical assessments, event checks and private evidence comparisons from the existing owner/source-scoped local reads, newest first; exact record links lead to the matching company history. Private relevance checks retain their existing history section. Partial read failures name the affected company and allow retry. This bounded MVP index has no server pagination and should be replaced with a dedicated paginated index before materially expanding the catalogue.

Company-only workspace keys still preserve shell/data across tabs. Company changes use the existing skeleton loading frame. Removing a sidebar item preserves open research and selected scope; it does not clear selection or change monitoring. Browser-local sidebar preferences and the phase63 custom menus remain intact.

## Verification

- Production build, complete frontend formatting and 22 existing frontend checks pass.
- The new read-only scope journey checks AAPL/GOOGL through all four tabs, sidebar/dropdown/URL synchronization, selected and all-company ideas/history, exact history links, clearing selection, reload and phone selectors.
- Installed-app scope and custom-menu/removal checks pass with isolated browser preferences and no API writes. An authored one-company history outage preserves other results, names the failed company and recovers on retry.
- The phase63 custom-menu/removal/stable-tab checks pass with the shared state. Nine-size layout verification passes at 320–2560px.
- The disposable core save/approve/review/history journey, mixed-stream inbox journey and weekly-review/export journey pass. Their historical expectations were updated to explicitly select a company or All companies under the new contract.
- The initial scope test checked all-company cards before loading finished; the wait now follows the rendered scope. The initial core check still expected two idea cards while Aurora was selected; it now expects only Aurora and explicitly selects Northstar for subsequent updates. The weekly-review journey exposed a remaining old local-state shortcut; it now updates shared selection. Original failures are retained.
- Desktop all-history and phone all-idea screens were visually inspected. An initial footer inherited the hidden sample's fictional-only label; all-company views now disclose the mixed company/sample scope. Chrome checks do not establish Safari or assistive-technology coverage.

No backend/schema/model change and no paid model calls. One Finnhub analyst-target access probe returned 403 and acquired no targets; it advanced only the existing request pacing clock. Main browser checks are read-only. Existing research/watch settings are preserved. [Price-reference design](../../archive/planning/price-reference-design.md) records the separate requested feature investigation and its unimplemented status.

Evidence: `.local/live-tests/shared-company-20261004T035151Z/`. Source/build backup: `.local/backups/phase64-shared-company-20261004T035151Z/`.

## Five-perspective review

One agent applied these perspectives, not independent consultants.

| Perspective | Assessment |
| --- | --- |
| Product | One company context follows the user's work; All companies is explicit and recoverable. |
| UX | Sidebar selection stays in the active tab, preventing the reported unexpected return to Workspace. |
| Engineering | Root state and URL are canonical; list filters derive from them and old asynchronous company reads cannot replace a new component's state. The small all-history index reuses scoped reads without a new backend contract. |
| Accessibility/QA | Custom keyboard menus and narrow-screen selectors remain operable; history links retain exact company/record identity. |
| Evidence/cost | Saved records are read through existing access checks. Analyst consensus and formula scenarios remain separate in the proposed feature; denied target access is not replaced with invented data. |
