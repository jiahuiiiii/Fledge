# Thesis — real-case implementation and purpose review

2 October 2026, Singapore. Local pitch MVP in `Documents/GitHub/Thesis`.

The core demonstration is company research → saved reasoning → exact evidence comparison → retained review history. It now uses actual Microsoft, Apple and Alphabet filing, quote and news data. The wider product plan remains a roadmap: this is not a complete valuation platform, autonomous investment adviser or production launch.

## What was checked against the intended purpose

| Stage | Intended purpose | Implemented and tested | Assessment |
| --- | --- | --- | --- |
| Reuse and foundations | Build on the team's existing work without inheriting the old database | Kestrel frontend/API/evaluation patterns and Deus evidence/acquisition concepts; recorded provenance; one new PostgreSQL migration history | Working bounded adaptation; not the complete upstream feature set |
| Persistence | Keep an investor's original reasoning and evidence trustworthy | Atomic revisions, approval separate from saving, immutable sources/assessments, restricted roles and private comparisons, backup/restore, concurrent edits and delayed results | Functional checks pass; one local account is not production authentication |
| Research | Understand the company before deciding what to believe | Three real-company workspaces, source-linked snippets and shared briefing, reported/interpretation/uncertainty filters, inspectable sources | Useful entry point; no exhaustive search, consensus dataset or question-specific research claim |
| Fundamentals | Ground the story in comparable reported performance | SEC revenue growth and operating margin, exact selected inputs, fiscal periods, calculation trails, original filing links, unknown and expiry states | Selected real inputs reconciled; only two metrics, no fair-value calculation |
| Saved idea | Write a belief without inventing a numerical rule | Qualitative drafts, optional conditions, blank thresholds, explicit approval, private comparison tied to the exact saved revision | Full local journey exercised with actual Alphabet evidence and an authored demo question |
| Monitoring | Revisit an explicitly defined numerical condition | Durable worker, source/period/age checks, corrections and outage/recovery, grouped in-app updates, unchanged-input suppression | Working within two metrics. Data refresh is manual; draft-only reasoning has no automatic qualitative alert engine |
| Review and return | See what changed next to what was believed at the time | Exact new/corrected sources, before/after figures, saved reasoning, prior source versions, review acknowledgement and comparison history | Browser regression covers old qualitative comparisons after new evidence, edits and archive; usefulness/retention remains unmeasured |
| Paid/live operation | Exercise the actual integration without losing control of cost | Finnhub/SEC pacing, no automatic paid retries, immutable requests/responses, two priced OpenAI profiles sharing one original US$10 ledger | Real calls performed and recorded; output completion is assessed separately from semantic quality |

## Actual company evidence

These are selected reported results, not investment recommendations. Display rounding is separate from Decimal calculations used by monitoring.

| Company | Selected period | Revenue / comparable prior revenue / operating income | Revenue growth / operating margin |
| --- | --- | --- | --- |
| Microsoft | Annual, ended 30 June 2026 | USD331.839bn / USD281.724bn / USD155.237bn | 17.79% / 46.78% |
| Apple | Direct quarter, 29 March–27 June 2026 | USD109.417bn / USD94.036bn / USD35.695bn | 16.36% / 32.62% |
| Alphabet | Direct quarter, 1 April–30 June 2026 | USD119.796bn / USD96.428bn / USD40.770bn | 24.23% / 34.03% |

Selected input values were compared with each original SEC filing: [Microsoft annual filing](https://www.sec.gov/Archives/edgar/data/789019/000119312526323660/msft-20260630.htm), [Apple quarterly filing](https://www.sec.gov/Archives/edgar/data/320193/000032019326000020/aapl-20260627.htm), and [Alphabet quarterly filing](https://www.sec.gov/Archives/edgar/data/1652044/000165204426000071/goog-20260630.htm). This is a bounded reconciliation of the implemented metrics, not a complete accounting audit.

Finnhub data is actual retrieved quote/headline/snippet data. Publisher links and timestamps are retained. Review of model explanations checks them against those supplied snippets; it does not independently verify every news allegation or read inaccessible full articles. One checked Finnhub link redirected to CNBC, which returned 403; no access bypass was attempted.

## Failures found and changes made

1. **Quotation formatting:** five of the first eight private outputs were withheld because their quotations did not match. The comparison now selects original passage IDs and code renders the quotations. Whitespace-only recovery remains available for shared briefing quotations.
2. **Incorrect relationships despite exact quotations:** the Mini profile confused another company's revenue denominator, mislabelled contrary evidence and treated launch/aggregate revenue as evidence of product adoption. Only two of eight initial passage-ID outputs met the frozen core semantic criteria; three additional Mini reasoning cases also had material relevance errors.
3. **Stronger-profile retest:** using the same eight packets and the same prompt, GPT-5.4 with medium reasoning met all eight core expectations; all three additional matched reasoning cases also met their criteria. The model, reasoning setting and output allowance changed together, so the test cannot isolate their individual effect.
4. **New actual UI failure:** the next qualitative draft correctly left paid enterprise demand unproved, but completed a cut-off source phrase, “Google's internal…”, as “Google's internal use.” That is a material fidelity failure. The eleven earlier passes must not be reported as general accuracy or a clean twelve-case result. The correction excludes ellipsis-bearing source passages from both model input and citation eligibility, preserves raw originals and stable remaining passage IDs, counts omissions and stops empty requests before payment. It deliberately favors omission over guessing. Final live retest results appear below; the failed output is retained.
5. **History and input clarity:** qualitative comparisons were stored but could become unreachable after a new snapshot/revision. History now exposes each saved comparison and its exact evidence. Thresholds start blank; users can save a draft without monitoring. Assessment labels distinguish multiple same-day results; generic busy messages no longer falsely imply every source is refreshing.
6. **Source robustness:** malformed news text is quarantined without losing valid items; repeated corrections can return to earlier content; current packets exclude future or expired news. Workspace reads use a consistent database snapshot, so simultaneous retrieval cannot mix evidence versions.

7. **Shared briefing attribution:** Mini briefings retained valid quotations but dropped “former” from an executive role, implied distinct analysts from separate snippets, and attached a safety inference to launch-only citations. The shared route now uses the stronger priced profile and explicit qualification/claim-coverage rules. The original briefings remain saved; final retests are reported below.

All development failures and charged attempts remain in the original ledger and private evidence archive. An independent AI subagent used predefined criteria for the cited cases. These are development reviews, not independent professional certification or student research.

## Verification evidence

- **Offline behavior:** 218 backend checks passed after the incomplete-passage correction, including 15 opt-in replays of actual saved SEC bundles. Routine tests never call paid providers. They exercise fiscal mismatch, unknown/conflicting data, expiry, correction returns, duplicate events, owner isolation, revision races, crash/recovery, charge ambiguity and shared budget limits.
- **Frontend:** three contract checks and the production build pass. Recorded, SEC, reporting-age, market and private-review browser journeys cover the supported flows. The extended private journey exercises draft comparison history after new evidence, editing and archive, exact old sources, keyboard navigation/focus, and 320/390/1440px layouts.
- **Actual cached-data load:** 90 workspace reads across the three real companies at concurrency 1/5/15 completed without errors. Recorded p95 latency was 11.49/23.29/91.02 ms. These are local cached reads, not supplier throughput or a production scalability result; no additional supplier requests were made.
- **Caching:** each explicit evaluation batch repeats completed requests to verify the original review/call is reused without another charge. Historical comparisons do not silently become comparisons of a newer revision.
- **Preservation:** each installed upgrade keeps matching source/database backups and checks every preexisting record plus private configuration. No prior idea, evidence version or charge is reset.

## Corrective results and installed morning checkpoint

The final filtered private run completed **12/12 core cases**, with **70/70 eligible exact source citations** and **33/33 saved reasoning excerpts**, and twelve cache repeats. The separate updated Google UI comparison also met its bounded expectations after an actual new Finnhub item advanced snapshot 12 to 13. Its old reasoning/revision and earlier comparisons remained unchanged. The new article did not establish a meaningful Gemini catalyst; the interpretation correctly left demand unproved. See [retained evidence review](../../reviews/2026-10-02/evidence-business-review.md) for all failed and accepted rounds.

Shared v5 Microsoft corrected the role qualification but still implied stock/investor motives in an interpretation. The Apple v5 request timed out; Google v5 was not attempted. The user subsequently reported the dashboard at **US$0.87 / 56 requests** and authorized continuing. A separate append-only decision keeps the timed-out call's full **US$0.13926** maximum against the budget without inventing its charge, response ID or token usage. A longer bounded read timeout and durable client-request ID improve future diagnostics; they do not recover or retry the original response.

Shared prompt v6 explicitly narrows titles/motive claims. **3/3 actual-company briefings completed**, with **23/23 exact eligible quotation entries**, and every unchanged repeat reused its cache. Parent-agent review accepted their core attribution/temporal/adoption boundaries, with small editorial limitations recorded separately. This was not another independent three-reviewer panel. [Shared v6 report](../../reviews/2026-10-02/shared-briefing-v6-review.md).

The installed next phase adds **Download research record** for a selected definition, numerical assessment or comparison. It preserves history and source access in a printable offline HTML file. The complete offline suite passed **230 checks, zero skipped**, including actual saved SEC inputs; 38 focused market/fragment checks passed after the final prompt update. Three frontend checks and the production build passed. The expanded idea browser downloaded and reopened a historical report without remote resources, checked phone/desktop layout and retained the selection after a synthetic download error. The final market browser passed its cached-source, omission, configuration, paused-state and responsive cases. This adds to the earlier five complete browser journeys; it is not a claim of five wholly repeated suites after every text change.

Installed read-only verification at **08:08 SGT** found current v6 cached briefings and actual filing/news records for all three companies, three retained private Google comparisons, and the same current snapshot. It saved an actual Google export through the authenticated local endpoint without model spending: `.local/live-tests/Alphabet-research-record-20261002.html`. The in-app-browser download-event automation timed out, so that specific UI file handoff is not counted as verified; the Chromium download test and installed actual endpoint export both passed. Existing ideas, evidence and credentials were preserved during installation. Backup: `.local/backups/phase8-export-accounting-20261002T000143Z/`; source/hash/budget verification: `.local/live-tests/phase8-final-verification.json`.

**Budget checkpoint:** US$0.919065 confirmed usage + US$0.13926 authorized maximum hold = **US$1.058325 committed**, leaving **US$8.941675** under the original US$10 cap. There are 59 call records: 58 settled, one original timeout with its full maximum retained. New requests are no longer blocked by that explicitly authorized hold. The dashboard's rounded earlier total is not presented as an exact per-call reconciliation.

The [full requirement-by-requirement audit](requirements-audit.md) distinguishes working, partial, missing and deliberately excluded scope. The [consultant synthesis](../../reviews/2026-10-02/consultant-synthesis.md) links the three prior reports and states their evidence cutoffs. The latest export/accounting review was performed by the parent agent; a reviewer hit its Codex usage limit and no missing independent review is invented.

## What still needs real users or a later product phase

The demo does not establish that students understand the result, make better decisions, return after meaningful changes, or will pay. Compare it with a chronological sourced summary plus notes using the same evidence, including people who do not complete the flow. AI reviewers cannot substitute for that study.

The wider roadmap's catalysts/deadlines, proposal approvals, broader fundamentals, social listening, consensus/valuation, general extraction, production accounts, billing, external notifications and deployment remain unimplemented or deferred. They are not represented by a numerical threshold or a source-linked AI paragraph. The strongest supported pitch is a research companion with inspectable real evidence, saved reasoning and bounded monitoring—not a claim that it predicts investments correctly.

## Phase 9 event checkpoint — 08:44 SGT, 2 October

Installed event criteria, required/risk roles, UTC report-publication windows, explicit event evidence checks, deadline catch-up, history and exports. 251 backend tests, four frontend checks, event-only browser journey and prior private-history journey pass. Initial actual-company calls exposed one false denial label; corrected retest matched all nine frozen criteria across MSFT/AAPL/GOOGL, with 15 exact quotation entries. This is a development retest, not a general accuracy result. See [event case evidence](../../reviews/2026-10-02/event-real-case-review.md).

Accounted total is US$1.21173: US$1.07247 confirmed plus the unchanged US$0.13926 authorized maximum hold. Existing Google research remains intact. Microsoft and Apple have labelled pitch examples; Alphabet event tests use a separate local owner. Typed proposals, wider fundamentals/valuation and recurring acquisition/digest remain outstanding. The complete implementation plan is not yet finished.


## Phase 10 suggestion checkpoint — 2 October, after the morning deadline

The app now turns a research question or saved idea into typed pending reasoning/numeric/event suggestions with exact source passages, before/after review, editable definitions, atomic approval/rejection and immutable history. Users can combine compatible selections into one revision, save only a draft or explicitly approve monitoring. Concurrent edits preserve unsaved review text and require a fresh suggestion against the new revision.

269 backend checks, five frontend checks, the dedicated proposal browser and prior private-history browser journeys pass. Seven explicit live requests tested four authored actual-company situations and corrective retests. These found weak paid-adoption evidence, a partial-versus-complete scope problem and cut-off generated criteria. Prompt/code corrections and retained failures are documented in [the actual-case review](../../reviews/2026-10-02/proposal-real-case-review.md). One final Google revenue suggestion remained too broad and was rejected; it is not counted as a clean full-response success. The useful reasoning and paid-customer suggestions remain pending beside the unchanged original Google draft. Isolated QA checks approved the exact Microsoft 15%/20% annual assumptions in one revision and preserved approved-proposal evidence in an export.

Budget: US$1.4089575 confirmed + US$0.13926 retained maximum hold = US$1.5482175 committed; US$8.4517825 remains. The review is parent-authored and does not replace independent consultants or student research. The wider plan is still incomplete: broader fundamentals, valuation and scheduled acquisition/digest remain the next product work.
