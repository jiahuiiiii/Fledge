# Reviewable suggestions — phase 10

**Phase 44 update:** Numerical suggestions now explicitly distinguish requirements from risks, including updates to existing risk rules. The preview explains the comparison and equality; every change still needs review and saving. [Implementation, actual-company checks and review](../reviews/2026-10-03/numeric-risk-proposals-phase-review.md).


The app can propose a starting research idea or changes to a saved idea, numerical condition or event criterion. It reuses the existing bounded source-packet builder, exact source passages, direct OpenAI profile and original cumulative ledger. Generation is explicit. Suggestions are private and pending; no suggestion changes the saved idea on arrival.

## User journey

Open **Get help defining this idea** or the company's saved idea. Request a starting idea or suggested checks. Read the rationale, exact supporting passage and before/after definition. Suggestions are initially unselected. Select up to three compatible changes, then review the complete resulting idea. Fill missing thresholds/dates and edit wording. **Use suggestions in draft** saves without activating monitoring; **Approve monitoring** also requires the explicit approval checkbox and a valid nonempty condition set. Rejecting a suggestion leaves the saved idea unchanged.

The generation prompt requests concise, complete evidence requirements. A schema-validated but unfinished or ellipsis-bearing requirement is rejected before any suggestions are published; its paid response remains in the ledger and is not retried automatically. This completeness guard does not prove semantic correctness.

The generation prompt requests numbers/dates only from explicit saved reasoning or existing definitions; otherwise these fields stay blank for the user to choose. Any displayed threshold or window is a proposed research assumption, not a recommended investment or verified observation. Numeric suggestions remain limited to reported revenue growth and operating margin. Event windows remain inclusive UTC publication dates, not inferred event-occurrence dates. Full-article retrieval and exhaustive risk coverage do not exist.

## Exact-version decisions

Migration 011 stores immutable typed `reasoning`, `numeric` and `event` proposals and separate append-only approval/rejection decisions. Numeric/event operations are add, update or remove. Update/removal targets must belong to the correct owner, company and base revision; the database also enforces target membership and snapshot/company alignment. A new idea uses an explicit research question and an empty base without creating a phantom saved revision.

Approvals check the expected base revision and current source snapshot inside the same locked transaction as the new revision and all selected decisions. Selecting several compatible suggestions creates one revision. A source/idea change makes a pending suggestion stale. A stale suggestion must be requested again against current evidence, never silently applied. A late generation response can be stored as stale, but cannot overwrite the newer idea. Duplicate identical approvals return the original accepted revision; a different decision or payload conflicts. Missing/withdrawn source access withholds the affected suggestion and blocks approval.

The existing save service remains the only revision writer. Advisory locks preserve append-only table grants; there is no new privilege to mutate proposal history. All HTTP/model work occurs outside mutation locks. No automatic model retry, new budget, acquisition scheduler or external notification is introduced.

Previous suggestions remain visible with their state and an accepted-revision link. Exporting an accepted revision includes the reviewed suggestion's evidence trail under current source access, even for an unevaluated draft; it does not mislabel that source trail as a monitoring assessment.

## Verification and limits

Mocked tests cover pending/cached results, first-idea generation, target membership, owner/company isolation, atomic multi-selection, failure after revision insertion, duplicate/concurrent approvals, numeric update/removal, differing repeat payloads, stale source/base revisions, edits during model calls and withdrawn evidence. The browser journey covers unselected before/after cards, two suggestions becoming one revision, manual reasoning edits, missing date validation, accepted history, a concurrent edit preserving the reviewer's unsaved text, and desktop/phone layouts without automatic paid calls. Existing private-comparison/history/export behavior was rerun.

This completes the bounded proposal workflow, not proof that AI suggestions improve a student's reasoning. See [actual-company checks and retained failures](../reviews/2026-10-02/proposal-real-case-review.md) for the live evaluation. These source-grounding checks do not establish student usefulness. A five-perspective review by the implementing agent is not independent consultant validation. Broad fundamentals, valuation and recurring source acquisition/digest remain separate incomplete requirements.
