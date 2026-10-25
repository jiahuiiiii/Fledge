# Pro research tabs: four-tab restructure

Drafted 25 October 2026. Status: **approved, not built.** The owner approved the four destinations below, reviewed wireframes of all four tabs, and settled the price chart behaviour and the News & discussion order. No open decisions remain. This guide is the implementation contract; record dated progress and verification in `docs/reviews/YYYY-MM-DD/`, not here.

## Why

The Pro company view has six tabs: Summary, Overview, Financials, News & discussion, Outlook and Compare & value. Several of them repeat each other, so a reader opens two "start here" pages and finds the same guidance, headlines and peers in several places.

| Overlap | Where it appears today |
| --- | --- |
| Management guidance and analyst revenue forecasts | Outlook (`ManagementOutlook`, `FmpPanel mode="outlook"`), the Financials revenue chart (`RevenueHistory` already plots both), and Overview section 2 "Growth & outlook" |
| Two summary pages | Summary (`BeginnerSummary`: price, three signals, news, people, world, your view) and Overview (`CompanySnapshot` + `OverviewSections`: glance, your view, latest activity, five sections that retell every other tab) |
| Company headlines | Summary news card, Overview "Latest activity" and Overview section 4 "News & discussion" |
| Your view | Summary "Your view" card and Overview `YourView` |
| Online tone | Summary signal lights and Overview section 4 |
| News-reported expectations | Outlook only, but read from saved news stories, so it belongs beside the news |

## Scope

- **Pro only.** Beginner mode keeps exactly two tabs, Summary and News & discussion, and must look and behave the same after this change.
- **Fictional sample (recorded) companies** in Pro show Overview, News & discussion and Financials (today: Summary, Overview, Financials, News & discussion).
- Frontend restructure only. No API, schema, migration, worker, provider, Telegram or spending change. No new paid action, and no paid action may start because a block moved or opens by default.

## New structure

| Order | Tab (label) | Internal key | Replaces |
| --- | --- | --- | --- |
| 1 | Overview | `business` | Summary + Overview |
| 2 | News & discussion | `evidence` | News & discussion + Outlook's news expectations |
| 3 | Financials | `fundamentals` | Financials + Outlook's guidance and analyst forecasts |
| 4 | Compare & value | `valuation` | Unchanged |

Keep the existing internal keys to limit churn in `App.jsx`, `lib/companion.js` and `onView(...)` callers. `summary` stays a Beginner-only key; `expectations` is removed.

The order puts news second because the project prioritises alerts and sentiment ([AGENTS.md](../../AGENTS.md)).

### 1. Overview (merged)

Top to bottom:

1. **Price.** Price, today's move and the line "Prices move for many reasons", then the past-year chart (`HistoricalPrices`), open by default and showing saved prices only. See [Price chart behaviour](#price-chart-behaviour).
2. **At a glance.** The revenue-growth headline and short sentences from `CompanySnapshot`, then the three signals (News, People online, World) from `BeginnerSummary`.
3. **Your view.** One copy only.
4. **What's being said.** News and People online side by side, top three per tone group, with "All news and posts →" to News & discussion. This replaces Summary's two cards, Overview "Latest activity" and Overview section 4.
5. **The business in four reads.** Four compact cards from `OverviewSections` sections 1, 2, 3 and 5: How it makes money, Growth and outlook, Financial health, Value. Each has one or two key figures, one reading sentence, evidence, and a link to its tab (Financials, Financials, Financials, Compare & value).
6. **World news that may matter.** Compact; up to two linked events and "World news →".
7. **Understand the business.** `BusinessPanel` (brief, questions to research next, original evidence) inside a closed `Disclosure`. Creating a brief stays an explicit paid action; reading a saved brief stays free.

Removed: Overview "Latest activity", Overview section 4 "News & discussion", the second "Your view", and the Pro-only Summary tab.

Keep `Freshness`, the practice-company notice for recorded companies, financial loading/error/retry states and the "not whether to buy or sell" line.

### 2. News & discussion

Keep today's order:

1. What's developing (`MarketResearch`)
2. What's the tone? (`SentimentPanel`: window, source filters, tone per source, tone filters)
3. Discussion themes (`DiscussionThemes`)
4. Read analysed sources (closed `Disclosure`)
5. **Expectations reported in the news** (`ExpectationsPanel`) in a closed `Disclosure`, labelled as an optional AI reading. It loads only when opened, as it does today in Outlook.
6. More headlines, not analysed (`MarketResearch headlinesOnly`)
7. Watch and alerts (watch dialog, check history and tone history)

**Owner decision, 25 October 2026:** keep What's developing above the tone panel. Overview already shows the tone signals, so this tab leads with the stories.

### 3. Financials

1. Fill in missing figures with AI (`FinancialRecovery`): only when figures are missing, unchanged.
2. Key figures summary row: revenue, net profit or loss, free cash flow and period selector; every figure opens its source.
3. How sales become profit: `RevenueFlow`, then `RevenueHistory` with guidance and analyst forecasts plotted ahead.
4. **What management expects** (`ManagementOutlook`): directly under the revenue chart. It shows quoted guidance and items the chart can't plot, such as margin or earnings guidance. Keep "No saved company guidance" and withdrawn, expired or truncated states.
5. **Analyst forecasts table** (`AnalystForecasts`): in a closed `Disclosure`. It holds the numbers behind the plotted forecast points, with the existing check and public-update actions kept explicit.
6. What it owns and owes.
7. More detail (closed): segments, liquidity, borrowing over time, definitions and filings.

Replace the `PeerContext` strip with a one-line link "Compare with peers →" to Compare & value, keeping its single fiscal-year growth sentence if it is still useful. [competitor-position.md](../features/competitor-position.md) already says the full comparison lives only in Compare & value.

### 4. Compare & value

No structural change. Current order: `SectorPosition` (the only peer picker), `ValuationPanel` (analyst price targets, then Explore the assumptions), then `FmpPanel mode="ratios"` (other comparison measures, closed).

> Correction to the wireframe review: the wireframe showed a second peer picker, "Choose useful comparisons", being removed. That picker lives in `FmpPanel mode="peers"`, which no tab currently renders; Compare & value uses `mode="ratios"`, which says "Edit the group above". There is no duplicate picker on screen. After the restructure, check whether `mode="peers"` has any remaining caller and remove it only if it is unused.

## Reusable components (required)

Build the new tabs by composing existing components. Do not copy JSX between Beginner and Pro or between tabs. Where a block is needed in two places, extract it once and import it in both.

**Use the shared UI kit first.** [`frontend/src/components/ui`](../../frontend/src/components/ui/README.md): `Card`, `SectionHeader`, `Button`, `Badge`, `Disclosure`, `FilterGroup`, `MetaRow`, `StoryCard`, `EmptyState`, `Pagination`, `Tabs`. Every new heading, card, collapsed section, tone badge and empty state uses these. Replace hand-written `<details>` (for example `.outlook-news`) with `Disclosure`. Add or extend a kit component, with a `/?ui-preview` example, rather than adding page-specific styles.

**Extract from existing components:**

| New shared component | Extract from | Used by |
| --- | --- | --- |
| `SignalLights` | `BeginnerSummary` lights, key and pointer | Beginner Summary, Pro Overview block 2 |
| `ToneHeadlineGroups` | `BeginnerSummary` `group()` / `headline()` | Beginner news and people cards, Pro "What's being said" |
| `PriceMoveLine` | `BeginnerSummary` price row | Beginner Summary, Pro Overview block 1 |
| `YourViewCard` | `CompanySnapshot` `YourView` and `BeginnerSummary` "Your view" (merge into one) | Beginner Summary, Pro Overview block 3 |
| `WorldSignalCard` | `BeginnerSummary` world card | Beginner Summary, Pro Overview block 6 |
| `OverviewReadCard` | `OverviewSections` `Section`, `Reading`, `KeyInformation` | Pro Overview block 5 (four cards) |

**Reuse as-is in their new homes:** `ManagementOutlook`, `AnalystForecasts` (import directly instead of going through `FmpPanel mode="outlook"`), `ExpectationsPanel`, `HistoricalPrices`, `BusinessPanel`, `RevenueHistory`.

Rules for extraction:

- Extracted components render presentation only. Callers keep requests, permissions, selection, dates and mutations, as the UI README requires.
- Beginner output must stay identical: same text, order, tone shapes, anchors (`#bs-news`, `#bs-people`, `#bs-world`) and accessible names. Pass variant props for Pro differences (for example `limit`, `compact`, a destination link) instead of forking.
- One source of truth for derived values: tone grouping, signal moods, revenue-growth sentences and guidance readings keep using the existing helpers (`groupByTone`, `worldLight`, `snapshot`, `revenueComparisons`, `currentGuidance`). Do not recompute them in the new layout.
- After moving everything, delete `OutlookPage.jsx` and `OutlookPage.css`, and remove CSS that only served deleted blocks. Keep CSS that an extracted component still uses, moved next to that component.

## Navigation and state changes

- **`ResearchNavigation.jsx`.** Remove the `expectations` section. `researchTabs()` returns `["business", "evidence", "fundamentals", "valuation"]` for Pro, `["business", "evidence", "fundamentals"]` for recorded companies, and Beginner is unchanged. Update section descriptions (Overview now covers price and signals; Financials now covers guidance and forecasts).
- **Old keys.** Add an explicit alias before the clamp effect in `App.jsx` (around line 776), because the clamp alone sends removed keys to the first tab:
  - Pro `summary` → `business`
  - `expectations` → `fundamentals`, then scroll to and focus the "What management expects" heading
- **Links to update:**
  - `OverviewSections` "Open Outlook →" → open Financials at management expectations
  - `ExpectationsPanel` `onView` links: check they still make sense from inside News & discussion
  - `lib/companion.js` starter "What do analysts and management expect?": `section: "fundamentals"`, destination "Financials · What management expects"
  - `CompanionGuide` recorded filter for `expectations`
- **Data loading.** `needsFinancials` in `App.jsx` lists `summary`, `business`, `fundamentals`; drop Pro `summary` but keep it for Beginner. Keep `visible` gating so blocks in hidden tabs don't fetch, and `RetainedView` so tab switches keep state.
- **Default tab.** Pro already opens on `business` (Overview) and Beginner on `summary`; keep both.

## Price chart behaviour

**Owner decision, 25 October 2026:** open the price chart by default, but only read saved prices until the user chooses Refresh prices.

Today `HistoricalPrices` sits in a closed disclosure (`priceChartOpen` starts `false` in `App.jsx`). While it is open and visible, a timer calls `refreshPrices` about once a minute (`priceRefreshDelay`), which can call `api.refreshPriceHistory` to fetch new prices from the provider. Opening the chart by default without changing this would start provider checks on every company visit.

Required change:

- **Open by default.** Render the chart open in the merged Overview. Remove the `priceChartOpen` disclosure, or start it open.
- **Read saved prices only.** On load, call only `api.priceHistory` (saved data). Add a prop, for example `autoRefresh={false}`, that disables the once-a-minute timer until the user chooses Refresh prices. `HistoricalPrices` has no other caller today, so the new behaviour can be the default if that is simpler.
- **After Refresh prices.** The button runs the existing `refreshPrices` path unchanged: read saved state, check the provider only if the shared refresh delay allows it, and respect the source lease. After that choice, the existing once-a-minute updates may resume for that company while the chart stays visible. They stop when the user leaves the company or the page is hidden, and the next visit starts from saved prices again.
- **Honest status line.** Before Refresh prices, replace "Updates every minute while this chart is open and visible." with wording such as "Showing saved prices. Choose Refresh prices for a newer check." Keep the checked time, the delay note and the stale warning ("last checked more than 24 hours ago"), so old saved data is never shown as current.
- **Unchanged:** the server's company-open load steps (the "Price chart queued…" and "Fetching daily prices…" states) and the header price quote. This decision covers only the chart's own refresh timer.

Tests: opening a company makes no `refreshPriceHistory` request from the chart; choosing Refresh prices makes at most one; the status text matches each state.

## Documentation to update when built

- [beginner-mode.md](../features/beginner-mode.md): list of hidden Pro tabs
- [companion-journey.md](../features/companion-journey.md): Outlook shortcut and tab lists
- [competitor-position.md](../features/competitor-position.md) and [financial-reading.md](../features/financial-reading.md): references to Outlook
- Search `docs/features` for "Outlook" and "Summary" before finishing

## Tests

Offline browser tests reference the old tabs and must be updated, not deleted:

- `tests/browser_business.cjs`, `browser_expectations.cjs`, `browser_topic_homes.cjs`, `browser_reading_flow.cjs`, `browser_companion.cjs`: clicks on the Outlook tab → Financials (guidance, analyst table) or News & discussion (news expectations, `.outlook-news` selector)
- `tests/browser_research_design.cjs`: expected tab list
- `tests/browser_company_overview.cjs` (already modified in the working tree): merged Overview blocks

Add checks for:

- Pro shows exactly four tabs and recorded companies three; Beginner still shows Summary and News & discussion with unchanged content
- `expectations` and Pro `summary` keys redirect correctly, including the companion shortcut
- No duplicates: one Your view, one headline list on Overview, management guidance only in Financials
- News expectations and the analyst table stay closed and make no request until opened
- No paid action starts on load in any tab
- 320 px width, keyboard order and focus, reduced motion, and loading, error and empty states for each moved block

Run `tests/run_browser.py` for the affected browser tests and the related pytest suites per [AGENTS.md](../../AGENTS.md). When building the frontend, build outside `dist`, copy the assets in, and swap `index.html` last. Do not restart the running app from an agent sandbox.

## Suggested build order

1. Extract the shared components and switch Beginner Summary to them; confirm Beginner is unchanged.
2. Build the merged Overview from those components and the `OverviewReadCard`s.
3. Move `ManagementOutlook` and `AnalystForecasts` into Financials and `ExpectationsPanel` into News & discussion.
4. Update navigation, aliases, companion links and loading conditions; delete `OutlookPage`.
5. Update tests and feature docs; record verification in `docs/reviews/`.
