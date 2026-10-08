# Findings tied to their own evidence — phase 42

The previous live evaluation found plausible but unsupported additions to sentiment explanations, incorrect company/product ownership in an answer, an assumed different parent author and social opinions marked as reported facts. This phase addresses those observed failures before broadening the product.

## Implementation

Sentiment method `thesis-source-sentiment-9` and question method `thesis-research-answer-5` select citation fields before explanation/finding text in their structured output. Answers select evidence points and direct-answer citations before their direct answer. A shared writing instruction requires each finding to stand on its own selected passages, preserve antecedents, entity ownership and current versus superseded views, and avoid invented causes, durations or payoff conditions. Source-platform metadata is now explicit in sentiment inputs, without adding author identity or extra source votes.

The answer validator rejects `reported` points that cite any social source. Previously, adding one news citation could bypass the all-social test. Mixed-source interpretations and contrary evidence remain possible; no prose or label is silently rewritten. Existing saved results retain their original interpretation, method and citations. All source limits, original-parent boundaries, withdrawal, private ownership, model, cumulative budget, watch settings and no-automatic-paid-retry rules remain unchanged. There is no new model stage or schema migration.

Citation ordering and instructions are an authoring hypothesis, not a proof of semantic correctness. The mixed-source rule is a deterministic boundary; the actual wording must still be checked against source text.

## Software verification

91 focused checks passed. The broad run passed 796 checks, skipped six expanded-filing replays because their corpus was not configured, and failed two HN replays because the runner pointed at an incorrect directory. No product code was changed in response to that configuration error. The verified original-HN and expanded-filing paths were then supplied to the three affected test files: all 51 checks passed, including those eight cases. This covers 804 distinct backend checks across the runs, with overlap in the follow-up; it is not 847 distinct checks. Automated provider calls are mocked and all databases are disposable.

Five new cases exercise social-source laundering across all four finding kinds and preservation of explicit platform metadata without adding votes or leaking author hashes. Existing checks cover saved-record immutability, older-method notices, parent withdrawal, source membership and history/download access. No frontend code changed in this phase.

## Bounded live evaluation

Eight requests were frozen before dispatch: the same two Microsoft/NVIDIA sentiment packets and two question packets that failed previously, one retained Amazon packet per route, and one wholly authored NovaCompute contrast per route. Amazon is an additional selected development case, not an independently labelled unseen benchmark. Source text is retained original material, not freshly acquired news; the fictional company remains separate. Criteria require review of every generated label, explanation, direct answer and evidence point, including its own citations. No evaluation result is automatically published into product research. Watches remain off.

Evidence is in `.local/live-tests/finding-grounding-20261003T054610Z/`; the pre-install source/database backup is `.local/backups/phase42-grounding-20261003T054929Z/`. The frozen maximum is eight requests and US$1.6345675 total reserved maximum, within the existing US$20 cumulative cap. Actual usage and semantic findings are recorded below after completion.

## Sentiment outcomes

All four requests completed and structurally validated: 42 actual-source classifications and five authored classifications. Every item and all five news-coverage links were read against their selected quotations. The two specific prior explanation additions disappeared: Microsoft no longer invents a future payoff/end to margin pressure, and NVIDIA no longer introduces required AI spending. The ambiguous Microsoft reply remains unclear; the NVIDIA benchmark remains a question, and past dislike/current respect remains positive without an invented improvement.

The broader reading still fails the phase's semantic requirement. Microsoft's sold-shares explanation combines its selected title and software-sales statement into an argument about the economics behind current spending, which those two quotations do not establish. Its earnings-yield explanation adds “too heavily” to a growth-dependence observation. Its neutral label for a passage explicitly warning of lower margins is also questionable. NVIDIA continues to give a buyback authorization positive direction based on its record size and to attach general AI-sector cost/competition framing to the company; those target/direction judgments are not established by the selected excerpts. The benchmark/system explanation also describes “testing” where its selected statement only conveys cautious optimism, and one growth-opinion summary drops “possibly.” These are preserved as errors or review concerns, not silently accepted because the original two phrases were fixed.

The Amazon sample preserves the selected distinctions: offloading chips is not labelled distress; praise for another nuclear stock is not assigned to Amazon; the generic holdings list is unrelated; Synopsys results remain separate; incomplete source passages are not reconstructed. The earnings-yield explanation names the 30-year Treasury while its selected passages only say “long bond”; the term is present elsewhere in the source but absent from those quotations. Treat this as an additional citation-specificity concern, not proof of a clean complete sample.

The authored contrast matches the intended five directional labels, but the sold-shares explanation says the poster sold **because** of GPU economics. The two sentences are adjacent and do not explicitly establish that cause. This is a clear failed grounding criterion despite correct labels and exact quotations. Citation-first ordering plus additional instructions are therefore insufficient by themselves. None of these four results is promoted as verified product research. Retain the earlier method and these responses for a more targeted verification approach; do not claim improved aggregate accuracy from one run per packet.

## Question outcomes so far

The Microsoft answer preserves the Microsoft/Apple distinction in its main answer, avoids claiming an official policy or different parent author, and now cites the nearby antecedent for “an argument like that.” Its second point still calls that a “broad security-risk argument,” although the selected antecedent only describes an inability to provide a valuable service because of a hypothetical unusual Linux user. That wording still depends on unselected wider context. The direct answer is more restrained, but this is not a clean whole-answer pass.

The NVIDIA response correctly avoids `reported` labels for its social findings, but omits every required parent citation. The existing validator rejects it. It also again foregrounds the historical driver criticism and omits the explicitly stated current respect from the answer and finding, failing the semantic criterion independently of the structural rejection. Preserve the completed charged response; no answer is saved and there is no automatic retry.

The Amazon answer distinguishes the announced chip-design/power deals from the sought chip offload, retains the given amounts and capacity, and explicitly limits missing spending detail to the supplied tables. It does not infer completed savings, AI-specific margins, zero capital spending or Amazon growth from Synopsys growth. Its three evidence points and direct answer meet the selected review criteria; this is one developer-reviewed retained-source case, not general answer accuracy.

The authored answer preserves company/product ownership and does not invent improved drivers or benchmark results, but it omits the explicit current respect from both the direct answer and its driver finding. It gives the superseded dislike prominence instead. This fails the frozen stance criterion even though all quotations resolve and the answer structurally validates. Source selection, quotation correctness and faithful synthesis remain different checks.

## Accounting, preservation and decision

All eight requests returned usage; seven results structurally validated and NVIDIA's question response was rejected. The phase cost **US$0.5605155**, bringing cumulative confirmed spending to **US$8.919994** across **216** calls. The two historical maximum holds remain **US$0.301565**, leaving **US$10.778441** of the owner's original cumulative **US$20** allowance. No new timeout, unresolved-charge blocker or automatic retry occurred. No source refresh, product publication, saved-idea edit or watch activation occurred. All protected research, private records and watch settings remained exact.

The deterministic mixed-source guard and explicit source metadata are implemented. The revised authoring method remains a fallible model interpretation, not a validated quality improvement. This experiment does not satisfy the intended semantic gate: two old exact phrases disappeared, but other overreach and omission remain, including a clear authored causal error. Do not add more prompt rules and call the issue closed. The next bounded experiment should independently test whether a separate, source-complete verification pass can catch unsupported clauses and material omitted context before publication, while preserving useful supported answers. The existing theme checker provides a reusable pattern, but its success cannot be assumed to transfer; the positive controls must survive and the extra call must share the same ledger. No such additional stage was implemented or dispatched in this phase.

## Five-perspective review

These are five roles applied by one agent, not independent consultants or participant evidence.

| Perspective | Conclusion |
| --- | --- |
| Product | Correct labels with invented explanations still undermine the core promise. Fix faithful readings before widening features. |
| Research | Eight frozen selected cases expose meaningful failures; retain them. The additional company and authored contrast are not a representative or unseen accuracy benchmark. |
| ML/data | Citation-first formatting plus more instructions is insufficient. Evaluate claim entailment and material omissions separately from citation identity. |
| Architecture | The mixed-source guard closes a concrete bypass without a new service or migration. Preserve immutable responses, source access, private ownership and cumulative accounting when evaluating a verification stage. |
| UX/business | Keep original sources and dated earlier readings available. None of this establishes comprehension, alert usefulness, retention or a sellable accuracy claim. The complete implementation plan remains unfinished. |
