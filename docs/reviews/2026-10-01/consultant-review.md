# Thesis consultant review

Reviewed 1 October 2026. **Thesis is worth testing as a focused investment-research workflow. The current evidence does not yet justify building the full feature set or assuming a subscription business will work.** Its strongest product hypothesis is helping a person compare their saved reasoning with new evidence and understand what changed.

This report combines five consultant roles: product strategy, commercial strategy, UX/customer research, technical architecture, and investment-research quality/risk. The environment allowed three subagent threads; two were reused for the last two roles. The first three reviews were separately scoped, but the five reports are not five independent agents or human professional opinions. They are AI assessments of the planning documents and SQL, with selected official sources checked. Agreement is useful for prioritisation, not customer validation.

The review did not change the product plan, UX proposal, architecture or SQL. Suggestions below remain recommendations. No customer research, paid calls, recruitment, deployment or new database tests occurred in this review.

## Findings by role

| Role | Judgment | Most useful improvement | Full report |
| --- | --- | --- | --- |
| Product strategy | The demographic audience is broad and the differentiated benefit needs proof | Start with people already revisiting a few individual-company ideas; demonstrate a before/after evidence review | [Product strategy](product-strategy.md) |
| Business model | Continuing monitoring could be valuable, but neither payment motivation nor serving cost is known | Test a bounded paid offer and measure renewal, support and data costs | [Commercial strategy](business-model.md) |
| UX and research | The proposed first session demands too much investment discipline from a beginner | Help the user understand one question first; offer monitoring as an optional next step | [UX and research](ux-research.md) |
| Technical architecture | One API, worker and PostgreSQL is feasible; important behaviour remains unimplemented | Complete one atomic, version-correct research-to-review workflow | [Technical architecture](technical-architecture.md) |
| Research quality and risk | Evidence retention is a good foundation, but citations alone cannot establish correct analysis | Define claim support, metric meaning, time cutoffs and abstention rules, then test them | [Research quality and risk](research-quality-risk.md) |

## What to preserve

Keep the latest Kestrel frontend and selective Deus reuse. The user has already confirmed ownership and permission; this review introduces no new code-reuse permission gate. Keep the historical thesis/evidence model, user approval of changes, contrary evidence and visible missing data. Those choices support the intended recurring job.

Preserve the clear separation between research and learning support. The reviewers found no reason to restore credit cards, broad money planning or an education-led business. Campus access remains a useful recruitment route, while its commercial value still needs measurement.

## The most important strategic change

Position the first product around a specific occasion: **“New results are out. Do they change the reasons I was interested in this company?”** Earnings or another bounded company development provides a concrete trigger, relevant evidence and a before/after comparison. This is a proposed first test, not a decision to restrict the product permanently to earnings.

The suggested initial participant is a novice investor already following a few supported individual companies and revisiting their reasoning. Students and graduates can both qualify. “Student” describes an accessible audience; existing research behaviour identifies the problem to test. Do not assume every beginner wants to maintain a thesis or that salaried graduates will pay more.

Broad summaries are an insufficient differentiation claim. Koyfin advertises financials, estimates and watchlists in its free offering. Quartr advertises free mobile AI research, transcripts and source traceability. These are vendor-described capabilities, not independently tested quality. They support testing Thesis against existing alternatives; they do not establish that competitors lack thesis-review features. [Koyfin pricing](https://www.koyfin.com/pricing/) · [Quartr mobile](https://quartr.com/products/mobile-app)

The candidate advantage to demonstrate is the connection between the user's original reasoning, exact new evidence and a recorded reassessment. Compare that workflow against a good source-linked summary plus ordinary notes, using the same evidence.

## Prioritised improvements

| Priority | Current issue | Proposed change | Evidence needed |
| --- | --- | --- | --- |
| First | Audience and recurring job are too broad | Recruit by recent company-research/review behaviour; test one results-review task | Participants demonstrate a real existing problem before seeing the concept |
| First | Activation requires an approved thesis even when rejection is a useful outcome | Separate research activation from monitoring activation; count supported rejection and unresolved conclusions | Users understand the evidence and their next step without being pushed to save a belief |
| First | Conditions require thresholds, periods and evidence rules beginners may not understand | Start from one question, then offer one explained condition; permit “I cannot define this yet” | Users distinguish the assumption, matching evidence and limitations without coaching |
| First | The differentiating before/after workflow is not integrated | Connect one brief, approved condition, evidence update and review using recorded fixtures | Correct history, complete results and useful comparison with the simple baseline |
| Before multi-user use | Planned security and transaction rules are not yet executable guarantees | Implement real API/worker roles, atomic edits/approvals, complete evaluation publication and source permissions | Cross-account, concurrent-edit, stale-job and restricted-source checks pass |
| Before paid operation | Price, usage limits, data commitments and support effort are unknown | Meter work; define a bounded offer; obtain applicable data quotations; test actual paid continuation | Heavy included usage remains viable and renewal occurs beyond one useful event |
| Before broader coverage | Research claims, periods, cutoffs and coverage states are underspecified | Introduce a narrow typed evidence contract and a fixed adversarial evaluation set | Unsupported confirmation, temporal leakage and misleading missing-data states are caught |

“First” means the next product/engineering iteration, not permission to perform outreach, spend money or deploy. Research interviews and a recorded-fixture integration can proceed as complementary proposed workstreams; there is no need to resurrect the original plan's blanket no-code rule.

## Revised journey to test

**Choose a company or sample → understand one question → inspect a source and an uncertainty → decide whether to pursue, leave unresolved or reject → optionally save and monitor one condition.**

On return: **open a grouped evidence change → compare it with the previous observation and reasoning → mark reviewed, edit, or leave unresolved.** Acknowledging an update should not require declaring that the investment remains attractive. “Mark reviewed” is clearer than using “Keep my idea” as the default acknowledgement.

A quiet period and a failed source check need distinct states. Freshness and disagreement can coexist, so neither should disappear behind a single reassuring status. Notification deduplication in the database is necessary but insufficient: the UX also needs to group repeated stories and related changes so the user does not receive several interruptions about the same underlying event.

Measure research completion and monitoring adoption separately. Report the full recruited cohort, non-completers and departures as well as activated users. Add return rates after a relevant covered event; do not penalise a user simply because no meaningful development happened that week. A replayed historical event can test comprehension, but cannot establish natural return behaviour or renewal.

## Minimum first product

Keep a bounded set of supported companies and metrics, a compact source-linked brief, user reasoning, a small condition vocabulary, versioned evaluations and one before/after review. Begin with in-app updates; add one optional digest when its coverage and recovery behaviour work.

Defer broad social listening, general-purpose chat, arbitrary valuation scenarios, several external notification channels and systematic strategy backtesting until the central workflow demonstrates value. Deferral does not mean deleting reusable Deus/Kestrel capabilities or abandoning the long-term direction.

The technical reviewer did not consider the table count itself the central problem. Simplify the feature perimeter while preserving the integrity needed for the chosen workflow. In particular, the inspected draft needs service enforcement of complete evaluations and immutable history; typed metric/period rules; an exact input manifest; restricted roles; and durable source-check/coverage state. These are implementation gaps in a design draft, not claims that an inspected production app is broken. [Schema](../../archive/planning/schema.sql) · [Database design](../../archive/planning/database-design.md)

The research-quality reviewer also identified two specific schema limitations: brief evidence is linked at section level, and condition coverage is a mutually exclusive fresh/stale/missing/conflicting field. Specify claim identifiers and support rules inside validated brief output, and model availability, freshness and disagreement separately. Do this before presenting those outputs as reliable monitoring states.

## Commercial test and costs

Sell the continuation of useful work: monitored evidence changes and understandable reassessment. Avoid relying on withholding a user's completed history as the purchase trigger. Keep completed results accessible subject to source rights; charge for additional ongoing work and capacity.

The commercial reviewer proposed **S$12 per month as a hypothetical experiment**, not an established price or approved offer. Compare monthly continuation with an explicitly priced earnings-season offer if use is concentrated around results. The reviews do not establish which model wins. No annual-retention claim can be inferred from a short pilot.

Account for net receipts, payment fees, private model calls, allocated shared research, usage-based data/infrastructure, delivery and support labour. Then separately account for fixed data minimums, hosting, free-user service and acquisition costs without double counting. Reused software does not remove these costs. A quota on thesis count alone does not constrain repeated refreshes, chat volume or unusually complex private conditions.

Provider access remains an unresolved cost input. Finnhub's enterprise listing describes commercial/redistribution rights with contact-sales pricing; it is not a quote for this product. OpenBB likewise distinguishes its software licence from provider-data terms. Neither finding requires adding OpenBB or committing to Finnhub. [Finnhub enterprise](https://api.finnhub.io/pricing-startups-and-enterprise) · [OpenBB data rights](https://docs.openbb.co/odp/python/faqs/license)

## Differences between the recommendations

| Tension | Synthesis |
| --- | --- |
| Strategy favours investors already tracking companies; UX supports newcomers without a formed view | Use behaviour to select the first buyer cohort, while keeping the entry interaction understandable to a beginner |
| Strategy favours a structured saved idea; UX questions mandatory thesis creation | Offer research value first; structured monitoring is a separate, informed conversion |
| A subscription assumes continuous value; earnings reviews may be episodic | Test payment and renewal across both relevant events and quiet intervals; compare packaging rather than assuming a winner |
| Product advice cuts scope; technical and quality advice add integrity requirements | Reduce companies, condition types and features; keep correctness and provenance for the reduced scope |

These are design tradeoffs, not a five-person vote. Two role pairs shared a reviewer thread, and all reviewed the same plans. Repeated findings should be tested rather than treated as independent proof.

## Proposed decision sequence

1. **Clarify the job.** Interview a small group with recent research behaviour, including people outside the founders' circle. Ask about the last actual review before showing the product. The role reports give proposed small-sample thresholds; these are planning choices, not established benchmarks.
2. **Compare two workflows.** Use identical recorded evidence to compare the current thesis-first flow with the question-first flow and a simple summary-plus-notes baseline. Counterbalance order; measure comprehension, material errors, effort and reasons for stopping.
3. **Complete the technical slice.** Implement atomic saving, exact historical inputs/results, missing-data handling and in-app review. Exercise conflicting edits, expired conditions, outage recovery and access isolation with fixtures and mocked providers.
4. **Evaluate research quality.** Include fabricated or negated quotes, wrong-company evidence, period/currency mismatches, syndicated stories, denials and restatements. Define expected outcomes before tuning. A supported quotation is not automatically support for the surrounding conclusion.
5. **Test commercial continuation when ready.** After measuring costs and defining the offer, observe payment and renewal through real review opportunities and quiet periods. Separate independent customers from friends. If repeated usefulness or viable economics is absent, revise the proposition rather than widening features.

For Singapore launch planning, review actual generated thresholds, chat and notification wording for implied buy/hold/sell recommendations. The MAS material cited by the risk reviewer is relevant context, not a legal classification of this unbuilt product. A product-specific assessment remains necessary before public launch. [MAS explanation](https://www.mas.gov.sg/news/parliamentary-replies/2024/pq-on-complaints-against-online-finfluencers)

The immediate recommendation is a narrow prototype and evidence-gathering plan. Keep the current code-reuse direction, revise the first-session success definition, and make the saved-reasoning/change-review workflow the thing users compare and potentially pay for.
