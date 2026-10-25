# Financial extraction and optional recovery

Implemented 11 October 2026 for the local research application. These rules apply to registered SEC companies; there is no AAPL/INTU/QCOM/AMD extraction allowlist.

## Normal extraction comes first

The reader uses the saved SEC Company Facts response, then the exact original filing’s standard tagged facts, then supported complete statement/table structures. All inputs retain their reporting dates, currency, original filing, content hash and cell/context identifiers. This is a read-time research overlay; raw payloads, historical observations and numerical monitoring are not rewritten.

- Read missing whole-company standard USD facts directly from retained originals. An existing reported fact in any currency blocks replacement for its exact concept family and period; conflicts stay unknown.
- Sum separate product/service costs and explicitly reported cost amortization only when their categories reconcile to consolidated revenue and the full labelled cost section is accounted for. Separate selling/marketing and general/administration lines retain their calculation.
- Read separately displayed borrowing lines on a reconciled balance sheet. Keep its carrying-value scope explicit. A broad long-term-debt tag can be combined with current debt only when the original table proves separate current/noncurrent sections. Do not add overlapping short-term totals and commercial paper, assume absent borrowing is zero, or substitute leases.
- Recover an omitted liabilities subtotal only from the complete supported noncurrent-liability section plus current liabilities, and only when those amounts plus equity equal reported assets and liabilities-and-equity. Unknown, missing, foreign-currency, overlapping or unreconciled components block recovery.
- Use explicitly labelled debt-interest expense when the preferred non-operating-interest category is absent; its different scope stays visible.
- Read the company’s explicit operating-segment reconciliation, including reconciling items, when segment and consolidated revenue use different tags. All components must reconcile; negative adjustments remain listed without positive-width flows.
- Accept the standard geographic concentration qualifiers only for a complete reconciled geography table. Existing geography partition and conflict checks remain.
- An explicitly declared standard zero transformation can establish zero; an ordinary dash or `nil` cannot.
- Permit case-only member-tag continuity for past-12-month segment calculations only when original printed labels establish the same category. Require the complete annual/current/prior-year-to-date bridge and unchanged category set.
- Recognize an earnings-release Exhibit 99 description split across adjacent filing-table cells. The existing same-accession URL restrictions and normal collection schedule remain.

Only retained originals are read during page loads. Missing historical originals still require the usual **Update data** action; page reads do not contact SEC or AI. A number of limitations are real: incompatible periods, unsupported currencies/layouts, ambiguous definitions, amended reports without adequate evidence, and incomplete breakdowns remain gaps.

## Optional OpenAI recovery

Open **Financials → Fill missing figures** to expand the report checklist. The left-aligned header shows the report count. Shared missing figures are named once above the checklist; reports with different gaps retain their own labels. Choose individual reports or use **Select all**; **Clear selection** resets the choices. **Find figures with AI** reads only selected available reports, one at a time. A single combined maximum cost appears beside the action after selection; technical row counts and per-report costs are omitted from the main list. Limited samples retain one short availability note. Reports without suitable evidence or with a blocked reading stay visible and disabled. Opening, selecting or collapsing the checklist makes no AI call. A failed batch stops immediately, keeps completed suggestions and shows the failure; reloading the preview makes no paid retry. Saved readings remain under **Review saved suggestions**.

The initial target set covers revenue, cost, gross/operating profit, operating expenses, selling/general/administrative expenses, parent net income, operating cash flow, cash purchases of property/plant/equipment, assets, liabilities and cash. The model can interpret a custom tag using its original row text, but it cannot supply numerical answers. It selects known cell IDs and an allowed reported/sum/subtract operation. Code validates identifiers, dates, periods, units and exact decimal arithmetic. Incompatible or duplicate suggestions are withheld.

The sample is limited to 120 complete, dated, whole-company USD tagged cells and 30 kB of cell content. Omitted cells are disclosed when a reading is needed. Untagged amounts without established units/dates, arbitrary PDF/OCR extraction, IFRS, inferred missing values and AI-created segment partitions are not supported by this first fallback. This is a bounded interpretation aid, not proof that every financial gap is recoverable.

Suggestions remain unapplied until the owner selects them and chooses **Save reviewed figures**. Evidence includes the original report, cells, dates, explanation and calculation. Approved results are labelled AI-assisted, private to that owner and confined to financial research views. Uncheck and save to revoke an interpretation. Existing reported facts win; conflicting approved interpretations cannot create a confident result. Source withdrawal or a replaced original withholds the interpretation.

Migration 049 adds append-only, forced-RLS readings and reviews. It does not alter source or accounting rows. The existing GPT-5.4 mini profile, 2,000-output-token limit and cumulative US$40 ledger are reused. Identical settled requests are reused without another charge. Incomplete/unknown calls block retry; malformed settled answers cannot trigger a new paid attempt under the same identity. There is no automatic paid retry or new allowance. Whole input identities are checked again before dispatch.

The model’s semantic accuracy has not been independently established. Automated validation proves cell identity, arithmetic and structural constraints; the owner’s review is still needed to assess the financial meaning.

## Verified examples

Saved public-source replay, without new collection or AI calls:

| Company | Recovery |
| --- | --- |
| AAPL | Separately shown borrowing: US$84.344bn at 27 June 2026; derived borrowing/cash/equity views become available. |
| INTU | Borrowing US$7.669bn at 31 July 2026. FY2026 cost of revenue US$4.253bn and gross profit US$17.195bn reconcile to US$21.448bn revenue. |
| QCOM | Borrowing US$15.270bn at 28 June 2026. Explicit segment and geography reconciliations; past-12-month segment revenue US$44.069bn. |
| AMD | Complete liabilities section US$17.240bn at 27 June 2026; past-12-month segment revenue US$41.305bn after exact printed-label continuity checks. |

QCOM’s narrower cash-PPE-purchases target remains eligible for an optional interpretation; the existing broader cash-capital-spending reading remains distinct. No missing figure is filled merely to remove an “Unavailable” label.

See [implementation review](../reviews/2026-10-11/financial-recovery.md) for tests, deployment evidence and limitations.

## Use all suggestions at once — 25 October 2026

Above the report selector, **Use all suggestions from all N reports** saves every suggested figure from every reviewed report as that report's choices in one step (reads and saves reviews only; no AI call). Each report keeps its calculation, original rows and its own untick-and-save revocation, and a line says how many figures from how many reports are now used. If one report fails, those saved before it stay saved.
