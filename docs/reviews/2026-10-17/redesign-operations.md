# Redesign operations review — 17 October 2026

The owner identified automatic migrations, uncertain deployed code, high AI cost,
excess rollout complexity, unreadable status docs, sleep-related price gaps and
an unmerged schema branch. This review records the verified findings and bounded
cleanup. It does not mark the redesign or its live gates complete.

## Automatic migrations and approval

`run.py:database()` invokes `apply_migrations()` on every actual startup. The
runner applies all ordered pending files in one transaction, verifies saved
checksums and rejects a checkout missing already-applied files. There is no
approval guard. Describing prepared migrations as waiting for approval was
misleading once they were on disk, and keeping “unapplied” in the current guide
after the 15:54 restart was wrong.

The earlier owner approval covers additive redesign migrations. Accept 065–067
for the next deliberate restart; retain automatic startup upgrades rather than
adding another switch. 065 removes the database's preview-only constraint and
adds a daily-record policy field, 066 adds story claims, and 067 adds assessment
records. Applying those changes does not itself enable the application gates or
enroll an account in Telegram. Applied 061–064 remain immutable. No migration is
edited or added by this cleanup.

At 23:25 SGT the live database is schema 064 with every applied checksum matching.
065–067 are pending **and approved**, not protected by an approval mechanism.
A private full database archive is prepared before the future upgrade; see local
`redesign-operations-20261017/backup.json` for its integrity/catalogue record.
A readable catalogue is not a tested restore.

## Running source versus source on disk

The app process started at 15:54:29 SGT. Exact source at that start was not
recorded. An important correction to the audit: `price-move-rules-2` was saved
at 14:03 and committed at 14:05, before that restart, so it is not established
that this specific fix is absent. Later phase 5 changes were written afterward.
Lazy imports and dynamically read settings also mean “everything is the exact
15:54 snapshot” is too strong. Do not infer a deployed commit from today's HEAD.

The cleanup adds a private startup source manifest before background workers
start, and `.venv/bin/python -m thesis.runtime_status` reports:

- Matching process/start time, startup source fingerprint and current fingerprint.
- Unknown running source when a matching manifest is absent; later file changes
  require a deliberate restart, not a claim that the change is already live.
- Applied/pending migrations, missing or altered applied files and automatic
  startup behavior.
- Named mode summaries and the production feature gates, including start-time
  checks. No new settings or account changes.
- Active work and checks due within 90 seconds. This is a read-only observation,
  not an admission lock or guarantee that no work starts afterward.

The fingerprint describes source on disk at startup, not a memory dump of every
lazily loaded module. Frontend installation is separate. A manifest write error
logs a fixed warning and leaves the app able to start, with version unverified.
The manifest contains no credentials or account identities and uses mode 0600.

## Cost remains a release concern

The 23:21 SGT read-only core report covers 10.7232 hours from 12:38:12 SGT:
43 completed checks, zero failed/stopped and two unfinished. Normal AI cost is
US$2.352457, no unsettled amount, zero closed daily windows. The straight-line
rate is about US$5.27/day, above the US$3 target. It is an early-window warning,
not a measured full-day cost or proof of steady-state spending.

The proposed US$5 notice level is neither approved nor active. No threshold,
model, watch interval or account setting is changed to conceal the cost gap.
Smaller tasks remain off because quality/noise gates are incomplete. Their
replay reused tones; its US$1.88 importance-task cost does not establish total
steady-state savings. A comparable closed-day ledger measurement is still needed.
No paid test or source request is made by this cleanup.

## Scope and modes

Before this cleanup, `main..HEAD` contains 30 commits, 171 changed files,
18,634 insertions, 266 deletions and 12 migration files. That is substantial scope
before the faster cadence or new Telegram delivery has been observed live.

Use existing gates rather than adding more. The status tool summarizes
**Combined research checks**, **Price previews**, **Fast research checks** or
**Fast price previews**; requested new delivery is clearly a custom configuration
with its individual gates shown. These are descriptive names, not aliases that
silently override switches or account preferences.

The immediate sequence stays narrow: deliberate compatible restart, finish the
provider baseline, observe approved fast checks and price previews, resolve
coverage/quality/cost, then seek the still-required new-delivery approval.
Optional discussion weighting and broader additions stay deferred.

## Documentation cleanup

The former 1,927-line / 487,862-byte `AGENTS.md` is retained in the dated
[implementation archive](../../archive/status/2026-10-17-implementation-history.md).
The former 514-line / 46,618-byte plan is retained in the
[redesign archive](../../archive/status/2026-10-17-sentiment-redesign-progress.md).
Relative links are adjusted; historical checkpoint wording is preserved, with a
prominent warning that old budgets, permissions and deployment states are not
current authority.

The replacement guide is 104 lines / about 12 KB; the plan is 170 lines /
about 18 KB. The guide keeps operating/product/evidence rules and current
boundaries. The plan keeps the design, acceptance tests and short status table.
Neither awards a phase pass because implementation exists. Put subsequent dated
progress here or in another dated review, not back into those two files.

## Sleeping Mac and missed sessions

The current move worker returns outside regular hours plus 15 minutes after
close, and `checked_quote` rejects quotes older than 30 minutes. There is no
closed-session recovery cursor. A wholly missed session can therefore be lost.
US regular hours correspond to 21:30–04:00 SGT during US daylight time and
22:30–05:00 during US standard time; early closes differ.

A free authored probe uses the production rules: the stock closes down 4%, the
worker wakes an hour after close, then the next session trades at 97 against
that prior 96 close and a two-session base of 100. The stale close is rejected;
the rebound is only about +1.04% for the day and −3% over two sessions, so no
later threshold recovers the missed −4% move. This is a demonstrated coverage
gap, not speculation.

**Catch-up is not implemented by this cleanup.** The next price-alert change
needs durable, clearly dated closed-session evidence. It must:

1. Start recovery from the approved activation/last checked session, without
   retroactively enrolling a pre-activation backlog.
2. Use complete saved daily bars from one validated vintage, with index context
   from the same session. Missing bars/permissions remain unknown.
3. Retain session date and first-observed time, label the result delayed, and
   share durable session/direction claims with live alerts.
4. Keep explanations within evidence available for that session; never substitute
   today's headlines or automatically retry a paid explanation.
5. Test sleep across weekends/holidays/early closes, rebounds, duplicate recovery,
   provisional/corrected bars, source withholding and partial multi-day gaps.

Do not merely relax live freshness or manufacture a “current” quote from a daily
bar. Closing recovery cannot reconstruct an intraday crossing that reversed
before the close. For a timely overnight alert, the Mac still needs to stay awake
with the server running. No power setting or hosting arrangement is changed.

## Branch and restart boundaries

Remain on `codex/redesign-phase-5`. `main` lacks schema files the current database
requires; it is not a runnable rollback. No merge, push or PR is performed.

The initial 23:25 report treated every `dispatched` ledger row as active. A
read-only investigation found the sole such row dates from 13 October, while
the production `model_activity()` reports zero running requests. The corrected
tool uses that existing active-request contract and reports accounting records
needing attention separately; it neither settles nor retries them. The initial
report also observed an active action, which was gone at 23:36. That later
snapshot is not itself permission to restart: obtain a fresh corrected check.
No app/DB start, stop or restart is performed by this cleanup at this checkpoint.
Recheck immediately before a deliberate owner-Terminal restart; preserve the
current flags. That restart will apply approved 065–067 and load the current
source together. Fast cadence and new Telegram delivery remain off afterward
unless separately activated under their existing approvals/gates.

## Verification and private evidence

Final offline run: **45 passed** across `test_runtime_status.py`,
`test_phase_review.py`, `test_move_watch.py` and `test_integration.py`. Cases cover
source changes, stale/malformed/reused-process manifests, private output,
actual start gates, missing migration files, read-only DB access, due work/leases,
startup write failure, historical-versus-active AI records and existing
restart-preservation behavior. Test workers,
providers and app lifecycle are mocked or use disposable databases only.
The first fixture used an unsupported fictional company; its failure log remains,
and the corrected supported-company fixture passes. The broader historical suite
is not represented as rerun by this cleanup.

Private records: `.local/live-tests/redesign-operations-20261017/`. Preserve the
original/current docs, integrity checks, core observation, read-only runtime
snapshots, authored missed-session probe, test logs and backup metadata.
User `app.css`, `.claude/`, `.env`, saved research and watch/Telegram preferences
are preserved. No live source request, paid call or Telegram send is performed.

Final restart handoff, 23:41 SGT: the corrected read-only check finds two active
news-watch leases, zero running AI requests and no data update, evaluation or
send. Restart is therefore deferred. Historical accounting records remain
separate and unchanged. The computer-use tool also explicitly refuses Terminal
control; the owner's no-sandbox rule still applies. Do not bypass either boundary.
The owner must use Terminal after a fresh clear idle check. The private database
backup is 297,777,713 bytes with 1,214 readable catalogue entries; restore is not
rehearsed. The app remains running and schema remains 064 at this handoff.
