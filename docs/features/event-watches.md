# Current recurring event watches — phase 56

An approved recurring condition is checked against its current concrete window at the existing optional news-watch cadence. Earlier-period confirmations cannot be reused for a new period. Clock rollover alone makes no source or AI request and leaves the condition unknown until suitable evidence is checked. New recurrence settings require a new approved revision; old pinned watches pause as before. A late response is retained in history without replacing current monitoring. Migration enables no watch.

[Schedule controls and limitations](event-conditions.md) · [Verification](../reviews/2026-10-03/recurring-events-phase-review.md). Earlier phase sections below retain their historical scope.

# Current event watch timing — phase 55

Approved event watches preserve each condition's chosen date meaning: report publication or source-stated occurrence. Publication-only checks retain prompt v2 and exact cache identities. Any occurrence condition uses `thesis-event-occurrence-2`; dates must come from its own exact cited passage and pass code-owned calendar/window checks. The same optional watch controls, revision pinning, late-response restrictions and grouped condition Updates remain in force. Migration enables no watch.

[Date choices and limits](event-conditions.md) · [Verification](../reviews/2026-10-03/event-occurrence-phase-review.md). The phase31 material below is historical where it describes publication-only capabilities.

# Automatic approved-event checks — phase 31

The existing news watch now offers **Also check my approved event conditions**. It is off by default and requires a currently approved monitoring revision containing events. It uses that news watch's hourly/four-hour acquisition schedule and adds an explicitly authorized private AI check when eligible event inputs differ. It can run alongside company sentiment or saved-reasoning alerts. Social sentiment does not establish that a defined event occurred: this event route uses selected company reports/structured filing evidence, not social posts.

The **Automatic event checks** disclosure is visible even with the news watch off. Opening it is read-only; enabling requires the news watch and approved event conditions. An existing event selection can be cleared even when news monitoring is stopped.

The control pins an exact version. Editing reasoning/conditions, saving a draft or archiving stops automatic event application until the user explicitly chooses the current approved events. Turning off the event option or the news watch prevents new event application. An already-dispatched model request may finish and cost money, but a late result after stop, lease expiry, changed revision or a newer source snapshot is retained only as history. No subsequent model stage starts after the watch is stopped during event analysis.

Migration 23 adds the watch's event revision, recorded event-watch configuration on each scheduled attempt, an immutable automatic/manual origin flag and private append-only activation records. Legacy event checks retain their original manual meaning. Automatic checks affect numerical/event reassessment only after activation under a still-current watch/revision/snapshot. A later explicit manual request can apply a retained completed result without paying for it again. The source collector cannot read private activation rows.

The existing event classifier remains prompt 2 and uses the original shared ledger/model limit. It assesses inclusive UTC report-publication windows and the exact event/evidence requirement. Code maps report matches to required/risk outcomes; denial, conflicting reports, plans and missing evidence remain unknown. Report confirmation is an AI interpretation, not independent event verification. No eligible reports means no model call. A failed request is recorded and not immediately retried. Numerical thresholds remain code-computed.

## Exact-input reuse

Previously a new acquisition snapshot—even one with unchanged eligible texts—required a new event interpretation and could discard an otherwise applicable check. Reuse policy `identical-event-inputs-1` compares the exact saved version, definitions, source IDs/text/metadata/passages, eligibility sets and omission counts. Only snapshot ID and acquisition cutoff are excluded. The original model/method must match; a later acquisition clock cannot turn a plan into completion. A changed eligible source, corrected text, changed definition, expired source selection, changed omissions or lost source permission prevents reuse.

A carried interpretation keeps its original check ID, source snapshot/cutoff and model date. New assessment manifests store its policy, original snapshot and full input signature; workers recompute that proof before applying it. Historical assessments are never rewritten. Reuse alone does not create another alert or charge. The current report-window/deadline state still comes from code. Reads, history and exports perform no model work. The UI and exports explain reuse when a later assessment applies the original interpretation.

The existing snapshot → complete condition evaluation → grouped Updates path remains the only event alert publisher. Watch history records the separate event stage and whether it checked, reused, lacked eligible reports, paused after an edit or retained a historical-only result. Its company/social alert count excludes asynchronously produced condition changes and says so.

## Verification boundary

Tests cover opt-in, owner/revision membership, exact-input reuse, changed reports, required/risk/denied/uncertain outcomes, stops/edits/new snapshots/expired leases during analysis, activation privacy/immutability, exports, failed requests and no-call cases. Browser tests use authored reports and mocked models but real configuration endpoints, source inspection, history and export. Actual-company model checks are recorded separately in [the five-perspective review](../reviews/2026-10-02/event-watch-phase-review.md).

This completes a bounded automatic catalyst-checking path, not broad filing/transcript extraction, event-occurrence-date detection, recurring event windows, prospective alert recall/latency or participant validation. News selection still contains at most twelve eligible supplied source texts and seven days of provider news at the snapshot; a longer configured window does not retrieve earlier reports.
