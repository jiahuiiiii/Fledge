# Sentiment and alert redesign

Plan dated 16–17 October 2026; status reconciled 18 October. This file contains the design, acceptance tests and a short status table. Dated work records belong in `docs/reviews/YYYY-MM-DD/`; the earlier inline progress is preserved in [the archived plan](../archive/status/2026-10-17-sentiment-redesign-progress.md).

## 1. Problem and scope

The local app must tell the owner when something important happens to a watched company, with the price move, market context and cited evidence together. The old pipeline reacts mainly to negative textual reporting: it misses market-wide sell-offs, promotes opinion/listicles, waits on slow social collectors and costs too much.

The 13–16 October baseline had 84% check completion, median check duration 202 seconds, no timely price alert for the 14–15 October sell-off and substantial opinion noise. Model choice alone does not solve those structural problems. See [experiments and numbers](../testing/sentiment-model-comparison.md).

Prioritize faster checks and price-move previews before optional recaps, ratings and discussion weighting. This remains a local app; it cannot monitor while the Mac sleeps or the server is stopped. A delayed close-based recovery can address some missed sessions, not reconstruct all intraday moves.

## 2. Current status

These are verified checkpoints, not live telemetry. Schema/mode observation: 17 October, 23:25 SGT. Core observation: 23:21 SGT. Owner-quality scoring: 18 October.

| Phase | Implemented / installed | Acceptance remaining |
| --- | --- | --- |
| 0 — source fixes | Done, 16–17 October | None for this phase |
| 1 — reliability | Installed; GPT META 16/16 and AVGO 15/15, AVGO repairs 0/64 | Three days with ≥97% completion |
| 2 — model choice | GPT-5.4 / mini approved and retained; no switch cost | 48-hour completion and full-day cost gates |
| 3 — collection lanes | Code and schema installed; cadence off, passive metrics on | Baseline ends no earlier than 18 October 12:55:59 SGT; then three-day timing/denial comparison |
| 4 — price moves | Price previews enabled; GPT-5.5 approved; 10/10 explainer citation cases pass | Resolve literal replay coverage wording; verify deployed source, awake-Mac coverage and five trading days of previews; new Telegram delivery not approved |
| 5 — smaller tasks / routing | Prepared, off; schema 061–064 applied; rubric 2 tested; rubric 3 incorporates three separate owner clarifications | Agreement remains 24/50 = 48%; original hard cases 4/6, rubric 2 has 3/6; rubric 3 unmeasured; noise 2/18 = 11.11% fails ≤10%; usefulness, cost and live routing gates |
| 6 — discussion weighting | Optional, deferred | Decide only after first useful alert path works |

Current named summary is **Price previews**: combined news/social watches plus price detection; fast lanes, smaller prompts, severity routing, daily records and new Telegram types remain off. Existing account preferences are unchanged.

Schema **064** is applied with matching checksums. **065–067 are approved additive changes and will apply automatically on the next startup.** There is no migration-approval guard. Activation of new behavior is separate. Do not launch an older checkout missing applied migration files; remain on `codex/redesign-phase-5` until a merge is requested and completed.

The running app started at 15:54:29 SGT without a startup fingerprint. `price-move-rules-2` predates that restart; later fixes do not. Exact running source remains unverified. The prepared [status tool](../../thesis/runtime_status.py) records source at the next app startup and compares it with disk thereafter; it adds no configuration switches.

Cost is a release concern: US$2.352457 over 10.72 hours projects to about US$5.27/day, above the US$3 target. This is not a complete day or a cost pass. Core checks: 43 completed, zero failed/stopped, two unfinished. Smaller prompts remain off until their quality gates pass; reduced cost is not yet demonstrated.

For paid-test costs, failures and precise limits, see [quality](../testing/sentiment-quality-campaign.md), [news replay](../testing/news-noise-replay.md) and [operations](../reviews/2026-10-17/redesign-operations.md). Do not paste a new running log into this plan.

## 3. Target design

```text
Fast lane: quotes + index/sector context + company headlines
  every 15 minutes in approved US hours, hourly otherwise
                        ↓
  relevance → tone → news importance → severity
                        ↑
Slow lane: incremental Reddit + Hacker News, hourly

Code move trigger → bounded cited explainer → one evidence card
```

The chosen path is GPT-5.4 for bulk tasks, GPT-5.4 mini for quick relevance and GPT-5.5 for rare explanations. Retain old item-level model/call provenance; do not silently reread an entire pool when tasks have not changed. Other-provider results remain comparison evidence, not rollout blockers. [Provider comparison](../testing/sentiment-model-comparison.md).

## 4. Phases and acceptance tests

### Phase 0 — source fixes (done, 16–17 October)

Keep Google News items' own headlines, not cluster bodies; deduplicate by URL. Preserve the recorded account watch/Telegram decisions and OpenAI baseline. Keep original model experiments and failures.

### Phase 1 — reliability foundation

1. Repair bounded single-item consistency errors in code: incompatible tone becomes unclear; inconsistent events become insufficient detail without trigger impact; invalid social/news-only fields are dropped. Retain original fields and repair reasons.
2. Structural, incomplete, duplicate-label or foreign-source citation errors still reject. More than a quarter repaired, with at least one allowed, rejects the batch.
3. Recheck saved failed answers for free before any explicit redispatch. Reuse unchanged labels across models with their original provenance. Keep an explicit full reread action.
4. An explicit terminal recovery can split a previously failed batch once; children cannot retry/split again. No automatic paid retry.

**Done when:** selected GPT-5.4 passes 16/16 META and 15/15 AVGO batches with ≤5% repaired items, and three live days show ≥97% completion. [Verification](../testing/sentiment-reliability.md).

### Phase 2 — model selection

Retain the approved GPT-5.4 / mini pair. A provider change requires a separate choice, known prices, preserved spending ledger and an idle Terminal restart. A switch must carry over compatible labels rather than forcing a full seven-day reread.

**Done when:** 48 hours show ≥97% completion, switch catch-up costs under US$1 and daily AI cost meets the section 6 target. [Measurement](../testing/sentiment-model-rollout.md).

### Phase 3 — faster collection

1. Fast lane: quotes, Finnhub/company headlines, publisher RSS and Alpha Vantage; no Reddit/Hacker News waits. Every 15 minutes in approved hours, hourly otherwise.
2. Slow lane: hourly Reddit/Hacker News. Re-download Reddit comments for new/changed feed entries; rotate retained Hacker News deletion checks daily.
3. Preserve provider pacing, cooldowns, current source permissions, independent leases and cancellation fencing. Existing slow-watch preferences keep their meaning.
4. Compare at least 24 hours of passive provider observations with three days after activation. Missing provider traffic is unknown, not zero denials.

**Done when:** over three days, fast median ≤60 seconds, slow median ≤180 seconds and no increase in provider denials. [Contract](../features/watch-lanes.md).

### Phase 4 — price moves and cited explanations

1. Trigger in code on a session move of ±3%, a gap of 2 percentage points against QQQ or ±5% over two sessions. Use exact arithmetic; no threshold rounding to fit a case.
2. Keep QQQ/SPY/sector funds as separate price-only references. Missing/stale index context stays unknown. Group at least two qualifying same-direction stocks with the same index vintage; other members are explicitly context-only. A two-session decline cannot join today's upward rebound group.
3. One bounded GPT-5.5 explanation per trigger/group receives the numbers and last 24 hours of saved company/world headlines. It returns market-wide, sector, company-specific or no clear cause, with exact citations and no advice or predictions. A failed paid explanation does not retry automatically or prevent the numeric preview.
4. Store private immutable triggers, inputs, explanation, evidence versions and call IDs. Show them together in Updates. A future Telegram message starts with numbers and carries at most two cited links, escaped/bounded and protected against uncertain resends.
5. Confirm recovery after downtime before claiming unattended coverage. A future catch-up must say which closed session it describes, retain exact completed-bar inputs, preserve first-observed time and share durable deduplication with live alerts. Never relax live-quote freshness to make yesterday look current.

**Done when:** saved 13–17 October price/headline replay alerts on the 14–15 October NVDA/AMZN/GOOGL episode, tests cover thresholds/grouping and 10 authored/real explainer cases pass citation checks.

The current replay has a 14 October group with NVDA qualifying and AMZN/GOOGL context; no separate 15 October trigger because NVDA's two-session move is −4.94049%, below 5%. Literal acceptance wording remains unresolved; do not change thresholds or mark this passed silently. Citation validity alone does not establish explanation accuracy. [Contract](../features/price-move-alerts.md).

Drawdown/volatility candidates remain offline and unapproved: [saved-history comparison](../testing/drawdown-rule-comparison.md). They do not replace the accepted 3/2/5 preview defaults.

### Phase 5 — smaller prompts, importance and severity

1. Split into relevance, tone/evidence, news event/importance and candidate-only duplicate linking. Each task's instructions must be ≤6,000 characters; keep complete bounded sources and required context.
2. Classify news importance separately from tone. Categories: earnings/guidance, legal/regulatory, deal, management, product, analyst opinion or market commentary. Opinion, comparisons and price recaps are low by rule; a real background fact does not turn an editorial into an announcement.
3. Proposed routing: high to immediate Telegram, medium to a daily recap, low app-only. Capture previews first; never promote old preview records into live delivery. Existing saved-idea preferences remain authoritative.
4. Keep useful/not useful ratings beside evidence, per account and exact alert; optional Telegram callbacks must map to confirmed sent messages.
5. Preserve unchanged tones and their original provenance across task changes. Backfilling new importance may cost once; a prompt change alone must not invent a tone-flip alert.

**Done when:** a one-week replay puts ≤10% of Telegram-bound messages in low-value categories and section 6's label-quality check still passes. Use independent excerpt judgments, not the classifier's own categories to grade itself. Current company-news replay fails at 11.11%; private ideas, social, conditions, price/cost delivery and live timing remain outside that replay. [Results](../testing/news-noise-replay.md).

### Phase 6 — optional discussion weighting

After the first useful alert path works, consider thread/author caps so one busy discussion cannot dominate. Preserve bounded/incomplete-thread warnings and choose comment order deliberately. This phase is deferred, not implicitly complete.

## 5. Rollout and operating safety

- Five US trading days of previews before any new Telegram delivery; compare with the existing pipeline. Weekend calendar days do not count.
- Check idle immediately before a deliberate Terminal restart. Next startup applies approved pending migrations automatically and records its source fingerprint. Back up the database before that upgrade and `.env` before any configuration change.
- Keep new live delivery off until explicitly approved. A raw flag alone is not proof of an active route: starts, permissions, account settings, current evidence and delivery journals also matter.
- Named status summaries describe current gates; avoid introducing another stack of configuration switches to manage rollout.
- Proposed daily cost summary/alert remains separate from the US$3 success target. US$5 alert level/delivery still needs approval.
- Each existing phase gate can roll back its behavior without deleting schema or semantic history. Do not restart from `main` before its migration files are compatible.

## 6. Outcome measurement

Measure ten US trading days after phase 4's actual delivery starts. The aim is one clear source-linked alert within about 20 minutes of a qualifying move, with fewer interruptions and lower daily cost. The [outcome operator](../testing/redesign-outcomes.md) distinguishes actual/preview records, incomplete observation, unavailable inputs and unresolved costs.

| Metric | Baseline | Target | Evidence |
| --- | --- | --- | --- |
| Qualifying moves alerted | No timely 14–15 October alert | ≥90% | Detector assessments versus confirmed sends |
| Market-hours latency | About 1.5 days | Median ≤20 minutes | Trigger/first observation and sent timestamps |
| Duplicate story deliveries | Three in one account on 16 October | Zero within 24 hours | Displayed-story claims and delivery journal |
| Low-value message share | About half of 12 earlier messages | ≤10% | Independent review of all displayed excerpts |
| Alerts rated useful | Not measured | ≥70% | Latest usefulness ratings |
| Checks completed | 84% | ≥97% | Watch history, including unfinished work |
| Companies stuck >2 hours | Several during earlier trial | Zero | Watch/lease history |
| Labels lost to repair | Not measured | ≤5% | Item repair provenance |
| Check duration | Median 202 seconds, worst 974 | Fast ≤60 / slow ≤180 seconds | Lane-labelled history |
| AI cost, five watches | Estimated GPT baseline US$2.70/day | ≤US$3/day, including explainers | Closed full-day ledger windows; experiments separate |
| Model-switch cost | US$9–13 | <US$1 | First 24-hour catch-up ledger |
| Label quality | GPT hard cases 4/6 | ≥40/50 owner labels and ≥4/6 hard cases | Fixed independent source set |

Rollback criteria: completion below 90% on a full day, AI cost above US$6/day for two days, fewer than 70% of qualifying moves alerted or more not-useful than useful ratings over a week. Unknown denominators cannot pass; a read-only report does not automatically change configuration.

The blind owner review is complete: all 50 labels were supplied on 18 October. Exact agreement is 24/50 (48%), relevance 38/50 and tone 29/50; the owner-quality gate fails while the fixed hard-case gate remains 4/6. Preserve the original labels and denominator. Evidence/context matches all 50 AI inputs; disagreement includes interpretation/rubric differences and does not prove 26 model errors. Clarify short-excerpt and topic-context limits before any revision; these exposed labels cannot become an untouched holdout again. [Results](../reviews/2026-10-18/owner-sentiment-quality.md).

The [18 October rubric](../testing/sentiment-tone-rubric.md) clarifies attribution, uncertainty and conditional wording. Version 2's approved 56-request same-set comparison cost US$0.47429 with zero failures/repairs/retries/unresolved cost: agreement remains 24/50 and hard cases fall to 3/6. [Run and free review](../reviews/2026-10-18/sentiment-rubric-candidate.md). Version 3 incorporates three separately recorded owner clarifications; 192 related offline tests pass, but model quality is unmeasured and no paid attempt is authorized. Original labels/results remain exact. [Follow-up](../reviews/2026-10-18/sentiment-owner-clarifications.md). Fresh acceptance still needs separately held-out owner labels under the stable rubric.

## 7. Notes for whoever implements this

Read [AGENTS.md](../../AGENTS.md) first. Direct owner instructions override old archived checkpoints.

- **Tests:** `LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8 .venv/bin/python -m pytest -q tests/<file>.py`. Disposable database, no network. Run related suites as well as new cases.
- **Restart:** never operate the real app/DB from an agent sandbox. Use the owner's Terminal after no active leases/AI/data update and nothing due within 90 seconds. A read-only status check is not an admission lock. Never execute archived sandbox restart scripts.
- **Migrations:** ordered files are the schema authority. Never edit an applied file. Startup automatically applies all pending files; additive 065–067 are already approved, while their features remain separately gated. Do not claim they wait for an approval mechanism that does not exist.
- **Paid work:** spending ledger, known model prices and exact provenance. No automatic paid retry; retain unresolved costs. Disclose expected spend above US$2. A previous completed test does not authorize a new paid attempt.
- **Private configuration:** back up `.env`, never print credentials. Existing settings may be read dynamically or fixed at import; verify the relevant code instead of assuming every setting needs a restart.
- **Replay inputs:** private META inputs under `.local/live-tests/fair-meta-20261016/run/`; AVGO under `.local/live-tests/soclaas-avgo-20261016/run15/`. Do not refetch or redispatch a completed experiment merely because an old note says incomplete.
- **Lane schema:** existing 056/057 provide independent fast state/history. The original watch interval keeps its meaning. Preserve pacing and source-access boundaries.
- **Reference prices:** QQQ/SPY/SOXX are not SEC companies. Use their separate reference tables/client and existing pacing, not `instruments` company ingestion. Sector mapping remains owner-editable and private.
- **Price data:** the live detector requires recent same-session quotes; two-session arithmetic uses one validated daily-bar vintage. An awake Mac is required for timely detection. There is currently no durable closing-session catch-up.
- **New records/UI:** keep triggers, explanation/citations, routing, claims and ratings append-only/private with exact evidence. Updates, review digest and Telegram use the actual move kind. Follow existing design; keep evidence together.
- **Prompt changes:** reuse only compatible task outputs with their original prompt/model/policies. Do not force a full-pool reread or signal a tone flip solely because model/task identity changed.

### Choices requiring the owner's explicit OK before live activation

| Decision | Plan default | Current approval |
| --- | --- | --- |
| Bulk / quick models | GPT-5.4 / GPT-5.4 mini | Approved; retained |
| Explainer | GPT-5.5 on OpenAI path | Approved for previews |
| Move thresholds | ±3%, 2 points vs QQQ, ±5% over two sessions | Approved for previews |
| Fast hours | US session plus one hour each side | Approved 08:30–17:00 New York, early-close adjusted; wait for baseline |
| Severity routing | High immediate, medium daily, low app | Not approved |
| Daily cost alert | US$5 | Not approved |
| Shadow period | Five US trading days | Approved; new Telegram delivery still needs separate OK |

Do not mistake additive schema approval, passing unit tests or an empty weekend preview for permission to activate new Telegram delivery.
