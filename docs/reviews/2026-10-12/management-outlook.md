# Management revenue outlook — 12 October 2026

The owner requested general release collection, prose/table guidance support, truthful missing reasons and verification of all nine saved companies. The earlier audit found one usable outlook out of nine: three missing linked releases, four unsupported formats and Apple's release without numerical revenue guidance. The financial-history extraction path is separate.

## Changes and source evidence

- `guidance_formats.py` implements general sentence/range/table grammar, decimal plus/minus arithmetic, fiscal labels and explicit scope/currency/column guards. There are no issuer-specific extraction branches.
- `guidance.py` preserves exact original passages, resolves a unique dated same-release reconciliation, retains comparison rules and returns specific availability reasons. Unsupported/ambiguous values remain unknown. Current releases must still match their retained parent results filing; source withdrawal hides results.
- Overview/Outlook display named fiscal periods without guessing dates, historical guidance, specific missing reasons and original range/date evidence. Chart dates/currency controls stay strict; truncated or conflicting guidance is excluded.
- A one-time normal source collection reused retained originals and fetched four explicitly linked SEC exhibits for AMD, INTU and NVDA (including AMD's results presentation). The same row-based Exhibit 99 discovery operates during normal Update data. Do not rerun `collect.py`.

Evidence: `.local/live-tests/management-outlook-20261012/`; backup `.local/backups/management-outlook-20261012/`. Original pre-collection audit: `.local/live-tests/management-outlook-audit-20261012/`.

| Company | Revenue guidance retained after extraction | Period / result |
|---|---|---|
| AAPL | None in saved release | Explicit no-numerical-outlook-in-this-release reason |
| AMD | $12.7–13.3bn | Q3 2026; exact date not stated |
| AVGO | Approximately $34.8bn | Quarter ending 1 November 2026 |
| FN | $1.375–1.425bn | Quarter ended 25 September 2026; historical |
| INTU | $23.279–23.512bn; $4.294–4.313bn | Year ending 31 July 2027; quarter ending 31 October 2026 |
| MRVL | $2.9925–3.3075bn | Quarter ending 31 October 2026 |
| MU | $60–63bn | Q1 FY2027; exact date not stated |
| NVDA | $105.84–110.16bn | Q3 FY2027; exact date not stated |
| QCOM | $9.7–10.5bn | Q4 FY2026; exact date not stated |

A dollar sign alone remains unspecified currency; this table does not assert USD. Original forecasts, midpoint/plus-minus wording, attribution, publication/availability times and conditions remain in the evidence. Apple's earnings call was not collected, so no claim is made about guidance outside the saved release.

## Validation and operational notes

Initial 33 prior outlook tests passed; expanded extraction tests include all nine retained companies, invented issuers/layouts, exact quoted offsets, segment/other-issuer rejection, reversed/mixed-currency ranges, multi-period ambiguity, expired/unsupported/permission states and Exhibit 99 row discovery. Final focused suite: 69 passed. Frontend: 148 passed and candidate build passed. Full offline suite and candidate/installed browser results are recorded below after completion.

Collection changed the expected original-document/current-pointer/refresh/clock tables. Separate concurrent app AI/watch work changed model_calls, model_dispatches, news_watches, sentiment_analyses, watch_check_results and watch_seen_sources during collection. This task made no AI call. Do not claim all tables/accounting unchanged across collection. A separate app restart occurred during browser preparation; its PID changed 57871→85624 and reset one pending browser valuation read. Nothing was interrupted by this task.

Preserve the initial pre-dispatch active-AI guard failure, short authored-fixture failure, guessed test filename, heading-selector timeout, wrong-working-directory diagnostics and browser connection reset. Browser logs with request headers are mode 600; subsequent route failures are logged without cookies/headers. All browser writes and nonlocal requests are blocked.

The complete offline run finished with 1,933 passed, 93 optional skips and one unrelated failure: `test_full_plan_insufficient_budget_stops_before_dispatch`. The pre-existing working-tree sentiment batching change removes whole-plan preflight, while that test still expects it. A temporary access-mock diagnostic confirmed the policy mismatch; the test was restored byte-for-byte. No sentiment/budget production or test changes belong to this outlook task. Final focused outlook/currency guards passed 69 tests; the full run had loaded the earlier parser revision before the last currency/reason safeguards. Candidate browser passed 15 cases (all nine companies plus INTU/NVDA/AAPL at 390/320), exact ranges/source quotations, derived-date evidence, focus return, explanations and no page errors/overflow. Desktop INTU and phone NVDA screenshots inspected.

Final focused outlook plus original-disclosure suite: **93 passed**. Frontend **148 passed**, clean build/diff and syntax checks. All final candidate source/assets were fingerprinted after the 15-case browser pass. The temporary unrelated test diagnostic was restored; the existing whole-plan-budget policy/test mismatch remains recorded rather than hidden.

Installation status at 01:00 SGT: **not installed yet**. The idle watcher reached zero active loads/calls after batch 22 and invoked the installer, which stopped before any mutation because page-loading edits changed service.py/app.py and related runtime files after our verification. The candidate bundle remains frozen at `.local/live-tests/management-outlook-20261012/dist/`; its outlook UI and parser have passed the 15-case/93-focused checks. All outlook source changes remain in the shared working tree. No restart or frontend swap by this task has occurred. The final broad run excludes only the documented unrelated sentiment-budget test. Combined installation must preserve the concurrent page-loading changes and reverify the combined bundle; installed outlook browser verification remains outstanding.

Final broad verification completed: **1,934 passed, 93 optional skips, 1 explicitly deselected** (the unchanged sentiment whole-plan preflight test described above), 255.65 seconds. Initial full-suite failure remains retained. No tests were removed or weakened in the repository.

Combined candidate verification also passed **15 cases** against the real API at port 8842 and `.local/live-tests/page-loading-20261012/candidate/` (no injected outlook response). All nine release arrays, methods and availability reasons equal the verified extraction output; exact range/date quotations, SEC links, historical/missing explanations, keyboard focus and 390/320 layouts pass with zero page errors/overflow. Evidence is `combined-candidate-browser.json` and matching screenshots. This confirms compatibility with the concurrent page-loading candidate; installed verification is still pending.

The concurrent page-loading task's final combined backend run now passes **1,949 tests with 93 optional skips**, and its final candidate outlook run also passes the same 15 cases. It updated the unrelated sentiment-budget test for the separately authorized per-request policy; this task did not alter that policy. The earlier failure/exclusion above remains the historical record of our initial runs. Combined source and asset fingerprints are in `.local/live-tests/page-loading-20261012/verified-source-hashes.json` and `candidate-hashes.json`.

## Final installed verification

The page-loading task installed the combined build after the active watch completed: app PID85624→1424, frontend index `4e9ff62d37341fd2a1e0ca07256bfb8366d98ea4adc23c15ed505463744fc4dc`, all57assets verified and older assets retained. Its installation report confirms the worker advisory lock, unchanged116tables/schema49/environment/ledger across installation and no database restart. All six outlook runtime files exactly match this task's verified fingerprints and the combined manifest. No duplicate restart or frontend installation was performed by this task. Final combined frontend tests154pass.

Independent installed outlook verification passed **15 cases** against the real app at8841, without injecting outlook responses: all nine companies plus INTU/NVDA/AAPL at390/320px. Methods, release arrays and availability reasons exactly match the verified original-data projection; every extracted revenue range, original quote and SEC evidence link passes. INTU/MRVL same-release date evidence, FN historical status, AAPL saved-release absence, named-period disclosures, keyboard activation/Escape focus return and no page errors/overflow all pass. `installed-browser.json`, `installed-browser.log` and `verify-wait.log` record completion. Installed INTU desktop and AAPL/NVDA phone screenshots inspected. Browser writes and nonlocal requests were blocked; no source, AI or watch action was triggered by verification.


Combined installation completed by the page-loading task: app85624→1424, frontendindex4e9ff62d/all57assets verified, worker lock confirmed, all116tables/schema49/.env/ledger exact across install. The final combined offline suite passes1,949tests/93optional skips, including the corrected per-request sentiment-budget contract;154frontendchecks pass. Installed all-nine-company and phone outlook/evidence/focus browser checks pass15cases with blocked writes/nonlocal requests. Evidence and final source manifest are in `.local/live-tests/page-loading-20261012/`; see [loading review](page-loading.md). The earlier standalone installation guard failure remains preserved.
