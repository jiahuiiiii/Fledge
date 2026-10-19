# Sleep recovery — 20 October 2026

Read-only investigation on 19 October at about 22:15 SGT, followed by offline code changes. The running app (started 18 October 23:40 SGT) was not restarted; these changes apply at the next deliberate restart from the owner's Terminal.

## What was observed

- The Mac's power log shows 47 sleeps between 18 October 23:00 and 19 October 09:00, and continuous sleep from 19:33 to 22:00 on 19 October, with Power Nap wakes of about two seconds every 15–20 minutes. Idle sleep was set to one minute.
- Since the 23:40 start: 128 checks completed, 29 failed, 37 stopped. The stopped checks end at the same minutes as the Power Nap wakes.
- The 29 failures: 10 lane overlaps ("already running for this company"), 10 requests cut off by sleep, 7 checks blocked by those cut-off requests, 2 unexplained `ValueError`s (GOOGL fast lane, 06:13 and 06:29; details are only in the app's Terminal output).
- 15 AI requests were left without a settled response (14 timeouts, 1 transport error), several at the same second (06:31, 08:19, 21:44), which matches a lost connection rather than slow answers.
- "Telegram rating check failed" came from the 1.5-second rating poll failing while the connection was down after a wake. Polling recovers once it returns (last success 22:12). Taps are not lost: Telegram keeps them for 24 hours and the offset only advances after a rating is saved.

## Changes

| Problem | Change |
| --- | --- |
| Requests sent during the seconds after a wake are cut off and can never be resent | `thesis/wake.py` detects sleep from the gap between wall time and the awake clock (`CLOCK_UPTIME_RAW`). Scheduled news, price, filing and Telegram loops wait until the computer has been awake for 90 seconds. `ledger.execute` refuses live requests in that window before reserving anything (`WakePaused`). User-facing loading and evaluations are not paused; their AI requests are covered by the ledger check. |
| One unsettled request fails the company's whole reading | The quick relevance check and the tone, event and duplicate tasks raise `HeldSources` naming the affected sources. A scheduled reading leaves out only those sources, saves a reading of the rest with `held_sources` (ids, channel and reason only) and a distinct request key. Held sources are never resent. Explicit re-reads, retries and split recovery still stop. If every source is held, the check fails as before. |
| A partial reading could look like a sample shift | A reading with held sources publishes no alert and does not replace the watch baseline, so the next complete reading is compared with the last complete one. |
| Log noise and misleading failures | The rating and delivery polls back off up to 60 and 120 seconds and log once per outage (error type only) and once on recovery. Lane overlaps and wake pauses are recorded as stopped with `skip_reason`, retry after three minutes and share the two-quick-retry limit, because each retry fetches sources again. App-authored blocks are logged in one line without a traceback. |

No schema change. No setting, saved research or account preference was changed.

## Verification

Offline only, with invented clocks, mocked providers and the disposable test database.

- New `tests/test_sleep_recovery.py`: 12 tests covering wake detection (a sleep, repeated Power Nap wakes, small and backwards clock corrections), back-off and its log lines without transport text, no reservation during the wake pause, held sources from the quick check and from a tone task, a scheduled partial reading and its free reuse, explicit recovery and fully held samples still stopping, a partial reading publishing nothing and keeping the baseline, and overlap or wake skips retrying within the limit.
- The six related suites (prefilter, task runner, failure feedback, check history, lanes, alert feedback) passed with 110 tests before the new file was added.
- Full offline suite (192 files): 2,847 passed, 93 skipped, 0 failed in 8 min 38 s. The skip reasons were not inspected.

## Limits

- Sleep that starts in the middle of a request still leaves that one request unsettled. The change stops new requests during Power Nap and stops one cut-off request from blocking everything else.
- When the held sources are removed, later batches can shift and be sent as new requests with different content. These are not resends of the unsettled request, and the same thing already happened whenever new articles arrived.
- While a company has held sources, it publishes no news alerts until a complete reading is possible, for example after the held article leaves the seven-day window or a new article changes the batch. This is shown in check history and is no worse than the earlier failed checks, which also published nothing.
- The 29 unsettled requests remain unsettled and retained. Nothing here reviews or settles their charges.
- Not verified on a real sleep and wake cycle. That needs the restarted app and one night with the lid closed.
