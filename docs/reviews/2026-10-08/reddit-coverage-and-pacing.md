# Broader Reddit coverage and response-aware pacing — 8 October 2026

The owner asked where rate limits occur, whether collection can improve and whether more subreddits can be checked. [Current feature contract](../../features/reddit-rss-collection.md).

## Implemented

Migration 041 adds StockMarket, ValueInvesting, SecurityAnalysis, BroadcomStock and NVDA_Stock. All registered companies search the first three alongside stocks, investing and wallstreetbets; AVGO additionally searches BroadcomStock and NVDA additionally searches NVDA_Stock. These are intersected with enabled source permissions. One combined company/ticker search covers the relevant communities, still capped at 50 candidates, then up to three comment feeds. No new watch, model stage, paid source or API credential is introduced. Source coverage now names the configured communities; configuration is not proof of returned results from every community.

The original JSON/HTML denial, 30-second local minimum, 240-request daily cap, 15-minute company interval and conservative 429 pause remain. The live test below exposed reset headers that the reader previously ignored. It now stores exhausted `X-Ratelimit-Remaining`/`X-Ratelimit-Reset` windows in the persistent `reddit-rss:quota` clock, waits until reset plus one second and rechecks before dispatch. Shorter headers cannot shorten a prior window or release a denial/429 pause. Missing/malformed headers leave the existing safeguards in place. A queue wait over 60 seconds is deferred visibly, rather than holding a worker indefinitely. The RSS company lease is six minutes to cover up to four bounded requests and their waits; expiry/token fencing remains. Initial 429 messages show the next check time.

No invented reply relationships were added. An audit of three retained actual comment feeds found 5, 76 and 59 comment entries, all without parent fields or parent link relations. Their fields were author, category, content, ID, link, title and updated. This confirms the limitation in these responses; it is not proof that every possible Reddit endpoint lacks hierarchy. Exact thread links remain available, and contextless replies remain excluded.

## Actual source check

Evidence: `.local/live-tests/reddit-coverage-20261008/live-20261008T084606Z/`. The existing company cooldown expired naturally before the run. No clock was reset.

| UTC | Request | Outcome |
| --- | --- | --- |
| 08:46:06 | AVGO/Broadcom search across seven enabled communities | HTTP 200; remaining `0.0`, reset `53` seconds. |
| 08:46:36 | First new BroadcomStock comment feed | HTTP 429; remaining `0.0`, reset `23` seconds; no Retry-After. Collection stopped, with the existing pause preserved until 09:01:36 UTC. |

The run retained **26 company-matched posts**, compared with two in the earlier three-community search. Seventeen are from BroadcomStock, six from ValueInvesting, and one each from StockMarket, wallstreetbets and investing. This is an observed retrieval increase, not an exhaustive result or a controlled causal comparison of identical-time samples. No new comments were acquired in this run; **five earlier Broadcom comments remain saved**, for 31 saved Reddit sources in the current discussion window. Four Reddit sources fit the current combined analysis selection. No new AI interpretation was requested.

The successful search and subsequent rejection show that 30 seconds was too short for this observed server window. They do not establish a universal RSS request allowance, an IP/account enforcement key, or unlimited access after the fix. The reset-header implementation was added after that failure and verified with controlled responses. No further live request was made during the preserved cooldown, so live acceptance under the new pacing is not yet verified.

## Verification and preservation

- Full guarded isolated backend suite: **1,324 passed, 59 optional-corpus skips**, before the later reset-header refinement. Final overlapping RSS/loading/Deus checks: **91 passed**, including the new pacing and expired-lease cases. Do not add these counts together.
- Preserve `focused.log`: an old generic-feed test assumed all configured communities had been attempted by the legacy three-feed route. It now checks the three actual failures and separately verifies the new unattempted communities have no fabricated failure. The first focused run was 153 passed, one failed. `reset-header-followup.log` and `reset-header-final.log` preserve the subsequent checks.
- Additive migration backup: `.local/backups/phase84-reddit-coverage/before.dump`. Of 100 table fingerprints, only schema metadata and `social_feeds` changed during migration; **98 tables stayed exact**.
- The live source check changed only `provider_checks`, `provider_clocks`, `public_feed_cache`, `reddit_company_checks`, `social_discovery` and `social_posts`; **94 tables stayed exact**, including all private research, model/budget, watch and notification records and the original denied Reddit clock.
- The running local app's read-only workspace endpoint returned Broadcom's seven configured communities. No frontend component/layout changed; this is not a new browser visual test.
- No OpenAI charge or Telegram message. The original US$30 ledger remains US$17.5683695 confirmed plus US$0.60249 historical holds, US$11.8291405 available, 323 calls and no unresolved blocker.

## Research and implementation review

The [Reddit Data API wiki](https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki) describes eligible authenticated-client limits; those allowances cannot be applied to this unauthenticated RSS route. Reddit's [infrastructure announcement](https://www.reddit.com/r/modnews/comments/1wubgvt/continuing_our_infrastructure_updates_whats/) confirms RSS retirement on 13 November 2026 and does not promise a replacement for outside-community RSS collection. Public pages were inspected for [BroadcomStock](https://www.reddit.com/r/BroadcomStock/), [NVDA_Stock](https://www.reddit.com/r/NVDA_Stock/), [ValueInvesting](https://www.reddit.com/r/ValueInvesting/), [SecurityAnalysis](https://www.reddit.com/r/SecurityAnalysis/) and [StockMarket](https://www.reddit.com/r/StockMarket/). Page visibility is separate from local RSS access.

One agent reviewed this change from five perspectives:

- Product: more relevant places to discover discussion, while retaining explicit sampling limits.
- Architecture: one bounded combined query, shared provider clocks, source permissions and immutable evidence; no parallel scraping pool or alternate-host fallback.
- Evidence quality: company forums can concentrate enthusiastic or promotional views. Source acquisition does not establish reliable sentiment, parent relationships or independent authors.
- Operations: honor actual exhausted-window headers and expose pause timing. Preserve the failed live response; rate-limit elimination remains unverified.
- UX/business: community coverage is visible without a new configuration burden. This is an MVP route with an announced expiry, not a permanent free data supplier.
