# Sentiment effectiveness experiment for the pitch

**Status update, 9 October 2026:** the owner chose published research to support the method for the current pitch, deferring execution of this experiment. Use [the research basis and slide wording](sentiment-research-basis.md) for the immediate deck. The original proposal below is retained for future validation; its schedule is not an active execution commitment.

Proposed protocol, 9 October 2026. Mentor presentation: Tuesday, 13 October 2026. Main pitch: approximately one month later. The immediate priority is a retrospective backtest. The sizes, thresholds and dates below are design choices, not completed results or established benchmarks.

Thesis should test whether its sentiment reading is correct, whether it relates to subsequent returns, and whether it helps people research a company. These are three different claims. A correctly labelled optimistic post can precede a falling share price; that is a failed directional signal, not necessarily a classification error. Conversely, a lucky return does not validate a wrong interpretation.

**Recommendation:** prepare a bounded historical pilot for Tuesday, report it as exploratory, and use the following month for independent annotation, a larger locked evaluation and fresh short-horizon observations. Keep the proposed 90-day comparison, alongside shorter horizons. Design the experiment to reveal a null or negative result as clearly as a positive one.

## What existing research supports

| Research | Relevant evidence | What to borrow and what it does not establish |
| --- | --- | --- |
| Paul Tetlock, 2007, *Giving Content to Investor Sentiment*, Journal of Finance. [Author manuscript](https://www.columbia.edu/~pt2238/papers/Tetlock_Media_Sentiment_JF.pdf) | Newspaper pessimism was associated with short-term market declines followed by reversals. | Examine several prespecified horizons. Positive tone need not imply persistent outperformance. This study concerns a newspaper column and an aggregate market index. |
| Hailiang Chen, Prabuddha De, Yu Jeffrey Hu and Byoung-Hyoun Hwang, 2014, *Wisdom of Crowds*, Review of Financial Studies. [Publisher abstract](https://academic.oup.com/rfs/article-abstract/27/5/1367/1581938) | Article and reader-comment opinions predicted subsequent returns and earnings surprises in the studied investment community. | Evaluate discussion separately from news. The publisher abstract supports the broad finding; this protocol does not claim to replicate its detailed specification or transfer its results to Reddit/Hacker News. |
| Alejandro Lopez-Lira and Yuehua Tang, *Can ChatGPT Forecast Stock Price Movements?*, first posted 2023, revised 2025; Journal of Financial Economics publication 2026. [Full author version](https://arxiv.org/html/2304.07619v6), [publisher](https://www.sciencedirect.com/science/article/pii/S0304405X26001066) | Post-cutoff headline assessments related to market reactions and subsequent drift; effects were stronger for smaller stocks and negative news. | Separate the initial reaction from returns available after processing. Their approximately 90% figure concerns portfolio-days and the non-tradable initial reaction, not individual-stock forecasting accuracy. Their price-impact task also differs from Thesis's source-tone task. |
| Dogu Araci, 2019, *FinBERT*, University of Amsterdam thesis / arXiv. [Paper](https://arxiv.org/abs/1908.10063) | Domain-adapted language modelling improved financial sentiment classification on the evaluated datasets. | Use FinBERT as a reproducible classification baseline. Classification performance is not a stock-return result. |
| Yixuan Tang and colleagues, 2023, *FinEntity*, EMNLP. [Paper and dataset links](https://aclanthology.org/2023.emnlp-main.956/) | Introduces financial entity sentiment annotations and benchmarks models including FinBERT and ChatGPT. | Judge sentiment toward the named company, not the whole document. Its three labels do not cover Thesis's mixed and unclear categories. |
| Tim Loughran and Bill McDonald, 2011, *When Is a Liability Not a Liability?*, Journal of Finance. [Publisher](https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.2010.01625.x) | General-purpose negative-word lists misclassified common financial language; the authors developed finance-specific lists. | Include a financial dictionary baseline; do not assume a generic positive/negative word count is a strong comparator. A dictionary remains limited on attribution and context. |
| Alejandro Lopez-Lira, Yuehua Tang and Mingyin Zhu, 2025, *The Memorization Problem*, working paper, revised December 2025. [Paper](https://arxiv.org/abs/2504.14765) | Models recalled historical financial information. Historical-boundary prompts and entity masking did not reliably remove this problem. | A current model reading old news is not automatically an out-of-sample forecast. Prefer outcomes after the frozen model's training period, and eventually predictions saved before outcomes occur. |

These studies support a testable hypothesis, not a generally proven trading method or a validation of Thesis. The practical design below is our proposal informed by those findings.

## The three experiments

| Question | Experiment | Main measurement | Claim it can support |
| --- | --- | --- | --- |
| Does Thesis interpret the supplied sources correctly? | Independently labelled, previously unused news and discussion | Company relevance, five-class macro-F1, unsupported directional labels and abstention | Quality of the sentiment reading on the stated sample |
| Does the reading contain information about later prices? | Locked historical replay with identical inputs for baselines | Subsequent benchmark-relative returns and association with sentiment | Historical predictive association within the tested population |
| Does it help a person research? | Randomised, counterbalanced comparison with the same sources | Evidence-task accuracy, material errors and completion time | Research usefulness for the tested users and tasks |

No one experiment establishes all three. A return association does not establish causation, achievable trading profit, or better user decisions.

## Immediate historical pilot

### Freeze the sample before examining outcomes

Aim for **12 companies × 12 weekly cutoffs = 144 company-week slots**, conditional on an adequate historical archive and affordable complete processing. Count actual eligible slots separately. Hundreds of articles in one company-week are not hundreds of independent return predictions.

Use Friday 18:00 America/New_York cutoffs from **17 April through 3 July 2026**, inclusive. Each input window contains the preceding seven calendar days. This leaves time for the proposed 90-calendar-day outcomes to mature before the mentor meeting. Resolve all entries and exits against an exchange calendar; retain UTC instants and local dates.

For selection, obtain a dated universe from before the first cutoff. Sample 12 issuers with a fixed recorded seed, stratified across at least four sectors, without using future returns. Freeze the issuer identifiers, share classes, sector mapping and benchmark mapping. Retain subsequently delisted or acquired names and their outcomes. If only today's familiar large-company list is available, describe the study as a convenience-sample case study with survivorship limitations. Do not call it representative of all stocks.

Reserve two earlier, separate dates for testing the data process. Exclude these from the final evaluation. Freeze code, selection rules, model snapshot, prompt, source grouping, score, horizon and outcome definitions before revealing the 12-week results. Record changes as a new study version. No tuning against disappointing test results.

### Establish what was actually available at each cutoff

The first deliverable is an availability table for every company, week and platform. Audit publication timestamps, exact historical text versions, parent comments, acquisition/archival timestamps and missing periods. A search result today bearing an old date is not sufficient historical evidence.

Use three explicit evidence categories:

- **Strict replay:** the exact text and required context were captured by Thesis or a verifiable contemporaneous archive before the cutoff. The archive route is an experimental import, not a claim that Thesis itself collected those records then.
- **Reconstructed retrospective sample:** publication is dated, but the original text/version or historical retrieval coverage cannot be demonstrated. Keep it separate and label the limitation.
- **Ineligible:** unknown original time, later edits without an original version, future parent context, denied access or incomplete required wording. Record the exclusion and reason.

Recent RSS feeds and a 30-day display do not establish a 90-day archive. In the current app, some Reddit timestamps are feed-update times; they cannot stand in for verified original publication times. If discussion history fails the audit, run and name a news-only study. Do not substitute current Reddit/HN posts or imply that the combined feature was validated.

The model receives only the exact eligible texts, company identity and permitted context at the cutoff. Later replies, edits, comparison articles, engagement totals and company facts cannot enter. Apply current full-source batching and source-access rules; do not select eight favourable examples or silently shorten a large eligible pool.

Retain the current price-guard boundary: a historical close used in classification must already satisfy the app's permitted capture-at-post-time rule. A price series retrieved today for measuring outcomes must never flow back into the classifier or fill a missing historical guard reference. Later verified prices may be used in the separately stored outcome table.

### Address model knowledge separately from source timing

Pin the exact deployed model identifier and document its training boundary, including known later training. The current reviewed method is sentiment v23, GPT-5.4 with low effort and a 12,000-token response ceiling. A model name or a request to “pretend it is April” does not prove absence of future knowledge.

Only call the return evaluation temporally out of sample when the evaluated information and outcome period follow a defensible frozen training boundary. If that boundary cannot be established for April–October 2026, the pilot remains a contamination-sensitive retrospective association study. An older checkpoint can form a separately labelled baseline; its results cannot be presented as performance of the current Thesis model. Masking company names is only a sensitivity check, not a cure. [Memorization study](https://arxiv.org/abs/2504.14765).

### Define the signal without changing the product

Retain Thesis's exact five labels and production grouping. Within each company-week and channel, count positive, negative, neutral, mixed and unclear groups. News is the primary channel; Reddit and Hacker News are separate secondary analyses. Do not merge their volumes into a single vote.

For this research only, define:

`S = (positive groups − negative groups) / (positive + negative + neutral + mixed groups)`

Require at least five interpretable groups, as in the current product. Otherwise abstain. Unclear and unrelated observations do not become neutral; record their separate counts. Neutral and mixed contribute zero net direction in this scalar encoding, while retaining their distinct labels and proportions in results. This score is neither an existing product feature nor a calibrated probability.

Also evaluate the actual displayed leaning: positive or negative only under the existing strict-majority rule; balanced and thin samples make no directional call. Preserve news/social distinctions and record every no-call. Do not tune the score, threshold or majority rule after inspecting returns.

### Measure what happens after the signal

Use the next regular-session opening price after the cutoff as the replay entry. This deliberately gives processing time and excludes the earlier price reaction. In a live test, processing must actually finish before that entry; otherwise delay entry using the same prespecified rule. A historical replay assumes that operational availability and must say so.

| Horizon | Exact convention | Role |
| --- | --- | --- |
| 1 trading session | Next-session open to that session's close | Secondary immediate follow-through |
| 5 trading sessions | Entry open to the fifth session's close, counting entry as session one | Primary short-horizon test |
| 20 trading sessions | Entry open to the twentieth session's close | Secondary persistence |
| 90 calendar days | Entry date plus 90 calendar days; use the first regular-session close on or after that date | The requested longer-horizon check |

Prespecify every horizon. Do not choose whichever looks best. Five sessions is a proposed primary endpoint because the cited literature gives reason to expect short-lived effects; it is not established as optimal for Thesis.

Compute shareholder total returns using consistent entry/exit prices, splits and cash distributions, with delisting/acquisition handling. Audit provider adjustment conventions rather than dividing an adjusted close by an unadjusted open. If only price returns can be verified, label them explicitly and keep the benchmark on the same basis. Outcomes not yet mature or unresolved remain missing, never zero.

`excess return = company return − prespecified sector benchmark return`

Use a fixed sector-index or sector-ETF mapping with the same timestamps and dividend basis; show broad-market-relative and raw returns as secondary views. Benchmark subtraction is not full risk adjustment or proof of alpha.

For illustration only: a company rising 8% while its benchmark rises 12% has **−4 percentage points** of excess return. An optimistic label did not anticipate outperformance merely because the stock went up.

### Compare against meaningful alternatives

Run identical historical samples through a pinned FinBERT checkpoint and a pinned Loughran–McDonald dictionary implementation. Fix their preprocessing and group aggregation before outcomes. Use the same target-company scope for an end-to-end comparison; additionally isolate tone classification on the common independently relevant subset. Disclose that these simpler models do not match all of Thesis's context or five-label capabilities. Never map mixed/unclear to neutral to improve the comparison.

Compare market association with **past 20-session benchmark-relative momentum**, computed only from prices available by the cutoff. Directional hit rates also need always-up and always-outperform baselines on exactly the same evaluated observations. A shuffled-signal diagnostic should shuffle within dates, and within sectors where sample size allows; it is a diagnostic, not a substitute for dependence-aware inference.

The key ablation is Thesis sentiment versus a price-only baseline. For the larger study, fit a simple price-only model using lagged return and volatility, then an otherwise identical model adding sentiment. Train only on earlier fully matured outcomes; purge overlapping outcome windows at time-split boundaries. Compare their untouched future-period prediction error. The tiny Tuesday pilot is insufficient to fit and validate a flexible forecasting model.

### Report uncertainty and every denominator

Primary statistic: for each eligible date, calculate Spearman rank correlation between news sentiment score and five-session excess return, then average across dates with equal date weights. Require at least six eligible companies and nonconstant scores and outcomes for a date; log omitted dates. This asks whether more positive readings tend to precede better relative performance without forcing every reading into a trade.

Show positive-leaning, balanced and negative-leaning mean excess returns as an understandable secondary display, with each group's company-week count. Report directional balanced accuracy on calls, positive and negative recall, and coverage across all 144 scheduled slots. No direction label predicts an exactly flat price; define zero-excess outcomes as ties and report them separately.

Do not treat posts, companies on the same market date or overlapping 90-day windows as independent. For a sufficiently long panel, use contiguous date-block resampling that retains all companies and spans at least the outcome overlap, plus issuer sensitivity checks. With only 12 weekly cutoffs, the 90-day windows overlap across nearly the whole pilot: a credible long-horizon significance claim is unavailable. Present those results descriptively. Even five-day confidence intervals from 12 date clusters are provisional; include leave-one-company and leave-one-week-out ranges.

Report all prespecified horizons and platforms. Treat secondary tests as exploratory; if making simultaneous inferential claims in the larger study, adjust for multiple comparisons. A null result is “not established on this sample,” not permission to reverse the hypothesis after the fact.

The pilot can demonstrate feasibility and a historical pattern. A stronger claim requires a larger untouched sample, defensible historical availability and model timing, stable effect sizes, uncertainty that excludes no improvement, and evidence that sentiment improves on price-only and simpler text baselines. Net trading-profit claims additionally require an executable portfolio rule, turnover, spreads, slippage, fees and short-borrow assumptions; this first study does not establish those.

## Independent interpretation check

Before Tuesday, target **100 previously unused originals**, with 20 used to clarify the annotation rubric and 80 locked for evaluation. Aim for 50 news, 25 Reddit and 25 HN items, subject to genuine availability; publish actual counts. This can use recent sources if the historical discussion archive is inadequate, but it is then a separate dataset from the return study.

For the main pitch, target 300 originals, with 60 for rubric development and 240 locked. These are practical pilot sizes, not a statistical-power guarantee. Select by company, source and time before reading model predictions. Keep all copies, shared stories and thread relatives in one split. Retain realistic ambiguity instead of selecting only easy sentiment sentences.

Two people independently annotate target-company relevance, the five sentiment labels, whose view is expressed, and the exact supporting wording. They must not see Thesis/FinBERT output or subsequent returns. Use an adjudicator for disagreements and report pre-adjudication agreement, class counts and unresolved ambiguity. An additional AI judge is not independent human ground truth. Record annotator roles and any involvement in developing the prompts.

Report relevance precision/recall, five-class macro-F1, per-class precision/recall, confusion counts, exact-evidence support and the proportion of unsupported positive/negative labels. Publish unclear/abstention rates. For FinBERT and dictionary comparisons, report a separate common three-class human-labelled subset with its denominator; keep mixed/unclear performance in the full Thesis evaluation. Pair comparisons on the same items and cluster uncertainty by story/thread.

The existing 45/50 reference replay and older local model comparisons belong in development history. They are not this held-out set, independent accuracy, or current-v23 live performance. [Price-guard evaluation](../reviews/2026-10-09/sentiment-price-guards.md), [local model comparison](local-sentiment-models.md).

## User usefulness study during the month

Plan a small randomised study with approximately 24 students/newer investors and four matched historical research tasks per person. Treat participants, not the 96 task completions, as the independent sample. Counterbalance task and interface order. Each person sees a source packet only once, with two tasks in each condition.

Both conditions provide the same dated sources, links, company context and navigation. The control offers a chronological source list and notes; the treatment adds Thesis sentiment and its evidence display. Keep unrelated AI features constant so the comparison measures the sentiment contribution.

Ask users to identify the target company's positive and negative evidence, distinguish an opinion from a reported fact, and justify what remains uncertain. Score against a rubric frozen by human reviewers before sessions. Measure accuracy and material attribution errors first; compare completion time while retaining non-completers and timeouts. Self-reported confidence is secondary. Do not grade users by whether they selected the stock that later rose.

A proposed practical target is 25% faster completion without more than a five-percentage-point loss of accuracy. These are planning thresholds; a small pilot may not establish that accuracy margin statistically. Show paired effects and uncertainty, including incomplete tasks. Recruitment and scheduling remain future work.

## Schedule and execution constraints

| Date | Deliverable |
| --- | --- |
| Friday, 9 October | Freeze the proposed questions and protocol; audit historical archive availability, model timing, annotation capacity and total run cost before dispatch. |
| Saturday, 10 October | Freeze issuer/sample manifests and independent annotation rubric; dry-run the process on excluded development dates. |
| Sunday, 11 October | If inputs and existing execution controls permit, generate and lock the complete pilot labels without revealing outcomes. Preserve all failed/unsent work. |
| Monday, 12 October | Join outcomes, run frozen comparisons, review errors and prepare one results slide plus a methods appendix. A second person checks the calculations and claim wording. |
| Tuesday, 13 October | Present measured pilot results if available; otherwise present the explicit protocol and feasibility findings. Never substitute illustrative numbers for results. |
| Following month | Expand independent labels and the untouched historical panel where feasible; run the user study and separately record fresh short-horizon predictions if enabled by the owner. |

Expansion target: approximately 30 companies and at least a year of weekly cutoffs, subject to archive and model-cutoff feasibility. Choose final size using variance and dependence estimates from development data, a minimum meaningful effect and a power calculation; do not promise statistical power from row counts. Reserve whole later periods for evaluation. A broad historical panel is still not equivalent to a live test.

Fresh predictions saved after this protocol can mature at one and five sessions before the main pitch; some early twenty-session outcomes may mature depending on the actual pitch date. A new 90-calendar-day outcome will take until January 2027 or later. No watch or scheduled collection is enabled by this plan.

Historical source access is not established by the current repository evidence. The latest recorded shared allowance also has a separate unresolved request and approximately US$4.49 available; this design does not reconcile or release that hold. Current figures require a fresh read before execution. The reviewed 120-source Broadcom run cost US$0.70617 in contributing calls; **144 equally costly reads would be approximately US$101.69**, solely an order-of-magnitude illustration. Source density, reuse, failures, annotation labour and data access could change the cost substantially. Actual dispatch requires a complete input plan and its maximum reservation under the existing ledger. [Recorded run and costs](../reviews/2026-10-09/sentiment-low-reasoning.md).

If the pilot is too large, reduce the prespecified company/date scope before opening outcomes and label the narrower study. Process every eligible original in the retained scope. If original historical text or model timing cannot be established, present a reconstructed case study or the interpretation check, with the corresponding limits. The Tuesday deadline does not turn an unavailable dataset into evidence.

## Pitch slide content

### Before results exist

**Testing whether source sentiment adds useful information**

- Historical pilot: target 12 companies across 12 weekly cutoffs, using dated news and eligible discussion.
- Freeze the reading first; compare with subsequent benchmark-relative performance at 1, 5 and 20 trading sessions and 90 calendar days.
- Compare with financial sentiment baselines and past price momentum; report coverage, uncertainty and failures.
- Validate interpretation with human labels and research usefulness with a controlled user study.

Footer: Proposed validation programme. No Thesis predictive-performance result is established yet.

### After the pilot is complete

Use a three-panel slide: human-label quality; subsequent returns for positive/balanced/negative readings; and coverage including no-calls. Populate only measured values. Put the primary five-session result first and show the 90-day comparison in the appendix or alongside it, even when it is weaker. Use a chart of group means and uncertainty instead of a hand-picked winning stock chart.

Required result sentence: “On [actual companies] over [dates], using [strict/reconstructed] historical inputs, [actual eligible slots]/[scheduled slots] produced usable readings. The five-session result was [effect and uncertainty] versus [baseline]. The 90-calendar-day comparison was [result]. This is an exploratory historical evaluation; [specific model/data limitation].”

If classification improves but returns do not, say so: “The study supports clearer interpretation of the tested sources; predictive return value remains unestablished.” A useful research product does not require a fabricated stock-picking success story.

## Records needed to reproduce the experiment

Keep the frozen protocol and code versions, source/parent text hashes and timestamps, universe/sector manifest, all scheduled and excluded slots, complete model requests and outputs, checked labels and original labels, annotation assignments/adjudications, baseline versions, outcome-price/corporate-action provenance, and every result table. Hash the labels before joining outcomes. Store historical inputs and future outcomes separately. Log every attempted specification and failure; retain zero, null and adverse results.

This document specifies the study. No backtest, new annotation, participant session, market-data collection or paid Thesis model run was performed in preparing it.
