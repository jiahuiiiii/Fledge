# Discussion summary feedback — 9 October 2026

The owner reported that **Read themes from this sample** appeared to do nothing and asked what the control was for. It creates an optional source-linked reading of recurring topics, differing views and unresolved questions from the relevant texts in the saved sentiment sample. The source filter selects displayed themes; generation reads the whole sample.

## Actual failure

Read-only inspection identified call `e5ba85ee-985f-41f0-be1d-ea634510f2b3`, started at 10:00:25.464554 SGT and settled at 10:01:43.593290 SGT. Its provider status is `incomplete`, reason `max_output_tokens`, under the existing 6,000-token profile. The response contains reasoning with no output message. It charged US$0.1023675; no evidence-check call or saved theme review followed. This is a response-limit failure, not an established transport timeout or exhausted account allowance. The stored call and response remain unchanged. This task did not retry the paid request or produce a new actual reading.

The screenshot's generic “New AI readings are unavailable” message was a separate UI error. `enabled` treated every unresolved reservation as unavailability, including this component's own running request. Thus the progress button and a contradictory warning appeared together while the request was working.

## Change

- The button is **Summarise discussions**, with a short explanation of its output, whole-sample scope and the existing two paid steps.
- Idle availability now uses the shared model checks, including running work, billing attention and exhausted allowance. Missing or withdrawn samples and a busy workspace have their own explanations. Blocked generation leaves saved history accessible.
- Its own running request shows progress without the generic unavailable warning. A read-only AI-status refresh precedes the completion state, so progress and success/failure are not displayed together. The existing request sequence protects against late results after a scope change.
- Successful results show “Discussion summary ready below.” Failure retains existing saved reading content. The specific provider response-limit failure says no reading was saved, budget was used and no automatic retry occurred.

The prompt, model, request body, response limit, metering, cache identity, source permissions, watches and retry policy remain unchanged. An explicit repeat of an exact cached incomplete synthesis continues to report its failure without another synthesis dispatch. No claim of improved model completion or semantic accuracy is established by this presentation/error change.

## Verification

The guarded focused backend suite passed **35 tests**. A new case reproduces a settled incomplete response, checks the cost disclosure, confirms no publication or evidence-check request, and repeats the explicit action to verify one dispatch and an unchanged charge. All **47 frontend checks**, build, targeted formatting and browser-script syntax passed. The build retains a roughly 504 kB entry-chunk warning.

The final guarded `--themes` browser journey passed with authored data and mocked responses: platform filtering, exact citations and original source dialog, parent evidence, current/legacy history, cached generation, export, unchanged watches/sentiment labels, a delayed request whose reservation is observed by polling, refreshed success state, response-limit failure with/without saved history, accessible blocked reasons, readable history while generation is blocked, withdrawal and 320/390/1440px layouts. Four generation POSTs are a cache read or controlled browser fixtures; no paid call occurred. Final pending/error/desktop/phone screenshots were inspected. These are authored Microsoft cases, not an owner-company result.

Retained failures are in `.local/live-tests/theme-feedback-20261009/`: the first browser run lacked the existing automatic-loading fixture, and the second counted an aborted FMP logo request. Both were corrected with controlled responses. The first full-page/element captures exposed a brief simultaneous progress/error state during the status refresh; the final implementation publishes the outcome after that refresh and the verified run passed. Harmless wrong-path reads, an accidental `.gitignore` command and a paragraph patch-context failure also occurred. The first installation safeguard rejected a changed live index before any restart or replacement. The newer presentation build was inspected and backed up, and a fresh build matched the already verified candidate exactly.

## Installation and preservation

Backup: `.local/backups/theme-feedback-20261009/` includes touched implementation/test files plus initial and newer installed frontend assets. Evidence: `.local/live-tests/theme-feedback-20261009/`, including `actual-call.json`, `before-install.json`, `after-install.json`, `installation.json`, the retained browser runs and screenshots.

The verified local app process was restarted only after confirming no active source/watch leases or running/unresolved/attention model calls. The PostgreSQL process remained running. Session/backend readiness preceded atomic index installation; older assets remain, and all 12 candidate assets matched their served bytes. Existing local-pitch login mode and `.env` are unchanged. Schema remains **47**, and all **114 table fingerprints** match across the measured install interval. No migrations were changed or added.

At install: US$22.447824 confirmed, US$0.9156025 historical holds, US$6.6365735 available of the original US$30; 388 calls and zero blockers. Initial diagnosis had 386 calls; two other app calls appeared before the pre-install audit. This task requested no live source, AI, email or Telegram dispatch and does not claim globally zero concurrent app traffic. Forecast-access restrictions and the broader original goal remain separate.
