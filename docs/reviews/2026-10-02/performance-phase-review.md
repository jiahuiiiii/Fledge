# Phase 14 — fundamentals purpose review

Parent-authored review through five professional perspectives; these are not independent consultants or participant results.

| Perspective | Purpose and result | Remaining concern |
| --- | --- | --- |
| Product | Users can put cash generation, profit and balance-sheet facts next to the company story. Separate annual/direct-quarter views close a clear research gap. | Valuation, longer trends, normalized total debt and broader issuer coverage remain missing. |
| UX | Fifteen rows are grouped by business performance, cash generation and balance sheet. Exact dates are visible; formulas/inputs open on demand. Unknown and zero differ. | Long pages can still require scrolling; beginner comprehension and whether these metrics answer their actual questions require participants. |
| Evidence | Same-accession facts, direct periods, explicit YTD cash, no incomplete debt total, decimal formulas and 146 original-filing input checks support this bounded output. | Custom tags, issuer accounting differences, restatement breadth and general accuracy are not established by three issuers. The audit-reader correction is preserved. |
| Architecture | Reuses SEC transport, request clock, payload retention and tested ratio selection. Adds immutable financial snapshots and a separate current pointer without changing saved monitoring definitions. | Current UI lacks financial-snapshot history/export selection; two-metric monitoring does not automatically expand to every displayed row. The older historical-source presentation concern remains separate. |
| Commercial | A stronger factual basis supports the proposed research companion; reading the view adds no model cost and needs no new paid source. | Revenue, retention and cost to serve active investors remain unvalidated. More metric rows are not proof of willingness to pay. |

Acceptance: 345 backend checks, five frontend checks, build, financial-performance browser and existing SEC/monitoring browser pass. Six original filings yield 146/146 exact current/comparison input matches after correcting the independent audit reader for nested `fixed-zero` tags. All original files and the initial audit are retained. See [the implementation contract](../../features/financial-performance.md).

The next core product gap is transparent valuation scenarios, while alert quality still needs broader unseen-case evaluation. Do not turn these financial values into automatic trade recommendations or claim student validation.

## Actual installation and current records

Backup: `.local/backups/phase14-financial-performance-20261002T032925Z/`. Evidence: `.local/live-tests/financial-performance-20261002T032925Z/`. Installation verified preservation of every preexisting row/value and private configuration. Three fresh SEC refreshes prepared the new statements; all six reports matched the independently reconciled saved corpus and returned unchanged existing monitoring inputs. Main saved versions, assessments and watch settings matched the frozen pre-install records. No main watch was enabled.

The final browser correction also verifies an initially empty view receiving financials: the newer report is selected unless the user has chosen a view. Existing SEC approval/history behavior remains passing. This phase used no paid request; confirmed spend remains US$2.0708375 plus the original US$0.13926 maximum hold, 85 calls. No provider uncertainty was silently settled.
