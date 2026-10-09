# Reddit posts and comments through RSS

**9 October analysis update:** [Full-corpus sentiment batching](sentiment-batching.md) now classifies every distinct eligible saved news/social text. It supersedes the eight-news/eight-social and two-items-per-thread analysis selection below. Acquisition, permissions and date windows remain bounded.

Implemented 8 October 2026 for the owner's requested MVP integration. [Actual tests and remaining gaps](../reviews/2026-10-08/reddit-rss-integration.md).

## Workflow

First company open, **Refresh research**, **Refresh & analyse**, and existing enabled news/social watches use `reddit_rss.py` through the normal company collection service. No additional key, account, cookie, proxy, scraper service or Python dependency is needed. Acquisition itself has no OpenAI charge; analysis still uses the original explicit request and budget controls. No watch is enabled by this change.

The initial implementation adapted Deus revision `74d5aea`'s `/r/{community}/hot/.rss` route. Following the owner's AVGO suggestion, new discovery uses company/ticker RSS search and can reuse saved hot feeds. It uses Thesis's identifying User-Agent, standard HTTPS and no redirects. Reddit comment RSS is a separate implementation; Deus's old-host HTML enrichment is not the comment transport.

- Make one RSS search across the company's enabled communities, combining the ticker and registered company alias, for example `"AVGO" OR "Broadcom"`. Inspect at most 50 results in the selected date window and verify the original title/body, community, post ID and publication date. Bare `AVGO`/`avgo` is now an explicit recognized alias; common-word ticker safeguards remain.
- Supplement with any already saved hot-feed bodies, at most 25 posts per community, without extra hot-feed requests. Deduplicate post IDs before selecting comment threads. Search discovery uses immutable `reddit-company-search-rss-1` metadata; earlier hot-feed records retain their original method. Search results remain bounded, not a full historical archive.
- Prioritize company names in titles, then recent posts, for up to three comment feeds. Validate the feed URL, root post ID, title and original publication time.
- Inspect at most 50 comment entries per thread; retain up to 12 that name the company in their own wording. Preserve original IDs, bodies, links and hashed author identities. Removed/deleted entries are withheld through the existing withdrawal path.
- Comment feeds supply `updated`, without a verified creation time or immediate-parent ID. Store that date with the immutable `reddit-comment-rss-updated-1` discovery method; expose `feed_updated` and its limitation to source previews, model inputs and exports. Do not pretend the root post is each comment's immediate parent. Contextless replies such as “this” are excluded.
- Keep existing exact-text grouping, two-items-per-thread selection and the eight-social-source analysis limit. Retrieved comments are not all independently analyzed. News, Reddit and other social platforms remain separate.

The selected 1/7/30-day discussion window applies to post publication dates and comment feed-update dates. First availability here remains separately recorded. These windows do not promise exhaustive historical retrieval, author independence or market representativeness.

## Communities

Migration 041 adds five community records without changing old permissions or monitoring settings:

| Scope | Communities |
| --- | --- |
| All registered companies | stocks, investing, wallstreetbets, stockmarket, valueinvesting, securityanalysis |
| Broadcom / AVGO additionally | broadcomstock |
| NVIDIA / NVDA additionally | nvda_stock |

`social.company_feeds` intersects this list with currently enabled sources. The relevant communities are combined into the same single search request; adding them does not introduce one search request per subreddit. Company-specific forums do not establish relevance by themselves: original text must still match the company. Source coverage shows the configured search communities, which does not imply each returned relevant posts. The historical generic feed collector retains its original three-community scope and existing denied transport.

## Pacing and recovery

Shared raw-feed caching, capability status and request pacing use the existing `public_feed_cache`, `provider_checks` and `provider_clocks` tables; no migration is required. Global RSS request starts are at least 30 seconds apart, with a local limit of 240 per UTC day. A new live company check is limited to once per 15 minutes. Uncached multi-feed research can take a few minutes; the normal progress queue remains visible.

Those numerical limits are Thesis safeguards shared across its companies, communities and comment requests, not Reddit-published allowances. The actual HTTP 429 responses originate at Reddit. On 8 October the expanded search returned HTTP 200 with `X-Ratelimit-Remaining: 0.0` and `X-Ratelimit-Reset: 53`; a comment request 30 seconds later returned 429 with reset 23. This establishes that the fixed spacing was too short for that observed window, without proving Reddit's overall quota or IP/account enforcement scope. The [official Data API limits](https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki) apply to eligible OAuth clients and are not an allowance for this unauthenticated RSS route.

The reader now records exhausted response windows in the shared persistent `reddit-rss:quota` clock, waits until the reported reset plus one second (or the longer existing local spacing), and rechecks before dispatch in case another worker extended the window. Shorter headers never shorten an existing wait or clear a 429/denial. Missing/malformed headers do not invent a quota. A backlog exceeding 60 seconds is deferred visibly instead of holding a worker indefinitely; the RSS company lease is six minutes for up to four paced requests. Actual 429 responses still preserve the existing conservative pause. Initial 429 messages now include the local next-check time. Header behavior is verified with controlled responses; the first broader live run's 429 remains preserved, and this does not establish elimination of rate limits.

An HTTP 429 pauses all RSS requests for at least 15 minutes and honors a longer Retry-After. No request to another feed follows a rejection in that collection run. Previously acquired bodies can still be read: normal cache freshness is 15 minutes; outage/recent-company recovery can use saved bodies up to 24 hours old, with the requested discussion date window still enforced. Missing cached feeds remain visible gaps. A repeated company refresh within its live cooldown only reads saved feeds and does not extend the live-check interval.

A 401/403 blocks its RSS capability persistently. Search and hot feeds share the same post capability: neither can bypass the other's denial. Cached retrieval does not bypass that capability denial. Redirects/login/challenge pages are not followed and cannot become an empty successful sample. Post and comment outcomes are displayed separately, including retained counts when coverage is partial. Permission changes during acquisition prevent newly disabled feeds from being retained. Search caches are separately keyed by company query, discussion window and enabled communities.

The separately recorded old JSON/HTML access denial is unchanged. Explicit owner authorization to integrate the demonstrated working RSS capability is not a reset of that denial. The experimental HTML reader remains off. RSS requests stop at the existing 13 November 2026 retirement boundary; retained historical sources remain readable.

## Verified scope

The initial live NVIDIA hot-feed test first retained seven posts and 12 comments; the app's subsequent coordinated load reached stocks and investing and retained nine posts plus the same 12 comments. Wallstreetbets returned 429. A comment feed returned 77 entries including its root post; the bounded parser inspected 50 comments and retained 12 company-matched comments. This establishes a working MVP path, not uninterrupted access to every community.

The later AVGO/Broadcom search returned three candidates and two verified company mentions, one using the ticker and one using the name. Two successful comment-feed requests added five directly matched comments to Broadcom's workspace. One post asks about brokerage fees, illustrating that ticker mentions alone do not establish useful sentiment. No new AI analysis was run for this acquisition check.

With the added communities, the next live Broadcom search retained 26 company-matched posts, including 17 from BroadcomStock, six from ValueInvesting and one from StockMarket. The first new comment request hit 429; five earlier comments remain saved. See [the broader coverage review](../reviews/2026-10-08/reddit-coverage-and-pacing.md). The unchanged analysis selection remains bounded; company-focused communities can be concentrated or promotional and are not a representative investor survey.

One explicit paid sentiment reading used eight Reddit texts, including two comments. Both comments matched the predeclared developer expectations of relevant, positive, attributed opinion. The other six texts were not an independently labeled accuracy benchmark. Existing sarcasm/attribution gaps, missing reply trees, incomplete deletion reconciliation, provider volatility and participant validation remain open.
