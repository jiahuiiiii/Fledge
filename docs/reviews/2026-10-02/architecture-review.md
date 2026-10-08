# Thesis — bounded final architecture and purpose review

Reviewed 2 October 2026 by the architecture subagent. Scope: the local pitch MVP, especially real acquisition, private evidence comparisons, history, isolation, recovery and the one cumulative model budget. This is a code/evidence review, not an independent professional certification or user study. No code changes, provider calls, credential reads or original-database writes occurred during this final audit.

## Verdict

**No new release-blocking architecture or data-integrity defect was found in the reviewed slice.** The implementation now connects real company research with a person's saved reasoning; it is materially beyond the earlier shared summary plus notes demonstration. The bounded technical workflow is suitable for continued local pitching, subject to completion of the ongoing UI history-access check and honest reporting of the live comparison findings.

This does **not** establish that all implementation-plan acceptance criteria are complete. In particular, reliable semantic support/challenge classification, improvement over a chronological source summary plus notes, and sustained user value remain unproven. Exact quotation selection prevents altered quotations; it does not validate the model's explanation or relationship label.

The installed project is `/Users/jiahuiwong/Documents/GitHub/Thesis`; staging is `/private/tmp/thesis-purpose`. Eleven critical files matched byte-for-byte between those locations during this review: private review, market acquisition/briefing, SEC client/service, all three provider modules, state service, database transactions and migration 008. That establishes source agreement for this audited subset, not an independent verification of every installed database row or the running frontend build.

## Acceptance against the current guide

The controlling local-pitch sequence is [AGENTS.md](../../../AGENTS.md). The broader original sequence remains in [architecture.md](../../archive/planning/architecture.md).

| Stage | Covered in the current slice | Remaining acceptance or bounded exclusion |
| --- | --- | --- |
| Inspect and freeze | Actual Kestrel frontend/API conventions, selected evaluator behavior and Deus normalization/source mapping are recorded in `PROVENANCE.md`; the database is redesigned around immutable evidence and revisions. | This is selective adaptation, not full upstream feature compatibility. No need to install additional frameworks merely to resemble the older plan. |
| Establish persistence | Checksummed sequential migrations, restricted app/source roles, atomic whole-revision saves, expected-revision conflicts, immutable history and actual RLS tests. Migration 008 isolates private model requests/results and preserves shared budget totals. | Typed proposal generation/approval is not implemented. Production identity is deliberately outside this local release. |
| Connect research and review | Shared sources, deterministic figures, optional qualitative drafts, explicit numerical approval, complete assessments, private source-to-reasoning comparisons and exact historical revision/snapshot boundaries. | Private qualitative comparisons are explicitly requested AI interpretations. They are not approved monitoring definitions or a validated narrative-condition evaluator. |
| Background monitoring | Durable job manifests, leases, fencing, ordered catch-up, expiry boundaries, source coverage, grouped in-app changes and independent acknowledgement. Tests cover corrections returning A→B→A, unchanged polls, interruption and late completion. | Public source retrieval is manual; the worker processes committed evidence and local aging. Qualitative drafts do not autonomously receive relevance-filtered AI alerts. Nothing runs as a hosted always-on service. |
| Verify local demo | Earlier recorded/SEC/market/age browser flows are recorded; backend history and concurrent-read correctness have direct regression evidence. | The UX reviewer is completing qualitative comparison history access. Final browser verification/build identity and latest backup/install evidence belong in the main handoff. Export is not part of this scoped delivery. |
| Bounded live operation | Authorized SEC/Finnhub adapters, three named issuers, immutable original/calculated evidence, attributed snippets, optional paid analysis and one durable US$10 ceiling. | Live output quality evaluation is still being finalized at this review cutoff. Complete software execution must not be reported as complete research-quality acceptance. |

The broader fundamentals/expectations stage is partial: supported reported fundamentals and attributed news exist, but no consensus dataset, valuation model, broad social listening or general extraction pipeline exists. Historical evaluation currently includes saved-response replay and controlled adversarial cases, not a longitudinal labelled benchmark of confirmation precision, missed developments or detection delay. Systematic investment-strategy backtesting remains deferred.

## Material boundaries verified

### Private comparison, history and access

[`idea_review.prepare`](../../../thesis/research/idea_review.py) resolves the owner/version, same-company immutable snapshot and optional exact evaluation before spending. Source IDs are intersected with that snapshot's document list and availability cutoff. Changed source selection only ranks members of that allowed set; a change record cannot introduce an unrelated or future source. Active SEC evidence follows its saved checkpoint, and historical preparation does not borrow later corrections.

The packet preserves source cutoff separately from the evaluation's later assessment time and freshness. Expired reporting evidence therefore cannot regain fresh coverage merely because the original snapshot was fresh. `service.state` uses a repeatable-read, read-only transaction so its displayed evidence and comparison snapshot cannot come from different concurrent refreshes.

Private comparisons run outside database transactions and persist against their original revision/snapshot/evaluation. A synchronized test changes both evidence and reasoning while a mocked model call is in flight; completion stays on the old revision. Reopening that exact comparison reuses the immutable result. Actual non-superuser tests show that another owner and an anonymous connection cannot read private model calls, dispatches or reviews. The source collector cannot read the global model-total function.

### Acquisition and recovery

[`market.refresh`](../../../thesis/research/market.py) uses bounded quote/news requests, persistent pacing and cooldowns. Quotes are separate from research monitoring. Partial source failure preserves successful components and previous evidence; provider text with forbidden control characters or invalid Unicode is excluded item by item. Older quotes cannot replace newer ones. Completion checks the attempt token and lease, while the local interruption path fences late completion.

News corrections append occurrences, including a return to an earlier content hash. A URL can belong to more than one company. Current briefings apply a seven-day publication/availability window without deleting historical documents. Poll time alone does not change the shared briefing cache when eligible evidence is unchanged.

[`sec.refresh`](../../../thesis/research/sec/service.py) keeps HTTP outside collection transactions and checks completion after acquiring the shared lock. Normalization, amendment selection, fiscal scope and calculation trails remain independent of model output. Source aging makes no HTTP requests. These bounds are appropriate for three manually refreshed companies; this review does not assert production throughput.

### Paid work

[`ledger.reserve`](../../../thesis/providers/ledger.py), `settle` and `authorize_dispatch` preserve one global allowance across shared/private and mini/strong profiles. Reservations precede dispatch; unknown charges block further requests. Settlement chooses the stored model and immutable price version, not caller metadata. Reasoning tokens are already included in output usage. Unsupported models, price versions, service tiers or usage bounds cannot settle as a cheaper profile.

Independent tests cover a hidden private charge exhausting another owner's allowance, pending requests blocking both profiles, a stronger request not fitting a remaining allowance that still fits mini, legacy mini cache/charge preservation, and a mocked HTTP dispatch invoking the requested model's configuration gate exactly once per preflight/send boundary. No automatic paid retries were introduced.

## Remaining product-quality limits

1. **Traceability is stronger than semantic validation.** The new passage IDs ensure displayed source/reasoning quotations are extracted by code, with original case, punctuation and spacing. The model still authors the explanation and support/challenge/context label. Earlier live mini cases included rejected altered quotes and an accepted misleading relationship label; switching to a stronger profile must be assessed against the same expected outcomes, not counted as proof by itself. See the distinction required by [AGENTS.md](../../../AGENTS.md).
2. **Selection is bounded and can miss decisive evidence.** Private packets contain at most twelve current sources and 24 KB of source text, prioritizing changed evidence, the active filing and recent news. Company-name ranking and exact-content deduplication are useful heuristics; they are not exhaustive discovery or independent corroboration. Historical replaced text remains inspectable but is not necessarily supplied alongside its correction in the AI packet.
3. **Monitoring remains deliberately narrow.** The automatic numerical vocabulary is revenue growth and operating margin, with explicit fiscal period scope and optional reporting-age limits. No catalyst deadlines, narrative confirmation engine, consensus tracking, proposals or automatic qualitative relevance routing is implemented. The UI must not imply those capabilities from the presence of a saved idea or AI comparison.
4. **Local testing does not establish demand or research advantage.** Neither the tests nor the consultant reviews measure student comprehension, natural return behavior, willingness to pay or superiority to a sourced summary plus ordinary notes using the same evidence. This remains an explicit acceptance item, not a reason to add more infrastructure.

These are declared scope/quality limits rather than newly discovered database blockers. Production accounts, deployment, billing, external notifications and brokerage execution should not become prerequisites for the authorized pitch.

## Evidence and handoff accounting

- **Directly observed by this reviewer:** the most recent complete offline backend run after the model-profile change reported **187 passed, 15 skipped**; skipped cases require the opt-in saved real SEC corpus. Earlier focused runs covered private isolation, synchronized revision/acquisition races, passage-ID rejection, market correction chains and mixed-model accounting. All used mocked providers/disposable databases.
- **Real-record replay:** `tests/test_real_case_replay.py` defines fifteen opt-in cases using saved MSFT/AAPL/GOOGL SEC bundles, selected-filing numeric expectations, fiscal scope, expiry, reordering and wrong-company rejection. The main task separately reports having exercised these with the corpus. Their authored thresholds, replay timing and injected faults are not observed investor behavior or a prospective market backtest.
- **Actual live integration:** the main task reports real retrieval and filing reconciliation, and seven of eight stronger-model private cases completed at the time of this request without budget errors. This audit did not independently inspect or rerun that unfinished batch. The final number of accepted/rejected cases, semantic failures, model versions and cumulative charges must come from its retained records; no final figures are inferred here.
- **Historical versus current documentation:** dated phase sections should retain their historical counts/spending. The current-status header and current private-review contract should be refreshed after the final live batch: they still describe the previous phase/current counts and the older quote-generation mechanism. The main task owns this update. Old figures are not errors when clearly presented as historical checkpoints.

The strongest defensible pitch claim is: **a local research companion that connects supported company evidence to saved reasoning, preserves exact history, and offers explicitly requested, cited AI comparisons alongside code-calculated numerical monitoring.** It is not yet a validated investment-analysis system or a complete implementation of the wider roadmap.

## Addendum — marked unfinished-source exclusion, 2 October 2026

This addendum records subsequent corrective implementation and supersedes the earlier audit's code/evidence cutoff. The earlier “no new release-blocking architecture or data-integrity defect” finding was a bounded, dated architecture finding, **not semantic approval** of AI outputs. A later actual Google UI case exposed a material fidelity failure: the model completed the source fragment “Google's internal...” as “Google's internal use”. Exact citation selection had not prevented that unsupported completion in its explanation.

The corrective change is implemented in `thesis/research/citations.py`, `idea_review.py` and `market_brief.py`:

- A shared eligibility function numbers original title/body passages first, then excludes every passage containing an ellipsis marker (`...`, `…` or bracketed forms). Surviving original passage IDs remain stable, and complete preceding sentences remain eligible. User-authored reasoning segments are unchanged.
- Both private-comparison and shared-briefing provider requests use filtered projections. Ellipsized titles and publisher metadata cannot expose an otherwise excluded fragment. Stored raw source titles/bodies and the source-inspection view remain unchanged.
- Rendering recomputes eligibility from the original source. A forged removed passage ID, a tampered stored selection list, or a quotation drawn only from a removed fragment is rejected. The shared route retains filtered text input; the private route selects stable passage IDs.
- Packets and rendered results carry `omitted_fragment_count`, separately from omitted-source accounting, with a visible limitation. Requests without surviving eligible evidence stop before reserving model spending; the shared route requires surviving news evidence, not only SEC context.
- Prompt/cache versions are now `thesis-private-evidence-3` and `thesis-market-brief-4`. Earlier model rows remain historical records and cannot satisfy a newly generated request under these versions.

**Directly verified here:** the complete backend suite passed **213 tests, zero skipped**, with `THESIS_REAL_CORPUS=/private/tmp/thesis-real-corpus`. Providers were mocked and storage was disposable. The added tests replay the exact public Google snippet, show the unfinished claim absent from both provider inputs, preserve the complete announcement sentence and raw source, reject removed citations/title bypasses, and verify unchanged numerical conditions/evaluations. They also cover all-fragment requests without ledger changes, conservative exclusion of a seemingly complete sentence ending `filing....`, unchanged user reasoning containing ellipses, and cache-version invalidation. The earlier 187-pass/15-skipped result above remains its historical checkpoint.

**Installation reported by the main task:** the corrected production files were installed in the existing Thesis project, with backup `phase7-complete-passages-20261001T192833Z`. Existing database rows, credentials and the cumulative ledger were preserved. This subagent did not perform that installation or read credentials. The main task has started a fresh twelve-case actual-provider private-comparison batch; its outputs, semantic acceptance and final charges are not included in this addendum and must be reported from the retained batch evidence. No provider request or paid spending was performed for this corrective implementation or its verification.

**Remaining limitation:** this is conservative exclusion of explicit ellipsis-marked passages, not a general sentence-completeness detector or proof of meaning. It can exclude a complete passage that happens to contain an ellipsis, and unmarked fragments or misleading interpretations may still occur. It does not establish correct support/challenge classification, independent corroboration, investment validity or benefit over a sourced summary plus notes. Fresh live evaluation remains necessary evidence of behavior after the correction; a passing structural regression is not a substitute for that evaluation.
