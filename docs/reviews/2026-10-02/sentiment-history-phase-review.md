# Phase 22 — compare the evidence behind sentiment

This is a parent-authored review through five professional perspectives, not an independent consultant panel or participant study. It addresses the journey's requirement to show previous and current evidence together. The latest sentiment summary alone could not explain whether a difference came from new reporting, a changed sample, changed labels or an updated analysis method.

| Perspective | Finding | Outcome / limit |
| --- | --- | --- |
| Product | Users need to inspect what changed before treating tone as a reason to reconsider an idea. | Earlier/later news and social readings show selected, removed, relabelled and unchanged texts. Original quotations and sources remain accessible. Opening the view does not create an alert or alter a saved idea. |
| UX | A historical comparison should not overwhelm the main workspace or blur the two samples. | A collapsed panel, separate channel sections, paired readings and optional source detail preserve the existing workspace. Desktop uses two columns; phone stacks them. Visual review found identical displayed times in rapid test runs; numbered sample options now distinguish them. These numbers describe list position, not permanent record identity. Participant comprehension remains unmeasured. |
| Data / ML | An apparent trend can be a method change or a reanalysis of unchanged text. | Method, comparison-context and news-grouping changes have explicit warnings. Eighteen of 22 actual-record pairs select the same texts; 21 cross analysis methods. No line chart, synthetic confidence score or market-wide trend is inferred from this development history. |
| Engineering | Historical source inspection must resolve the exact old packet, not today's source list. | Read-only, company-scoped history/comparison APIs use one consistent database snapshot and existing whole-packet source-access checks. Withdrawal on either side withholds derived comparisons. No schema, prompt, provider or model change was needed. |
| Commercial | The feature helps explain recurring monitoring, but does not prove recurring paid value. | All comparisons reuse saved analyses and add zero provider/model requests. This does not measure willingness to pay, retention or normal customer serving cost. |

## Contract and reuse

[Sample comparison](../../features/sentiment-sample-comparison.md) records the boundaries. Full content hashes include headlines and are kept separate by source channel. Comparison-only news cannot become an added selected story. Relevance, tone, statement type and topic determine label changes; explanation wording alone does not. Original labels and summaries remain immutable, including earlier errors. Removed means outside the later selected sample, not retracted. Newly selected does not imply newly published or economically material.

The new view reuses the existing Deus-derived classification/source records, Kestrel-derived client/source controls, current permission checks and PostgreSQL. It adds no framework, source, model, prompt, migration or account/watch enrollment. Historical source-health snapshots are not reconstructed; the separate scheduled-check history supplies those only where recorded.

## Actual-record verification

Evidence: `.local/live-tests/sentiment-history-20261002T073014Z/` contains the prewritten read-check manifest, all comparisons, history payloads, independent raw-record counts, budget snapshot and unchanged-record verification. These are actual previously retrieved Finnhub/Reddit records, not fresh acquisitions or newly labelled evaluation cases.

- All **13 saved analyses across Microsoft, Apple and Alphabet** load through the source-access boundary.
- All **22 ordered same-company pairs** preserve the exact stored summaries and original title/body/URL payloads. Independently counted channel/content identities match added, removed, relabelled and unchanged totals.
- All **330 source quotation associations** across the unique saved analyses match their recorded text. This checks quotation integrity, not the truth of the AI interpretation or underlying social claims.
- **21 pairs cross analysis methods**; those comparisons warn against interpreting the difference as sentiment movement. **18 pairs select unchanged texts**, with reanalysis identified. These overlapping counts describe the existing development records, not a representative market dataset.
- The latest Microsoft pair uses the same current method: eight news items in both samples, with one newly selected text, one removed text, two changed classifications and five unchanged classifications. News groups move from six to seven; both aggregate tones remain mixed/balanced. All four social texts and their labels are unchanged. Changed statement-type labels count even if tone itself stays the same.
- Reads leave stored analyses, main saved revisions, watch settings, company/private alert publications and the original model ledger unchanged. No watch is enabled and no new review action is recorded.

The installed Microsoft workspace shows the verified pair and exact sample dates. Old outputs remain available with method warnings. This is not a prospective alert trial, independent accuracy/recall benchmark, measured detection delay or causal attribution of a tone change.

## Verification and delivery

**492 integrated backend checks pass**, including eleven new cases for cache/no-extra-entry behaviour, actual selected-text turnover, headline corrections, reclassification versus wording, method/context changes, complete-source withdrawal, company/order validation, stable tied-cutoff pagination and authenticated read-only endpoints. Existing saved public SEC records are used where required; model/provider tests are mocked.

Five frontend checks and the final production build pass. The new browser journey covers distinguishable sample choices, method/reanalysis warnings, separate news/social changes, exact earlier-source inspection, blank selection clearing, reload, disabled watch and 320/390/1440px layouts without writes or external requests. The existing sentiment/watch browser regression passes. Desktop and phone renders were visually inspected.

The pre-phase source/database backup is `.local/backups/phase22-sentiment-history-20261002T072839Z/`. Installation preserved prior records and private configuration. Schema remains 18. Final source hashes and verification logs/screenshots accompany the actual-record evidence.

Additional AI spending: **US$0**. The original ledger remains **US$4.3040235 confirmed + US$0.13926 original maximum hold**, **138 calls**, **US$5.5567165 remaining**, and no new unresolved charge. The old interrupted charge remains unsettled and its maximum stays deducted.

The bounded historical comparison is implemented. Wider sources/issuers, structured expectations, broader unseen alert evaluation, missing fundamentals/valuation features and participant comprehension/recurring-use evidence remain outstanding. This phase does not establish full-plan completion.
