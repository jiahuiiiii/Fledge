# Phase 5 — reporting-age monitoring

Three AI reviewer threads covered architecture, product/UX and evidence/business. These are development reviews, not independent professional opinions or customer validation.

The reviewed scope is an optional user-defined age limit on numerical conditions. Review led to explicit UTC boundary semantics, separate assessment/source clocks, immutable expiry manifests, durable queue order and assessment cursors, frozen source-check selection, old pending-manifest compatibility and expiry-specific update wording. A synchronized save-versus-recorded-acquisition race was identified and corrected by acquiring the collection lock before the instrument lock. The final architecture review found no remaining blocker in that correction.

UX corrections distinguish past deadlines from future ones and explain invalid input instead of treating it as a blank limit. Last figures remain source-linked and visibly outside the selected age limit. Coverage wording refers to assessment time, because a source check may have aged since the evidence cutoff.

Verification results and remaining boundaries are recorded in [implementation status](../../archive/status/implementation-status.md) and [reporting-age contract](../../features/reporting-age.md). SEC contact configuration and live response validation remain separate pending work. No new provider call or API spending is required by this phase.

Final evidence: 123 backend tests, 3 frontend contract tests and all three browser journeys passed. The visual review accepted desktop/mobile editing and expired results; the additional browser scenario verifies actual local background updates and two distinct expiry records. No live source/provider call occurred.
