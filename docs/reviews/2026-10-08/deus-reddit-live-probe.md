# Exact Deus Reddit adapter — live check

8 October 2026, 15:09 SGT. This follow-up corrects the inference from the earlier [Thesis HTML preflight](reddit-html-collector.md): that different request did not test Deus's actual adapter.

## Result

**Deus's subreddit RSS collection succeeded on this Mac. Its first comment-page request reached a login page and returned no comments.** This is a bounded result for one feed and one thread, not proof that all comment collection fails or that the builder's deployment is broken.

| Stage | Actual response | Adapter output |
| --- | --- | --- |
| `https://www.reddit.com/r/stocks/hot/.rss` | HTTP 200, Atom XML, 68,641 bytes | 25 distinct posts, all with original publication dates and nonempty summaries |
| First eligible thread on `old.reddit.com` | HTTP 302 to `/login/?reason=lor2&dest=…` | Followed by Deus's existing client |
| Redirected login page | HTTP 200, title “Welcome to Reddit”, no `div.comment` elements | Empty comment list |

The selected thread was [Rate My Portfolio — r/Stocks Quarterly Thread September 2026](https://www.reddit.com/r/stocks/comments/1w46d05/rate_my_portfolio_rstocks_quarterly_thread/), the first item supplied by the feed and accepted by Deus's existing financial pre-filter. It was older than seven days. Of the 25 feed items, 24 were within seven days. Deus's `hot` feed reader does not itself impose Thesis's seven-day window or exact-company matching, so these are retrieved subreddit posts, not 25 eligible Broadcom sentiment sources.

The probe stopped after the login/challenge response; no second thread, credential entry or challenge submission was attempted. There were three HTTP GETs including the automatic redirect, no retries. The fallback independent thread check was not used because RSS discovery succeeded.

## What was executed

The actual `RedditSource.fetch()` and `RedditSource.enrich()` methods were imported from the existing complete source snapshot at upstream revision `74d5aea8b0acf72e1851dfc841f9f1408e9e6609`. That snapshot was verified against current GitHub before this test. The adapter file was unmodified before and after execution (SHA-256 `fee91707e9c73c38f0d38f3ec9a4d453e837bf2e422f22ef3a99760d139de195`). This was execution of the original adapter, not a launch of the complete Deus application or a new Git clone.

The test selected `stocks`, one of Deus's default communities, and retained its default maximum of 25 posts. It used Deus's original user agent, original RSS and old-Reddit URLs, original pre-filter, parsing code, client redirect setting and comment limit. A surrounding harness recorded real responses, limited the experiment to three candidate threads/five network requests, added a 20-second default socket timeout and 90-second overall deadline, and constrained destinations to the two original Reddit hosts. It did not replace returned bodies or rewrite source URLs/headers. The request bound was not reached.

The owner explicitly requested this exact-adapter test after being told it uses RSS and `old.reddit.com`. That authorization covered this isolated reproduction despite Thesis's recorded denial; it did not enable a production fallback or clear the denial.

## Isolation and reproducibility

Only the adapter's dependencies were installed in `.local/experiments/deus-reddit-venv/`: feedparser 6.0.14, httpx 0.28.1, beautifulsoup4 4.15.0, pydantic 2.13.5, pydantic-settings 2.15.0 and structlog 26.1.0. These satisfy the upstream requirements; the builder's actual dependency versions and network environment are unknown.

The process ran from an empty working directory with credentials and proxy environment variables excluded. No Thesis modules, databases, `.env`, application worker or model pipeline were loaded. Original adapter logging was retained. Response bodies, hashes, parsed posts, the enriched article, metadata and a separate offline assessment are under:

`.local/live-tests/deus-exact-adapter-20261008/live-20261008T070938Z/`

The harness and console log are in its parent directory. Captured bodies are private local evidence, not new production research records. No OpenAI, Apify or Telegram request or charge occurred. The existing app configuration, Reddit denial, watches, source records and budget ledger remain unchanged. No production code changed, so no new backend/frontend regression run is claimed.

## Implication

There is now direct evidence for a usable RSS post-acquisition route in this environment. Comment acquisition remains unresolved for the tested thread. Deus's comment helper checks final HTTP status but does not distinguish a successful login-page response from an empty discussion; its returned zero count here must not be interpreted as “no comments exist.”

A future Thesis integration should report posts and comment coverage separately, retain original dates and company relevance checks, and preserve the old denied-request evidence. The result does not identify which request or environment difference made RSS succeed, establish continuous reliability, or validate sentiment interpretation. The useful builder follow-up is whether their recent runs contain actual comment bodies and what environment/version they use when that stage succeeds.
