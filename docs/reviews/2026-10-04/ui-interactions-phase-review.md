# Custom menus, company removal and stable navigation — 4 October 2026

## User request and implementation

All application dropdowns now use a shared styled HTML option list instead of the operating-system popup. The native select remains as the labelled value/form control so real bubbling changes retain approval-reset and input semantics. Mouse selection, arrow keys, Home/End, typeahead, Enter, Escape and Tab are supported. Disabled options cannot be chosen. Menus fit the viewport, flip above when needed and render inside a modal's top layer. The prominent green dropdown outline is replaced with a subtle border for keyboard focus; focus indication is retained. No new package was added.

Each company row has an always-visible Remove button. This removes the company from this browser's sidebar, with Undo and Restore in Add company. The management dialog supports removal/restoration on phones and an empty sidebar can be recovered. Adding a previously hidden company restores it. Removal does not delete research or stop monitoring; that meaning is stated at the control and in the notice. The current open research remains available if its company is hidden. Preferences persist in localStorage for this origin and are not account-wide or synced across browsers; blocked storage falls back to the current session.

The former CompanyWorkspace key included the active tab and historical record, forcing a complete unmount and workspace reload on navigation. It now depends only on company identity. The header, company rail and current-idea rail remain mounted across Workspace, My ideas, Updates and History. The research scroll resets for a new destination; explicit historical links still select the requested record. Loading placeholders replace the bare initial loading screen and the inbox/weekly-review loading text, with status announcements and reduced-motion support. Inbox filters now survive tab changes within the same company; this supersedes phase62's reset-on-re-entry behavior. Reloading or changing company still starts fresh filters.

## Verification and limits

- Production build, complete frontend formatting and 22 existing frontend checks pass.
- The disposable complete save/approve/review/history journey passes. The event journey additionally chooses an actual custom-popup option and confirms monitoring approval resets, then checks saved revision/export/history semantics. The mixed-stream inbox journey passes exact records, filters, pagination, review acknowledgement, deep links, delayed-response/outage recovery and source withholding. No live provider calls were made.
- New read-only interaction checks exercise actual mouse and keyboard menus, Escape/Tab cancellation, typeahead, subtle focus, modal option selection, a delayed inbox skeleton, stable header/grid object identity and no extra workspace fetch on tab changes. Sidebar removal, Undo, reload persistence, Restore, empty-list recovery and phone popup bounds pass in an isolated browser context.
- Nine-size layout checks pass from 320px to 2560px, including keyboard scrolling, source dialogs and expanded settings. Desktop and phone dropdown screenshots and the delayed inbox skeleton were visually inspected.
- The first new keyboard test exposed ancestor scrolling closing the menu; active-option scrolling now affects only its popup and pane scrolling repositions it. A later Escape check exposed suppression of modal dismissal when the menu was already closed; Escape is now intercepted only for an open menu. Both original failed logs are retained.
- Chrome checks do not constitute Safari or assistive-technology validation. No broad backend suite was repeated because backend/schema/model code is unchanged. This UI work is not evidence of investment accuracy or participant value.

Source/build backup: `.local/backups/phase63-ui-interactions-20261004T032733Z/`. Evidence, failures, screenshots and installation hashes: `.local/live-tests/ui-interactions-20261004T032733Z/`. Main-account browser verification is read-only; no research or watch settings are edited and no API credits are used.

## Five-perspective review

One agent applied these perspectives; these are not independent consultants or user validation.

| Perspective | Assessment |
| --- | --- |
| Product | Removing a sidebar item is reversible and separate from deleting research or changing a watch. Cross-browser preference sync remains future work. |
| UX | Consistent menus and a stable shell address the reported visual disruption. Loading has a visible shape without removing navigation. |
| Engineering | One reusable menu preserves form change semantics; tab identity no longer invalidates company data. Targeted history remounts preserve deep links. |
| Accessibility/QA | Labelled controls, keyboard navigation, subtle visible focus, status announcements and reduced motion are retained. Broader platform/accessibility testing remains open. |
| Evidence/cost | Source access, immutable saved records and paid-call boundaries remain unchanged. Zero new API spend. |
