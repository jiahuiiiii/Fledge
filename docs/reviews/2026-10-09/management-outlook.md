# Original management outlook — phase 91

9 October 2026. The original four-part expansion includes source-backed company research and dated expectations. This phase adds a bounded original-release outlook view; it does not complete the full roadmap or establish full analyst-consensus access.

## Installed behavior

**Management outlook** in Fundamentals shows retained original release sections, explicit release datelines, target-period dates, approximate points/ranges, accounting basis and exact source context. It distinguishes the company's expectations from reported results and analyst forecasts. The view is read-only, uses `sec-management-outlook-1`, and makes no model or source request. No migration, existing method/prompt revision, paid stage, watch, private condition or notification is added.

The prose reader supports selected short outlook headings and bounded following passages. It does not derive values from table layout, a nearby reported result or a segment forecast. Dollar-only currency and absent accounting basis remain unknown. Complex ranges, conflicting fiscal labels, original-source status requiring review and unsupported prose are not coerced into comparable forecasts. The full section/disclaimer remains inspectable within the stated bound.

Release selection retains original document IDs and first availability. Current exhibits must match the current results filing; historical versions are labelled accordingly. Scope is at most 20 release versions. Comparison inspects at most 100 reporting periods, after selecting the earliest retained non-amended result/snapshot for each period. It requires explicit GAAP USD revenue, matching quarter/annual period and end date, compatible duration and original input identity. The forecast must have been filed and saved before period end. Later retained corrections do not replace the first matched result. No missing or non-GAAP value is compared against GAAP as if equivalent.

Comparisons expose source IDs, exact amounts and the current method. They are current projections over immutable inputs, not saved retrospective assessments: adding earlier evidence may change what is available. Filed results can follow the earnings announcement. Approximate point estimates produce a difference without an invented beat/miss tolerance. No general forecast-accuracy claim follows from authored cases.

The interface uses a date timeline and two-column amount cards, with a single-column phone layout. Local history selection is keyboard-accessible, source content is escaped, the entry transition respects reduced motion, and lazy loading keeps this view out of the initial application bundle. Original release/structured-fact withdrawal remains enforced independently.

## Actual retained source check

No fresh source request was made. The existing Broadcom release `1108460d-ff22-59bd-8466-be73d865659f`, accession `0001730168-26-000076`, supplies:

| Field | Retained source meaning |
| --- | --- |
| Release dateline | 2 September 2026, explicitly in passage p15 |
| SEC acceptance | 2 September 2026 at 20:26:04 UTC; different from a verified announcement timestamp |
| First saved | 8 October 2026 at 17:16:41 UTC |
| Target period | Fourth fiscal quarter, ending 1 November 2026; p40–p41 |
| Revenue outlook | Approximately $34.8 billion; p42. Dollar currency and accounting basis are not silently completed |
| Operating income outlook | Approximately 66% of projected revenue, explicitly non-GAAP; p43 |
| Context | The complete following estimate/reconciliation disclaimer, p44 |

The source is the [original filed earnings release](https://www.sec.gov/Archives/edgar/data/1730168/000173016826000076/avgo-08022026x8kxex99.htm). The view does not report a comparable actual result: its period has not ended, and currency/basis or non-GAAP scope also prevent an automatic comparison. Selecting an old source does not relabel it current.

## Verification and failures

The first focused run had **73 passes and one fixture failure**: its synthetic ingestion cutoff predated company registration. Using the actual disposable test clock corrected it without weakening the source-progress guard. The corrected focused run passed **75** cases. The full isolated backend run passed **1,502**, with **66 optional skips**. A later overlapping 33-case run checked the retained actual release and an additional later-correction scenario inside the history case. Final overlapping source/account-scope checks passed **61** after refining non-revenue missing-data explanations. These are separate runs, not additive coverage counts. The final reason-text change did not repeat the entire backend suite.

All **28 frontend tests**, production build and targeted formatting pass. The guarded business journey passes, including outlook at **1440/980/390/320px**, history, exact source context, a synthetic compatible annual comparison, missing currency/basis, withdrawn source, keyboard controls, reduced motion and headline figure size. Existing business/peer/source/financial/login paths also pass. Desktop and 320px screenshots were visually inspected. They use authored Microsoft-shaped data, not actual Microsoft results; no signed-in main-browser visual claim is made.

The first browser attempt failed because the old test expected one source-document button after the fixture gained additional releases. The corrected selector passed. A later explicit typography assertion found that the phone paragraph rule still overrode the new headline figure; the scoped component rule fixed it and the final run passes. The initial bundle crossed the 500 kB warning threshold; lazy loading reduced the entry bundle to 499.15 kB. Original failed and successful logs remain in the evidence folder.

Read-only operational checks also preserve their initial failures: a guessed `market_references` table from the preliminary peer audit, a guessed `source_request_clocks` table in restart preflight, and a sandbox-denied process inspection. The corrected reads used verified repository table names and process access. The first manual invalid-email request omitted the existing local-request header and correctly received 403. The corrected request, matching the normal client header, received 422. No protection was removed and no email was sent. The first documentation checker mishandled an existing angle-wrapped absolute PDF path; repository-relative link checks then passed, with that original personal-file reference preserved. These were inspection/test invocation failures, not evidence of source access or a new login regression.

## Installation and preservation

Backup `.local/backups/phase91-management-outlook/` retains prior touched integration files, documentation and installed frontend. This read-only feature does not need a new schema/data restore. The existing phase87 full-database restore rehearsal remains the separate recovery evidence; the login-only rollback remains documented in [managed login](../../features/managed-login.md#recovery).

Before restarting, every table with a lease field had zero live leases and the original ledger had no running/attention/unresolved call. The verified Thesis server process stopped gracefully; the database stayed running. The new backend and original saved outlook were verified before atomic frontend index replacement. Previous assets remain available for already-open tabs. Installed index hash: `d749a1303be15deec925580afc9439432b16b4187d44e81a7b5bc2acced4b81a`.

Post-install checks: managed session endpoint works, expired/absent session stays signed out, private workspace rejects unauthenticated access with 401, and invalid email receives 422 before any email send. No fresh user sign-in was performed in this phase; earlier successful real sign-ins remain separate evidence.

All **114 table fingerprints are identical** across the measured read/install interval, schema remains 46, three owner watches and zero other watches remain enabled. Original private research, source denials, provider clocks, account mappings, notifications and cumulative allowance are preserved. The feature made no AI/Telegram call. Ledger is unchanged: **US$20.850354 confirmed + US$0.9156025 historical holds**, **US$8.2340435 available** of the original US$30, 369 calls and zero blockers.

Evidence: `.local/live-tests/management-outlook-20261009/`, including retained original release, extraction, before/after fingerprints, tests, authored screenshots, restart preflight and installed-projection/bundle checks. Alpha Vantage's existing shared cooldown remains exact until **9 October 13:00:28 SGT**. No owner-key forecast request or pause override was made. FMP restricted access, full quarterly/multi-year consensus, broader guidance formats/comparability and independent participant validation remain open. The original four-part goal remains active.
