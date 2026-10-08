# Separate evidence checking — phase 43

A separate model checker was evaluated against unchanged findings from phase 42. It received each finding's own quotations and the full eligible source context, including saved conversation parents. It could retain or withhold a finding, but could not rewrite it. This is a development experiment; the checker is not connected to app publication, sentiment totals, saved answers or alerts.

## Design and evaluation boundary

`thesis/research/finding_check.py` constructs closed-schema decisions for classifications, coverage links, answers, evidence points, gaps and follow-up questions. It checks original quotation membership before dispatch, keeps selected evidence separate from wider context, excludes private source-storage metadata and includes the owner, policy and complete request in identity. It does not fetch sources, dispatch a call, mutate research or apply verdicts. Production integration would still need access rechecks, worker-lease fencing, immutable history, owner-scoped accounting and visible handling of rejected findings.

The frozen evaluation contains eight packets: Microsoft, NVIDIA and Amazon sentiment, Microsoft and Amazon answers, two fictional-company packets, and a paired fictional control. NVIDIA's phase-42 answer was structurally rejected and is not silently treated as an accepted candidate. The eight packets contain **80 decision units**, with **33 predeclared selected decisions** requiring either retention or withholding. Labels remain outside the model request. All original evidence, candidate wording, requests, verdicts and failures are retained in `.local/live-tests/finding-review-20261003T060757Z/`.

The paired control includes the same incorrect cause and omitted-current-opinion answer beside authored corrections. This tests whether valid alternatives survive and whether the same error receives a consistent decision. These are selected development cases and agent-authored expectations, not independent human labels or an unseen accuracy benchmark. A selected-decision match is not an overall accuracy measurement.

## Initial medium-reasoning result

All eight requests completed and returned all required decisions. The checker matched **29 of 33** selected expectations. It caught the authored sale-cause invention and the omitted current respect in the ordinary authored answer packet. It also caught the Microsoft current-spending addition and unsupported inherent positivity of NVIDIA's buyback authorization.

Four selected misses remained: Microsoft's added “too heavily” wording, target-company direction derived from general AI-sector framing, Microsoft's security-risk wording absent from its own quotations, and the omitted-current-respect answer in the paired control. The last answer was withheld in the normal packet but accepted when presented beside a corrected answer: batching context affected a material decision. That prevents treating the check as a reliable publication gate.

Additional review found a possible false rejection: a repeated Amazon report was withheld because generic praise for a counterparty stock was treated as materially new coverage. That framing is not a new Amazon event fact. The checker also accepted other previously recorded concerns, including “testing” substituted for cautious optimism and loss of a “possibly” qualification. The exact expected treatment of mild evaluative language remains a developer judgment; preserve that uncertainty rather than claiming an objective error rate.

The first eight calls cost **US$0.346585**. No result was promoted into the app.

## Controlled higher-reasoning comparison

A second frozen run uses the same eight packets, candidates, ordering, instructions, schema and selected expectations. Only reasoning effort changes from medium to high and the finite output ceiling from 6,000 to 9,000 tokens. This is a configuration comparison, not a pure single-variable effort experiment. Both use the same dated GPT-5.4 model and token prices. The [official model documentation](https://developers.openai.com/api/docs/models/gpt-5.4) supports high reasoning effort and lists the standard input/cached-input/output rates used by the ledger.

The new explicit profile is restricted to the evidence-check format and retains the old profiles unchanged. It uses the same cumulative US$20 ledger, persists a maximum before dispatch, charges returned usage including reasoning tokens once, and stops on ambiguous charges. No automatic retries or alternate allowance exist. The whole second batch has a conservative combined maximum of **US$1.808275**. Source before installing the profile is in `.local/backups/phase43-checker-profile-20261003T061852Z/`.

The completed results and final verification follow below.

## Completed comparison and decision

All eight high-effort requests completed and returned all 80 decisions. They matched **31 of 33** selected expectations, compared with **29 of 33** at medium effort. Both configurations retained all 23 selected positive controls. High effort caught eight of ten preselected withhold cases, versus six at medium. These are selected-case counts, not estimates of production precision or recall.

| Selected case | Medium matches | High matches |
| --- | ---: | ---: |
| Microsoft sentiment | 4 / 5 | 4 / 5 |
| NVIDIA sentiment | 4 / 5 | 5 / 5 |
| Amazon sentiment | 3 / 3 | 3 / 3 |
| Authored sentiment | 5 / 5 | 5 / 5 |
| Microsoft answer | 2 / 3 | 2 / 3 |
| Amazon answer | 4 / 4 | 4 / 4 |
| Authored answer | 4 / 4 | 4 / 4 |
| Paired authored readings | 3 / 4 | 4 / 4 |

Higher effort caught the NVIDIA target/direction mismatch and the paired omitted-current-respect answer. It also caught Amazon's 30-year-Treasury specificity absent from the selected quotes, an additional concern recorded before this run but not one of the 33 required labels. It still accepted the Microsoft stronger valuation wording and security-risk wording. It continued to miss other concerns about testing language and qualification.

It also withheld two Microsoft social reports because it treated the `reported_development` classification as asserting verified fact. In this route, that label describes what a social post reports; the source remains visibly social and is not promoted to independent confirmation. The stricter answer `reported` finding rule is a different contract. This is an example of a shared checker confusing adjacent product concepts. Both effort levels treated Amazon's generic counterparty-positive headline as materially new detail; automatically applying that decision could increase repeat alerts. These additional decisions prevent describing the selected positive-control result as proof of low false rejection.

**Neither configuration meets the intended publication gate.** Keep the checker disconnected from app publication and alerts. The retained module and its two bounded request profiles make the experiment reproducible, but do not establish an automatic fact verifier. No classifier or answer-generation profile was switched to high effort. A future intervention should narrow generated claims and preserve direct source extracts, and explicitly separate source-statement classification from verified-answer claims. Another generic prompt expansion or extra checker call is not justified by these results alone.

## Verification and accounting

The complete isolated suite passed **824 checks** with the actual retained SEC, expanded-company and HN-context corpus paths supplied. After adding an explicit selected-parent-type check and a reproducible high-effort request option, **73 focused checks** passed, including the two additional cases. These runs overlap. All automated provider traffic is mocked and test databases are disposable; the sixteen live requests above are a separate evaluation.

The final request builder reproduces both frozen request sets exactly. It rejects mismatched parent type, altered quotations, detached parents, incomplete verdict sets and unpriced reasoning variants. The high-effort profile is format-specific, preserves old reservation pricing and counts returned reasoning tokens within total output only once.

High effort cost **US$0.665275**, making this phase's sixteen requests **US$1.01186**. Cumulative confirmed spending is **US$9.931854** across **232** calls. The two historical ambiguous requests remain unresolved with their full **US$0.301565** maxima separately accounted; no new ambiguity or retry occurred. This leaves **US$9.766581** available under the same **US$20** cap.

Schema stays at 27. All protected research, saved-idea, answer, theme, alert and watch records remain unchanged. No source acquisition, product publication or watch activation occurred. The local app continues to respond. No frontend behavior changed, so this phase makes no new browser-journey claim. The overall implementation plan and participant validation remain incomplete.

## Five-perspective review

These are five perspectives applied by one agent, not independent consultants or participant evidence.

| Perspective | Assessment |
| --- | --- |
| Product | The core requirement is useful, faithful research and alerts. A checker that catches some errors but suppresses valid context is not ready to control that workflow. |
| Research | Frozen failures, positive controls and unchanged inputs support a narrow comparison. Selected agent-authored labels and one run per setting do not establish general accuracy or stability. |
| ML/data | Higher reasoning helps some omissions and direction judgments, but misses clause-level support and confuses route-specific labels. Separate those contracts and reduce unsupported synthesis before adding model stages. |
| Architecture | The evaluation boundary is reusable, bounded and separately metered. Keep it out of publication until usefulness is demonstrated; any later integration still needs lease, access, owner and history controls. |
| UX/business | Original sources remain available. No new automatic rejection should hide potentially useful evidence. These tests say nothing about willingness to pay or comprehension by students. |
