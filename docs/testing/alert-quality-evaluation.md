# Alert quality evaluation — phase 16

This phase tests the product's main selling point against additional actual public sources and new authored reasoning. It adds a repeatable development evaluation and fixes a demonstrated source-selection failure. It is not an independent benchmark, student study or prospective alert trial.

## Frozen evaluation

`evaluate_alerts.py` validates one named case from a private manifest. Without `--execute`, it validates the exact request hash and estimates its maximum possible charge only. With `--execute`, it uses the existing production request/render functions and original OpenAI ledger under a separately labelled evaluation account. It does not alter product sentiment samples, ideas, watches or alert publications. An unchanged repeated request uses the ledger cache; ambiguous charges still stop execution. A case is capped at US$0.25 maximum reservation. The configured original cumulative cap remains authoritative.

```sh
.venv/bin/python evaluate_alerts.py --manifest .local/live-tests/alert-quality-v1-20261002T041333Z/manifest.json --case msft-sentiment
```

The actual source corpus remains private/local under `.local/live-tests/`; it is not bundled into Git or made a public dataset. The initial manifest freezes nine cases: three sentiment batches and two reasoning situations for each of Microsoft, Apple and Alphabet. It includes 18 previously unclassified news versions, one previously unclassified social version and five reused social versions. Some describe events seen in other reports before. Expected labels, rationales, exact source versions/text, cutoff, request hashes and source hashes were recorded before dispatch.

The reasoning situations contrast stated beliefs with open research questions. The model must not infer a directional position from a request for evidence. The relevance scorer reports supports/challenges/risks separately from quiet context. A paired company-relevance gate can show when otherwise useful evidence would be excluded upstream. These checks use deliberately selected source packets and do not measure the production eight-item sampler's recall, event arrival, worker scheduling or detection latency.

Scoring rejects incomplete, duplicated, foreign or ambiguous expected/results coverage. It preserves failed field comparisons and confusion counts against the developer's frozen labels. Label matches and exact quotations do not establish semantic truth. The inert HTML review packet shows the source, authored reasoning, explanation and selected passages, with the expected answers in a disclosure. Expert/user disagreement should be recorded separately rather than overwriting the frozen expectation. This approach follows [OpenAI's evaluation guidance](https://developers.openai.com/api/docs/guides/evaluation-best-practices): task-specific criteria and retained outputs need judgment and external calibration.

## Changes resulting from actual failures

### Complete sentence lost after a quotation

The Apple source contained an ellipsis inside a quoted opinion, followed by a separate complete sentence giving a future product-availability date. The existing sentence splitter did not recognise punctuation followed by a closing quotation. The ellipsis filter therefore excluded the availability sentence together with the earlier quote. The model could not challenge an already-available belief using evidence it never received.

`source_passages` now splits complete sentences at closing straight/curly quotations. Unsplit IDs remain unchanged; separated parts have explicit suffixes. Each part is still an exact source substring. The ellipsis-bearing part remains excluded; no text is reconstructed. User reasoning segmentation is unchanged. This does not solve arbitrary abbreviations, malformed text, all languages or complete-sentence detection in provider snippets. Saved historical results keep their original quotations and identities.

### Concrete relationships excluded as incidental mentions

The Google sentiment test labelled a disclosed customer/channel relationship unrelated because the headline subject was another company. Prompt `thesis-source-sentiment-2` clarifies that a concrete customer, supplier, partner, contract or revenue-channel relationship can be relevant to the target. Former-employee career mentions, ticker lists and unconnected sector stories remain excluded. Relevance and sentiment remain separate: another company's risks or combined revenues do not establish the target's losses, direction or recognised revenue. The model, endpoint, budget, output schema and private relevance prompt are unchanged. The prompt change is scoped to this classification contract, consistent with the [GPT-5.4 guidance](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-5.4).

### Sample size is visible

The sentiment panel now shows the candidate pool alongside the number selected for analysis. A reader can see, for example, that eight stories were analysed from 45 available candidate items. This improves disclosure; it does not expand source coverage. Historical cached analyses retain their original sample, model output and prompt identity.

## Verification and next questions

The source fix and evaluation tools pass 390 integrated backend checks with the saved SEC corpus. The final prompt/UI refinement passes 70 focused checks, five frontend checks, the build and the dedicated sentiment/watch browser journey. The installed browser shows the actual candidate-pool disclosure. Actual model outcomes and retained mismatches are recorded in [the five-perspective phase review](../reviews/2026-10-02/alert-quality-phase-review.md).

The development corpus is small and deliberately selected. A broad Reddit economics argument can be relevant yet too indirect for some users to want an alert; that disagreement remains recorded. Wider source/event coverage, semantic repeat grouping, participant noise preferences, independent labelling, prospective detection delay and measured recurring value remain open. No public deployment, new model, external notification or silent watch activation was introduced.
