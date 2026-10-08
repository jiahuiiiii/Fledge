# Phases 71–72 — UI refinement and alternative valuation data

5 October 2026. Readability, spacing and reduced-motion-aware menu/dialog feedback are installed. The original API budget is increased to US$30, preserving charges and historical holds. A separate analyst-target panel now connects the public Stock Analysis forecast summary/table, attributed to S&P Global, with immutable snapshots and explicit manual refresh. User scenarios remain separate. [UI review](../../reviews/2026-10-05/ui-rhythm-phase-review.md) · [Target contract](../../features/analyst-targets.md) · [Target review](../../reviews/2026-10-05/analyst-targets-phase-review.md).

Actual source verification: all six companies have 12-month target snapshots; 24 range values and six poll counts match the publisher tables. 86 focused valuation/source cases pass across staged and real-page replay runs; 74 budget checks, 22 frontend checks and responsive/motion/navigation browser checks pass. No additional AI spending: US$13.4597155 available of US$30 after confirmed charges and retained holds. Saved private research is preserved. This does not resolve prior sentiment interpretation failures, source continuity or participant validation.

# Phase 70 checkpoint — conditional share price references

5 October 2026. Valuation optionally converts total-equity scenarios into per-share horizon prices and entry references for an explicitly chosen annual return. Projected diluted shares, basis, date and assumptions remain visible in saved records, sensitivity and exports. Old requests/save hashes remain unchanged. 51 focused backend cases including six real filing bases, 22 frontend checks/build and the expanded 320–1440px browser journey pass. [Contract](../../features/valuation-scenarios.md) · [Review](../../reviews/2026-10-05/price-reference-phase-review.md). No automatic share-count feed, consensus target or paid call is added.

# Phase 69 checkpoint — fresh sentiment and question-alert cases

Fresh AMZN/META/NVDA source evaluation completed six calls for US$0.49402. Criteria match 30/30 scored relevance, 16/17 tones, 41/41 answer boundaries and 37/38 quiet reporting cases; 181 quotation associations match. NVIDIA retains opinion/report, comparison and answer-attribution concerns. Reviewed AMZN/META sentiment is available from paid cache; other outputs stay in evaluation. [Review](../../reviews/2026-10-05/fresh-alert-cases-phase-review.md). Cumulative US$15.9377945 confirmed + US$0.60249 held leaves US$3.4597155 of US$20. Watches stay off. General accuracy and user validation remain open.

# Phase 68 checkpoint — skeleton shimmer

Loading text bars and chart placeholders now have a subtle left-to-right shimmer. Reduced-motion preferences disable it; placeholder geometry and existing loading/navigation behavior are preserved. Build/targeted formatting and desktop/phone motion checks pass. [Implementation and review](../../reviews/2026-10-04/skeleton-shimmer-phase-review.md). No backend/schema changes or API spending.

# Phase 67 checkpoint — stable view transitions

The reported remaining blinking came from sequential workspace/chart loads, chart remounting on tab return and Updates changing shared column geometry. New-company content now reveals together after a readable skeleton; visited views retain their state and Updates preserves the shared frame. [Implementation and review](../../reviews/2026-10-04/stable-transitions-phase-review.md).

Build/formatting, 22 frontend checks, normal/slow loading checks, shared scope and interactions, nine sizes and five disposable browser journeys pass. The earlier skeleton verification did not establish normal-speed visual stability. No backend/schema changes or API spending; user acceptance and broader project requirements remain open.

# Phase 66 checkpoint — animated removal notice

The stock-removal banner smoothly expands below the stationary header, reveals its green background from left to right and groups undo/close icons at the right. Exit also collapses smoothly; reduced-motion preferences disable animation. Build/formatting, existing interactions and desktop/phone motion checks pass. [Implementation and review](../../reviews/2026-10-04/removal-animation-phase-review.md). No backend/schema changes or API spending.

# Phase 65 checkpoint — selective loading

Header, company sidebar and desktop columns now remain mounted through stock changes as well as tab changes. Only changing research and saved-idea areas show static skeletons. Charts and slower research subsections reserve their space; failed reads show retry, and late reads/saves cannot replace the newly selected company's state. [Implementation and review](../../reviews/2026-10-04/selective-loading-phase-review.md).

Build/formatting, 22 frontend checks, controlled slow-response checks, shared company-scope checks, nine viewport sizes and five disposable browser journeys pass. No backend/schema changes, source retrieval or paid calls. This supersedes the earlier company-keyed remount; broader implementation and user validation remain open.

# Phase 64 checkpoint — shared company selection

One selected company follows Workspace, My ideas, Updates and History. Sidebar and company-dropdown changes keep the active tab. All companies clears selection and shows a workspace overview, all ideas, all updates or the new saved-history index with exact record links. Current weekly reviews share that scope. [Implementation and review](../../reviews/2026-10-04/shared-company-phase-review.md).

Build/formatting, 22 frontend checks, core/inbox/digest browser journeys, dedicated scope and menu/removal checks, and nine viewport sizes pass. No backend or paid-model changes. The [price-reference design](../planning/price-reference-design.md) is investigated, not installed: the existing Finnhub key returned 403 for analyst targets; formula prices would extend the current valuation engine with explicit share-count/horizon assumptions.

# Phase 63 checkpoint — custom menus and stable navigation

Dropdowns now use the app's dark menu style with keyboard support and a subtle focus border. Companies can be removed from the sidebar, undone or restored; this browser preference preserves saved research and monitoring. Tab changes keep the shared workspace shell and company data mounted; skeletons cover actual loading. [Implementation and review](../../reviews/2026-10-04/ui-interactions-phase-review.md).

Build/formatting, 22 frontend checks, three disposable browser journeys, dedicated interaction checks and nine viewport sizes pass. No backend/schema changes or paid calls. Chrome verification does not establish cross-browser or participant validation.

# Phase 62 checkpoint — readability and Updates filtering

Updates ticker buttons now filter the inbox, synchronized with its dropdown. Review-status selection is preserved, pagination resets, and All companies clears the scope. Empty companies remain in the inbox. The interface uses larger main text and controls, removes repeated helper copy and reveals optional metadata/settings through named details. Important source problems remain visible. [Implementation and review](../../reviews/2026-10-04/readable-inbox-phase-review.md).

Build/formatting, 22 frontend tests, seven disposable browser journeys and nine-size read-only layout checks pass. Installed company filtering is checked separately. No backend/schema changes or paid calls; full-plan and user validation remain incomplete.

# Phase 61 checkpoint — full-screen layout

Desktop now has a fixed workspace frame: persistent navigation, compact company rows, independently scrollable research and saved-idea panels, and a full-width footer at the bottom. Shared gutters and greater section spacing improve the area below the chart. Phones keep natural page scrolling. [Implementation, checks and five-perspective review](../../reviews/2026-10-04/fullscreen-layout-phase-review.md).

Build and 22 frontend checks pass. The installed saved-company layout passes nine viewport sizes from 320 to 2560px, keyboard scrolling, navigation and source dialogs; the existing disposable save/approve/review/history journey also passes. No paid calls or backend/schema changes. This presentation correction does not establish user acceptance or close the broader plan.

# Phase 60 checkpoint — retained-source alert continuity

4 October 2026. Sixteen forced-due checks across company/private scenarios exercise the existing production delivery path using retained Apple/Alphabet source wording and paid labels with explicitly authored arrivals and faults. New reports alert once; sample gaps/repeats stay quiet; failed/stopped checks preserve pending work; independent review/revision history and source access survive. Private recovery works after the company baseline advances. [Replay guide](../../testing/alert-continuity-replay.md) · [Five-perspective review](../../reviews/2026-10-04/watch-continuity-phase-review.md).

140 relevant backend checks and the new phone/desktop inbox journey pass. One bounded actual-source private answer preserves potential legal claims and two exact quotations, costing US$0.0070975. The remaining allowance is US$3.9537355 after US$15.4437745 confirmed plus US$0.60249 historical maxima, 300 calls. No new blocker. Runtime/UI/schema remain unchanged; main data and off watch settings are preserved. This adds integration evidence, not general model or prospective validation. Earlier checkpoints follow.

# Phase 59 checkpoint — complete sentiment inputs and valid news references

4 October 2026. New sentiment method v14 retains v10 semantic instructions and constrains earlier-news references in code. Complete-source fitting keeps the request within its existing byte limit and discloses omissions throughout current/saved/history/alert/export views. A real Alphabet packet preserves all 16 originals at 63,197 bytes, leaving out 13 additional comparisons. [Contract](../../features/sentiment-input-limits.md) · [Five-perspective review](../../reviews/2026-10-04/source-limits-phase-review.md).

Final paid evaluation: 43 items, 109 exact quote associations, 40/40 selected relevance and 19/19 selected tone decisions. Three ambiguous relevance cases stay unscored. Four expected reporting alerts and 24 quiet cases pass in authored-baseline replay; all-seen replays stay quiet. Apple completes with no semantic links, while exact-body grouping counts its duplicate once. Known tone/answer errors and broad/prospective accuracy remain unverified.

1,061 distinct backend cases pass across the broad and focused follow-up (the initial expired-test-lease failure is retained), with 22 frontend checks/build and three responsive browser journeys. Schema 32, original records preserved, watches off. Seven requests add US$0.5798525 confirmed and one US$0.300925 unresolved maximum. Following the reported dashboard total and separate continuation decision, cumulative confirmed US$15.436677 plus US$0.60249 held leaves US$3.960833 of the original US$20. No source acquisition or app research publication. Full-plan completion remains open. Earlier checkpoints follow.

# Phase 58 checkpoint — question-only sentiment candidate rejected

A narrower correction makes three selected information questions neutral and passes ten authored reply-tone controls, but newly includes a generic NVIDIA ticker-list/portfolio question in the company sample. The original selected tones remain 30/34; its adoption gate fails. Candidate v13 is archived and staging is restored to installed v10. Raw responses also correct an earlier review-writing error: phase53's original temporal selections were identical to its baseline. [Results, correction and five-perspective review](../../reviews/2026-10-03/sentiment-questions-phase-review.md).

1,049 candidate backend checks with six corpora and 92 overlapping focused checks pass. Six paid requests cover 73 items and 187 exact quotation associations, costing US$0.654. Same US$20 ledger: US$14.8568245 confirmed plus US$0.301565 historical maxima leaves US$4.8416105, 292 calls, no new blocker. App/frontend/schema 32, earlier research and watch settings remain unchanged; no acquisition or publication. The full plan remains incomplete; prioritize broader target-relevance/alert evidence over another small rewrite of the same tone prompt.

# Phase 57 checkpoint — expected reporting evidence

Numerical conditions can now explicitly require a reporting period ending on or after a chosen date, expected by a second date. After that inclusive UTC day, missing matching figures make the condition unknown while preserving old value/source. Existing clock catch-up, grouped Updates, history, suggestion review and individual/weekly exports preserve the expectation. These are user assumptions, not verified company filing dates. Migration 032 defaults both fields to null; unchanged definitions keep their prior methods and signatures. [Contract](../../features/report-expectations.md) · [Five-perspective review](../../reviews/2026-10-03/report-expectations-phase-review.md).

1,049 backend checks with six corpora, 22 frontend checks/build and four browser journeys pass. Sixty deterministic criteria use retained SEC observations across six companies; 34 legacy manifests/signatures and 12 numerical outcomes remain exact. No new source/model calls. US$14.2028245 confirmed plus US$0.301565 historical maxima leaves US$5.4956105 of the same US$20 allowance, 286 calls. Watches/schedules remain off. The full plan is incomplete; earlier checkpoints follow.

# Phase 56 checkpoint — recurring event expectations

Event conditions now support finite monthly, quarterly or yearly windows. Preview all dates before approval; each new period requires its own evidence. Clock rollover resets earlier confirmations without API spending. Explicit earlier-window checks and late completions remain in History, while optional event watches keep their existing cadence. Migration 031 defaults existing events to one window and preserves eight legacy request identities. [Contract](../../features/event-conditions.md) · [Five-perspective review](../../reviews/2026-10-03/recurring-events-phase-review.md).

1,033 backend checks with six corpora, 104 overlapping focused checks, 19 frontend checks/build and five browser journeys pass. Six Meta/Amazon saved-response findings retain 11 quotation associations; all three confirmations clear in the next authored period. This is deterministic replay, not a new semantic benchmark. No new paid/source calls: US$14.2028245 confirmed plus US$0.301565 historical maxima leaves US$5.4956105 of the same US$20 allowance, 286 calls. Watches remain off. The overall plan is incomplete; earlier checkpoints follow.

# Phase 55 checkpoint — event occurrence timing

Event conditions now distinguish article publication from a source-stated occurrence date. A later report can support an earlier event; a new report cannot silently place an older event inside the window. Missing, partial, ambiguous or outside-window dates remain unconfirmed. Existing report-only conditions and eight retained request identities stay exact. Migration 030, editor, reviewable edits, optional watches, history and exports preserve date meaning. [Contract](../../features/event-conditions.md) · [Five-perspective review](../../reviews/2026-10-03/event-occurrence-phase-review.md).

1,014 backend checks, 85 overlapping focused checks, fifteen frontend checks/build and four relevant browser journeys pass. The final four paid packets match 12/12 predeclared labels, retaining the initial 11/12 run and its not-yet/denial error. Eight calls cost US$0.1783950. Total confirmed US$14.2028245 plus US$0.301565 retained historical maxima leaves US$5.4956105 of US$20, 286 calls. No source retrieval, user-definition edit or main alert publication; watches remain off. The overall plan is incomplete. Earlier checkpoints follow.

# Phase 54 checkpoint — source-specific news comparisons

New comparisons use a code-written interpretation label and paired original excerpts instead of a free generated sentence that can transfer details between reports. Earlier summaries remain unchanged and are identified in workspace, alerts and weekly exports. Classifier v10 and paid request identity stay unchanged; rendering policy is now version 6. [Implementation and five-perspective review](../../reviews/2026-10-03/coverage-wording-phase-review.md).

984 backend checks with six retained corpora, 52 overlapping focused checks, fourteen frontend checks/build and responsive sentiment/reporting-update journeys pass. All seven saved comparison decisions preserve quotations, grouping, guards and seen keys. The existing Amazon sample was appended from its exact cached response without another charge; the installed app and original-source dialog passed a read-only browser check at 390/1440px. Schema 29; private records and schedules stay unchanged/off. This phase costs US$0: confirmed US$14.0244295 plus US$0.301565 historical maxima leaves US$5.6740055 of US$20, 278 calls. The overall plan remains incomplete. Earlier checkpoints follow.

# Phase 53 checkpoint — question/context candidate evaluated

Candidate v12 improves the original selected tones to 31/34 without a new selected tone failure and matches all ten new reply tones. It is not installed: the different-company Meta challenge matches 8/9 and the temporal-evidence criteria still fail. A phase58 raw-response audit corrects the earlier regression claim: the original temporal selections were identical. The app remains v10, medium reasoning, schema 29. [Experiment, concrete comparison-prose finding and five-perspective review](../../reviews/2026-10-03/sentiment-contract-phase-review.md).

979 candidate backend checks with five corpora and 88 overlapping focused checks pass. All six paid responses complete; 73 items and 188 exact quotation associations are retained. No frontend/source/watch/research-publication changes. Six calls cost US$0.59955. Cumulative US$14.0244295 confirmed plus US$0.301565 historical maxima leaves US$5.6740055 under the same US$20 cap, 278 calls and no new unresolved charge. Next work targets unsupported news-comparison prose while preserving the paired original excerpts. The full plan remains incomplete. Earlier checkpoints follow.

# Phase 52 checkpoint — higher reasoning not adopted

The fixed sentiment comparison failed its adoption gate. Three complete packets match 17/23 selected criteria versus 20/23 for the same baseline subset; NVIDIA reached its output cap and was rejected. The app keeps v10 medium reasoning. The new bounded profile is evaluation-only. [Experiment and five-perspective review](../../reviews/2026-10-03/sentiment-depth-phase-review.md).

979 backend checks with five retained corpora and 77 overlapping focused checks pass after fixing the first run's transport compatibility regression. All 35 accepted items and 88 original quotation associations were reviewed. No frontend/source/watch/research-publication changes; schema 29 and protected records stay exact. Four paid calls cost US$0.6654925. Cumulative confirmed US$13.4248795 plus US$0.301565 historical maxima leaves US$6.2735555 under the same US$20 cap, 272 calls, no new unresolved charge. The plan and semantic/participant validation remain incomplete. Earlier checkpoints follow.

# Phase 51 checkpoint — sentiment candidate not promoted

The separate-positive/negative-excerpt candidate passes its software tests but regresses from 30/34 to 29/34 original tone criteria; another new control response is rejected. It is preserved for evaluation only. The app still runs sentiment v10 and schema 29 with the phase50 weekly reviews. Saved research, watches, profiles and frontend build remain unchanged. [Experiment and five-perspective review](../../reviews/2026-10-03/sentiment-direction-phase-review.md).

Candidate checks: 977 backend cases, 102 overlapping focused cases, fourteen frontend checks/build and sentiment/history browser flows. These counts do not imply installation or improved meaning. Five paid calls cost US$0.577065; the original US$20 ledger now records US$12.759387 confirmed plus US$0.301565 historical maxima, leaving US$6.939048 across 268 calls. No new blocker or source acquisition. All original responses and failures are retained; staging was restored after archiving the candidate. The overall plan remains incomplete. Earlier checkpoints follow.

# Phase 50 checkpoint — optional scheduled weekly reviews

Weekly in-app reviews now save the original membership/overview and expose independent seen status, with current source access checked on reopening and download. The schedule defaults off and makes no new source/AI calls. Local weekly time zones, DST, catch-up, failures, concurrent workers and stop/reconfiguration are covered. See [behavior](../../features/periodic-review.md) and [five-perspective review](../../reviews/2026-10-03/scheduled-reviews-phase-review.md).

Final verification: 962 backend cases, fourteen frontend checks/build and both saved/current review browser journeys at 320/390/1440px. The first full run's test-fixture failure is retained and the corrected full run passes. A separate read-only audit matches fourteen existing updates across three actual companies; this is not prospective-delivery or classification-accuracy evidence. Schema 29; source/database backup and unchanged protected records are verified at installation. Source watches remain off and no main account is enrolled.

Cost added: US$0. Same cumulative US$20 ledger: US$12.182322 confirmed, US$0.301565 retained maxima, US$7.516113 available, 263 calls. Both historical ambiguous records remain unchanged; no new blocker. This completes local scheduled digest delivery, with broader semantic/product/participant requirements still open. Earlier checkpoints follow.

# Phase 22 checkpoint — compare sentiment samples

The news/social panel now compares exact earlier and later saved analyses, showing selected/removed texts separately from changed labels. Historical sources, method changes, additional comparison context and grouping differences remain inspectable. This is a comparison of irregular samples, not a market sentiment trend. [Contract](../../features/sentiment-sample-comparison.md) · [Five-perspective review](../../reviews/2026-10-02/sentiment-history-phase-review.md).

**492 backend checks**, five frontend checks/build and comparison plus existing sentiment browser journeys pass. All **13 saved analyses / 22 ordered company pairs** preserve exact stored summaries/sources and independently counted changes; **330 quotation associations** match. Twenty-one pairs cross methods and eighteen select unchanged texts, explicitly warned in the view. The latest Microsoft comparison has one newly selected news text, one removed, two changed labels, five unchanged and four unchanged social texts. These are actual-record read checks, not new accuracy or recall evidence.

No AI/source requests or new spending. Main records/watch choices/publications remain unchanged and watches off. Original cumulative ledger: **US$4.3040235 confirmed + US$0.13926 retained maximum hold**, **138 calls**, **US$5.5567165 remaining**. Schema stays 18; backup and final evidence are recorded in the phase review. The full roadmap and participant validation remain incomplete. Earlier checkpoints follow.

# Phase 21 checkpoint — explain scheduled checks

News/social watches now retain immutable check history: baseline, quiet, failed, stopped and missing-completion outcomes, with source-health snapshots and links to produced updates. A recent Finnhub refresh is reused during the five-minute cooldown. History is collapsed and read-only; installation does not enable watches. [Contract](../../features/watch-check-history.md) · [Five-perspective review](../../reviews/2026-10-02/watch-history-phase-review.md).

**481 backend checks**, five frontend checks/build and history/sentiment/private-alert browser journeys pass. An actual Microsoft exercise analysed **8 news items and 4 Reddit posts**, preserving two failed social feeds. Company and private QA checks stayed quiet: the new coalition story did not meet company alert rules or answer the authored product/leadership question. An immediate repeat reused analysis with no extra charge or duplicate. This verifies bounded integration and a quiet path, not recall or event-detection latency. Main saved revisions/watch preferences/publications were unchanged; all watches remain off.

Two calls added **US$0.1104875**. Original cumulative spending is **US$4.3040235 confirmed + US$0.13926 original maximum hold**, **138 calls**, **US$5.5567165 remaining**, with no new unresolved charge. Schema 18 preserves prior rows and private configuration. Evidence: `.local/live-tests/watch-history-20261002T070739Z/`. Full roadmap and participant validation remain incomplete. Earlier checkpoints follow.

# Phase 19 checkpoint — compare repeated reporting

Sentiment now compares related news as **repeated coverage, new detail or contradiction**, with both exact sources available beside the explanation. Related reports count once in the news summary; social opinions stay separate. Company/private watches can keep already seen repeats quiet while retaining new details, changed headlines and denials. [Contract](../../features/news-coverage.md) · [Five-perspective review](../../reviews/2026-10-02/news-coverage-phase-review.md).

Four initial actual-source/authored-contrast requests matched 12/12 prewritten checks, but manual review found an unsupported Apple analyst-identity merge and a numeric-suffix parsing issue. Both are retained and corrected. Four v4 retests match 14/14 specified checks; 224 quote associations match across both runs. A constructed delivery replay with actual Google/Microsoft sources suppresses the seen repeat and retains the new detail. This is not whole-feed recall, unseen-case accuracy or live latency evidence.

Verification: **443 full backend checks**, **68 focused checks after the final legacy-key guard**, five frontend checks/build and final sentiment/private-alert browser journeys at 320/390/1440px. Schema remains 16; existing rows/private configuration are preserved. Main saved versions, watch settings, publications and monitoring state are unchanged; watches remain off. Initial/final model evidence: `.local/live-tests/news-coverage-20261002T053604Z/` and `news-coverage-retest-20261002T054330Z/`.

This phase costs **US$0.602105** across eight calls. Original cumulative ledger: **US$3.824481 confirmed + US$0.13926 original maximum hold**, **125 calls**, **US$6.036259 remaining**. No new ambiguous charge. The full roadmap and participant validation remain incomplete. Earlier checkpoints follow.

# Phase 18 checkpoint — real daily charts

MSFT, AAPL and GOOGL now have cached daily charts in the market workspace, with line/candlestick views, date ranges, keyboard/touch inspection and an exact-source table. This reuses Deus's public Yahoo daily-price approach after Finnhub candle access returned HTTP 403. No extra key, paid data plan or model call was needed. [Contract](../../features/price-history.md) · [Five-perspective review](../../reviews/2026-10-02/price-history-phase-review.md).

Three actual acquisitions each return **252 sessions, 2025-10-01 through 2026-10-01**. All **3,780 OHLCV fields** match the raw provider responses; the last closes match the saved same-date Finnhub quotes to the displayed cent. This checks parsing and stored data, not independent historical-price or corporate-action accuracy. The current New York date is excluded. Failed refreshes preserve the prior whole window; source access, dates, missing data and retrieval time are visible.

Verification: **424 backend checks**, **five frontend checks/build**, dedicated price and prior recorded research browser journeys pass. The price journey covers 320/390/1440-pixel layouts and makes no external/model requests. The actual installed Microsoft browser shows the retrieved daily series. Installation applied **schema 16**, preserving every existing row and private configuration. Backup: `.local/backups/phase18-price-history-20261002T051205Z/`; actual evidence: `.local/live-tests/price-history-20261002T051421Z/`. Main ideas, watches, publications and monitoring state are unchanged; watches remain off.

No added AI spending: **US$3.222376 confirmed + US$0.13926 original maximum hold**, **117 calls**, **US$6.638364 remaining** under the original cap. Alerts/sentiment remain the main focus, with social-risk calibration and repeated-story noise unresolved. The full roadmap and participant validation remain incomplete. Earlier checkpoints follow.

# Phase 17 checkpoint — evidence toward open questions

The local app now surfaces a concrete answer or partial answer to an explicit saved question as **Evidence toward your question**. It shows the original question/reasoning and source together, preserves the research outcome and uses the existing review/history/download/watch workflow. [Contract](../../features/idea-relevance-alerts.md#evidence-toward-an-open-question--phase-17) · [Five-perspective review](../../reviews/2026-10-02/question-alert-phase-review.md).

Verification: **401 integrated backend checks**, **62 focused checks after final prompt v6**, five frontend checks/build and the private-alert browser journey, including 320/390/1440-pixel layouts. Fourteen actual-source calls retain initial v5 results and four targeted v6 retests. Initial labels match **55/56**; targeted final labels match **24/26**. Concrete question answers survive the correction, and an unsupported source deadline is removed. Broad social-risk classification remains unstable: the final subset has one additional risk and one expected risk left quiet. Exact text checks cover **160 source quotations and 46 saved-text anchors**; they do not establish semantic truth or user benefit.

Installed with schema 15 and all preexisting rows/private configuration preserved. Main versions, watches and publications are unchanged; watches remain off. Evidence folders: `.local/live-tests/question-answers-v1-20261002T044514Z/` and `question-answers-v2-20261002T045050Z/`. Backups use phase17 timestamps `20261002T044446Z` and `20261002T045021Z`. This phase costs **US$0.428085**: cumulative **US$3.222376 confirmed + US$0.13926 original maximum hold**, 117 calls and US$6.638364 remaining. No new ambiguous charge. The complete roadmap and participant validation remain unfinished. Earlier checkpoints follow.

# Phase 16 checkpoint — actual-source alert evaluation and fixes

A frozen development corpus exposed two concrete gaps: a complete future-availability sentence was being excluded with an earlier ellipsis-bearing quotation, and a disclosed counterparty/channel relationship was classified as unrelated. The source splitter now preserves that exact sentence; sentiment prompt v2 distinguishes concrete business relationships from incidental mentions and keeps relevance separate from tone. The app also shows the available candidate pool beside the selected sample. [Evaluation method](../../testing/alert-quality-evaluation.md) · [Five-perspective review](../../reviews/2026-10-02/alert-quality-phase-review.md).

The initial nine paid cases and nine corrective retests use actual stored public news/social content with authored beliefs/questions. Final checks match **48/48 sentiment fields** and **47/48 reasoning relations**. All eight expected alert connections are retained, with 39 quiet results and one additional broad social-risk interpretation. That disagreement is preserved for external calibration; these counts are not population accuracy or prospective detection measurements. All **286 quotation associations** match their original text. The test deliberately selects packets rather than measuring the live sampler's recall.

Verification: **390 integrated backend checks** after the source fix; **70 final focused checks**, five frontend checks, build and the sentiment/watch browser journey after the prompt/UI refinement. The installed browser shows 8 selected from 45 candidate MSFT news items. The source/database backup is `.local/backups/phase16-alert-quality-20261002T042356Z/`; final evidence and the reviewer packet are under `.local/live-tests/alert-quality-v2-followup-20261002T042731Z/`, with original/retest folders linked by their manifests.

Existing main-account reasoning, watches, publications and private configuration are preserved. Evaluation outputs are not published as app alerts, and watches remain off. This phase adds **US$0.7234535**: cumulative **US$2.794291 confirmed + US$0.13926 original maximum hold**, 103 calls and US$7.066449 remaining. No new ambiguous charge; the original timeout charge is still unsettled. The full implementation plan remains incomplete, including historical charts, broader fundamentals/source coverage, structured expectations and further alert/user evaluation. Earlier checkpoints follow.

# Phase 15 checkpoint — explicit valuation assumptions

The new Valuation tab compares up to three P/E or P/S cases using reported annual revenue and user-selected growth, net margin and multiples. Sensitivity tables, manual Finnhub TTM references, private immutable saves, old-source identity and offline downloads are implemented. Values represent undiscounted total company equity at the chosen horizon, not share-price targets or current fair value. [Method and limits](../../features/valuation-scenarios.md) · [Five-perspective purpose review](../../reviews/2026-10-02/valuation-phase-review.md).

**368 integrated backend checks** passed with the saved SEC corpus. A final formula-display refinement passes all **23 focused valuation checks**. Five frontend checks, build, the new valuation browser journey and prior financial browser journey pass. The installed actual-data test retrieved three fresh Finnhub reference sets and matched **150 case/grid outcomes** with an independent rational-arithmetic checker across Microsoft, Apple and Alphabet. Six private QA comparisons and one clearly labelled Microsoft pitch example were saved, read, exported and checked for idempotency. The actual browser opens the example and downloads its HTML successfully.

The annual bases were USD331.839bn for MSFT (2026-06-30), USD416.161bn for AAPL (2025-09-27) and USD402.836bn for GOOGL (2025-12-31), selected from the previously reconciled filings. Growth/margin assumptions were authored test inputs, not forecasts. The Finnhub P/E and P/S references are supplied values, not independently reconstructed valuations or a validated peer group.

Source/database backup: `.local/backups/phase15-valuation-20261002T035716Z/`. Actual test evidence: `.local/live-tests/valuation-20261002T035657Z/`. All preexisting rows and private configuration survived installation. Existing main-account reasoning, assessments and watch choices were unchanged; watches remain off. This phase added **US$0** in model spending. Cumulative confirmed spending remains **US$2.0708375**, plus the original **US$0.13926 maximum hold**, 85 calls and US$7.7899025 remaining. The original ambiguous charge remains unsettled.

The first multiples/sensitivity workflow is complete within its stated scope. Historical price charts, broader trends/ratios and source coverage, reverse valuation/DCF, broader unseen-case alert evaluation, and participant comprehension/demand remain outstanding. Alerts and company-news/social sentiment remain the product's main focus. Earlier checkpoints follow.

# Phase 14 checkpoint — financial performance behind the story

The Fundamentals tab now has independent annual/direct-quarter views with fifteen reported/calculated rows: performance, cash generation and balance-sheet/debt components. Exact dates, same-filing comparisons, formula/input detail, original SEC links and missing-data explanations are included. The existing SEC transport and growth/margin selector are reused; no new key, model or paid supplier was added. [Contract](../../features/financial-performance.md) · [Five-perspective purpose review](../../reviews/2026-10-02/performance-phase-review.md).

**345 backend checks**, five frontend checks, the build, the new financial browser journey and the previous SEC/monitoring journey pass. The final browser also checks financials arriving after an initially empty view; the default selects the newer report. Original-filing reconciliation matches **146 exact current/comparison inputs across six filings**. The initial audit reader missed three tagged-zero values; its corrected result and original failed output are retained.

The phase was installed after source/database backup at `.local/backups/phase14-financial-performance-20261002T032925Z/`. Fresh SEC refreshes for Microsoft, Apple and Alphabet populated all six reports, matching the reconciled corpus and reporting unchanged preexisting monitoring inputs. Existing main-account saved versions, assessments and watch choices were unchanged. Main watches remain off. Evidence is in `.local/live-tests/financial-performance-20261002T032925Z/`.

No paid calls were made. Confirmed cumulative spending remains **US$2.0708375**, plus the retained **US$0.13926 maximum hold**, 85 calls and US$7.7899025 remaining. The original ambiguous charge remains unsettled. This phase closes the bounded cash/debt/annual-quarter research gap; valuation scenarios, historical price charts, broader trends/ratios, source breadth and participant validation remain outstanding. Financial-snapshot history/export selection is not yet exposed, and numerical monitoring still supports growth/margin. Earlier checkpoints follow.

# Phase 13 checkpoint — one periodic research review

An on-demand weekly review now combines condition changes, company news/sentiment alerts and private saved-reasoning alerts. Period/company/status filters, older unread carryover, current coverage, unresolved questions, exact historical links and a complete filtered download support the return visit. Opening it makes no new data or model request. See [workflow](../../features/periodic-review.md) and [five-perspective review](../../reviews/2026-10-02/periodic-review-phase-review.md).

The integrated suite passes **329 backend checks**, five frontend checks and the build. The periodic-review and previous private-alert browser journeys pass at 320/390/1440 pixels. After a source/database backup and installation, independent counts matched all **eight saved main-account updates across three companies**: six condition changes and two private reasoning alerts. The main account currently has no company-alert publications; that third type was exercised in the isolated browser and backend fixtures. Saved reasoning, revisions and watch choices were preserved. All main-account watches remain off, and failed Reddit feeds are visible. This is a real-record read/export check, not new source acquisition or prospective alert evaluation.

Phase 13 added **US$0**. Cumulative confirmed spending remains **US$2.0708375**, plus the original **US$0.13926 maximum hold**, with 85 calls and US$7.7899025 remaining under the original cap. The on-demand review is complete within this scope; scheduled digest delivery, broader fundamentals/valuation, source breadth and participant validation remain outstanding. Earlier sections below are historical checkpoints.

# Phase 12 checkpoint — alerts tied to saved reasoning

The news/Reddit sentiment layer now feeds private, revision-pinned reasoning checks and opt-in local alerts. Specific risks to investigate are distinct from supports/challenges to a belief the user actually states. Context-only results stay quiet in History. Exact quotations, old revisions, downloads, unread counts and review acknowledgement are implemented. The final code passes **317 backend tests**, five frontend checks, the production build and the dedicated desktop/phone browser journey. Ten paid actual-source requests across three companies and the existing Google demo exposed and corrected four semantic issues; all failed results remain preserved. See [phase review](../../reviews/2026-10-02/idea-alert-phase-review.md), [actual-case review](../../reviews/2026-10-02/idea-alert-real-case-review.md) and [workflow](../../features/idea-relevance-alerts.md).

The unchanged Google demo now shows two **Risks to investigate** in Updates, without attributing optimism to its request for evidence. Main-owner watches remain off. Cumulative confirmed spend is **US$2.0708375**, with the original **US$0.13926 maximum hold** retained, 85 calls total and US$7.7899025 remaining under the original cap. This phase added US$0.492515. No new unresolved charge exists. Source coverage remains bounded, with two Reddit feeds rate-limited in the last retrieval; this is not validated alert accuracy or a complete social/OSINT product. Broader fundamentals/valuation, digest and participant validation remain outstanding. Earlier sections are historical checkpoints.

# Phase 10 checkpoint — reviewable suggestions

Typed proposals now cover a starting idea, reasoning edits, numerical conditions and event criteria. Explicit selection/review can save several compatible suggestions in one revision. Source/base staleness, duplicate/concurrent approval, target membership, privacy and old history are enforced. See [the workflow](../../features/reviewable-suggestions.md) and [five-perspective self-review](../../reviews/2026-10-02/proposal-phase-review.md). 269 backend checks and five frontend checks pass, along with the dedicated proposal and existing private-history browser journeys. Four actual-company situations and corrective retests are recorded in [the live case review](../../reviews/2026-10-02/proposal-real-case-review.md), including a final overbroad revenue suggestion that was rejected. Confirmed cumulative spending is US$1.4089575 plus the retained US$0.13926 maximum hold; the original US$10 ledger is unchanged. Broader fundamentals/valuation and recurring acquisition/digest remain incomplete.

# Phase 9 checkpoint — 2 October 2026

Event conditions, required/risk roles, report-publication deadlines, explicit source-linked event checks, immutable history and event exports are implemented. 251 backend checks pass with the actual SEC corpus, plus four frontend checks and the dedicated event browser journey. The existing private research-history journey also passes. See [event conditions](../../features/event-conditions.md), [phase review](../../reviews/2026-10-02/event-phase-review.md) and the [full requirements audit](requirements-audit.md). Live event cases are recorded in [the event case review](../../reviews/2026-10-02/event-real-case-review.md): the corrected retest matched 9/9 criteria, after preserving one initial false denial. Automated test providers remain mocked.

At the phase 9 checkpoint, proposals/approval were still outstanding; phase 10 above implements them. Wider fundamentals, valuation and scheduled acquisition/digest remain explicit work.

# Local implementation

Current status, 2 October 2026, morning: phases 7–8 are installed. Microsoft, Apple and Alphabet have actual retrieved filing/quote/news records, reconciled selected SEC inputs and current cached v6 briefings. Qualitative saved ideas have private source comparisons and exact history; selected reviews now export to an offline HTML record. The full offline suite passed **230 checks**, plus three frontend checks; focused final prompt and browser checks passed. Confirmed OpenAI usage is **US$0.919065**, with a separately authorized **US$0.13926 maximum hold** still counted for one timeout. The original US$10 cap is unchanged. [Overnight evidence/purpose review](overnight-purpose-review.md) and [full requirements audit](requirements-audit.md) record failures, fixes and incomplete roadmap items. The wider plan is not complete. Earlier phase sections below are historical checkpoints, not current restrictions.

The first complete fictional research-to-review workflow is implemented. The selected visual direction combines Terminal structure with Radar evidence cards, a compact chart, a persistent idea panel and restrained lime/green/rose accents. The application lives entirely in Thesis; Fork is not a runtime dependency or deployment target.

## Working

- Question-first research for one fictional company; question-specific authored context, reported fundamentals, dated guidance, contrary news, explicit unknowns and exact source reading.
- Three research outcomes: investigate, unresolved and reject. Saving an idea and activating monitoring are separate actions.
- Persistent drafts, typed conditions, explanations and explicit monitoring approval. Editing a definition clears the local approval checkbox. A draft can have no conditions.
- Atomic optimistic revision saves with stable condition identities. A conflicting edit preserves the user's draft; the user explicitly loads the latest revision before retrying.
- Durable worker records, bounded recovery leases, complete condition results and deterministic decimal comparisons. Failed work is visible and can be reevaluated by saving a new revision; there is no paid retry path.
- Five recorded developments: Q2 baseline, unconfirmed independent renewal report, mixed Q3 results, source outage, and Q3 restatement. Related evidence produces one assessment snapshot per revision and development.
- Separate condition outcome, source freshness, evidence availability, disagreement and review acknowledgement. Pending new assessments are labelled, with the previous cutoff visible.
- Immutable historical reasoning, thresholds, evidence manifests and results; earlier 12% growth is preserved after a 13% restatement. Current evidence hides superseded document versions and earlier-period reported fact cards; the source library and history retain them.
- Review or unresolved acknowledgement, idempotent concurrent review handling, edit and archive. Archive stops future monitoring and preserves history.
- Private PostgreSQL cluster, restricted API/worker login with forced account policies, same-origin local session and private filesystem state.

## Verification

The verification uses authored fictional records and no external model/data calls.

- **34 backend tests** cover decimal boundaries, missing/conflicting evidence, incompatible units/basis/periods, invalid conditions, fabricated/wrong-company quotes, negation preservation, claim availability, draft/approval behaviour, concurrent edits, actual non-superuser account isolation, reused physical connections, immutable history, incomplete evaluation rejection, stale job completion, historical cutoffs, restatements, unchanged-source ingestion, review idempotency, source entitlement checks, lease recovery, bounded failure, CSRF/host/session handling and strict request fields.
- A real database stop/start preserves prior history and pending jobs. A PostgreSQL dump is restored to a fresh test database and checked using the restricted role.
- **2 frontend contract tests** verify stable condition identity, expected revisions, explicit metric scope, empty drafts and rejection of incomplete/non-finite numeric rows.
- **End-to-end browser journey passed (including the corrective review):** exact sources, unresolved research, persisted/reloaded draft, approval reset after an edit, two conditions, mixed result, review, source outage, corrected current value, exact historical source, archive, two-tab conflict resolution, every saved draft/archive revision, missing fundamentals and no browser exceptions.
- Desktop and mobile screenshots were inspected. No horizontal overflow at **320, 390, 768, 1056 or 1440 px**. Native labelled fields, visible focus styling, dialog Escape/focus behaviour, readable outcome labels and reduced-motion support are included. This is not a formal screen-reader or full accessibility audit.
- Production frontend build succeeds. The installed frontend dependency audit reports **0 known vulnerabilities** after replacing inherited vulnerable build dependencies and removing unused packages. This is a point-in-time dependency check, not proof of application security.
- The Python tests currently emit a Starlette deprecation notice for its supported `httpx` TestClient compatibility. All checks pass; a future test-client upgrade can address the warning without changing the app transport.

Test commands are in [README](../../../README.md). Tests run in separate temporary database clusters and do not overwrite the local demo's history.

## Schema and API boundary

`migrations/001_initial.sql` defines 18 tables, including migration metadata. It is the original schema; migration 002 adds sealed revision membership and worker claim fencing. Upgrades are ordered, checksummed and transactional. The preserved `docs/archive/planning/schema.sql` contains the older 24-table planning draft and must not also be applied. No legacy data migration was performed.

The API uses Kestrel's `/api/v1`, cookie transport, `result` envelope, UUID identities and structured error conventions. It deliberately implements a smaller, atomic workflow instead of claiming compatibility with all upstream routes. See [API contract](../../development/api-contract.md) and [provenance](../../../PROVENANCE.md).

The local session represents one fictional account derived by the server. Restricted database roles are exercised, but the launcher also owns a private cluster administrator for initialization and the explicit fixture-ingestion control. This is an OS-local development trust boundary, not a production multi-tenant deployment design.

## Historical phase-1 limits (superseded where later phases apply)

There is no live acquisition, general generated synthesis, social listening, free-form extraction, market-data supplier, production user registration, suggestion/proposal workflow, external notification, export, billing or deployment. The separate provider phase below adds metered original-passage selection. Source permissions permit authored fixtures only. No quote validation is being represented as general claim-entailment verification. Real-time coverage, fiscal-period mappings, delayed publication, supplier denials, extraction quality, source entitlement tiers,  proposal staleness and real-auth recovery require separate implementation and evidence before live operation.

The worker runs inside the local app process using persisted database jobs. It recovers interrupted pure fixture evaluations; it is not yet an independently supervised production worker. Data retention/deletion and authenticated multi-user access need decisions before real accounts or financial data are introduced.

This proves the bounded software workflow can run. It does not establish investment accuracy, user comprehension, recurring usefulness, natural retention or willingness to pay. The authored brief is a transparent baseline for later comparing a Deus-powered live synthesis; the metered selection pass below is not yet a demonstrated improvement over the sourced baseline.

## Corrective review

Three AI reviewers covered product strategy/UX, architecture, and evidence/business. Their read-only re-review accepted the corrective slice. Implemented corrections include sealed condition membership, fenced worker attempts, ordered checksummed migrations, shared typed fundamental resolution, unknown coverage when checks are missing, approval reset after condition removal, complete revision history and explicit side-by-side conflict recovery. Upgrade tests preserve a saved draft, monitoring revision, assessment, acknowledgement and pending/running jobs. See [phase review](../../reviews/2026-10-01/phase-1-corrective-review.md).

The user subsequently authorized direct OpenAI tests under one cumulative US$10 building-period cap. No paid call has been made at this corrective phase. Live execution requires the next phase's durable accounting and source permission controls; a key alone does not enable ingestion.

## Phase 2 — metered source selection

The deterministic brief now comes from typed facts and authored claim records instead of frontend stage branches. Growth, risk and expectations questions have distinct source-linked responses. Empty sources leave the workspace usable. Optional direct OpenAI selects existing original paragraphs; omitted passages and selection limits are visible. It never writes numeric facts, changes conditions or produces a trading recommendation.

The accounting review found and corrected three issues before any paid dispatch: copied-checkout allowance duplication, hidden-context input shapes that invalidate token bounds, and writable settled charges. A unique immutable dispatch record also guards the HTTP boundary. The evidence/UX reviews led to intact paragraphs, explicit omission counts, empty-source handling and immediate paused-state refresh after an ambiguous request.

Verification: **64 tests passed in the full backend suite**, two frontend contract tests remain passing, and the extended browser flow passed including model response rendering, original-source access, ambiguous-charge pause and empty-source states. A subsequent timestamp-equivalence regression passed with all 11 focused brief tests; it makes UTC and Singapore representations of the same publication reuse one cached response. Production build succeeds; desktop passage rendering was visually inspected. No paid call occurs in these tests.

Three explicit live OpenAI checks then passed: baseline, contrary renewal news with qualifications, and a restatement excluding the replaced source version. Each identical request was repeated without another dispatch or charge. **Total accounted cost: US$0.00221475 of US$10**, three settled calls, zero reserved/unresolved charges (1 October 2026). Raw responses, request identities, token usage and charges are in the original private database; local test records are under `.local/live-tests/`. This is a small integration check, not extraction accuracy, balanced research or investment validation.

Migrations 001–003 are now applied; the data backup and matching phase-1 source are retained under `.local/backups/`. No existing saved records were changed during either upgrade. [Provider controls](../../development/live-provider-controls.md) and [implementation tracker](implementation-tracker.md) describe current limits and the remaining full-plan work.

## Phase 3 — company research, saved ideas and material updates

Two independent authored companies now use the same transactional acquisition contract. Evidence versions, facts, coverage checks and instrument progress commit together. An immutable shared snapshot log and private per-revision cursor let a worker catch up on every accepted transition after downtime. Consecutive unchanged polls produce no new assessment; outage → recovery → repeated outage does. Exact copied content retains its provenance without a duplicate alert.

The interface adds company search and a mobile selector, **My ideas**, and **Updates** across saved companies. Updates identify the changed metric, old/new periods and exact prior assessment. Assessment links survive reload; unavailable links are explicit. Each company retains its own reasoning, progress and reviews. Aurora's absent price feed is shown as unavailable.

Verification: **84 backend tests and 2 frontend tests pass**. The extended browser journey passed company switching at 320px, independent reasoning, repeated idea/update navigation, exact assessment reload, both-period metric labels, invalid links, grouped-source provenance, existing conflict/approval/history flows, mocked model pause and 320–1440px overflow checks with no browser errors. Mobile updates and desktop rendering were visually inspected. The production build passes. No new live API calls were made; accounted spend remains **US$0.00221475 of US$10**.

Three AI reviewer threads re-reviewed corrections and found no remaining blocker for this bounded recorded release. See [phase 3 review](../../reviews/2026-10-01/phase-3-company-review.md). New migration 004 preserves earlier history while adding company research, lineage, snapshots, private cursors and change events. Matching pre-upgrade source and a database dump are retained locally under `.local/backups/`; the update verifies every preexisting row, including model accounting, and that `.env` is unchanged.

This is a reusable local contract exercised by two authored companies. It does not establish real coverage, independent source corroboration, financial-fact expiry, investor usefulness or commercial viability. General extraction, real fiscal facts, permitted live sources, typed catalyst/proposal workflows and production authentication remain on the implementation tracker. The 24-hour coverage rule measures source-check age only.


## Phase 4 — SEC fundamentals capability (2 October 2026)

The app can add Microsoft, Apple and Alphabet filing workspaces, manually refresh the SEC submissions/companyfacts APIs, retain parsed source payloads and calculate same-accession revenue growth and operating margin. Annual versus quarterly scope is explicit in observations, conditions, conflict resolution and history. Actual fiscal dates and a calculation trail link back to the filing. Missing/amended/conflicting inputs remain unknown; older responses cannot move the current period backwards. SEC content does not enter the authored-only OpenAI route.

This phase is **offline verified**. The requested contact identity is still pending; no live SEC request or reconciliation against an actual filing has been performed. The recorded samples remain the ready-to-use demonstration. This is not a live news/price/consensus connection.

Verification: **108 backend tests passed in the full suite**, including synchronized clock/commit concurrency and a corrected source returning to an earlier value while preserving all intermediate history. **2 frontend contract tests pass**, including annual-period preservation. Both complete browser journeys passed with no page exceptions: recorded research/history and synthetic SEC data, direct source calculations, annual/quarterly approval reset and mismatch explanation, scope-only edit conflicts, add-company failure inside its modal, immediate denied coverage after failure, unavailable configuration and empty new company. Layouts at 320–1440px were checked and SEC desktop/mobile renders inspected. The production build passes.

No additional paid request occurred. Accounted OpenAI spend remains **US$0.00221475 of US$10**. Migration 005 adds the SEC evidence/calculation tables and restricted shared-source role, preserving previous rows and source history. Pre-upgrade source and database backup are retained under `.local/backups/`. Existing private environment values are preserved; only a blank SEC_USER_AGENT entry is added if absent.

[SEC contract and pending live verification](../../features/sec-fundamentals.md) · [AI consultant review and corrections](../../reviews/2026-10-02/phase-4-sec-review.md). The remaining full-plan work includes broader metrics, observation expiry, catalysts/proposals, permitted news acquisition and synthesis, valuation scenarios and validation of user usefulness. None is treated as complete by the passing software checks.


## Phase 5 — optional reporting-age limits (2 October 2026)

Each numerical condition can now set a maximum number of days since its reporting period ended. The editor previews the period, age and expiration; changing or clearing the limit requires approval again. Expired evidence becomes unknown while preserving its last figure/source. Reporting age and source-check freshness are separate. Blank limits preserve existing behavior.

The worker freezes assessment time separately from source cutoff, catches distinct deadlines in order after downtime, preserves exact historical definitions and avoids duplicate clock alerts. Recorded examples use scenario time; SEC workspaces use UTC wall time while the app runs. Local polling reveals background changes without fetching financial data. Expiry-only updates explicitly say no new figure was received.

Verification: **123 backend tests and 3 frontend contract tests pass**. The three complete browser journeys passed: original recorded research/history, extended synthetic SEC/age editing and conflict handling, and background delivery of two expiry updates followed by their exact historical clocks. Tests cover exact UTC boundaries, leap/fiscal dates, invalid limits, retained values with fresh coverage, distinct deadline ordering, no new fetch, archived ideas, restatement age, clearing limits, recorded-clock isolation, legacy pending manifests and synchronized saving versus acquisition. Desktop/mobile editor, expired result and Updates screenshots were inspected; tested widths range from 320 to 1440px. The production build passes. All tests use synthetic/authored inputs and make no paid calls.

Three AI reviewer threads accepted the corrected scope. Review identified queue-order, cursor, legacy-manifest and source-watermark requirements; implementation and a synchronized regression address them. Migration 006 appends nullable limits, a private assessment cursor and durable queue order. The upgrade preserves existing semantic rows, all immutable evaluation/source history, the private environment and the model ledger, with matching source and database backup retained under `.local/backups/`.

Accounted spend remains **US$0.00221475 of US$10**, with no additional provider calls. This is user-defined numeric evidence eligibility, not expected filing dates, catalyst expiry or validated financial guidance. Those workflows, typed proposals, broader metrics, permitted live news/synthesis and the pending SEC filing reconciliation remain on the full implementation plan.

[Reporting-age contract](../../features/reporting-age.md) · [AI review](../../reviews/2026-10-02/phase-5-age-review.md).

## Phase 6 — real-company pitch research (2 October 2026)

The user clarified that this is a pitching MVP and authorized Finnhub without the previous compliance prerequisite. The installed workspace now retrieves a timestamped quote and up to 25 company-news snippets. Company-name/symbol mentions rank ahead of broader market coverage, newest within each group. Quotes are stored separately from research monitoring; news retains source, first-seen time, immutable corrections and company-scoped identity. Empty, failed and interrupted checks remain distinct.

An explicit **Summarise sources** action generates a concise source-linked briefing from up to ten deduplicated news items and active SEC context. Company reasoning stays private and out of the shared model packet. The reviewed second prompt produced four concise, attributed points, including the CNBC executive-departure report. It removes duplicated raw SEC figures. An AI evidence reviewer found no material mismatch against the supplied snippets. This is bounded integration/quality feedback, not a model-accuracy benchmark or customer validation. A remaining teaser phrase and a combined-news point are noted as presentation limitations.

Microsoft live evidence:

- Finnhub refresh at 2026-10-01T18:12:04Z succeeded for both endpoints; quote USD515.19, provider time 18:11:42Z, 25 retained articles. This is a recorded retrieval, not a real-time-price promise.
- SEC accession `0001193125-26-323660` inputs were reconciled against the original HTML's non-dimensional inline-XBRL USD contexts. Revenue/prior revenue/operating income match exactly. A later permitted SEC refresh returned `changed=false` and preserved facts, source versions and the first cached briefing.
- Two live market briefing versions were run deliberately during review. Both identical repeats reused the saved response without another charge. Together with three earlier authored calls, accounted spending is US$0.01260675; five settled, zero unresolved.
- The supplied CNBC wrapper returned 302 to its publisher. The publisher rejected the programmatic request with 403; no bypass or full-article extraction was attempted. Stored evidence remains clearly a provider headline/snippet.

Final browser checks covered real company landing, quote/source timestamps, concise brief, source modal, original filing trail, accessible mobile Save idea and no horizontal overflow at 320/390/768/1056/1440px. Opening the app made no paid call and no existing saved-user content was edited. The disposable market journey additionally saved/reloaded reasoning and distinguished empty versus failed feeds.

Migration 007 was installed after a source/database backup at `.local/backups/phase6-20261001T181125Z/`. The installer verified every preexisting row and the ledger were preserved, and private settings were unchanged; the authorized Finnhub enable flag was then changed separately while preserving all other values. The earlier brief implementation and all original paid request/response records remain retained. Private integration records are under `.local/live-tests/`.

[Market contract](../../features/market-research.md) · [Consultant review](../../reviews/2026-10-02/phase-6-market-review.md). The wider backlog remains separate from this local pitch: catalysts/proposals, additional metrics, production accounts, notifications, billing and public deployment are not represented as implemented.


## Phases 7–8 — actual evidence, saved interpretation and portable review

The implementation now pairs exact changed sources with immutable saved reasoning, supports explicitly requested private comparisons for drafts and assessments, and preserves their access after later snapshots, edits and archive. Mini's real-evidence semantic errors and a later truncated-source failure are retained; a stronger model plus filtered eligible passages met twelve corrective core cases. Shared summaries were reviewed separately, corrected through v6, and all three latest actual-company results are cached. No matching quotation is treated as proof of its interpretation.

A selected record exports through the authenticated, owner/source-scoped API. Code/source versions remain pinned, private notes are disclosed, script/URL injection is escaped/rejected, and unavailable source dependencies are withheld. Normal exports and old-history reads make no paid call. Export browser fixtures and the installed real Google endpoint were verified; the in-app download-event automation itself did not complete.

Migration 009 records only explicitly authorized maximum-cost holds outside ordinary application write privileges. The user authorized continuation after reporting US$0.87 / 56 dashboard requests; the original timeout keeps its full reservation, unknown usage and error record. The cap check includes both confirmed spend and all held maxima, preventing a hold from creating more allowance. The original request cannot be redispatched.

230 offline checks passed with the actual SEC replay corpus, three frontend checks/build passed, and the extended idea/export and focused market browser journeys passed. The final prompt-only correction additionally passed 38 focused checks. See the overnight report for exact artifacts and independent-review limits. Catalysts/deadlines, typed proposals, broader fundamentals/valuation and scheduled acquisition/digest remain outstanding product work. Production accounts, billing, external notifications and deployment remain outside the current local pitch.


## Phase 20 — question-focused research, 2 October 2026

The optional question workspace now answers a specific research question before a saved idea is required, using existing news, Reddit posts and annual/direct-quarter filing tables. It supports exact citations, gaps, bounded follow-up, private history, source inspection and local download. Source categories come from stored citation metadata; generated prose remains AI interpretation. No watch or saved idea is created by asking. Migration 017 preserves owner isolation and immutable history.

Verification: 466 integrated backend checks, 22 focused question checks, five frontend checks/build, question and prior sentiment browser journeys. Eleven actual-source calls retained several evidence-type/attribution errors and targeted corrections; 99 exact quotations do not establish universal correctness. The final Microsoft answer and earlier warned versions are available in Question history. [Contract](../../features/question-research.md) · [Five-perspective review and evidence](../../reviews/2026-10-02/question-research-phase-review.md). Original cumulative spending: US$4.193536 confirmed plus US$0.13926 maximum hold, no new unresolved charge.


## Phase 23 — broader company coverage and fuller alert evidence


Phase 23 verification: 528 backend tests, five frontend checks/build and catalogue/sentiment/private-alert browser journeys pass. NVIDIA/Amazon/Meta have actual quote/news/chart data and 122 selected financial inputs reconciled across six original filings, then replayed into the installed app. Each has 252 daily sessions and 1,260 raw OHLCV-field matches. Three sentiment requests match 10 of 11 frozen selected criteria; retain the unsupported adverse Amazon transaction label. An initial NVIDIA alert omitted a fuller report because of within-request semantic deduplication; the code correction and two explicit retests preserve fuller evidence. All three final authored QA questions have expected direct answers, with 61 exact private quotation associations. These are development checks, not an independent accuracy study. Main private state is unchanged and watches remain off. Eight phase calls cost US$0.411555; cumulative US$4.7155785 confirmed plus the original US$0.13926 maximum hold, 146 calls, US$5.1451615 remaining. No new unresolved charge. [Five-perspective review and evidence](../../reviews/2026-10-02/catalogue-phase-review.md). Full plan and participant validation remain incomplete.


Phase 24 improves neutral-transaction sentiment and adds a same-sample original-source reading view. Method changes cannot alone create aggregate reversal alerts; historical records stay unchanged with a warning. Five requests match 31/31 selected development criteria, not a broad accuracy benchmark. 531 backend tests, seven frontend checks/build and three browser journeys pass. The retrospective alert baseline retains six preselected answer reports from 32 selected texts; user benefit is unmeasured. [Contract](../../features/sentiment-source-reading.md) · [Five-perspective review](../../reviews/2026-10-02/sentiment-calibration-phase-review.md). Broader source coverage, actual-user validation and the remaining full-plan capabilities remain incomplete.


Phase 25 fixes omitted neutral/favourable updates to previously watched reporting and shows both cited reports in alerts and weekly exports. Five saved-output replays pass their delivery checks; three previously silent cases now alert. The constructed timeline and authored contrasts are not prospective monitoring or broad accuracy evidence. 541 backend checks, seven frontend checks/build and a dedicated browser journey pass. [Contract](../../features/reporting-updates.md) · [Five-perspective review](../../reviews/2026-10-02/reporting-updates-phase-review.md). The next presentation concern is a clearer combined review inbox; full-plan and participant requirements remain incomplete.
