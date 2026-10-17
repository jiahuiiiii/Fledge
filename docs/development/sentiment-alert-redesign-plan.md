# Sentiment and alert redesign — implementation plan

Proposed 17 October 2026. Direction: build option **(c) most cost-effective** first (a mid-tier model for bulk reading, a small model for the quick check), then add selected parts of option **(b) most effective** where they matter most: a price-move trigger, a top-tier "why is it moving" explainer, and market/sector context. The model names below use the Claude family; [Model choice by provider](#model-choice-by-provider) gives the OpenAI and DeepSeek equivalent for each role, with measured results and costs. The evidence behind every number here is in the [experiment record](../testing/sentiment-model-comparison.md).

## 1. The issue right now

1. **Big moves don't alert.** Alerts only fire on new article text. Price never enters a watch, and the prompt tells the model to ignore trading signals. During the 14–15 October sell-off (NVDA −3.2% then −1.8%, AMZN and GOOGL −1.7%) no timely alert went out; the first came about 1.5 days later, worded like every other alert.
2. **Too many low-value alerts.** Opinion pieces, "X vs Y" listicles and price recaps pass as reported events. Of the 12 Telegram alerts the owner's account received on 13–17 October, about half were listicles, price recaps or Google News clusters (developer's count).
3. **Duplicates.** Three accounts shared one Telegram chat, and Google News's rotating related-headlines list made the same article look new every hour. Both are fixed (section 4, phase 0); the plan must keep it at zero.
4. **Slow.** A watch check takes a median of 202 s and up to 16 minutes. The AI step is only about 10 s; collection is about 4 minutes, mostly Reddit's 30 s gap between requests shared by all watches. Every source re-downloads the full 7-day window every hour.
5. **Brittle.** 16% of checks failed at the AI step on 13–16 October. One inconsistent label in a batch of 8 rejects the whole batch, and a batch that fails twice stays stuck. Switching models discards every saved label, forcing a full re-read (US$13.46 on Sonnet, US$9.18 on GPT-5.4 in the 16–17 October trial), and the Sonnet trial failed most of its checks for this reason.
6. **One prompt does six jobs.** About 16,000 characters of rules plus a 79,000-character schema per batch of 8: relevance, tone, evidence basis, event type and impact, dollar amounts and cross-article linking. Nothing in it asks "how important is this?" or "why is the stock moving?".

## 2. Why change

The product's selling point is "tell me when something important happens to a company I'm watching, and why". Today the system answers a narrower question, "is there a new negative article?", so it misses what matters (price moves with a market-wide cause), sends things that don't (listicles), and does it slowly and expensively. The model tests show model choice is a secondary issue: every model, including Opus, treated sell-off stories as not about the company. The rules and structure of the pipeline need to change; a cheaper, faster model then comes almost free.

## 3. Target design

```
Fast lane (every 15 min in US market hours, hourly otherwise)
  quote + price vs index/sector ─► move detector (code) ─┐
  company headlines (Finnhub, RSS) ─► quick check (small model) ─► labels (mid-tier model, split prompts)
                                                         │
Slow lane (hourly)                                       ▼
  Reddit + Hacker News (incremental) ─► labels ─► importance + severity ─► alert
                                                         ▲
  move trigger ─► "why is it moving" explainer (top-tier model, rare) ┘
```

| Part | From option | Model / method |
| --- | --- | --- |
| Bulk labelling of new sources | (c) | Sonnet 5.5 or GPT-5.4, smaller prompts |
| Quick relevance check | (c) | Haiku 5.5 or GPT-5.4 mini |
| Item-level repair, label carry-over | (c) | code |
| Fast/slow collection lanes | (c) | code |
| Price-move detector with index/sector comparison | (b) | code |
| "Why is it moving" explainer | (b) | **Opus 5.5** or GPT-5.5: low volume (a few calls a day), where nuance matters most |
| Importance and severity routing | (b) | part of the event-labelling task, code routing |

### Model choice by provider

Each role can be filled from any of the three providers the app supports. Measured on the same 16 fresh META batches ([experiment record](../testing/sentiment-model-comparison.md#4-experiment-3--sonnet-haiku-and-gpt-models-on-the-same-meta-batches)). "Pass" is batches passing the app's checks today, without item-level repair; "with repair" is the share of labels that would be dropped. Daily cost assumes the owner's current 5 watches, about 60 bulk batches a day once caught up.

| Role | Anthropic | OpenAI | DeepSeek |
| --- | --- | --- | --- |
| **"Why is it moving" explainer** (a few calls a day; nuance matters most) | **Opus 5.5**: 15/16 pass, 7 s, 5/6 hard cases, about US$0.077 per call | **GPT-5.5**: 16/16, 11 s, 4/6, about US$0.077 per call | DeepSeek V4 Pro: priced in the app, **not tested** |
| **Bulk labelling** (every new source) | **Sonnet 5.5**: 16/16, 5.5 s, 3/6, 81% tone agreement with Opus; about US$2.40/day | **GPT-5.4** (live today): 16/16, 18 s, 4/6, 80%; about US$2.70/day | DeepSeek V4.1 Flash via OpenRouter (DeepInfra fp8): 13/16 (3 labels dropped with repair), **95 s**, 4/6, 75%; about **US$0.32/day** (measured). On NUS's deployment: 9/16, 1/6 |
| **Quick relevance check** (cheap filter before labelling) | **Haiku 5.5** | **GPT-5.4 mini** (live today) | DeepSeek V4.1 Flash, thinking off (not tested for this task) |
| **Cheapest possible bulk labeller** (option d) | Haiku 5.5: 12/16, 15 s, 4/6; about US$0.20/day, about 8% of labels dropped with repair | GPT-5.4 nano: 5/16, 9 s, 4/6; about US$0.22/day, about 20% dropped. GPT-5.4 mini: 3/16, 2/6, about 30% dropped; not recommended | DeepSeek V4.1 Flash via OpenRouter, as above: more reliable than Haiku or nano, but about 6× slower |

**What this means for the decision:**

- **OpenAI path** (GPT-5.4 bulk, GPT-5.4 mini quick check, GPT-5.5 explainer): about the same reliability and daily cost as the Anthropic path, and it is already live with all its saved labels, so there is no switch cost. GPT-5.4 is about 3× slower per batch than Sonnet, but the AI step is not the bottleneck: collection is (section 1).
- **Anthropic path** (Sonnet bulk, Haiku quick check, Opus explainer): fastest and slightly cheaper for bulk labelling, best explainer on the hard cases (Opus 5/6). A switch costs a one-off re-read unless phase 1's label carry-over is in place.
- **DeepSeek path** (via OpenRouter, one pinned host): the cheapest model that passed most batches without repair (13/16, about US$0.32/day), with 4/6 hard cases. Its drawback is speed: about 95 s per batch, which would make the fast lane depend on the slow model. It fits a cheap bulk labeller in the slow lane, not the fast lane or the explainer. Results depend heavily on the host: the same model on NUS's deployment passed 9/16 and got 1/6. Always pin one host and re-test after any host change.
- **Mixing providers is allowed**: for example GPT-5.4 bulk with an Opus explainer. Each role is configured separately in phases 2 and 4.

## 4. Phases

Each phase ships on its own, is tested offline first, and restarts the app only from the owner's Terminal panel (never from an agent sandbox; see the 16 October outage).

### Phase 0 — done (16–17 October)

- Google News items keep only their own headline; articles are de-duplicated by URL ([`source_hub.py`](../../thesis/research/source_hub.py), [`coverage.py`](../../thesis/research/coverage.py)).
- Demo account watches stopped; Telegram on only for the owner's account.
- Provider back on OpenAI (GPT-5.4) as the stable baseline while this plan is built.
- GPT-5.5, GPT-5.4, GPT-5.4 mini, GPT-5.4 nano and DeepSeek V4.1 Flash via OpenRouter added to the 16-batch comparison (17 October).

### Phase 1 — reliability foundation (no model change)

**17 October 2026: implementation prepared; acceptance pending (not done).**
Offline related suites: 488 passed / 3 optional skips; later affected suites:
150 passed, final recovery suites 68 passed (overlapping). Frontend: 198 tests and 8 isolated component behavior
groups pass; build passes. META replay: Opus/Sonnet/GPT-5.5/GPT-5.4 each 16/16;
Haiku 14/16 with 9/119 repaired items (7.56%), above the 5% gate. AVGO Opus
15/15; the other four required models have no saved AVGO responses. Three-day
live measurement and installation remain pending. No model change, paid test
or app restart. See [phase 1 verification](../testing/sentiment-reliability.md).

1. **Item-level repair** in `sentiment.render` and `reporting_basis.render`. When a single item breaks a consistency rule, keep the batch and repair that item instead of rejecting everything:
   - tone and basis disagree, or a non-relevant item has a direction → tone and basis become `unclear`;
   - event fields inconsistent with the kind or relevance → event becomes `insufficient_detail` / `not_applicable` with no impact, so it can never trigger an alert;
   - event fields on a social item, earlier-attitude passages outside a relevant social post, price claims on news → dropped.

   Structural failures still reject the batch: missing or duplicate labels, passages not from the source, broken or unfinished output. A batch that needs more than a quarter of its items repaired (at least 1) is also rejected. Each repaired item records `repair: {policy, reasons, original}`, is counted in the reading, and shows "the AI's label and its evidence disagreed" in the app. Previously failed saved batches are re-checked under the new rules before anything is re-sent, so stuck companies recover without new spend. The summary policy name stays the same, so saved labels remain reusable.
2. **Label carry-over across models.** When the main model changes, reuse saved labels for unchanged sources if the prompt and policies match, and record the original model on each item. Only new sources go to the new model. An explicit "re-read everything" action stays available.
3. **Stuck batches.** If a batch still fails after its one retry, an explicit paid recovery action can re-send its sources once as two half-size batches before giving up. No automatic paid retry; child batches cannot retry or split again.

**Owner decision, 17 October 2026:** use GPT: retain GPT-5.4 for bulk readings and GPT-5.4 mini for the quick relevance check. Haiku is excluded from the selected rollout; its benchmark failure is not a release blocker. Other unselected models remain comparison evidence, not required rollout gates. No provider switch or environment change is needed. This records the phase 2 model choice without starting the next implementation phase or choosing the phase 4 explainer.

**Done when (selected GPT path):** replaying the 16 META and 15 AVGO batches passes 16/16 and 15/15 for GPT-5.4 with at most 5% of items repaired, and 3 days live on GPT-5.4 show at least 97% of checks completing. META passes16/16; the separately approved17October GPT-5.4 AVGO run passes15/15,64items,0repairs for US$0.5073675. The three-day observation remains pending (start12:38:12SGT17October). The earlier all-model gate is superseded by the owner's GPT selection; retain all comparison results.

### Phase 2 — choose the bulk and quick-check models

**17 October 2026: model choice approved; verification prepared, acceptance pending (not done).** Stay on GPT-5.4 + GPT-5.4 mini. Do not switch to Haiku or Sonnet. A read-only 48-hour report and related suites pass111tests. No switch (US$0 catch-up); 0/48 hours after confirmed installation and 0 complete daily cost windows. Phase1 still needs its matching frontend install and idle backend restart; the 11:56 SGT idle check deferred restart because4watches were due within90seconds. [Phase 2 verification](../testing/sentiment-model-rollout.md).

**Follow-up, 17 October 2026:** owner requested fixing Haiku first, then continuing
phase 2. The compact Anthropic format now passes **16/16 META batches, 119 items,
0 repairs**, using six successful revised responses and ten separately approved
remaining responses after an HTTP 400 stop. Hard-case interpretation is 3/6;
GPT remains selected. Three approved runs cost US$0.053381665 plus an unresolved
maximum hold of US$0.011598500. No automatic paid retry, model switch or app
restart. This authorises phase 2 preparation while phase 1's GPT AVGO and
three-day live gates remain unverified; phase 1 is not marked done.
[Details](../testing/sentiment-reliability.md#haiku-transport-follow-up--17-october-2026-meta-format-gate-passed).

Decide between the OpenAI path (stay on GPT-5.4 + GPT-5.4 mini) and the Anthropic path (Sonnet 5.5 + Haiku 5.5), using [Model choice by provider](#model-choice-by-provider). Re-run the 16-batch comparison with item-level repair on before deciding (the OpenRouter DeepSeek run is already included). The default is to **stay on GPT-5.4**: equal reliability in the tests, about the same cost, and no switch cost. Move to Sonnet if the fast lane (phase 3) needs faster AI responses. For the Anthropic path, set `THESIS_MODEL_PROVIDER=anthropic` and `ANTHROPIC_REASONING_MODEL=claude-sonnet-5-5` with an idle restart; label carry-over keeps the switch cost near zero.

**Done when:** 48 hours at 97% or more check completion on the chosen models, any switch catch-up costs under US$1, and daily AI cost is within the section 6 target.

### Phase 3 — faster collection

**Installation follow-up, 17 October 2026:** approved056/057 applied (schema57)
and matching tested frontend installed after a full archive backup; saved data
and preferences were exact across preparation. Owner started the stopped app
in Terminal. HTTP200/two combined checks verified12:38:12SGT, the conservative
phase1/2 observation start. Lanes/metrics remain off, so phase3's live measurement
has not started. No new Telegram delivery or environment change.

At12:55:59SGT, backed up `.env` and enabled only the dynamically read passive
source-status counter. The24-hour denial baseline starts then. No restart,
model/schedule/account preference change; lanes and new alerts remain off.

**17 October 2026: implementation prepared; live acceptance pending (not done).**
Owner approved additive migrations and continuing the entire plan without
phase-boundary confirmation. Migrations056/057 add independent fast runtime
state, lane-labelled history, incremental-source checkpoints and scoped HTTP
status observations; existing preferences/history are preserved. Features are
off pending the required live choices. Full offline backend2194pass/93optional
skips; related438pass (overlapping); frontend199pass,
build and6isolated browser groups at1440/390/320pass. 0/72live hours; medians and
provider-denial baseline unverified. [Contract/results](../features/watch-lanes.md).

1. **Fast lane**, every 15 minutes during US market hours (plus 1 hour either side) and hourly otherwise: quote and price, Finnhub, publisher RSS, Alpha Vantage. No Reddit or Hacker News.
2. **Slow lane**, hourly: Reddit and Hacker News.
   - Re-download a Reddit thread's comments only when the thread is new, or its feed entry's updated time changed.
   - Re-check old Hacker News comments for deletion once a day instead of every hour.
3. Keep the shared provider pacing and cooldowns; fast-lane checks never wait on the Reddit clock.

**Done when:** fast-lane checks have a median of 60 s or less and slow-lane checks 180 s or less over 3 days, with no increase in provider denials.

### Phase 4 — price-move trigger and "why is it moving" (from option b)

**17 October 2026: implementation prepared; acceptance pending (not done).**
Migrations058–060 are tested only in disposable databases; live schema57.
Price-only references, Decimal3/2/5rules, grouping, immutable private previews,
a separately disabled explainer role and cited evidence together in the existing
Updates/review design are prepared. No new Telegram delivery. Full offline suite
2308pass/93optional skips; final citation/worker regressions125pass, trial-runner
regressions101pass (overlapping); frontend202pass/build and8isolated browser
groups1440/390/320pass. User CSS preserved. [Contract and limits](../features/price-move-alerts.md).

The retrospective produces3events across4sessions; the14October market group
includes NVDA/AMZN/GOOGL (AMZN/GOOGL context-only). No15October trigger: NVDA's
two-session fall is4.94049%, below5%. Thresholds are unchanged; the literal
14–15October acceptance wording remains unresolved with the owner. All10paid explainer answers now pass citation checks: five saved answers
revalidated for free after a repeated-source validator fix, then five previously
unattempted cases in a separately approved continuation. Phase4 tests cost
US$0.116235 with0unresolved holds; no automatic paid retry. These checks do not
establish semantic accuracy. Owner subsequently approved GPT-5.5,3/2/5rules,08:30–17:00NewYork fast hours
(adjusted early closes), and5UStrading days of previews. Fast cadence waits for
the24-hour baseline; no new Telegram delivery. Installation is prepared, waiting
for normal active watches to finish and an owner Terminal restart. Phase4 is not
yet installed or marked done.

1. **Move detector (code only).** For each watched stock, compare today's change with the Nasdaq-100 (QQQ), the S&P 500 (SPY) and a sector fund (SOXX for semiconductors, otherwise the closest sector fund). Trigger on:
   - a move of ±3% or more in a session;
   - a gap of 2 points or more against the index;
   - ±5% or more over 2 sessions, to catch slides like 14–15 October.

   When two or more watched stocks trigger in the same direction as the index, group them into one **market event**. Add the index and sector funds as price-only instruments using the existing Yahoo adapter and pacing.
2. **Explainer (Opus 5.5, or GPT-5.5 on the OpenAI path).** One call per trigger or market event. It receives the move numbers, the last 24 hours of company headlines, and the World tab's market headlines ([`world_news.py`](../../thesis/research/world_news.py)). It returns a cause type (market-wide, sector, company-specific or no clear cause) and one or two sentences that cite exact headlines, with the existing citation validation. No price prediction or trade advice.
3. **Alert**, for example: "NVDA −3.2% today (Nasdaq −2.1%) · market-wide · investors rotating out of AI on spending worries" with the cited sources. A market event lists every affected watched stock in one message.

**Done when:** a replay over saved 13–17 October prices and headlines produces an alert for the 14–15 October NVDA, AMZN and GOOGL moves, unit tests cover the thresholds and grouping, and the explainer passes its citation checks on 10 authored and real cases.

### Phase 5 — smaller prompts, importance and severity

**17 October 2026: first task prepared; not done.** A private blind50-source
review page and strict scorer are prepared from permitted saved META/AVGO news
and discussion. No AI suggestions or prefilled labels. Read-only export and
related suites41pass;7authored browser groups1440/390/320pass with0HTTPrequests.
Owner annotations0/50received; no accuracy claim, new prompt or live route change.
[Review workflow](../testing/owner-sentiment-quality.md). Smaller-task request/validator
contracts are also prepared (instructions3924/3379/2497characters, related106tests
pass), with no dispatch or live pipeline integration yet. Routing/ratings/digest
and all quality/replay gates remain outstanding.

1. **Split the prompt into smaller tasks:**
   1. relevance (the existing quick check);
   2. tone and evidence basis;
   3. news only: event type, impact and **importance**;
   4. duplicate-story linking, run only when code finds headline candidates with similar wording.

   Target: each task's instructions are 6,000 characters or less.
2. **Importance:** high, medium or low, with a category: earnings or guidance, legal or regulatory, deal, management, product, analyst opinion, or market commentary. Opinion pieces, comparisons and price recaps are low by rule.
3. **Severity routing:**
   - high (price-move triggers, high-importance events): Telegram straight away;
   - medium: daily digest;
   - low: in the app only.
4. **Rate this alert:** a useful / not useful button in Updates and Telegram, stored per alert, to measure the outcome in section 6.

**Done when:** a 1-week replay puts 10% or fewer of Telegram-bound alerts in the low-value categories, and the label-quality check in section 6 still passes.

### Phase 6 — optional: Reddit counted by discussion

Weight Reddit tone by thread and cap per author, so one busy thread can't swing the tally. Choose comment order deliberately (newest, or Reddit's ranking) instead of the feed default.

## 5. Rollout and safety

- **Shadow week before Telegram.** Phases 4 and 5 first run in shadow mode for 5 US trading days: alerts are saved and shown in a "preview" list, not sent. They're compared with what the current pipeline sent.
- **Restarts** only from the owner's Terminal panel, after an idle check; back up `.env` before every provider change.
- **Cost guard:** a daily summary of AI spend, and an alert to the owner if a day exceeds US$5.
- **Rollback:** each phase is behind a setting so it can be turned off without a code revert.

## 6. Outcome and how success is measured

**Aim:** when something important happens to a watched company — especially a big price move — the owner gets one clear alert within about 20 minutes that says what moved, by how much against the market, and the most likely cited cause. Low-value articles stop interrupting, and the system runs reliably at about the cost of today's GPT-5.4 setup or less.

Measured over 10 US trading days after phase 4 is live. Baselines are from 13–17 October 2026.

| Metric | Baseline | Target (success) | How it is measured |
| --- | --- | --- | --- |
| Big moves alerted (rules in phase 4) | 0 timely alerts for the 14–15 Oct moves | 90% or more of qualifying moves | Move detector log against alerts sent |
| Time from move to alert | about 1.5 days (14–16 Oct) | median 20 min or less in market hours | Trigger time against Telegram sent time |
| Duplicate deliveries (same story, same account, 24 h) | 3 in one account on 16 Oct | 0 | Telegram delivery log, matched by article |
| Low-value share of Telegram alerts | about half of 12 (13–17 Oct) | 10% or less | Importance category on sent alerts |
| Alerts rated useful | not measured | 70% or more | "Rate this alert" button |
| Watch checks completing | 84% (13–16 Oct) | 97% or more | Watch history |
| Companies stuck more than 2 h | several during the Sonnet trial | 0 | Watch history |
| Labels lost to item repair | not applicable | 5% or less | Repair records per reading |
| Check duration | median 202 s, worst 974 s | fast lane median 60 s or less; slow lane 180 s or less | Watch history |
| AI cost per day (5 watches) | about US$2.70 (GPT-5.4, estimated) | US$3 or less, including Opus explainers | Spending ledger |
| Cost of a model switch | US$9–13 | under US$1 | Ledger, 24 h after a switch |
| Label quality | GPT-5.4 80% and Sonnet 81% tone agreement with Opus; 4/6 and 3/6 proofread cases | 80% or more against an owner-labelled 50-source set; 4/6 or more on the hard cases | Fixed labelled set, re-run after each prompt change |

**The change has failed, and the previous phase's setup is restored, if any of these happen:** check completion below 90% on any day, AI cost above US$6 a day for 2 days, fewer than 70% of qualifying moves alerted, or more alerts rated not useful than useful over a week.

The owner-labelled 50-source set doesn't exist yet. Building it is the first task of phase 5, and the [AnnoABSA](../testing/sentiment-research-basis.md) annotation tool, with its AI suggestions off, is one option for it.

## 7. Notes for whoever implements this

Read this before starting a phase. Read [AGENTS.md](../../AGENTS.md) too: it has the project's working rules.

### Working in this repo

- **Tests:** run with a locale set, or the throwaway test database refuses to start ("postmaster became multithreaded during startup"):
  `LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8 .venv/bin/python -m pytest -q tests/<file>.py`.
  Tests create their own database under `/private/tmp` and make no network calls; they never touch the owner's data.
- **Never start or restart the app from an agent's sandbox.** On 16 October an app restarted that way couldn't read the system's TLS certificates; every outside request failed, and the app died when the agent's session ended (about 8 hours without monitoring). Ask the owner, or use the desktop app's Terminal panel, and run `.venv/bin/python run.py --port 8841` from the repository folder.
- **Restart only when idle:** no watch lease active, no AI call running, no data update running, and no watch due within about 90 seconds. Checking the same tables as the `idle()` function in `.local/live-tests/sonnet-switch-20261016/restart.py` (not in Git) is enough. Back up `.env` before any provider change; a running app refuses AI calls as soon as `.env` changes, until it restarts.
- **Paid AI calls** go through the spending ledger (`thesis/providers/ledger.py`), which only allows the configured models at known prices. Experiment scripts in [`experiments/soclaas_replay/`](../../experiments/soclaas_replay/) show how to price another model inside one test process without changing the app. OpenRouter is not in the ledger: cap spend in the script and record OpenRouter's reported cost.
- **Replay inputs** for the 16 META and 15 AVGO batches are in `.local/live-tests/fair-meta-20261016/run/` and `.local/live-tests/soclaas-avgo-20261016/run15/`, on the owner's Mac only. Use them for phase 1 and phase 2 checks; fetch fresh batches with `fair_compare.py` if they're missing.
- **Phase 0 is committed** on the branch that adds this plan. Start from that branch or after it's merged.

### Phase 3: watch intervals

The database only allows 60- or 240-minute watches: `CHECK (interval_minutes IN (60,240))` on `news_watches` ([migration 012](../../migrations/012_sentiment_alerts.sql)) and `watch_checks` ([migration 018](../../migrations/018_watch_check_history.sql)), and `news_watch.configure` enforces the same values. A 15-minute fast lane needs a new numbered migration that adds 15 to both checks, plus code changes. Prefer a separate lane setting over reusing `interval_minutes`, so the existing slow-lane schedule and its watch history keep their meaning. Never edit an already-applied migration.

### Phase 4: index and sector prices

- **Live price source.** Watches don't refresh price history today; `price_history.refresh` only runs when the chart is open. Use the Finnhub quote that `market.refresh` already fetches each check: `normalize_quote` gives current price, previous close and `change_percent`. Finnhub has a 5-minute per-company cooldown; a recent check is reused, not re-fetched. Use the saved Yahoo daily bars (`price_history`) for the two-session rule.
- **Index and sector funds are not companies.** The `instruments` table (id, symbol, name) is filled from the SEC company directory (`thesis/research/sec/service.py` `add_company`), and much of the app assumes every instrument is a company with filings. Don't add QQQ, SPY or SOXX there. Add a small reference table (symbol, role such as `index` or `sector`, sector mapping) with its own quote snapshots, fetched with the same Finnhub client and pacing. Check that the Finnhub key returns ETF quotes before building on it.
- **Sector mapping** (which fund is each company's sector) is a small owner-editable table, defaulting to SOXX for semiconductors and none otherwise.

### Phase 4: explainer storage and Telegram

- Store each trigger and explanation in a new table: trigger time, the move numbers used, cause type, the explanation text, cited source versions and the AI call ID. Make it append-only like other research records.
- Alerts appear in three places that only know three alert kinds today: `research_alerts` (company alerts), the shared events query in `thesis/review_digest.py` (condition, company, idea), and `thesis/monitoring/telegram_message.py` `render`. Add a fourth kind (for example `move`) to all three, and to the Updates inbox in the frontend, rather than stuffing moves into company alerts.
- A Telegram move message should start with the numbers ("NVDA −3.2% today · Nasdaq −2.1%"), then the cause type, the explanation, and at most two cited source links. Keep the existing safeguards: escaped text, length limit, no resend after an uncertain delivery.

### Phase 5: prompt changes and re-reads

Saved labels are reused only when the prompt version, model, summary policy and related policies all match (`compatible` in [`sentiment_reuse.py`](../../thesis/research/sentiment_reuse.py)). Splitting the prompt creates new prompt versions, so every company would re-read its whole 7-day pool once, US$4–13 based on the 16–17 October switches. Either extend phase 1's label carry-over to cover prompt changes for tasks whose output didn't change, or schedule the switch at a quiet time and accept the one-off cost. Tone-flip alerts also need the old and new readings to use the same prompt version, model and summary policy (`changes` in `thesis/monitoring/news_watch.py`), so expect no tone-flip alerts on the first check after the switch.

### Decisions that need the owner's OK

Defaults are given in the phases; confirm each with the owner before going live:

| Decision | Default in this plan |
| --- | --- |
| Main and quick-check models (phase 2) | Stay on GPT-5.4 + GPT-5.4 mini |
| Explainer model (phase 4) | Opus 5.5 (or GPT-5.5 on the OpenAI path) |
| Move thresholds | ±3% in a session, 2 points against the index, ±5% over 2 sessions |
| Fast-lane hours | US market hours (09:30–16:00 New York time) plus 1 hour either side |
| Severity routing | High to Telegram now, medium to a daily digest, low in the app only |
| Daily cost alert | US$5 |
| Shadow period before Telegram | 5 US trading days |
