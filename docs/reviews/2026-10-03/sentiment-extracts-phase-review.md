# Sentiment grounded in original wording — phase 47

Sentiment labels could be reasonable while their generated explanations invented a cause, financial implication or missing qualifier. A generic second AI checker did not reliably solve this in phase 43. This phase changes the sentiment output contract: each label is accompanied by selected original wording and a code-written description of the model's evidence category. The model no longer authors a per-item explanation. Research answers, discussion synthesis, news comparisons and private reasoning alerts remain separate generated interpretations; their known failures are not resolved by this change.

## What the user receives

New sentiment cards show the selected source wording immediately. Where the model identifies a superseded attitude, the earlier wording appears in a separate disclosure. The label refers to the current expressed view, while its selected excerpt may retain historical context or an antecedent. “View used for this label” avoids claiming that every sentence in that contextual selection is current. Parent messages remain separate and never add a sentiment vote.

The same component serves current samples, saved sample comparisons and published company-alert evidence. Weekly downloads retain the selected current/contextual wording and any earlier-attitude excerpts. Old results keep their original prose and method identity; they are not rewritten or relabelled. Source withdrawal still withholds both sets of excerpts and affected interpretations. The compact workspace, separate news/Reddit/HN samples, source controls and explicit watch settings remain.

## Implementation and checks

`thesis-source-sentiment-10` selects exact source IDs, current/contextual passages, optional earlier-attitude passages and pinned-parent passages. Source-specific nested schemas bind IDs and passages before choosing basis/relevance/tone/type/topic. A source with a supplied parent must cite its own child body and its own parent. Without a supplied parent it cannot return parent references. Earlier-attitude passages belong only to relevant social items. Code checks complete item coverage, exact source membership, duplicates and permitted basis/tone combinations. A directional label needs an evaluative or stated-outcome basis; a descriptive basis pairs with neutral. These structural categories do not prove that the model selected the correct basis or tone.

The provider/model, reasoning effort, output ceiling, source sample, grouping/counting policy and budget are unchanged. Nested `anyOf`, enum and array bounds follow the official [Structured Outputs contract](https://developers.openai.com/api/docs/guides/structured-outputs). No extra model stage or schema migration is introduced. News-coverage comparisons retain their existing separately generated explanations and were reviewed separately.

The final isolated suite passed **884 backend checks**, including all four configured retained-source corpora. Fourteen frontend checks, the production build and targeted syntax/undefined-name checks passed. Responsive sentiment and saved-history browser journeys passed at 320, 390 and 1440 pixels. The changed-view card was visually inspected at phone width. New tests cover rejection of invented prose, missing/inconsistent basis, foreign/duplicate earlier passages, inappropriate news/unrelated temporal claims, exact current/earlier wording, reuse without another charge, export escaping and source withdrawal.

The initial runs exposed old mock responses still emitting arbitrary explanations or changing tone without updating their newly required basis. Those fixtures were corrected, preserving their original behavioral scenarios; product validation was not loosened. An export assertion expected the word “unavailable” whereas the existing UI correctly says source excerpts are withheld; its assertion was corrected. A heading-edit command initially ran from the wrong directory, then was corrected and rebuilt. All original logs are retained. The final suite includes the later export case; earlier partial counts are not additional distinct tests.

## Actual-source evaluation

Four packets and criteria were frozen before dispatch: retained Microsoft, NVIDIA and Amazon news/discussion plus a separately labelled fictional NovaCompute packet. The fictional packet extends the previous causal/stance controls with reversed attitude, simultaneous mixed opinion, bare buyback authorization and an explicitly adverse reported outcome. No source was newly acquired. No independent participant labels or unseen benchmark are claimed.

All four requests completed and validated, covering **51 items**. All **135 quotation associations** match their originals: 102 label-basis, three earlier-attitude, eleven parent and nineteen news-comparison citations. There is no freely generated per-item explanation field that can add a sale cause or future financial payoff. This is an enforceable output restriction, not proof of correct tone, completeness, source truth or general grounding across the app.

**30 of 34 selected tone criteria matched. Four did not:**

- Microsoft's spending/margin-warning report remained neutral instead of the predeclared negative/mixed options.
- NVIDIA's buyback authorization remained positive instead of the predeclared neutral expectation.
- The fictional benchmark question was unclear instead of the predeclared neutral expectation. It remained nondirectional, but this still fails the frozen exact-tone criterion.
- The fictional security-handling description was negative instead of the predeclared neutral expectation.

All three changed-attitude cases retain the current and earlier wording and the intended directional label. Only NVIDIA exactly matches the predeclared separate passage lists. Both fictional transitions include the earlier sentence in the main selection as context as well as in the earlier disclosure; their exact separation criterion therefore fails. The card heading was clarified after inspecting this result, without changing the paid output or retroactively relaxing that recorded expectation. A single passage can legitimately contain both views, so an unconditional disjoint-ID rule would be incorrect.

Every item and all six news-comparison links were reviewed, beyond the selected tone checks. Further concerns include inferred criticism of Microsoft's patching practice, a negative interpretation of an earnings-yield comparison, and question/rumour labels on snippets that also report developments. The selected excerpts expose that ambiguity but do not resolve it. The actual Amazon sample matches its four selected criteria and has no additional unsupported per-item generated clause because those clauses are no longer accepted. This is sufficient for a dated local demonstration, not a clean broad semantic-quality gate.

## Installation, preservation and spending

Evidence: `.local/live-tests/sentiment-extracts-20261003T072024Z/`. Installation creates a source/database backup and checks all protected prior research/private records and watch settings. Schema remains 28. The reviewed Amazon reading is appended using the exact previously paid request and response; its saved source cutoff remains 05:46:10 UTC on 3 October, not a claim of fresh collection. Existing readings remain exact. No private idea, approved condition, review action or watch is changed. All watches stay off, and no update is published automatically.

Four paid requests cost **US$0.4039975**. Cumulative confirmed usage is **US$10.936487** across **249 calls**, plus unchanged **US$0.301565** historical maximum accounting, leaving **US$8.761948** of the same **US$20** allowance. The two original ambiguous calls remain unresolved with separate maximum-accounting decisions; there is no new uncertain charge or automatic paid retry.

## Five-perspective review

These are five perspectives applied by one agent, not independent consultants or customer research.

| Perspective | Assessment |
| --- | --- |
| Product | Original wording makes sentiment easier to challenge and removes invented per-item explanations. Broad private-risk noise and standalone answer errors remain; this phase does not redefine those features as complete. |
| UX | Showing the basis up front and an earlier-view disclosure makes changed opinions inspectable. Long posts and multi-sentence excerpts can increase reading effort; student comprehension remains unmeasured. |
| Research/ML | Exact-source and output-shape guarantees are stronger than prompt-only wording rules. Four tone misses, two non-exact temporal splits and additional interpretation concerns prevent a general accuracy claim. |
| Engineering | One versioned sentiment route, one ledger, source-specific schemas and shared evidence presentation preserve the existing architecture. No extra verification stage, provider, migration or automatic paid retry is needed. |
| Business | A real dated Amazon example improves the pitch demonstration. Source transparency does not establish recurring value, willingness to pay or viable service margins. |

The full implementation plan remains incomplete. Next work should improve the classification and broad reasoning-alert failures using explicitly defined source relationships, and continue the remaining requirement audit. Further narrow passing tests must not be presented as proof of the whole product or participant value.
