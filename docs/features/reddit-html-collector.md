# Own Reddit public-page collector

Updated 8 October 2026. [Implementation review](../reviews/2026-10-08/reddit-html-collector.md).

Thesis has an experimental collector for rendered Reddit post and comment HTML. It uses Python's standard HTML parser, normal HTTPS requests and the existing source pipeline. It needs no Reddit key or Apify account, and introduces no scraper fee. This does **not** establish that Reddit will accept requests from the installation.

## What it reads

The reader searches enabled communities for the registered company, accepts at most 20 posts, and visits at most three matching threads. Each thread supplies at most 12 rendered comment elements. It does not paginate or expand hidden replies. Manual discussion windows remain 1, 7 or 30 days; automatic watches remain seven days.

Records require original item IDs, matching source links and publication dates. Each author's body stays separate from nested replies and interface text. Immediate reply context is retained separately, while the root thread identity keeps existing selection diversity limits effective. Changed thread versions are rejected for context attachment. Recognised removal markers can withdraw previously collected sources; this is not complete deletion reconciliation.

Missing markup, login/challenge pages, missing dates and unresolved reply chains are coverage failures or exclusions, not evidence of neutral sentiment. A commentless page without an explicit zero count is unverified. Stored source versions and existing analyses remain immutable.

## Access and configuration

The reader uses the same persistent Reddit clock, denial and company leases as the existing collector. It identifies the app, accepts no redirects and has bounded response size. It does not use another Reddit host, proxies, cookies, disguised requests or hidden APIs. A recorded 401/403 remains blocked; selecting this reader does not clear it.

The optional setting is off by default:

```dotenv
THESIS_REDDIT_HTML_ENABLED=false
```

With permitted and verified access, enabling it selects HTML collection during the existing first-open and refresh workflow. `THESIS_LIVE_DATA_ENABLED` must also be enabled. Live HTML requests are prohibited in disposable or relocated data directories. An injected test transport can exercise the integration without live access.

The default RSS/JSON collector remains available when the setting is off. There is no automatic fallback between methods. Collection itself makes no AI request; explicit analysis and existing opted-in watches retain their original budget and publication rules. This feature enables no watch or Telegram recipient.

## Verification and current limitation

**Separate exact-Deus test, 8 October 15:09 SGT:** its original RSS adapter returned 25 posts from `r/stocks`; its first old-Reddit comment request redirected to a login page and returned zero comments. This establishes RSS post access for that test. It does not verify this experimental search-HTML reader, other threads, or automatic collection. [Exact adapter execution and evidence](../reviews/2026-10-08/deus-reddit-live-probe.md).

Authored HTML fixtures and mocked responses test parsing, nested context, source storage, sentiment selection and rejection handling. The initial restricted preflight failed to connect; automatic approval review rejected the subsequent network-enabled preflight because the project's existing instruction preserves Reddit's earlier 403 denial.

The owner subsequently approved one ordinary public-page access check. On 8 October at 14:49 SGT, the Broadcom search returned HTTP 200 but contained only a JavaScript verification page: zero rendered posts or comments. The parser rejected it as unverified coverage. The challenge was not executed or submitted and no further request was made. **No current live post/comment markup or usable source content has been verified.** The collector remains off and the original denial remains unchanged.

Real post/comment markup may differ from the fixtures. Usable live access and real-page evaluation are still required before claiming this provides working Reddit coverage. It also cannot promise complete discussions, uninterrupted access or sentiment accuracy.

Deus's pinned implementation reads posts via RSS and comments via HTML. Its HTML helper returns author/body pairs without the IDs, dates and immediate-parent relationships required here. Thesis implements those evidence boundaries itself and does not adopt Deus's alternate-host request. Apify was discussed as another option; no Apify connector or paid scraper request was implemented in this phase.
