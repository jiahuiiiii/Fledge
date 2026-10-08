# Source and adaptation record

Phase 80 re-inspected the complete public Deus revision `74d5aea8b0acf72e1851dfc841f9f1408e9e6609`. `data/sources/reddit_source.py`, `data/sources/hackernews_source.py`, `pipeline/aggregator.py` and `pipeline/classifier.py` inform the company discovery → original-source verification → reply enrichment → duplicate/diversity selection → structured classification flow. New Thesis implementations are `reddit_research.py`, `social_threads.py`, the expanded `hackernews.py`, and `deus_sentiment.py`. Social vocabulary/author-attribution guidance is adapted into the existing single metered classifier; Deus's separate Reddit provider route is not copied. PostgreSQL state, source-version/withdrawal boundaries and tests are new Thesis work. No runtime dependency on the upstream checkout is introduced. The old Reddit-host fallback, Nitter mirrors, numeric trading score, predictions and embeddings are not imported. [Implemented scope and access limits](docs/features/deus-social-research.md).

Phase 76 executes public Prosus FinBERT, HKUST FinBERT-tone, CardiffNLP Twitter RoBERTa and VADER in an **isolated evaluation environment**, using Transformers/PyTorch for local inference. These are actual downloaded classifier weights/library use, but are not production dependencies or part of the app's alert path. Pinned versions, hashes, outcomes and limitations are in [the comparison](docs/testing/local-sentiment-models.md) and `experiments/sentiment_models/`. FinTwitBERT, NewsSentiment and FinEntity remain research references only. Earlier statements below about no imported sentiment weights describe their historical phase and the still-unchanged app runtime.

Phase 75 adapts the team-owned local Kestrel `kestrel_backend/app/service/telegram_service.py`, `app/api/v1/telegram.py`, scheduler alert-message workflow and `kestrel_frontend/src/components/NotificationChannels.jsx` connect/disconnect patterns, inspected 5 October 2026. Thesis implements a new local polling connection, hashed expiring private-chat link, owner-scoped durable outbox and deterministic evidence messages. It does not copy Kestrel credentials, database records, public webhook, hardcoded bot handle or its swallowed-send-error behavior. No new runtime package is required. [Telegram contract](docs/features/telegram-alerts.md).

Phase 31 adds new Thesis orchestration around the existing metered event classifier and Kestrel-derived condition evaluator. Optional event-watch revision binding, activation records and exact-input reuse are local implementation work. No additional framework or open-source dependency is introduced. [Contract](docs/features/event-watches.md).

Phase 30's daily filing schedules, journal, controls and tests are new Thesis code around its existing SEC reader. They reuse the same Deus-derived normalization and Kestrel-derived evaluation path; no additional open-source platform is copied and no upstream project is credited with this scheduler implementation. [Contract](docs/features/daily-filing-checks.md).

Phase 5 extends the adapted Kestrel numerical evaluator with new user-defined reporting-age rules, ordered clock-driven assessments and history displays. The age arithmetic, cursor/queue changes and focused recovery tests are Thesis implementation work; they are not claimed as upstream Kestrel or Deus behavior. Existing upstream attribution below remains applicable.

Inspected 1 October 2026 by cloning the public repositories without using stored Git credentials. Remote heads matched the planning references below. This app is a bounded adaptation of selected working components; it does not run the full upstream products.

| Source / revision | Imported mechanism | Local implementation and changes |
| --- | --- | --- |
| [Kestrel main](https://github.com/jiahuiiiii/Kestrel/tree/77cd15cee1aa1d91be81e9d99a67309f6ee7e621) | `src/api/client.js` | `frontend/src/api/client.js`: keeps cookie requests, typed API errors and `result` unwrapping; replaces old routes and refresh login with the explicit local demo session. |
| Same Kestrel revision | `src/lib/thesisDiff.js` | `frontend/src/lib/kestrelDiff.js`: retains stable condition identity and numeric form filtering; replaces multipart mutations and `<None>` sentinel with one atomic expected-revision save. Finite and blank-value validation is stricter. |
| Same Kestrel revision | `src/components/Modal.jsx` | `frontend/src/components/Modal.jsx`: portal and Escape dismissal adapted to native dialog focus containment. The new compact workspace is tailored to the accepted UI direction. |
| Same Kestrel revision | React/Vite application structure and package manifest | React 18 retained. Build tooling updated; unused routing, icons and Tailwind dependencies removed from this narrow slice. Styles use ordinary CSS; icons and fictional charts are local SVG components. |
| [Deus main](https://github.com/c0vo/Deus/tree/74d5aea8b0acf72e1851dfc841f9f1408e9e6609) | `data/models.py` | Copied into `thesis/research/deus_models.py`; its `NewsArticle` is used by shared evidence normalization. |
| Same Deus revision | `pipeline/aggregator.py`; `pipeline/grounded_answer.py::_evidence_from_articles` | `thesis/research/pipeline.py`: adapts article normalization and source packaging. Content hashes distinguish revisions at a shared URL. Recorded ingestion replaces live adapters, global SQLite, provider settings and empty-on-failure fallbacks. |
| [Kestrel backend development](https://github.com/brandontan2003/kestrel_backend/tree/4278cbe614d10095039b5e2ea580535ad72d8334) | `pipeline/evaluator.py` | `thesis/monitoring/evaluator.py`: adapts three-valued ALL evaluation. A definite failure dominates unknown; an empty condition set is invalid. Adds typed scope, decimal comparison and restatement handling; removes trade firing. |

The latest frontend was the reference. The older standalone Kestrel ML schema was not imported. The new PostgreSQL migration, transaction services, fixtures and job runner were written for Thesis. Previous editorial and trading-workspace previews were authored in this chat; their layout concepts inform the new application.

The user states that Deus and Kestrel are built by their team and explicitly authorized reuse. No standalone LICENSE or COPYING file was found in these inspected source checkouts. Do not represent this as a new open-source licence grant, invent a permissive licence, or remove existing attribution. Dependency package notices remain with their packages. Commercial rights and any required contributor permissions should be resolved before external distribution.

All Northstar data, source documents, claims, prices and events are authored fiction. Software reuse does not establish rights to any future market or news feed. There are no runtime imports from Fork, the source clones or other sibling projects.

## SEC adapter addition — 2 October 2026

`thesis/research/sec/` is new code around the official SEC companyfacts and submissions contracts. It reuses the existing HTTP client, PostgreSQL acquisition/history, Deus article normalization and Kestrel-derived evaluator; no EdgarTools/OpenBB platform dependency was introduced. Supported issuer CIKs were checked against SEC issuer/filing pages. The original passage-selection route remains authored-only; phase 6 adds a separate authorized market briefing. Synthetic SEC-shaped test payloads were written for software verification and are never presented as real company results in the saved application. [Source contract and live-validation status](docs/features/sec-fundamentals.md).

## Finnhub pitch adapter — 2 October 2026

`thesis/research/market.py` adapts Deus `data/sources/finnhub_source.py` at the Deus commit above: headline, summary, publisher, URL, provider ID and publication timestamp mapping. It uses company-news rather than general market news. Thesis adds header-based key handling, bounded transport, explicit errors, persistent pacing/cooldowns, company-scoped immutable versions, independent quote storage and late-response fencing. The upstream silent empty-list fallback, query-string token and global storage are not reused. `market_brief.py` extends the existing metered source packaging with a new structured, cited AI briefing; it is not claimed as upstream model behaviour.

## News/social sentiment and watch adaptation — 2 October 2026

At the Deus revision recorded above, `data/sources/reddit_source.py` supplies the public Atom-feed approach and `_plain_summary` mechanism (strip tags before unescaping, remove the submitted-by footer). `thesis/research/social.py` adapts these with an allowlist, bounded XML/HTTP, explicit errors, publication/availability times, persistent pacing, immutable versions, hashed author counts and company matching. No account cookies, proxy rotation, denied-access workaround or comment scraper is used.

Deus `pipeline/classifier.py` supplies the batch item labels, structured taxonomy and completeness-check pattern used by `thesis/research/sentiment.py`. Thesis separates supplied news framing from expressed social opinion, validates exact same-item passage IDs, counts labels in code and uses the existing metered OpenAI adapter. Upstream synthetic confidence, trade direction and price-prediction outputs are omitted. No additional sentiment library or model weights were imported; this is an adaptation of the team's Deus classifier using the configured OpenAI model.

Deus `bot/alerts.py`, `pipeline/event_tracker.py` and `pipeline/ranker.py` were inspected for alert/event flow. The watch, transactionally persisted delivery identities, private reviews, stored seen-content set and sample-change policy are newly written Thesis code; upstream Telegram sending, global SQLite and urgency/ranking outputs were not copied. Kestrel-derived source inspection, API client and revision-review interactions remain the surrounding UX.

## Phase 12 private relevance alerts

`thesis/research/idea_alerts.py`, migration 013 and the private alert review UI are new Thesis implementation. They reuse the existing exact-passage helpers, shared news/social sampling, metered provider adapter and Kestrel-derived API/review conventions. This does not claim that upstream Deus or Kestrel supplied the private revision matching or its evaluation results.

## Phase 14 financial research

`thesis/research/sec/performance.py`, migration 014 and `FinancialPerformance.jsx` are project-specific additions around the existing SEC adapter and tested ratio selector. They consume the already authorized whole-entity SEC bundle; no additional finance library or upstream code was copied. Existing transport, decimal, immutable-source and Kestrel-derived client conventions remain in use. The separate one-off original-filing audit uses the SEC inline-XBRL facts and XBRL transformation registry; its source and retained results accompany the private live-test evidence. This audit reader is not a new production HTML ingestion path.

## Phase 15 valuation scenarios

`thesis/valuation.py`, `thesis/research/multiples.py`, migration 015 and `ValuationPanel.jsx` are new project-specific code reusing the installed SEC snapshots, Finnhub transport, account boundary and Kestrel-derived client conventions. Finnhub's official client verifies the `stock/metric` endpoint mapping. P/E/P/S calculations and sensitivity are deterministic application code with explicit user assumptions; no external valuation engine, new sentiment model or additional dependency was imported. References are provider-supplied values rather than an independently computed peer dataset.

## Phase 16 alert quality

The evaluation runner/scorer/reviewer packet and quoted sentence-boundary handling are new Thesis code. The sentiment prompt refines the existing Deus-derived classification contract around target-company business relationships. No additional model, library, social platform or external evaluator was added. Actual source copies and authored expectation manifests remain local evaluation evidence, not an upstream/public dataset.


### Phase 17 — question-answer connections

Extends the existing Deus-derived structured source classification and Kestrel-derived private review workflow with an application-authored `answers` relation and exact question anchors. No additional third-party code, provider, model, licence or data source was introduced. Existing stored source text and the original shared OpenAI ledger are reused for bounded development evaluations. Earlier outputs are retained with their own prompt identities.

## Phase 18 — historical daily prices

`thesis/research/price_history.py` adapts the daily Yahoo chart endpoint, aligned OHLCV-array parsing and cached-history approach from Deus [`pipeline/price_feed.py`](https://github.com/c0vo/Deus/blob/74d5aea8b0acf72e1851dfc841f9f1408e9e6609/pipeline/price_feed.py), re-inspected at the same recorded commit. Thesis adds explicit dated windows, New York calendar handling, exact decimal strings, immutable whole-window snapshots, validation, restricted source-role persistence, pacing/cooldowns, late-attempt fencing and visible failures. It uses an identifying application User-Agent and no alternate-host or automatic-retry fallback. The source's adjustment-vintage warning informs whole-snapshot replacement; no corporate-action reconciliation is claimed.

Migration 016, the API/read model, `HistoricalPrices.jsx` and the enhanced accessible/responsive SVG chart are Thesis additions. Existing HTTPX and Kestrel-derived client conventions are reused. The yfinance project was inspected as a reference for the public endpoint; no yfinance code/package, external charting package or new model was imported. Team-code reuse and the original attribution apply; public Yahoo access for this local demonstration does not establish a production feed agreement.

## Phase 19 — comparing news coverage

`thesis/research/coverage.py` and the accompanying classifier, watch and UI changes are new Thesis code around the existing Deus-derived batch classification and Kestrel-derived review conventions. Deus `pipeline/aggregator.py` and `pipeline/event_tracker.py` were re-inspected at the recorded commit: URL deduplication and ticker/date/type calendar deduplication do not establish semantic equivalence between reports, so those keys were not substituted for evidence-backed comparisons. No new library, model, provider, embedding store or database was imported. Source identity, citation validation, metered requests and immutable history reuse the existing app infrastructure.

## Phase 20 — question-focused answers

`thesis/research/answers.py` adapts the evidence-sufficiency/abstention and dated numbered-evidence approach inspected in Deus [`pipeline/grounded_answer.py`](https://github.com/c0vo/Deus/blob/74d5aea8b0acf72e1851dfc841f9f1408e9e6609/pipeline/grounded_answer.py), specifically `grade_context`, `GradeVerdict`, `GRADER_PROMPT`, `_evidence_from_articles` and `_number_evidence`. Thesis combines sufficiency and answer generation into one metered structured request, resolves exact passages in code, reuses current permitted news/social/filing stores and keeps private immutable question history. Deus's global SQLite/config, Tavily fallback and autonomous price explanations are not imported. Migration 017, lexical source selection, bounded follow-up and UI/export are new Thesis code using Kestrel-derived client/review conventions. No extra dependency, source provider or API key is introduced.

## Phase 21 — scheduled-check history

`thesis/monitoring/watch_history.py`, migration 018 and `WatchCheckHistory.jsx` are new Thesis code around the existing Deus-derived source/classification adapters and Kestrel-derived review/client conventions. Starts/completions, source-status snapshots and read-only pagination reuse the restricted account and source-access boundaries. The Finnhub cooldown now returns the app's existing typed conflict to support the scheduler's documented shared-cache path. No upstream framework, data source, key, delivery channel or model was added.

## Phase 22 — recorded sentiment sample comparison

`thesis/research/sentiment_history.py` and `SentimentHistory.jsx` are new read-only Thesis views over the existing Deus-derived source/classification records. They reuse Kestrel-derived API/source-modal conventions and the existing complete-packet access check. No new upstream code, package, database, migration, model, prompt or source provider was introduced. Exact content comparison describes input/label differences, not semantic event equivalence or market sentiment measurement.


## Phase 23 — expanded operating-company catalogue

`thesis/research/catalogue.py` centralizes the existing SEC company registry and lexical candidate matcher, with NVIDIA, Amazon and Meta identities checked against their public SEC submissions and original filings. This is new application glue around the already adapted Deus sources/classifier and Kestrel-derived workspace. No new upstream code, package, model, prompt, provider or schema was introduced. The original-filing reconciliation reuses the prior bounded audit reader and is retained with actual public payloads.


## Phase 24 — sentiment specificity and original-source reading

`OriginalSample.jsx`, its selector and tests, the classifier instruction revision and method-compatible reversal guard are new Thesis code around the existing Deus-derived classification and Kestrel-derived source/review interfaces. No new library, source, model, provider, schema or API key was added. Saved actual packets and wholly authored contrast fixtures are evaluated separately under the same original OpenAI ledger; authored fixtures never enter product research records.


## Phase 25 — previously seen reporting updates

The changed-report watch rule, comparison disclosure and two-source weekly export are new Thesis application logic using the existing Deus-derived classifier/coverage records and Kestrel-derived review interfaces. No additional upstream code, library, model, source, schema or provider was introduced. The offline evaluation replays retained actual-source/model results and labels its separately authored contrasts and constructed seen history.

## Phase 26 — combined review inbox

`UpdateInbox.jsx` and the preview helper are new Thesis presentation code over the existing periodic-review read model. Embedded company/private cards and exact-condition navigation reuse the Kestrel-derived review/source interfaces and retained Deus-derived research records. No additional upstream code, dependency, database, prompt, provider or source was introduced.

## Phase 27 — structured expectation readings

`thesis/research/expectations.py`, migration 019 and `ExpectationsPanel.jsx` are new Thesis application logic over the existing Deus-derived evidence/source pipeline and Kestrel-derived draft/source-dialog conventions. Selection reuses the question research module's bounded lexical ranking and citation segmentation; storage, permissions, exact quotations and metering reuse the current application infrastructure. No additional upstream code, library, model or source provider was added. Management and analyst views are extracted from retained Finnhub snippets, not misrepresented as a new primary-guidance feed.

## Phase 28 — numerical risk roles

Migration 020, role-aware result wording and the editor controls are new Thesis code around the existing Kestrel-derived typed evaluator and atomic revision workflow. The required-only comparison retains its earlier method identity; the numerical-risk extension has a distinct evaluator version. No additional upstream code, dependency, model, prompt, provider or source was introduced. Saved real-filing tests reuse the existing SEC corpus with explicitly authored risk rules.

## Hacker News discussion adapter — phase 29

`thesis/research/hackernews.py` is a new bounded adapter around the existing Deus-derived social/classification flow. It uses [Algolia HN Search](https://github.com/algolia/hn-search) for candidate IDs and the [official HN API](https://github.com/HackerNews/API) for original comment text/deletion state. No upstream application code or new model package was copied. The archived search repository is a documented dependency risk; successful current retrieval is not a maintenance guarantee. Kestrel-derived source review and private alert behavior remain the presentation/monitoring foundation. [Method](docs/features/social-platforms.md).

## Original conversation inspection — phase 32

`thesis/research/conversation.py`, migration 024 and `SocialConversation.jsx` are new Thesis glue around the existing original HN item transport, persistent source clock and Kestrel-derived source dialog. They use the official API's immediate-parent relation, not copied upstream application code. No new package, classifier, model, data vendor or key is introduced. Parent text remains separate inspection material and never enters existing model requests.


## Phase 33 discussion themes

`thesis/research/discussion_themes.py`, migration 025 and `DiscussionThemes.jsx` are new Thesis code around the existing Deus-derived source/classifier and Kestrel-derived API/source-inspection patterns. No additional open-source sentiment model, weight package or framework was imported. The bounded thematic/supporting-and-opposing-evidence use case follows the reconciled architecture; its prompt, validation and evaluation are not claimed as upstream Deus behaviour. [Contract](docs/features/discussion-themes.md).

Phase 34's per-claim source contract, validation, legacy presentation and export are new Thesis implementation on the same adapted Deus/Kestrel research path. No new dependency or third-party classifier was imported. [Review](docs/reviews/2026-10-03/theme-claims-phase-review.md).

The phase-34 `discussion_theme_check.py` evidence-review/filtering stage is new Thesis code using the already configured model and ledger. No separate open-source model, external evaluator or third-party package was added. It is not independent validation of the Deus-derived classifier.

## Phase 35 — context-aware sentiment inputs

`sentiment_context.py`, the classifier/alert integration and `SentimentContext.jsx` are new Thesis code connecting the phase-32 original HN records to the existing Deus-derived classifier and Kestrel-derived evidence/review views. No upstream framework, model weights, new provider or package was added. Original parent collection and current-context classification are distinct operations; input verification does not establish model quality.


## Phase 36 — private alert conversation context

The private matcher, context disclosure and shared export helper are new Thesis glue between the existing Deus-derived research flow and Kestrel-derived private review workflow. They reuse phase 35's pinned original-parent evidence. No third-party sentiment model, framework, data source or dependency was added. No claim of improved semantic accuracy is made from mocked tests.


## Phase 37 — theme conversation context

The theme prompt/schema, bounded checker projection and finding-level context disclosure reuse phase 35's original-parent records and phase 36's export helper. They are new Thesis integration around the existing Deus-derived research and Kestrel-derived review interfaces. No new upstream code, package, provider or model was imported. Input provenance is not semantic verification.


## Phase 38 — question research context

The question-source projection, scoped parent citations, withdrawal checks and UI/export reuse the existing Deus-derived question/sufficiency approach and phase 35's original-parent store. This is new Thesis integration, not a newly imported open-source classifier or source. No new model, package, database or service was added.

Phase 39's optional context-watch stage, settings and journal fields are new Thesis orchestration around the existing original-HN collector, Deus-derived sampler/classifier and Kestrel-derived review flow. It adds no third-party package, model or platform. Retained original-source replay is an acquisition test, not upstream model validation. [Contract](docs/features/watch-conversation-context.md).

Phase 40's current-source projection and preview are new Thesis code around the existing Deus-derived source selector and Kestrel-derived source inspection/workspace response. It imports no library or model and performs no source/model call on read. [Contract](docs/features/current-sentiment-sources.md).

## MiSans Latin — 8 October 2026

The app now uses Xiaomi's official MiSans Latin Regular, Medium, Semibold and Bold WOFF2 files, unmodified, downloaded from the [official font page](https://hyperos.mi.com/font/en/download/). Source URLs, hashes and the original license are retained in `frontend/public/fonts/`. The app footer provides the required MiSans credit. Font files are served locally.


## Phase 81 — Deus publisher feed fan-in and official X adapter

`thesis/research/source_hub.py` adapts the publisher URLs, bounded RSS/Atom fan-in and Alpha Vantage company-news flow from the pinned Deus 74d5aea source. The original snippets stay news; provider scores are not copied as Thesis sentiment. Durable PostgreSQL leases, rate limits, source permissions, shared caching and canonical-URL selection are new Thesis integration. `x_source.py` is a new official API adapter informed by X's published recent-search contract, not Deus's unfinished Twitter collector or Nitter mirror fallback. No dependency or model was added. Devvit was researched but not installed. [Contract, source links and limitations](docs/features/multi-source-research.md).
