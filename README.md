# Fledge

Previously named Thesis. The app is now Fledge; the repository directory, configuration names and saved-data identifiers retain their existing names for compatibility.

**Fledge helps you explore an investment idea, keep your reasoning, and review changes in the evidence you follow.**

A local research companion for newer investors: start with a question, understand a company, save your own reasoning and revisit it alongside dated evidence. It does not tell you what to buy or execute trades.

**Current stage: local pitch MVP.** The first companion features—starter questions, explanations beside financial terms and reasoning prompts—are implemented alongside company research, source-backed sentiment, saved ideas, opt-in monitoring, in-app updates and optional Telegram alerts. Source coverage and interpretation quality still have gaps. Status below reflects recorded verification on **9 October 2026**, not participant validation or public-launch readiness.

Built with React/Vite, FastAPI and PostgreSQL, selectively adapting [Kestrel](https://github.com/jiahuiiiii/Kestrel) and [Deus](https://github.com/c0vo/Deus). Fledge has its own schema and evidence/monitoring contracts; it does not install either upstream application wholesale. [Source provenance](PROVENANCE.md) records the versions and adaptations.

[Companion features](#start-with-a-question) · [Run locally](#open-it-on-this-mac) · [Fresh setup](#fresh-setup) · [Source availability](#sources-and-current-availability) · [Paid AI restriction](#paid-ai-installation-restriction) · [Documentation](docs/README.md)

## Start with a question

Choose a company you own or want to understand, then open **Ask a question → Your research → Start with a question**. Four optional shortcuts point to existing research:

| Question | Where it leads |
| --- | --- |
| How does this company make money? | The business explanation in Overview |
| Is it growing? | Financials, including revenue, profit and cash flow |
| What could go wrong? | Disclosed risks in Overview |
| What do analysts and management expect? | Outlook, keeping forecasts and management guidance separate |

Each shortcut adds a temporary reading prompt. It does not save a question, generate an AI answer or enable monitoring; ordinary first-open source loading remains separate. Missing or withheld research stays explicit. Fictional samples offer only their three supported shortcuts.

Short **?** explanations beside relevant terms cover revenue, growth, operating margin, free cash flow, P/E, guidance, analyst consensus and GAAP/adjusted figures. **Ask my own question** opens the existing private question interface. **Save my reasoning** opens the draft editor with a sentence template: *I think… because… I'm unsure about… I would reconsider if…* A selected starter can fill a new idea's question; your reasoning stays blank until you write it, and existing saved words are preserved. You can save a draft without monitoring conditions.

The first audience to test is new investors with a few holdings, with university investment clubs as one possible recruiting channel. Holdings are not required, and deciding not to invest is a valid research outcome. This audience and channel are hypotheses, not established demand.

The companion has no buy/sell score or trading streak. Distinct evidence limitations remain visible rather than becoming one confidence rating. Plain-language worry-to-condition suggestions, revised personal-alert narratives, decision notes and a dedicated look-back view remain planned. See [the companion journey and product judgment](docs/features/companion-journey.md) and [first implementation verification](docs/reviews/2026-10-09/companion-start.md).

## Open it on this Mac

Double-click **Start Fledge.command**, or run from this folder:

```sh
.venv/bin/python run.py --open
```

Open [the local workspace](http://127.0.0.1:8841). The launcher starts a private PostgreSQL instance if needed. Close the terminal or press Control-C to stop the web app. Stop its database separately with `.venv/bin/python run.py --stop-db` when it is no longer needed.

Local state persists in `.local/`, including research history, the PostgreSQL cluster, spending ledger and local session key. Both `.local/` and `.env` are excluded from Git: pushing the repository backs up the code, not the saved workspace or credentials. Keep separate private backups and preserve the original spending database.

With Supabase configured, sign in using an email link opened in the same browser. The verified owner email preserves access to existing research; other users get separate private workspaces. Sessions last at most one hour. [Login setup and reversible local recovery](docs/features/managed-login.md).

## Research workflow

1. **Choose a company.** Use **Add company** to search SEC listings beyond the original six-company test sample. The selected company follows Workspace, My ideas and Updates. Sidebar selections filter the current page; **All companies** clears the selection. Removing a company from the sidebar preserves its research and monitoring.
2. **Let sources load.** First open queues quotes/news, structured and original filings, daily price history, Reddit, Hacker News, publisher RSS, Alpha Vantage, X, analyst targets and reference multiples. Four workers handle independent steps, subject to provider access and cooldowns. **Research updates** holds progress, source-check and refresh controls, including running, queued, partial and blocked work. Later opens reuse the saved load; **Refresh research** starts another coordinated source check. Source loading makes no paid AI request.
3. **Understand the company.** **Overview** is the starting view: a saved business explanation, dated financial highlights and reported revenue mix. **Financials** holds the detailed performance, cash flow, balance sheet and filings. The price chart opens on demand. **Outlook** separates original management guidance, analyst forecasts and expectations extracted from news. **Compare & value** holds your reviewed peers, sourced target ranges and P/E/P/S scenarios. These scenarios are conditional calculations, not consensus buy prices.
4. **Read news and discussion.** The **News & discussion** tab starts with recent headlines, followed by sentiment analysis. The AI company briefing is expandable; choose another sentiment source to read discussion separately. **Refresh & analyse** explicitly requests AI analysis, with bounded batches and reusable completed work. **Inspect evidence** opens a story’s exact excerpts, source context and report comparisons. **Evidence** opens the analysed sample, current saved sources and history. **Data & sources** contains connection checks and the source library; relevant coverage gaps remain beside the reading. Reading evidence makes no new source or AI request. [Reading journey](docs/features/reading-journey.md) · [Batching and recovery](docs/features/sentiment-batching.md).
5. **Investigate a question.** **Ask a question** opens **Your research** to add, edit or select a question and read its saved answers. **Start with a question** offers the companion shortcuts above. Saving a question costs no AI credits. **Summarise sources** and **Answer this question** are explicit paid actions; identical settled requests can reuse saved responses. Question and peer drafts survive closing their view and switching tabs within the same company.
6. **Save your reasoning.** Save a draft before defining any monitoring rules. Add numerical requirements/risks or event conditions when ready, review proposals and explicitly approve the conditions. Approval and watch activation are separate. Optional private AI checks connect evidence to the exact saved revision or look for answers to the saved question.
7. **Review changes.** Updates combines company, saved-idea and condition alerts. **History · versions and evidence checks** within an idea preserves revisions, earlier source checks and comparisons. Mark an update reviewed or unresolved without changing the underlying assessment. Saved results, private downloads and weekly reviews can be read without another AI call.

Open **Research updates** in the company header for reports and progress; a small header indicator shows active research. The chevron at the company sidebar's bottom collapses it to clickable company logos; expand it to search or manage the full list. The plus button opens **Add company**. **Watch · on/off** in News & discussion opens monitoring controls; opening it does not change any settings. Layout preferences persist in that browser. Company logos appear in the list and header, with initials when an image is unavailable. Initial loading, refresh status and source availability are visible rather than inferred from an empty panel.

Discussion windows are **24 hours, 7 days (default), or 30 days**. News and automatic watches use seven days. Reddit comment windows use the feed’s update timestamps, with original publication time explicitly unverified. X recent search retrieves at most seven days; a thirty-day view may include older locally saved posts but is not a complete thirty-day archive.

Current sentiment analysis covers all eligible distinct originals in the saved selection, in batches of up to **eight complete originals and 48,000 request bytes per request**. Coverage shows analysed sources and exclusions, including duplicates, incomplete passages and missing required context. These are request bounds, not a whole-reading source cap. Earlier limited readings retain their original sample and are labelled accordingly; analysing the saved selection does not establish complete market coverage.

Sentiment is a way to inspect the tone and themes of selected sources and identify changes worth investigating. It is not a market-wide opinion poll, price forecast or buy/sell signal. Missing access is shown as a coverage gap, not neutral sentiment. Earlier analyses retain their original sources, method and labels.

## Sources and current availability

| Source | Used for | Current status |
| --- | --- | --- |
| Finnhub | Company quotes/news and reference multiples | Existing integration; requires the project's own API key. Endpoint availability depends on account access. |
| SEC | Company catalogue, financial facts, original annual/quarterly reports and filed earnings releases | Implemented; four original Broadcom documents were retrieved. Requires a valid project/contact user agent, not an API key. Original text and calculation inputs remain inspectable. |
| Financial Modeling Prep | Sector/industry, suggested comparison companies, financial consensus and TTM ratios | Broadcom profile and peers returned 200; consensus and ratios returned subscription-access 402. Missing datasets remain unavailable. Existing Finnhub references are shown separately. |
| Yahoo Finance price history | Daily line/candlestick chart | Existing separate integration; no extra key. Its availability is independent of Yahoo news RSS. |
| Stock Analysis, attributed to S&P Global | Price targets and limited public annual revenue/adjusted-EPS forecasts | One shared page request and 24-hour company interval. Actual Qualcomm financial forecasts saved; restricted years, unknown forecast currency and pre-release comparability remain explicit. [Contract](docs/features/public-financial-forecasts.md). |
| Public publisher RSS | Company-matched headlines and summaries | **10 of 11 feeds responded** in the latest live check. Sources include WSJ Markets/Business/Technology, CNBC, MarketWatch, NYT Business, Google News Business, Federal Reserve and Korea Times Economy/Business. Yahoo Finance news RSS returned 404. |
| Hacker News | Verified company-related comments and bounded reply context | Working in the recorded live check: nine matching Broadcom comments retrieved. This remains a limited tech-community sample. |
| Reddit | Company/ticker search and comment RSS | **Working with bounded coverage:** six general investing communities plus mapped Broadcom/NVIDIA communities. Expanded Broadcom discovery retained 26 posts; five earlier comments remain available. The latest new comment request hit 429; the collector now honors reported reset windows. No extra key is needed; the earlier JSON/HTML denial remains unchanged. [Scope and limits](docs/features/reddit-rss-collection.md). |
| Alpha Vantage | Company-filtered news headlines/summaries | `NEWS_SENTIMENT` is documented as **Premium**. Key configured, but the first Broadcom check returned an unclassified service error, not news. Successful live retrieval remains unverified; the app's one-day cooldown is not a confirmed provider reset time. |
| X / Twitter | Original posts through official recent search | Deferred by the owner; remains disabled. Adapter and controlled-response tests exist, but no live X request was made during verification. Replies, quotes and reposts are excluded. |
| Nitter | Potential upstream social source | Not enabled. It is not an active fallback for unavailable X access. |

Publisher retrieval retains available headlines/summaries and original links; it does not fetch full paywalled articles. Matching and selection are bounded. The successful WSJ Business/Technology checks returned the same Broadcom report: both source versions were retained, with one selected news candidate after URL deduplication. A responding feed does not guarantee relevant or comprehensive coverage. Alpha Vantage's own sentiment scores are not imported as Fledge labels.

Open **Data & sources → Publisher feeds & source connections** for feed outcomes and setup/failure reasons. Provider checks, cached feeds and cooldowns persist across restarts. One failed news provider does not stop all other collectors; partial coverage stays visible in watch history.

**Devvit was assessed, not implemented.** It supports Reddit-native apps and reviewed external connections, but registration alone does not authorize exporting Reddit discussions into this external research app. A Reddit-approved integration route and data deletion lifecycle are still required. [Connection setup, source limits and Devvit assessment](docs/features/multi-source-research.md) · [Actual verification](docs/reviews/2026-10-08/multi-source-research.md).

**Our own Reddit HTML reader is experimental and off.** It needs no API key or scraper subscription. The owner-approved public-page check on 8 October returned a JavaScript verification page, with no usable posts or comments. Offline tests pass, but current discussion markup and working collection remain unverified. [Collector bounds and setup](docs/features/reddit-html-collector.md).

**Deus-style Reddit RSS is now integrated.** The exact upstream diagnostic established the hot-post route; Fledge also fetched real comments through the same host’s comment RSS. The NVIDIA workspace contains a saved eight-source sentiment reading with two original comments, tested for about US$0.08. Comment feeds do not expose the reply tree or verified publication time, so the app labels their feed-update dates and includes only comments that name the company themselves. Thirty-second pacing, persistent cooldowns and cached recovery reduce failed work; 429 responses still occur. RSS retirement remains scheduled for 13 November 2026. [How it works](docs/features/reddit-rss-collection.md) · [Actual verification](docs/reviews/2026-10-08/reddit-rss-integration.md).

## Monitoring and Telegram

All watches and schedules start off. Adding a company or saving a draft does not enroll it in monitoring.

- **News/social watches:** explicitly enable **Watch news + social changes**. Optional saved-idea checks distinguish reasoning connections from answers to a question. Watch settings and manual-check controls hide when the watch is off; saved preferences and history remain. New samples may use paid AI; unchanged eligible inputs can reuse saved results. Inspect **Watch check history** for baselines, quiet checks, failures and completed updates.
- **Filing checks:** **Start daily filing checks** runs once now, then every 24 hours while the app runs. Supported new figures feed approved numerical conditions without AI credits. Missing, expired or mismatched evidence remains unknown.
- **Event checks:** approve event conditions, enable the news/social watch and separately select **Also check my approved event conditions**. These are metered AI checks. Event occurrence dates, report-publication dates and recurring windows have distinct meanings; sentiment alone cannot confirm an event.
- **Weekly reviews:** open **Updates → Weekly review → Weekly review settings** to opt into a local schedule. Reviews use saved records without extra source/model calls. Marking a review seen does not acknowledge each alert inside it.
- **Telegram:** add a dedicated `TELEGRAM_BOT_TOKEN`, open **Telegram** in the top bar, connect a private chat and explicitly enable future alerts. Delivery uses structured messages tied to published research updates, with no additional AI call or automatic backlog at activation. [Connection and delivery guide](docs/features/telegram-alerts.md).

The **local server and an awake Mac must remain running** for monitoring and Telegram dispatch. There is no hosted 24/7 worker. Telegram setup needs no public webhook; closing the browser alone does not stop a running server.

## Fresh setup

Verified here with **Python 3.12, Node 24 and PostgreSQL 18**. Use an installed PostgreSQL 18 distribution; Fledge does not modify another cluster. The default binary directory is `/opt/homebrew/opt/postgresql@18/bin`; set `THESIS_PG_BIN` if different. The launcher is verified on this Mac, not a cross-platform deployment package.

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
| FMP | `FMP_API_KEY`; dataset and symbol access depend on the subscription. The app does not purchase a plan or bypass restrictions. |
| Managed email login | `SUPABASE_URL` (project API URL), `SUPABASE_PUBLISHABLE_KEY`, `THESIS_OWNER_EMAIL`; allow `http://127.0.0.1:8841/auth/callback` in Supabase. [Setup and recovery](docs/features/managed-login.md). |
| SEC | `SEC_USER_AGENT` containing the project/contact identity |
| Alpha Vantage | `ALPHA_VANTAGE_API_KEY` with Premium `NEWS_SENTIMENT` access. A free key alone does not unlock this endpoint; it is optional for the MVP. |
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

Recorded verification on **9 October 2026**:

- **Companion:** 87 tests of the shared frontend and the production build passed. The guarded companion browser journey covers starter navigation, term explanations, draft preservation/cancellation and layouts at 1440, 980, 390 and 320px. Separate read-only checks verified the installed features against saved Broadcom research at 1440, 390 and 320px. [Results and retained failures](docs/reviews/2026-10-09/companion-start.md).
- **Backend:** the latest documented full run for the sentiment price guards passed 1,668 checks with 66 optional skips. [Scope, evidence and limitations](docs/reviews/2026-10-09/sentiment-price-guards.md).
- **Saved-source batching:** the recorded Broadcom run analysed 120 originals in 15 batches. Its original method and results remain immutable; it does not establish a new live run under the later price guards. [Actual run and paid failures](docs/reviews/2026-10-09/sentiment-low-reasoning.md).

These are separate verification runs, not additive test totals. They verify software behaviour and selected saved records, not independent interpretation accuracy, complete provider coverage or participant comprehension.

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
.venv/bin/python tests/run_browser.py --companion
.venv/bin/python tests/run_browser.py --social-platforms
.venv/bin/python tests/run_browser.py --sentiment
.venv/bin/python tests/run_browser.py --watch-history
.venv/bin/python tests/run_browser.py --idea-alert
.venv/bin/python tests/run_browser.py --valuation
```

`PLAYWRIGHT_MODULE` can point to an installed module; `CHROMIUM_PATH` selects its browser binary and `THESIS_NODE` a Node executable. The runner starts a disposable instance on port 8843 by default (`THESIS_BROWSER_PORT` overrides it), which must be free, and stops it afterwards. Screenshots go under `/private/tmp/`; the companion journey uses `/private/tmp/thesis-companion/` unless `THESIS_COMPANION_EVIDENCE` is set. Its test-only network guard blocks external access from the Python server/seed processes, preventing first-open collectors from reaching real APIs. Do not load that guard into the normal app. Further journey options are listed in [the runner](tests/run_browser.py).

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

**The ordered SQL files in `migrations/` are the schema authority**, currently through migration 047. The launcher supports fresh initialization and checksummed upgrades. [The archived SQL draft](docs/archive/planning/schema.sql) is unapplied planning material; do not run both. No existing Kestrel or Deus database has been imported.

Use [the documentation index](docs/README.md) for feature contracts and dated reviews:

| Area | References |
| --- | --- |
| Companion | [Journey, product judgment and planned work](docs/features/companion-journey.md), [implemented entry, explanations and verification](docs/reviews/2026-10-09/companion-start.md) |
| Sources and research | [Multi-source setup](docs/features/multi-source-research.md), [Deus social collection](docs/features/deus-social-research.md), [company questions](docs/features/question-research.md), [discussion themes](docs/features/discussion-themes.md) |
| Fundamentals and valuation | [Financial performance](docs/features/financial-performance.md), [expectations](docs/features/company-expectations.md), [price history](docs/features/price-history.md), [analyst targets](docs/features/analyst-targets.md), [scenarios](docs/features/valuation-scenarios.md) |
| Business and accounts | [Original documents, financial depth and reviewed peers](docs/features/original-company-research.md), [managed email login](docs/features/managed-login.md), [actual verification and recovery](docs/reviews/2026-10-09/original-research-and-managed-login.md) |
| Sentiment and alerts | [Sentiment watches](docs/features/sentiment-alerts.md), [saved-idea checks](docs/features/idea-relevance-alerts.md), [source comparisons](docs/features/news-coverage.md), [event conditions](docs/features/event-conditions.md), [weekly reviews](docs/features/periodic-review.md), [Telegram](docs/features/telegram-alerts.md) |
| Development | [Implementation guide](AGENTS.md), [API contract](docs/development/api-contract.md), [provider controls](docs/development/live-provider-controls.md), [provenance](PROVENANCE.md) |
| Planning and evaluation | [Original product plan](docs/archive/planning/product-and-launch-plan.md), [architecture](docs/archive/planning/architecture.md), [user journey](docs/archive/planning/ux-and-user-journey.md), [local sentiment model comparison](docs/testing/local-sentiment-models.md) |

Remaining work includes approved Reddit access, resolving Alpha Vantage access, broader source coverage and sentiment/alert correctness evaluation. X is deferred; live verification and automatic deletion reconciliation would be needed before activating it later. Known sarcasm, attribution and answer-relevance failures remain; exact citations alone do not establish correct interpretation. FinBERT, CardiffNLP and VADER were evaluated separately and are **not production replacements** for the current sentiment method.

Companion work still includes reviewable suggestions from plain-language worries, clearer evidence-status presentation without a confidence score, personal alert/weekly-review narratives, explicit decision notes and a dedicated look-back view. Participant testing should measure comprehension, return after a relevant event and deliberate reasoning edits or decisions, including not investing. These measures are proposed; no new analytics were added by the first companion implementation.

Participant validation, Singapore regulatory review of the actual service, AI/data cost evaluation, supported portable AI setup, public deployment/security hardening, hosted monitoring, external weekly-digest delivery, billing, broader financial analytics and reverse valuation/DCF remain unfinished. Managed email identity and account isolation are now implemented for the local installation; this does not make the app remotely hosted. The plans cover a wider product; consultant recommendations and proposed pricing are hypotheses, not demonstrated customer value or readiness to ship.

[Beginner business analysis](docs/archive/planning/product-and-launch-plan.md#future-business-analysis) now has a first implementation: selected original disclosure passages explain operations, customers, revenue, competition and obligations, alongside reported revenue mixes, code-calculated finances and reviewed peer selections. Deeper accounting normalization, verified pre-release consensus comparisons and independent beginner/interpretation testing remain future work. Subscription-restricted consensus/ratio access is still unresolved.
