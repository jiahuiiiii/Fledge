# Numerical risk suggestions — phase 44

The plan requires students to define both what must hold and what would undermine an idea. Numerical risks already worked when entered manually, but AI suggestions could only describe requirements and could not update an existing risk. That left the “make my idea testable” workflow unable to express one of its intended outcomes.

This phase closes that specific gap. It does not resolve the sentiment/answer interpretation failures from phases 41–43 or connect the unsuccessful generic evidence checker to publication.

## Implemented behavior

Proposal method `thesis-condition-proposals-4` requires every generated numerical definition to state `required` or `risk`. A requirement says the comparison must hold; a risk says satisfying that comparison flags a concern to review. Both operators remain inclusive. Role changes do not invert the operator or alter the number. The preview now explains the exact comparison in plain language, including equality.

The model can propose additions, updates and removals for either role. Every change remains pending and unselected, with the original and proposed definitions side by side. The user reviews the complete resulting idea, fills missing thresholds, edits it if needed, and explicitly saves or approves monitoring. Generation alone never changes a saved idea. Updates retain condition identity; accepted changes produce a new immutable revision and preserve prior results.

The prompt asks for thresholds and reporting-age limits only when chosen in the user's question, reasoning or existing conditions. Otherwise those fields stay blank. Reported figures and analyst estimates are not user-chosen thresholds. Existing risk purpose should be preserved unless the expressed intent calls for a change; the rationale must explain a proposed purpose change. These are model instructions, not deterministic proof of semantic fidelity. The app independently rejects absent/invalid roles, malformed numbers and invalid target membership, while explicit review remains necessary.

The numerical schema has a required role with no default for newly generated outputs, consistent with the [structured-output contract](https://developers.openai.com/api/docs/guides/structured-outputs). A new response using the old role-less schema cannot silently turn an existing risk into a requirement. Historical pending suggestions retain their original payloads and default-required interpretation through the existing save model. Old approval hashes, idempotency and saved results remain compatible. No migration, provider/profile change, new model stage or source integration was needed.

## Verification

- **835 backend tests passed**, with all retained SEC, expanded-company and HN-context corpora configured. This includes the three actual-filing numerical-risk replays and nine new suggestion cases.
- **14 frontend checks passed**, and the rebuilt application succeeded.
- The proposal browser journey passed at 320, 390 and 1440 pixels: initially unselected suggestions; requirement/risk preview; blank threshold; changing a threshold clears approval; three compatible suggestions saved as one revision; role/operator/threshold persistence; historical link; stale conflict preserving unsaved text; no external or automatic paid calls.
- The numerical-risk browser journey passed: explicit purpose, approval reset, a fictional growth crossing from 18% to 12%, the risk update in the inbox, original history and download, and phone/desktop layouts.
- Desktop and phone screenshots were inspected. The installed app was reloaded, its suggestion entry point displayed the new requirement/risk explanation, and the original NVIDIA workspace was restored without generating or saving an idea.

The first focused run passed 51 checks and skipped three real-filing replays because that runner lacked the corpus setting. The subsequent full run supplied the correct corpus paths and passed those cases. The initial frontend build was stopped by the dependency-cache filesystem boundary; the same build succeeded with the required local write permission. Neither event required changing product behavior.

New cases cover pending risk additions, an unset threshold that cannot be silently saved, explicit approval and the later risk crossing, idempotent decisions, updates/removals preserving the old revision, explicit role changes without number/operator changes, invalid roles rejected before publication, and historical pending required-only suggestions. Provider calls in automated tests are mocked; the three paid checks below are separate.

## Actual-company evaluation

Three requests were frozen before dispatch using saved original company source packets and explicitly authored questions/rules. They do not use the owner's investment beliefs and are not prospective monitoring or real-user research. Expected outcomes remain outside the model request. Each request produced exactly one numerical suggestion with no additional non-numerical suggestions.

| Case | Expected and observed result |
| --- | --- |
| Microsoft | Add an annual revenue-growth risk, `<= 15%`, using the explicitly chosen number and leaving report age blank. |
| NVIDIA | Add a quarterly operating-margin risk with `<=`, leaving the unchosen threshold and report age blank. It cannot be saved as a complete numerical condition until a threshold is chosen. |
| Apple | Update the existing growth-risk identity to annual `<= 12%`, retaining risk purpose and leaving the separate quarterly margin requirement unchanged. |

All requested fields and target identities matched. Seven citation associations match the original supplied passages. The rationales preserve the chosen role and period, do not assert that a suggested threshold is recommended, and keep unspecified settings blank. The Microsoft and NVIDIA metric passages come from their respective annual and quarterly structured SEC calculation documents; document titles and original periods were checked as context, not treated as model-authored facts. Apple's period distinction is an extraction-rule passage rather than a newly reported company event. The suggestions do not claim a risk has already occurred. They propose future checks that still require review.

The 15% and 12% values above are authored development criteria, not investment recommendations or demonstrated useful thresholds. These three selected successes do not establish general suggestion quality, broad risk discovery, comprehension or willingness to pay. No paid result was automatically published or applied to a saved idea.

## Installation, spending and preservation

Evidence: `.local/live-tests/numeric-risk-proposals-20261003T063743Z/`. Source and database backup: `.local/backups/phase44-risk-proposals-20261003T064142Z/`. The code and rebuilt frontend are installed in Thesis; schema remains 27.

The three calls cost **US$0.073905**. Confirmed cumulative usage is **US$10.005759** across **235** calls, plus unchanged historical maximum accounting of **US$0.301565**, leaving **US$9.692676** under the same **US$20** allowance. Both original ambiguous records remain unresolved with separate maximum accounting; there is no new blocker or automatic retry.

Protected saved ideas, proposal decisions, answers, sentiment, themes, private alert records and watch settings remain unchanged. All watches remain off. No source was refreshed and no new result was published into product research. This closes the AI numerical-role gap; it does not complete the broader implementation plan.

## Five-perspective review

These are five perspectives applied by one agent, not independent professional opinions or participant evidence.

| Perspective | Conclusion |
| --- | --- |
| Product | The suggestion path now supports both favourable requirements and invalidating numerical conditions, matching the monitoring journey rather than forcing risks into the wrong role. |
| UX | Before/after purpose and a plain-language inclusive comparison make the proposed consequence visible. Explicit editing and approval remain essential; actual student comprehension is unmeasured. |
| Research | Selected real-source cases support the bounded role/threshold behavior. Authored questions and three successes cannot prove useful threshold choice or broad risk recall. |
| Engineering | The change reuses existing schema, review, revision and evaluator contracts. Strict new outputs and compatible historical payloads avoid silent role conversion. |
| Business | This makes the research-to-monitoring pitch more complete, but does not establish recurring usage, willingness to pay or customer value. Sentiment/answer correctness and source continuity remain important gaps. |
