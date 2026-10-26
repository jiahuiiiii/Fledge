# Pro UI cleanup plan

Drafted 25 October 2026 from owner feedback after the four-tab restructure ([guide](pro-tab-restructure.md)). Pro mode only; Beginner is unchecked and must not change. Frontend only: no API, schema, worker, provider, Telegram or spending change. Nothing here may start a paid action on load.

## Rules for every task

- Compose from `frontend/src/components/ui` first. Add a kit part (with a `/?ui-preview` example) only when none fits. Needed new parts are listed below.
- One look: quiet filled surfaces, no cards inside cards, no boxed sub-panels, tight spacing tokens. Match the Life Forge UI feel (https://ui.lifeforge.dev/); inspect it for spacing, radius and density before styling.
- Removing a block removes its CSS and dead imports. Keep the components and API reads that other screens use.
- Honesty rules stay: dates, units, "not checked"/stale states, attribution and "not advice" remain, but in one short line, not paragraphs.

## New or changed shared parts

| Part | Purpose | Used by |
| --- | --- | --- |
| `EvidenceDialog` (replaces the bodies of `FinancialEvidence`, `AlertEvidence`, the Overview evidence modal) | Flat list, no nested boxes. Row = label, value, period, one source link. Optional footer slot (for Useful / Not useful) | Updates, Overview, Financials |
| `Combobox` (ui kit) | Input + floating list (absolute, never resizes its container), keyboard and 320 px safe | Peer picker |
| `SourceChip` (ui kit, tiny) | Publisher + date; a real link that opens the original in a new tab | Every story/evidence row |
| `TrendTile` (ui kit) | Small chart + latest figure beside it + period label; click opens `EvidenceDialog` | Financials top, Overview |
| `DisclosureGroup` (ui kit) | Stack of `Disclosure`s with one tight gap token | Financials, News |
| `ReviewList` | Tone-grouped list used by Overview "news and people online"; extract from `ToneHeadlineGroups` | Weekly review, Overview |

## 1. Updates tab and weekly review (`UpdateInbox.jsx`, `DailyUpdates.jsx`, `ScheduledReviews.jsx`, `ReviewDigest.jsx`, `AlertEvidence.jsx`)

1. **Inspect evidence** opens `EvidenceDialog` directly. Show only: the source (`SourceChip`, link to original), the quoted text, and two buttons **Useful / Not useful** (reuse `AlertRating`; keep its saved value and undo). Delete the expandable "evidence details" and everything else from the modal. Anything dropped (model, reasoning, ids) stays reachable only through a closed "Details" disclosure at the bottom if the audit rules require it. Confirm below.
2. **Weekly review** opens one modal, not a nested page: top = the review settings (day, time, what it includes: existing controls, as a compact form); below = "Latest review" rendered with `ReviewList` (same grouping as Overview news/people: tone groups, top few each, "show more"). Older reviews: a small select, not extra nesting.
3. Remove the parent wrapper/cards around the review content.

## 2. Overview tab

1. Keep the old **Latest activity** list (price move, headlines in the past day, "tone not up to date", updates waiting, watch status) as the main feed, restored from the pre-restructure `Activity` component.
2. Remove the **What's being said** block (it duplicates News & discussion). The three signal lights stay and link to that tab.
3. Order: at a glance + signals, Your view, Latest activity, The business (below), World news (compact), price chart (collapsed, saved prices only).
4. **The business** (merges "four reads" and "Understand the business") becomes one section: a `FilterGroup` (How it makes money, Growth, Financial health, Value) showing, for the selected topic, one reading sentence, at most two `TrendTile`s, and `SourceChip`s. Below it the brief (questions to research next, original evidence) as a closed `Disclosure`. Creating a brief stays an explicit paid action. Delete "View evidence": figures and chips open their source or the flat `EvidenceDialog` directly.

## 3. News & discussion tab (`SentimentPanel.jsx`, `MarketResearch.jsx`, `ExpectationsPanel` usage, `SourceFilters.jsx`)

1. Default layout, top to bottom: one freshness line ("News checked 25 Oct 17:32 SGT · analysed 25 Oct 17:20 SGT") and one caveat line ("Tone describes what people said, not facts or investor consensus"); filters (window, source, tone: existing `FilterGroup`s); **stories open by default**, compact (smaller padding/margins); `Pagination` at the bottom.
2. One click on a story or source opens the original link in a new tab. Fallback to the dialog only if no URL exists or access was withdrawn (keep that withdrawal notice).
3. Keep source coverage: one "Source coverage" disclosure holding how sources are counted, unavailable sources and the "label needed repair" notice. Move the rest of the status text there or delete it.
4. Remove: the "Show / Relevant / Unrelated / unclear" row with "1–6 of 27 · newest first" (tags already filter), **Expectations reported in the news**, **More headlines, not analysed**, "Compare different kinds of evidence", "Read saved sources again", and the separate analysed-sources collapse. Hide the Expectations panel; do not delete its API.
5. Keep "What are people discussing?" as one compact row if themes exist; otherwise omit. Watch and alerts stay at the bottom.

## 4. Financials tab (`FinancialsPage.jsx`, `FinancialPerformance`, `FinancialHistory`, `RevenueBreakdown`, `RevenueHistory`, `FinancialEvidence`)

1. Top: three `TrendTile`s (revenue growth, operating margin, free cash flow). Chart first, latest figure and period beside it, period selector shared. Use the saved history series already loaded; if a series is missing show "Not available", never zero.
2. Then the revenue breakdown, then `RevenueFlow`/`RevenueHistory` with guidance and forecasts.
3. Delete the "View all figures and evidence" button; every figure and chart point is already clickable into `EvidenceDialog`. Redesign that dialog as above.
4. Dissolve **More detail**: segments go under revenue breakdown, liquidity/borrowing under "What it owns and owes", filings and definitions into a small footer disclosure. Use `DisclosureGroup` so gaps are tight.
5. **What management expects**: reduce to the quoted guidance line(s) plus a chart marker; drop the explanatory paragraphs. Analyst forecasts table stays in a closed disclosure.
6. The "plot estimates with unstated currency" option: see question 2.

## 5. Compare & value (`SectorPosition.jsx`, `ValuationPanel.jsx`, `AnalystTargets.jsx`)

1. Peer search becomes `Combobox`; typing never changes the surrounding box height.
2. Restyle the tab with the same `Card`/`SectionHeader`/`TrendTile` pieces as the others. Reuse the existing P/E chart, not a new one.
3. Remove **Other comparison measures** (`FmpPanel mode="ratios"`); then check whether `mode="peers"`/`"ratios"` have any caller left and delete dead code.
4. **Analyst price targets**: a price chart (saved price history, free read) with the current price line and low / average / high target lines ahead of today; label the upside and downside percentages on the lines. Keep one line under it: source, fetched time, "over a day old" if stale, and "analyst opinions, not a probability". Move the rest into a closed "Source details and limits".

## Questions to settle before building

1. **Updates modal audit trail.** Is a closed "Details" disclosure acceptable for model/prompt provenance, or can it go entirely? AGENTS.md requires provenance to be preserved somewhere, so I recommend keeping it closed, not removing it.
2. **Unstated currency as USD, ticked by default.** I advise against silently plotting it as USD (missing must stay unknown). Better: plot by default but draw those points hollow with a one-line "currency not stated, shown as USD". Agree?
3. **Price chart collapsed** reverses your own earlier decision (open by default, saved prices only). OK to reverse? Either way it never refreshes on load.
4. **Direct links on one click.** Some sources are access-restricted or withdrawn; the fallback dialog covers those. Fine?
5. **Stale warning on analyst targets.** I'd keep one short "fetched 13 Oct · over a day old" chip so old data is never shown as current. Agree?

## Build order (one session per area; they all touch `App.jsx`, so run them one after another)

0. Finish and verify the restructure first: build, offline browser tests, Beginner unchanged. Commit.
1. Shared parts (`EvidenceDialog`, `Combobox`, `SourceChip`, `TrendTile`, `DisclosureGroup`, `ReviewList`) with ui-preview.
2. Updates and weekly review.
3. Overview and News & discussion.
4. Financials.
5. Compare & value.
6. Update browser tests and feature docs; record verification in `docs/reviews/2026-10-25/`.
