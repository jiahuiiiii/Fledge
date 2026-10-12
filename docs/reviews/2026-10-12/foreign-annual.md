# General 20-F annual support and Alibaba recovery

The owner authorized general 20-F support and a normal Alibaba annual-data fetch so BABA can appear in AMZN's comparison. The previous adapter accepted only 10-K/10-Q forms; accepting a new form alone would still leave the annual classification, ratio currency and chart validation incorrect.

## Implementation

`filing_rows` accepts 20-F/20-F/A as annual reports. Performance, financial story/depth/income views and bounded original-history plans share that annual classification. History dependencies stay in the same form family. Existing domestic normalization remains exact in saved-payload replay. 6-K is not interpreted as a standard quarter; 40-F and arbitrary foreign forms remain unsupported. A safe fixed unsupported-form reason distinguishes a known coverage gap from an unexplained transport failure without exposing exception text.

`sec-foreign-annual-1` selects one explicit supported currency and standard accounting namespace from the selected accession, form and filed date. US GAAP uses the existing whole-company revenue concepts and operating income; IFRS uses `Revenue` and `ProfitLossFromOperatingActivities`. A unique complete annual revenue pair identifies the basis. A current-only USD convenience translation cannot displace a complete native-currency pair. Multiple complete bases, conflicting totals, invalid numeric precision and incompatible fiscal windows remain withheld. Growth and margin preserve their original currency, inputs, formula and exact decimal result. No issuer branch, currency conversion, custom-tag mapping, segment estimate or inferred zero was added.

20-F/A keeps only figures actually reported in that amended accession. Existing domestic amendment-note proof cannot inherit an older foreign figure. Monetary cards and revenue-size comparisons still require explicitly reported US-GAAP USD facts; native CNY/EUR inputs are never relabelled USD. Percentage rows identify their accounting basis, input currency and filing form. Native calculation amounts have readable currency labels in the evidence dialog. The existing 120-day fiscal-end rule is unchanged.

## Actual BABA source collection

One normal structured SEC refresh succeeded through the existing collection route, using configured identity, pacing, size bounds, cooldown, leases, permission checks and source transactions. The completed operator script must not be rerun. It made no model call, watch-setting change or private peer write.

Source check: `df9ff50c-6538-426e-818f-df7770b84c8a`. [BABA FY2026 20-F](https://www.sec.gov/Archives/edgar/data/1577552/000119312526231755/baba-20260331.htm), accession `0001193125-26-231755`, filed 20 May 2026, period 1 April 2025–31 March 2026. The saved first-party structured facts provide:

| Input or result | Saved value |
| --- | ---: |
| Current annual revenue | CNY 1,023,670,000,000 |
| Previous annual revenue | CNY 996,347,000,000 |
| Operating income | CNY 50,150,000,000 |
| Calculated revenue growth | 2.742317686508816707432250000% |
| Calculated operating margin | 4.899039729600359490851543955% |
| Separately reported current USD revenue | USD 148,401,000,000 |

All ratio inputs belong to that same accession and US-GAAP/CNY basis. BABA's fiscal end is 90 days from AMZN's 31 December 2025, so BABA is plotted under the existing rule. MSFT's 30 June 2026 end remains 181 days away and excluded. Actual installed financial-story and deferred workspace-financials reads also succeed, with annual 20-F identity and only explicitly reported USD amounts in monetary views.

Collection changed 15 expected source tables: `document_lineage`, `document_versions`, `documents`, `fact_scopes`, `filing_calculations`, `instrument_state`, `observations`, `performance_current`, `performance_snapshots`, `research_snapshots`, `sec_payload_current`, `sec_refresh_state`, `source_checks`, `source_payloads` and `source_request_clock`. Schema 49, environment and cumulative model ledger stayed exact. Installation preservation below starts after this authorized collection; no all-table equality claim is made across collection.

## Verification and installation

The offline backend suite passed 2,022 tests with 93 optional skips. Final focused verification passed 113 with 12 optional skips after the final safe-error and shared annual-classification changes, which were completed after the full suite began. Coverage includes native US-GAAP/IFRS ratios, USD convenience amounts, competing currencies/taxonomies, conflicts, invalid numbers, missing amended facts, unsupported forms, normal collection and permission withdrawal. Frontend verification passed 162 tests, build and scoped formatting; syntax and diff checks pass.

Actual saved-payload replay over all 13 saved companies proves the 12 domestic ratio/performance and permitted current comparison projections remain exact against the pre-change modules/captures. The actual BABA annual projection exactly matches its newly stored result. The existing isolated full comparison journey passed with no source/model requests. Candidate and installed browser suites each passed 12 checks, using actual installed API data with explicit read-only peer parameters, blocked writes and blocked external requests. Cases cover AMZN at 1440/980/390/320, BABA at 1440/390/320, growth and margin bars, explicit USD size, 20-F links, native calculation amounts, MSFT exclusion, keyboard Escape/focus and no errors/overflow. Screenshots were inspected.

Concurrent status/alignment interface work began after the tested build. An isolated source copy restored those unrelated files from their pre-edit backups without modifying the shared source. Its rebuilt 30-file bundle exactly equals the original tested candidate. Installation used this frozen bundle, retained older assets and guarded all backend/migration/config sources and this task's frontend files. Unfinished unrelated UI edits remain in the working tree and were excluded from this installation.

Idle admission locks closed the restart race. App-only restart 53025 → 32699; the research-loading worker advisory lock was confirmed. Frontend index `79dfff6b` and all 30 candidate files were verified over HTTP; old assets remain. All 116 tables, schema 49, environment and ledger remain exact from before installation through installed browser/final verification. PostgreSQL was not restarted. No additional source/model/watch/private-peer action was used for verification.

After that successful installed verification, the separate bar-alignment task installed index `fbbabab6` on the same app process. Its baseline is exactly this task's installed index, and its frozen source retains every 20-F/frontend source file exactly; the only functional difference is its separately verified Overview bar CSS. A repeated final guard correctly detected the changed index. No duplicate restart or overwrite was performed. The actual 20-F installed browser suite was repeated against that combined frontend, and final preservation checks accept it only with the verified baseline/source relationship and exact served bundle. Original successful installation verification is retained as `verification-initial-install.json`.

Evidence: `.local/live-tests/foreign-annual-20261012/`. Recoverable source/database/index backups: `.local/backups/foreign-annual-20261012/`; the pre-collection and pre-install database dumps are private. `collection.json`, `replay.json`, `isolated-build-verification.json`, `candidate-browser.json`, `installed-browser.json`, `installation.json` and `verification.json` retain the outcomes. Do not rerun the completed collection or installer scripts.

## Diagnostics and limits

Retain initial guessed path/query-column diagnostics; the nonexistent amendment-test filename ran no tests; an authored shared-view assertion initially expected a mapping where the API supplies a list. Browser diagnostics retain the initial disclosure selector, compact USD-label location and an enhanced evidence assertion that expected unrounded input text instead of the intended display rounding. These harness assertions were corrected and the final checks pass. Preserve the subsequent concurrent-frontend guard and the unrelated whole-tree diff warning for a new trailing blank line in `financial-reading.md`; this task's scoped diff check passes. The web reader could not load the companyfacts API and rejected the original 11.7MB HTML above its size bound; the normal bounded structured SEC client succeeded. Numeric reconciliation here is against saved SEC structured facts, with original-report links, not an independently downloaded original-HTML reconciliation.

Recognized general patterns are supported; universal issuer/taxonomy coverage, complete native-currency financial statements, foreign quarterly reports, FX normalization and general accounting comparability are not claimed. The interface exposes basis differences rather than declaring every peer economically interchangeable.
