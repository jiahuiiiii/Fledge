# Thesis

A local investment research workspace for students and newer investors: investigate a company, compare fundamentals with expectations, save your reasoning and revisit it when the evidence changes.

**Current stage: local pitch MVP.** Company research, source-backed sentiment, saved ideas, monitoring, in-app updates and optional Telegram alerts are implemented. Source coverage and interpretation quality still have gaps; this is not a trading execution platform. Status below reflects verification on **8 October 2026**.

Built with React/Vite, FastAPI and PostgreSQL, selectively adapting [Kestrel](https://github.com/jiahuiiiii/Kestrel) and [Deus](https://github.com/c0vo/Deus). Thesis has its own schema and evidence/monitoring contracts; it does not install either upstream application wholesale. [Source provenance](PROVENANCE.md) records the versions and adaptations.

[Run locally](#open-it-on-this-mac) · [Fresh setup](#fresh-setup) · [Source availability](#sources-and-current-availability) · [Paid AI restriction](#paid-ai-installation-restriction) · [Documentation](docs/README.md)

## Open it on this Mac

Double-click **Start Thesis.command**, or run from this folder:

```sh
.venv/bin/python run.py --open
```

Open [the local workspace](http://127.0.0.1:8841). The launcher starts a private PostgreSQL instance if needed. Close the terminal or press Control-C to stop the web app. Stop its database separately with `.venv/bin/python run.py --stop-db` when it is no longer needed.

Local state persists in `.local/`, including research history, the PostgreSQL cluster, spending ledger and local session key. Both `.local/` and `.env` are excluded from Git: pushing the repository backs up the code, not the saved workspace or credentials. Keep separate private backups and preserve the original spending database.

## Research workflow

1. **Choose a company.** Use **Add company** to search SEC listings beyond the original six-company test sample. The selected company follows Workspace, My ideas, Updates and History. Sidebar selections filter the current page; **All companies** clears the selection. Removing a company from the sidebar preserves its research and monitoring.
2. **Let sources load.** First open queues quotes/news, filings, daily price history, Reddit, Hacker News, publisher RSS, Alpha Vantage, X, analyst targets and reference multiples. Four workers handle independent steps, subject to provider access and cooldowns. **View progress** shows running, queued, partial and blocked work. Later opens reuse the saved load; **Refresh research** starts another coordinated source check. Source loading makes no paid AI request.
3. **Inspect performance and expectations.** Read annual/latest-quarter fundamentals with reporting dates and filing inputs. Inspect saved news for management outlook and named analyst views. In **Valuation**, compare sourced analyst target ranges with your own P/E/P/S scenarios, sensitivity and optional entry/horizon price references. These scenarios are conditional calculations, not consensus buy prices.
4. **Read the discussion.** **Refresh & analyse** collects news/discussions and then explicitly requests sentiment analysis. Company news, Reddit, Hacker News and X stay separate, with exact source passages, optional saved reply context and coverage gaps. **Read current sources** previews saved inputs without an AI request. Optional themes show what sources discuss and where views differ.
5. **Investigate a question.** Use **Add question** or **Edit question** in the research card. Saving a question costs no AI credits. **Summarise sources** and **Answer this question** are explicit paid actions; identical settled requests can reuse saved responses. Question history retains previous answers and their original evidence.
6. **Save your reasoning.** Save a draft before defining any monitoring rules. Add numerical requirements/risks or event conditions when ready, review proposals and explicitly approve the conditions. Approval and watch activation are separate. Optional private AI checks connect evidence to the exact saved revision or look for answers to the saved question.
7. **Review changes.** Updates combines company, saved-idea and condition alerts. History preserves revisions, earlier source checks and comparisons. Mark an update reviewed or unresolved without changing the underlying assessment. Saved results, private downloads and weekly reviews can be read without another AI call.

Use the up-chevron to hide the progress strip and **Progress** to reopen it. The panel icons beside Telegram hide/show the company and idea sidebars; layout preferences persist in that browser. Initial loading, refresh status and source availability are visible rather than inferred from an empty panel.

Discussion windows are **24 hours, 7 days (default), or 30 days**. News and automatic watches use seven days. X recent search retrieves at most seven days; a thirty-day view may include older locally saved posts but is not a complete thirty-day archive. Sentiment analyses select a bounded sample of up to eight news and eight social texts; broader acquisition does not mean every retrieved item was analysed.

Sentiment is a way to inspect the tone and themes of selected sources and identify changes worth investigating. It is not a market-wide opinion poll, price forecast or buy/sell signal. Missing access is shown as a coverage gap, not neutral sentiment. Earlier analyses retain their original sources, method and labels.

## Sources and current availability

| Source | Used for | Current status |
| --- | --- | --- |
| Finnhub | Company quotes/news and reference multiples | Existing integration; requires the project's own API key. Endpoint availability depends on account access. |
| SEC | Company catalogue and annual/quarterly filing fundamentals | Implemented; requires a valid project/contact user agent, not an API key. |
| Yahoo Finance price history | Daily line/candlestick chart | Existing separate integration; no extra key. Its availability is independent of Yahoo news RSS. |
| Stock Analysis, attributed to S&P Global | Analyst target range, average/median/high/low and potential upside/downside | Implemented; source dates, analyst count and missing values stay visible. Shared 24-hour refresh cooldown. |
| Public publisher RSS | Company-matched headlines and summaries | **10 of 11 feeds responded** in the latest live check. Sources include WSJ Markets/Business/Technology, CNBC, MarketWatch, NYT Business, Google News Business, Federal Reserve and Korea Times Economy/Business. Yahoo Finance news RSS returned 404. |
| Hacker News | Verified company-related comments and bounded reply context | Working in the recorded live check: nine matching Broadcom comments retrieved. This remains a limited tech-community sample. |
| Reddit | Company search and reply parsing | Implemented collector, but the public reply endpoint returned 403. Collection remains paused pending an approved connection; no OAuth connector is implemented. |
| Alpha Vantage | Company-filtered news headlines/summaries | Adapter and controlled-response tests implemented. No key configured during verification; live endpoint access is unverified. |
| X / Twitter | Original posts through official recent search | Adapter and controlled-response tests implemented. Requires a token and explicit enablement; no live X request was made during verification. Replies, quotes and reposts are excluded. |
| Nitter | Potential upstream social source | Not enabled. It is not an active fallback for unavailable X access. |

Publisher retrieval retains available headlines/summaries and original links; it does not fetch full paywalled articles. Matching and selection are bounded. The successful WSJ Business/Technology checks returned the same Broadcom report: both source versions were retained, with one selected news candidate after URL deduplication. A responding feed does not guarantee relevant or comprehensive coverage. Alpha Vantage's own sentiment scores are not imported as Thesis labels.

Open **Publisher feeds & source connections** in Evidence radar for feed outcomes and setup/failure reasons. Provider checks, cached feeds and cooldowns persist across restarts. One failed news provider does not stop all other collectors; partial coverage stays visible in watch history.

**Devvit was assessed, not implemented.** It supports Reddit-native apps and reviewed external connections, but registration alone does not authorize exporting Reddit discussions into this external research app. A Reddit-approved integration route and data deletion lifecycle are still required. [Connection setup, source limits and Devvit assessment](docs/features/multi-source-research.md) · [Actual verification](docs/reviews/2026-10-08/multi-source-research.md).

## Monitoring and Telegram

All watches and schedules start off. Adding a company or saving a draft does not enroll it in monitoring.

- **News/social watches:** explicitly enable **Watch news + social changes**. Optional saved-idea checks distinguish reasoning connections from answers to a question. Watch settings and manual-check controls hide when the watch is off; saved preferences and history remain. New samples may use paid AI; unchanged eligible inputs can reuse saved results. Inspect **Watch check history** for baselines, quiet checks, failures and completed updates.
- **Filing checks:** **Start daily filing checks** runs once now, then every 24 hours while the app runs. Supported new figures feed approved numerical conditions without AI credits. Missing, expired or mismatched evidence remains unknown.
- **Event checks:** approve event conditions, enable the news/social watch and separately select **Also check my approved event conditions**. These are metered AI checks. Event occurrence dates, report-publication dates and recurring windows have distinct meanings; sentiment alone cannot confirm an event.
- **Weekly reviews:** open **Updates → Open weekly review → Weekly review settings** to opt into a local schedule. Reviews use saved records without extra source/model calls. Marking a review seen does not acknowledge each alert inside it.
- **Telegram:** add a dedicated `TELEGRAM_BOT_TOKEN`, open **Telegram** in the top bar, connect a private chat and explicitly enable future alerts. Delivery uses structured messages tied to published research updates, with no additional AI call or automatic backlog at activation. [Connection and delivery guide](docs/features/telegram-alerts.md).

The **local server and an awake Mac must remain running** for monitoring and Telegram dispatch. There is no hosted 24/7 worker. Telegram setup needs no public webhook; closing the browser alone does not stop a running server.

## Fresh setup

Verified here with **Python 3.12, Node 24 and PostgreSQL 18**. Use an installed PostgreSQL 18 distribution; Thesis does not modify another cluster. The default binary directory is `/opt/homebrew/opt/postgresql@18/bin`; set `THESIS_PG_BIN` if different. The launcher is verified on this Mac, not a cross-platform deployment package.

From the cloned project folder:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cd frontend
npm ci --ignore-scripts
npm run build
cd ..
.venv/bin/python run.py --open
```

A new database starts with authored Northstar/Aurora demo fixtures for the local research-to-review journey, including **Next development** to demonstrate recorded changes. Existing databases preserve their research and reset preference; launching does not clear or reseed an intentionally emptied workspace. Clones contain neither the owner's saved research nor private real-case evaluation corpora.

Copy `.env.example` to `.env` **only if `.env` does not already exist**, then edit the private copy. Keys remain server-side and must not be committed.

| Connection | Private configuration |
| --- | --- |
| Live source retrieval | `THESIS_LIVE_DATA_ENABLED=true`; individual providers also need the settings below where applicable. |
| Public RSS, Hacker News, Yahoo history, analyst targets | No additional key; source availability and cooldowns still apply. |
| Finnhub | `FINNHUB_API_KEY` |
| SEC | `SEC_USER_AGENT` containing the project/contact identity |
| Alpha Vantage | `ALPHA_VANTAGE_API_KEY`; verify access to `NEWS_SENTIMENT` with that account. |
| X | `X_BEARER_TOKEN` with recent-search access **and** `THESIS_X_ENABLED=true`. Default is off. |
| Telegram | `TELEGRAM_BOT_TOKEN`, followed by in-app chat connection and delivery opt-in |
| OpenAI | `OPENAI_API_KEY` plus the approved installation settings below. Keep `THESIS_LIVE_MODELS_ENABLED=false` on clones. OpenRouter is not required. |

Alpha Vantage is locally capped at 25 requests per UTC day; X at 20 requests per UTC day and up to 20 returned posts per request. Both use a one-minute provider-wide interval and a fifteen-minute company cooldown. These application limits do not establish provider entitlement or a guaranteed bill. **X data billing is separate from the US$30 OpenAI allowance.** Public RSS shares a fifteen-minute cache. Provider denials and pacing records survive a restart or workspace reset. [Detailed connection rules](docs/features/multi-source-research.md#connection-setup).

The database uses a Unix socket inside the private data directory, with TCP disabled. The web app binds to `127.0.0.1`. Use `--port 8842` for another web port. Give independent offline experiments their own `THESIS_DATA_DIR`; do not run two workers against the same data directory. This does not authorize a new paid-AI allowance.

For frontend development, run the API above and `npm run dev` inside `frontend/`. Vite proxies same-origin `/api` requests to port 8841. The normal launcher serves the built frontend directly through FastAPI.

## Paid AI installation restriction

Paid AI is configured for the owner's original installation, not a portable multi-user setup. Before dispatch, [`live_key()`](thesis/providers/settings.py) checks the resolved paths:

| Setting | Required original location |
| --- | --- |
| Project root (`APPROVED_ROOT`) | `/Users/jiahuiwong/Documents/GitHub/Thesis` |
| Data directory (`DATA`) | `/Users/jiahuiwong/Documents/GitHub/Thesis/.local` |

This is a software path restriction, not a Mac hardware check. Another checkout path or alternate `THESIS_DATA_DIR` is rejected for paid calls, even with a valid OpenAI key. The configured provider/models, explicit live-model switch and `THESIS_LIVE_TEST_BUDGET_USD=30` must also match the approved settings.

The **US$30 allowance is cumulative across the original build period**, including earlier charges and timeout reservations. The database enforces that ledger and unresolved-charge holds. Changing an environment value does not grant a new allowance.

A clone can run fictional workflows, save questions/ideas, calculate scenarios and run offline tests. Real-company retrieval can work with its own source configuration independently of the AI guard. New AI briefings, sentiment, answers and generated research remain unavailable outside the approved installation. Saved AI results are readable only if present in that installation's database.

Relocation requires a deliberate code/configuration change and migration of the **original database, including every call, charge, reservation and accounting decision**. No self-service rebind or per-clone budget setup is implemented. Do not remove the guard, delete the ledger or replace `.local/` to obtain a fresh allowance. [Detailed controls and historical decisions](docs/development/live-provider-controls.md).

## Verification and testing

Latest recorded verification, **8 October 2026**: **1,216 backend checks passed**, with **59 optional corpus checks skipped**; **27 frontend tests and the production build passed**. Source/status and watch-history browser journeys passed at 320, 390 and 1440px. These are software checks, not evidence of sentiment accuracy or complete live-provider coverage. [Results, original failures and live-source evidence](docs/reviews/2026-10-08/multi-source-research.md).

```sh
.venv/bin/python -m pytest -q
npm test --prefix frontend
npm run build --prefix frontend
```

Database tests create and stop disposable private clusters under `/private/tmp`; they do not mutate the original `.local/`. Optional retained-corpus checks require private evidence that is not included in a clone. For example, the SEC replay can be selected when its original corpus is available:

```sh
THESIS_REAL_CORPUS="$PWD/.local/live-tests/real-sec-corpus" .venv/bin/python -m pytest -q
```

With Playwright and a browser installed, run one isolated journey at a time:

```sh
.venv/bin/python tests/run_browser.py
.venv/bin/python tests/run_browser.py --social-platforms
.venv/bin/python tests/run_browser.py --sentiment
.venv/bin/python tests/run_browser.py --watch-history
.venv/bin/python tests/run_browser.py --idea-alert
.venv/bin/python tests/run_browser.py --valuation
```

`PLAYWRIGHT_MODULE` can point to an installed module; `CHROMIUM_PATH` selects its browser binary and `THESIS_NODE` a Node executable. The runner starts a disposable instance on port 8843, which must be free, and stops it afterwards. Screenshots go to `/private/tmp/thesis-*.png`. Its test-only network guard blocks external access from the Python server/seed processes, preventing first-open collectors from reaching real APIs. Do not load that guard into the normal app. Further journey options are listed in [the runner](tests/run_browser.py).

For manual testing, use [the usability guide](docs/testing/wednesday-testing-guide.md) and [feedback notes](docs/testing/wednesday-feedback-notes.md). The owner's workspace is already in active testing; a Git push requires no reset. If another session needs an explicitly requested reset, stop the app and run `.venv/bin/python reset_workspace.py` to inspect the scope first. `--apply` archives the database before clearing research and preserves API spending and provider pacing. Existing backups and `.env` remain private.

## Architecture, references and remaining work

```text
React/Vite workspace
        |
FastAPI routes → atomic services → PostgreSQL
                         |
                 durable background jobs
                    /             \
          source acquisition    monitoring checks
                    \             /
                saved evidence and evaluations
                         |
                 Updates / Telegram outbox
```

Source adapters live in `thesis/research/`; typed numerical checks in `thesis/monitoring/`. Model access and cumulative accounting sit behind `thesis/providers/`. Historical evaluations retain the exact source snapshot and reasoning revision. New acquisition does not rewrite previous interpretations.

**The ordered SQL files in `migrations/` are the schema authority**, currently through migration 040. The launcher supports fresh initialization and checksummed upgrades. [The archived SQL draft](docs/archive/planning/schema.sql) is unapplied planning material; do not run both. No existing Kestrel or Deus database has been imported.

Use [the documentation index](docs/README.md) for feature contracts and dated reviews:

| Area | References |
| --- | --- |
| Sources and research | [Multi-source setup](docs/features/multi-source-research.md), [Deus social collection](docs/features/deus-social-research.md), [company questions](docs/features/question-research.md), [discussion themes](docs/features/discussion-themes.md) |
| Fundamentals and valuation | [Financial performance](docs/features/financial-performance.md), [expectations](docs/features/company-expectations.md), [price history](docs/features/price-history.md), [analyst targets](docs/features/analyst-targets.md), [scenarios](docs/features/valuation-scenarios.md) |
| Sentiment and alerts | [Sentiment watches](docs/features/sentiment-alerts.md), [saved-idea checks](docs/features/idea-relevance-alerts.md), [source comparisons](docs/features/news-coverage.md), [event conditions](docs/features/event-conditions.md), [weekly reviews](docs/features/periodic-review.md), [Telegram](docs/features/telegram-alerts.md) |
| Development | [Implementation guide](AGENTS.md), [API contract](docs/development/api-contract.md), [provider controls](docs/development/live-provider-controls.md), [provenance](PROVENANCE.md) |
| Planning and evaluation | [Original product plan](docs/archive/planning/product-and-launch-plan.md), [architecture](docs/archive/planning/architecture.md), [user journey](docs/archive/planning/ux-and-user-journey.md), [local sentiment model comparison](docs/testing/local-sentiment-models.md) |

Remaining work includes approved Reddit access, live Alpha Vantage/X verification, automatic X deletion reconciliation, broader source coverage and sentiment/alert correctness evaluation. Known sarcasm, attribution and answer-relevance failures remain; exact citations alone do not establish correct interpretation. FinBERT, CardiffNLP and VADER were evaluated separately and are **not production replacements** for the current sentiment method.

Participant validation, supported portable AI setup, production authentication/deployment, hosted monitoring, external weekly-digest delivery, billing, broader financial analytics and reverse valuation/DCF also remain unfinished. The plans cover a wider product; consultant recommendations and proposed pricing are hypotheses, not demonstrated customer value or readiness to ship.
