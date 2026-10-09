# Original company research, managed login and financial visuals

9 October 2026. The owner requested completing original-document coverage, beginner business research, managed identity and broader consensus/peer data, supplied an FMP key, and subsequently requested visual fundamentals informed by Simply Wall St. This report covers functionality and the financial overview; the concurrent presentation task has its [own review](research-navigation-and-source-filters.md).

## Outcome and scope

| Requested work | Installed behavior | Actual verification / outstanding limit |
| --- | --- | --- |
| Original filings and earnings releases | Immutable canonical SEC HTML/text, dates, exact passages and bounded Exhibit 99 reading; coordinated loading step | Broadcom annual report, quarter, results 8-K and earnings release retrieved in four requests. PDF/foreign-format and exhaustive filing-history coverage remain limited. |
| Beginner business brief and financial depth | Explicit metered explanation, exact source evidence, history/export, annual revenue, trailing measures, FCF/margin and borrowing | One actual Broadcom call; 16 claims retained, two withheld. Selected developer audit and arithmetic checks only; independent beginner/semantic validation remains open. |
| Managed login | Confirmed Supabase email/PKCE identity, server-side sessions, private account scoping and owner migration | Two real verified identities: one linked to the original owner and one to a separate account. Signed-in workspace inspected. Default mail-service participant coverage and public deployment are not established. |
| Consensus and reviewed peers | Separate FMP datasets, immutable vintages, source restrictions, private selections, separately labelled existing Finnhub/SEC references | Actual profile/peers work; Broadcom consensus/TTM ratios return HTTP 402. Current subscription access blocks those live datasets. No purchase or alternate access workaround. |
| Visual fundamentals and smoother UX | Four dated figures, selectable annual revenue bars, cash-flow comparison, evidence controls and restrained transitions | Guarded browser checks at 1600/1440/980/390/320px, with missing values, negative cash flow and reduced motion. No proprietary scores or fair-value estimate imported. |

Contracts: [original company research](../../features/original-company-research.md), [managed login and recovery](../../features/managed-login.md). Migrations 042–045 are now installed after original schema 41. Applied migration checksums must remain unchanged.

## Preservation and recovery

Private pre-installation backup: `.local/backups/phase87-managed-login-20261008T170902Z/`. `before.dump` and the preserved `.env` copy are mode 0600. `candidate-source/` records the implementation candidate at installation; it is not a pristine pre-edit source checkout. Git retains the earlier committed source history. The backup preserves the original database, allowance and research rather than creating another paid installation.

The migration audit found 98 of 100 pre-existing tables exactly identical; only `sources` and `schema_migrations` changed. Thirteen new tables hold disclosure/current/lease records, business briefs, authentication and FMP/private-peer state. Existing research, watches, notification records and original ledger were exact across migration. This is a migration-point comparison, not a claim that a running monitored app never changes thereafter.

Recovery was exercised in an independent temporary PostgreSQL cluster. The original dump restored into a blank `thesis_recovery` database, and all 100 original whole-table fingerprints matched. The first attempt restored into an already migrated/seeded target with `--clean`; newer-table references prevented that approach. Its failure remains in the evidence. The corrected blank-target restoration succeeded without changing the owner database.

The owner's reported generic sign-in failure came from a frontend/backend mismatch: the new form was served while the old server still lacked `/auth/login`, returning 404. The old session endpoint also lacked the new managed-session fields. This was an installation error, not data corruption. The server was restarted after backup/migrations, and session/private API/invalid-input checks returned the expected 200/401/422 responses. Subsequent frontend candidates were staged separately to prevent another mismatch.

An earlier `SUPABASE_URL` pointed at the dashboard, not the project API. Only that `.env` field was corrected. The real dashboard had the expected loopback Site URL and `/auth/callback` redirect; email was enabled, confirmation on, anonymous off and Google off. The configured project/key settings request returned HTTP 200. Credentials and email addresses are excluded from public evidence.

For login-only recovery, `THESIS_AUTH_ENABLED=false` plus a local app restart/reload restores previous loopback owner access while retaining research and identity mapping. Controlled tests verify that switch. It is an operator recovery mode, not a public-server authentication fallback. A full old-database restore would discard later work, so prefer the login-only switch for a login problem.

Later saved-data audit confirms `theses`, `thesis_versions`, `telegram_settings`, `model_budget` and `model_budget_amendments` still match the pre-installation signatures. The whole `news_watches` table no longer matches: normal running-watch state and real account use continued. Counts remain three enabled original-owner watches and zero other enabled watches. This task did not enroll a watch, recipient or peer automatically, and did not revise private reasoning.

## Actual originals and financial inputs

The four retained Broadcom documents are:

- [Annual 10-K](https://www.sec.gov/Archives/edgar/data/1730168/000173016825000121/avgo-20251102.htm): 3,059 rendered passages.
- [Latest 10-Q](https://www.sec.gov/Archives/edgar/data/1730168/000173016826000080/avgo-20260802.htm): 1,711 passages.
- [Results 8-K](https://www.sec.gov/Archives/edgar/data/1730168/000173016826000076/avgo-20260902.htm): 50 passages.
- [Filed earnings release](https://www.sec.gov/Archives/edgar/data/1730168/000173016826000076/avgo-08022026x8kxex99.htm): 272 passages.

Original bytes, rendered words/table cells, versions and exact offsets remain saved. Business selection supplied 27 passages from three documents among the four available originals, with a 33,865-byte actual serialized model request. This is not a full-filing AI reading. The original input packet is frozen and matches the recorded call request.

Retained structured facts support a trailing fiscal interval of 4 August 2025–2 August 2026: revenue US$89.104bn, operating income US$42.814bn, operating cash flow US$40.653bn, capital spending US$1.25bn, calculated FCF US$39.403bn and operating margin about 48.04947%. Reported combined borrowing is US$61.079bn at 2 August 2026. Each bridge uses explicit annual/current-YTD/prior-YTD inputs of the same concept and compatible dates. An independent Decimal recomputation matched every available bridge, derived value, debt fact and five retained annual revenue values. Net income remains unavailable; no alternative concept was silently substituted. These checks establish arithmetic over the saved inputs, not accounting-policy or restatement comparability.

The overview keeps annual reported revenue distinct from trailing results. Every chart includes zero, retains missing-year gaps and represents negative values. Cash rows covering a different period are excluded. Bar interaction is local/read-only. Expanded values keep exact formula, dates, concepts and original filing links; omitted obligations are not treated as zero debt. The existing annual/direct-quarter reporting and monitoring definitions are unchanged.

## Actual business explanation

Six developer criteria were frozen before the call: company operations; supplier/customer/channel attribution; qualified reported drivers; liquidity/debt/liability distinctions; no invented named competitor; and exact quotations plus preservation. `business-live-criteria.json` retains them.

The original response had 18 findings. Initial numeric validation wrongly included punctuation in tokens such as `2025,`; the parser was corrected. Two driver claims still inserted a fiscal-year period absent from their own cited passages, and remain withheld. `business-evidence-filter-1` retains the other 16 without rewriting the claims or making another AI request. Original response and original failure are preserved. All 16 published evidence quotations match both selected passages and their exact original-document offsets.

The published subset meets the six selected developer criteria with limits: customer concentration statements are historical company disclosures, competition names are not established by these selected passages, and management liquidity is an attributed belief rather than an independent solvency verdict. Filing dates stay visible beside claims. This is one retrospective developer review, not independent interpretation accuracy or beginner usefulness validation. A bounded citation/number check does not establish semantic truth.

Reopening the identical source selection returned saved brief `663bc8fe-8038-4bc8-83b1-8c0317c948af`; the ledger before/after was identical. Its HTML export retained attribution, dates, quotations, limitations and withheld-claim explanations, with inert export policy. No new paid call was used for the audit/export or visualization.

## FMP live access and vintages

The key authenticated profile and stock-peers requests (HTTP 200; one profile and ten suggestions). The returned profile description included questionable/outdated business structure wording; it is excluded from AI business evidence. Profile sector/industry and vendor metadata stay labelled as vendor information.

The ratios request returned HTTP 402. The first estimates probe failed parsing a non-JSON response before its status/body was preserved; that missing diagnostic remains unknown. A later bounded integrated estimates check explicitly returned HTTP 402 requiring supported subscription/key access. Persistent `fmp:ratios` and `fmp:estimates` restrictions remain; profile and peers have separate capabilities. Five actual FMP requests are recorded. Successful saved profile/peer replies were imported with the original diagnostic timing, without refetching. First database availability and current-check timing remain distinct.

FMP suggestions are not automatically selected or labelled direct competitors. Peer selection requires private review/rationale. Saved Finnhub valuation references and registered peers' SEC measures are read separately with permission checks; they are not mixed into a uniform FMP dataset. Authored forecast tests exercise low/average/high, analyst counts, missing currency, immutable A→B→A and private-peer isolation. They do not prove live consensus availability. Automated comparable pre-release consensus-versus-actual verdicts remain future work.

An alternative information route was found on [Stock Analysis's public Broadcom forecast page](https://stockanalysis.com/stocks/avgo/forecast/), with S&P attribution, a limited fiscal-year financial forecast and adjusted EPS. Later table years remain membership-restricted. The FMP panel now offers a clearly external source link when consensus is unavailable. No figures from that page were imported, no additional Thesis collection request was sent and the existing target-page cooldown was not overridden. A future collector must have its own evidence/access contract and share that same page's pacing/cache.

## Authentication and installation

Real confirmed sign-ins now exist for two identities: original-owner mapping and separate-account mapping. A current signed-in local workspace was inspected read-only. No email was sent by this agent. Neither a successful project-settings check nor this small real-login sample proves email delivery to every future participant.

Sessions stay server-side, last at most one hour and recheck confirmed provider identity every minute. Private routes use verified internal account scope; flow/session/token tables are server-only. Login/logout/401 behavior, source-role boundaries, CSRF, expiry, replay, original-owner claim protection, private exports and two-account API/RLS isolation are tested with controlled responses. Background owners are the installation owner plus identities belonging to the configured project; historical QA users are not enrolled merely because account support is installed. Existing authorized owner watches keep running.

## Validation, failures and accounting

The final guarded backend run passed **1,418 checks / 59 optional-corpus skips**, with one existing Starlette deprecation warning. The subsequent acceptance-time label/export refinement has a focused follow-up rather than another whole-suite claim. Frontend 28 checks and the 101-module production build pass. Guarded authored browser journeys verify original evidence, saved business, private peers, sign-in UI, financial charts at five widths, negative/missing values and reduced motion. Decorative external logo responses are mocked; other browser egress is blocked. The browser runner's guard applies only to disposable processes, never the owner's app.

Initial failures remain: sandboxed PostgreSQL shared-memory setup; fixture schema/source-entitlement/expected-revision assertions; model-ledger fixture cleanup needing the new brief FK; FMP role-permission expectation and leaked refresh-state fixture; the midnight UTC-versus-session-day quota fixture; an unimported `os` in the disposable frontend override; browser asynchronous document/duplicate text selectors; and the initially uncontrolled decorative image request. The latest older-amendment guard initially expected the wrong authored filename; its identity-based assertion now passes. These are retained alongside corrected runs. No successful controlled test is represented as live source or semantic validation.

The explicit business call cost US$0.068295. The final saved audit records US$20.486704 confirmed plus US$0.9156025 historical maximum holds, US$8.5976935 remaining of the same cumulative US$30, 365 calls and no unresolved blocker. Besides the one explicit business request, five shared sentiment calls settled during normal app/watch use. Do not attribute all concurrent traffic to this task or claim no global OpenAI/Telegram activity. This task made no direct Telegram/test dispatch, added no allowance and cleared no old hold or provider denial.

Private evidence is `.local/live-tests/source-expansion-20261009/`: original captures, FMP access diagnostics, frozen business packet/response/failure/filtered result, numeric/source/cache/export audits, authentication checks, final preservation signatures and software/browser logs. Backup proof lives in the directory above. Earlier RSS, model-quality, participant-validation and deployment limitations remain open.

## Final installed check

The staged candidate was installed after verifying the new backend: managed `/session` returned 200, an unauthenticated private workspace 401 and invalid email input 422 with a useful message. New assets were copied before atomic index replacement; older assets remain for open tabs. A private frontend backup is recorded in `frontend-backup-path.txt`.

The actual signed-in Broadcom workspace survived a reload/restart and displayed its new revenue history, cash generation, dated figures and exact retained documents. The live review identified a date-label ambiguity: original acceptance timestamps were previously labelled simply “Filed”, which could disagree with the structured filing date across time zones. The UI/export now explicitly identify SEC acceptance and UTC; historical timestamps were not altered. A seven-case overlapping backend export follow-up and the final guarded browser journey passed. A subsequent display-only date-label adjustment distinguishes unavailable duration figures from instant balances; production build passes. The running app was allowed to finish its active research requests, then restarted between jobs to load the final export wording. This preserved sessions, research, enabled monitoring and settled charges.
