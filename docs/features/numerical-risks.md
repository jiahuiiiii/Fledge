# Numerical requirements and risks

Phase 28 · 2 October 2026

A saved numerical condition now has an explicit purpose: **Requirement — must hold** or **Risk — flag when reached**. This extends the existing event-role distinction to reported revenue growth and operating margin. It does not turn a price move or sentiment reading into a financial fact.

| Definition | 12% reported | Exactly 15% | 18% reported |
| --- | --- | --- | --- |
| Requirement: growth at least 15% | Requirement unmet | Requirement met | Requirement met |
| Risk: growth at most 15% | Risk threshold reached | Risk threshold reached | Risk threshold not reached |

These are authored examples, not recommended investment thresholds. `>=` and `<=` include equality. Changing purpose does not flip the comparison or alter the threshold. The editor clears approval and requires the revised definition to be approved again. Saving creates a new immutable revision, retaining condition identity where edited.

## Assessment and alert contract

Code computes the comparison with exact Decimal values. A required predicate maps true to `met` and false to `not_met`; a risk predicate maps true to `not_met` and false to `met`. The latter means only that this chosen threshold was not reached. The result explanation explicitly avoids a claim of investment safety.

Missing, incompatible, conflicting or expired observations remain `unknown` for either role. Source freshness remains a separate coverage dimension: an outage does not delete a retained reported figure or renew its age. An unmet requirement or reached risk dominates the combined assessment; otherwise any unknown leaves it incomplete. Existing event-evidence rules remain unchanged.

Risk changes use the existing complete assessment transaction, ordered worker, grouped in-app change record and independent review action. The Updates row, historical definition, result explanation and selected-record/periodic exports carry the role. Marking reviewed never resolves the risk or changes its outcome. Withdrawn numerical sources withhold results through the existing access checks.

## Compatibility and suggestions

Migration 020 appends `role` with `required` as its default. It does not change historical evaluations, values, outcomes, fingerprints or saved reasoning. Required-only manifests retain the omitted-role representation and evaluator 4 so installation alone does not manufacture reassessments. Risk definitions use evaluator 5 and include their role. Finishing a legacy queued job normalizes the missing role to required before checking exact revision membership. An older queued assessment can finish after an edit without becoming the new revision's assessment.

Proposal base definitions and reviewed candidates retain numerical roles. Default-required approval hashes preserve the prior omitted-role representation, retaining retry idempotency. That phase initially kept AI numerical suggestions required-only. Phase 44 supersedes that limitation: method `thesis-condition-proposals-4` requires an explicit `required` or `risk` role and permits pending add/update/remove operations for either. Missing roles in new model outputs are rejected, while historical required-only proposals remain readable and approvable. The complete before/after definition is reviewed before saving; unspecified thresholds remain blank. Reasoning/event suggestions preserve untouched risks. See [the implementation and evaluation](../reviews/2026-10-03/numeric-risk-proposals-phase-review.md).

## Verification

`tests/test_numerical_roles.py` covers exact boundary values, both operators/roles, unknown evidence, legacy manifests, unchanged-repeat suppression, late older jobs, immutable roles, owner/source access, change records, historical export, suggestion preservation and three saved real-filing replays. `tests/run_browser.py --roles` exercises the editor, approval reset, a recorded 18%→12% risk crossing, Updates, original history, download and 320/390/1440 layouts. Reporting-age and proposal browser regressions remain separate checks.

The real replays use previously acquired MSFT/AAPL/GOOGL SEC records, with deliberately authored growth-at-most-20% and margin-at-most-33% risk rules. The expected outcomes were written before execution: growth flags MSFT/AAPL, margin flags AAPL, neither flags GOOGL. These tests verify software against saved inputs, not prospective alerts, useful thresholds or investment outcomes. See [the phase review](../reviews/2026-10-02/numerical-risk-phase-review.md) for final counts and installation evidence.
