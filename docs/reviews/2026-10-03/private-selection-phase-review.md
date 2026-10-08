# Private alert source selection — phase 45

A company-level sentiment judgment was excluding evidence before the private stage could compare it with the user's saved question. A discussion can be irrelevant to general stock sentiment yet directly answer a narrower research question. This phase removes that exclusion gate within the existing saved sample.

The selection change works, but the live negative control failed: two already-eligible reports received indirect risk interpretations without supplying the requested evidence. This phase does not establish accurate or quiet alerts. The generic finding checker remains evaluation-only.

## Implemented behavior

`private-original-sample-1` considers every original source with usable passages, independent of the shared sentiment relevance label. It preserves the original 16-source cap, channel alternation, exact-text deduplication, immutable source and parent versions, owner isolation and revision checks. A Hacker News comment must have an eligible body passage; its generic title alone is not evidence. The existing conservative ellipsis rule remains. Meaningful news/Reddit titles remain eligible even without body text.

The source-selection policy participates in new request identities without changing the existing v7 model prompt, schema or paid profile. Historical requests retain their old identity, output and count meanings. Current and earlier selection policies are explained in the alert card, private download and periodic review. Opening history creates no paid call.

Watch baselines and seen texts are unchanged: installing this policy, adding parent context or reclassifying an existing sample cannot trigger a fresh private check. A genuinely new source can be checked even if shared sentiment calls it unrelated. Prior validated repeat-coverage links still suppress seen stories, so this is independence from relevance labels, not every shared model decision. Upstream collection and selected-sample limits still constrain recall.

No new integration, migration, model stage, automatic retry or watch enrollment was added.

## Verification

The full isolated suite passed **847 backend tests** with retained SEC, expanded-company, HN-context and private-selection corpora. A final focused run passed **62 tests**, overlapping the full suite and covering the subsequent periodic-export addition and final wording. Fourteen frontend checks and the build passed.

The isolated browser journey passed at 320, 390 and 1440 pixels, covering current and earlier selection messages, exact old reasoning/question, source inspection, private downloads, review acknowledgements, quiet history and archive persistence. Desktop and phone screenshots were inspected. Fixtures and model responses in these automated checks are authored/mocked; they are not paid or actual-source model evaluation.

New tests cover label-independent selection, unusable HN bodies, meaningful title-only evidence, exact duplicates, seen keys, channel balance and the cap, legacy cache identity, old-record/export semantics, quiet baseline after reclassification, and exactly one delivery for genuinely new material. A retained Microsoft sample replay identifies the recovered source and proves that the unchanged sample remains quiet as a watch baseline.

One new export assertion initially used an invalid `days=None` parameter. It was corrected to the existing `days=0` all-history contract; product behavior did not need changing. The initial evidence-freezing script missed a required read-only record field and was corrected before any paid request. Both failed logs are retained.

## Actual-source evaluation

Two requests were frozen before dispatch using the same retained Microsoft news/Reddit/Hacker News sample and explicitly authored questions. The original sample had 16 texts. Earlier company relevance selected 14; the new policy selected 15, adding one usable study discussion while excluding a separate HN record whose only eligible passage was its generic title. No new source was fetched, and these questions are not the owner's investment beliefs.

| Case | Expected | Observed |
| --- | --- | --- |
| What did the reported Microsoft code-review study measure about stated reasons versus comments? | One attributable partial answer; other sources quiet; no claim of proven engineering effectiveness or financial impact. | Met the selected criteria: the recovered comment supplied the reported 44% versus 14% distinction, attributed to the comment; 14 other texts stayed quiet. The answer said effectiveness remained unanswered. |
| What is the reported Microsoft Copilot paid-seat retention rate? | All 15 sources quiet because none supplied the requested metric or a direct specific threat to it. | **Failed:** 13 stayed quiet, including the newly included study comment. A broad Reddit AI-spending opinion and a report of a Copilot-associated executive's planned departure were labelled risks to future retention. Neither cited passage establishes that connection. |

Across 30 source relations, 28 matched the predeclared alert/quiet expectations. This is a selected development comparison with agent-authored labels, not a precision estimate or independent evaluation. Both problematic sources were already eligible under the old filter, but this does not establish that the selection change had no effect on model behavior. No old/new randomized quality comparison was performed.

All 58 source quotation associations and six pinned-parent quotation associations were matched to their originals. Structural and exact-quote checks passed for both responses; the negative control demonstrates why that does not prove an interpretation. A further prose concern is the control's coalition explanation saying “sustainability commitments” where its own selected passages state concerns and aims. Model prose also exposed internal anchor IDs such as `q0`/`r1`. These are recorded defects, not silently repaired output.

The positive case establishes a concrete source-reachability improvement for an authored question. It does not verify the underlying study, endorse its conclusions, prove better investment decisions or demonstrate prospective alert timing. Original failures remain in the evidence folder. No paid output was published into the owner's research.

## Spending and preservation

Evidence: `.local/live-tests/private-source-selection-20261003T065056Z/`. Two requests cost **US$0.1873125**. Cumulative confirmed spending is **US$10.1930715** across **237 calls**; retained historical maxima are **US$0.301565**, leaving **US$9.5053635** under the original cumulative **US$20** allowance. Both historical ambiguous records retain their append-only maximum accounting, with no new blocker or retry.

Source/database backup: `.local/backups/phase45-private-selection-20261003T065607Z/`. Final protected-state hashes are recorded in the evidence folder. Schema remains 27. Saved reasoning, proposal decisions, sentiment, answers, themes, private checks, publications and watch settings are preserved. All watches remain off. No source acquisition, account message or product publication occurred.

## Five-perspective review

These are five perspectives applied by one agent, not independent consultant opinions or participant research.

| Perspective | Judgment and next implication |
| --- | --- |
| Product | General sentiment and private research relevance now have appropriate boundaries. The positive case supports this correction; indirect risk alerts still undermine the central promise. |
| UX | Coverage messages explain what was examined without silently updating old checks. Internal IDs in generated prose and indirect risk explanations remain confusing and require a narrower output contract. |
| Research | The negative control is a failed acceptance criterion and must remain visible. Test specific question answers separately from directional belief monitoring before asserting alert quality. |
| Engineering | The change reuses bounded sampling, immutable records, the shared ledger and current delivery safeguards. It adds no generic verification layer. Exact references still cannot validate inference. |
| Business | Better linkage to saved research strengthens the pitch story, but noisy alerts can weaken recurring value. No evidence here establishes student comprehension, retention or willingness to pay. |

The next correctness work should separate the user's requested monitoring purpose from the model's inferred risk category, then evaluate useful positive cases and quiet controls. Do not add another prompt sentence or generic checking stage and call the noise problem solved. Broader plan requirements and participant validation remain incomplete.
