# Event occurrence dates — phase 55

3 October 2026. Event conditions now offer **Report published during** or **Event happened during**. A newly published report about an old launch no longer needs to count as a new event: the user can choose occurrence timing, and a later report can establish an explicitly dated earlier event. Existing conditions retain their publication-window meaning.

## Implementation and boundaries

Migration 030 adds `date_basis` to immutable event definitions, defaulting earlier rows to `report_publication`. New occurrence conditions use the same revision, approval, event-check, optional watch, assessment, Updates and export workflow. Editing date meaning resets approval and creates a new version; it cannot silently retarget an old watch. Pending AI edits preserve an existing event's basis. New AI-generated event additions still start as report-window suggestions and can be changed in review.

For an occurrence condition, selected reports may be published outside the event window. The model selects exact date text from the event's own cited original passage. Code accepts a complete ISO date or English month/day/year date, validates the calendar, and compares it with the inclusive chosen dates and the report's UTC publication day. It never substitutes publication time for occurrence, invents a missing year/day, or resolves ambiguous numeric, partial or relative dates. A date after the report's UTC day stays unconfirmed; near-midnight timezone ambiguity is not resolved. Plans, denials and conflicting reports cannot produce a positive occurrence finding merely because a date matches.

No selected date, a partial/ambiguous date, a future date or an outside-window date prevents a confirmed occurrence result. Exact date text must belong to its cited passage; wrong-source/invented date text is rejected. Selected dates remain attached to those citations so source withdrawal also withholds them. Calendar arithmetic is code-owned; choosing the correct event/date and interpreting completion still depend on the model and reader.

The occurrence route is `thesis-event-occurrence-2`, with the existing GPT-5.4 medium/6,000-output allowance, schema format and cumulative ledger. The publication-only route stays `thesis-event-evidence-2`. All **eight existing saved event requests and identities** match the installed old route exactly. Default date-basis fields are omitted from legacy monitoring manifests and proposal packets to prevent spurious new assessments/charges. Historical responses and job manifests are not rewritten. Exact-input reuse still requires the same revision and all eligible source inputs.

UI, saved checks, assessments and exports identify the chosen window and show each selected source date next to its original passage. The new browser journey is `.venv/bin/python tests/run_browser.py --event-occurrence`. All schedules remain off in the main account; installation adds no event definition, user alert or shared reading.

## Checks and actual-source evaluation

**1,014 backend checks** pass with six retained corpora. **85 overlapping focused checks**, fifteen frontend checks/build and the event editor, dated result, existing event-watch and proposal browser journeys pass. The dated result and editor were checked at 320/390/1440px; its phone rendering was visually inspected. Initial local failures were two mistakes in the new test helper (syntax and mocked model identity), plus a proposal browser assertion still expecting the old report-window wording. They are retained with the corrected passing runs.

Four initial paid packets and four corrected evaluations use the exact same twelve predeclared expectations. Six criteria use cached actual Meta/Amazon provider snippets; six are separately authored controls. No new source acquisition occurred. No model evaluation was published into the owner's research. All tests outside these explicit metered scripts use mocked providers.

| Case | Intended distinction | Final result |
| --- | --- | --- |
| Meta | A September launch reported in October; September occurrence versus October occurrence versus October publication | 3/3 labels; source date 8 September 2026 retained |
| Amazon | Undated completed signing; seeking a chip transfer versus completed transfer; report-only signing confirmation | 3/3 labels |
| Authored dates | Late report of an in-window launch; a future planned launch; a newly reported out-of-window launch | 3/3 labels; 30 September 2026 retained |
| Authored uncertainty | Month-only timing; disputed dates; explicit denial of a completed-launch allegation | 3/3 labels |

The first candidate matched **11/12**, incorrectly labelling “has not launched yet” as a denial. Both that finding and its charge remain retained. The corrected instruction distinguishes a pending progress update from disputing an allegation; the final run matches **12/12** without changing labels, source packets or the acceptance gate. All **22 quotation associations** and **four selected date associations** match their original passages. These are bounded agent-authored developer checks, not broad model accuracy, prospective alert recall or independent human validation.

## Preservation and spending

Evidence: `.local/live-tests/event-occurrence-20261003T120922Z/`, including frozen packets/expectations, both evaluated methods, original responses, scores, initial/final logs, browser artifacts and installation/final verification records. Source and database backup: `.local/backups/phase55-event-occurrence-20261003T122355Z/`. Migration 030 preserves every preexisting column and row across all 84 tables at the stopped-app checkpoint. The restarted app preserves them too, except ordinary monotonic cursor-clock advancement with unchanged owners/revisions/snapshot targets. The installed Microsoft editor was checked read-only at 320/390/1440px: existing conditions still select publication meaning, the new choice resets approval, and closing without saving makes no write or provider request. Its phone rendering was visually inspected. Background monitoring cursor clocks can advance normally while the app runs; this is separate from changes to research, definitions, findings, alerts or watch choices.

Eight paid requests cost **US$0.1783950**. The shared US$20 ledger now has **US$14.2028245 confirmed plus US$0.301565 retained historical maxima**, leaving **US$5.4956105**, across 286 calls. No new ambiguous charge. Earlier unknown charges remain unresolved with their original maximum accounting; neither cap nor history is reset.

## Five-perspective review

These are five perspectives applied by one coding agent, not independent consultants or participant research.

| Perspective | Judgment and consequence |
| --- | --- |
| Product | The user can finally distinguish an event deadline from an article date while keeping the same saved-idea alert workflow. An unknown result remains visible rather than declaring deadline failure. |
| Research quality | Source-owned dates and deterministic calendar checks remove a specific timing substitution. The selected positive/negative cases pass after a retained failure; date association, completion interpretation and missed evidence still need wider evaluation. |
| UX | Date meaning is explicit before approval and survives editing, history and export. Full-day requirements may make many short news snippets unconfirmed; explain that beside the control and show the source so the user can judge the gap. |
| Architecture | One nullable-free enum column and the existing pipeline suffice. Separate method/identity handling preserves old requests and immutable history; source scope, watch leases and budget accounting remain in force. |
| Business | This is a concrete alert capability with about eighteen cents of development evaluation. It does not establish natural return, willingness to pay, notification quality or production unit economics. |

The phase implements exact source-stated occurrence days, not recurring event periods, a filing-expectation calendar, broad historical article retrieval or timezone inference. Selected sentiment/standalone-answer errors, wider alert precision/recall and other reconciled-plan requirements remain unfinished. Next alert work should make recurring/expected evidence windows reviewable so a one-time event cannot stand in for an ongoing quarterly expectation. The active overall goal remains incomplete.
