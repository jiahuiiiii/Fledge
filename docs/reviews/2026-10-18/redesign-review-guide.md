# Sentiment and alert redesign — what we did and what happens next

18 October 2026 · branch `feat/sentiment-analysis-redesign` · for the teammate reviewing it

## In one paragraph

Our alerts missed the 14–15 October tech sell-off, arrived late when they did come, repeated the same story and were often low-value. We tested nine AI models and found the **model was not the problem: the pipeline's rules were**. So we kept the current model (GPT-5.4) and rebuilt the pipeline in five phases. Phases 1–2 (reliability) are live and working. Phases 3–4 (faster checks, price-move alerts) are built and need a few days of live observation before we switch them on fully. Phase 5 (smaller prompts, smarter routing) is built but not good enough yet. **What we need from you:** review the code, and help run the observation week, which means the app running on an awake laptop for several days.

## 1. The problem

| What went wrong | Evidence |
| --- | --- |
| A sell-off produced no timely alert | NVDA fell 3.2% and then 1.8% on 14–15 Oct; the first alert came about 1.5 days later. Alerts only reacted to new article text and ignored price completely. |
| Low-value alerts | About half of 12 recent Telegram alerts were opinion pieces, "X vs Y" listicles or price recaps. |
| Duplicates | The same Google News story was sent 3 times in one afternoon. Three accounts also shared one Telegram chat. |
| Slow | A check took 3.4 minutes on average, up to 16. The AI part was only about 10 s; most of the time was waiting between Reddit requests. |
| Unreliable | 16% of checks failed, because one bad AI label made the app throw away a whole batch of 8. |
| Expensive | About US$9/day on Claude Opus for 11 watches. |

## 2. What we tested and concluded

Full record: [model comparison](../../testing/sentiment-model-comparison.md).

We sent the **same 16 batches of fresh META sources** (119 news articles and posts) to nine models and checked every answer with the app's own validation rules:

| Model | Batches passing | Time per batch | Cost / 16 batches | Hard cases right (of 6) |
| --- | --- | --- | --- | --- |
| Claude Opus 5.5 | 15/16 | 7 s | US$1.23 | **5** |
| Claude Sonnet 5.5 | **16/16** | **5.5 s** | US$0.64 | 3 |
| GPT-5.5 | 16/16 | 11 s | US$1.22 | 4 |
| **GPT-5.4 (kept)** | **16/16** | 18 s | US$0.73 | 4 |
| Claude Haiku 5.5 | 12/16 | 15 s | US$0.05 | 4 |
| GPT-5.4 mini / nano | 3/16 / 5/16 | 6–9 s | US$0.21 / US$0.06 | 2 / 4 |
| DeepSeek V4.1 Flash (OpenRouter) | 13/16 | 95 s | US$0.08 | 4 |

**What we concluded:**

1. **Every model missed the sell-off stories.** All of them treated "investors rotate out of AI" as not about the company. Changing models can't fix that; the alert rules have to change.
2. **The bigger models are about equally good.** We kept GPT-5.4: reliable, already running, and switching would have cost a full re-read.
3. **We tried switching live to Sonnet, and it failed.** Switching models threw away all saved labels, forcing a big re-read (US$13), and one bad label in any batch killed the whole run. We reverted to GPT-5.4. That failure is why phase 1 exists.
4. **DeepSeek's quality depends heavily on who hosts it:** 9/16 on one host, 13/16 on another. It is cheap but very slow, so it's only an option for background work.

## 3. What we built

| Phase | What it does, in plain words | State |
| --- | --- | --- |
| 0 | Google News stories no longer look "new" every hour; extra accounts no longer share one Telegram chat | **Live** |
| 1 | If one AI label is inconsistent, fix that one label instead of throwing away the batch. Saved labels survive a model switch. | **Live** |
| 2 | Keep GPT-5.4 for reading and GPT-5.4 mini for the quick relevance filter | **Live** |
| 3 | Split checks into a **fast lane** (price and news every 15 min in US hours) and a **slow lane** (Reddit/Hacker News hourly, only re-downloading what changed) | Built, **off** |
| 4 | **Price-move alerts:** flag a stock that moves ±3% in a day, 2 points more than the Nasdaq, or ±5% over two days. Group stocks moving together into one "market event", and add a short AI explanation quoting real headlines. | **Preview only**: saved in the app, not sent to Telegram |
| 5 | Smaller single-job AI prompts, an "importance" rating, routing (important → Telegram now, medium → daily recap, low → app only), useful/not-useful buttons, no same story twice in 24 h | Built, **off** |

Almost everything new sits behind a switch that is off by default. `.venv/bin/python -m thesis.runtime_status` shows which ones are on.

## 4. Results so far

| What | Result | Target | Verdict |
| --- | --- | --- | --- |
| Failed checks (first 10 h after install) | 0 of 43 | — | ✅ reliability fix works |
| Checks completed over 3 days | Broke when the laptop slept overnight: 15 stopped, 5 failed | ≥97% | ⚠️ needs an awake laptop |
| Price-move replay of 14–15 Oct | Catches 14 Oct (NVDA, AMZN, GOOGL as one market event); misses 15 Oct (NVDA's two-day fall was 4.94%, just under 5%) | Catch the sell-off | ⚠️ decision needed |
| Explanation quotes real headlines | 10/10 test cases | 10/10 | ✅ |
| Low-value messages (7-day replay) | 65% → 11% | ≤10% | ❌ close |
| AI labels match the owner's own labels | 24/50 | 40/50 | ❌ |
| AI cost | About US$3.90/day for 5 watches (was about US$9 for 11) | ≤US$3/day | ⚠️ close, not yet a full day |

**Conclusion:**
- **Reliability (phases 1–2):** done, pending its 3-day check.
- **Price-move alerts (phase 4):** the real fix for "missed the sell-off". They need one preview week, then a decision to send them to Telegram.
- **Phase 5 is not ready.** Its quality gaps may come from the labelling rules rather than the AI. We haven't checked yet whether the old pipeline scores any better on the same 50 labels.

## 5. What needs to happen next

### Your part (reviewer)

1. **Review the code**, using the reading order in section 6. We care most about anything that could send a **wrong, duplicate or unwanted Telegram message**.
2. **Push back on design.** Is this too much machinery? Where would you simplify? There are about 19 on/off switches; fewer would be better.
3. **Leave comments on the pull request.** Please don't merge.

### The observation week (owner's laptop, needs both of us to watch)

The app runs locally on the owner's MacBook. Several checks can only pass by watching it run for real, so the laptop must stay **on, awake, plugged in and online**:

| When (Singapore time) | What | Why |
| --- | --- | --- |
| Sun 18 Oct | Restart the app once from Terminal, after checking nothing is running (`runtime_status` shows `"idle_at_observation": true`) | Loads all the latest code and records which version is running |
| Sun 18 Oct | Turn on the fast lane (phase 3) | Its 24-hour baseline finished today at 12:55 |
| From the restart, **3 days** | Laptop awake 24/7 | Phase 1 needs ≥97% of checks completing for 3 days; phase 3 needs 3 days of timing data |
| **Mon 19 Oct 21:30** onward, **5 US trading days** (to Fri night) | Laptop awake through US hours, 21:30–04:00 | First live price-move previews; this is when they're recorded |
| Sat 24 Oct | Review the week's previews together | Decide whether price alerts go to Telegram |

**How to keep the MacBook awake:** System Settings → Battery → Options → turn on *Prevent automatic sleeping on power adapter when the display is off*, and keep it plugged in. Alternatively, run `caffeinate -i` in a spare Terminal tab while the app runs. The lid can stay open with the screen off. If it sleeps during US hours, that day's price moves are **lost**; there's no catch-up yet.

### Building, during the same week

| Task | Who | Notes |
| --- | --- | --- |
| Price-alert catch-up after sleep | Dev (AI session) | Detect a move from closing prices when the laptop wakes, marked "delayed" |
| Score the old pipeline on the owner's 50 labels | Dev | Free, no new AI calls; tells us whether phase 5's gap is the prompts or the labelling rules |
| Go through the 26 label disagreements | Owner + reviewer | Agree the rules, e.g. "is a question neutral or unclear?" |
| Fix a test that fails between 00:00 and 07:00 SGT | Dev | Test bug, not an app bug (see below) |

### Decisions the team needs to make

1. **The 15 Oct miss:** accept it, or add a "fell X% from its recent high" rule. A one-year replay of both options is in [drawdown comparison](../../testing/drawdown-rule-comparison.md).
2. **After the preview week:** send price-move alerts to Telegram, yes or no.
3. **Phase 5:** is "80% exact agreement with one person's labels" the right bar, or should we judge by whether the alerts it sends are useful?
4. **Cost:** is about US$4/day acceptable while phase 5's cheaper prompts aren't ready?

## 6. Code reading order

You don't need to read all 183 files; about a third are tests and a quarter are docs and experiments.

1. **Reliability (live)**
   - [`sentiment_reliability.py`](../../../thesis/research/sentiment_reliability.py), and [`sentiment.py`](../../../thesis/research/sentiment.py) `render()`, which applies it.
   - [`sentiment_reuse.py`](../../../thesis/research/sentiment_reuse.py) and [`sentiment_batching.py`](../../../thesis/research/sentiment_batching.py).
   - *Can a repaired label ever trigger an alert? Can an old label stick to changed text?*
2. **Price moves (preview live)**
   - [`price_moves.py`](../../../thesis/monitoring/price_moves.py), [`move_watch.py`](../../../thesis/monitoring/move_watch.py), [`us_session.py`](../../../thesis/monitoring/us_session.py).
   - [`reference_prices.py`](../../../thesis/research/reference_prices.py), [`move_explainer.py`](../../../thesis/research/move_explainer.py), [`MoveAlertCard.jsx`](../../../frontend/src/components/MoveAlertCard.jsx).
   - *Time zones, US holidays and early closes, daylight saving; can an explanation claim a cause it can't support?*
3. **Telegram safety (off)**
   - [`alert_routing.py`](../../../thesis/monitoring/alert_routing.py), [`telegram_stories.py`](../../../thesis/monitoring/telegram_stories.py), [`daily_telegram.py`](../../../thesis/monitoring/daily_telegram.py), [`daily_updates.py`](../../../thesis/monitoring/daily_updates.py), and changes in [`telegram.py`](../../../thesis/monitoring/telegram.py).
   - *Any path to a duplicate, a send after delivery is switched off, or a resend after an unconfirmed send?*
4. **Fast/slow lanes (off)**
   - [`watch_lanes.py`](../../../thesis/monitoring/watch_lanes.py), changes in [`news_watch.py`](../../../thesis/monitoring/news_watch.py), [`reddit_rss.py`](../../../thesis/research/reddit_rss.py) and [`hackernews.py`](../../../thesis/research/hackernews.py).
   - *Can the two lanes race and publish the same reading twice?*
5. **Smaller prompts (off, will change)**: skim [`sentiment_tasks.py`](../../../thesis/research/sentiment_tasks.py) and [`sentiment_task_runner.py`](../../../thesis/research/sentiment_task_runner.py).
6. **Database migrations 056–067** ([`migrations/`](../../../migrations/)): all additive. 056–064 are already applied to the owner's database and **must not be edited**; 065–067 apply automatically on the next start.

Skip: prompt wording, `experiments/`, `docs/archive/`, CSS.

## 7. Running it yourself

```bash
LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8 .venv/bin/python -m pytest -q
```

The tests use their own throwaway database and make no network calls. They take about 8½ minutes. Without the locale setting, the test database won't start. Last run on 18 Oct at 15:57: **2,784 passed, 93 optional skips**.

```bash
cd frontend && npm test
```

Last run: **202 passed**.

**Known test bug:** `test_daily_schedule_catches_up_one_window_at_a_time_and_keeps_boundary_routes_in_next_day` fails if run between 00:00 and 07:00 Singapore time. It assumes the next 07:00 recap is always tomorrow; the app is correct.

To run the app on your machine, follow the [README](../../../README.md). You'll start with an empty database and need your own API keys. The live observation results above only come from the owner's running copy.

## Please don't

- **Start the app from `main`** against a database that has these migrations. `main` doesn't have the files and startup will refuse.
- **Merge, or push to this branch**, without checking with the owner; it's the code the live app runs.
- **Treat a failed check as passed.** The open gates above are recorded as failing on purpose.
