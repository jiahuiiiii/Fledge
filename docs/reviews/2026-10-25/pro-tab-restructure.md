# Pro tabs: four-tab restructure — 25 October 2026

Built the [four-tab restructure](../../development/pro-tab-restructure.md) in the
Pro company view. Beginner mode keeps Summary and News & discussion. Fictional
sample companies keep Overview, News & discussion and Financials. No API,
schema, migration, worker, provider or Telegram change was made.

## Structure

| Order | Tab | Key | Content |
| --- | --- | --- | --- |
| 1 | Overview | `business` | Price, saved-price chart, three signals, one Your view, news and people online, four business reads, world news, Understand the business |
| 2 | News & discussion | `evidence` | Developing stories, tone and sources, discussion themes, closed news expectations, unanalysed headlines, watch and alerts |
| 3 | Financials | `fundamentals` | Key figures, revenue flow and history, management guidance, closed analyst table, balance sheet, more detail |
| 4 | Compare & value | `valuation` | Unchanged |

`OutlookPage.jsx` and `OutlookPage.css` are removed. `expectations` is no longer a
section; Pro `summary` and `expectations` are aliased to `business` and
`fundamentals`. The `expectations` alias also focuses the "What management
expects" heading once financials have loaded.

## Shared pieces

New `OverviewShared.jsx` holds `PriceMoveLine`, `SignalLights`,
`ToneHeadlineGroups`, `YourViewCard` and `WorldSignalCard`, extracted from
`BeginnerSummary` and reused by the Pro Overview. New `OverviewReadCard`
renders the four compact business reads. Beginner output keeps the same text,
order, anchors and limits.

## Price chart

The chart renders open in Overview and reads saved prices only. Its
once-a-minute provider timer starts only after an explicit **Refresh prices**;
the next company visit starts from saved prices again. The status line says
"Showing saved prices. Choose Refresh prices for a newer check." until that
choice.

## Verification

- Fixed a leftover `setPriceChartOpen` reset in `App.jsx` (the state was removed
  with the chart disclosure). The first build deployed a blank page; the
  corrected bundle `assets/index-Co1o7wQD.js` contains no `setPriceChartOpen`
  reference.
- Pro Overview now groups every saved news item by tone, matching the Beginner
  Summary. It previously grouped only the first five source items, so relevant
  stories later in the saved list could vanish. It also shows headlines that
  have no tone label even when a saved reading exists.
- Fictional sample companies now reuse the Summary content on their Overview,
  so removing the Pro Summary tab did not hide their signals, news, people
  online, world or Your view.
- `npm test` in `frontend`: 214 passed, 0 failed.
- `vite build`: succeeded outside `dist`; the new hashed assets were copied
  into `frontend/dist` and `index.html` was swapped last. The running app at
  `127.0.0.1:8841` serves the new `assets/index-Co1o7wQD.js` bundle (HTTP 200).
- Offline browser tests updated for the new tabs and selectors:
  `browser_business`, `browser_expectations`, `browser_topic_homes`,
  `browser_reading_flow`, `browser_companion`, `browser_research_design`,
  `browser_loading`, `browser_prices`.
- Browser tests were **not run** in this session: Playwright is not installed in
  the sandbox, and the suite needs the owner's running app and database. They
  remain pending a deliberate test run.
- No paid action, provider refresh or watch change was started while building.
  No app restart or database operation was performed from the sandbox.

## Docs

Updated `README.md` and `docs/features/beginner-mode.md`,
`companion-journey.md`, `competitor-position.md`, `financial-reading.md`,
`reading-journey.md` and `original-company-research.md`.
