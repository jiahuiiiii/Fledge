# Six-company coverage and fuller alert evidence — phase 23

2 October 2026. Parent-authored review from five perspectives; this is not an independent consultant panel, investor study or market-accuracy benchmark. The deliverable remains a local pitch MVP. The full implementation plan is still incomplete.

## Outcome and purpose

The workspace now supports Microsoft, Apple, Alphabet, NVIDIA, Amazon and Meta using the same source, financial, sentiment and private-review contracts. The additional three companies were chosen as bounded implementation examples under the ongoing full-plan request, not as investment recommendations or tickers individually selected by the user. No company registration creates an idea or watch.

This phase also corrects a substantive alert-source omission. A newer NVIDIA roundup displaced a fuller report in the same semantic-repeat group, leaving the initial private answer unable to identify the explicit buyback authorisation and remaining capacity. Private checks now keep distinct unseen source texts within the existing sixteen-source cap. Semantic keys still suppress previously seen watch coverage; one check still creates one grouped publication. Historical outputs and both prompts remain unchanged.

## Actual source evidence

Evidence: `.local/live-tests/catalogue-expansion-20261002T073911Z/`. Its manifests precede acquisition or paid requests. The public source responses, original filings, exact model requests/responses, frozen expectations, original failures and corrective retests are retained locally.

| Company | SEC CIK | Direct-quarter period end | Original filing inputs matched | Daily sessions / raw OHLCV fields matched | Selected news / social |
| --- | --- | --- | --- | --- | --- |
| NVIDIA | 1045810 | 2026-07-26 | 42 across annual and quarter | 252 / 1,260 | 8 / 8 |
| Amazon | 1018724 | 2026-06-30 | 38 across annual and quarter | 252 / 1,260 | 8 / 2 |
| Meta | 1326801 | 2026-06-30 | 42 across annual and quarter | 252 / 1,260 | 8 / 4 |

The 122 selected current/prior financial inputs match nondimensional USD contexts in six original inline-XBRL filings. Primary identity references include [NVIDIA's annual filing](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/nvda-20260125.htm), [Amazon's annual filing](https://www.sec.gov/Archives/edgar/data/1018724/000101872426000004/amzn-20251231.htm) and [Meta's annual filing](https://www.sec.gov/Archives/edgar/data/1326801/000162828026003942/meta-20251231.htm). Exact quarterly URLs, contexts, source hashes and comparisons are in `reconciliation.json`.

Installation ingested these already retrieved, reconciled SEC responses; it did not claim another fresh SEC request. Finnhub quote/news and Yahoo daily-chart requests were new live retrievals. Each chart covers 2025-10-01 through 2026-10-01, excluding the current New York date. Raw-price-field reconciliation is not independent market-price or corporate-action verification.

NVIDIA and Amazon cash capital spending/free cash flow remain unavailable under the supported concepts. Amazon liabilities and some company-specific debt fields also remain unavailable. Quarterly cash flow retains its actual year-to-date dates. No zeros or unsupported tag substitutions were invented.

Public r/stocks retrieval succeeded. The other two configured communities failed; the app exposes those gaps. Sample sizes are small and selected; comments, other platforms and whole-market sentiment are not covered. The catalogue matcher excludes selected ambiguous terms such as “meta-analysis” and “Amazon rainforest”, but is not comprehensive entity resolution.

## Model and alert findings

Three actual sentiment requests classified 38 company/source items. Eleven specific semantic criteria were frozen after source acquisition and before model responses: ten matched. **One retained failure:** Amazon's reported proposed chip-financing transaction was labelled negative with “adverse if true”, although the supplied text did not establish the downside. No prompt was tuned or label manually overwritten to make that result pass. Eighty-six item/comparison quote associations match exact source passages; that does not make all interpretations correct.

News and social remain separate. NVIDIA's selected news is mixed/balanced and its social subset negative-leaning; Amazon's social subset is too thin for a directional aggregate. These describe the observed selected packets, not all investors or expected share returns.

Three private checks used authored questions in a separate QA account, with no watches enabled:

| Authored question | Initial result | Final reviewed result |
| --- | --- | --- |
| NVIDIA authorisation versus completed repurchases | A short roundup produced a partial answer; the fuller expected report was omitted by within-request grouping | After the code fix, the full report identifies $150bn additional authority and $235bn remaining unexecuted; it explicitly lacks an amount already repurchased |
| Amazon contracted nuclear power versus electricity delivery | Three relevant source connections; unrelated chip/healthcare/valuation stories stayed quiet | Contract, supplier and 690 MW are attributed to the report; a signed agreement does not establish current delivery. No corrective paid rerun was needed |
| Meta requested privacy penalty versus final/paid amount | One relevant source connection; product/valuation stories stayed quiet | Corrective retest retains both reports, including the jury finding and requested $35–40bn range, without claiming the requested sum has been ordered or paid |

The correction was retested explicitly for NVIDIA and Meta using the same frozen questions. All three final cases contain an expected direct answer; 61 quotation associations in those final private records match. This is a development retest, not unseen-case accuracy, prospective alert latency or a complete recall measure. Earlier 57-quote private records and the incomplete NVIDIA output remain preserved. Repeated requests reused records and incurred no extra charge/publication. Each check creates one grouped publication even when it includes several connections. Main-account ideas, watches and publications remain unchanged.

## Verification and delivery

- 528 backend tests passed using both saved public SEC corpora, including four order/automatic-mode regression cases for preserving fuller unseen reports, and existing previously-seen repeat suppression.
- Five frontend checks and the production build passed. The catalogue, sentiment and private-alert browser journeys passed at 320/390/1440px. The catalogue browser replays actual public filings; sentiment/alert browser fixtures are authored with mocked model outputs.
- Browser testing caught the original API's three-symbol restriction; it now validates against the shared catalogue. Unsupported symbols/extra fields remain rejected. A phone overlap between large percentages and period dates was corrected and visually checked.
- The installed NVIDIA daily-price and separate news/social panels were inspected in the app. Browser reads made no new model/source request.
- Source/database backups: `.local/backups/phase23-catalogue-20261002T075758Z/` and `.local/backups/phase23-catalogue-20261002T080928Z/`. Both installs preserved every preexisting row and private configuration. Schema stays 18.

Eight explicit calls cost **US$0.411555** in this phase. Original cumulative accounting: **US$4.7155785 confirmed**, plus the unchanged **US$0.13926 maximum hold** for the original interrupted request; **US$5.1451615** remains under the original US$10 ceiling. There are 146 calls and no new operationally unresolved charge. The original interrupted call's actual amount is still unsettled, not written off or represented as a known cost. No automatic paid retry was used.

## Five-perspective review

| Perspective | Judgment | Improvement / limit to preserve |
| --- | --- | --- |
| Product strategy | More recognisable companies let the same research-to-alert journey be demonstrated beyond the first three examples | Six large US companies are bounded coverage, not broad market validation. Prioritise useful question-specific alerts over ticker-count expansion |
| UX and accessibility | Dynamic company selection, explicit fiscal dates, separate source channels and phone spacing support the intended journey | Sparse social samples and failed feeds must remain prominent. A source count is not investor consensus; beginner comprehension still needs participants |
| Architecture and reliability | One catalogue removes registry drift; the API regression catches future mismatches. Existing adapters, schema and budget are reused | Exact content and semantic delivery keys serve different purposes. Never let a weaker unseen excerpt displace a fuller one merely to deduplicate a request |
| Research quality | Original-filing reconciliation and frozen actual-source tests expose both useful behavior and errors | Retain the disputed Amazon label and original NVIDIA omission. Exact quotes and a three-case retest do not establish broad accuracy or recall |
| Business and operating cost | No new API key, package or paid data supplier was needed; cache reuse works | US$0.411555 is a development batch cost, not customer unit economics or proof of subscription demand. Social availability and participant value remain unresolved |

## Next bounded work

Strengthen sentiment/alert quality with more varied, frozen source/reasoning cases and a transparent sourced-summary baseline, especially neutral transactions and vague headlines. Keep source coverage and completeness visible. The broader roadmap still lacks guidance/consensus time series, other social platforms, full articles/comments/transcripts, rolling financial trends, reverse valuation/DCF and participant evidence. Production accounts, hosting, billing and external delivery remain outside this local pitch request.
