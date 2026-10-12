# SEC fundamentals connection

Implemented and live-checked 2 October 2026. Microsoft submissions/companyfacts were imported at 2026-10-01T17:33:16Z; the selected financial inputs were reconciled against the original filing. Synthetic browser evidence remains separate from the actual Microsoft workspace.

## Connect

Add a declared project/contact identity to the private `.env`, for example `SEC_USER_AGENT="Thesis research your-contact@example.org"`, using your real contact address. It is sent only as the SEC request header. It is not an API key. It is never exposed by the workspace API, stored in evidence or sent to OpenAI.

In the app choose **Add company**, then Microsoft, Apple or Alphabet. Open that workspace and choose **Refresh filings**. Adding a company itself makes no network request. Refreshes are manual, at least 15 minutes apart, with no automatic retry. A global persisted request clock reserves at most one SEC request per second. Failed and denied checks preserve earlier evidence and create a visible coverage gap. Local clock checks expose coverage older than 24 hours and interrupted attempts without fetching anything. Optional financial reporting-age limits are implemented separately; see [reporting age](reporting-age.md).

The API is free and does not need an API key, according to [SEC API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces). The SEC asks automated clients to declare a user agent and limits aggregate requests to 10 per second; this app stays below that bound. [Access guidance](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data) · [Developer resources](https://www.sec.gov/about/developer-resources)

## What is calculated

The latest recent supported 10-Q/10-K/20-F or amendment is selected by reporting end and acceptance time. An older/truncated response cannot move current fundamentals backwards. Domestic calculations retain whole-entity US-GAAP USD values in the selected accession. Foreign annual ratios use the bounded single-currency rules below:

- Revenue growth: `(current revenue / comparable prior revenue − 1) × 100`.
- Operating margin: `operating income / revenue × 100`.

Supported revenue concepts are `RevenueFromContractWithCustomerExcludingAssessedTax`, `Revenues` and `SalesRevenueNet`; operating income uses `OperatingIncomeLoss`. Conflicting total concepts or incompatible periods abstain. Annual durations are 350–380 days, direct quarters 70–110 days. A prior comparison must end 357–373 days earlier with duration difference no greater than seven days. Actual start/end dates remain visible; these are bounded compatibility rules, not general fiscal-calendar inference.

There is no annual-minus-YTD quarter, custom-taxonomy mapping, segment comparison, currency conversion or cross-accession stitching. A latest amendment without compatible figures leaves them unknown; old facts remain in history but cannot silently become current again. A denominator of zero or less is undefined here. Results outside the existing −100% to 1,000% monitoring range abstain. Annual and quarterly conditions are explicitly different. The current workspace follows the latest filing period; phase 14 now adds separate annual/direct-quarter research views in [Financial performance](financial-performance.md). The original two-metric monitoring calculation still follows the latest active filing.

Transport parsing retains fractional numeric lexemes as strings rather than passing through binary floats. Stored selected inputs canonicalize mathematically insignificant zeros; the parsed payload retains original fractional spellings. Arithmetic uses Decimal with 28 significant digits, without display rounding before evaluation. The interface rounds display to two decimal places and exposes the stored value and exact selected inputs. Inputs beyond the supported 100-digit/exponent bound are rejected.

## Evidence, security and identity

Parsed companyfacts and submissions payloads are immutable. The source calculation stores its accession, original filing URL, selected inputs, formulas, method version, result/unknown reason and limitations. It is visibly an app calculation, not a verbatim filing excerpt. Availability is first committed retrieval in this installation, never backdated to publication. Older saved evaluations retain exact input identities.

## General 20-F annual reports — 12 October 2026

20-F and 20-F/A are annual reports throughout structured acquisition, performance selection, financial-history/depth/income classification and bounded original-history plans. 6-K is not treated as a standard quarterly report, and no new quarterly subtraction or conversion is inferred. There is no issuer allowlist.

`sec-foreign-annual-1` calculates annual revenue growth and operating margin from recognized standard-taxonomy facts in one exact accession/form/filed date, accounting namespace and explicit currency. US GAAP uses the existing three revenue concepts plus `OperatingIncomeLoss`; IFRS uses `Revenue` and `ProfitLossFromOperatingActivities`. Supported monetary currency codes are bounded explicitly in the adapter. A unique complete annual revenue pair identifies the basis, so a current-only USD convenience translation cannot replace complete native-currency inputs. Multiple complete currency/taxonomy bases, conflicting totals, invalid precision, mismatched dates, absent standard concepts or incompatible prior periods stay withheld. Custom/segment facts and inferred zeros remain excluded. Actual periods, native inputs and calculation identities remain visible.

Monetary cards and revenue-size comparisons retain their existing requirement for explicitly reported US-GAAP USD facts. An issuer's explicitly reported USD convenience amount may be shown with that source; the app performs no exchange-rate conversion. Native CNY/EUR amounts are never relabelled USD. Percentage comparisons accept the supported foreign annual basis, disclose the currency/accounting namespace and retain the existing 120-day fiscal-end rule. A 20-F amendment uses only its own reported figures; domestic unchanged-note proof cannot inherit an earlier foreign amount. Unknown reporting formats now have a fixed unsupported-format failure reason rather than a generic transport failure.

One authorized normal BABA structured refresh succeeded on 12 October. Its [FY2026 20-F](https://www.sec.gov/Archives/edgar/data/1577552/000119312526231755/baba-20260331.htm) covers 1 April 2025–31 March 2026. Same-accession CNY revenue 1,023,670,000,000 versus 996,347,000,000 gives exact growth `2.742317686508816707432250000%`; CNY operating income 50,150,000,000 gives margin `4.899039729600359490851543955%`. The source also explicitly supplies USD148,401,000,000 current revenue. Its fiscal end is 90 days from AMZN's, so the existing comparison rule includes it. MSFT's 181-day exclusion remains. No model call or watch/private-peer action was required.

[Verification](../reviews/2026-10-12/foreign-annual.md). This supports recognized 20-F annual patterns, not every issuer's taxonomy or complete native-currency financial statements. A subsequent [comparison display change](competitor-position.md#different-year-ends-remain-visible--12-october-2026) now plots MSFT as clearly labelled different-year-end context, while keeping its 181-day gap outside the peer average and ranking.

Raw response ordering and unused YTD/historical facts do not change material source identity. Equivalent number spellings do not create new documents, assessments or alerts. Changed raw payloads remain stored for inspection. One restricted `thesis_source` role writes shared evidence and clock state; it cannot read private ideas or model accounting. Short shared collection transactions are serialized; HTTP occurs outside transactions. A request attempt has a lease and identity; interrupted/replaced attempts cannot later publish a result.

Each successful source check records the exact active document version. If corrected inputs later return to an earlier value, the earlier immutable source version becomes current again and generates the appropriate new assessment; the intermediate correction remains in history. Retrieval timestamps alone never select the active version after such a return.

SEC structured facts may be displayed locally and evaluated by code. They remain excluded from the current authored-source OpenAI selection route. The separate market adapter now supplies Finnhub quotes/news for the authorized local pitch. No market prices, consensus, financial advice, management-guidance extraction or news acquisition is supplied by this connection.

## Verification and live reconciliation

The offline corpus includes annual/direct-quarter separation, 53-week comparability, ignored YTD rows, wrong company, mismatched currencies/periods/accessions, duplicate equivalent numeric spellings, wire-level decimal preservation, zero denominators, stale-response rejection, missing amended facts, idempotent repeat, role isolation, denial, age, interrupted requests and synchronized clock/commit concurrency. Browser cases use explicitly synthetic SEC-shaped data only.

Microsoft 10-K accession `0001193125-26-323660`, filed 2026-07-29, covers 2025-07-01–2026-06-30. Original filing: [Microsoft 2026 annual report](https://www.sec.gov/Archives/edgar/data/789019/000119312526323660/msft-20260630.htm). The downloaded original HTML is retained privately under `.local/live-tests/`. Its non-dimensional inline-XBRL USD contexts and scale=6 values match the selected companyfacts inputs:

| Input | USD | Original displayed millions |
| --- | ---: | ---: |
| Revenue | 331,839,000,000 | 331,839 |
| Comparable revenue | 281,724,000,000 | 281,724 |
| Operating income | 155,237,000,000 | 155,237 |

Code-computed growth is 17.78868679984665843165651490%; operating margin is 46.78081840892722073053498835%. The UI displays 17.79% and 46.78%. This verifies these selected figures for one filing; it is not validation of every issuer, filing type or accounting concept. A permitted repeat refresh at 18:14:19Z returned unchanged and preserved facts, source versions and the cached market briefing. Broader issuer coverage remains separately checkable. No additional paid API call was needed for the reconciliation.

## Filing failures and recovered checks — 12 October 2026

Known structured-data failures now retain safe categories for timeouts, connection errors, unreadable responses, size limits, HTTP statuses and a busy shared connection. The UI explains which stage failed: the filing list or reported financial figures. Only fixed app-authored wording and validated numeric response codes are exposed; raw exception text, response bodies and contact identities remain excluded. Unknown exceptions retain the generic failure, and older records are never retroactively assigned a cause. Existing pacing, fifteen-minute cooldown, size/host bounds, no automatic retries, denied status and transaction rollback are unchanged.

Original-document acquisition requires a successfully saved, recent filing list. Its dependency message now explains that missing or stale filing details prevented the check. A failed structured check and blocked originals can therefore be the same underlying failure, not two independent missing datasets.

A skipped filing step can now display a newer successful or failed source checkpoint recorded by a direct filing update or the daily filing watch, instead of repeating an older loading-run error. The checkpoint must match the company, remain permitted and predate the current run. Newer failures stay visible; current failures/running steps never borrow success; the immutable loading/source records are unchanged.
