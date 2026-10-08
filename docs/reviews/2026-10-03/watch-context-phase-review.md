# Phase 39 — optional original-parent checks in watches

This is one agent's review from five perspectives, not independent consultant signoff or participant evidence.

| Perspective | Finding | Response and remaining limit |
| --- | --- | --- |
| Product | Parent-aware models still depended on opening each source manually, weakening the recurring monitoring workflow. | Add an explicit default-off watch option that prepares bounded original-parent context before the existing sentiment call. Broader investor-discussion coverage remains missing. |
| Research | A reply edit detected after acquisition could leave old wording in a newly interpreted sample. | Stop that attempt before model analysis; preserve the old source and let a later refresh acquire the edit. Missing/failed context stays visible, and parents never become additional votes. Semantic attribution still needs live evaluation. |
| Data/ML | More context can add input costs without establishing better quality. | Reuse recent eligible parents, preserve the four-parent/eight-request and model passage bounds, and use the existing model call/ledger. No quality or cost-to-serve claim follows from software checks. |
| Architecture | Additional source work can outlast a watch claim or race a stop/change. | Check claim ownership and expiry before dispatch stages and between source requests; block late automatic publication. Reuse the existing collector, request clock, source store and owner-scoped journal. |
| UX/business | Users need to distinguish disabled collection, missing context and a quiet result. | Expose an opt-in control with scope/cost copy and immutable per-check context counts. A disabled collection option can still use already saved context; the UI states this. Actual comprehension and recurring value remain unmeasured. |

## Verification and retained limits

The initial focused suite passed 57 checks. The first integrated run passed 783 checks, including both real filing corpora and two retained original-HN replay cases. A later review added a regression for expired model completion and strengthened automatic publication fencing; final verification is recorded below after completion.

The browser checks six authored attempt outcomes, context details, explicit opt-in, frequency/reload persistence, stopping and opting out, source coverage and update navigation at 320/390/1440px. The first browser invocation used an unsupported `--watch` flag and silently ran the general journey. That general regression passed, but it did not verify this feature. The runner now rejects unknown/multiple journey flags before starting a database. The first correct journey then exposed a test waiting assumption for server-confirmed controlled checkboxes; the harness was corrected to await confirmed UI state and the watch journey passed. These failures are preserved rather than counted as feature passes.

The original-HN replay preserves five exact child-parent identities and timestamps across Microsoft and NVIDIA, dispatches ten mocked original-item reads from retained real responses, and confirms the resulting bounded model inputs. The test deliberately raises at the model boundary, so its attempt is recorded as failed at sentiment analysis, with completed context acquisition and zero model calls/publications. This is an acquisition replay with an authored schedule, not live monitoring, a generated answer or a semantic evaluation.

All automated sources/models are mocked. No main/QA watch is enabled, no new actual model response is published, and the phase-34 unresolved charge still blocks fresh paid dispatch. Earlier semantic failures remain evidence. Full-plan, prospective alert and participant validation remain incomplete.

## Final verification and installation

The final integrated suite passes **784 checks**, including both retained real filing corpora and the two original-HN replay cases. Twelve frontend checks and the final production build pass. The final watch browser journey passes after the lifecycle changes and final control copy; the unsupported browser flag now exits with an error before database creation.

Backup: `.local/backups/phase39-context-watch-20261002T233644Z/`. Evidence: `.local/live-tests/context-watch-20261002T233646Z/`. Migration 026 applied successfully. Every preexisting column value and database record is preserved; added option fields default to false on existing settings and check headers. The private environment is unchanged. The installed app runs on port 8841, and the browser verifies that the new option is off/disabled while the company watch is off. No watch was enabled during installed-app inspection.

The original model budget is unchanged: US$7.407271 confirmed, US$0.301565 reserved, US$2.291164 remaining, 194 calls and one blocking unresolved charge. This phase makes no actual supplier/model call and publishes no new research. The replay source files are retained and hashed alongside the logs; no model response is invented to make the replay appear successful.
