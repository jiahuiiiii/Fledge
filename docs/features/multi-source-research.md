# Multi-source research and Devvit assessment

**9 October analysis update:** [Full-corpus sentiment batching](sentiment-batching.md) now classifies every distinct eligible saved news/social text. It supersedes the eight-news/eight-social and two-items-per-thread analysis selection below. Acquisition, permissions and date windows remain bounded.

Implemented 8 October 2026. This extends [Deus social collection](deus-social-research.md) with publisher feeds and optional Alpha Vantage/X adapters. It does not install the whole Deus application. [Verification](../reviews/2026-10-08/multi-source-research.md).

## Current connections

| Source | Thesis behaviour | Verified access on this Mac |
| --- | --- | --- |
| Finnhub | Existing company news and market data | Existing key and integration retained; not separately revalidated in this phase |
| Hacker News | Existing exact company search, original comment verification and bounded parent context | Phase80 retrieved nine Broadcom comments; retained unchanged |
| Reddit | Company-matched hot-post and comment RSS | Later phase83 verified live posts and comments; [current route and limitations](reddit-rss-collection.md). The old JSON/HTML denial remains preserved. |
| WSJ | Markets, Business and Technology public RSS headlines/summaries | All three feeds responded; Business and Technology exposed the same Broadcom report, selected once |
| CNBC, MarketWatch, NYT Business, Federal Reserve, Korea Times Economy/Business | Public RSS; exact company/ticker matching | All six feeds responded; no Broadcom match in the examined recent items |
| Yahoo Finance news RSS | Deus's configured public feed | Returned 404. Existing Yahoo price-history integration is separate |
| Google News Business RSS | Public feed with bounded same-host HTTPS redirects | Initial request returned 302. After its normal cooldown, bounded redirect handling retrieved the feed successfully; no Broadcom match in 30 examined items |
| Alpha Vantage | `NEWS_SENTIMENT`, company-filtered headlines/summaries | Key added; first live Broadcom request on 8 October returned an access/usage-limit message rather than news. Existing one-day cooldown retained; successful live access remains unverified |
| X / Twitter | Official recent-search API; original posts only | Owner has deferred X; remains disabled. Adapter tested with controlled responses, not live access |
| Nitter | Not activated | Upstream is archived and its issue tracker reports broken public instances; it is not a dependable substitute for X access |

A feed responding successfully does not establish complete company coverage. This is a bounded selection of available material. News feeds are not social opinions; Alpha Vantage's own sentiment scores are not imported as Thesis labels.

## User workflow

First company open and **Refresh research** queue independent market, filings, chart, valuation, Reddit, HN, publisher-feed, Alpha Vantage and X steps. Four queue workers handle independent steps; the publisher step uses up to three concurrent feed readers. **Refresh & analyse** waits for its news/discussion steps, then explicitly requests analysis using the original AI allowance.

In Evidence radar, expand **Publisher feeds & source connections** to inspect each feed's last check, matched count and failure/setup reason. The **X / Twitter** sample is separate from Company news, Reddit and Hacker News. A missing connection never becomes a neutral result. A source acquisition does not rewrite an earlier saved interpretation; request a new analysis to interpret the new sample.

Enabled news/social watches use the same additional collectors. One failed news provider does not prevent other providers from being checked. Watch histories record the extra provider coverage and flag failed sources. No watch was enabled by this installation, and no alert backlog or Telegram message was sent.

## Connection setup

The existing private `.env` and `.env.example` contain:

```dotenv
ALPHA_VANTAGE_API_KEY=
X_BEARER_TOKEN=
THESIS_X_ENABLED=false
```

Public RSS needs no additional key. Existing `THESIS_LIVE_DATA_ENABLED=true` is required. Alpha Vantage's [current documentation](https://www.alphavantage.co/documentation/#news-sentiment), checked 8 October 2026, labels `NEWS_SENTIMENT` **Premium**. A free API key alone does not unlock it; verify that the account includes this endpoint before configuring it. Alpha Vantage is optional: Finnhub and public publisher RSS remain independent news sources. Thesis caps this integration at 25 requests per UTC day and one per minute across companies; those local caps do not imply free-tier endpoint access.

The owner added the Alpha Vantage key on 8 October. A single actual Broadcom request at 05:00 UTC returned the adapter's access/usage-limit outcome and retrieved no news. The saved diagnostic combines provider access and quota messages, so it does not establish which specific account restriction caused the response. No retry or cooldown override was made, and no OpenAI call was used. The private outcome is retained in `.local/live-tests/alpha-vantage-20261008/verification.json`.

The error handler now distinguishes recognised invalid-key, request-limit, Premium-access and invalid-request responses using code-written messages. A rate-limit message advertising premium plans remains a rate-limit diagnosis. Unknown messages stay explicitly unclassified; raw provider strings, which can echo credentials, are not displayed or persisted. The historical generic response cannot be recovered or retrospectively labelled as a confirmed plan rejection. Premium access is the documented requirement, not proof of the cause of that particular response.

While the existing one-day pause is active, source status shows its expiry as a **Thesis cooldown**, not Alpha Vantage's confirmed quota-reset time. Refreshes during the pause make no request and preserve the original check and diagnostic. Waiting can allow a future check; it cannot grant missing Premium access. If already subscribed, confirm that the private key belongs to the entitled account or contact Alpha Vantage support. No subscription is necessary to keep using Thesis's other news sources.

For X, use a token from the [X developer console](https://developer.x.com/) with recent-search access, then explicitly set `THESIS_X_ENABLED=true`. X data has [separate usage billing](https://docs.x.com/x-api/getting-started/pricing); this is not part of the US$30 OpenAI allowance. Thesis caps X at 20 requests per UTC day, one per minute, and 20 returned posts per request. No X data requests or charges were made during this phase.

Both adapters also keep a 15-minute company cooldown. A provider rejection is shown explicitly: 429 creates a cooldown, 401/403 stops further requests. An Alpha Vantage usage/access response stops requests for a day. Correcting a previously rejected connection requires deliberate review of its saved denial state; merely restarting or resetting the workspace does not erase it. Never put credentials in chat or Git.

## What is retained and selected

Publisher feeds are shared through a 15-minute local cache. Each feed examines its first 15–30 entries, accepts only an explicit, aware publication date in the last seven days, and retains matched headline/summary text and its original link. Missing dates are not replaced with the current time. It does not retrieve full articles or bypass publisher access controls. Feed items can be incomplete, out of date or irrelevant.

A single URL received through different feeds remains separately attributable in storage, but only one enters the news candidate list. Known tracking parameters, including WSJ's `mod`, do not create another article. Exact text deduplication and existing coverage grouping remain additional boundaries; this is not a guarantee that all syndication is detected.

X searches by ticker/company name. It excludes replies, quotes and reposts because their necessary context is not acquired by this adapter. Author identifiers are hashed locally. The 24-hour setting is enforced after retrieval; a seven- or thirty-day setting retrieves at most seven days through the recent-search API. Older locally saved originals can appear in a thirty-day view, but that is not a complete thirty-day archive. No engagement-based vote weighting is added. Current source disabling and recorded withdrawals apply; automatic X deletion/compliance-stream reconciliation is not implemented.

The classifier remains bounded to eight news and eight social texts. Sentiment v18 adds X to the platform guidance and summaries; theme v8/checker v4 support a separate X scope and exclude its generic title as evidence. No model, pricing profile or automatic AI stage was added. Existing saved results keep their method, text and meaning. Prior interpretation errors remain open; broader coverage does not establish better sentiment or alert accuracy.

## Does Devvit fit?

Devvit can run a Reddit-native app. It also supports authenticated [external endpoints](https://developers.reddit.com/docs/capabilities/server/external-endpoints), but that capability is limited-access and requires a request. Its [external fetch policy](https://developers.reddit.com/docs/capabilities/server/http-fetch-policy) requires specific domain approval and justification for unsupported external services. The [Devvit rules](https://developers.reddit.com/docs/devvit_rules) expect a benefit delivered within Reddit and include data handling/deletion requirements.

Our conclusion: Devvit is not an immediately available replacement for this external Mac application's blocked Reddit collector. An approved Reddit-native companion could be a future integration, but a normal Devvit registration does not establish permission to export discussions into Thesis for external AI analysis. No Devvit app was created, registered, uploaded or described as operational in this phase.

The next concrete step is to explain the actual external research use case to Reddit: selected investing discussions, private company research, attributed sentiment summaries, external OpenAI inference, intended retention/deletion behaviour and possible future commercialization. Ask whether they approve a Devvit companion with external endpoints or require external Data API access. Once the approved route and credentials are known, implement that connection and deletion lifecycle against those terms. An on-Reddit app that only benefits users there would be a distinct product surface, not a silent architectural swap for Thesis.

## Upstream references

- [Pinned Deus source tree](https://github.com/c0vo/Deus/tree/74d5aea8b0acf72e1851dfc841f9f1408e9e6609): publisher list, RSS fan-in, Alpha Vantage news adapter and platform classification patterns.
- [Alpha Vantage documentation](https://www.alphavantage.co/documentation/): `NEWS_SENTIMENT` request/response contract.
- [X recent search](https://docs.x.com/x-api/posts/search-recent-posts): authenticated post search.
- [Nitter issue and archived repository](https://github.com/zedeus/nitter/issues/1442): current maintenance/access limitation.

## Scheduled checks and connection failures — 9 October 2026

A shared refresh interval is a deferred check, not a publisher outage. The exact older “This source was checked recently; saved data is retained.” diagnostic is projected as **deferred** without rewriting the original record or claiming a successful request. A new deferred attempt releases only its own current lease and preserves any previous actual success/failure, date and matched count. New companies remain unchecked/deferred until a real response is processed. A wholly deferred publisher step reports cached work, not a completed fetch.

The shared RSS cache starts its fifteen-minute lifetime after response validation so it cannot expire before the request interval merely because collection started earlier. Publication dates, company matching, size/entry limits, original text, provider pacing/denials and access checks remain unchanged. Neither cache reuse nor waiting is proof of new company news.

News status distinguishes successfully checked feeds, genuine failures, deferred checks and feeds not yet checked for the company. Successful checks can have zero company matches. Details group deferred checks and show the next permitted check time; a denied connection never promises permission after its timer expires. X with its explicit enablement flag off appears as an optional source that is off, separate from news failures. Source-only refresh remains available through Research updates; paid analysis keeps its independent restriction.

The Apple and Qualcomm screenshot state had eleven exact timer diagnostics. A bounded normal RSS recovery checked ten responding publisher feeds for each company (Qualcomm reused the shared responses); Apple retained two matching reports. Yahoo's configured RSS still returned HTTP404. Alpha Vantage was not checked for those companies and X remains off. The saved Finnhub check brings each company to eleven of thirteen news feeds successfully checked. These counts describe checks, not eleven publishers contributing stories. [Verification](../reviews/2026-10-09/feed-availability.md).

## Company discovery and refresh counts — 9 October 2026

Search names strip an explicit slash-delimited incorporation code only after a legal suffix (`QUALCOMM INC/DE` → `QUALCOMM`). Registered issuer identity remains unchanged. AMD/Advanced Micro Devices, Marvell/Marvell Technology and Micron/Micron Technology have bounded search names tied to both their symbol and registered name. Original-text matching shares these names; shorter Micron and AMD mentions retain case constraints to avoid ordinary lowercase fragments/units. Unknown tickers still require explicit financial context. No fuzzy match, new community, broader date window, request-limit change or new model classification is introduced.

Research updates separates currently readable saved news/discussion counts from the results of a particular check. Saved counts use the existing permission, current-version, date-window, deduplication and withdrawal rules; they are source counts, not relevant/analysed developments. Finnhub reports its own returned news count. Publisher results name the checked sample, failures and deferrals; a wholly deferred attempt never claims zero matches. Reddit reports when no matching posts meant no comment requests, and cache-only work states that no new request was made. HN reports its bounded search window. Disabled discussion sources are not successful empty checks.

Exact older summary formats are clarified at read time without rewriting the retained load journal or historical analysis. Earlier zero results can remain historical zero results after a corrected new check; the current saved-source total is separate. [Verification](../reviews/2026-10-09/zero-source-counts.md).

### Saved results during a skipped repeat

Research updates leads each news/discussion row with current permitted saved counts even when a new request is deferred. A skipped attempt can also show the nearest earlier recorded non-deferred result, explicitly dated and selected for the same owner, company, source and discussion window before that attempt. A more recent failure is retained ahead of an older success. Historical counts never prove current availability; withdrawal/permission/date filtering still controls the saved count. Original load journals remain unchanged.

Cooldown reasons and the timestamp of that specific attempt are expandable under **Refresh details**, rather than presented as ongoing waiting. Optional X that is currently off is labelled **Off** and excluded from connection-failure totals; enabled X failures and the independent AI block retain their meaning. The refresh intervals, provider guards and original accounting hold are unchanged. [Follow-up verification](../reviews/2026-10-09/cooldown-results.md).
