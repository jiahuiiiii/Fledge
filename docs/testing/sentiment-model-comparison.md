# Sentiment model comparison and live trials — 16–17 October 2026

This is the record of the model and pipeline experiments run on 16–17 October 2026 (GPT models and an OpenRouter DeepSeek run added on 17 October), after the owner reported that the 14–15 October tech sell-off produced no useful alert and that the pipeline felt slow. It covers four offline comparisons, one live model switch, an unplanned outage and a duplicate-alert investigation. The explanation section at the end compares four possible setups; the follow-up work is in the [alert redesign plan](../development/sentiment-alert-redesign-plan.md).

All scripts are in [`experiments/soclaas_replay/`](../../experiments/soclaas_replay/). Raw requests, answers and summaries are under `.local/live-tests/soclaas-avgo-20261016/`, `.local/live-tests/fair-meta-20261016/` and `.local/live-tests/sonnet-switch-20261016/` (not in Git). Nothing in these experiments was saved as an app reading, alert or watch result, except the live trial in section 5.

## 1. Starting point: how the pipeline behaved

Measured from the app database over 13–16 October (237 watch checks, 11 hourly watches).

| What | Finding |
| --- | --- |
| Alert trigger | Text only. A watch alerts on a tone flip or a new article labelled `reported_event` with adverse/mixed impact. **Price never enters the watch**, and the prompt tells the model to ignore stock-trading signals. |
| The sell-off | NVDA −3.2% (14 Oct) and −1.8% (15 Oct); AMZN and GOOGL −1.7%. No timely alert. The first sell-off alert came about 1.5 days later (16 Oct 14:31 SGT), worded like every other "adverse reporting" alert. |
| Noise | Opinion and comparison listicles passed as `reported_event`, e.g. "Is Amazon Stock Poised to Gain…?", "How Much Of Qualcomm Stock Rides On One Business?", "Broadcom vs. SK Hynix…". |
| Check duration | Median 202 s, 90th percentile 549 s, worst 974 s. |
| Where the time goes | Source collection median 238 s; AI reading median about 10 s. **Reddit averaged 224 s per company** (30 s gap between requests, shared by all watches). News feeds were under 1 s each. |
| Failures | 38 of 237 checks (16%) failed at the AI step; 24 more "stopped" checks hung for a median of 31 minutes. |
| Prompt size | Per batch of 8 sources: system prompt 16,294 characters, output schema 78,860 characters, sources 10,878 characters (call `c54d6a22…`, 16 Oct 14:49). A saved copy is in `.local/research/sentiment-prompt-20261016.md`. |
| Labels | Already incremental: only new or changed sources are sent to the AI (e.g. 129 new, 538 reused). Fetching is not incremental: every source re-asks for the full 7-day window each hour. |
| Cost | Claude Opus 5.5 main reading: US$27.90 over 3 days (397 calls), about US$9/day at 11 watches. |

## 2. Experiment 1 — DeepSeek V4.1 Flash on saved AVGO batches

**Question:** can the free NUS SOC LaaS model `x-test-2` (the server reports `deepseek-v4.1-flash`) replace Claude?

**Method.** The 15 most recent AVGO batches that Opus had read (saved 14 Oct 10:18 – 16 Oct 14:41 SGT, 64 sources) were sent unchanged to `https://soclaas-api.comp.nus.edu.sg/v1` with the identical system prompt and sources. Round 1 used the existing DeepSeek translation in [`thesis/providers/deepseek.py`](../../thesis/providers/deepseek.py): JSON mode, schema pasted into the instructions, 12,000-token limit. Answers were checked with the app's rules ([`replay.py`](../../experiments/soclaas_replay/replay.py)). Two workers, no retries.

**Round 2 probes** (tiny test requests): the server **enforces** a strict `json_schema` response format, even when the prompt asks for another shape. `reasoning_effort: "low"` did not reduce thinking; `"none"` turned thinking off.

| Setup | Batches passing | Median / max time | Output tokens (thinking) | Tone agreement with Opus | Relevance agreement |
| --- | --- | --- | --- | --- | --- |
| Opus (saved answers) | 15/15 † | 5.7 s / 8.7 s | about 380 | — | — |
| Round 1: JSON mode | 11/15 | 39.3 s / 59.9 s | 7,546 (6,955) | 77% | 90% |
| Round 2a: strict schema, effort low, 24k limit | 12/15 | 49.2 s / 88.1 s | 8,259 (7,862) | 71% | 84% |
| Round 2b: strict schema, thinking off | 7/15 | 2.1 s / 3.0 s | 305 (0) | 41% | 100% (22 sources) |

† Biased by construction: only answers that had already passed were replayed.

**Failures.** Round 1: 2 ran out of tokens, 1 broken JSON, 1 put news-only event fields on Reddit posts. Strict schema removed all of these; the remaining round 2a failures were consistency rules a schema can't express (e.g. "neutral" with an "unclear" basis). Thinking off labelled 17 of 22 sources neutral.

**Proofreading.** DeepSeek was more cautious (20 neutral against Opus's 12). It handled opinion pieces and product launches by the rules more often; it guessed on vague replies. One earlier verdict was corrected when the Reddit thread topic was considered: "It could mean the stock will fall regardless" (topic: Anthropic's Q3 and AVGO) is negative, so DeepSeek was right and Opus too cautious.

## 3. Experiment 2 — fair test on fresh META data: Opus vs DeepSeek

**Method.** On 16 Oct 15:52 SGT the app's normal collectors fetched fresh META sources (Finnhub returned 25 reports; publisher feeds 1 match; Alpha Vantage paused; X off; **Reddit plus Hacker News took 191.5 s**). The 7-day packet had 355 eligible sources; the newest 128 were planned into batches, and the first 16 batches (119 sources) went to both models at the same time with byte-identical requests ([`fair_compare.py`](../../experiments/soclaas_replay/fair_compare.py)). Opus went through the app's normal spending ledger. DeepSeek used strict schema, default thinking, 24,000-token limit. Both answers were judged by the app's real validator (`sentiment.render`).

| | Opus 5.5 | DeepSeek V4.1 Flash |
| --- | --- | --- |
| Batches passing | **15/16** | 9/16 |
| If single bad items were dropped | 16/16 (1 item lost) | 15/16 (13 items lost) |
| Median / max time | 7.2 s / 9.2 s | 64.1 s / 99.0 s |
| Output tokens | about 790 | about 14,115 |
| Cost | US$1.229 | free (NUS) |

Opus's one failure: event fields on a Reddit post. DeepSeek's seven: 3 tone/basis mismatches, 2 event fields on non-events, 1 directional label on an unrelated item, 1 missing label, 1 out of tokens. Agreement on the 110 sources both labelled: relevance 75%, tone 75%, event type 82%, impact 98%. Neither found an adverse-news alert candidate.

## 4. Experiment 3 — Sonnet, Haiku and GPT models on the same META batches

**Method.** The 16 saved META requests were sent again, changing only the model name ([`fair_claude.py`](../../experiments/soclaas_replay/fair_claude.py)). Rebuilding the batches from the database was rejected because META's saved discussion data had changed after a later watch run (only 1 of 16 rebuilt requests matched), so the saved bodies were used directly. The app only allows its configured models, so Sonnet was enabled inside the test process only; the first attempt was refused before sending and cost nothing. Answers were judged by the replay checker, which applies the same rules the app validator raised in this run.

On 17 October the same 16 requests went to four OpenAI models ([`fair_openai.py`](../../experiments/soclaas_replay/fair_openai.py)) at low reasoning effort and a 12,000-token limit, the app's production settings. GPT-5.4 used the app's own price profile; GPT-5.5, GPT-5.4 mini and GPT-5.4 nano got evaluation price profiles at OpenAI's official rates (per million tokens: GPT-5.5 US$5 input / US$30 output, mini US$0.75 / US$4.50, nano US$0.20 / US$1.25), inside the test process only. The newer GPT-5.6 models were available but left out because no official price could be confirmed.

Also on 17 October, DeepSeek V4.1 Flash was run on the same 16 requests through OpenRouter ([`fair_openrouter.py`](../../experiments/soclaas_replay/fair_openrouter.py)), to test a host other than NUS. OpenRouter listed 35 hosts for the model, from US$0.03 to US$0.60 per million input tokens and at different precisions; DeepSeek's own host there did not support strict schema. The run was pinned to **DeepInfra (fp8)**, US$0.14 / US$0.42 per million input / output tokens, with no fallbacks, strict schema, default thinking and a 24,000-token limit. Every call stayed on that host. OpenRouter is not part of the app's spending ledger, so the script had a hard US$1 cap and recorded OpenRouter's reported actual cost per call.

| | Pass (no repair) | With item-level repair | Median / max time | Output tokens | Cost for 16 batches |
| --- | --- | --- | --- | --- | --- |
| Opus 5.5 | 15/16 | 16/16 (1 item) | 7.2 s / 9.2 s | about 790 | US$1.229 |
| **Sonnet 5.5** | **16/16** | 16/16 | **5.5 s / 6.7 s** | about 782 | US$0.640 |
| Haiku 5.5 | 12/16 | 16/16 (9 items) | 15.0 s / 20.2 s | about 3,468 | US$0.053 |
| GPT-5.5 | **16/16** | 16/16 | 11.2 s / 16.0 s | about 950 | US$1.224 |
| GPT-5.4 (current) | **16/16** | 16/16 | 18.4 s / 32.6 s | about 1,424 | US$0.728 |
| GPT-5.4 mini | 3/16 | 16/16 (36 items) | 6.2 s / 9.5 s | about 1,256 | US$0.210 |
| GPT-5.4 nano | 5/16 | 16/16 (24 items) | 8.8 s / 12.0 s | about 1,290 | US$0.058 |
| DeepSeek V4.1 Flash (NUS) | 9/16 | 15/16 (13 items) | 64.1 s / 99.0 s | about 14,115 | free (NUS) |
| DeepSeek V4.1 Flash (OpenRouter, DeepInfra fp8) | 13/16 | 16/16 (3 items) | 95.4 s / 128.8 s | about 12,426 | **US$0.084 (actual)** |

**Agreement with Opus** (sources both labelled):

| | n | Relevance | Tone | Event type | Impact |
| --- | --- | --- | --- | --- | --- |
| Sonnet 5.5 | 119 | 91% | 81% | 91% | 97% |
| Haiku 5.5 | 119 | 78% | 80% | 84% | 98% |
| GPT-5.5 | 119 | 87% | 72% | 81% | 97% |
| GPT-5.4 | 119 | 81% | 80% | 84% | 97% |
| GPT-5.4 mini | 119 | 73% | 65% | 76% | 93% |
| GPT-5.4 nano | 118 | 78% | 71% | 76% | 91% |
| DeepSeek V4.1 Flash (NUS) | 110 | 75% | 75% | 82% | 98% |
| DeepSeek V4.1 Flash (OpenRouter) | 119 | 76% | 75% | 81% | 98% |

**Six proofread cases** (the developer's reading of the source text in brackets):

| Source | Opus | Sonnet | Haiku | GPT-5.5 | GPT-5.4 | mini | nano | DeepSeek (NUS) | DeepSeek (OpenRouter) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| HN "next level legal judo… still innovating… Terms of Service" (sarcasm) [negative] | negative ✓ | negative ✓ | unclear | negative ✓ | negative ✓ | positive | positive | positive | unclear |
| HN "…almost none of them have" (cut off) [unclear] | unclear ✓ | unclear ✓ | unclear ✓ | negative | unclear ✓ | negative | negative | unclear ✓ | negative |
| HN "…still a bad look" [negative] | negative ✓ | negative ✓ | negative ✓ | negative ✓ | negative ✓ | negative ✓ | negative ✓ | unclear | negative ✓ |
| Reddit "Meta Muse is cool, but I use Gemini more" [mixed] | mixed ✓ | negative | mixed ✓ | mixed ✓ | negative | mixed ✓ | mixed ✓ | unclear | mixed ✓ |
| Senators question Meta's $6.6B AI tax credits [negative] | negative ✓ | neutral | neutral | negative ✓ | negative ✓ | neutral | negative ✓ | neutral | negative ✓ |
| "Meta climbed 12%: take profits or hold?" (question) [neutral] | positive | positive | neutral ✓ | positive | mixed | mixed | positive | neutral ✓ | neutral ✓ |
| **Correct** | **5/6** | 3/6 | 4/6 | 4/6 | 4/6 | 2/6 | 4/6 | 1/6 | 4/6 |

**Market-wide stories.** "Dow Sees Best Day… As Investors Rotate Out Of AI Trade On Overspending Concerns" and "Hot CPI and PPI… AI Angst" were labelled unclear, neutral or unrelated by every Claude model, DeepSeek and the GPT small models. GPT-5.5 and GPT-5.4 were the only ones to read the Dow story as relevant and negative for META, but no model labelled it a reported event, so none would have alerted. The missing sell-off alert is a pipeline-rule problem, not a model problem.

**GPT notes.** GPT-5.4 passed all 16 batches here, but about 10–15% of live checks still fail: a live re-read sends 30–74 batches, so one slip somewhere is likely. GPT-5.5 was faster than GPT-5.4 (11 s against 18 s) and labelled more sources positive (18 against 11). Mini and nano are not usable as the main labeller without repair (30% and 20% of labels would be dropped). Mini remains the app's quick relevance check, a simpler task not tested here.

**DeepSeek notes.** The same model did much better through OpenRouter on DeepInfra than on NUS's deployment: 13/16 against 9/16, and 4/6 hard cases against 1/6. The host, its precision and its settings matter as much as the model. It was also the slowest model tested (median 95 s per batch, mostly thinking), and it missed the sarcastic comment. At US$0.0053 per batch it is the cheapest model that passed most batches without repair.

## 5. Live trial — switching the app to Sonnet 5.5

On the owner's instruction, `ANTHROPIC_REASONING_MODEL=claude-sonnet-5-5` was added to `.env` (backup `.local/backups/sonnet-switch-20261016/env.before`) and the app was restarted at 16:49:18 SGT after a 234 s wait for a quiet window.

| Window (SGT) | Checks completed | Failed at AI step | Other |
| --- | --- | --- | --- |
| 16 Oct 17:00–19:30 | 9 | 18 (mostly tone/basis mismatch) | 3 stopped |

Sonnet cost **US$13.455** (364 calls) plus Haiku US$0.264. Two causes that the offline test did not show:

1. **Switching models discards every saved label.** Saved labels are reused only when the model matches ([`sentiment_reuse.py:52`](../../thesis/research/sentiment_reuse.py)), so each company re-read its whole 7-day pool: 23–62 batches instead of about 4.
2. **One bad item still rejects a whole batch.** With 30–60 batches per re-read, at least one slip is almost certain. A batch that fails twice stays stuck until its sources change.

**Unplanned outage.** The restarted app ran inside the agent's sandbox, so it could not read the system's TLS certificates. From about 19:30 every outbound HTTPS request failed ("Operation not permitted"; 8 + 62 failed checks at "company news"). The process died after 01:24 on 17 Oct, when the agent's background jobs were cleaned up. **No monitoring ran from about 19:30 on 16 Oct to 09:07 on 17 Oct.** The app is now started from the owner's Terminal panel, outside the sandbox.

**Revert.** On 17 Oct the provider was switched back to OpenAI (`THESIS_MODEL_PROVIDER=openai`: GPT-5.4 main, GPT-5.4 mini quick check), backup `env.before-openai`. From 09:07: 7 checks completed and 1 failed (an event field on an item not marked relevant). Catching up cost US$9.184 (204 GPT-5.4 calls, 19.1 s average) plus US$0.565 for mini, because labels made by Opus and Sonnet cannot be reused.

## 6. Duplicate Telegram alerts

**Three accounts in the local installation were connected to the same Telegram chat:**

| Account | What it is | Watching |
| --- | --- | --- |
| Owner account | The account the owner signs in with | AVGO, GOOGL, META, NVDA, QCOM |
| Demo account | Old built-in demo account, no sign-in | AMD, AMZN, AVGO, FN, MU, QCOM (+ AVGO filing check) |
| Leftover account | From the earlier email sign-in, no sign-in | nothing |

AVGO and QCOM, watched by two accounts, arrived twice. The demo account's AMD alerts looked like cross-company duplicates of the owner's NVDA alerts. On 17 Oct about 09:25, the demo account's 6 news watches and filing check were stopped, and Telegram was turned off for both extra accounts, using the app's own functions.

**Google News within one account.** The owner's account received the same story cluster for NVDA three times (16 Oct 14:31, 15:30, 16:31). Google News gives no article text; its description is a rotating list of other outlets' headlines, shared by every article in the cluster. Each rotation made a new version (new fingerprint → "unseen"), and the AI quoted the list instead of the article, so a different CNA article produced an identical message. It also caused false company matches: GOOGL matched three Malaysian economy stories through the list.

**Fix (live from the morning of 17 Oct):** Google News items keep only their own headline, which ends with the outlet ([`source_hub.py`](../../thesis/research/source_hub.py)), and are recognised as already seen by article URL ([`coverage.py`](../../thesis/research/coverage.py)). Two new tests plus the related suites: 175 passed. A replay on the saved Google News feed kept the real Nvidia story and dropped the list-only matches.

## 7. Limitations

- One company sample per experiment (AVGO, then META); 16 batches in the fair test. Not a benchmark.
- Agreement is measured against Opus, not ground truth. The six proofread cases are one developer's reading.
- The OpenRouter DeepSeek result is for one pinned host (DeepInfra fp8); other hosts, especially cheaper fp4 ones, may behave differently.
- Item-level repair figures are what the checker would drop; repair is not yet implemented in the app.

## Explanation: four possible setups

All costs are estimates at the owner's current 5 watches (about 60 AI batches a day once caught up), using per-batch costs measured above. The table uses Claude models; the equivalent OpenAI and DeepSeek choices for each role are in the [archived provider comparison](../archive/status/2026-10-17-sentiment-redesign-progress.md#model-choice-by-provider). The [current plan](../development/sentiment-alert-redesign-plan.md) records the selected models and outstanding cost gate.

| | **(a) Current** | **(b) Most effective** | **(c) Most cost-effective** | **(d) Cheapest** |
| --- | --- | --- | --- | --- |
| Main model | GPT-5.4 | **Opus 5.5** | **Sonnet 5.5** | **Haiku 5.5** |
| Quick relevance check | GPT-5.4 mini | Haiku 5.5 | Haiku 5.5 | Haiku 5.5 |
| Cost per batch | about US$0.046 | about US$0.077 | about US$0.040 | **about US$0.003** |
| Est. AI cost per day | about US$2.70 | about US$4.60 | about US$2.40 | **about US$0.20** |
| Time per batch | about 18 s | about 7 s | **about 5.5 s** | about 15 s |
| Batches passing (16 META batches) | 16/16 (about 85–90% of live checks) | 15/16 | 16/16 | 12/16 |
| Batches passing with repair | — | 16/16 | 16/16 | 16/16 (about 8% of labels dropped) |
| Nuance on the 6 test cases | 4/6 | **5/6** | 3/6 | 4/6 |
| One bad item | rejects the whole batch | dropped, batch kept | dropped, batch kept | dropped, batch kept |
| What triggers an alert | new adverse article only | **price move + "why is it moving"**, plus big company events | price move + explainer, plus big events | price move (code only); one short AI explainer only when triggered |
| Collection | all sources hourly, Reddit about 4 min | fast lane every 15 min (price + headlines), Reddit hourly | fast lane every 15 min, Reddit hourly | fast lane every 15–30 min, Reddit every 4 h |
| Prompt | one 16k-character, six-job prompt | split into small tasks + "how important is this" step | split into small tasks + importance step | split into small tasks |
| Catches the sell-off | no | yes, with cited cause | yes | yes, cause is shorter |

DeepSeek V4.1 Flash is not in the table. Through OpenRouter (DeepInfra) it is a real candidate for the cheapest setup: 13/16 batches passing, 16/16 with repair, 4/6 hard cases, about US$0.32 a day. But it was the slowest model tested (about 95 s per batch), and Haiku is still cheaper (about US$0.20 a day). On NUS's deployment it did much worse (9/16, 1/6).

**(b) Most effective: Opus plus a price-move trigger.** Alert when a watched stock moves a lot, or much more than the index or its sector. One Opus call then explains why, labelling the cause as market-wide, sector or company-specific with cited headlines, or saying "no clear cause found". This catches sell-offs and moves listicles out of alerts. Opus was best on sarcasm and mixed views, and item-level repair takes it to 16/16. It costs the most.

**(c) Most cost-effective: Sonnet plus the same trigger and repair.** Sonnet passed 16/16 and was fastest at about half Opus's price. Its live failures came from one bad item rejecting whole 30–60-batch re-reads, which item-level repair removes. With a 15-minute fast lane and hourly Reddit, checks drop from about 4 minutes to well under a minute. The cost is a little nuance (3/6 against 5/6).

**(d) Cheapest: Haiku plus code-only triggers.** The price-move detector is plain code. Haiku does relevance and labels; the explainer runs only when a move triggers; Reddit is checked every 4 hours. About US$0.20 a day, roughly 13× cheaper than now, with about 8% of labels dropped by repair and shallower explanations.

All three depend on the same foundation, which matters more than the model choice: item-level repair, the price-move trigger, the fast/slow collection split and smaller prompts. Any model switch also costs a one-off re-read of the 7-day sources (US$4–13 depending on the model, as seen in section 5) unless labels can carry over between models.
