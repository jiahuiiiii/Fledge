# Scheduled watch check history

Expand **Watch check history** in the news/social panel to see recorded scheduled attempts for the selected company. This is private, read-only history: opening it does not refresh data, invoke AI or enable a watch. It starts with this version; older checks are not guessed from mutable status fields. Manual analyses remain separate.

Every claimed attempt records its owner, company, start, original lease, watch cadence/scope, baseline and current saved revision. A separate immutable completion records successful steps, the precise failed stage, selected/candidate news/social counts, original analysis timestamp/cutoff and counts of grouped updates actually produced. The original idea-check ID is retained. Existing shared acquisition, deduplication, late-result checks and one cumulative model ledger are reused.

Completed, failed, stopped/changed and missing-completion attempts have different wording. An attempt without a completion may show “No result yet” during its recorded lease; it is not a verified live-process signal. Once its lease ends or its watch/token changes, it shows “Completion missing.” A failed/interrupted check never becomes a quiet success. After a crash, publication already committed before the crash remains preserved even if the completion record is missing. The history does not reconstruct unrecorded intermediate stages.

Quiet outcomes distinguish the first baseline, no new eligible text, a result superseded by an edit and no triggered alert within the bounded sample. None establishes that nothing important happened. A source status snapshot at completion preserves partial errors even after a feed later recovers. Failed news/social coverage remains explicit beside a completed analysis. A quote failure is separately shown; quotes do not determine news alerts. Reused analyses retain their original save time and source cutoff.

Finnhub's existing five-minute cooldown now raises the app's typed conflict, letting a watch reuse the recently retrieved shared coverage. This does not retry HTTP or ignore failures. Source health is still recorded, including a failed recent fetch. Hourly/four-hour scheduling, explicit opt-in and the no-automatic-paid-retry policy are unchanged.

Migration 018 stores starts and completions with restricted owner rows, immutable triggers and owner/company membership checks. History pages have twenty attempts and a stable cursor. Current source permissions can withhold derived analysis details/counts; no source text or raw provider exception is stored in the operational history. Source statuses are frozen at completion, while current withdrawal and no-completion status are evaluated when read.

Timing is elapsed application processing time, not market-event detection latency. The selected sample does not measure whole-feed recall. See the [phase review](../reviews/2026-10-02/watch-history-phase-review.md) for automated checks and the actual-source exercise.
