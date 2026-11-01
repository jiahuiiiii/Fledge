# Setup dialog, Telegram connect and slow cold opens — 1 November 2026

Owner feedback after PR #26: the "Analyse the news" choice could not be
selected while the setup bird was running, with no reason given; "Connect
Telegram" led to the Account page instead of the setup itself; opening Apple
on a phone for the first time showed the loading skeleton for 20+ s.

## Analyse choice in the setup dialog

Cause: the dialog took `modelAvailability(...).blocked`, which is also true
while the AI status is still unknown or another analysis is running. The AI
status was only read after the company read finished, so during a slow first
collection the box stayed disabled and unchecked, and the only text was "AI
analysis is switched off right now."

- The AI status (owner-wide, cheap) is now read as soon as a company opens,
  not after its company read.
- The dialog gets the full availability. Only "switched off" disables the
  choice, with that reason. While collecting it reads "You can choose this
  now. It starts by itself once the news has been collected." (the analysis
  step already waits for sources and queues behind other AI work, see
  `test_analysis_waits_for_sources_and_ledger_then_runs`). Once ready, a
  running analysis elsewhere is named instead.

## Telegram connect

`TelegramSettings` can now be opened by its caller (`open` / `onClose` /
`continueLabel`) without its Manage button. `useTelegramGuard` opens it in
place of navigating to Account; once a chat is connected, the pending action
(e.g. turning on the watch) runs by itself after "Continue". Closing it
without connecting returns to "Connect Telegram first" (turn on without
Telegram, or cancel). Applies to the setup dialog's "Connect Telegram first",
news alerts in News & discussion and other watch toggles using the guard.

## Slow first open: not reproduced; diagnosis added

Measured on a throwaway local instance (disposable database, network
blocked), cold browser opening a company directly: the skeleton waits only
for `session` then `workspace` and cleared at 774 ms. The company read built
in 77–274 ms with 57 SQL statements and 351 KB, also with 300 saved news
items. Real Apple data (SEC) could not be fetched here. Leaving Home cancels
its queued card reads, so at most three are still running on the server.

So the 20 s is on the hosted server, most likely the single web process
waiting for CPU behind its ~15 background threads (see the earlier review in
this folder), possibly on a burstable instance out of CPU credit. Not
verified. To decide it, the "Slow request" log line now also records load
average, CPU count and thread count: a small database share with load above
the CPU count means the request waited for the machine, not its own work.

## Verification

- Frontend `npm test` 262 passed; build succeeds.
- Backend: `test_db_pool.py` + `test_research_loading.py` 29 passed (new
  slow-log test), disposable PostgreSQL 16.
- Browser, throwaway instance with faked AI status, loading run and Telegram
  replies: while AI status was pending the choice was enabled and explained;
  with AI off it was disabled with the reason; "Connect Telegram first"
  opened the Telegram modal on the company page (no Account page), connect →
  check → Continue turned the watch on; closing without connecting showed the
  question again and "Turn on without Telegram" turned the watch on. No page
  errors.
