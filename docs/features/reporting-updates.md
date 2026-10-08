# Updates to previously watched reporting

Phase 25 extends company watches to retain a substantive reported change even when its tone is neutral or favourable. It reuses existing cited news comparisons, the `new_reporting` alert group, private watch history and review controls. No schema, prompt, model, source or paid call is added.

## Delivery rule

A selected report must be relevant and fresh under the existing exact-content and justified-repeat keys. Its comparison must reference an exact report this watch previously saw, either in the preceding selected sample or its durable seen history. Merely supplying an older article as comparison context does not establish that the watch saw it.

The report is eligible when its cited comparison says `adds_detail` or `contradicts`, regardless of sentiment. It is also eligible when a proposed repeat is blocked by the existing numeric/status-wording guard. That conservative guard indicates text to inspect, not a verified semantic correction. A repeat retained only because it is an opinion does not itself qualify for this rule. Unlinked neutral reporting still does not alert under this company rule; saved-reasoning watches remain a separate option.

New adverse/mixed reports and these changed reports share one `new_reporting` publication per sample. Sentiment reversals retain their existing separate grouped alert and method compatibility requirements. Repeats remain quiet after the new text is recorded as seen. No old alert, old sample, saved reasoning or review acknowledgement is rewritten, and installing the rule does not enable watches or backfill missed alerts.

## Review experience

An eligible alert says **New reporting changes an earlier story**. Each changed item includes a disclosure labelled **Added detail**, **Conflicting reports** or **Changed wording**. It contains the comparison explanation, exact passages from both reports, publication dates and source actions. It does not establish which claim is true or whether a publisher formally issued a correction.

The earlier alert remains independently reviewed or unresolved; the new one needs its own review. Weekly review reuses this UI, and its downloadable record includes both passages and an earlier-source link. Current permission checks withhold the complete affected alert, its excerpts and export content when a consumed source becomes unavailable. Restoration makes the same immutable record readable again, without new delivery.

## Verification

`tests/test_reporting_updates.py` covers neutral/favourable updates, known versus unseen references, repeated/relabelled content, grouping, guarded repeats and a complete risk → clarification → repeat → failed check → recovery → source withdrawal/restoration sequence. These cases use authored data and mocked responses in disposable storage. `tests/run_browser.py --reporting-updates` checks source comparisons, source dialogs, persistent independent review, export and 320/390/1440px layouts.

The [phase review](../reviews/2026-10-02/reporting-updates-phase-review.md) records before/after replays of saved actual Microsoft reports and separately authored contrasts. Replay availability and seen history are constructed; this is not prospective monitoring, fresh model evaluation, whole-feed recall or measured user benefit.

## Retained-source continuity verification — phase 60

The disposable replay now follows retained Alphabet/Apple source wording and paid labels through the actual watch claims, publication, durable seen history, independent review, withdrawal/restoration and exports. Authored arrivals/faults and one new private-question response remain explicitly separated from prospective evidence. [Replay guide](../testing/alert-continuity-replay.md) · [Results and limitations](../reviews/2026-10-04/watch-continuity-phase-review.md).
