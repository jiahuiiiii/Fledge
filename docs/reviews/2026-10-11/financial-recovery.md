# Financial recovery review — 11 October 2026

Owner authorized a general deterministic extraction repair followed by an optional LLM fallback, starting with AAPL, INTU, QCOM and AMD. [Contract](../../features/financial-recovery.md).

## Outcome and design review

One agent reviewed the change through five lenses; these are not independent reviewers or participant validation.

- **Product:** fix extraction before offering AI. The first four companies’ key statement and segment gaps recover from retained originals. AI remains an explicit per-report option.
- **Financial meaning:** report exact dates and distinguish borrowing carrying values, debt interest, whole-group equity and narrower cash-PPE purchases. Complete table/reconciliation rules replace issuer-specific guesses. Unknown values are not zero.
- **UX:** the optional panel is visible in Financials, collapsed by default. Preview, maximum cost, original evidence, unchecked suggestions, explicit acceptance and revocation form one review path. Existing reported figures remain the primary content.
- **Engineering:** ephemeral overlays preserve immutable source/monitoring inputs. Exact accession/hash/cell identities and existing amendment resolution remain required. Private append-only reviews are protected by forced RLS. Candidate frontend excludes concurrent unfinished revenue-history/forecast work while preserving that source.
- **Validation:** deterministic fixtures, actual saved filing replay, metered transport mocks and responsive browser checks serve different purposes. No paid model evaluation occurred; real semantic accuracy of optional interpretations remains unproven.

## Verification

Evidence: `.local/live-tests/financial-recovery-20261011/`.

- Full offline backend: **1,857 passed, 66 optional skips** before the final narrow borrowing-layout and liabilities-section additions; all providers mocked.
- Final extraction suite with nine-company saved originals and the liabilities addition: **189 passed, one optional skip**. Includes AAPL, INTU, QCOM, AMD, AVGO, MU, NVDA, MRVL and FN; existing available flow values remain unchanged. AMD’s existing amendment proof is retained in the replay.
- Recovery, accounting and private-isolation suite: **98 passed**, including duplicate reuse, unknown-charge blocking, malformed settled responses, access withdrawn during dispatch, review/revoke and cross-owner denial.
- Isolated frontend: **123 checks** and production build pass. Browser: four saved companies at 1440/390/320, plus an authored, intercepted review/revoke case. Candidate and installed checks pass (13 cases each); installed monetary figures, original-report links, evidence dialogs and focus return are also checked in `installed-browser.json`. Desktop and phone screenshots were inspected. No real browser writes, source collection or AI request is permitted by these journeys.
- Actual numeric examples and remaining limits are in the feature contract. Recovery figures are calculations over original reported inputs, not newly fetched provider values.

## Installation and preservation

Recoverable backup: `.local/backups/financial-recovery-20261011/database-before-049.dump` (custom-format PostgreSQL backup, private file), original frontend assets and HEAD source archive. Migration 049 adds two empty private tables; schema becomes 49. First idle app restart: 6970 → 75374; final liabilities correction: 75374 → 79983. PostgreSQL was not restarted. The research-loading advisory lock is checked by its identity, not solely by its connection’s latest query.

The verified isolated frontend index is `99ea9fa6`; all 29 candidate files are checked, older assets retained. It includes the already-installed tone-header controls and this recovery UI, but not the ongoing FinancialHistory/RevenueHistory/forecast replacement. Shared concurrent edits are left intact. Final fingerprints show every pre-existing table except schema_migrations unchanged, both new tables empty, and the cumulative spending ledger unchanged. The final restart also verifies the environment and frontend index unchanged. Final tables/ledger fingerprints and installed browser result are recorded in the evidence folder. No new paid call, source refresh, watch activation, message, account reset or accounting adjustment by this task.

## Diagnostics retained

- Initial segment recovery incorrectly considered ordinary geography tables; six existing negative controls failed. Restricting the new path to the specified three-dimension qualifiers and complete global coverage fixed them.
- Optional original-corpus AMD harness initially omitted its existing amendment resolver, then the collector-supplied period metadata. Both failures are retained; the complete original evidence path passes.
- An initial default frontend build wrote live `dist`. The previously verified tone-header index and all retained assets were restored immediately; subsequent builds used isolated output/source directories. No source or accounting action was caused by that build.
- First installation completed the migration/restart/index switch, but its verification requested `/index.html` (the app serves `/`); the corrected verifier checks the root. A subsequent audit needed escaped SQL percent placeholders. Both failures are retained.
- A final-restart guard paused on an advisory lock. A read-only inspection identified the persistent worker lock; the final guard recognizes its exact hash and requires an idle holder. It does not bypass active loads/model calls.
- One formatting command used the repository root instead of the frontend dependency directory. This did not edit files. The candidate was built and tested from its isolated frontend source.

## Remaining limitations

This does not establish universal financial-statement extraction. Only known, proven layouts and USD reporting scopes qualify. Older missing originals, legitimate non-disclosures, foreign currencies, ambiguous tags, untagged/PDF cells and conflicting sources can remain unavailable. The optional AI fallback covers its listed statement totals, not arbitrary business segmentation or forecast fabrication. Source retrieval still uses existing consent, pacing and cooldown controls. No real AI run was made for this feature.
