# Reddit RSS integration — 8 October 2026

The owner requested first integrating the working Deus route into Thesis and then fetching comments. Both are now verified with actual Reddit content and a saved Thesis sentiment reading. [Feature contract](../../features/reddit-rss-collection.md).

## Actual requests and failures

Evidence: `.local/live-tests/reddit-rss-integration-20261008/`. All times below are UTC. The earlier exact-Deus adapter experiment remains separately recorded in [its review](deus-reddit-live-probe.md).

| Check | Result |
| --- | --- |
| 07:24:15, stocks hot RSS with Thesis's honest identifying header | 200; 25 entries, 24 within seven days. Original body/hash retained. |
| 07:24:19, NVIDIA buyback comment RSS | 429. The initial probe did not retain Retry-After; a conservative local 15-minute pause was recorded rather than guessing a provider reset time. |
| 07:39:45, same comment feed after the pause, through the Thesis reader | 200; 64,080 bytes, 77 entries including the root post. Original body SHA-256 `31fda1167e8902c2452b35c5b1c007e4881384bc05f327e87af739b2b179dd2c`. |
| 07:48, first company integration run | Stocks 200, investing 429 with no Retry-After; seven NVIDIA posts stored. No further network request in the run. Initial recovery did not use already saved comments. |
| 07:51, corrected cached recovery | Zero HTTP requests; seven posts and 12 genuine comments retained, 19 sources total. Two comments selected within the eight-social-source analysis limit. No live cooldown cleared or extended. |
| 08:04–08:05, actual app first-open coordinated research | Thirty-second RSS pacing reached stocks and investing; wallstreetbets returned 429. Nine matching posts and 12 comments remain available. Other standard NVIDIA source steps also ran; existing Broadcom research was not reset. |

The 07:24, 07:39, 07:48 and 07:51 payloads, headers where captured, clocks and packets remain separate. Do not erase the first failures or describe all Reddit communities as working. At this checkpoint the RSS global clock recorded eight requests, including the two initial probes. No account, cookie, alternate host, proxy or challenge-solving was used.

## Interpretation and spending

`analysis-20261008T080107Z/` freezes the packet and two-comment criteria before the paid call. Analysis `5c171586-4c22-44de-a6f9-3ad6f1516378` is saved in NVIDIA's workspace. Both comments match relevance, positive tone and opinion type (six selected decisions); exact passage validation passed. This is a developer spot check of two comments, not measured general accuracy or validation of the other six social texts. No reply parent was invented, and feed-update date metadata is included in the request.

The single new request cost **US$0.0777175**. Original cumulative ledger: US$17.5683695 confirmed, US$0.60249 historical maximum holds, US$11.8291405 available of US$30, 323 calls and no new ambiguous charge. No watch, private research revision, alert publication or Telegram recipient was created by this test.

## Verification and preservation

- Broad backend run: **1,297 passed, 59 optional-corpus skips**. Final focused source/conversation/export follow-up: **75 passed**, overlapping the broad run and including the two later cache-recovery cases.
- Earlier focused controls: 88 passed for post/loading integration; 84 passed for comment/source/answer/export integration; 80 passed for Reddit collector regressions. These overlap and are not additive totals.
- Preserve `focused-initial.log`: one authored test attempted a settings write with the source role, which correctly lacks permission; the fixture now uses its administrative test role. Preserve `comments-focused.log`: the first invocation named a nonexistent test file and ran no tests. Neither is a live source success.
- All 27 frontend checks and production build pass. Actual desktop and 390/320px source-modal checks have no horizontal overflow and cover feed-update labeling and the saved comment result. The UI follow-up replaces a misleading “collected” parent-context message with the actual RSS limitation.
- Private backup: `.local/backups/phase83-reddit-rss/before.dump`. Schema remains 40. All 100 preexisting table fingerprints were recorded; 56 whole tables stay exact, including private research/watch/notification configuration, original budget configuration and old Reddit denial. Changed tables are recorded in `changed-tables.json`: new NVIDIA source/analysis records and expected shared acquisition clocks/caches. The browser's first-open workflow also acquired NVIDIA filings, quotes, prices, analyst references, news and HN comments.

## Five implementation perspectives

This is one implementation review from five perspectives, not five independent consultant opinions.

- **Product:** The app now presents original Reddit comments and a real saved interpretation. Hot-feed matching is still sparse for some companies; absent Broadcom matches cannot be described as absent discussion.
- **Architecture:** Reuse the working Deus RSS mechanism, existing restricted roles, immutable source versions, loading queue and spending ledger. Keep legacy denials and RSS capability clocks separate. No new service or dependency is required.
- **Evidence quality:** Do not invent publication dates or immediate parents from flat RSS. Only direct company mentions enter the comment sample; two-per-thread selection limits amplification. Source acquisition success is not model accuracy.
- **Operations:** Rate limits occurred even during bounded live tests. Cache-only recovery retains useful work, and provider gaps remain visible. Thirty-second pacing reduced burst pressure but did not eliminate 429 responses.
- **UX/business:** No extra data subscription is needed for this MVP route. The existing announced RSS retirement and unstable coverage make it unsuitable to promise a permanent free production feed. Further user testing and durable supplier decisions remain open.

Final preservation audit confirms all original 322 model-call and dispatch rows remain exact after excluding the single appended paid check. `final-audit.json` retains source counts, cache timestamps and the budget; its first read-only invocation used a nonexistent column name and made no changes before correction. `browser-check.json` records the actual desktop/phone checks; native screenshots remain in the conversation.

## AVGO search follow-up

The owner suggested searching `AVGO` instead of only Broadcom. Inspection found two distinct gaps: live discovery scanned generic hot feeds, and the fallback issuer matcher required `$AVGO`, an exchange prefix or a financial noun when the company name was absent. Bare `AVGO`/`avgo` is now an explicit Broadcom alias. Other issuers' common-word ticker controls remain unchanged.

One combined `"AVGO" OR "Broadcom"` RSS search across the enabled stocks/investing/wallstreetbets communities at **08:26:47 UTC** returned HTTP 200. Three candidates had verifiable original identities/dates; two matched, one using each term. Original body SHA-256: `f3eec54b5bf88a44c68de60baf5e452ec97f3714b26cece4315fc414b27a6a23`. Evidence: `avgo-search-20261008T082647Z/`. This is not a controlled AVGO-only versus Broadcom-only search comparison; it demonstrates that combining both terms recovered discussions outside the earlier sample.

The production collector now uses that single combined search, up to 50 candidates, followed by up to three matching comment feeds. Saved hot feeds can supplement it without additional network calls. Search/hot post denials share the same capability; cooldowns, honest identification and no redirects remain. Cache keys include the query, enabled communities and window. Candidates from disabled communities, missing original publication dates, mismatched IDs or wrong hosts are excluded. Search/hot duplicates are removed before comment selection. New search discovery metadata does not overwrite an earlier source's method.

The actual integration at **08:30:39 UTC** reused the search response and requested two comment feeds, both HTTP 200, at 08:30:40 and 08:31:10. It retained **two posts and five directly matched comments** for Broadcom. Evidence: `avgo-integrated-20261008T083039Z/`, including response metadata, original bodies, source records, an undispatched analysis packet and table fingerprints. Two Reddit sources fit the current combined sample, with existing per-thread/channel limits still enforced. One post asks which broker to use: a ticker mention is only a candidate for relevance analysis, not proof of company sentiment. No new semantic-accuracy result is claimed.

Three additional actual RSS requests bring the recorded count to 11. Of 100 table fingerprints, only `provider_checks`, `provider_clocks`, `public_feed_cache`, `reddit_company_checks`, `social_discovery` and `social_posts` changed. The remaining 94 tables, including private research, model calls/budget, watch and notification settings and the original Reddit denial, remain exact. No AI request, watch enrollment or Telegram message was made; spending remains US$17.5683695 plus US$0.60249 historical holds.

Verification: **89 passed, 3 optional skips** in the RSS/catalogue/directory checks; **113 passed, 2 optional skips** in disjoint Deus/HTML/loading/sentiment/selection regression files, using disposable databases and the external-network guard. Logs are `search-focused.log` and `search-regression.log`. Checks cover combined queries, common-word safeguards, scoped caches, shared denials, direct company mentions, permission changes, original date/identity requirements, bounds, deduplication and cache-only recovery. The actual search body also has an optional replay check. No layout or frontend component changed in this follow-up; earlier browser verification is not represented as a new run.
