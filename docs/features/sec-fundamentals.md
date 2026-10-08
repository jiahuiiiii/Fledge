# SEC fundamentals connection

Implemented and live-checked 2 October 2026. Microsoft submissions/companyfacts were imported at 2026-10-01T17:33:16Z; the selected financial inputs were reconciled against the original filing. Synthetic browser evidence remains separate from the actual Microsoft workspace.

## Connect

Add a declared project/contact identity to the private `.env`, for example `SEC_USER_AGENT="Thesis research your-contact@example.org"`, using your real contact address. It is sent only as the SEC request header. It is not an API key. It is never exposed by the workspace API, stored in evidence or sent to OpenAI.

In the app choose **Add company**, then Microsoft, Apple or Alphabet. Open that workspace and choose **Refresh filings**. Adding a company itself makes no network request. Refreshes are manual, at least 15 minutes apart, with no automatic retry. A global persisted request clock reserves at most one SEC request per second. Failed and denied checks preserve earlier evidence and create a visible coverage gap. Local clock checks expose coverage older than 24 hours and interrupted attempts without fetching anything. Optional financial reporting-age limits are implemented separately; see [reporting age](reporting-age.md).

The API is free and does not need an API key, according to [SEC API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces). The SEC asks automated clients to declare a user agent and limits aggregate requests to 10 per second; this app stays below that bound. [Access guidance](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data) · [Developer resources](https://www.sec.gov/about/developer-resources)

## What is calculated

The latest recent 10-Q/10-K or amendment is selected by reporting end and acceptance time. An older/truncated response cannot move current fundamentals backwards. Only whole-entity US-GAAP USD values in that selected accession are used:

- Revenue growth: `(current revenue / comparable prior revenue − 1) × 100`.
- Operating margin: `operating income / revenue × 100`.

Supported revenue concepts are `RevenueFromContractWithCustomerExcludingAssessedTax`, `Revenues` and `SalesRevenueNet`; operating income uses `OperatingIncomeLoss`. Conflicting total concepts or incompatible periods abstain. Annual durations are 350–380 days, direct quarters 70–110 days. A prior comparison must end 357–373 days earlier with duration difference no greater than seven days. Actual start/end dates remain visible; these are bounded compatibility rules, not general fiscal-calendar inference.

There is no annual-minus-YTD quarter, custom-taxonomy mapping, segment comparison, currency conversion or cross-accession stitching. A latest amendment without compatible figures leaves them unknown; old facts remain in history but cannot silently become current again. A denominator of zero or less is undefined here. Results outside the existing −100% to 1,000% monitoring range abstain. Annual and quarterly conditions are explicitly different. The current workspace follows the latest filing period; phase 14 now adds separate annual/direct-quarter research views in [Financial performance](financial-performance.md). The original two-metric monitoring calculation still follows the latest active filing.

Transport parsing retains fractional numeric lexemes as strings rather than passing through binary floats. Stored selected inputs canonicalize mathematically insignificant zeros; the parsed payload retains original fractional spellings. Arithmetic uses Decimal with 28 significant digits, without display rounding before evaluation. The interface rounds display to two decimal places and exposes the stored value and exact selected inputs. Inputs beyond the supported 100-digit/exponent bound are rejected.

## Evidence, security and identity

Parsed companyfacts and submissions payloads are immutable. The source calculation stores its accession, original filing URL, selected inputs, formulas, method version, result/unknown reason and limitations. It is visibly an app calculation, not a verbatim filing excerpt. Availability is first committed retrieval in this installation, never backdated to publication. Older saved evaluations retain exact input identities.

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
