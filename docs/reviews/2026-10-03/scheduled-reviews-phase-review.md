# Scheduled weekly reviews — phase 50

The optional weekly digest in the plan is now implemented for the local app. Users choose a weekly day/time/zone and receive a saved in-app review of existing updates. It starts off, costs no API credits and does not enable source or AI watches. This completes the bounded local scheduling requirement; the wider plan remains incomplete.

## Behavior and evidence

Saved membership, overview, source coverage and acknowledgement state remain fixed at generation. Original sources are rehydrated through current access checks instead of duplicating their text. Source withdrawal withholds affected details on reopening/export. Opening or marking a weekly review seen does not acknowledge any constituent alert. Individual review actions remain in current Updates.

The local worker commits the report and next occurrence atomically while locking its schedule. Duplicate workers, stop/reconfiguration and failures are serialized. A crash before commit leaves neither a partial report nor an advanced due time. After downtime, one latest-week report discloses skipped scheduled weeks and carries older unread counts. Calendar weeks respect the chosen zone, including daylight-saving gaps/repeated times. Migration 029 adds owner-scoped schedule, immutable manifest and append-only seen records without enrolling an account.

The final suite passes **962 backend checks**, including all five retained actual-source corpora. The new scheduler contributes 23 cases; the focused scheduler/current-digest run passes 35 overlapping cases. Tests cover default-off configuration, invalid inputs, DST, half-open period boundaries, catch-up, failure/backoff, concurrent workers/stop, owner isolation, immutable records, exact membership, pagination, source withdrawal, original reasoning after edits, seen/acknowledgement separation and session protection.

The first full run passed 961 and failed one test: the withdrawal fixture assumed a constraint still existed after earlier tests. The corrected fixture preserves either its original definition or absence. The entire final suite then passed; retain both logs. This was a test setup failure, not a successful first run. The existing Starlette/httpx test-client deprecation warning remains; no dependency migration is part of this feature.

Fourteen frontend checks and the build pass. New scheduled-review and existing current-review browser journeys pass at 320, 390 and 1440px. They exercise saving/stopping/reloading settings, quiet-week coverage, saved deep links, original-source dialogs, complete private download, explicit seen behavior, individual acknowledgements and exact assessment navigation. Both use authored data and no supplier/AI request. The new phone controls were also visually inspected expanded.

A separate read-only audit matches **14 existing actual-account updates** against independent table counts: two private reasoning publications and twelve condition changes, across Apple (6), Alphabet (2) and Microsoft (6). All record IDs rehydrate and all fourteen appear in the download. These records contain previously evaluated inputs and interpretations; this audit checks collection/presentation, not their semantic accuracy. It neither creates a weekly report in the main account nor simulates elapsed real time. Scheduled persistence is exercised with explicitly authored, simulated-clock cases.

## Five-perspective review

These are five review perspectives by the implementation agent, not independent professional opinions or participant research.

| Perspective | Assessment | Improvement or remaining limit |
| --- | --- | --- |
| Product | A user can return to a stable weekly list and distinguish fresh items from older unreviewed work. | The app must run for timely delivery; startup catches up once. External email/push remains outside this local delivery. |
| UX | Current review and saved review are visibly separate. Seen status does not imply an investment judgment or dismiss alerts. | Dense histories remain long on phones; filtering and progressive evidence disclosure are available. Whether students understand and reuse this flow needs observation. |
| Architecture | One existing PostgreSQL store and existing event/evidence renderers support the feature; no new service/provider is introduced. | Generation is bounded at 1,000 records and holds a local row lock. Large hosted workloads would need separate capacity review. |
| Evidence and reliability | Immutable membership, boundary tests and rechecked permissions preserve traceability; quiet weeks keep coverage warnings. | Saved counts and coverage reflect generation time; current source availability may differ. This does not fix earlier sentiment/answer classification errors. |
| Business | Scheduling provides a reason to return without another per-review model charge. | Cheap summaries do not prove recurring value or willingness to pay. Source acquisition and analysis retain their existing costs and coverage limits. |

Decision: ship the bounded local schedule with off-by-default controls and explicit saved/current status. Keep historical AI failures, participant validation and the remaining requirements visible; do not equate more completed features or automated checks with a validated investment product.

## Preservation and cost

Evidence: `.local/live-tests/scheduled-reviews-20261003T102150Z/`, including the frozen prior state, actual-record manifest/export/audit, original failed and final test logs, browser screenshots, installation record and final verification. Installation backs up source/database, applies schema 29 and verifies all protected research/private/watch records remain exact. New schedule tables begin empty; all source watches remain off. No source acquisition or paid call occurs in this phase.

The cumulative **US$20** ledger remains **US$12.182322 confirmed**, **US$0.301565 retained historical maximum accounting**, **US$7.516113 available**, **263 calls**, with no new blocking unresolved charge. The two historical ambiguous calls keep their original unresolved rows and separate maximum-accounting decisions.

Next work remains prioritized in the requirements audit: semantic quality of sentiment/standalone answers and broader alert evaluation; primary guidance/forecast comparisons; normalized debt/trends and richer valuation; event-occurrence/recurring windows and source continuity. Participant comprehension, recurring use and paid value are unestablished. This phase does not complete the overall goal.
