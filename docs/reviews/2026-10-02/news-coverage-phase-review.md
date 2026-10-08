# Phase 19 — quieter repeated coverage, visible new details

Parent-authored review through five professional perspectives. This is not an independent consultant panel or participant validation; independent agents remain unavailable under the previously recorded account limit. This phase returns to the user's primary selling points: useful sentiment and evidence-linked alerts.

| Perspective | Finding | Implementation / remaining work |
| --- | --- | --- |
| Product | Differently worded reports of one development could overcount sentiment and interrupt a watch again. | Compare reports as repeated coverage, added detail or contradiction. Count related news once while retaining every source. Only justified repeats of already seen reports may stay quiet. Bounded lookback still misses older or unselected matches. |
| UX | Grouping can hide disagreement unless the reason and both reports are inspectable. | Each comparison exposes exact passages, both original sources and an explanation. Conflicting framing becomes mixed/unclear in the group count. Phone/desktop inspection passes. The interface labels grouping as interpretation; participant comprehension remains unmeasured. |
| Data / ML | The initial model grouped two Apple analyst stories using an institution/person connection absent from the supplied snippets. | Preserve that result. Prompt v4 requires explicit shared identifiers; the corrective run keeps those stories separate. Initial prewritten checks missed this problem, showing why manual review still matters. No general precision/recall claim follows from the retest. |
| Engineering | Copied-body keys alone can hide a corrected headline. Numeric suffix handling also falsely blocked a legitimate repeat. | Use full-content delivery identity, exact repeat-reference identities and conservative guards; keep body grouping only for counts. Fix `$3.2B` versus `$3.2 billion`. Retain immutable histories, source withholding, private revision checks, watch fencing and the original paid ledger. |
| Commercial | Repeated interruption weakens the case for paid monitoring, but quietness alone can conceal missed developments. | Evaluate useful retained updates and missed material changes together. The observed development cost is not customer cost-to-serve or willingness to pay. Prospective feeds and participant feedback remain necessary. |

## Implemented scope

[The contract](../../features/news-coverage.md) records the precise source, grouping and delivery rules. The existing sentiment request now classifies up to eight news/eight social items and compares the news against each other and up to sixteen additional permitted recent snippets. Comparison-only sources do not add votes. Social opinions never join news groups. There is one metered request, not a second grouping service.

Each comparison carries two-sided exact citations. Added information, contradictions, uncertain opinions, differing explicit status terms and new numeric text remain reviewable. A model link is not factual verification. A changed counting policy cannot itself trigger a sentiment-reversal alert. Private watches remember newly seen repeats without editing saved reasoning. Old outputs are unchanged and source withdrawal includes comparison-only evidence. No watch was enabled and no alert was published into the main account by this evaluation.

Deus URL/calendar deduplication was inspected but cannot substitute for semantic report comparison. This layer is new Thesis code around the existing Deus classifier and Kestrel review patterns, documented in [provenance](../../../PROVENANCE.md). No extra API key, library, data purchase or schema migration was needed; schema remains 16.

## Actual-source and authored contrast evaluation

Four initial v3 requests used three frozen actual-company packets and one explicitly fictional contrast packet. Actual packets have 39 selected news/social sources in total, plus sixteen comparison-only news snippets per company. The fictional packet has nine selected items contrasting planned/completed launches, rumour/denial, different reporting periods, an exact-meaning paraphrase and separate social opinion. Source records had been seen previously; this is not an unseen-source benchmark.

Initial checks matched **12/12 prewritten grouping/delivery-eligibility expectations**, with **113 exact quotation associations**. Manual review separately caught the unsupported Apple analyst-identity inference. It also found that the numeric guard parsed the short `$3.2B` spelling incorrectly, retaining a Google repeat that should have been eligible for suppression. Neither issue is concealed by the initial passing count.

After correction, four explicit v4 retests reused the frozen source packets with two added expectations for those observed failures. They match **14/14 specified checks**, with **111 exact quotation associations**. All eight paid outputs remain retained; **224 quotation associations** match source text across the two runs. Exact quotation matching does not establish all labels or explanations as semantically correct.

| Final checked case | Result |
| --- | --- |
| Apple Watch copied reports | Count together; both source cards remain. |
| Apple CEO memo versus Watch updates | Remain separate. |
| Apple Morgan Stanley versus Woodring-only snippets | No unsupported shared-note/identity inference; remain separate in v4. |
| Google EU access orders versus US publisher damages case | Remain distinct legal proceedings. |
| Google venture fund versus nuclear deal | Remain distinct transactions. |
| Google same publisher-damages ruling, two amount spellings | Repeat comparison survives; no false new-number guard. |
| Microsoft Roslansky reports | One coverage group, with added growth/Copilot/timing detail retained for review. |
| Microsoft Wells Fargo tactical-list stories | One coverage group; additional upside framing remains reviewable. |
| Authored plan/completion and rumour/denial | Added detail and contradiction, respectively; never silently treated as repeats. |
| Authored different quarters and social opinion | Keep distinct; the social item does not join a news group. |
| Authored same cloud-outage paraphrase | Repeat eligible for quieter delivery only after earlier coverage is seen. |

The main Microsoft news sample now counts **six interpreted groups from eight reports**, preserving all eight cards. This reduces two duplicated developments without claiming independent corroboration. Apple counts seven groups after removing the unsupported extra merge.

A separate pure delivery-rule replay uses the saved final Google and Microsoft source/model records. Assuming the referenced earlier report was already seen, Google produces **zero** new adverse-report alerts for the repeat, while Microsoft's added departure details produce **one** grouped alert. The baseline is constructed for this rule check; this is not an observed live watch transition, historical sentiment accuracy or prospective latency measurement.

Evidence folders:

- `.local/live-tests/news-coverage-20261002T053604Z/`: initial v3 manifest, requests, responses, results, scores and accounting.
- `.local/live-tests/news-coverage-retest-20261002T054330Z/`: final v4 manifest, four corrective results, original-source quotations, delivery replay and before/after account checks.

The unused first authored manifest included numeric test labels in headlines; it was corrected before any dispatch so those labels would not masquerade as new reported numbers. Initial and final paid manifests remain separate and immutable. Six actual-source analyses are stored in the app with their own versions; synthetic output stays in the evaluation directory. No new feed retrieval occurred during this phase.

## Software verification and installation

- **443 integrated backend checks** pass with the saved actual SEC corpus after the prompt, numeric and headline-identity corrections. **68 focused checks** pass after the final legacy-body-only delivery guard, including its added regression case. Provider calls are mocked in these checks.
- Five frontend checks and production build pass. Sentiment/watch and private-alert browser journeys pass on the final UI at **320/390/1440px**, covering both quoted reports, original-source inspection, persisted opt-in controls, private question anchors, history, downloads and review status. The final legacy-key guard changes backend delivery only and is covered by the focused suite.
- The actual Microsoft browser shows the six-group/eight-report summary and two-sided report comparisons. Reads and comparisons do not make supplier or model requests.
- Initial installation and correction backups use `.local/backups/phase19-news-coverage-20261002T053434Z/` and `...20261002T054255Z/`; the final installation's backup is recorded alongside its verification. Every preexisting row and private environment value is preserved. Main saved versions, watches, publications and monitoring state match the pre-evaluation snapshots; watches remain off.
- One existing dependency deprecation warning remains. There is no production-authentication or hosted-service claim.

## Accounting and next phase

Eight explicit OpenAI requests cost **US$0.602105** confirmed in this phase. Cumulative confirmed spend is **US$3.824481**, plus the unchanged **US$0.13926 original maximum hold**; **125 calls**, **US$6.036259 remaining** under the original US$10 software ceiling. No new ambiguous charge occurred. The original interrupted charge remains unsettled.

The semantic-coverage gap is now addressed within a bounded source sample. Broader social-risk calibration, unseen-event grouping, whole-feed recall, prospective alert timing and participant usefulness remain unverified. The full roadmap is incomplete. A further product gap is answering the user's chosen research question directly before requiring a saved idea; the current company-wide briefing explicitly does not do that. Wider source/issuer coverage and structured guidance/consensus also remain outstanding. Do not keep tuning this small corpus and call it independent validation.
