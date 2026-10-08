# Stable view transitions — 4 October 2026

## Problem and correction

The user reported that blinking remained after the skeleton pass. The earlier checks proved skeleton presence and shell DOM identity; they did not prove visual stability at normal local response speeds or on repeated tab entry. Reproduction showed a workspace placeholder followed by a separate short-lived chart placeholder, then the chart. Returning to Workspace recreated its chart. Updates hid the shared company/status/idea regions and changed the column widths, so unchanged content shifted too.

Company loading now reads its workspace, model availability, saved daily chart and the selected Expectations/Valuation subsection before one reveal. These are local saved-data reads, not supplier/model requests. Chart or subsection errors become scoped errors and do not leave the entire workspace loading. A cold successful read keeps its placeholder visible for at least 280ms; already-loaded/background reads and rejected requests have no added delay. This supersedes phase65's no-minimum-duration design. Scope tokens still fence A → B → A and late saves; old-company actions/data are withheld immediately.

Workspace and visited research subsections remain mounted between tabs for the selected company. The chart retains its time range and does not show another skeleton on return. Its width is measured before paint; a hidden panel's zero width cannot overwrite the last geometry. Updates and all-company History also retain loaded results while local reads revalidate on return. Filter/scope changes still withhold mismatched results; read failures remain explicit. Retained views are hidden from layout/accessibility when inactive and discarded on company changes; this is not a shared cross-company or persistent data cache. Unsaved valuation input can now survive subsection navigation within the same company.

Updates keeps the same company header, status strip, company selector, sidebar, idea panel and column geometry as the other selected-company tabs. All-company views retain their explicit aggregate layout. Skeletons include quote space and remain static. Cold weekly/aggregate reviews and first visits to Expectations/Valuation use readable loading duration too. The removal-banner animation remains unchanged.

## Verification

- Production build, complete frontend formatting and all 22 existing frontend checks pass.
- The revised loading journey holds chart and company reads, checks a single workspace reveal, retains the exact chart DOM/range and inbox DOM, and compares shared frame positions across all four tabs. It covers late responses/saves, failed workspace retry, a failed chart read and phone switching without server writes (one locally authored intercepted save).
- Shared company scope, existing menu/removal interactions and nine viewport sizes from 320 to 2560px pass. Desktop/phone skeleton screens were inspected.
- Disposable core save/approve/review/history, mixed-stream inbox, daily-price, valuation and weekly-review browser journeys pass. They exercise existing mutations only in isolated fictional data. Main-account browser checks are read-only.
- Normal-speed frame traces retain both the original multi-step loading sequence and the new single-reveal sequence; returning to Workspace keeps its chart with no chart skeleton. The earlier baseline trace recorder allowed old loops to continue; a corrected recording is retained separately.
- One intermediate browser check exposed a remaining delayed Valuation placeholder after company loading. The selected research subsection is now included in the initial read bundle and the check passes. The initial JSX restructuring syntax error was caught before preview/build and corrected. Preserve those diagnostics with the final passes.

The installed app on port 8841 passes the final stable-transition and shared-company-scope journeys. Installed source/build match the checked version, and installed screenshots and logs are retained with the evidence. These checks cover Chrome behavior, not full Safari/assistive-technology validation or user acceptance. Prior claims that phase65 alone ended all blinking were too broad.

No backend, schema, provider, prompt or data changes; no source/model calls or API spend. Existing research/watch settings and broader implementation/semantic-quality gaps remain unchanged.

Evidence: `.local/live-tests/stable-transitions-20261004T054316Z/`. Backup: `.local/backups/phase67-stable-transitions-20261004T054316Z/`.

## Five-perspective review

One agent applied these perspectives, not independent consultants.

| Perspective | Assessment |
| --- | --- |
| Product | Tab revisits retain the user's current chart and research work; loading does not imply new market retrieval. |
| UX | One cold-load reveal replaces the visible cascade; unchanged columns stay stationary. Minimum placeholder duration addresses single-frame flashes. |
| Engineering | Retention is scoped to the current company, late completions stay fenced and partial read failures terminate correctly. |
| Accessibility/QA | Hidden panels are excluded from navigation/accessibility; static skeletons and readable controls remain. Normal-speed and delayed reads are checked separately. |
| Evidence/cost | Existing access checks, exact revisions and visible source dates remain. No cached response crosses company scope and no paid requests are introduced. |
