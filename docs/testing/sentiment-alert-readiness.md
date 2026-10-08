# Sentiment and alert readiness — 5 October 2026

This update prepares the main research loop for the owner's Wednesday test. It improves event-alert eligibility and source continuity; it does not establish market-wide sentiment accuracy or complete alert recall.

## Research and decisions

Financial sentiment research identifies conditional statements, opinion ownership and missing aspects as common failure modes. We used those distinctions to separate the article's tone from a specific reported development and its stated effect. This is an implementation inference from the error analysis, not a claim that the paper validates our model. [Financial sentiment error analysis, COLING 2020](https://aclanthology.org/2020.coling-main.85.pdf). Company-specific sentiment remains separate from whole-document positivity. [SemEval financial sentiment task](https://aclanthology.org/S17-2089/).

[FinBERT](https://github.com/ProsusAI/finBERT) is an open-source financial sentiment baseline. A polarity label alone cannot establish a concrete event, evidence novelty, actor attribution or whether a rumour was confirmed. We retained the existing Deus-derived classification and Kestrel-derived workflow, and improved those boundaries instead of adding an unvalidated second model to the alert path. The previous generic finding checker remains evaluation-only.

[Prometheus Alertmanager](https://prometheus.io/docs/alerting/latest/alertmanager/) separates grouping, deduplication and routing from the underlying alert conditions. We applied the same separation to research updates: one grouped delivery with original evidence, a quiet baseline, seen-source deduplication and an explicit novelty check. No Prometheus server or new infrastructure dependency was added.

## What changed

- News classification now has a separate source-development reading: a specific reported event, specific unconfirmed claim, opinion, conditional outcome, question, insufficient detail or no applicable company development. Event evidence uses exact source passages.
- Event impact is separate from article sentiment. A negative speculative headline cannot supply an adverse impact for a neutral product announcement. An adverse reporting alert requires an explicitly stated adverse or mixed effect of the reported development; rumours remain labelled unconfirmed.
- Updates to a previously seen story require cited event evidence absent from the linked earlier source. Identical selected excerpts cannot justify a new-detail alert. A changed headline can still qualify when its actual changed assertion is cited. Paraphrase and semantic matching remain model-dependent.
- Sentiment is still visible for opinions and hypotheses. Its source excerpts, separate news/Reddit/HN samples, author counts and method history remain inspectable. No automatic watch is enabled and no old reading is rewritten.
- The analyst view has a price-range graph: low, mean, median, high, retrieved quote and calculated potential price changes. The axis expands if the quote is outside the range. Missing quotes produce no fabricated percentage. [TradingView's analyst-target page](https://www.tradingview.com/symbols/NASDAQ-AAPL/forecast-price-target/) informed the information shown; this chart does not fabricate a future price path.
- The removal notice uses adjacent revert and dismiss icons in a right-aligned group, with the existing row expansion and left-to-right background animation. Keyboard labels and reduced-motion support remain.

## Social platforms: access is different from integration

| Platform | What we verified | Current app status |
| --- | --- | --- |
| Reddit | Existing bounded RSS collection; feed failures remain visible. Existing retirement warning still applies. | Integrated; availability is variable. |
| Hacker News | Public original-item API supports comment/source verification. Its audience is mainly technical. [Official API](https://github.com/HackerNews/API). | Already integrated alongside Reddit. |
| Mastodon | Public hashtag timelines can be available without a token, depending on instance settings. [Official timeline API](https://docs.joinmastodon.org/methods/timelines/#tag). Live checks returned five posts each for AAPL/NVDA; NVDA had recent English posts, while every sampled AAPL post was older than seven days. Anonymous AAPL status search returned no results. | Feasible next connector, not integrated in this update. An instance's hashtag feed is not the whole network. |
| Bluesky | The public search endpoint returned HTTP 403 in our actual check. No alternate route was used to evade that denial. | Not integrated; documented/public access must not be assumed to work. |
| YouTube | The official API exposes video comment threads and quota-based access. [CommentThreads API](https://developers.google.com/youtube/v3/docs/commentThreads/list). | Feasible with a separate project/API key and a deliberate video-selection policy. No key requested or integration claimed here. |
| X | Official access uses separately purchased API credits. [Pricing and access](https://docs.x.com/x-api/getting-started/pricing). | Not integrated; no purchase made. The OpenAI budget is not an X allowance. |
| Stocktwits | Developer registration page currently says new registrations are unavailable; help describes enterprise API access. [Developers](https://api.stocktwits.com/developers), [plans](https://help.stocktwits.com/c/stocktwits-edge/stocktwits-edge/plans-compared). | Not an immediately available free connector. No scraping workaround added. |

Mastodon is the most practical credential-free candidate from these checks, but sparse ticker coverage makes it a supplement. Before integration it needs source identity, withdrawal handling, pagination bounds, company matching, parent-context rules and separate platform samples. Adding it hastily would not prove improved investor coverage.

## Owner test boundary

The active workspace remains empty, with fixture bootstrap off. Paid tests read archived public-source packets and write evaluation artifacts only; browser and database tests use isolated storage. There is no need to clean the database again before Wednesday.

Use the [Wednesday guide](wednesday-testing-guide.md). Treat a quiet watch as a valid result when nothing new qualifies. Check source wording before accepting a label. Scheduled polling needs the app running and Mac awake. Prospective alert recall/latency, semantic accuracy across broader companies and participant usefulness remain unvalidated.
