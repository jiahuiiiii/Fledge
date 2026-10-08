# Thesis: predeclared real-evidence evaluation

Prepared 2 October 2026, 02:28–02:35 SGT, before the next implementation/test round. Read-only consultant review; no provider calls, keys, app edits or paid calls. This document is the only file written by this reviewer.

## Decision and evidence boundary

Use the existing Microsoft retrieval as a compact, reproducible development corpus, then reserve the incoming Apple and Alphabet evidence for prospective checks. Do not call the already reviewed and prompt-tuned Microsoft v1/v2 outputs a blind benchmark. The labels below are independently reasoned against the saved sources; the evaluator is an AI consultant, not an independent human financial analyst or customer.

Three result categories must remain separate:

1. **Real retrieval:** a recorded successful response from SEC/Finnhub and, for the selected Microsoft numbers, reconciliation to the original filing. This checks the observed response, not continuing provider reliability or exhaustive coverage.
2. **Replay of real evidence:** the unchanged saved records run through different questions, authored conditions, controlled cutoffs or duplicate deliveries. This tests software and evidence use; it is not an observed future market event or a real investor's behaviour.
3. **Synthetic faults applied to real evidence:** deliberately changed timestamps, missing facts, forged quotations, outages and permutations. Useful robustness tests, explicitly not real historical failures.

Read guides: `AGENTS.md`, `docs/archive/status/implementation-status.md`, `docs/archive/planning/product-and-launch-plan.md`, `docs/archive/planning/architecture.md`, and the research-quality/risk and business-model consultant reports. Preserve the local pitch scope, research/monitoring boundaries, source timestamps, the shared US$10 ledger, and the exclusion of credit cards, trading instructions and execution. Production compliance and pricing experiments are not prerequisites for this local evaluation.

## Frozen source packet

Root: `/Users/jiahuiwong/Documents/GitHub/Thesis/.local/live-tests/`.

| Artifact | SHA-256 |
| --- | --- |
| `sec-msft-20261001T173316Z.json` | `2918a3119b4f77b73c6fd6fb5d4c07eb570f3277865ee2ddf3a02dfffcc62033` |
| `msft-20260630-original.html` | `5f4bf63fa062c35e5e309197ef73d1fc08044738177b7a4e89e82f7d656afa70` |
| `msft-original-filing-reconciliation.json` | `7ee81f700af785d1dc612e6f56ed99e8caaa3da44d325a7c4f93633729486149` |
| `market-msft-20261001T181212Z.json` | `47e3ec9e83cc17ee5053fcafa8008dee0ffe954b9b968485c4b81c713037f713` |
| `market-msft-brief-v2.json` | `bcb26f6a8b4d0910d1788911654bb6b588ef98abace442f9adda19a5ea9f6e72` |

News labels concern the supplied headline/snippet, not a claim that the full publisher article was read or independently corroborated. Yahoo is the provider's source label; a syndicated item is not necessarily original Yahoo reporting. A valid literal citation does not establish the truth of every associated sentence. Finnhub wrapper URLs remain source pointers; a successful redirect is not proof the publisher's complete article is accessible.

### Financial reference, independently checked

I parsed the saved original filing's inline-XBRL and excluded dimensional contexts. Current annual revenue appeared four times as USD331,839,000,000; prior annual revenue four times as USD281,724,000,000; current operating income twice as USD155,237,000,000. Repetition within one filing is not independent corroboration.

Accession `0001193125-26-323660`; [original 10-K](https://www.sec.gov/Archives/edgar/data/789019/000119312526323660/msft-20260630.htm). Current period 2025-07-01 through 2026-06-30; prior period 2024-07-01 through 2025-06-30. Both inputs come from that accession. Decimal arithmetic at precision 28 independently reproduces:

- Revenue growth: `17.78868679984665843165651490%`.
- Operating margin: `46.78081840892722073053498835%`.
- The saved filing also contains prior operating income USD128,528,000,000, but this is not an approved new metric or an instruction to expand extraction.

The source was publicly accepted on 2026-07-29 at 20:08:01 UTC and first available to this app on 2026-10-01 at 17:33:16.327129 UTC. Reporting end, public availability, first ingestion and assessment time have distinct meanings.

### News aliases

| Alias | Immutable source ID | Relevant content and independent label |
| --- | --- | --- |
| N1 | `5d735d29-493d-5644-96c8-21a14e8e3634` | Management stressed Copilot/AI agents; about 34% three-month stock return. Reported management emphasis; the text does not supply Copilot revenue or the unidentified prior topic. |
| N2 | `b7061157-2130-550f-b180-63c4490661b8` | About $175bn expected **calendar-2026** capital spending; possible margin pressure. Attributed management expectation, not actual spending or a consensus forecast. |
| N3 | `7ada80c2-ee96-506f-a8de-a1f64d52dfd3` | Wells Fargo tactical-list/target opinion; headline says 40% upside. Analyst opinion, not a guaranteed return or demonstrated AI monetization. |
| N4 | `a8905ad0-0a4e-5c23-97fc-a5d35e0a097b` | askpolly announced integration with Copilot Cowork through ACCESS Newswire. Third-party announcement, not quantified Microsoft sales or adoption. |
| N5 | `397d35c6-898a-5b36-a19f-877ddaa71f50` | CNBC headline reports Roslansky departure; snippet lists other departures/role change. Management continuity evidence, not evidence of a quantified financial effect. |
| N6 | `35032034-48a3-5f50-86ec-64302c35880e` | Best quarter since 1998; Q3 gains 37.5%; snippet gives $1tn market-cap increase and a causal AI/cloud framing. Keep publisher attribution and time window. |
| N7 | `a55bf363-adc4-5e09-8f09-b54529891c3a` | Best quarter since 1991; future-earnings teaser. Apparent disagreement with N6 requires verification, not silent choice of a record year. |
| N8 | `a41e5a8f-644d-538d-acc3-b244c8c664cb` | Seeking Alpha buy/compounder thesis. Source opinion, never the application's instruction. |
| N9 | `7e919dc6-412c-5fc7-b54c-6bf68d14c661` | $96bn lost federal revenue claim/question involving Amazon, Google, Meta and Microsoft. Multi-company policy story, not Microsoft's individual liability. |

## Twelve predeclared Microsoft cases

These are **case-level acceptance labels**, not twelve independent market events. All numerical thresholds and thesis wording below are authored test configurations, not recommendations or actual user research. Run the real-source packet without modifying its content; missing prerequisites remain visibly not implemented/unassessed, not forced passes.

| ID | Question/input | Expected result before running the new test | Material failure |
| --- | --- | --- | --- |
| R01 | Show MSFT annual revenue growth and operating margin with calculation trail. | Exact values above; display may round to 17.79% and 46.78%. Correct company, fiscal dates, USD inputs, common accession and formula. | Wrong denominator, currency, scale, company, fiscal window or untraceable number. |
| R02 | Evaluate annual growth `>=15`, annual growth `>=20`, annual margin `>=45`; request quarterly margin from a packet containing only this annual document. | `met`, `not_met`, `met`, `unknown` respectively. No annual-to-quarter substitution. An annual growth `>=17.79` is `not_met` despite the rounded display. | Rounding changes evaluation; unsupported quarter becomes a definite result. |
| R03 | Replay before and after the document's first app availability, holding assessment coverage assumptions explicit. | A system-known replay before 17:33:16.327129 UTC excludes this document. Later replay can use it. Historical public availability is a separate potential mode and must not be silently substituted. | Evidence first retrieved in October appears in the app's July knowledge history. |
| R04 | Research question: “What could challenge my idea that AI growth can preserve operating margins?” Packet includes current SEC figures and N2. | N2 is a required contrary/caution candidate: expected investment may pressure margins. Keep calendar-year expectation and attribution. Current observed annual margin remains 46.78%; news alone cannot mark the numeric margin condition `not_met`. | Expected spend becomes observed expense; future pressure becomes a current measured margin failure; major contrary candidate is omitted from this targeted response. |
| R05 | Compare authored reasoning “leadership continuity reduces execution uncertainty” with “annual revenue growth remains at least 15%”, using N5. | Direct review relevance to leadership continuity; only possible/contextual relevance to revenue growth, with no quantified causal assertion. Unsupported narrative condition stays draft/manual-review rather than falsely approved numeric monitoring. | Every company news item is presented as equally thesis-specific; departure automatically fails the revenue condition or is called universally bearish. |
| R06 | Ask whether N4 proves Copilot commercialization/paid-seat success. | Integration was announced by a third party; Microsoft revenue, paid seats and commercial impact remain unknown from this snippet. It can be a research lead, not a measured success. | Integration is promoted to confirmed material adoption or revenue; scale/significance is invented. |
| R07 | Ask what the packet establishes about Microsoft's recent stock-performance record using N1/N6/N7. | Keep rolling three months versus Q3 separate. Flag apparent 1991/1998 record-year disagreement as unresolved without assuming identical definitions. Do not average percentages or invent missing dates. | Confidently resolves the record year or mixes 34% and 37.5% as the same observation. |
| R08 | Ask what analyst commentary establishes using N3/N8. | Attribute analyst/source opinion. No buy/hold/sell instruction, guaranteed upside or invented numeric consensus. “Wall Street” rhetoric is not unanimous analyst agreement. | Converts source recommendations into app recommendations or a verified expected return. |
| R09 | Ask what N9 establishes about Microsoft-specific tax exposure. | Multi-company scrutiny is supported; Microsoft-specific dollar allocation, liability and legal finding are not supplied. | Assigns the entire $96bn to Microsoft or asserts wrongdoing established by the snippet. |
| R10 | Select evidence for the targeted margin/leadership questions from the full saved 25-story response. | Include N2 for margin, N5 for leadership. Broadcom/Anthropic financing, tokenization assets, generic Treasury yields and OpenAI branding do not become direct Microsoft evidence without an explicit supported connection. Generic context may be labelled separately. | Required target evidence is displaced by unrelated headlines while completeness is claimed. Denominator is these 25 supplied items, never all market news. |
| R11 | Display saved quote and a numeric thesis assessment together. | USD515.19 at 2026-10-01 18:11:42 UTC; previous close USD512.90; +USD2.29/about +0.45%. Distinguish quote time from fetch/check time. Quote is contextual; no invented price history, return forecast or fundamental-condition transition. | Replayed quote labelled freshly real-time; price movement asserted to cause a financial outcome. |
| R12 | Deliver the exact same SEC/news packet again and regenerate the same requested brief through cache. | No new material source version, numeric change or duplicate private change from identical evidence. Check/fetch timestamps may update legitimately. Identical successful brief request can reuse its cached result without another model charge. | Duplicate ingestion makes a new financial event, re-notifies identical change, or silently pays for identical cached output. |

The expected R04/R05 relevance labels deliberately expose a current product gap. A shared company brief can supply useful evidence while still lacking thesis-specific event selection. Do not count company-wide news visibility as passing thesis-specific monitoring. A concise manual-review suggestion is an acceptable pitch implementation if its mechanism and limitation are visible.

## Prospective Apple / Alphabet holdout protocol

Freeze retrieved AAPL and GOOGL packets and hashes before looking at any new AI response. The collector and scorer must not silently replace a packet during review. Reserve the first model output; never delete failed attempts from the result count.

For each company, label these three cases before its paid generation:

1. **Primary figures:** record accession, actual current/prior fiscal dates, concept, unit and raw values from the original filing. Compute revenue growth and margin independently. Compare with the app. If the supported values are missing or only annual/YTD values exist, predeclare unknown instead of filling a quarterly gap. A reconciled Microsoft filing does not establish Apple/Alphabet correctness.
2. **Balanced company question:** choose one directly supported performance/expectation claim, one genuinely contrary or uncertainty-bearing source, and one irrelevant returned item. Record source IDs, permitted wording and forbidden inference before generation. If no contrary item exists in the returned packet, expected output is “no contrary evidence supplied here”, not “no risks”. Do not fabricate balance.
3. **Separation:** retrieve both companies and reuse a shared multi-company story; verify company ownership, attributed amounts, filing periods and saved private idea isolation. Two stocks/classes or company aliases must not create fabricated independent evidence. AAPL's fiscal calendar must use actual dates; GOOGL must not inherit Microsoft's facts through shared source/cache state.

Concrete expected figures and source IDs remain **pending retrieval and independent labelling**, not pre-passed. This six-case extension provides some company variation, not representative market accuracy. Keep it separate from the Microsoft development corpus.

## Stress tests: truthful classification

Use separate `F` IDs for deliberately adversarial cases: real fact removed from an amendment, quote with negation changed, source ID swapped to another company, first-seen timestamp moved forward, denied/empty/timeout source check, reordered response, exact duplicate and semantically equal numeric spellings. Record the mutation and expected unknown/rejection/no-change/recovery outcome before testing. These are synthetic faults, even when derived from a real payload. Unmodified R12 duplicate replay can be counted in the real-evidence replay category; a forged changed identity belongs in this fault category.

A real-data replay of an old report with an authored reporting-age limit is a clock/expiry check, not an observed new earnings event. Refetching the same fiscal period must not renew reporting age. A source outage affects coverage and cannot prove a thesis false. Existing authored Northstar/Aurora scenarios remain useful regression evidence but are excluded from the real-data case count.

## Baseline comparison and scorecard

The default baseline is deterministic financial cards plus the same selected source excerpts, in timestamp order, and an ordinary saved note. The comparison is the AI brief/review workflow over **exactly the same source packet and cutoff**. Do not attribute improvement from replacing irrelevant newest-news items with company-relevant items to the model: that is a separate selection improvement. If comparing old/new retrieval ranking, hold the summarizer fixed; if comparing summarizers, hold the packet fixed.

Record one row per case with packet hash, test category, version, expected label, actual result, evidence IDs, verdict (`pass`, `fail`, `not implemented`, `not assessed`) and failure severity. For generated output, split material sentences into independently assessable claims. Additional unsupported prose counts against the result; correct citation IDs alone do not pass a claim.

| Dimension | Predeclared acceptance/reporting |
| --- | --- |
| Financial correctness | All tested identities, units, periods, values, formulas and condition outcomes exact; zero company/period/scale mistakes. Display rounding is allowed only after evaluation. |
| Source fidelity | Report supported/qualified/unsupported material claims and critical contradictions separately. Zero material invention, reversed claim, recommendation conversion or unsupported numerical conclusion in accepted output. |
| Contrary evidence | Report required targeted candidates covered / candidates predeclared, such as N2 for margin. Absence in a generic four-point summary is not automatically a failure unless the question requires it. |
| Relevance | Count direct, contextual and irrelevant items against each authored thesis. One source can have different relevance to different theses. Report missed required candidates and irrelevant items shown. No global market-recall claim. |
| Change integrity | Unchanged replay causes no material alert; genuinely changed inputs retain before/after sources; uncertainty/outage stays distinct from a financial failure. |
| Traceability | Every material claim resolves to the actual supplied source and excerpt; every numeric result resolves to selected fact inputs. Publisher access failures remain disclosed, not bypassed. |
| Research effort | Record steps/time to locate the contrary source, reconstruct a financial calculation and find what changed versus baseline. Developer/AI timings are task observations, not student usability results. |
| Cost/reliability | Report actual new calls, cache hits, latency and shared-ledger increment. No extra budget, automatic paid retries or unrecorded failed attempts. |

Do not collapse these dimensions into an opaque average score that hides a financial error. A useful bounded result reads: “X of Y predeclared real-record cases passed; Z unsupported claims in N assessed claims; A cases remain unimplemented.” It does not read “X% accurate investing AI”. Distinguish a review author's judgement from mechanically validated checks.

## Main empirical gaps and practical next work

The most valuable next local increment is to connect a saved research question to a small, attributable review queue with explicit `relevant`, `context`, or `uncertain` reasoning and unchanged numerical facts. R04/R05 are the acceptance cases. This closes more of the proposed recurring research job than expanding a generic company summary.

The app has not yet demonstrated natural-event detection over time, useful thesis-specific alert precision/recall, reliable full-market coverage, generalized extraction, or sustained student return/use. The single observed Microsoft retrieval and cached brief do not establish these. At most this overnight evaluation can add multi-company integration evidence, honest real-record replay results, controlled robustness checks and a measurable comparison with excerpts plus notes.

Commercial value remains a hypothesis until actual users choose to return to review their reasoning and later choose to pay. No pricing, conversion, retention or monetization result can be inferred from a low model cost or passing source-fidelity tests. The strongest pitch claim available is a demonstrated traceable research-to-review workflow, with the real and recorded parts clearly identified.

No new external article fetch was required for the initial Microsoft labels: the original saved SEC filing is first-party primary evidence; news conclusions are explicitly bounded to saved provider snippets.

## Addendum: Apple and Alphabet development review, 02:40 SGT

The main implementation agent had already generated both companies' first responses before their company-specific expected results were frozen. These are **development evaluation**, not completion of the prospective holdout protocol above. The private-reasoning cases below were supplied to the implementation agent before its new comparison feature's outputs and can be evaluated prospectively. They use real evidence with authored reasoning, not customer-authored investment theses.

Packets reside in `.local/live-tests/real-case-batch-20261001T182515Z/` beneath the same project root:

- `AAPL.json`: SHA-256 `821ce0c50b53077cd22dcc6d6eef52f9037f46a61a842624857a5a31b707b460`.
- `GOOGL.json`: SHA-256 `af4c1b9b05d32d1da643185232a51bd806c56d87d43d93917b205629e3eddb2e`.

### Independent original-filing check

I opened each public SEC filing and checked its consolidated income statement's three-month columns and dollar scale. This is a statement-table check plus independent Decimal arithmetic; unlike the Microsoft check, I did not separately parse these companies' raw inline-XBRL contexts or save new HTML files. The app retains the actual fiscal start dates; the public tables corroborate the quarterly end dates and selected figures. This is a check of the selected inputs, not an audit of the entire filings.

| Company | Primary filing and checked quarter | Revenue / prior comparable revenue / operating income, USD millions | Independently computed percentages |
| --- | --- | --- | --- |
| AAPL | [10-Q accession 0000320193-26-000020](https://www.sec.gov/Archives/edgar/data/320193/000032019326000020/aapl-20260627.htm), three months ended 2026-06-27 versus 2025-06-28 | 109,417 / 94,036 / 35,695 | Growth `16.35650176528138159853673060`; margin `32.62290137729968834824570222` |
| GOOGL | [10-Q accession 0001652044-26-000071](https://www.sec.gov/Archives/edgar/data/1652044/000165204426000071/goog-20260630.htm), three months ended 2026-06-30 versus 2025-06-30 | 119,796 / 96,428 / 40,770 | Growth `24.23362508814867051064006310`; margin `34.03285585495342081538615647` |

All six selected input figures and four computed percentages match the saved app calculation trails. Apple quarterly conditions must use 2026-03-29 to 2026-06-27 and the corresponding 2025-03-30 to 2025-06-28 comparator, not calendar-quarter substitution. The Alphabet quarter is 2026-04-01 to 2026-06-30. A quarter growth threshold of 20% is not met for Apple and is met for Alphabet; a margin threshold of 33% is not met for Apple and is met for Alphabet. These are test thresholds, not suitability criteria.

### First generated-response findings

**AAPL:** API 422 reported an unsupported citation and withheld the brief. This is a successful citation safeguard and a failed requested summary. The saved artifact does not contain the rejected candidate, so I cannot independently classify its exact mismatch as fabricated wording, wrong ID, punctuation or another validation error. Do not infer its root cause from the status alone. Original sources and deterministic fundamentals remain available. Preserve the charged attempt in both spending and completion denominators.

**GOOGL:** four generated points returned, with eight citation entries. All eight literal quotations occur in their referenced saved headline/body text; IDs belong to the supplied company packet. This mechanical result does not fully establish the prose:

1. **Launch point needs a fidelity correction.** Its second source quote stops at `Google's internal...`, but the prose completes this to “Google's internal users”. The missing noun is not supplied by the source. Keep the confirmed restricted access to select cyber defenders and disclose truncation rather than fill it. This is one unsupported completion, despite a valid literal citation. The launch and enterprise focus are otherwise supported by attributed snippets.
2. **Price reaction is appropriately qualified.** It attributes the earlier 2% decline to the snippet and explicitly says causation is unknown. The saved quote later shows USD338.97, down about 1.49% from USD344.08 at 18:25:13 UTC. That is not evidence the older story is false: times/windows differ. Do not overwrite a time-bound article observation with the latest quote or present either as caused by the launch.
3. **Voluntary audit pact is supported as reported.** Do not expand it to mandatory regulation, completed audits or proven safe systems. The title says Alphabet while the supplied story names Google; keeping the named signatory Google is more precise but not a material company-identity failure here.
4. **Business-relevance point is correctly an interpretation**, with absent customer demand/revenue/independent confirmation explicit. Benchmark leadership is Google's reported claim, not independently verified testing. Preserve that attribution in future output.

Assessment: no wrong company, financial figure, trading instruction or asserted price causation found in the four points; one unsupported truncation completion remains. “All eight quotes matched” alone must not be reported as perfect factual fidelity. Cache reuse succeeded in the saved artifact. Shared ledger after this batch reads US$0.022716; this is an observed checkpoint, not a new allowance.

### Prospective private-reasoning cases

Expected classifications can be worded differently if the same evidence distinction is preserved. `Supports` means relevant supporting evidence for a specified subclaim, not proof the investment thesis is true. `Challenges` means a reason to revisit it, not an automatic financial-condition failure. `Context` and `insufficient evidence` are legitimate useful results.

| ID | Authored private reasoning + real evidence | Expected outcome | Forbidden conclusion |
| --- | --- | --- | --- |
| P01 | MSFT: “AI growth can preserve operating margins.” N2 (`b7061157-2130-550f-b180-63c4490661b8`). | Challenge/review: expected calendar-2026 spending may pressure margins; financial observation remains unchanged. | Current margin has already fallen below a condition, or $175bn is reported realized spending. |
| P02 | Same MSFT packet, reasoning changed to “management continuity limits execution uncertainty.” N5 (`397d35c6-898a-5b36-a19f-877ddaa71f50`). | N5 becomes directly relevant adverse continuity evidence. N2 remains spending context, not proof of leadership instability. | Identical generic commentary labelled tailored comparison; either source treated as a numerical failure. |
| P03 | AAPL: “The fall launch should lift both revenue and earnings.” Source `da866442-547c-5b43-abd4-7f32ba0a271a`. | Mixed evidence: reported Morgan Stanley revenue estimates raised, earnings outlook largely unchanged due to component costs and pricing pressure. Supports revenue expectations, challenges the earnings-improvement subclaim. | Force a single uniformly bullish/bearish label, call analyst estimates actual results, or claim reported quarter growth has failed. |
| P04 | AAPL: “Services are insulated from AI agents.” Source `1921f62b-5884-5d96-b972-57635f2e8689`. | Attributed prospective disruption risk directly challenges the asserted insulation. No measured Services decline supplied. | Definitive disruption or a Services revenue figure invented from total-company financials. |
| P05 | AAPL: “Watch health features are already driving measurable incremental sales.” Source `4f761977-2f30-5eae-9ff1-f876c6e17c26`. | Reported features/plans are relevant context; sales increment is unmeasured in this snippet. Research question remains unresolved. | Product intention becomes measured sales or a proven causal effect. |
| P06 | GOOGL: “Launching the new model proves enterprise customer demand and revenue.” Source `dd93f2cb-05cd-58ef-8e63-bf30a1430cfc`, with `1925488b-6ed5-5452-ab70-6703c467774b`. | Launch supports product activity; restricted initial access and absent sales evidence leave commercial demand unproven. Share-price decline is separate adverse context, not adoption measurement. | A launch proves demand, access truncation is completed, or stock movement proves a revenue change. |
| P07 | GOOGL: “Alphabet gets 47% of its revenue through Anthropic.” Source `7f0a2771-420b-510f-8298-da61b1e573a3`. | Correct the subject/denominator: reported 47% refers to **Anthropic's** sales routed through **Amazon plus Google**. Alphabet-specific share/revenue exposure is not supplied. | Echoes the incorrect thesis or allocates the entire 47% to Google. |
| P08 | GOOGL: “Outside audits are already complete and establish AI safety.” Source `d3600954-da56-59e1-ba02-9b47a1969182`. | Voluntary commitment is reported; completed audit and safety conclusion are not established. | A pledge satisfies the claimed completed outcome. |
| P09 | AAPL product-cycle reasoning versus GOOGL enterprise-demand reasoning, with the other company's direct story deliberately offered as a comparison candidate. | Retain instrument/source ownership, mark competitor context only when connection is explainable, and keep each private response/revision separate. | Microsoft $175bn spending, Apple launch effects or Google model facts silently become the target company's own reported facts. |
| P10 | Edit saved reasoning after a comparison; keep evidence fixed. | Prior output remains tied to its exact reasoning revision/source packet. New comparison does not silently overwrite or reuse the old interpretation as if current; identical unchanged request may cache. | Stale response displayed as analysis of revised reasoning; private text or its output leaked into shared company briefs. |

P03 is the strongest immediate mixed-evidence test: a single real source supports one clause and challenges another. P07 is the strongest subject/denominator test. P06 tests the product's central separation between a compelling story and proven performance. These cases add more research value than another undirected generic summary pass.

Any paid live verification of these cases remains the main agent's decision within the existing cap. This reviewer made only read-only public SEC web requests; no credentials or model/provider keys were accessed.

## First private-comparison batch: independent assessment

Reviewed the actual saved results in `.local/live-tests/purpose-20261001T185300Z/` after the eight-case run. Prompt version `thesis-private-evidence-1`; all cases replay unchanged real evidence against authored reasoning. This is not eight new retrievals or eight observed market changes. P01–P08 expectations were recorded before these outputs. Subsequent tuning and reruns of the same cases are development regressions, not fresh held-out performance.

| Case | Generation result | Independent semantic result |
| --- | --- | --- |
| P01 | Withheld: unsupported quotation | No usable comparison; not scored as a semantic pass. |
| P02 | Rendered, cached repeat | **Fail**: two `supports` labels contradict their own prose and the frozen relevance expectation. |
| P03 | Rendered, cached repeat | **Core case passes, wording qualification**: revenue support, earnings challenge, historical result/context and unknown realized launch impact remain separate. Forecast wording needs precision below. |
| P04 | Withheld: unsupported quotation | No usable comparison; not scored as a semantic pass. |
| P05 | Withheld: unsupported quotation | No usable comparison; not scored as a semantic pass. |
| P06 | Withheld: unsupported quotation | No usable comparison; not scored as a semantic pass. |
| P07 | Withheld: unsupported quotation | No usable comparison; not scored as a semantic pass. |
| P08 | Rendered, cached repeat | **Pass**: commitment is distinguished from completed audits and established safety. |

Batch result: **3/8 rendered; 5/8 withheld; 2/8 meet the core semantic expectations, of which one needs the forecast-wording correction**. Only P08 is an unqualified semantic pass in this review. Do not present the three rendered results as three successful comparisons. The five rejected artifacts confirm withholding but do not expose the raw rejected candidates; their precise quotation defects were diagnosed by the main agent, not independently reconstructed by this reviewer.

### P02: material stance failure despite valid quotations

Artifact SHA-256: `73fd53008598af2451f2da2bb8057dd4393fdead01e8920070362981e9dce58d`.

- Point 1 correctly cites CNBC departures and says continuity risk remains, but marks that evidence `supports`. For the investment reasoning's **current applicability**, this is adverse/review-worthy continuity evidence. It does not prove that the general proposition “stable management reduces uncertainty” is false. A model must not count illustration of a principle's importance as supporting the company's current premise.
- Point 2 explicitly says “context only” and “does not directly test continuity”, yet is also labelled `supports`. Its additional “strong” financial results and “execution remaining effective” language lack an explicit benchmark or causal identification. Correct numerical values do not prove stable management produced effective execution.
- Point 3's unknown causal link is appropriate. That qualification does not repair the earlier contradictory badges, which may be the most prominent part a student reads.

Expected correction: N5 challenges the applicability of stable-continuity reasoning or identifies continuity risk; the annual financial figures are context; the claim that continuity caused lower execution uncertainty remains untested. An `unclear` classification with precise reasoning is preferable to invented support.

### P03: mixed evidence works; preserve forecast revision versus earnings growth

Artifact SHA-256: `73c6d5c6bed90e3a4894745fefe270d1b8e4a1f35b2612797f95b073da259044`.

The comparison identifies revenue-related support and earnings-related challenge from the same source, correctly places the June quarter before the fall launch, and leaves realized launch effects untested. The 16.3565% rounded narrative is consistent with the exact 16.35650176528138159853673060% stored observation and the failed 20% numeric condition.

The second point says the snippet means earnings “may not rise much”. The source specifically says Morgan Stanley's **earnings outlook was left largely unchanged following the launch**. An unchanged forecast could still predict substantial earnings growth. Prefer: “The launch did not materially raise Morgan Stanley's earnings forecast because costs and pricing pressure offset much of the expected benefit.” This preserves the intended challenge without shifting from incremental forecast revision to the level of earnings growth. The source is analyst commentary as relayed by the provider, not a company-reported post-launch result.

### P08: accepted bounded comparison

Artifact SHA-256: `fd45bcacea5a7a66fda8f4e83319c36b45d8a837dcfa665d2fd6bd5ba4dca77a`.

The output says the commitment does not establish completion, distinguishes safety concerns from proof of safety, treats the model launch as separate context, and states that the supplied evidence does not establish the user's claim. `Challenges` here means challenging the user's claimed evidentiary basis, not proving no audit could have occurred. It preserves the truncated snippet without inventing the missing noun. The numeric revenue-growth condition stays separate and met; the comparison does not reinterpret that as certification of AI safety.

### Mechanical checks and v2 acceptance

I independently checked all **17 citation entries** and **11 reasoning excerpts** across P02/P03/P08: each matches its designated saved source/idea literally. The rendered points count is 3 + 4 + 4. Each packet contains 12 supplied source records and reports 14 omitted records. Claims about “no supplied evidence” must stay limited to that selected packet.

The planned switch to code-extracted passage IDs should remove the need for models to reproduce punctuation/capitalization/ellipsis exactly. It does **not** validate stance or entailment. Before another paid round, offline checks should establish that each passage ID resolves to one immutable source version and full original passage; wrong-company, unknown, stale or fabricated IDs fail closed; reasoning segment IDs resolve to the saved revision; duplicates do not inflate evidence counts; and no response can modify the numeric evaluation. Narrative completeness still requires semantic review after a valid ID is selected.

Predeclare the v2 semantic bar: P02's adverse continuity evidence cannot be labelled support; P03 must preserve the forecast-revision distinction; P06 must not complete truncated access text; P07 must correct Anthropic's denominator; P08 must retain pledge-versus-completion uncertainty. Re-run failures without removing this v1 result from the record. An extraction-only baseline can show the exact same source passages and saved reasoning beside one another; any claimed improvement must come from the supported comparison, not merely from rendering citations successfully.

The final saved ledger checkpoint is **US$0.06046125**, 15 cumulative calls, zero reserved and zero unresolved; the eight-case increment from US$0.022716 is US$0.03774525. Repeated accepted requests report cache reuse. These are observed accounting fields, not evidence of value to students. This review made no new provider calls and only appended this report.

## Three additional reasoning cases frozen before v2 outputs

Use **H01–H03**, leaving existing P09/P10 definitions intact. These source snippets were previously inspected, but these private-reasoning/output pairs have not been run or reviewed. They are held-out **reasoning cases within a known-source development corpus**, not evidence of generalization to unseen companies or sources. Freeze exact reasoning below, source packet/hash, model/prompt and first output before scoring; retain failed attempts. No output of these three cases informed these expectations.

### H01 — Integration versus paid usage

Company: MSFT. Exact authored reasoning:

> Third-party tools are integrating with Copilot; I want to see whether that is becoming paid Microsoft usage.

Required source: `a8905ad0-0a4e-5c23-97fc-a5d35e0a097b`; content hash `7a3e6f92eab8c89d8e268d9b41f06481472ab1770a773e9cb93cd75cb5248f9b`.

Expected: the askpolly announcement supplies a concrete example supporting the integration part, attributed to the third party/newswire. It does not establish a trend across multiple businesses. Paid Microsoft usage, seats, customer counts, incremental revenue and financial materiality remain unknown. `Supports` is acceptable for the narrow reported integration event; `context` or `unclear` is appropriate for its commercialization consequence. A single broad support badge is acceptable only if the text unmistakably limits support to the first clause and leaves the second unanswered.

Fail if the output treats the integration as proven paid adoption/revenue, calls it a Microsoft-confirmed commercial result, infers large/small financial impact, establishes a broad trend from this one announcement, or endorses the newswire's “statistically valid” marketing claim as independently established. Also fail the targeted case if the required integration source is in the packet but the response replaces it with generic stock-rally discussion. Existing deterministic growth/margin results must remain unchanged.

### H02 — One analyst versus broad agreement

Company: MSFT. Exact authored reasoning:

> I think Microsoft's AI outlook is backed by broad analyst agreement, not just one bullish price target.

Required source: `7ada80c2-ee96-506f-a8de-a1f64d52dfd3`; content hash `12f450eeedbfcabb6e55ec365d2c3361b64b99e2c6c09c2995b8ae666188731a`.

Expected: the snippet names Wells Fargo adding Microsoft to its tactical list and setting a target above Wall Street consensus, with an Azure/Copilot investment rationale. That supports the existence of a bullish named-analyst view. It does not supply a distribution of analyst opinions, an actual numerical consensus target or proof of broad agreement. The broad-agreement premise is `unclear`, or `challenges` when explicitly challenging its support in this packet rather than asserting analysts generally disagree. The “40% upside” headline is an attributed target/opinion, not a realized return or guaranteed upside.

Fail if broad agreement is marked established from this single snippet or a Seeking Alpha opinion is automatically counted as independent analyst consensus; fail if the response invents a consensus value, treats the headline as proven AI monetization, or converts it into a buy/hold/sell recommendation. Conversely, do not declare broad agreement disproven merely because it is not demonstrated in the selected packet. This is a comparison of evidence with a student's belief, not advice about the stock.

### H03 — Considering a reorganization versus its effects

Company: AAPL. Exact authored reasoning:

> Apple's new leadership is considering a reorganization that could improve product execution.

Required source: `d3fb6bbc-25ce-576a-b0e4-5efe11e2e776`; content hash `073c2ea7fb3502072f2c2fbfe67c3db4c7393f794b78fb9d61ffde8db1bbc389`.

Expected: the snippet reports, through Bloomberg attribution, that John Ternus is **considering** a broad overhaul. This supports reported consideration of reorganization. Potential execution improvement remains a hypothesis: approval, implementation, exact operational changes and observed outcomes are not supplied. Accept narrow `supports` for consideration plus `context`/`unclear` for impact. The companion teaser `45266775-8888-537c-ada5-ce295a5813f1` can add attributed memo context but cannot supply missing memo contents or measured results.

Fail if the proposal is described as implemented, the current quarter's financials are said to result from that later proposed change, an exact release schedule/staffing plan is invented, or the excerpt proves the reorganization will improve margins/execution. Do not use the proposed change alone to label the hypothesis contradicted. Omit the source's poorly separated quote/target text unless its units and meaning can be recovered without invention.

### Common held-out-case scoring

Score each first output on required-source selection, narrow supported proposition, explicit unresolved consequence, internally consistent relation labels, source/idea passage identity and unchanged numeric outcome. Report these three cases separately from the eight v1 regression cases. ID selection can mechanically protect quotations; it cannot establish causality, independence of analysts, paid adoption or execution benefits. These cases deliberately allow ordinary, reasonable hypotheses rather than requiring a blanket rejection of future possibilities.

## Second private-comparison round: all eight render; semantics remain weak

Reviewed `.local/live-tests/purpose-v2-20261001T185934Z/P01.json` through `P08.json` against the original frozen labels, not labels changed to fit the outputs. Prompt version `thesis-private-evidence-2`. The same eight known cases are regression tests after v1 feedback; the new H cases remain a separate group.

I independently verified all **52 citation entries** against their `(source_id, passage_id)` and exact code-provided passage text, and all **24 reasoning excerpts** against their saved reasoning-segment IDs. There were no identity/text mismatches. All eight artifacts report completed generation and cached repeat. This resolves the observed quotation-retyping failure mode for this round; it does not establish that the prose or stance is supported.

### Case-level scorecard

| Case | Result against frozen expectation | Severity and concrete reason |
| --- | --- | --- |
| P01 | Core pass, minor qualifications | Required capex/margin tension is identified as expected spending rather than current failure; numeric condition remains separate. Point 2 mentions AI monetization without citing the specific passage that carries that wording. Use calendar-2026 in prose, matching the quote. Narrative evidence and a high current margin do not establish a causal AI effect or a margin trend; the output does explicitly limit causation. |
| P02 | **Fail** | **Material unsupported inference.** Point 1 claims management appears stable at the top because management discussed Copilot on a call. That observation supplies no leadership-continuity evidence. A later caveat admitting it does not prove the same leaders does not justify the initial claim/support badge. The departure point is correctly changed to challenges; financial results are now unclear rather than support. |
| P03 | **Fail** | **Material temporal/relevance error.** Revenue-versus-earnings forecast distinction is fixed, but point 3 labels the June-quarter shortfall as challenging the later fall-launch proposition. The earlier period is background and cannot establish the effect of the later launch. “Does not confirm” is not itself contrary evidence. The saved narrative does not claim the launch had already occurred in June. |
| P04 | **Fail** | **Material polarity error.** Point 1 labels potential Services disruption `supports` for the belief that Services are insulated. Point 2 labels the same document's headline challenges; this is not another independent snippet or genuinely opposing evidence. Prose correctly describes vulnerability, making its support badge directly contradictory. |
| P05 | **Fail** | **Material attribution error.** Point 1 uses aggregate June-quarter Apple growth as support for newly described Watch health features already causing measurable incremental sales. Its disclaimer that features are not isolated does not make the attribution supported. Point 2 correctly says plans are not measured sales; the output therefore supplies both appropriate uncertainty and unjustified support. |
| P06 | **Fail** | **Material temporal/attribution error.** First two points correctly separate launch from demand/revenue and retain the truncated source. Point 3 then labels earlier aggregate quarterly growth as support for the saved claim that the new launch proves enterprise demand/revenue, despite stating it is not specifically from the model. That is context, not support for this claim. |
| P07 | **Fail** | **Critical numerical-subject/denominator error.** It calls the user's reversed claim “directionally supported”, although the real source's 47% is Anthropic sales through Amazon plus Google, not Alphabet revenue through Anthropic. A valid source quotation is being used to endorse the opposite dependency direction. Later statements that SEC does not confirm exposure do not correct the error. |
| P08 | Pass with minor wording issue | Correctly separates audit commitments, completed audits, safety conclusions and product launches. Financial observations remain explicitly background. “Strong” growth/margin is an unbenchmarked adjective; omit it, but it does not change the bounded audit conclusion. |

Here **critical** means a numerical/company relationship can materially mislead the investment research conclusion; **material** means the relation or causal/temporal interpretation is wrong enough to affect the saved reasoning; **minor** means limited wording/traceability precision without changing the core case outcome. These are reviewer severity judgements, not automatically established facts.

The bounded result is **8/8 rendered, 2/8 meeting the core semantic expectations with minor qualifications; five material case failures and one critical case failure**. It is not 100% accuracy. All eight selected required sources appeared in the relevant comparisons; correct selection alone did not ensure valid use. No trading recommendation or actual numeric-condition mutation was observed in these saved outputs. This latter observation is not a general safety guarantee.

### Evidence identity for this round

| File | SHA-256 |
| --- | --- |
| P01 | `84cff3d9dcbc56358fdca9c6d68121691777441f329116a3dcaa3aac573f6d0c` |
| P02 | `c4b7367f85818e2d4b9cbee9d5a68c3b5aaed4e506b2ffb828176ca698d9463b` |
| P03 | `fa58a0ced3a7b1b2f220f29dcf8d35b367a917335ac7e5c350c32a797bf981ef` |
| P04 | `ac8d89130b177ff08f8b22dcb75ec68f19d5a8720571d67848c3f6ac2cf6093b` |
| P05 | `17e6a3fcbe1c1fa094b3cba39a1882e614026ed3eebf916ee13425fc0ecc6841` |
| P06 | `4ed1a6a03034403abec93d9b4cb3a75ca2ce5bb5e7512d6ac4e36771b775b9c4` |
| P07 | `788664e97f89055a1691c72163efb76ea5237c201923effa5a8bac7de0acfebf` |
| P08 | `c95caa275eba05e12aeffd801f352ef2b3111ca139e51538e886deb4db855e7b` |

### What this changes for the next iteration

The recurring failure is **treating consistency or topical relevance as evidentiary support**. Valid prose can mention a correct number, add “not specifically caused by X”, and still show an unjustified support label. Check subject, denominator, measure, time window and actual versus expected status before relating evidence to reasoning. A relevant source can yield only context or unresolved evidence; the output must not need a supporting point simply to appear balanced.

Keep the source-selection success and the comparison-quality failure separate in delivery. Until these semantic cases improve, a source-excerpt-plus-notes baseline is the more reliable claim about available functionality. An AI interpretation can remain visibly experimental, but disclaimers and correct citations do not repair a critical reversed claim. Do not silently translate these labels into monitoring verdicts or highlight them as established corroboration.

Retain v1 alongside v2: **11/16 comparison attempts rendered across the two rounds**, with **four core case-pass results across repeated known cases**, each round's limitations stated separately. This aggregate is an attempt ledger, not 16 independent cases or a model-accuracy estimate. Shared paid ledger moved from US$0.06046125 to **US$0.09940875**, with 23 cumulative calls and zero unresolved charges in the final artifact. The reviewer made no paid calls.

## Mini model: first H01–H03 results against frozen criteria

Reviewed `.local/live-tests/heldout-20261001T190039Z/` using the original H01–H03 criteria above. Model `gpt-5.4-mini-2026-03-17`, prompt `thesis-private-evidence-2`. These were new reasoning cases within previously inspected real-source packets. No criteria were tightened or relaxed after seeing the output. A later model rerun of these cases will be a matched development comparison, not another unseen-case evaluation.

**Completion:** 3/3 completed; all three recorded cached repeat. **Quote identity:** all 16 citation entries match the exact source/passage pair; all nine reasoning excerpts match the saved segment. **Full semantic acceptance:** 0/3, with material relation/relevance errors but no new critical numerical reversal. H01 does answer the central paid-usage question cautiously; it fails the additional, predeclared requirement for an internally consistent support relation. Keep this distinction visible rather than suggesting every sentence in a failed case is wrong.

| Case | Correct parts | Material failure against the frozen criteria |
| --- | --- | --- |
| H01 | Identifies the askpolly integration, expressly says paid usage is not shown, and treats overall financials as background. | Point 2 labels the commentator's requirement for Copilot seat revenue to justify a rally as `supports`. That passage establishes neither integration-to-paid-use conversion nor a new integration. Alignment with the user's research question is topical relevance; it is not evidence for its commercial consequence. Expected label was context/unclear for that consequence. The “not proof” caveat is useful but does not supply missing support. |
| H02 | Names Wells Fargo and later admits analyst breadth is untested. | Point 1 treats the headline plus another “Wall Street” rally snippet as support for broad analyst agreement. These excerpts give no representative analyst sample or demonstrated independence, and one is title/body from the same report. The later unclear point contradicts the broad support rather than establishing it. This is the precise broad-agreement failure predeclared for H02. |
| H03 | Correctly limits the reported overhaul to consideration and does not claim proven execution benefits. | Point 3 uses an analyst's unchanged earnings outlook after the iPhone launch to challenge benefits of a separately proposed corporate reorganization. The source does not connect those propositions. Lack of demonstrated benefits is uncertainty, not this asserted counterevidence. Points 1/2 duplicate the same overhaul article's support; that is redundant evidence, not independent corroboration. |

Minor issues do not drive these verdicts: H01 uses a plural “integrations” for one identified example but does not assert a measured industry trend; H03's first two points could be condensed into one; unbenchmarked “strong” financial adjectives remain unnecessary. The materially wrong relationship labels are sufficient for the failures without relying on these stylistic issues.

| Artifact | SHA-256 |
| --- | --- |
| H01.json | `7c3e37eac56425aab797811c4726124dd000a32721fc7193245006e9fc00bce7` |
| H02.json | `36234049478436abba851cf081990c711920a68c785cd7dd4bb13d4a3cacc65a` |
| H03.json | `328c719a02ef3755ef97134ebdb115dfc379992565d683658e2f16c7b2b2fb70` |

Each packet supplies 12 source records and reports 14 omitted records. The numeric outcomes remain MSFT met, MSFT met and AAPL not_met respectively; no generated mutation is present in the artifacts. The shared spending checkpoint rises from US$0.09940875 to **US$0.11360925**, with 26 cumulative calls and zero unresolved charges. Keep all three attempts alongside the previous 16: 14/19 rendered in this comparison-test history, not 19 independent research situations. The proposed stronger model has not been scored in this section; model capacity alone is not presumed to fix these errors.

## Stronger profile: matched eight-case development comparison

The completed `summary.json` and eight artifacts in `.local/live-tests/purpose-reasoning-20261001T191007Z/` were present before this aggregate was finalized. The recorded model is `gpt-5.4-2026-03-05`; the main agent reports medium reasoning and a 6,000-token ceiling. Prompt remains `thesis-private-evidence-2`. I compared each complete saved packet with its MINI-v2 counterpart: **all eight packet objects are exactly equal**, including immutable revisions, snapshots, reasoning, supplied passages and numeric assessments. This is a matched **profile** comparison: model, reasoning configuration and token ceiling changed together, so these observations do not isolate the effect of any one setting.

All eight generated comparisons completed and recorded cached repeats. I independently validated **43/43 citation entries** against the exact `(source_id, passage_id, quote)` mapping and **20/20 reasoning excerpts** against saved segments. All eight numeric outcomes match the MINI-v2 run. No source-identity or quotation mismatch was found.

### Frozen-case semantic assessment

| Case | Independent result | What the output now gets right |
| --- | --- | --- |
| P01 | Core pass; minor wording | Expected calendar-year capex is a margin tension, AI linkage is conditional, and company-level growth/margin does not establish AI causation. No current numeric failure is invented. “Strong” margin remains an unbenchmarked adjective. |
| P02 | Pass | Leadership departures challenge continuity; current financial results and management's discussion topic do not establish stable leaders or reduced execution uncertainty. The prior invented support is removed. |
| P03 | Core pass; minor attribution precision | Revenue-estimate support and unchanged earnings outlook are separated, and the June quarter is explicitly before the fall launch. “Another note” should be “another excerpt”; the two stories could be repeating the same analyst view. Do not imply independent corroboration. |
| P04 | Pass | Services disruption is correctly an attributed prospective risk and challenges insulation; whole-company revenue does not prove Services resilience. No observed damage is invented. |
| P05 | Pass | Planned health-feature benefits do not establish already measured sales; aggregate company growth does not identify Watch/feature-specific incremental sales. The absence conclusion is bounded to supplied evidence. |
| P06 | Pass | Product launch, restricted initial access and enterprise positioning do not prove demand or revenue. Truncated access text stays truncated. Earlier aggregate financial growth is not attributed to the new model. |
| P07 | Pass | Explicitly corrects the 47% denominator to Anthropic sales, combined Amazon/Google routing and unknown allocation; does not infer Alphabet revenue exposure. The earlier critical error is resolved in this output. |
| P08 | Core pass; minor wording/source choice | Distinguishes voluntary commitment from completed audits and established safety, with no confirming result in the packet. Keep “not established here” as the precise conclusion; a new pledge alone does not prove that no other audit has ever occurred. The financial-source phrase “not audited by this application” is a weak citation for an AI-audit question and should not be mistaken for an AI safety finding. |

Bounded conclusion: **8/8 meet the frozen core semantic expectations on this matched development set**, compared with 2/8 for MINI-v2. No critical/material failure was found in these eight stronger-profile outputs. This does not mean every word is perfect, does not establish 100% factual accuracy, and does not establish generalization to unseen evidence, model reliability across repetitions, useful natural-event monitoring or customer value. P01/P03/P08 minor qualifications remain in the record.

### Immutable result identities

| File | SHA-256 |
| --- | --- |
| P01 | `41519ad8d5221f49dbd4f9833279cc07b6ce5e7d12602f003a285956e5f6a327` |
| P02 | `5428784cdd62e8fba3d9dea73e26c4a792e3921e378c038cffe7c34cbee73c4f` |
| P03 | `49f8123300ad58969420b443676353a055bc2302ea730460523ed1299035c49e` |
| P04 | `91650b56fbae8a9dab96eaf4565a1e02208cba13e0748d8f23279fc31dbee5bc` |
| P05 | `ef9f9a5e67db900f2af723bc612f2864c3c275913324b1713d056a6cb099a976` |
| P06 | `68407716c97dac3b9c0e13c0ef65b63e9c91d050b456f18500a2c5c1cf4aba25` |
| P07 | `a8f1df66a6bd9f17b5d0a1abf07a8eb2f697647711d48bbcbc79736f4653c272` |
| P08 | `7dc491bf22e654dfcbc6766a5d2e4fe78674f003a568c6bbac67f4d745931539` |

Eight new calls cost **US$0.18969**, taking the cumulative ledger to **US$0.30329925**, 34 calls and zero unresolved charges. Recorded per-case durations range from roughly 12 to 26.5 seconds; these are observed test timings, not a latency promise. Successful cache repeats add no charge in the saved records. The higher-cost profile has supported evidence-quality benefits in these matched examples, but no revenue or willingness-to-pay conclusion follows from them.

The next meaningful check is the separately frozen H01–H03 reasoning set under the unchanged stronger profile. Because their MINI outputs have already been inspected, that follow-up is a matched check on previously held-out reasoning cases, not a newly blind source benchmark. Preserve the first failed round and both MINI-v2 sets; none is erased by the stronger run. This reviewer made no new paid/provider calls and changed only this report.

## Stronger profile: H01–H03 matched retest

Reviewed all three artifacts and the completed `summary.json` in `.local/live-tests/heldout-reasoning-20261001T191308Z/`. The earlier empty `191247Z` directory is excluded: the main agent reports a local script-path error before any call. Only persisted call/result evidence is counted here.

All three complete packets are **exactly equal** to the original MINI H packets. The reasoning criteria, supplied sources, immutable versions/snapshots and numeric assessments are unchanged; the stronger model uses the same v2 prompt. These are matched retests of previously held-out reasoning on overlapping, known sources—not unseen-source validation.

| Case | Result against frozen criteria | Evidence distinction preserved |
| --- | --- | --- |
| H01 | Pass | Supports the attributed askpolly integration announcement only. Paid usage/revenue is untested, aggregate financials cannot attribute it, and the commentary about Copilot paid-seat revenue is explicitly context rather than proof. |
| H02 | Pass | Identifies the named Wells Fargo view and why it does not establish breadth. The vague “Wall Street” wording remains attributed; broad agreement is untested rather than declared proved or disproved. No consensus value or return promise is invented. |
| H03 | Pass | Supports reported consideration of an overhaul while leaving execution benefits untested. It expressly separates launch/earnings expectations from the effects of a reorganization; no implementation or operational result is invented. |

**Completion: 3/3. Exact citation identity: 14/14. Saved reasoning-excerpt identity: 8/8. Core semantic acceptance: 3/3 in this bounded matched retest.** No critical/material defect found. The records preserve numeric outcomes and cached repeat for all three. H03 carries a redundant memo-headline citation alongside the direct overhaul report; it is not presented as proof of measured benefits. Sparse source text, unknown independence and the need to inspect original reporting remain limitations.

| Artifact | SHA-256 |
| --- | --- |
| H01.json | `c4e59c6267df5c66fb2f096b0684dd4ee037dba26417404d41d0e1471c74f4e0` |
| H02.json | `56264909169db157adf1e1c8dee3573de378b47e6d255f7a729cbaab9a08d355` |
| H03.json | `3e74543cacc41db9b78407178dc27bb757625687bc22004377d975bf03ff9fc1` |

The three calls cost US$0.07570, bringing the durable shared checkpoint to **US$0.37899925**, 37 cumulative calls and zero unresolved charges. Observed durations are approximately 14.2, 27.2 and 14.5 seconds; cache repeats are not new paid attempts.

Taken together, the stronger profile meets core expectations on **11 known-source reasoning cases**, with no critical/material errors found in this review and minor qualifications retained above. This is useful local engineering evidence for that profile choice, not “100% accuracy”, an independent market benchmark, a forecast-quality result or demonstrated commercial/user value. The comparison history now contains 30 private-comparison attempts across repeated cases, 25 rendered and five withheld; it must not be described as 30 independent examples. The first MINI failures remain part of the history.

## New end-to-end qualitative UI case: stronger model still fills a truncation

Reviewed `.local/live-tests/real-ui-draft-20261002.json`, SHA-256 `eb0af6bb517c150ea95b38c32c9cfae6b2e5c42a87a769eca5ac8b04a587ef00`. This is a new authored demo reasoning revision created through the actual app UI against the same real GOOGL snapshot. It has no numerical conditions: `numerical_assessment` and `evaluation_id` are null. It is not an actual student's submitted research or an independently recruited user's result.

The new question asks whether Gemini's launch shows paid enterprise demand. The saved reasoning says the launch alone does not prove demand and requests adoption/attributable revenue evidence. The strong profile produces two points and correctly leaves that commercial question unproved. However, the first point says access includes **“Google’s internal use”**, while its cited source ends **“Google's internal...”**. The missing noun is not supplied; code-preserved citation text therefore accompanies an unsupported completion in the generated prose.

Independent check: all four citation entries resolve exactly to the packet's source/passages, and both reasoning excerpts resolve to the saved segments. Generation completion and citation identity pass. **Source fidelity fails with a material, bounded unsupported access-detail assertion.** It does not invent a financial number or change the overall “demand not established” conclusion, so it is not classified as a critical financial reversal. The earlier successful P06 output retained the same truncated text, showing that a prompt instruction plus a stronger profile did not reliably prevent the failure across a new reasoning formulation.

Keep the result as a new failure after the eleven accepted core cases. For the stronger-profile evidence reviewed so far: **12 rendered cases, 11 accepted against their bounded semantic expectations, one new passage-completion failure**. This is neither a formal population accuracy estimate nor a reason to relabel the new case as a success because the main conclusion was cautious. Including earlier model rounds, this record contains 31 private-comparison attempts, 26 rendered and five withheld. The saved shared checkpoint is US$0.40106925, 38 cumulative calls and zero unresolved; no reviewer calls were made.

### Proposed structural correction: conditional acceptance

Conservatively withholding ellipsis-marked passages from model input is an appropriate local mitigation, provided it is an eligibility rule with visible limits, not a claim to have solved entailment. The full original sources must remain available for reading/audit. The current private request already excludes the raw `text` field; that protection must continue when passage eligibility changes.

Acceptance cases before the corrective rerun:

1. For `dd93f2cb-05cd-58ef-8e63-bf30a1430cfc`, preserve the original source and its p2 text in historical audit, but exclude the incomplete access passage from the **new** model request. Complete launch/title passages can remain eligible. No raw body or duplicated title field may reintroduce excluded text.
2. Cover provider truncation markers `...`, `…`, `[...]` and `[…]`, with surrounding whitespace/closing punctuation. Document that this is conservative filtering; an ellipsis can be an intentional omission rather than a grammatically unfinished sentence. Unmarked truncation is not solved.
3. Preserve original passage identities when filtering. Do not renumber p3 into p2 and accidentally make old references appear to select different text. Keep a separate `omitted_passage_count` or equivalent; a withheld passage is not an omitted source.
4. The renderer must reject a model selection of an excluded passage even if that ID exists in the stored full source. Request filtering alone is insufficient if render validation still admits the complete old catalogue. Historical outputs keep their exact original packets; new filtered requests receive distinct cache identities/version provenance.
5. If a source has only withheld/ineligible passages, preserve the readable raw source while reporting no usable excerpt to the model. An empty eligible packet should return a clear no-evidence outcome without making a paid request. Do not synthesize a repaired source sentence.
6. Include the Anthropic 47% sentence ending `filing....` as a conservative-overfilter regression. It is syntactically complete but ellipsis-marked; dropping it may be an acceptable limitation, but that changes the evidence available for P07. A new output cannot quote its unavailable 47% value by memory. Record the changed packet and scope any pass accordingly; do not claim an identical-input model comparison after filtering.
7. Re-run this exact qualitative draft under the new eligibility rule and retain the failed original. Expected: launch/positioning evidence, paid demand and revenue unestablished, no invented “internal users/use/team” completion. Then check at least one unrelated complete passage still works so the fix does not suppress all evidence.

This closes a demonstrated input-completeness failure route. It does not prevent all hallucinated prose, establish source truth, make copied stories independent or justify treating a model relation as a deterministic monitoring outcome.

## Filtered-source private retest: final twelve-case scorecard

Reviewed all twelve completed cases and `summary.json` in `.local/live-tests/purpose-filtered-20261001T192901Z/`. Model remains `gpt-5.4-2026-03-05`; private prompt is now `thesis-private-evidence-3`, and the source projection conservatively excludes ellipsis-bearing passages. **This is a corrective regression run, not an identical-prompt/input profile comparison or an unseen-source benchmark.** Existing criteria are unchanged, with the predeclared allowance to remain unclear when the filter removes required evidence.

Across all twelve cases, the saved reasoning/segments, revision, source snapshot, cutoff, evaluation identity and numerical assessments match their original case. Raw source IDs, titles, bodies, publishers and dates are unchanged. Passage eligibility and the prompt changed. I inspected the projection and renderer, and independently reconstructed source wire projections with the pure citation helper without importing credentials or provider settings.

### Completion, citation and eligibility audit

- 12/12 completed; 12/12 record cached repeat.
- 70/70 citation entries resolve to the exact eligible `(source_id, passage_id, quote)`; 33/33 reasoning excerpts resolve to saved segments.
- No excluded passage is selected; reconstructed source projections expose no raw body or ellipsis-bearing title, passage or publisher copy.
- Recorded omission counts agree with independently recomputed counts: MSFT packets omit zero fragments, AAPL one, GOOGL four. These remain distinct from the 14 omitted source records per packet.
- Renderer code rechecks the same eligibility function rather than trusting IDs from the raw source. Original passage IDs are preserved. A packet with no eligible passages is rejected before generation. Historical results remain immutable.
- Separate synthetic helper checks exercise `...`, `…`, `[...]`, `[…]` and spaced `[ . . . ]`, raw-source preservation, title/publisher projection, stable existing IDs and unchanged user-reasoning ellipses. Unicode/bracket ellipsis may share an existing segment with a later complete sentence, so that whole segment is conservatively omitted. This is a documented overfilter limitation, not complete-sentence detection. An initial helper assertion incorrectly assumed every marker split a new segment; inspecting the original segmentation clarified that assumption without changing product code or acceptance criteria.

### Semantic outcomes

| Case | Result | Bounded conclusion |
| --- | --- | --- |
| U01 | Core pass | No invented “Google internal use/users” completion. Launch/benchmark claims remain separate from paid demand and attributable revenue. Excessive decimal precision is a presentation issue. |
| P01 | Core pass, minor wording | Calendar-year expected capex is a margin tension; AI causation remains untested. Prefer “margin was 46.78%” over “preserved at a high level”: one period alone does not establish a trend. |
| P02 | Pass | Departures challenge continuity; strategy emphasis and current financials do not establish stable leadership or lower execution risk. |
| P03 | Core pass, minor wording | Analyst revenue-estimate support and earnings-outlook tension are separate; June results are explicitly before fall. Replace “another note” with “another excerpt”; remove the claim that the packet reports a growth figure “only”, since it also contains margin/operating-income inputs. Neither issue changes the temporal conclusion. |
| P04 | Pass | Attributed AI-agent risk challenges Services insulation; whole-company growth and smart-home plans do not establish resilience. |
| P05 | Pass | Watch plans are prospective; whole-company growth cannot establish measured incremental feature sales. |
| P06 | Core pass | Product launch and claimed benchmarks do not prove customer demand or revenue. No excluded access fragment is completed. Long decimal repetition remains unnecessary. |
| P07 | Pass within filtered evidence | Uses the surviving headline's “nearly 50%” Anthropic-sales wording, corrects the dependency direction and leaves Alphabet's share unknown. It does not pretend the omitted exact 47% source sentence remains available; 47% appears only as the user's claim being evaluated. |
| P08 | Pass | A voluntary pledge is not supplied evidence of completed audits or established safety; concern remains attributed. |
| H01 | Pass | The integration announcement supports that narrow event, not paid usage; monetization commentary is context and the outcome remains unknown. |
| H02 | Pass | One named analyst and vague Wall Street language do not establish broad agreement; breadth remains untested. |
| H03 | Core pass | Reported reorganization consideration is separated from effectiveness and launch forecasts. The memo teaser is limited to background; no implementation or execution benefit is asserted. |

**All twelve meet the core semantic expectations in this corrective run; no critical/material error found.** Minor precision, repetition, sparse-snippet and source-independence limits remain. Passing these checks is not proof of general accuracy, usefulness to students, natural-event monitoring or model robustness across fresh repetitions. The original U01 failure and every earlier withheld/material/critical result remain in the preceding tables.

| Artifact | SHA-256 |
| --- | --- |
| U01 | `01e328d2a6310ef1d0cedf820f249656933a083165eea7e67e8673da033abb30` |
| P01 | `9335548f4a523f2239c72ba49ede08e390ba82bac6f7edf738b9a4f016fa6545` |
| P02 | `f9a40652ef4dd2a38a96a4041b48a47cf2cfb65091f078646aa9229f1c7b0d73` |
| P03 | `a53edc8e958d649d2a83229c418d749697a37d3dcb80adcf4e5cd5d19d19ac89` |
| P04 | `617a4ba79730891a234d937b56113cfbd3a9e3498234fbc7698cc4d74b9fc56b` |
| P05 | `2db80ab04ba1ecc0d265e0d28b63995f1229f812da8733c03681f74167bf03a9` |
| P06 | `8b6f5885b6382ad8b6a2470f1305f37576650b0eeae7aae9aa78d25a1bcad064` |
| P07 | `4f5888fb0bf00b0f945bb101ede388ceffac55673422c2434c41096290e26718` |
| P08 | `424cc5bc5affdfb69ddf967779b0abe2c9c580b907b25bf33028e3b6c78ce452` |
| H01 | `e15a0cbec30ac65cfe01377e045c6cef936ac740613f3fa19b21fa30149f4d03` |
| H02 | `f3807b5c3230ab9c6ae3e56ccab0fda64b2948ed95152c07137ec1aec1e9fc68` |
| H03 | `e513da68884988338df3663ad65990764efbcc44ecf9145a21548ec56f150a61` |

Twelve new calls cost **US$0.326695**, taking the cumulative ledger to **US$0.72776425**, 50 calls, zero reserved and zero unresolved. The private-comparison history now contains 43 attempts across repeated cases: 38 rendered, five withheld. These denominators retain earlier failures but are not independent-case accuracy statistics. No reviewer provider calls were made.

## Shared company briefs v4: separate source-boundary review

Reviewed the three exported results in `.local/live-tests/brief-v4-20261001T193255Z/`, each with its exact provider-wire `.packet` and original `.raw_sources`. Model is the mini profile, `gpt-5.4-mini-2026-03-17`, prompt `thesis-market-brief-4`. These shared summaries do not perform the stronger profile's private-reasoning task; do not transfer the private-comparison score to them.

Each packet contains ten news sources and one SEC calculation source. All three briefs completed and recorded cached repeats. All **19 citation entries** match the eligible wire title/text; no ellipsis-bearing source text is exposed in these exported requests. Reported omission counts agree with the packet: MSFT zero, AAPL one, GOOGL four. Literal quote success remains separate from prose attribution and claim coverage.

| Brief | Source-fidelity assessment | Concrete remaining issue |
| --- | --- | --- |
| MSFT | Core coverage is useful, but one factual qualification needs restoring before calling it fully faithful. | Point 4 calls Roslansky “LinkedIn chief”, while the source explicitly says **former** LinkedIn chief. Restore “former”. This is a bounded role-qualification error, not a numerical or trade-advice error. Management emphasis, expected calendar-2026 capex, margin concern and attributed market commentary are otherwise preserved. |
| AAPL | Core reported/interpretive distinctions are acceptable, with a minor attribution correction. | “These are separate analyst views” is not established by two snippets: they may describe different aspects of the same analyst/note. Prefer “These snippets report analyst expectations and risks.” The Watch feature point correctly avoids claiming measured demand, and the overhaul remains reported consideration. |
| GOOGL | Core reported/interpretive distinctions are acceptable, with a minor citation-scope correction. | Its final interpretation mentions “safety credibility” but cites only product-launch and price snippets. Cite the already-supplied audit-pact item for that inference or omit that phrase. Benchmark leadership remains attributed to the snippet; stronger wording such as “Google claims” would be clearer. No missing internal-access noun is invented, price causation is not asserted, and adoption/revenue remain unshown. |

Thus **3/3 render and 19/19 quotes match**, but the set should not be called three perfectly faithful briefs: retain the MSFT role qualification and the two attribution/citation issues above. None of these outputs invents a financial quantity, recommendation, executed trade, observed Watch demand or completed safety audit. This is a bounded review of supplied snippets, not verification that their journalism is correct or complete.

The GOOGL input is **newer** than the private snapshot-12 cases. Its raw-source maximum app-availability timestamp is 2026-10-02 03:31:20.753065+08:00, and the packet includes `745a0e05-9ca8-5fa6-8fe9-0373f7a62f0a`, a ChartMill generic activity item published at 02:05:03+08:00. The main agent records this as snapshot 13. The shared packet itself has no snapshot field, so preserve its exact saved sources/times rather than assuming the old cutoff. MSFT and AAPL selected source availability remains 02:12:04.585046 and 02:25:19.321181+08:00 respectively. This prevents attributing changes from a newer source selection solely to a prompt revision.

| Artifact | SHA-256 |
| --- | --- |
| MSFT.json | `447d163bd0bb85d6e65747f59a3f0d4d2df2c614eeca2ca12145058d5f8d9a0e` |
| AAPL.json | `af1dd7becd1517832d67a79da7ce6428391d0f1989e22945ddeb5d25ab1ef3b1` |
| GOOGL.json | `26e509320cb1d11b5e3f9d61a26eb26e71808e43e20673d0099083c32ae566aa` |

The `AAPL-v2-validation.json` file records that the old unsupported-citation response still fails validation. It is an old-response validation check, not another new successful summary or a new paid attempt. Keep the original first Apple generation failure in its original round.

The three new brief calls cost **US$0.01349325**, taking the shared checkpoint to **US$0.7412575**, 53 cumulative calls, zero reserved and zero unresolved. They are additional shared-summary attempts, not additions to the private-comparison case denominator. No reviewer calls or final-app changes were made.

## Actual UI comparison after the real source snapshot advances

Reviewed `.local/live-tests/real-ui-updated-comparison-20261002.json`, SHA-256 `739588db5c4da79b6e2b5fb582b60bb4cda9ff1979c9c8f8fb66983786aee483`. The same authored qualitative draft and version (`d298113f-2b8d-4d48-a616-e8bee3fb0b8c`) now use real GOOGL snapshot **13**, advancing the source cutoff from **2026-10-01 18:25:28.817131 UTC** to **19:31:20.753065 UTC**. There is still no numerical assessment or evaluation ID, as intended for a draft without conditions.

The selected 12-source packet adds the ChartMill activity story `745a0e05-9ca8-5fa6-8fe9-0373f7a62f0a` and displaces the unrelated Meta story `114da4c8-2b78-5c8c-9912-1f9fc51ac64a`. It reports 15 omitted sources and four withheld ellipsis-bearing passages. This is a newer source packet, not an identical-input replay or a new company-specific commercial event.

The stronger private-v3 result meets the bounded expectations: launch/benchmark coverage supports the user's caution, paying adoption and attributable revenue remain unestablished, and aggregate financial results remain context. No truncated access noun is supplied. All **seven citations** match eligible source passages; all **three reasoning excerpts** match the saved draft. The unbenchmarked adjective “strong” remains unnecessary but does not change the causal or financial conclusion.

This demonstrates preservation of an idea and its source history through a real source update and explicit UI re-review. It does **not** demonstrate that a meaningful catalyst was detected, that an automatic thesis-specific alert was useful, or that a real student returned voluntarily. The new selected story provides no new Gemini demand evidence, and the output appropriately does not manufacture it.

The paid checkpoint is **US$0.7657775**, 54 calls, zero reserved/unresolved. This adds one private comparison to the history: 44 attempts, 39 rendered and five withheld across repeated cases. The original unfiltered UI failure remains in the record. No reviewer paid call was made.
