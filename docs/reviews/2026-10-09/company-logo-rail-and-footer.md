# Company logo rail and footer removal — 9 October 2026

The owner requested removing the entire footer, moving the left-sidebar toggle to its bottom, keeping company-logo navigation when collapsed, and using a plus-only Add button.

## Result

The workspace, loading shell and empty-workspace footer markup is removed, along with its styles. The bundled MiSans files, original license and source attribution remain in `frontend/public/fonts/`.

`CompanySidebar.jsx` owns the expanded company list and compact navigation. Its bottom action row contains a plus-only Add company button and an expand/collapse chevron. Only the list above it scrolls, so both controls stay at the sidebar's bottom. The top bar retains the Workspace-only idea-sidebar control.

On desktop, collapsing narrows the company sidebar to 64px. Company logos remain clickable and keyboard accessible, with full symbol/name labels and hover titles. An All companies grid icon clears the selection. Search, names, cross buttons and unread dots are hidden in compact mode; the search region is inert and excluded from assistive technology. Every visible saved company remains in the rail even if an earlier expanded search filtered the list. Expanding restores the saved search and full controls. Existing removed-company filtering and restore behavior are preserved.

The same plus-only action is used beside the narrow-screen company picker. At 980px and below the existing picker replaces the sidebar. The browser's existing sidebar preference persists across navigation and reloads; its old `companiesHidden` storage key now represents compact mode on desktop. Width and browse-region transitions retain the existing 300ms duration and reduced-motion behavior. Company logo sources and fallback behavior are unchanged.

## Verification

All 27 frontend tests, the production build and targeted formatting pass. No backend suite was repeated for this frontend change.

The updated `tests/browser_workspace_motion.cjs` passes: real-logo navigation while compact (including keyboard selection), plus-only Add dialog, footer removal in the normal and empty workspace, bottom controls while a thirty-company authored list scrolls, responsive sidebar body widths, animation interpolation/reversal, retained sidebar/search state, progress keyboard focus and retained details, reduced motion and reload persistence. Ten widths from 320 to 2048px have no document/main overflow; four desktop widths also verify the compact rail. The controls stayed 12px above the viewport/sidebar bottom while the list scrolled 1,734px in the authored long-list case.

`tests/browser_workspace_panels.cjs` also passes, retaining three actual bundled-logo checks, the controlled missing-logo fallback, fictional-company exclusion and Workspace-only right sidebar. Its 32 tab/width checks also assert there is no footer. Desktop, compact, phone and long-list screenshots were inspected.

Both browser journeys intercept loading, block application writes and abort external requests. Directory, long-name, long-list and empty-workspace cases are authored browser fixtures. No company was actually added/removed, source refresh submitted, model call requested or Telegram message sent by these checks. The app was not restarted; the compiled frontend is available on refresh. No database, schema, provider or monitoring settings were changed by this task.

Evidence is in `.local/live-tests/company-rail-20261009/`. Preserve `browser-initial.log`: the first expanded journey wrongly required a company-scoped progress element to survive selecting another company. The corrected test verifies retained sidebar/search nodes across selection and pins the new company's progress element before testing collapse/restore. Final passing evidence remains separate from that initial failure.
