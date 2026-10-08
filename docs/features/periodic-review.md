# Periodic and scheduled research reviews

Open **Updates → Open weekly review**, also available from My ideas. The page combines saved condition changes, company news/social alerts and private reasoning alerts. Reading it makes no source or AI request.

## Current-record review

Choose the last day, seven days, thirty days or all retained records, then filter by company and review status. Counts cover every matching record, independently of the twenty-record page. Older unread alerts, unresolved questions, quiet private checks and acquisition gaps remain separate. Expand source evidence or open an exact assessment in History. Individual acknowledgements remain explicit and append-only.

The period concerns when the app recorded an update, not when the underlying event occurred. Pagination pins its end cutoff. Saved reasoning, source coverage and acknowledgement state are read at generation time; this is not a reconstruction of past account settings. A quiet list does not establish that nothing important happened.

## Optional weekly schedule — phase 50

Expand **Weekly review settings**, choose a day, local time and IANA time zone, enable it and select **Save weekly schedule**. It starts off, with Monday 07:00 Asia/Singapore as the initial choice. Saving a schedule never enables news, filing or AI watches. The next due time is shown in the chosen zone.

While the local app runs, a worker checks for due reviews every five seconds. It reads existing records and saves an immutable overview and membership list; it makes no supplier or model call. A ready count appears beside the weekly-review entry and contributes to the Updates indicator. This is in-app delivery only; no email, push or operating-system notification is sent.

After downtime, the app prepares one review for the latest scheduled week. It discloses how many earlier scheduled weeks were skipped and retains older unreviewed counts. It does not create a backlog of near-identical summaries. Changing the schedule starts from its next future occurrence; saving identical settings preserves an already-due occurrence. Turning it off stops future generation and retains saved reviews.

Weekly periods are open at the start and closed at the end: an update exactly on a boundary appears in the earlier week once. The schedule follows local calendar weeks, which can span 167 or 169 hours across daylight-saving changes. A repeated wall-clock time uses its first occurrence; a nonexistent time moves to the first valid minute after the gap. Python's [zoneinfo](https://docs.python.org/3/library/zoneinfo.html) supplies time-zone transitions; the occurrence policy is implemented by this app.

## Saved review meaning

**Open saved review** preserves the exact membership, company overview, counts, coverage and acknowledgement state from generation. Original event/source records remain authoritative; external source text is not copied into the saved manifest. Reopening and downloading recheck current account/source access, withholding affected content if permission changed. An old review can therefore retain its original counts while its source details become unavailable.

Saved reviews are read-only views of their constituent alerts. **Mark review seen** clears that weekly reminder only. It does not review alerts, approve reasoning or resolve a risk. Use **Open current Updates** to act on an individual alert, or **Back to current review** for today's status. Opening a saved review alone does not mark it seen. A saved-review link survives reload; schedule drafts are not applied before Save.

History pages contain twenty weekly reviews. A saved report displays twenty records per page and exports all its members, up to 1,000. Larger weeks fail visibly instead of publishing a truncated report. Local failures wait an hour before retrying; no paid retry is involved. The user can still inspect the current filtered review.

## Persistence and recovery

Migration 029 adds owner-scoped `review_schedules`, immutable `scheduled_reviews` and append-only `scheduled_review_seen`. No account is enrolled by the migration. Actual application-role row-level security and membership checks reject foreign/fabricated records, wrong periods and duplicates.

Generation holds one schedule-row lock through the local read and atomic report/next-due commit. Competing workers skip that row; interruption before commit rolls back both. Stop or reconfiguration serializes with generation. A review committed before Stop remains valid, but no future generation follows a completed stop. A failed attempt saves a short status/backoff only if its original revision and due time still match.

## Download, coverage and verification

Downloads are inert private HTML containing saved reasoning and permitted source excerpts, with escaped content and a restrictive content policy. An exported file is a point-in-time copy; later source-access changes cannot recall a file already downloaded. No external delivery or production authentication is added.

Watch state, source errors and stale or missing checks remain visible. Daily filing checks are reported separately from news/social watches; when off, filings require manual refresh. Coverage freshness is not financial-fact expiry. The saved overview explicitly reflects generation time, while source access is checked now.

See [the phase 50 review](../reviews/2026-10-03/scheduled-reviews-phase-review.md) for isolated tests, actual-record replay, installation preservation and remaining limits. Phase 13 introduced the on-demand view; its earlier 329-test checkpoint and schema-13 description are historical. This phase adds scheduling, not evidence of user retention or improved AI accuracy.
