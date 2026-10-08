# Question-only sentiment evaluation — phase 58

3 October 2026. **Keep the installed v10 classifier.** Candidate v13 resolves the neutral-information-question instruction in a six-request evaluation, but produces a new company-relevance error and no net improvement on the original tone criteria. It is archived, not installed. Application source, frontend, schema 32, saved research and watch settings remain unchanged.

## Purpose and fixed scope

The previous bundled v12 experiment changed both question interpretation and temporal evidence selection. This experiment isolates only its question instruction: an intelligible, relevant information request without an expressed view is neutral; an ambiguous target or meaning remains unclear. Praise, criticism and conditional claims expressed as questions keep their direction. A parent's opinion must not become the child's stance.

The temporal instruction, original source packets, structured schema, medium/9,000-token GPT-5.4 profile, source quotas, comparison policy and cumulative US$20 ledger stay unchanged. The six packets and criteria were frozen before dispatch. This is a narrower, separately declared hypothesis; it does not change the failed phase53 criteria or promote v12. [Official model guidance](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-5.4) informed keeping the change small and testing a measured failure.

The adoption gate required six valid structures, exact quotations, at least 31/34 original tone matches with no newly failed original criterion, all ten authored reply tones, three selected information questions becoming neutral, retention of current/earlier evidence, and review of attribution. The older exact temporal and Meta scorecards remain reported separately. These are known developer cases, not an unseen or independently labelled benchmark.

## Results

| Packet | Selected tones matched | Cost |
| --- | ---: | ---: |
| Microsoft, 16 items | 9/10 | US$0.1489075 |
| NVIDIA, 16 items | 9/11 | US$0.1530350 |
| Amazon, 10 items | 4/4 | US$0.1081250 |
| Original authored, 9 items | 8/9 | US$0.0459300 |
| Retained Meta, 12 items | 8/9 | US$0.1300075 |
| Authored replies, 10 items | 10/10 | US$0.0679950 |

All six responses complete and validate. Across 73 items and seven news comparisons, 187 quotation associations match their original source: 139 main, five earlier, 21 parent and 22 paired-comparison excerpts. Structural/source validation does not establish the labels' meaning.

The two retained NVIDIA benchmark/security information questions and the original authored benchmark question become neutral. All ten authored reply tones pass, including praise/criticism inside questions, quoted disagreement, simultaneous mixed views and ambiguous sarcasm. However, NVIDIA's generic portfolio-allocation post changes from unrelated/unclear to relevant/neutral. Its ticker list does not establish a company-specific view; counting it alters the sample. This is a newly failed original criterion. The original selected score is **30/34**, equal to v10, below the frozen minimum and with a regression. Do not install the candidate.

The existing Microsoft conditional margin warning, NVIDIA promotional buyback headline and authored patching-practice disagreements remain. Meta's penalty-plus-share-momentum item is negative against the existing mixed criterion. These partly interpretive criteria are not externally established truth and were not relabelled to improve the score.

Manual review covered changed original decisions and the Meta/reply controls. An unscored Amazon contract announcement changes from neutral to positive, using “bolster”/“secure” wording; this is additional framing sensitivity, not evidence of financial gain. Microsoft study commentary becomes neutral without inventing a company investment stance. Meta's counterparty gains/debt remain attributed to the counterparty; the conditional AMD question retains the poster's favourable interpretation. Source fragments are not reconstructed. New coverage descriptions remain code-written with separate original excerpts.

Exact original temporal separation becomes 2/3: the two authored cases separate correctly, but the real NVIDIA case now includes earlier context in its main selection. Both new reply transitions separate correctly. All retain the current and earlier wording. This variation is recorded; the question-only change did not establish reliable role separation. A single changed-prompt run cannot disentangle prompt effects from model variability.

## Correction to an earlier review

Direct comparison of both raw and rendered phase47/v10 and phase53/v12 responses shows identical original temporal selections: NVIDIA uses current p2/earlier p1; both original authored cases include p1 and p2 in the main selection. The earlier phase53 prose incorrectly described a regression in the authored distrust case and a new improvement in NVIDIA. That writing error is corrected in the review, implementation status and AGENTS guide. Phase52's description of the original authored baseline count is also corrected from one separately selected case to zero.

No saved response, original criteria or score is changed. The frozen phase53 adoption gate still failed its Meta and new temporal criteria. The raw-call/result hashes and exact selections are retained in `thesis-phase58-baseline-correction.json`.

## Verification and preservation

The candidate passes **1,049 backend checks** with all six retained corpora, plus an overlapping 92-check focused run with one optional-corpus skip; that corpus runs in the full suite. The first focused command named a nonexistent test file and ran no tests; its log is retained with the corrected run. These are mocked-provider software checks, not sentiment accuracy. There is no frontend change; the prior verified build remains in use, without repeating browser/build checks for a rejected prompt candidate.

Evidence is in `.local/live-tests/sentiment-questions-20261003T141604Z/`: frozen requests and criteria, all six complete paid responses, rendered results, quote/decision audits, candidate/baseline source, test logs and final verification. Staging is restored to installed v10 after archiving. Earlier database rows are compared after excluding only the six new paid calls and their dispatch rows; ordinary background cursor advancement is separate. All watches and weekly schedules remain off. No source acquisition, research publication, user-definition edit or alert publication occurs. Documentation changes retain their pre-edit copies. The installed app remains available.

Phase spending is **US$0.6540000**. The same US$20 ledger records **US$14.8568245 confirmed + US$0.301565 historical maximum accounting**, leaving **US$4.8416105**, across 292 calls with no new blocker. The two historical charges remain unresolved under their separate maximum accounting; they are not reported as settled costs. No request is retried.

## Five-perspective review

These are five perspectives applied by one coding agent, not independent consultants or participant research.

| Perspective | Finding and next action |
| --- | --- |
| Product | Clear information requests improve, but a generic ticker list entering the company sample is a material regression. Retain v10 and prioritize relevance before further tone tuning. |
| Research quality | Preserve the failed gate, ambiguous framing, changed unscored result and exact baseline correction. Known developer cases and one run do not establish broad accuracy or a causal prompt improvement. |
| UX | Existing exact source excerpts and earlier-method labels remain useful for scrutiny. Do not make the app display the candidate as an improvement or imply that neutral means verified or favourable. |
| Architecture | No new model, checker, schema or dependency is justified by this outcome. Candidate source and responses remain separate from the app; prior research and request identities remain intact. |
| Business | The additional 65 cents rules out this correction as a safe standalone upgrade. Further budget should support broader alert/relevance evidence and the pitch workflow, rather than another small rewrite of the same tone prompt. |

The implementation goal remains active. Next substantive work should evaluate target-company relevance and alert precision across a wider fixed source set, with specific reasons for inclusion/exclusion and existing positive controls. Avoid another small tone-prompt variation on these same packets. Source continuity, remaining fundamentals/expectations, standalone-answer errors and participant value are still unresolved; no amount of internal consultant-style review establishes demand or willingness to pay.
