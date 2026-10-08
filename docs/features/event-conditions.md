# Current event schedules — phase 56

Choose **Repeat this window** when an event needs fresh evidence every month, three months or year. Choose 2–12 windows and inspect **Preview all windows** before approving. Month-end dates stay at month end; other day anchors clamp only in shorter months. The finite schedule cannot overlap or exceed 3,650 days. One-window definitions keep their existing behavior.

Each new window starts without the preceding window's confirmation. The local clock can create an unknown assessment and an Update without another AI/source call. Optional approved-event watches use their existing cadence to check current evidence. After the final window the app retains its result and stops creating additional periods.

Each result names its checked window. **Window to check** can select an earlier period for a report that arrived late; the result remains in History and does not replace current monitoring. Selecting any earlier condition makes the complete check historical-only. Future windows cannot be selected for dispatch. A response arriving after rollover is also history-only. This control uses the current saved source snapshot; it does not retrieve older articles.

Use **Event happened during** if the completed event itself must occur in every period. **Report published during** instead asks for a qualifying report each period, which may discuss an older event. Date meaning and recurrence both require explicit approval, survive pending suggestion edits and appear in historical downloads.

[Verification and five-perspective review](../reviews/2026-10-03/recurring-events-phase-review.md). Expected filing calendars are still unimplemented. The following phase55/phase9 sections are historical where they describe recurrence as future work.

# Current event-date choices — phase 55

When defining an event, choose **Report published during** or **Event happened during**. The first retains the existing inclusive UTC publication window. The second asks when the completed event itself occurred; reports arriving later may qualify. Existing saved definitions are not reinterpreted.

Occurrence timing needs an explicit full calendar day, month and year in a selected original passage. Code validates ISO or English named-month dates. Missing, relative, ambiguous, invalid, out-of-window or future dates stay unconfirmed. The model must associate the date with the specified completed event; plans, a dateline and unrelated events are insufficient. Exact date text does not prove the interpretation. Check the original source beside each selected date.

Changing the date meaning requires renewed approval. Saved definitions, assessments, automatic checks, history and downloads preserve it. A later report may resolve a previously unconfirmed deadline; silence never proves failure or safety. Occurrence dates are source-stated calendar days, without inferred timezones. The report's UTC day supplies a conservative future-date check.

This uses the existing optional event-watch and in-app Updates workflow; no separate subscription, source supplier or alert channel is introduced. The bounded latest-source sample still cannot exhaustively search an arbitrary historical window. Recurring windows and expected filing calendars remain future work.

[Verification, retained failure and five-perspective review](../reviews/2026-10-03/event-occurrence-phase-review.md). The following section records the original phase9 publication-only implementation; its limitations about occurrence-date support are historical.

# Event conditions — phase 9

A saved idea can now contain up to three explicitly authored event conditions, four numerical conditions, or both. Each event has a stable identity, description, evidence requirement, required/risk role and inclusive UTC report-publication window. Saving monitoring requires renewed approval; edits create a new immutable revision. Drafts can contain unapproved definitions.

This is a bounded catalyst workflow: **the dates govern when a report was published, not an inferred date on which an event occurred**. Exact occurrence-date extraction, recurring event windows and an expected-filing calendar are not implemented. A long chosen window does not obtain older news: the existing source packet contains up to 12 selected sources, with provider news limited to seven days at the snapshot. Full article retrieval and exhaustive search remain absent.

## Evidence and outcomes

An explicit **Check event evidence** action uses the same strong OpenAI profile, original persistent ledger and no-retry policy. The request contains this saved revision's event criteria and eligible sources from one immutable company snapshot. Code filters each event's publication window before dispatch. If there are no eligible reports for any condition, no paid call is made. Results require exactly one finding per saved event, and exact original passage IDs from that event's eligible sources. A new snapshot requires another explicit check; old interpretations do not silently become current.

| Evidence | Required event | Risk to watch |
| --- | --- | --- |
| AI interpretation finds a report meeting every criterion | Condition met, labelled as reported evidence | Condition not met; reported risk needs review |
| Denial, uncertainty, conflicting reports or no check | Unknown | Unknown |
| Window has not started | Unknown | Unknown |
| Deadline passes without qualifying confirmation | Unknown, deadline unconfirmed | Unknown, deadline unconfirmed |

A plan, rumour, promised audit, beta or product launch cannot establish a different completed event such as independent audit completion or paying customer adoption. This is a prompt requirement and an evaluated semantic boundary, not a guarantee of model correctness. Quotations are checked by code; the truth and relevance of the interpretation still require human review. A denial cannot prove no risk exists. A report that meets a one-time condition inside its chosen window does not expire merely because the deadline later passes.

Numerical results still come from code. All approved conditions contribute to the overall monitoring assessment: a definite unmet condition dominates; otherwise any unknown keeps the combined result unknown. This is not an investment verdict. Mark reviewed records attention, not approval of the interpretation.

## Persistence, timing and access

Migration 010 adds immutable owner-scoped event definitions, evidence reviews and complete per-assessment event results. The transaction must include every numerical and event result. Late model responses remain attached to their original revision. Explicit cached requests do not redispatch. The local scheduler records window start/deadline transitions without a network or paid request, including catch-up after downtime. The authored sample follows its recorded clock; actual companies follow UTC while the app runs.

History exposes the event checks separately, including checks of drafts and older revisions. Downloads include event definitions, the selected assessment/check and its exact source references. A withdrawn source suppresses the affected event explanation and quotes under current access; a withheld result cannot leave the displayed combined outcome met. Original records remain preserved in storage.

## Verification

Backend coverage includes required/risk mappings, denial/conflict/unknown, inclusive UTC boundaries, reversed/overflow dates, sealed revision membership, complete mixed results, owner isolation, no-charge empty windows, missing/duplicate/invalid citations, cached responses, edits during a provider request, new-snapshot invalidation, deadline catch-up and scoped exports. Automated providers are mocked. A dedicated browser journey covers event-only approval, changed-definition approval reset, an edited deadline, old-history selection, actual download and 390/1440px layouts with zero automatic model calls. The existing private-comparison journey was also rerun.

Real-company semantic results are recorded separately after the live run; do not describe mocked confirmations as actual events. Typed suggestions and proposal approval remain the next separate workflow. Source acquisition is still manual; there is no autonomous event-news scan or external notification.

Final phase verification: **251 backend tests passed**, including 15 actual SEC corpus replays; four frontend checks passed. The event journey and prior private-history journey passed in disposable browser instances. Initial live event results matched 8/9 expected categories, with one false denial label; the corrected three-request retest matched 9/9, with 15 exact quotations. See [the actual-case review](../reviews/2026-10-02/event-real-case-review.md) for failures, limited scope and cumulative spending.
