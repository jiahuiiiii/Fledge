# Phase 16 — alert quality purpose review

Parent-authored review through five professional perspectives. It is not five independent consultants, expert consensus or student validation. Independent agents remain unavailable under the recorded account limit.

| Perspective | Finding | Decision / remaining question |
| --- | --- | --- |
| Product | Paired beliefs/questions expose both over-alerting and missed evidence. A date that contradicts a belief can be quiet context for an open question. | Preserve the distinction. The next product question is whether a new concrete answer to an open research question deserves its own update type rather than only context; this phase does not add one. |
| UX | A sentiment label can appear more comprehensive than its eight-item sample. | Candidate-pool and selected counts are now visible. The installed MSFT view shows 8 selected from 45 candidate stories. Reading a larger source list is not the same as analysing all of it. |
| Data / ML | One Apple challenge was missed because the passage filter swallowed a complete sentence after an ellipsis-bearing quotation. Google counterparty relevance was too restrictive. | Fix quoted sentence boundaries and clarify concrete business relationships. Preserve all original failures. Exact citations and matching labels still need semantic review. |
| Engineering | Frozen request hashes prevent silently changing inputs/prompts in a supposed repeat. End-to-end app tests and model-quality tests answer different questions. | Add a bounded evaluation runner, strict scorer and inert reviewer packet; use the original paid ledger. Re-run every packet whose wire input changed. Existing app histories and watches remain untouched. |
| Commercial | The measurable outcome is better evidence handling, not more generated alerts. | The broad Reddit-risk disagreement needs independent/user feedback. Do not infer willingness to pay, retention, cost-to-serve or validated alert accuracy from this small corpus. |

## Baseline and corrections

The original manifest was frozen before nine paid requests at `.local/live-tests/alert-quality-v1-20261002T041333Z/`. It uses 18 previously unclassified news versions, one previously unclassified social version, five reused social versions and six new authored reasoning situations. Some sources cover previously encountered events. The source packets were deliberately selected for tests rather than produced by the live eight-item sampler; these are module-level actual-source evaluations, not alerts that fired prospectively.

The first sentiment run matched 46 of 48 prewritten field checks across 24 source/company assignments. The two mismatches concern one Google/Anthropic revenue-channel item: relevance and sentiment. Initial private checks matched 46 of 48 prewritten relation checks. Against the frozen alert expectations, there were seven requested connections caught, one missed Apple connection, one additional Microsoft risk and 39 quiet results. These are counts within the authored test set, not population precision/recall.

The Apple miss was traced to preprocessing, not merely model judgment: the future availability sentence was absent from the supplied passages because it followed a quoted ellipsis in the same segment. The corrected splitter retains that exact sentence under a suffixed passage ID. The source's original date and punctuation remain unchanged. The Google classifier now retains the concrete partner/channel relationship while using neutral target sentiment rather than inheriting Anthropic's risk or revenue.

A separate targeted retest froze the same expected labels/raw source text at `.local/live-tests/alert-quality-v2-20261002T042428Z/`. Request-hash comparison showed the quote-boundary fix also changed four other reasoning packets; they received a separate follow-up manifest at `.local/live-tests/alert-quality-v2-followup-20261002T042731Z/`. Together these rerun all nine cases on the final configuration. They are corrective, in-sample retests, not new held-out evidence.

The Microsoft social-risk mismatch remains deliberately unforced: an attributed broad AI-economics argument may be useful when investigating monetisation, but the frozen stance case expected it to remain quiet because it does not establish Microsoft revenue. Keep both the expectation and the model's risk interpretation for external calibration. Do not rename this disagreement as a confirmed semantic error or silently tune it away.

## Software verification

The integrated suite after the passage fix passes **390 backend checks** with the saved SEC corpus. Final prompt/UI changes pass **70 focused checks**, five frontend checks, build and the sentiment/watch browser journey. Tests cover quoted punctuation variants, preserving exact excerpts, excluding only ellipsis-bearing parts, unchanged plain/reasoning segmentation, request-hash changes, missing/duplicate/foreign records, gates and escaped reviewer HTML. The app browser shows the candidate-pool disclosure. Software tests use disposable data and mocked providers.

The source/database backup is `.local/backups/phase16-alert-quality-20261002T042356Z/`. Installation preserved every existing row and private environment value. No migration was added; schema remains 15. Initial/corrective raw outputs, frozen expectations, retained failures, scores, budget snapshots, source hashes and review HTML remain in the three evidence folders. Final measured outcome and accounting follow.

## Final result and accounting

All nine final-configuration cases completed. The three sentiment batches match **48/48 prewritten field checks**; the six private reasoning cases match **47/48 prewritten relation checks**. After applying the paired company-relevance gates, all eight expected alert connections were retained, 39 expected quiet items stayed quiet, and one additional Microsoft social-risk connection remained. This is one labelled disagreement within 48 authored source/reasoning combinations; it is not an established population false-positive rate. No expected connection was missed in this corrective set.

All **286 source-quotation associations** across initial and corrective runs match their exact stored originals. The final Apple challenge cites the newly preserved availability sentence; its question counterpart now accurately reports the planned date as context. The Google counterparty item is relevant/neutral, without allocating another company's combined channel revenue to Google. Existing main-account versions, watches and alert publications match the pre-evaluation snapshot. Main watches remain off. No evaluation result was inserted as a live product alert or substituted into the shared app sample.

The eighteen paid requests cost **US$0.7234535** confirmed. Cumulative building-period spending is **US$2.794291 confirmed**, plus the same **US$0.13926 maximum hold**, 103 calls and **US$7.066449 remaining**. There is no new ambiguous charge; the original interrupted charge remains unsettled and its maximum is still held. No new budget was created.

The final combined reviewer packet and `verification.json` are in `.local/live-tests/alert-quality-v2-followup-20261002T042731Z/`. Raw calls and original source/expectation manifests remain in their original folders. The source split, concrete-relationship contract and sample-count UI are installed. Broader unseen cases, independent/user review, semantic event grouping, broader sources and a measured return-visit benefit remain outstanding.
