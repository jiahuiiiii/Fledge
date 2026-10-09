# General financial-data gap audit — 9 October 2026

The owner reported missing financial data across stocks and requested a general diagnosis and resolution. Read-only audit covered every saved real company: AAPL, AMD, AVGO, FN, MRVL, MU, NVDA and QCOM, including the current measures and all retained annual/trailing/balance history.

## Shared causes and fixes

- **Incorrect standard concept spelling:** the non-operating interest selector used `InterestExpenseNonOperating` rather than the actual `InterestExpenseNonoperating`. Correct the selector and authored fixtures. General `InterestExpense` remains a different definition and is not silently substituted.
- **Available common revenue concept overlooked:** choosing each input's preferred tag independently can create a false mismatch. A bridge can now choose one common tag only when all three original values, periods, currencies and filing vintages are independently present under that exact tag. No cross-concept alias is inferred. This restores three NVIDIA historical revenue rows in 2022 while preserving genuine transitions such as Apple's 2019 gap.
- **Broader capital spending:** when no preferred PP&E fact is reported for that current filing/period, support the separately labelled `PaymentsToAcquireProductiveAssets` category. It includes software and intangible assets. Use a complete same-concept annual/YTD bridge; missing comparatives, currency problems, conflicts or negative capex are not concealed. Free cash flow carries that category's explanation through the history card, reading, evidence and separate peer measures. This restores NVDA and QCOM cash flow without representing their category as PP&E-only spending.
- **Different balance categories:** explicitly labelled accounts-and-other receivables, trade payables, intangibles excluding goodwill, and PP&E including finance-lease assets can be shown when the preferred category is absent. Conflicting or unsupported preferred facts still block substitution. Only the selected category contributes to the chart; residual categories recalculate to prevent double counting.
- **Complete liabilities components:** current plus noncurrent liabilities can supply an absent total when both are explicitly reported and nonnegative. Parent equity is not assumed to equal consolidated equity, and missing minority interest is not zero.
- **Borrowing reported with finance leases:** after preserving the original direct total and complete debt-component priorities, an explicitly reported total of debt and capital/finance leases can subtract the same-filing, same-date finance-lease liability. This restores MU borrowing excluding leases. No missing short-term debt, lease balance or credit-facility balance becomes zero.
- **Amendment scope verified too narrowly:** a general, bounded annual MD&A-only rule requires an explicit sole-purpose declaration, an unchanged-other-items clause, actual Item7 content (optionally Item15 exhibit index), no Item8 amendment, no restatement/financial-statement change in the note, the complete original/amendment chain, and all original identity/hash/permission/conflict checks. It applies to any issuer and retains the exact explanatory note. This establishes that Item8 financial statements remain unchanged for AMD's retained amendment, restoring net income, cash flow and related measures. Income-flow charts now use the same resolver and reject mixed amended vintages.

These are read-time research projections: `sec-financial-depth-2`, `sec-financial-story-2`, `sec-income-flow-2` and `sec-amendment-resolution-2`. Peer source validation accepts the corresponding known method versions; amendment basis identity includes the resolver version. Original saved performance, monitoring inputs, valuation bases, model evidence and source payloads remain unchanged.

The category definitions were verified against the [official FASB 2025 taxonomy documentation](https://xbrl.fasb.org/us-gaap/2025/elts/us-gaap-doc-2025.xml), retained locally with the exact selected definitions. They are distinct definitions, not interchangeable aliases.

## Saved-data result

| Company | Previously null values restored across retained annual/trailing/balance rows |
| --- | ---: |
| AAPL | 2 |
| AMD | 39 |
| AVGO | 4 |
| FN | 56 |
| MRVL | 18 |
| MU | 186 |
| NVDA | 55 |
| QCOM | 131 |
| **Total** | **491** |

Counts are presentation fields, including derived measures, repeated annual/trailing windows and supporting metrics; they are not491 independent source observations. No previously populated measure becomes missing. Previously populated values are unchanged except the explicitly unclassified chart residuals, which shrink as newly supported reported categories are included. Exact before/after matrices are in `changes.json`.

Examples from the retained current periods: NVDA trailing FCF127.006bn (broader productive-asset spending), QCOM10.416bn on that same stated definition, AMD trailing net income6.434bn/FCF8.403bn, and MU borrowing3.052bn after removing2.670bn finance leases from5.722bn combined obligations. These are saved observations with their original dates, not newly collected current financial results.

## Remaining gaps

The audit retains, rather than fills, unresolved reporting transitions (including AAPL2019 and several other historical quarters), missing preceding annual filings in the retained issuer history, incomplete borrowing components (including AAPL/FN/NVDA/QCOM), missing specifically non-operating interest, absent categories and AMD's unsupported consolidated liabilities total. A separately supplied parent-equity figure or a partial commercial-paper/long-term balance does not establish a complete total. Optional consolidated net-result fields may be absent while the displayed parent result is valid. No stock-specific constants, inferred zeros, newer-filing backfill, undocumented concept aliases or AI estimates were introduced.

The work addresses financial figures and comparisons raised in this conversation. It does not claim to restore inaccessible paid supplier datasets, resolve the existing unknown AI charge, or fill unsupported forecasts.

## Verification

- Full guarded offline backend:1746pass/66optional skips. Following final debt-priority and malformed-source refinements:135focused pass/3optional skips. Tests cover actual-tag selection, both capex definitions, preferred zero/conflict/currency/missing-prior rules, same-tag revenue bridges, exact lease subtraction, explicit liability components, amendment scope/foreign documents/restatements/conflicting facts, source withdrawal and original evidence preservation.
-105frontend checks and production build pass; touched frontend formatting and scoped diff checks pass. New checks retain the broader cash-spending wording and recognize current projection methods in peer evidence.
- Existing isolated Financials browser passes1440/980/390/320, including source withdrawal, missing/negative values, explicit periods/evidence, keyboard/focus and zero app writes/external requests.
- Saved eight-company candidate and installed browsers pass1440/980/390/320px: actual latest revenue/net income/FCF, broader spending labels, exact original report links, AMD amendment evidence, MU lease subtraction, keyboard/Escape/focus and no page overflow/errors. Desktop AMD, phone NVIDIA and installed phone Qualcomm screenshots inspected. Installed checks use the live endpoint without substituting calculated responses. Automatic loading mutations and external requests are blocked; no app writes. These checks are developer verification, not independent usability or accounting validation.

Evidence `.local/live-tests/general-data-gaps-20261009/`; backups `.local/backups/general-data-gaps-20261009/`. Retain initial guessed route/path/glob diagnostics, the `reported` local-variable collision, authored amendment fixture lacking net income, the case-sensitive interest fixture corrections and first browser focus on a wrapper instead of its button (plus request-disposal teardown). Corrected tests target the real button; no product behavior was changed to satisfy that selector. FASB XML could not be rendered by the web tool; Python's certificate configuration also failed. The system certificate store successfully retrieved the same official XML with verification enabled. No certificate check was disabled.

Idle app-only restart9766→55882 left the database running. The readiness guard stopped before frontend publication on AMD's nested amendment `available_at` timestamp serialization (`T` versus space); the differences were retained. Canonical comparison of timestamps verifies every financial amount/input/identity exactly for all eight companies. Publication resumed without another restart, after all114table fingerprints and the ledger matched the original pre-install audit. Source/file-set/prior-index guards pass; atomic index `ce8b47ee`,43candidate files (including retained earlier hashes), schema47, environment and local-pitch session verified. Old assets retained. All114tables are unchanged across the entire installation.

No app source refresh, model request, private research edit, watch change, email or Telegram send was performed. Public taxonomy verification was separate from app data collection. The original419calls,24.3479945confirmed/1.1624375reserved/4.489568available and one unresolved FN hold remain exact.
