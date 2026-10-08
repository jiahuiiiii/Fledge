# Phase 20 — ask a question before saving an idea

This is a parent-authored review through five professional perspectives, not an independent consultant panel or participant validation. The phase closes the journey gap in which changing a research question only changed a label while the company briefing stayed generic. Alerts and separate news/social sentiment remain the main recurring product features; question research is optional and collapsed within the market workspace.

| Perspective | Finding | Result / limit |
| --- | --- | --- |
| Product | A student should be able to investigate an uncertainty before asserting a thesis. | Custom cited answers, concrete gaps, bounded follow-ups, private history and optional transfer to the idea editor. Asking does not create an idea, enable a watch or resolve research. Real student task success remains unmeasured. |
| UX | A changed editor question must not relabel an earlier answer, and a saved answer must expose its source vintage. | The selected answer has its own question, parent and cutoff; reopening/history/download are read-only. Sources are progressively disclosed, and errors retain input. Question and existing sentiment journeys pass at 320/390/1440px. The expanded workspace is still long; comprehension and interaction effort require participants. |
| Data / ML | Valid quotations do not establish correct attribution or evidence type. | Actual-source tests exposed inferred prose marked reported, news opinions marked social, an internal-ID leak and app extraction limits attributed to the company. Preserve every output. Prompt/source formatting narrows attribution; code rejects IDs in prose. The UI now labels AI readings from actual cited source categories, not model-assigned point types. Semantic correctness beyond these cases remains unproven. |
| Engineering | Private question history must reuse the existing source access and metered model boundaries. | Migration 017 adds append-only owner records, same-owner calls and same-company parent links. No second framework/database/provider. Current entitlement rechecks cover reads/history/exports and withdrawal during generation. Follow-ups reuse only the prior question, not AI prose as factual evidence. |
| Commercial | A useful one-off answer does not itself prove recurring paid value. | The answer can lead into the existing saved-reasoning alert loop, while an unresolved or rejected idea remains a valid outcome. No subscription price, conversion result or customer willingness-to-pay claim follows from this phase. |

## Reuse and contract

[Question research](../../features/question-research.md) documents the behaviour. Deus's `grounded_answer.py` supplies the inspected sufficiency/abstention and dated-citation approach; Thesis adapts this into one structured metered call over existing sources. Kestrel-derived API/error/review conventions remain. No autonomous web search, additional key, package, external delivery or watch enrollment was added.

Selection is bounded lexical retrieval: up to eight recent company-mention news snippets, three optional Reddit posts and two filing tables. Reviewing the first unexecuted selection exposed provider-tagged articles with no target-company mention, so these are now excluded. The first selection manifest remains separate from the executed frozen manifest. Synonyms, implicit references, missing full articles and a narrow Reddit feed sample can still leave important evidence out.

The final prompt is `thesis-research-answer-3`. Filing scope statements now begin **Thesis extraction scope (not a statement by the company or SEC)**. The model can format existing numbers for reading, but does not calculate new facts or choose investment actions. Earlier prompt outputs remain unchanged and get a historical-method warning when opened or exported.

## Actual-source development cases

Six prewritten cases used previously retrieved Finnhub snippets, public Reddit posts and reconciled SEC-derived figures. They exercised the public question service, original persistent model ledger, immutable persistence, reopening and export; these are actual-source development checks, not prospective alerts, unseen accuracy or independent evaluation.

| Case | Observed result / qualification |
| --- | --- |
| Microsoft paid Copilot adoption | Initial answer abstained and identified missing paid-seat/revenue data. Its point labels mixed interpretation with reported evidence. The first correction then wrongly attributed our extraction scope to Microsoft's filing. The final correction says the supplied tables omit Copilot-specific figures and lists missing adoption/revenue information. |
| Apple Watch feature reports | Initial and final answers distinguish hoped-for sales benefits from actual paid demand. The final result limits whole-company data claims to the supplied tables, exposes missing Watch evidence and does not invent unit sales, clinical effectiveness or regulatory status. |
| Google publisher damages | Initial and targeted corrective answers distinguish permission to pursue roughly $3.2bn in claims from an award/payment. The initial answer printed raw source identifiers; v2 removes these, and code now rejects such identifiers in prose. This was not rerun under v3. |
| Microsoft cash-flow period | v1 reports USD127.494bn for 2025-07-01 through 2026-03-31, explicitly YTD rather than Jan–Mar alone. This matches the exact stored `operating_cash` passage. It was not rerun under v3. |
| Microsoft Reddit concerns | v1/v2 attribute concerns to selected posters, not market-wide consensus or verified outcomes. v2 explicitly avoids establishing a direct Microsoft risk from a CoreWeave post. It was not rerun under v3; broader counterparty-risk interpretation remains uncertain. |
| Exact Microsoft price on 31 December 2027 | v1 returns insufficient coverage and the fixed no-answer message, with missing future information rather than a forecast. It was not rerun under v3. |

There were **11 explicit paid calls**: six v1 cases, three targeted v2 corrections, and two targeted v3 attribution checks. All 99 quotation associations match their recorded source text (47 + 32 + 20). This count tests quotation integrity, not whether every generated inference is true. No general accuracy percentage is claimed.

The final Microsoft response still assigned `social_opinion` to news commentary and `reported` to some interpretive prose. Further prompt tuning was not treated as a reliable solution: the interface labels every generated point **AI reading**, with news/social/filing categories resolved from actual cited sources. The original model labels remain in saved evidence. A browser fixture reproduces the news-as-social error and verifies the correct news display. This fixes source categorisation in the UI, not semantic truth.

Evidence directories under `.local/live-tests/`:

- `question-research-20261002T062205Z/` — initial frozen cases, full requests/responses/results, exports and unchanged-main-state verification.
- `question-research-retest-20261002T062606Z/` — targeted v2 corrections, including the retained attribution failure.
- `question-research-v3-20261002T063006Z/` — two final attribution checks and final budget snapshot.

All eleven answers are retained: three Microsoft generations in the main account and eight QA answers under the labelled evaluation account. Existing ideas, revisions, watches, source snapshots and alert publications remained unchanged. No main-account watch was enabled. Earlier buggy answers are visibly marked when reopened; historical evidence is not silently rewritten.

## Verification and spending

- **466 integrated backend checks pass**, using temporary storage and the saved public SEC corpus; no paid calls occur in tests.
- **22 focused question checks pass**, including no-idea entry, private cache, parent/owner isolation, actual foreign keys, source withdrawal, late completion, exact citations, period identity, history pagination, inert export escaping and session/CSRF validation.
- Five frontend checks and the final production build pass.
- Question browser flow passes source inspection, follow-up, independent draft, download, historical reopening, preserved input after failure, reload and phone/desktop layouts. The existing sentiment/watch browser also passes after the feature integration.
- Source/database backups preserve every pre-existing row and the exact private environment. Final source installation verification is saved with the phase evidence.

Phase spending is **US$0.369055**, bringing the original cumulative ledger to **US$4.193536 confirmed**, plus the unchanged **US$0.13926 maximum hold** for the earlier interrupted request. Remaining under the original US$10 cap: **US$5.667204**, 136 total calls, no new unresolved charge. The old interrupted charge itself is still not settled; the retained maximum remains deducted. These development costs do not establish a customer serving-cost estimate.

The full roadmap remains incomplete. Wider sources/issuers, structured expectations, broader unseen alert evaluation, expected filing dates and participant comprehension/recurring-use evidence remain outstanding. Do not use more feature breadth or AI review votes as a substitute for testing whether students find and act on the right evidence.
