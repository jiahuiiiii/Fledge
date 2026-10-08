# Phase 15 — valuation purpose review

Parent-authored five-perspective review, not independent consultant signoff or participant evidence.

| Perspective | What this phase adds | Remaining question |
| --- | --- | --- |
| Product | Users can make the growth/margin/multiple assumptions behind an investment story explicit and compare up to three cases. Their research and saved conditions are not overwritten. | Whether this helps students reject unsupported narratives, compared with a spreadsheet or sourced notes. |
| UX | Blank starting inputs, optional labelled examples, source-base dates, reference adoption, sensitivity grids, saved comparisons and downloads give a concrete workflow. Failed saves preserve inputs. | Comprehension of total equity value, annual-base horizons, TTM differences and the distinction from a share-price target needs user observation. |
| Evidence | Decimal calculations, same-snapshot annual base, undefined loss cases, exact reference provenance and dated source comparisons separate evidence from assumptions. | Finnhub reference ratios are supplied values; their numerator/denominator timing has not been independently reconstructed. Candidate companies are not validated peers. |
| Architecture | Reuses SEC snapshots, Finnhub transport, collection locks, account policies and export conventions. Concurrent saves are idempotent; history is immutable and later source changes cannot rewrite it. | Broad-account performance, general issuer coverage and production identities remain outside this local phase. |
| Commercial | A local calculator adds research capability without additional model spend. | More functionality does not establish recurring demand or pricing. Validate whether alerts plus explicit reassessment create sufficient ongoing value. |

Review-driven details: avoid automatic assumptions; distinguish common-equity earnings from operating margin; keep terminal equity values undiscounted and company-wide; expose periods and reference timestamps; preserve original source/assumption records; use formulas relevant to the selected method only. Scope remains P/E and P/S, not DCF, EV or per-share targets.

Automated acceptance: 368 integrated backend checks, 23 focused final valuation checks, five frontend checks and build. New valuation and existing financial browser journeys pass. Initial fixture/capitalization test failures and their corrections are preserved. Actual installed-case evidence follows.

## Installed actual-case verification

A fixed plan was saved before installation/retrieval in `.local/live-tests/valuation-20261002T035657Z/frozen-plan.json`. Source/database backup is `.local/backups/phase15-valuation-20261002T035716Z/`. The migration preserved every preexisting row and the private environment exactly.

Three explicit fresh free-tier Finnhub checks supplied references. Actual annual bases and supplied multiples were:

| Company | Annual revenue USD | Annual end | Supplied P/E TTM | Supplied P/S TTM |
| --- | ---: | --- | ---: | ---: |
| MSFT | 331,839,000,000 | 2026-06-30 | 28.7586 | 11.5913 |
| AAPL | 416,161,000,000 | 2025-09-27 | 37.2976 | 10.3011 |
| GOOGL | 402,836,000,000 | 2025-12-31 | 16.9937 | 9.3076 |

The bases match the installed immutable financial snapshots from the earlier six-filing reconciliation. Reference values match the retained provider fields; they were not independently reconstructed from market capitalisation and earnings.

Two methods for each company produced six private QA saves, plus one main-account Microsoft comparison titled **Pitch example — illustrative assumptions**. Frozen cases used a 2-year horizon, a simple identity case (0% growth, 10% net margin, 10× P/E), a 10%-growth/20%-margin case using that company's supplied P/E, a negative-margin case with no P/E value, and a 10%-growth P/S case. All assumptions were authored for tests, not forecasts. A separate rational-arithmetic checker matched **150 case/grid outcomes**, including the main-account example. Duplicate save requests returned the same identities; stored reads and inert exports matched the previews. Existing main-account reasoning, assessments and watch configuration were unchanged, and watches remain off.

The actual in-app browser displayed the saved MSFT example and downloaded `thesis-valuation-41763399-371a-4c3c-8e5a-143cf9328d09.html` successfully. The three new supplier requests were free-tier requests; this phase made no model calls. Original accounting remains US$2.0708375 confirmed plus the same US$0.13926 maximum hold, 85 calls. Preserve the original ambiguous charge as unsettled.

Evidence includes frozen expectations, raw reference payloads, exact annual snapshots, private saved records, seven HTML exports, account/budget before and after, verification JSON, scripts, test logs, screenshots and source hashes. These are software/arithmetic checks on actual inputs, not proof of valuation quality, peer suitability, alert usefulness or participant demand.
