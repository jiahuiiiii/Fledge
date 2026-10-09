# Company report navigation and source filters — 9 October 2026

The owner requested platform icons and a combined source filter, then explicitly confirmed inspecting Simply Wall St in Chrome and improving Thesis's UI while another agent handles functionality.

## Presentation changes

- A clearer company header and a shared quote/chart surface. When its actual available width is at least 800px, quote and chart sit side by side; narrower columns stack them. Dates, source details, chart controls and quality notices remain available.
- The existing six research tabs now have icons and plain section introductions. At 1600px and above, they form a sticky vertical menu. Smaller desktop layouts use a sticky horizontal menu; phones retain a naturally scrolling menu. Arrow keys follow the visible orientation; Home/End and existing panel IDs remain intact.
- The Research question card sits inside Evidence radar, using the same selector, Add/Edit, explicit answer action and history. Its draft and selection remain mounted when switching research sections. No new question accordion or automatic analysis was added.
- Cards, source reading controls and spacing share a consistent visual hierarchy. Source collection/connection details sit below the saved reading. Warnings about stale/withheld readings and provider failures remain visible or under their existing labelled disclosures.
- Source filters use locally bundled news/Reddit/Hacker News/X icons with hover/accessibility names and 44px targets. **All** is the default in saved AI interpretation, saved Original sources and the current-source preview. News/social texts appear together newest first, retaining source attribution and feed-update timestamp meaning. Comparison-only news is excluded from selected original texts; unrelated selected texts remain.
- All keeps AI tone/count summaries separate by source platform. No pooled percentage, consensus or new analytical score was introduced. Original sources show original bodies without borrowed AI labels. Current inputs still use their independent permitted-source selection, including when a saved packet is withheld. Saved themes can be browsed together with their original source scope.

Geometry remains in `workspace-layout.css`; the shared research width applies to the report frame, with its wide section menu inset beside the reading column. Component appearance is in `research-design.css` and `source-filters.css`. Existing company/logo rail, sidebar availability, browser preferences, animations and reduced-motion support remain.

The concurrent account gate initially exposed a missing `signOut` prop that prevented rendering. Passing the already-existing control through the workspace fixed the UI connection. Authentication, acquisition, paid requests, data selection, provider settings, watches, notifications, schema and the other agent's business/disclosure logic were not changed by this task. No owner database write, migration or server restart was performed.

## Reference and assets

The [Simply Wall St Mastercard report](https://simplywall.st/stocks/us/diversified-financials/nyse-ma/mastercard) overview and Valuation section were inspected in the owner's Chrome. Company context, focused navigation and reading hierarchy informed the layout. Its code, data, financial scores, charts, text and branded visualizations were not copied. The first browser request was rejected because the goal update was treated as untrusted context; the owner's subsequent explicit confirmation allowed inspection.

[Icon sources, hashes and terms](../../../frontend/src/assets/source-icons/SOURCES.md) retain the original Simple Icons Reddit/X vectors and CC0 license, and the official Hacker News masthead. The initial Simple Icons HN lookup returned 404; the official asset returned 200. No runtime icon dependency was added.

## Verification and limits

- 28 frontend checks and production build pass. Targeted formatting, browser-script syntax and whitespace checks pass.
- `tests/browser_research_design.cjs`, run with `tests/run_browser.py --research-design`, verifies all six sections at 1920/1600/1440/1024/768/390/320px: 42 section/width layouts without document/main overflow, 44px tab targets, orientation-aware keyboard navigation, sticky wide navigation, retained question draft and eight expanded/compact/hidden sidebar combinations at 1440/1920px. Authored Microsoft source/price fixtures are seeded only into the disposable offline database.
- The source-filter journey first passed against the owner's saved 16-source AVGO reading, with loading intercepted and writes/external traffic blocked. After concurrent authentication work made the old running server unsuitable for the new frontend, final UI verification used the normal isolated local test session. `--source-filters` checks a saved authored news/Reddit reading and four-platform browser-only fixtures: exact combined ordering, original bodies, each individual filter, keyboard/tooltips, current preview, scoped themes, withheld/no-analysis states and six widths in both reading views. X cases are authored UI fixtures, not evidence of an enabled/live X connection.
- The existing `--sentiment-inputs` journey passes after adapting its source selection to the new icon controls and explicitly intercepting first-open loading and unavailable logo responses. It checks current-versus-saved selection, source/parent inspection, empty/first-reading states, reload and 320/390/1440px layouts.
- Desktop/phone screenshots were inspected. UI changes are compiled; applying the concurrent authentication/backend work to the owner's running server remains that work's responsibility. No whole-app/backend or live provider/model quality claim follows from these presentation checks.

Evidence is retained in `.local/live-tests/research-design-20261009/` and `.local/live-tests/sentiment-source-filters-20261009/`. Initial failures include the missing sign-out prop, a sticky-position test that scrolled insufficiently, the existing journey's loading-write assertion and a formatting invocation from the wrong working directory. Automatic review rejected a proposed browser-only session adaptation because it would fabricate authentication; it was removed and never executed. Final tests use the app's ordinary disposable local test session. All failed logs are retained.
