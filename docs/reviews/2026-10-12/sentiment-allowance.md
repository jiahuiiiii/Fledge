# Sentiment allowance checked per request — 12 October 2026

The owner explicitly requested removal of the upfront whole-reading allowance
check after NVIDIA's 680-source reading was blocked by a US$28.1890 worst-case
plan despite US$7.0122 remaining. Read-only reconstruction found 13 quick-check
requests with a US$0.474132 maximum plus 87 unfiltered full-reading requests with
a US$27.714850 maximum. These were reservation ceilings, not expected charges.

## Change

Removed `sentiment_batching.preflight` and both whole-plan allowance checks: before
the quick relevance filter and before the full-reading batches. Source/context
size validation still happens before dispatch. The existing two-pass models,
prompts, request identities, source selection and merged-result validation remain.

Every quick or full request still uses the unchanged atomic ledger reservation.
Actual settlement releases unused allowance before the next request. A request
that cannot fit stops before dispatch, preserving completed work for exact-request
reuse. An interrupted reading is not published as a complete or smaller sample.
Unknown-charge blocking, no automatic paid retries, access checks and the same
cumulative US$40 ceiling remain unchanged. Other research routes are outside this
change.

## Verification

126 focused tests passed using mocked transports and a disposable PostgreSQL
database: relevance prefilter, sentiment batching, model budget, failure feedback
and loading workers. Five cases replace the former upfront-budget expectation:

- With or without the filter, a reading can finish when the sum of request maxima
  exceeds the remaining allowance but actual settled charges fit.
- With or without the filter, exhaustion after one full batch preserves that
  result; repeating the exact request reuses completed work without another charge.
- The filter itself cannot dispatch a request whose own maximum exceeds allowance.

Existing tests cover ambiguous charges, explicit retries, source access changes,
cancelled watches, and partial/combined-result publication. The existing Starlette
test-client deprecation warning remains. `git diff --check` passed. No frontend
change or browser journey is needed for this backend-only check removal; the full
backend suite was not repeated.

Evidence is in `.local/live-tests/sentiment-allowance-20261012/`; source backup is
in `.local/backups/sentiment-allowance-20261012/`. The original module exactly
matched the previous installed backend before this change; no concurrent backend
edit was included. Initial restart guards correctly stopped for an active AI
request and for the continuing company's worker lock. Both diagnostics are retained.
The restart waited for existing reading activity to finish. Those paid requests
were existing user/watch activity, not verification calls made by this task.

## Installed verification

Backend-only restart completed from PID 57871 to 85624. The source hashes match
the tested candidate; the app returns the unchanged frontend index
`12b5aeb895d5806c34402422ea94ef41b8887275f649fb8658bf0af6b71dc472`.
The loading-worker advisory lock is held, PostgreSQL was not restarted, and schema
49, private settings and the complete model-ledger fingerprints remain unchanged
across the installation. Final accounting was US$32.57886475 settled plus
US$1.1624375 accounted holds, US$6.25869775 remaining, 622 calls and no unresolved
charge. No paid verification call or NVIDIA rerun was started by this task.

The all-table equality assertion failed after the successful restart: 20 source
and watch tables changed during the window, while the accounting tables stayed
exact. An already-enabled AMD watch began at 00:38:23 SGT, alongside installation,
and new source/check records were retained. The idle guard catches active model
calls and advisory locks but does not fence every scheduled HTTP acquisition;
do not describe this as an entirely idle installation or claim all 116 tables
were unchanged. At final inspection the AMD claim still had its original
00:53:23 lease deadline; this task did not reset its lease or assert its completion.
The original assertion output is retained in `install.log`; successful app/hash/
worker/ledger verification is recorded separately in `verified-installation.json`.
