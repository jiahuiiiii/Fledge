# Public annual financial forecasts

Stock Analysis publishes limited annual revenue and adjusted earnings-per-share forecasts attributed to S&P Global Market Intelligence. This separate connection supplements the FMP dataset whose actual estimates endpoint denied the configured key. It does not clear that denial or obtain restricted table cells.

## Meaning and evidence

`stockanalysis-visible-financial-forecasts-1` reads ordinary visible HTML tables, checking the registered ticker, exchange, provider attribution, fiscal columns, dates, ordered ranges and agreement between annual and range-table averages. Different displayed precision is retained; a rounded range-table average is not silently substituted for the more precise annual value. Script/template content and explicitly hidden elements are ignored. Missing/changed/ambiguous tables fail visibly. Pro/Upgrade years are omitted, including when a separate summary shows a later-year figure.

Revenue and EPS remain forecasts, never reported results or management guidance. EPS is explicitly non-GAAP adjusted. The public table's forecast currency is not established by the stock quote's USD label, so currency stays unknown. The table's overall analyst count is kept separately; per-metric contributors remain unknown. Page-update dates, collection observations and the unknown underlying forecast vintage stay distinct. These observations cannot establish a comparable pre-release consensus-versus-actual result.

Migration 046 adds a separate source permission and immutable `public_financial_forecasts` observations containing the original page, hash, parsed data or parser failure, and actual observation time. Full HTML is source-role-only; the application receives normalized evidence and history. Older observations are never rewritten or assigned a new vintage. A failed later read retains earlier successful forecasts with a visible error/age. Withdrawal hides current values and history.

## Shared acquisition

There is no new fetcher. Price targets and financial forecasts use the same `analyst_targets.refresh` page request, per-company 24-hour interval, two-second global clock and two-minute lease. Either allowed explicit refresh can populate both permitted datasets from one response; the existing coordinated first-open target step can do the same. A new financial scope cannot reset the existing page's clock. Existing target snapshots/method identities remain unchanged.

Access and lease ownership are checked before dispatch (including after pacing) and at commit. One scope's parser failure does not prevent the other scope's valid result being retained. Redirects, automatic retries, hidden APIs, membership access and provider substitutions are absent. No AI call, private research change, watch enrollment or notification is part of this connection. The existing local-pitch supplier limitations remain; public HTML is not a stable licensed production API.

The Business view shows separate public revenue/EPS range cards, average markers, explicit low/high endpoints and expandable exact values/definitions. Each metric uses its own range scale. Negative and zero EPS remain valid. Source units, unknown currency, observations, restrictions and saved history remain visible. Checking this source preserves unsaved peer-selection drafts.

Sources: [public forecast example](https://stockanalysis.com/stocks/avgo/forecast/), [publisher data attribution](https://stockanalysis.com/data-sources/). See the [implementation review](../reviews/2026-10-09/public-financial-forecasts.md) for actual checks and remaining limits.
