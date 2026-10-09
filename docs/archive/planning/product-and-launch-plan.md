# Investment research companion product and launch plan

Revised 1 October 2026. This plan combines the useful parts of the team's original product and launch plan with the current direction: help students and new investors investigate investment ideas, track fundamentals and expectations, identify risks, and monitor changes. Deus supplies research capabilities; the latest Kestrel frontend supplies the application experience. The database is being redesigned around that workflow.

**The product helps a user answer three recurring questions: Why might this investment work? What evidence could prove my reasoning wrong? What has changed since I last checked?** Learning happens while using those tools. The proposed recurring revenue comes from ongoing research and monitoring utility.

This is a product proposal, not a record of customer validation, paid demand or an executed launch. It complements the [architecture](architecture.md) and [database design](database-design.md). The [UX and user journey](ux-and-user-journey.md) maps the first visit, monitoring setup, return visits and alternate states to the existing Deus/Kestrel capabilities.

## Audience and problem

Start with students, paid interns and fresh graduates who already have an investment idea or want to begin researching one. Campus networks and investing clubs provide an accessible route to interviews and early users. Fresh graduates remain a useful segment to test for sustained usage and willingness to pay; higher willingness to pay is a hypothesis, not an established fact.

Keep the original plan's insight that beginners often ask a trusted friend to interpret conflicting information. Test whether a source-linked research workflow can provide value without that personal relationship. The initial task is researching a company and forming a view, so account balances, salary, CPF, debt and card details are unnecessary onboarding inputs.

The product promise is a clear view of business performance, the expectations behind an investment story, contrary evidence and developments worth reviewing. A user may use it to decide that they need more information or do not want to pursue an idea; placing a trade is not the activation goal.

## First session and ongoing use

Retain a short onboarding flow, with five minutes as a design target to test rather than a measured completion time. Ask for a company or idea, what the user wants to understand, their tentative reasoning, and an optional research horizon. Offer plain-language explanations and let users skip directly to research. Notification choices follow after the user has something worth monitoring.

The first session should produce a useful research brief and one approved thesis with meaningful conditions. Deus gathers and distils permitted sources. The brief distinguishes reported fundamentals, management guidance, available consensus data, social narratives and the user's assumptions. Social discussion is not automatically market consensus. Kestrel lets the user review the proposed thesis, supporting conditions and invalidating events before saving them.

| Moment | User experience | Purpose |
| --- | --- | --- |
| First session | Read a company brief, inspect a source and approve or edit a thesis | Turn a vague idea into explicit reasoning and questions to monitor |
| First week | Review supporting and opposing evidence; adjust an unclear condition | Check that the research is understandable and the conditions match the user's meaning |
| When relevant evidence changes | Receive an optional alert linked to the affected condition and exact evidence | Show why a development matters to this thesis |
| Weekly review | See new evidence, changed conditions, unresolved questions and coverage gaps | Reduce the effort of keeping research current |
| Around day 30 | Revisit the original reasoning and its revisions; give feedback on usefulness | Test repeat value and willingness to continue |

The original market-explainer idea becomes a company- and thesis-relevant explanation. A broad market event appears when there is a supported connection; the product should not invent relevance. A quiet period can say that no material change was detected within the stated coverage. Missing coverage must remain visible.

Replace automatic reassurance during market falls with an evidence review: what changed in fundamentals, expectations or the user's invalidation conditions? Do not default to telling the user to hold, buy more or stay with an outdated thesis.

Keep a place for basic questions, using Deus's research chat patterns with citations to the current brief and permitted sources. Explanations of terms should support the current task. A course sequence, quiz gate or options curriculum is outside the initial product.

## Product boundaries and trust

Reuse Kestrel's current frontend and suitable backend/evaluator functions. Treat the older ML repository as a source of useful code, not the current specification. Deus research and Kestrel monitoring share versioned evidence in the new PostgreSQL design. Historical evaluations must retain the conditions and sources they actually assessed.

Keep the original plan's transparency principles: show sources, timestamps, missing data and commercial relationships if any are introduced. Research ordering and conclusions must not depend on referral commission. The first product does not need product comparison rankings or affiliate integrations.

The proposed MVP supports company analysis and user-approved condition monitoring. Fund custody, trade execution, copy trading and personalised allocation instructions remain outside it. Retain a product/legal review before public launch as a planning task; calling the interface educational or adding a disclaimer does not establish its legal classification. Retain permitted-source access and data-use checks already present in the architecture.

## Revenue hypothesis

Test a subscription for continuing research and monitoring. The original plan's premium-tier idea is useful, but the paid value should be research capacity, saved monitoring work and review history rather than additional beginner lessons. Do not make card commissions or partner sign-ups the revenue foundation.

| Access | Proposed value | What must be tested |
| --- | --- | --- |
| Free or trial | A limited amount of company research and thesis monitoring, with sources and clear limitations | Can a new user reach the first useful result and return? |
| Paid | More active theses, greater research capacity, configurable monitoring, longer review history and research exports | Which capability users repeatedly need and will pay to retain |

Exact prices, quotas and refresh intervals are unresolved. Estimate them after measuring model, market-data, notification and support costs. Basic provenance and honest uncertainty should remain visible in every tier. Subscription interest in an interview is weaker evidence than actual paid continuation in a later authorised trial.

Campus sessions can demonstrate the tool and recruit users. Do not turn workshops or financial education into the assumed core business. Broker or other partnerships are not required for the initial workflow or revenue test.

## Validation and launch sequence

Use the original plan's small-cohort interviews and phased expansion, while testing the existing Deus/Kestrel foundation. The old instruction to build no app until a manual education pilot succeeds is not adopted. Technical integration and research interviews can proceed together within their authorised scope.

| Stage | Proposed activity | Evidence for the next decision |
| --- | --- | --- |
| Research and integration | Review recent investment questions; demonstrate one company brief, thesis, evidence change and alert using recorded fixtures | Users can explain the output; the team can trace claims and replay the monitoring flow |
| Small pilot | Aim for 20–30 participants over roughly four weeks, deliberately including people without a personal relationship to the founders; interview about 10 at the end | Repeat research use, source comprehension, useful alerts, reasons for leaving and willingness to pay |
| Closed beta and pricing test | Improve the repeated tasks identified in the pilot; test a defined paid offer when ready | Paid continuation, manageable errors and measured cost to serve; separate friends from independent users in results |
| Campus expansion | Broaden recruitment through clubs, referrals and research demonstrations once earlier evidence supports expansion | Repeat value beyond one social circle and sustainable acquisition/support costs |

These sample sizes and durations are proposed research parameters retained or adapted from the original plan, not completed work or commitments. Choose later cohort sizes from results and capacity. The old October 2026–August 2027 calendar, 1,000/5,000-user milestones and fixed percentage gates are not inherited as forecasts or deadlines. This document does not initiate recruitment, messaging, data collection, paid trials or deployment.

## Measures of usefulness

Define a meaningful research action before recruitment. Use the same definition throughout a cohort and report counts alongside rates.

| Measure | Definition or evidence | Interpretation |
| --- | --- | --- |
| Activation | Participant completes a research brief review and saves an approved thesis with at least one condition | Reached the core workflow; no trade or partner sign-up required |
| Week-four retention | Activated participants who perform a meaningful research action in days 22–28, divided by all activated participants with a full 28-day observation window | Repeat use; reminders, logins and automated deliveries alone do not count |
| Review value | User inspects evidence and records a reviewed, revised, rejected or unresolved conclusion | Whether the tool supports a deliberate decision; retaining a thesis can also be useful |
| Alert quality | Reviewed examples of relevant, irrelevant, missed or unsupported changes | Quality of monitoring, not alert volume |
| Independence from founders | Recruitment source and prior relationship, reported separately for activation, retention and feedback | Whether personal relationships explain apparent demand |
| Commercial viability | Paid conversion and continuation when tested; cost per active user and watched company; support time | Whether recurring value can support the service |

Weekly retention is useful, but it does not by itself prove trust, accuracy or investment returns. Combine observed use with interviews, source checks and complaints/corrections. A four-week cohort is an early product test, not proof of long-term retention.

## Selection from the original plan

Source: [Investment Companion — Product & Launch Plan](</Users/jiahuiwong/Downloads/Investment Companion — Product & Launch Plan.pdf>), seven pages, dated 1 October 2026. Page references below identify the historical idea; the adopted interpretation follows the newer user direction.

| Original idea | Source | Treatment |
| --- | --- | --- |
| Fresh graduates, interns and access through campus networks | pp. 1, 5–7 | Keep alongside the current student audience; test segments separately |
| Trust, approachable questions and accessible explanations | pp. 1, 3 | Keep as research UX principles and interview hypotheses |
| Five-minute onboarding and a guided first month | pp. 2–3 | Adapt to company research, thesis creation and review |
| Ongoing explanations, check-ins and milestones | p. 3 | Adapt to thesis changes, evidence review and monitoring setup |
| Cash flow, emergency funds, CPF, insurance, savings and card matching | pp. 1–4 | Exclude from this product scope |
| Low/medium/high curriculum stages and options quiz gate | p. 2 | Exclude; support learning within analysis instead |
| Payday investment amounts and automatic calming messages | p. 3 | Replace with optional research reviews; no default hold/buy-more nudge |
| Free app funded mainly by product referrals | p. 4 | Exclude as the core model; test recurring research subscriptions |
| Premium tier, transparency and independence from commission | p. 4 | Adapt premium value to ongoing tools; retain transparency |
| Interviews, small cohort, referrals outside friends and staged expansion | pp. 5–7 | Keep as proposed validation methods |
| No code before Phase 0; fixed dates, scale milestones and partner conversion targets | pp. 5–6 | Do not inherit; use the existing products and research-specific evidence |
| Claims about competitors and retention proving trust | pp. 4–6 | Do not adopt as established facts; no fresh competitor assessment was performed |

The original PDF remains unchanged. The current plan preserves its useful audience, usability and validation ideas while keeping investment research and monitoring as the product's continuing job.

## Future business analysis

Added 8 October 2026 at the owner's request. **9 October implementation checkpoint:** original filing collection, a sourced business brief, trailing calculations, managed local login and private reviewed peer choices are implemented. See the [feature contract](../../features/original-company-research.md) and [actual review](../../reviews/2026-10-09/original-research-and-managed-login.md). FMP Broadcom consensus/ratios require subscription access; general custom/multidimensional extraction, comparable consensus-versus-actual evaluation and beginner comprehension/usefulness testing remain future work. Supported original-filing segment/product/geography revenue now has a [verified breakdown view](../../reviews/2026-10-09/reported-revenue-breakdown.md); overlapping annual geography stays uncharted. Saved assets, liabilities, cash and borrowing now have a [dated financial-position view](../../reviews/2026-10-09/financial-position-and-forecast-access.md). A bounded [original management outlook](../../reviews/2026-10-09/management-outlook.md) now preserves dated release guidance and compares only explicitly compatible pre-period GAAP USD revenue; actual Broadcom remains uncompared. Saved peers now have a [visual comparison](../../reviews/2026-10-09/peer-comparison.md), with separate providers and preserved draft choices. The peer chart also reuses [annual reported revenue growth](../../reviews/2026-10-09/peer-revenue-growth.md), retaining both fiscal periods and original inputs. The original expansion requirements below remain the target, not a claim of full completion. A separate public annual forecast route is now implemented and live-checked for Qualcomm; it preserves missing currency and restricted years, and does not complete quarterly/pre-release consensus coverage. [Forecast review](../../reviews/2026-10-09/public-financial-forecasts.md).

### First version Business brief

Add a short **Understand the business** overview with expandable detail:

- What the company does, its sector/industry, main products and services, and explanations of unfamiliar terms.
- How it makes money: customers, revenue model and reported business-segment revenue where available, with the reporting period and source.
- The main drivers of revenue, profitability and cash generation, separating reported facts from AI interpretation.
- Relevant competitors and the products or markets in which they overlap.
- Financial position: cash, borrowing and other liabilities or obligations. Explain their meaning rather than treating all liabilities as debt or automatically adverse.
- Specific documented risks, dependencies and questions worth investigating.

Use the latest available annual filing's business section, financial notes and risk disclosures, supplemented by relevant quarterly filings and company materials. Preserve exact source references, dates, missing information and the distinction between company statements and interpretation. Existing recent-news summaries alone are insufficient for a complete business profile; narrative and segment evidence need additional collection. Reuse eligible financial inputs and the existing citation, source-permission and history controls.

AI explains the supplied evidence; code calculates financial values. Save and reuse briefs against their evidence versions, with visible source age and deliberate refresh. Retain the existing explicit paid-action and cumulative-budget controls. Suggested research questions require user selection and must not automatically save reasoning or enable monitoring.

### Later version Competitor comparisons

Start with two or three reviewed peers and explain the business overlap and why each comparison is useful. Distinguish competitors in one product from suitable peers for whole-company valuation; a shared sector label is insufficient.

Compare a small set of suitable measures, such as revenue growth, operating margin, cash generation and P/E or P/S when meaningful. Keep metric definitions, currencies, reporting periods and retrieval dates explicit; separate trailing results from forward estimates and reported earnings from adjusted earnings. Missing or unsuitable ratios remain unavailable. A lower multiple must not become an automatic investment ranking or buy recommendation.

### Acceptance before expansion

Check the brief's claims, segment figures and peer rationale against original evidence. Ask beginner participants to explain what the company sells, who pays it, one important risk and one research question after reading the brief. Test comprehension and usefulness before expanding the comparison engine. This future-work item sets no implementation date and does not establish validated user demand.
