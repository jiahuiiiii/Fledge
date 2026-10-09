# Phase 81 — publisher feeds and optional social connections

8 October 2026. The owner requested Devvit if suitable and Deus's broader source coverage. [Feature contract and current source matrix](../../features/multi-source-research.md).

Implemented migration 040, public-news source access, eleven publisher RSS adapters, Alpha Vantage news and official X recent search, per-provider pacing/cache/leases, queue integration, source coverage UI, X-specific selection/theme/alert scope and watch coverage. Existing source records, model allowance, private research and monitoring settings are preserved. Devvit remains an assessed dependency requiring an approved external-use route; no working Devvit app is claimed. Nitter is not activated.

## Actual-source evidence

One bounded Broadcom run checked eleven feeds. Nine responded: CNBC, three WSJ feeds, MarketWatch, NYT Business, Federal Reserve and two Korea Times feeds. WSJ Business and Technology each returned the same matching report; both original records are saved, with one selected news candidate after tracking-URL deduplication. Other successful feeds had no match within the examined items. Yahoo returned 404; Google returned 302. A follow-up after the normal 15-minute cooldown successfully followed Google’s same-host redirect and retrieved 70 feed entries, examining 30 with no Broadcom match. Final access is therefore 10 of 11 publisher feeds; the initial failure and follow-up are both retained. Alpha Vantage and X are unconfigured and were not called. The earlier Reddit 403 remains intact.

Raw successful RSS bodies, results, selected-source audit and failures are retained in `.local/live-tests/phase81-sources/`. No full article was acquired. The latest saved Broadcom sentiment stays unchanged; this run collected new news without another paid interpretation or alert publication. No semantic-quality claim follows from feed access or parsing.

## Verification

Verification is recorded in the phase evidence directory. Initial broad failures were expectations for the former three source scopes/two social platforms; the tests were updated to preserve existing fixture counts and explicitly allow an empty X scope. A follow-up still expected the old author-count dictionary; that failure is retained too. A first browser navigation used an outdated company identifier and timed out; the corrected run reads the actual Broadcom workspace.

Final verification: **1,216 backend tests passed, 59 optional corpus checks skipped; 27 frontend tests and production build passed**. The final focused source/watch/export sequence passed 74 overlapping checks. Isolated social-source inspection and actual Broadcom source status/X setup views passed at 320/390/1440px, with screenshots inspected and no horizontal overflow or page errors. Mocked tests cover RSS/Atom, missing/future dates, company matching, unsafe links, bounded XML, exact access permissions, shared caching, denied-request suppression, daily limits, secret-safe error messages, stale attempt fencing, duplicates, platform separation, disabled connections, X context exclusions and source withdrawal. No mocked test establishes actual X/Alpha Vantage access or model interpretation quality.

The source/database backup is `.local/backups/phase81-sources/`. Across migration, all 95 pre-existing tables other than `schema_migrations` and `social_feeds` remained exact; the latter received only the new X feed. No existing research was deleted or rewritten. Additional source acquisition subsequently appends the two WSJ versions and their normal source/snapshot records.

## Review perspectives

- Product: multi-source coverage serves the existing research/monitoring workflow. It does not promise trading signals, representative market sentiment or access to every named platform.
- Experience: one coordinated refresh and visible per-source outcomes; missing credentials and unsuccessful retrieval differ from a successfully checked empty feed. Desktop and phone views retain the same source distinctions.
- Architecture: independent acquisition, shared cache, source-specific history and current permissions; existing numerical filings and prices remain separate. No full upstream application or extra model stage is imported.
- Evidence: actual WSJ overlap exposed a tracking-URL duplicate, now covered by a regression case. Previously saved interpretations and known sarcasm/attribution errors remain unchanged. Sparse HN coverage and unconfigured X still limit social evidence.
- Operations/cost: original US$30 ledger, no paid requests, no activated watches and no Telegram delivery. External API credentials, Google/Yahoo live recovery and Reddit approval remain real dependencies. This is a local pitch MVP, not 24/7 or production-complete coverage.


The final broad run is `backend-verified.txt`. Earlier broad/focused failures remain saved. A watch continuity case originally expected one provider failure to stop all analysis; it now checks completed available-source analysis with explicit partial coverage. A later ordered focused run exposed old tests restoring a three-entitlement constraint after withdrawal simulation; these tests now restore the exact original schema and source access. These were isolated test fixtures, not changes to production access controls.

The final read-only preservation audit (`preservation-and-selection.json`) finds only eleven expected pre-existing tables changed by migration/acquisition, with 86 other tables exact. Private research, previous interpretations and the model ledger are unchanged. Active news watches: 0; Telegram delivery rows: 0. Confirmed spending remains US$17.490652 plus US$0.602490 historical maximum holds, leaving US$11.906858 of US$30 over 322 calls, no running/unresolved request. This phase used no model credits.


The optional watch-history browser fixture initially failed because its former “fail Finnhub and stop” shortcut now continued into default social collection. It was corrected to mock both collectors and fail the analysis stage explicitly, preserving the intended failed-check case without live collection. The failed run is retained in `browser-watch-history.txt`; its retry is recorded separately. This fixture correction does not change app behaviour or the backend test count.

A second watch browser attempt asserted immediately after an asynchronous watch-setting write, before the controls had updated. The browser check now waits for their actual detached state before asserting. This changes test synchronization, not the application or source/watch contract. Both failures remain retained.

The watch browser’s final request audit identified three existing first-open `/loading` requests in addition to seven intended watch-setting writes. Assertions now distinguish these routes. Older browser fixtures could therefore reach source collectors despite running a disposable database. `tests/run_browser.py` now loads a test-only `sitecustomize` guard for its Python server/seed processes: external DNS, direct-IP socket connections and `connect_ex` are rejected; localhost and PostgreSQL Unix sockets remain available. A direct guard check passes. The normal app and actual-source evaluation do not load it. Earlier browser runs must not be interpreted as proof of zero server-side source traffic. They made no paid OpenAI calls against the original ledger.

Final guarded watch-history journey passed at 320/390/1440px (`browser-watch-history-offline.txt`), including six recorded outcomes, context inspection, saved watch frequency, opt-in/stop behaviour and the Updates link. Actual source-status browser verification also passed after Google recovery (`browser-actual-final.txt`).

## Alpha Vantage setup follow-up — 8 October, 05:00 UTC

The owner added an Alpha Vantage key and deferred X while pursuing approved Reddit access. A single Broadcom `NEWS_SENTIMENT` request through the existing adapter returned an access/usage-limit message rather than news. The app recorded the failed check and its existing one-day provider cooldown. No key was printed, no source content replaced, no retry attempted and no OpenAI call or Telegram message made. The diagnostic groups provider access and quota failures; the precise restriction is not established. Outcome: `.local/live-tests/alpha-vantage-20261008/verification.json`. X remains disabled. This is an actual connection check, not an additional software-test run or evidence of successful Alpha Vantage access.

## Alpha Vantage diagnosis follow-up

The owner asked what the ambiguous failure meant and how to fix it. The [official endpoint documentation](https://www.alphavantage.co/documentation/#news-sentiment), checked 8 October 2026, explicitly labels `NEWS_SENTIMENT` Premium. A free key alone does not provide that endpoint; a plan restriction is therefore a plausible explanation, not a recovered diagnosis of the discarded original message. No purchase, retry or change to the provider cooldown was made.

The adapter now renders separate credential-safe messages for recognised invalid-key, request-limit, Premium-access and invalid-request responses. Unknown messages stay unclassified. Rate-limit notices that advertise premium plans are not mislabelled as plan rejections. Existing generic errors retain their stored text; the read view explains their uncertainty and shows the local cooldown expiry separately from any provider reset. Paused refreshes preserve the original provider check and clock without sending a request.

Focused verification: **44 tests passed** in `tests/test_multi_sources.py` using a disposable database and mocked transports, including 14 new diagnostic/preservation cases. No actual Alpha Vantage, OpenAI or Telegram request was made by these tests. Existing successful feed parsing, source scope, deduplication and denial/cooldown tests pass. Frontend markup and schema are unchanged; the full suite was not repeated. README, setup guidance and `.env.example` now state the Premium requirement without suggesting the MVP needs a subscription.

The local server was gracefully restarted. A read-only workspace API check confirms the revised historical-error explanation and pause expiry are served. Alpha Vantage's original check text/time remain exact; the provider clock still records one request and the same 9 October, 13:00 SGT pause expiry. No new provider request was used to verify the change.
