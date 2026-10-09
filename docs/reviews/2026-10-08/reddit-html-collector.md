# Own Reddit HTML collector — phase 82

8 October 2026. [Feature contract](../../features/reddit-html-collector.md).

## Request and resulting implementation

The owner requested an unofficial Reddit scraper for the MVP, then asked whether Thesis could build its own rather than require Apify. The implementation adds `thesis/research/reddit_html.py`, selected through the existing Reddit collector with an optional off-by-default setting. No third-party scraper package or fee is introduced.

The parser reads rendered `shreddit-post` and `shreddit-comment` elements. It validates IDs, dates, links, enabled communities, reply chains and discovered source versions. Own author text is separated from nested bodies and saved immediate-parent context; root thread grouping preserves selection diversity. It accepts at most 20 posts, three threads and 12 comment elements per thread, within the existing discussion windows. Missing markup and unverified commentless pages do not become successful empty coverage.

Transport retains the original identifying user agent, persistent Reddit denial, pacing, company leases, source permissions and bounded responses. No alternate host, proxy, cookie session, redirect, hidden API or disguised request was added. The source storage and sentiment pipeline use existing schema 040. No prompt, model, paid profile, alert threshold or approval semantics changed.

Deus was inspected at the existing pinned local source revision `74d5aea`. Its RSS post collector and HTML comment helper establish the architectural reference; its author/body output does not supply Thesis's required item/date/parent evidence. Its alternate-host substitution was not adopted. Apify was researched and discussed but no Apify connector was implemented.

## Verification

New tests use **authored HTML and mocked transports**, not actual Reddit examples. They cover original text boundaries, nested immediate parents, dates/windows, removals, duplicate limits, invalid chains, mismatched source versions, missing markup, response limits, redirects, denied access, default-off configuration, and collection through source storage into sentiment selection. A mock analysis checks integration only; it does not establish semantic accuracy.

- Initial restricted test execution failed during PostgreSQL setup because the sandbox disallowed the disposable server. Those setup errors do not establish a code failure.
- The first network-guarded focused run passed 42 cases and failed one fixture assertion: it counted the unrelated seeded news item alongside two social items. The corrected assertion counts social items. The initial output is retained as `focused-first.txt`.
- The focused rerun passed 43 cases, retained as `focused-final.txt`.
- Seven additional boundary cases and parser refinements were included in the final full run: **1,267 passed, 59 optional corpus skips**, one existing Starlette/httpx deprecation warning, in 153.66 seconds. Output is retained as `backend-full.txt`.

Evidence files live under `.local/live-tests/reddit-html-phase82/`. All database verification used disposable databases with `tests/offline_runtime/sitecustomize.py` blocking external network. This guard was not loaded into the owner's app. No frontend code changed, so no new browser or frontend-suite result is claimed.

## Live access is blocked and unverified

A restricted, ordinary public HTML preflight to the `r/stocks` Broadcom search failed with `ConnectError`; it acquired no source content. Automatic approval review rejected the network-enabled preflight because the existing AGENTS.md instruction preserves Reddit's earlier 403 denial and prohibits retrying or bypassing it. No alternate acquisition method was attempted after rejection.

There is therefore no current real-page fixture, proven live access or validated current markup. The reader remains off. The permanent denial remains unchanged; toggling the new setting does not override it. A specific owner decision on the rejected preflight is needed before another live request. A future successful page request would still require real-source parsing evaluation and would not establish durable coverage or accurate sentiment.

## Preserved state and remaining work

This phase made no changes to the owner's database, private `.env`, source clocks, research, existing watches or Telegram recipients. It did not restart the local app or enable collection. No OpenAI, Apify or Telegram request was made. The original cumulative US$30 ledger remains unchanged: US$17.490652 confirmed plus US$0.602490 historical maximum holds, US$11.906858 available, 322 calls.

Remaining work is permitted live access testing, real markup/source evaluation, installation activation only if viable, and broader sentiment/alert interpretation testing. This is an implemented but unverified live connector, not a claim that Reddit collection is now working or that sentiment/alerts are validated.

## Follow-up: owner-approved single access check

After the initial report, the owner explicitly said, “yes, run the access checking,” in response to the request for one ordinary public-page request despite the recorded denial. That specific request was approved and sent at **06:49:36 UTC / 14:49:36 SGT on 8 October 2026** to the `www.reddit.com/r/stocks/search/` Broadcom search. It used the same identifying app user agent, no credentials or proxy, no redirects, a 20-second timeout and a 2 MB response limit. It did not invoke the app collector or change the existing denial record.

The response was **HTTP 200, text/html, 8,413 bytes**, but it was a JavaScript verification page rather than discussion content. It contained zero `shreddit-post` or `shreddit-comment` elements. Its form and inline script request a challenge submission; that script was inspected as text only, never executed or submitted. The actual parser rejected the captured page with its existing missing-elements coverage error. There were **no additional network requests**, database writes, configuration changes, paid calls or app activation.

Original response metadata, response bytes and the separate offline assessment are retained in `.local/live-tests/reddit-html-phase82/approved-access-20261008T064936Z/`. The original response SHA-256 is `97011dc85b28351e05ee62b1478a1caebbcce58f494dd9348748b1a46dd3a53f`. The earlier approval rejection remains preserved above; it was followed by explicit owner approval, not bypassed.

This result establishes that simple direct HTML access receives a verification challenge here. It does not prove current discussion markup compatibility, reliable collection, or that another provider will succeed. The reader remains off and the original denial remains intact. The one-request approval is consumed. No code changed, so the prior software test results remain historical; the new verification consists of the single live response and an offline parser check against it.
