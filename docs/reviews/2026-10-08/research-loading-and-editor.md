# Phase 77 — visible research loading and a simpler idea editor

The owner's 8 October usability feedback replaces the fragmented manual refresh flow. Preserve their actual Broadcom workspace and current watch choices. The earlier instruction to leave an empty workspace until Wednesday is historical: the owner has now started testing. No reset was performed.

## Implemented journey

Opening a registered company for the first time queues quote/news, SEC filings/fundamentals, daily chart history, Reddit, Hacker News, analyst targets and reference multiples. Four workers run independent steps concurrently. The first open does **not** request paid AI analysis or enable a watch. Subsequent opens retrieve saved state; **Refresh research** requests another source check under each provider's existing cooldown.

The durable owner-scoped queue survives navigation and reloads. Its progress bar measures finished steps, including clearly labelled failed/partial/cooling-down steps, rather than estimating seconds or pretending all completed steps succeeded. **View progress** shows each step and its current explanation. Failed steps do not erase earlier data or block unrelated acquisition. A single process lease prevents a second local server from recovering live jobs; interrupted steps cannot be overwritten by a late worker and are not automatically replayed. Queued, undispatched work can resume.

**Refresh & analyse** is the single sentiment action. It checks news and discussions, then queues the existing v16 model analysis after those checks. Active AI work and uncertain charges have different states. A genuine uncertain charge requires review; the UI does not claim an automatic confirmation is running. The original cumulative budget and no-automatic-paid-retry rules remain in place.

Discussion windows are **24 hours, 7 days (default), or 30 days**. News stays at seven days. Reddit still supplies only the latest 50 posts from each of three feeds; this is not a historical archive. HN uses a bounded company-name search, verifies original comments, retains request pacing and respects withdrawals. Selecting 30 days cannot guarantee a larger sample. The saved analysis records its discussion window; current-source preview follows that saved window. Non-default windows have separate saved identities but can reuse an identical settled model response. They do not publish company-watch alerts or advance its baseline. Automatic watches retain their existing seven-day contract.

Registered company names now participate in conservative social matching. Broadcom Inc. becomes the exact alias Broadcom; explicit ticker syntax remains supported. Legal suffix stripping does not introduce fuzzy matching. Common standalone names such as Target still require explicit financial context. Existing curated company rules remain unchanged. Name matching selects candidates, not verified investor relevance.

The reasoning dialog now leads with the question and reasoning. Financial/event conditions are in an optional disclosure; existing conditions and proposal review remain visible. Draft saving, expected revision checks, condition identities, threshold ownership and explicit monitoring approval are preserved. Source-only refresh controls and their instructional copy are consolidated.

## Verification

- Full isolated backend run: **1,157 passed, 59 skipped** (optional retained-source corpora were not configured). A final overlapping suite after the worker-ownership/fencing addition: **138 passed**, including two additional safeguards.
- Frontend: **27 checks passed** and a successful production build.
- Desktop browser: first-open queue and automatic chart display using isolated mocked sources; optional condition editing and draft save; custom 30-day selection; queued fetch/analysis and saved 30-day result; installed Broadcom chart, running AI status and source coverage inspected.
- The first broad run retained five failures. Two recurring-event fixtures assumed the current date was in the first six days of the month; their authored reporting window now includes the test day. The new queue tests exposed final blocked-state completion and a test source-cooldown leak, both corrected. One reporting-deadline check failed in that run but passed its isolated rerun and the final broad/focused runs without a production code change. These original results are retained.

Actual Broadcom source refresh finished in about 13 seconds. Quote/news and SEC succeeded. Previously loaded price history, targets and multiples correctly reported their provider cooldowns. Reddit remained partially inaccessible (rate limits). HN produced one verified eligible discussion where the prior ticker-only search/matching had produced none. The following actual sentiment run processed eight news sources and one HN comment and completed in about 71 seconds. The HN tone was **unclear**, not silently treated as neutral. This establishes the acquisition-to-saved-result workflow for one case, not broad sentiment accuracy or alert usefulness.

The one new paid check cost **US$0.1013025**. After it: **US$17.140737 confirmed**, **US$0.60249 prior maximum-accounted holds**, **US$12.256773 available** of the original US$30; 319 cumulative calls and no new unresolved request. The owner made an additional call while this work was in progress, so changes from the initial backup's totals are not all attributable to this phase. No watch was enabled by this work; the owner's already-enabled filing watch remains enabled.

Evidence: `.local/live-tests/research-loading-phase77/`. Pre-change database/source backup: `.local/backups/phase77-loading-20261008T004029Z/`. Migration 037 is additive. Model prompts, profiles, historical labels and the phase76 local-model experiment were not promoted or altered.

## Five-perspective review

These are one implementer's review lenses, not five independent reviewers.

- **Product:** one source refresh and one sentiment action remove the extra coordination burden. AI remains an explicit paid action.
- **UX:** progress and a focused draft form address the observed confusion. Provider failures are visible, not equated with neutral sentiment or disguised as loading.
- **Architecture:** bounded workers, atomic claims, forced owner scoping, a process lease and late-result fencing protect durable work. The server and awake Mac remain necessary.
- **Evidence:** exact company-name candidates and wider windows improve acquisition options, not model accuracy. Thin samples and unavailable Reddit feeds remain material limitations.
- **Validation/business:** the owner can now test the journey with real data. Existing semantic failures, independent participant evidence, broad source coverage and production operations remain open; this is still a local pitch MVP.
