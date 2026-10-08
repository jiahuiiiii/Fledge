# Separate news and social discussion samples

**Current, 8 October 2026:** company research uses the [Deus social discovery/enrichment flow](deus-social-research.md). It replaces the original twelve-result HN query and general Reddit-feed scan described below. The current action is **Refresh & analyse**, with 1/7/30-day discussion windows; Reddit collection is blocked after an actual HTTP 403 until an approved connection is available. The older sections retain the development history, not the current acquisition limits.

The local pitch workflow now adds Hacker News comments alongside Finnhub company news and Deus-derived Reddit RSS. It reuses the existing structured classifier, citations, paid ledger, immutable samples and Kestrel-derived review/alert flow. No second model service, database or agent framework is introduced.

Choose **Refresh social posts**, then **Analyse sentiment**. Company news, Reddit discussion and Hacker News have separate tabs. Original sources shows the exact selected text without AI labels. Source coverage explains checked time, exclusions and failures. Opt-in company watches refresh both discussion adapters for the chosen company; private saved-reasoning checks use the same eligible cited sources. Opening these views makes no provider request and installation enables no watch.

## Acquisition contract

HN discovery uses one company-name query, newest first, for up to twelve comments published in the last seven days. Search hits are identifiers only: text is fetched from the original HN item API. Up to eight retained recent comments are also rechecked even when no longer in search. At most twenty original-item requests occur per company refresh. One persisted global clock spaces requests by one second; per-company refresh has a fifteen-minute cooldown and fenced five-minute lease. Responses have a two-megabyte bound, short timeout, fixed hosts and no HTTP retry, alternate-host workaround or account credentials. Original-API HTTP errors stop remaining item requests. A failed request retains older evidence with visible coverage failure.

Only original comment bodies mentioning the target are eligible; company mentions are candidates, not a relevance verdict. Personal job/resume ads, future/older/oversized/incomplete items are excluded. This is a heuristic, not exhaustive entity or personal-information detection. Authors are hashed; popularity never weights sentiment. Titles use a generic comment label instead of borrowing a parent headline. The automatic sample and AI input exclude parent/thread context, so ambiguity remains a reason for an unclear result. The original-source dialog can explicitly retrieve one parent for separate reading; see phase 32 below. The selected sample is tech-community discussion, not retail-investor consensus or verified company facts.

Confirmed deleted/dead items receive an immutable withdrawal marker. A consumed withdrawn source withholds its complete derived sentiment and linked private results. There is no claim of instantaneous deletion detection: only bounded retained/discovered comments are checked. Search/API outages, finite lookback, lexical query choice and uncollected aliases/comments limit coverage.

## Counts, history and alerts

A request keeps the existing eight-news/eight-social, sixteen-item and byte limits. Social selection alternates newest Reddit and HN items, filling unused capacity from the available platform. Code counts each platform separately, deduplicating substantive text within it. There is no combined directional social score once HN is present. History retains original outputs and displays platform readings separately; adding a source does not rewrite older samples.

Counting policy is `sentiment-coverage-5`; the phase-29 classifier prompt was `thesis-source-sentiment-7` and the model is unchanged. A company sentiment reversal compares the same platform and compatible recorded method, with new eligible text and at least three interpretable groups on both sides. Missing/added platforms alone do not make a reversal. Multiple eligible reversals remain one grouped publication. Private relevance still tests the exact saved question/reasoning and never receives aggregate sentiment as evidence. Baseline, seen-content, no-automatic-paid-retry and source-withholding rules remain in force.

Migration 021 adds HN acquisition state/clock/withdrawals and permits the new platform in immutable social records. Existing rows, financial monitoring and private saved state are preserved.

## Source longevity and reuse

[Reddit's official announcement](https://www.reddit.com/r/modnews/comments/1wubgvt/continuing_our_infrastructure_updates_whats/) says RSS support ends on 13 November 2026. Coverage shows that notice; the production adapter stops making RSS requests on that date. Retained dated posts remain historical evidence. General Reddit investor-discussion continuity needs a separately supported source; HN is an additional audience, not a substitute investor population.

The [official HN API](https://github.com/HackerNews/API) documents original items, comments and deleted/dead states. [Algolia's open-source HN Search](https://github.com/algolia/hn-search) supplies discovery; its repository is archived, although the public search worked in this phase's actual probes. This adapter uses those APIs, without importing the old Rails application or claiming it is actively maintained. See the phase review for retained actual-case evidence and limitations.

## Output-bound correction from an actual case

The initial Microsoft multi-source request reached its 6,000-token output cap and returned `incomplete`. Its usage/charge and failed rendering are retained; no partial product analysis or automatic retry was published. A separate priced request profile permits exactly 9,000 output tokens for `source_sentiment` only, retaining medium reasoning and the same GPT-5.4 snapshot/rates. Other research requests and all historical profiles remain at their original bounds. The full maximum is reserved in the original cumulative ledger before dispatch; explicit retests have distinct request identities.

[OpenAI's reasoning guide](https://developers.openai.com/api/docs/guides/reasoning) explains that reasoning and visible output share the token limit. The [GPT-5.4 model page](https://developers.openai.com/api/docs/models/gpt-5.4) was checked for the unchanged US$2.50/US$0.25/US$15 input/cached/output rates per million tokens. This is a bounded engineering adjustment, not a reliability guarantee for every future sample.

The next completed response exposed a source-label mismatch. Prompt `thesis-source-sentiment-6` and the dynamic response schema now limit news-link identifiers to the supplied `item_N`/`prior_N` labels; social and storage UUID references are excluded. Existing exact-quotation, same-source and chronological checks remain authoritative. This changes the request identity and method warning; historical responses are never silently repaired or relabelled.

The final prompt also distinguishes a current opinion from an explicitly superseded past stance. Five wholly authored contrasts and unchanged actual-source retests are recorded separately; this is a targeted development correction, not population validation.

## Optional original-parent inspection — phase 32

The classifier still uses comment-only inputs. The source dialog now separately offers **Load original conversation**, an explicit bounded check of the original comment and its immediate parent. Cached context is read-only, dated and clearly separated from the saved AI label. No automatic reanalysis or sentiment vote is introduced. [Contract and evidence](social-conversation-context.md).

## Saved context in new analyses — phase 35

New sentiment analyses may use up to four verified saved parents checked within 24 hours. Old labels remain unchanged; parents are separately cited and never add sentiment votes. The new prompt is `thesis-source-sentiment-8`. The comment-only descriptions above describe phase 29/32. Other research models keep their own inputs. [Current contract](context-aware-sentiment.md).
