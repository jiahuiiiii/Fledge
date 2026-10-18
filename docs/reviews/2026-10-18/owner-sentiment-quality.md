# Owner sentiment review — 18 October 2026

All 50 owner answers were supplied through an explicit local file path. The
fingerprint, complete case IDs, valid relevance/tone values and independent-owner
confirmation match the frozen review. The original file is unchanged; an exact
private copy and input hashes are retained. Raw exports are excluded from Git.
No answer is inferred from browser storage or another file location.

## Result

| Check | Result | Gate |
| --- | --- | --- |
| Owner answers received | 50/50 | Complete |
| Exact relevance-and-tone agreement | 24/50 (48%) | **Fails** required 40/50 (80%) |
| Relevance agreement alone | 38/50 (76%) | Diagnostic; no substitute for the joint gate |
| Tone agreement alone | 29/50 (58%) | Diagnostic; no substitute for the joint gate |
| Fixed hard cases | 4/6 | Passes the separate required 4/6 |
| Combined label-quality gate | Failed | Phase 5 remains unfinished |

| Source group | Exact | Relevance | Tone |
| --- | --- | --- | --- |
| 25 news excerpts | 14/25 (56%) | 20/25 (80%) | 16/25 (64%) |
| 25 discussion excerpts | 10/25 (40%) | 18/25 (72%) | 13/25 (52%) |

There are 26 disagreements: 14 on tone only, five on relevance only and seven
on both. All 50 cases stay in the denominator. No labels, predictions, thresholds
or scoring rules are changed to improve the result. All non-relevant owner
answers use unclear tone; the file does not violate that label convention.

This measures agreement with one person's interpretation under the supplied
rubric, not adjudicated objective accuracy, investment usefulness or return
prediction. The owner received general rubric clarification while labelling,
without individual AI predictions or case-specific recommended labels.
The earlier full-prompt pipeline has not been evaluated against these same
50 owner labels with identical evidence. This failed gate alone cannot identify
whether the smaller prompt regressed, the older baseline also disagrees, or the
rubric/input limits dominate. No comparative regression claim is made.

## Same evidence and saved answers

The exact frozen tone plan still validates against the current task contract.
All 56 saved request inputs are checked, including the two inherited earlier
requests; source text and required context match. All 56 raw answers revalidate
for free, reproduce their saved rendered predictions with zero repairs and
retain the original 4/6 hard-case result. The scored 50-prediction envelope
matches those validated results exactly.

All 50 owner/AI evidence projections match. Seventeen cases contain saved parent
or topic context, and all 17 contexts are also present in the AI inputs. The
observed disagreement is therefore not explained by withholding from the AI a
topic shown to the owner. Both readers may still lack verified parents, images
or complete articles. No missing context is silently reconstructed.

The context-bearing cases have six exact matches out of 17; the other cases
have 18/33. These groups differ in source content and difficulty. This is not a
controlled comparison and does not show that supplying context harms quality.

## Owner feedback and interpretation gaps

The owner reports that the saved discussion topic is often necessary to make a
judgment. Treat required topic context as evidence, not optional decoration. The
owner also questions whether short news excerpts represent the full story:
ten of the 25 news cases contain only one saved body passage. The review shows
all supplied passages but does not establish full-article understanding.

A first reading of the disagreements identifies hypotheses for review, not new
corrected labels:

- **Market context versus company relevance.** Several broad-market/sector items
  are useful to the owner as company context, while the model's current rubric
  requires an explicit target-company relationship. Useful market context and
  company-specific tone need distinct handling; neither market-wide pessimism
  nor optimism should automatically become every watched company's sentiment.
- **Reply stance versus topic stance.** Short acknowledgements, jokes and an
  image-link-only reply can be interpreted through the topic, but a topic's
  attitude does not necessarily establish the reply author's attitude. Explicit
  company/product questions also merit checking for overly cautious relevance.
- **Quoted remarks versus the author's evaluation.** Several differences involve
  quoted criticism, a response defending a company, or a prospective entry price.
  The target, speaker, timeframe and expressed stance require adjudication.
- **Neutral, unclear and mixed.** The model uses ten neutral labels versus the
  owner's five and two mixed versus seven. Some differences concern whether a
  short excerpt states an outcome, merely describes an action or supports no
  reliable interpretation. Counts alone do not decide whose judgment is right.

Do not classify all 26 disagreements as model mistakes or silently relabel the
owner's answers. Keep this original result as the baseline. Clarify the intended
rubric and review ambiguous examples before changing the prompt. If these labels
inform development, the same cases cannot later be presented as an untouched
holdout; any retest is explicitly a same-set development result.

## Focused ambiguity review — 18 October 2026

A free assistant review covers the eight disagreements entirely within
mixed/neutral/unclear and the three positive-versus-negative disagreements.
These are 11 selected cases, not a representative new test. The assessments
below are provisional hypotheses under the existing written contract, not
adjudicated replacement labels or a revised score.

| Review focus | Cases | Finding |
| --- | --- | --- |
| Priority model investigations | 15, 40 | An explicit company-product question was treated as unclear relevance; a two-company comparison received target-specific tone despite unnamed clause attribution. Check over-abstention and unsupported attribution. |
| Insufficient meaning or evidence | 01, 17, 28, 38 | Target remarks are absent from a news excerpt; an image-only reply has no supplied image; slang and a short joke leave meaning uncertain. Readable surrounding text alone does not establish the target's tone. |
| Speaker and timeframe | 06, 20, 48 | A reply's own conclusion can differ from a quotation/topic. Conditional future buying and present price caution can support different readings. Preserve the expressed speaker and timeframe before assigning direction. |
| Rubric boundaries | 44, 49 | Useful macro context need not be company-specific sentiment. Uncertainty about a statement's truth is different from uncertainty about the tone of an intelligible description. |

Two cases are priorities for investigating model behavior; this is not a count
of proven model errors. The other nine are not declared correct model answers.
In particular, the conditional-entry example needs a clearer policy before
either positive or negative becomes an authoritative reference.

The practical distinction remains: **neutral** is intelligible relevant text
without expressed direction; **unclear** means the supplied evidence cannot
support a reliable interpretation; **mixed** needs supported opposing current
framing about the target. A topic may resolve a reply's reference but cannot
supply the reply author's attitude. Broad-market context can be useful without
becoming every company's sentiment. These summarize the current contract;
no prompt, scoring convention or production behavior changes in this review.

Next development should clarify these boundaries and add authored offline
examples for explicit product questions, multi-company attribution and
conditional entry-price comments. Original owner answers remain intact; no
repeat of all 50 labels is needed now. A later same-set retest must be labelled
development evidence. Release confidence still needs a fresh held-out review
under a stable rubric; this audit does not authorize another paid campaign.

Private `triage-11.json` retains each original pair and a provisional rationale.
Checks confirm 11 unique reviewed cases, with original export, predictions,
blind-review page and protected CSS hashes unchanged. Original exact agreement
remains **24/50 (48%)**, and phase 5 remains unfinished. Incremental cost is
**US$0**, with no new model/source request, live change or restart. The earlier
60 passing tests still describe the evaluation machinery; they are not a new
test of these semantic judgments.

## Artifacts and limits

Private evidence is in
`.local/live-tests/redesign-phase-5-20261018/owner-score-v1/`: the exact received
answers, score, full disagreements, confusion counts, free revalidation and a
read-only `comparison.html` with original topic/reply evidence and both choices
together. It shows 26 differences without grading either side as automatically
correct. The original review page, manifest and predictions are unchanged.

The comparison has no scripts, remote images, network connections or editing
controls. Static structure is checked. Browser visual verification is not
claimed: the browser tool rejects local-file navigation. No alternate browser
surface or local-server workaround is used.

Offline scorer/context/task suites: **60 passed**, using disposable databases and
invented test responses, with no network/provider requests. These tests verify
the evaluation machinery and do not replace the failed semantic quality result.
No production behavior changed. Git ignore rules now protect private owner-label
exports; raw answers and source text are not committed.

Incremental scoring/revalidation cost **US$0**. The earlier paid quality campaign
remains US$0.445405 with zero unresolved holds; no new paid test or retry occurs.
No source collection, saved-research/preference/settings/schema change,
installation, app/DB restart or Telegram send is performed. Protected CSS and
the blind review page remain exact. The separate company-news noise gate still
fails at 2/18 (11.11%); this review does not supersede that result or authorize
activation. Live observation and new-delivery approvals remain separate.
