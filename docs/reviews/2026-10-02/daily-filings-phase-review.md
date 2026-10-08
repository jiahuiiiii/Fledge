# Daily-filing monitoring review — 2 October 2026

This is a parent-authored review from five perspectives, not independent consultants or participant research.

| Perspective | Purpose check and decision |
| --- | --- |
| Product | Acquisition must run for numerical alerts to notice new financial results. Add explicit daily SEC monitoring alongside existing news/social watches. Do not equate a fetch with an alert or change a saved investment idea. |
| Research/data | Preserve exact filing identities, annual/quarterly scopes and reporting age. Label the narrower structured-figure coverage, source failures, supplier lag and local downtime. Six-company replays establish compatibility, not prospective recall. |
| Engineering | Reuse the existing acquisition, snapshot, evaluation and publication path. Owner-scoped schedules, immutable journals, shared cooldown, leases and one overdue check address concurrency/restart risks. No new model calls, framework or external destination. |
| UX | Keep the control in Fundamentals, show the latest failure without requiring history expansion, and explain the first check, 24-hour cadence, local-only operation and stop behavior. Exact recorded source links and paged history support review. |
| Commercial/evaluation | The added recurrence supports the pitch's monitoring promise. It does not establish retention, timely detection, paid demand or advantage over ordinary alerts. Actual users still need to judge relevance and understand what is unmonitored. |

Iteration after review: distinguish the shared cooldown from a successful unchanged check; show failure status in the collapsed view; reject late completion as unconfirmed; preserve a newly enabled watch against an older completion; retain failures without immediate retry. Successful acquisitions feed existing monitoring, so there is no duplicate alert publisher.

Initial software verification: **630 integrated backend tests**, including both saved actual-filing corpora; **12 frontend checks and production build**. Focused and browser logs are retained. Tests use no live providers. Browser toggle responses are explicitly mocked, while the real API/scheduler is separately exercised in disposable databases. Live retrieval and installation verification follow below. The main account is not enrolled automatically.


## Installed verification

Installed schema 22 with backup `.local/backups/phase30-daily-filings-20261002T131502Z/` and evidence `.local/live-tests/daily-filings-20261002T131503Z/`. All preexisting rows and private configuration were preserved by installation. **630 integrated backend checks**, followed by **36 final focused checks** after the completion-lease guard, pass. **12 frontend checks/build** and filing-monitor, financial-performance and weekly-review browser journeys pass. The six supported companies were replayed from retained actual SEC responses; all repeats preserved their figures and reported unchanged inputs.

One actual Microsoft SEC submissions/companyfacts retrieval ran through a separate QA owner's daily monitor and returned **unchanged supported inputs**. Its exact checkpoint links the 10-K for the period ended 30 June 2026. The QA watch was stopped. No new main-account definition, evaluation, watch setting or published alert changed; only the existing worker's consumed-snapshot cursor advanced. The first overly broad all-private-table assertion flagged that expected cursor movement; the failure and diagnosis remain recorded, and no source call was repeated.

This phase made **zero paid requests**. Confirmed cumulative spend remains US$6.167211, with the original US$0.13926 maximum hold still retained (actual charge unsettled), 171 calls and US$3.693529 remaining. All main watches and the QA filing watch are off. Daily checks run only after explicit enable and only while the app runs. Actual future-filing detection, alert timeliness, participant comprehension and paid demand remain unverified.
