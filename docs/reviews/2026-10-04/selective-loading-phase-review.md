# Selective loading — 4 October 2026

## Implementation

The user requested skeletons only for components that change and take time to load, with the header and company sidebar kept in place. The CompanyWorkspace now survives both primary-tab and company changes. Its existing catalogue keeps the sidebar usable, while the selected company's identity updates immediately and its old research/idea content is withheld until the matching response arrives. The desktop columns and footer remain mounted. This supersedes phase63/64's company-keyed remount behavior.

A distinct selection token fences workspace reads and action completions, including A → B → A navigation. Slow reads cannot put one company's figures under another ticker. A save already submitted belongs to its original company; its late completion cannot close a different company's editor or replace its draft. Company-specific dialogs, errors and pending state reset on selection changes, while company search and sidebar visibility preferences remain. Workspace subsection selection persists across companies.

Shared static skeleton variants reserve chart, research-card and saved-idea space. Daily prices, expectations, valuation, discussion themes, sentiment history/comparisons, initial watch-check history, filing checks and saved weekly-review lists use local placeholders. Existing Updates and current weekly-review skeletons inherit the same static styling. Already-loaded lists remain visible during pagination/refresh. Cold first-load navigation still needs its initial placeholder; subsequent stock switches never replace the header or sidebar with skeletons.

Placeholders expose loading status to assistive technology without announcing decorative shapes. A failed company read replaces its skeleton with a retry state, and does not expose another company's actions. No artificial delay, paid/source polling, frontend dependency or backend/schema change is introduced.

## Verification

- Production build, complete frontend formatting and all 22 existing frontend checks pass.
- A dedicated read-only browser journey delays company, chart, expectations and valuation responses. It checks persistent header/sidebar/grid DOM identity, plot height, scoped loading, A → B → A late-response handling, unavailable/retry behavior and phone geometry.
- A browser-intercepted authored save response checks late completion after using browser Back to switch stocks and opening a different editor. No save is forwarded to the installed API. All other non-GET and external requests are blocked in this journey.
- Shared company-scope and nine-viewport layout checks pass, covering 320, 390, 740, 800, 1024, 1280, 1440, 1920 and 2560px widths. Desktop and phone skeleton screenshots were inspected.
- Disposable fictional core save/approve/review/history, mixed-stream inbox, daily-price, valuation/save/export and scheduled-weekly-review journeys pass. Their isolated data does not modify saved main-account research.
- The initial loading check attempted to locate a desktop-hidden quick-save button by visible role; it now inspects the existing control's disabled state. The original core check treated an immediately updated company heading as proof that data was ready; it now awaits the workspace loading state. One Chrome launch timed out before application testing and the later run passed. The first delayed-save test tried a company button while saving intentionally disables it; the final check uses browser Back, which can still change scope. Preserve these failed logs separately from final successes.

Installed-app selective-loading and shared-company-scope checks pass against port 8841. They use isolated browser preferences, block external/API writes and simulate the single delayed save entirely inside the browser. Installed source/build hashes match staging; the backend and migrations remain byte-for-byte unchanged. Chrome checks do not establish Safari or full assistive-technology coverage. This is UI/loading verification, not financial-model accuracy or participant validation. Existing pricing-reference design remains unimplemented.

No source/model requests or new API spending. Backend source and migrations match the installed version. No main-account research/watch settings are edited. Existing broad implementation and semantic-quality gaps remain open.

Evidence: `.local/live-tests/selective-loading-20261004T050728Z/`. Source/build backup: `.local/backups/phase65-selective-loading-20261004T050728Z/`.

## Five-perspective review

One agent applied these perspectives, not independent consultants.

| Perspective | Assessment |
| --- | --- |
| Product | The loading state makes delayed research visible without disrupting company selection or navigation. |
| UX | Static shapes hold the chart and research space; persistent navigation reduces the reported blinking. Existing loaded lists stay visible on refresh. |
| Engineering | Selection tokens protect retained component state from late reads and saves; errors terminate loading and allow explicit retry. |
| Accessibility/QA | Busy/status semantics accompany decorative placeholders; keyboard navigation and desktop/phone geometry remain operable. Full screen-reader validation is still open. |
| Evidence/cost | Old company data is withheld during a new selection. Existing source, revision and spending contracts remain unchanged; testing needs no paid calls. |
