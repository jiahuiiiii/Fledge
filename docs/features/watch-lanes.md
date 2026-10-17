# Independent news and discussion checks

Prepared 17 October 2026 for the sentiment/alert redesign. Additive migrations
056/057 were approved by the owner; their offline verification preceded the
live installation recorded below.
No existing account preference, reading or applied migration was edited.

`THESIS_SENTIMENT_LANES=true` enables two independent news workers alongside
the two existing discussion workers. The default is **off**. When off, the
original combined watch and its source behavior remain in use. Each company
can have a news check while its discussion collector is waiting: leases, due
times, retry history and errors are separate. Owner edits invalidate both
claims. Stopped, replaced and expired work cannot publish or renew its lease.
Private idea/event checks retain their existing owner and revision guards.

News checks refresh Finnhub quotes/company news, publisher feeds and Alpha
Vantage using their existing shared clocks, cooldowns, denials and collection
caps. They never collect Reddit, Hacker News or original reply context.
Discussion checks collect the existing social sources and reuse saved news.
Both analyse the current permitted packet; unchanged labels are reused and
no automatic paid retry is added. A single ordered publication baseline and
seen-story set still prevent duplicate or backwards alerts across both lanes.
Fast success cannot clear a slow failure or stamp its collection as current.

The proposed cadence is 15 minutes from an hour before the regular US session
until an hour after it, hourly otherwise. The clock uses `America/New_York`,
including DST. An hourly check before the fast window is brought forward to
its opening. The saved 60/240-minute choice continues to control discussions;
it is not rewritten. The watch dialog and immutable check history distinguish
the two checks and their own results.

The calendar covers 2026–2028 holidays and early closes from the
[NYSE announcement](https://ir.theice.com/press/news-details/2025/NYSE-Group-Announces-2026-2027-and-2028-Holiday-and-Early-Closings-Calendar/default.aspx).
Unknown years use hourly checks until the calendar is updated. Unscheduled
closures are not predicted. This calendar and the cadence need the owner's
live approval before the switch is enabled.

## Incremental discussions

Reddit RSS preserves the entry's update timestamp separately from publication.
A verified comment-feed response can be reused when that timestamp is known,
unchanged and its saved checkpoint is at most seven days old. The exact saved
body is re-parsed against thread identity/date and current permissions. A
changed timestamp fetches again; a missing/invalid timestamp never proves an
unchanged thread. Failed parsing does not advance the checkpoint. Denied access
blocks reuse too. Existing comment/topic limits and missing-parent/date caveats
remain. The alternative JSON/HTML collectors keep their existing behavior.

Hacker News verifies newly discovered comments normally. Retained comments,
including those rediscovered by search, are not re-fetched for 24 hours after a
successful original check. Up to eight due retained comments rotate per check,
so a repeatedly selected newest group cannot starve older comments. Failed
verification does not advance the check time. Withdrawals still apply to every
reading. Search, thread discovery and verified context retain their bounds.

## Measurement, rollout and rollback

`THESIS_SOURCE_METRICS=true`, separately **off by default**, records append-only
HTTP response status codes for the data providers. It stores provider, time,
status and an optional watch-check reference: no URL, credentials, body, personal
details or account identity. Watch-bound references have account isolation;
publisher workers inherit the check context. Local cooldowns are not counted as
new HTTP denials. Data-provider access denials are never retried by this feature.

Before enabling lanes, install the matching backend/frontend safely, enable
metrics and collect at least 24 hours of baseline. Then use
`experiments/soclaas_replay/lane_readiness.py` with that baseline start and the
confirmed lane-start timestamp. It reads one consistent read-only snapshot and
requires three full days, fast median ≤60s, slow median ≤180s, completion ≥97%,
and no increase in HTTP401/403/429 responses per day for any provider. Missing
baseline, empty lanes, incomplete windows and missing deployment confirmation
cannot pass. It reports recorded attempts; missed schedule slots are not inferred.

Turn the lane setting off to return to combined checks. Existing independent
history and source observations remain; old fast claims cannot continue. Metrics
can be switched off separately. Back up `.env` before any change and restart
only in the owner Terminal panel after the required idle/90-second due check.

## Verification — 17 October 2026

- Related offline backend suites: **438 passed**. They cover source collection,
  same-company concurrency, cancellation, private watches, permissions, history,
  ledger, reuse, loading and periodic review. Tests use mocked HTTP/model calls
  and disposable databases, never the app database. Earlier overlapping197pass;
  an expanded run's43fixture errors were fixed by including the new foreign-key
  children in disposable resets. Initial logs are retained.
- Complete offline backend run: **2,194 passed / 93 optional skips**, including
  all migrations, private isolation and source/model boundaries. This overlaps
  the related run; do not add the totals.
- Frontend: **199 tests pass**, temporary production build passes. Isolated React
  settings/history browser: **6 behavior groups**, 1440/390/320px, no overflow,
  browser errors or network requests. Screenshots inspected; no app installation.
- **Acceptance pending:** 0/72 live hours, no measured live medians or complete
  denial baseline. Do not mark phase3 done from offline timing or sample fixtures.
- This work: **0 paid AI calls / US$0**, no source fetch, environment edit,
  live migration, watch/Telegram setting change, frontend install or restart.

Evidence: `.local/live-tests/redesign-phase-3-20261017/`. The separately requested
full-plan continuation is authorised; phase4 work can proceed while live gates
remain explicitly pending. The earlier GPT AVGO lookup found0/15 exact saved
matches and made no paid call; the missing paid replay still needs approval.

## Installation follow-up — 17 October 2026

The app was already stopped when checked: no listener/process, zero active jobs,
four overdue watches and zero newly due within90seconds. The approved056/057
were applied after a full256,951,392-byte archive backup whose catalogue was
verified (no restore rehearsal). Schema is57. The tested30-file frontend was
installed atomically, retaining older assets and preserving the user's CSS.
Ten saved research/preference/ledger table fingerprints were exact across this
preparation; `.env` was unchanged. These checks precede normal resumed activity.

The owner started Fledge from Terminal. HTTP200 and two running combined checks
were verified at12:38:12SGT (04:38:12UTC). Use that conservative verification
time for the phase1/2 observation start. No app or database process was operated
by the implementation tools. New lanes and passive source metrics remain off;
their baseline/three-day acceptance has not started. No new alert delivery was
enabled. Backup `.local/backups/redesign-core-20261017T043032Z/`; preparation and
startup evidence `.local/live-tests/redesign-core-install-20261017/`.

At12:55:59SGT, only `THESIS_SOURCE_METRICS=true` was enabled after a fresh
`.env` backup (`.local/backups/redesign-metrics-20261017T045559Z/env.before`).
This flag is read dynamically, so no restart was needed. The selected models
and all schedules/account preferences remained exact. This begins the24-hour
passive denial baseline; lanes, moves and new delivery remain off.
