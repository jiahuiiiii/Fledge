# Deus social integration — 8 October 2026

## Outcome

The user requested implementing Deus's social features because the existing collection was too sparse. Thesis now uses company-directed discovery, original-source verification, bounded thread replies and parent enrichment, exact duplicate handling and per-thread selection limits. These feed the existing cited sentiment analysis and alert pipeline. [Feature contract and Reddit application steps](../../features/deus-social-research.md).

The actual Broadcom run verified nine Hacker News comments, compared with one in the earlier workspace check. Eight fit the saved social sample, alongside eight news texts. Reddit remains unavailable: its public comment endpoint returned HTTP 403. The implementation stops further requests and explains the access requirement. An approved Reddit OAuth connector is still future work; the reply adapter's controlled tests are not evidence of live Reddit access.

## Investigation and changes

The original HN search was fuzzy: “Broadcom” returned unrelated “broadcast” matches ahead of relevant material. The new query quotes the company name and disables typo/prefix expansion. Search results identify items; the original HN API supplies their text. New discovery also checks company-related stories and bounded immediate replies, including replies which need their parent to establish relevance. Acquisition saves the immediate parent separately and checks its identity and date.

Deus's source aggregation/enrichment and platform-aware classifier contracts were inspected at revision `74d5aea8b0acf72e1851dfc841f9f1408e9e6609`. Its vocabulary/context guidance is adapted into `thesis-source-sentiment-17`. This is still one existing metered structured classifier, not a new multi-agent framework, numeric trading score or prediction engine. No FinBERT trial was promoted. No Nitter mirror or Reddit old-host fallback was copied.

Migration 039 adds company Reddit checks, a shared persistent request clock, immutable discussion-discovery metadata and withdrawals. All 92 pre-existing tables were identical across installation. Sources and selected parent text remain distinct; thread membership does not imply relevance or agreement. At most two selected items come from one recorded thread, and exact repeated wording counts once. This does not measure independent people.

The actual semantic test exposed a second collection issue: a complete critical sentence followed by a shortened URL was discarded by the ellipsis filter. Extraction now splits a standalone URL following sentence-ending punctuation into its own passage, retaining the complete preceding sentence exactly. Inline/incomplete ellipsis text is still excluded. Saved historical passages and analyses are not rewritten.

## Actual-source evaluation

Inputs, expected decisions and initial failures are preserved in `.local/live-tests/deus-social-phase80/`. Expectations are developer-authored, frozen before dispatch, and are not independent human ground truth. The same eight social cases were evaluated twice; they are not sixteen independent examples.

| Case type | Initial run | Retest after extraction repair |
| --- | --- | --- |
| Six single-tone expectations: two descriptions and four explicit criticisms | Five matched; one criticism was missing from model input | Six matched; the recovered criticism was labelled negative |
| Sarcastic quoted criticism followed by an implied financial benefit | Positive, within the predeclared multiple-acceptable set | Negative, outside that set; failure retained |
| Question about a company's counterparty affording chips | Unclear direction, relevant | Unclear relevance/direction; within the predeclared acceptable set |

Both accepted responses pass exact-source quotation and structured-output validation. Those checks do not establish semantic correctness. The retest kept all sixteen selected news/social sources and used the existing request-size fitting policy to omit additional news-comparison material. One intermediate oversized retest was rejected before reservation or dispatch; no fee was incurred for that attempt. No ceiling, model, reasoning profile or retry policy was raised.

The final reading is saved from the exact settled response and its original 03:10 UTC cutoff. It remains an AI interpretation, with the sarcastic-reply limitation recorded here. News event semantics were not independently revalidated by this social-focused evaluation. Prior sentiment, answer and alert interpretation limitations remain open. No watch was activated and no Telegram alert was sent.

Two paid calls cost **US$0.316390**. The original US$30 ledger now records **US$17.490652 confirmed**, **US$0.602490 historical maximum holds**, **US$11.906858 available**, 322 calls, and no new unresolved request. Historical holds remain intact.

## Verification

The final complete backend run passed **1,186 cases**, with 59 optional-corpus skips. The earlier complete run passed 1,182. An intermediate run after extraction changes passed 1,185 and had one intermittent market-refresh lease failure in the Meta catalogue case; the focused extraction/catalogue replay passed 50 with three optional-corpus skips. That failure did not recur in the final full run; its cause was not established. Preserve the failed run and do not describe it as a fixed production defect. Counts overlap and must not be added together.

The final acquisition/context/loading checks passed 66 cases. The frontend passed 27 checks and its production build. The isolated social-platform browser journey passed at 320, 390 and 1440px: separate platform labels, original-source inspection, source-coverage disclosures and disabled watches. Its older assertions were updated to open the current details disclosure and distinguish current-source preview from saved-source reading; the initial stale-selector failures remain in the evidence folder.

The actual Broadcom browser also shows nine candidates, eight saved interpretations and the approved-Reddit-access explanation, with monitoring still off. Desktop and phone checks found no horizontal overflow; screenshots were visually inspected. Reading the saved result triggered no new model call.

## Five-perspective review

This is one implementation review using five lenses, not five independent consultants.

- Product: investigation of a saved company now has useful actual discussion coverage. Do not position the sample as a market consensus or buy/sell signal.
- UX: existing Refresh controls and source windows remain. Missing access is distinct from no matches and neutral tone. The Reddit approval process still needs an external decision.
- Architecture: retain one schema, ledger and alert system. New immutable source/context metadata fits existing permission and withdrawal checks; failed access remains blocked across restart/reset.
- Analysis quality: the extraction loss has a narrow reproducible fix. Sarcasm/quoted-view attribution still fails in one actual case; broader alert and sentiment accuracy is not established.
- Operations/business: HN works without an added credential, but its audience and coverage are limited. Reddit access, permitted downstream AI use and possible commercial use require the owner's application and Reddit's decision. Monitoring still requires the local app and awake Mac.

Backup: `.local/backups/deus-social-phase80/`. Evidence: `.local/live-tests/deus-social-phase80/`. Remaining work includes an approved Reddit connection, broader prospective source/semantic testing, and participant validation. This phase does not implement every feature in the full Deus product or complete the overall roadmap.
