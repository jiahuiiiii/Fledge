# Pro UI cleanup — 25 October 2026

Executes [pro-ui-cleanup-plan.md](../../development/pro-ui-cleanup-plan.md). Frontend only; no API, schema, worker, provider, Telegram or spending change.

## Built

- Shared parts in `components/ui`: `SourceChip`, `EvidenceDialog`, `DisclosureGroup`, `TrendTile`, `Combobox` (examples at `/?ui-preview`). The old `FinancialEvidence` dialog was restyled flat for every caller.
- Updates: `InboxRecord` card, flat evidence dialog (sources + Useful / Not useful, provenance in a closed Details line), weekly review as one modal (`WeeklyReview`). `ReviewDigest` and `ScheduledReviews` removed.
- Overview: restored Latest activity (`LatestActivity`), removed "What's being said", one `OverviewSections` "The business" (topic picker + closed brief), price chart in a closed disclosure (saved prices only).
- News & discussion: one freshness line, open compact stories, direct links, Source coverage disclosure; Expectations and "More headlines" removed from Pro.
- Financials: trend tiles, revenue breakdown first, figure buttons instead of per-row collapses, "View all figures" removed, More detail dissolved, management outlook header trimmed, unstated-currency estimates plotted by default.
- Compare & value: `Combobox` peer search, `TargetChart` for analyst targets, "Other comparison measures" and the dead `FmpPanel` peers/ratios modes and `PeerComparison` removed.

## Decisions taken from the plan's open questions

Provenance kept in a closed Details line; unstated-currency estimates plotted as USD by default with a visible assumption note; price chart collapsed; links open the original and fall back to the saved source; one short stale chip kept on analyst targets.

## Verification

- Frontend unit checks: 220+ pass (new: `alertEvidence`, `financialTrends`, dialog rows). Production build clean (built to a scratch folder; the live `frontend/dist` was not touched and the app was not restarted).
- New offline journey `tests/run_browser.py --pro-cleanup` passes: Updates evidence dialog (source link, quote, Useful / Not useful, closed Details, no nested collapses), weekly review modal (settings + tone-grouped latest review, no collapses), four Pro tabs, Overview without "What's being said"/"View evidence", News without Expectations/"More headlines", Financials trend tiles and evidence dialog, Compare combobox that never resizes its card, no external calls and no writes. The inbox and weekly-review endpoints are authored mocks.
- Looked at in the browser pane on the fictional seed: Overview, Financials (tiles, breakdown, chart with USD-assumed estimate, closed sections) and the shared parts at `/?ui-preview`.

## Not verified / outstanding

- The older journeys still assert the previous DOM and fail: `--company-overview`, `--business`, `--expectations`, `--news-discussion`, plus (not run) `--topic-homes`, `--reading-flow`, `--companion`, `--research-design`, `--financials`, `--sector-position`, `--valuation`. Each needs its selectors moved to the new layout (Outlook tab, expectations disclosure, "Read analysed sources", More detail, Weekly review page, per-row Inspect figure).
- `--inbox`, `--scheduled-review`, `--digest` and `--idea-alert` cannot seed: `seed_sentiment_browser.py` fails on `assert news_watch.publish(...) == 2`, independent of this work.
- Real seeded data was not used for the News story list, the analyst-target chart or the Latest activity list; check them on a real company after the owner installs the build.
- Dead CSS from removed blocks remains in `styles/app.css` (periodic review, saved weekly list, inbox detail) and `UpdateInbox.css`.
- Compare & value's layout (`SectorPosition`, `ValuationPanel`) kept its own card styling; only the peer picker, target chart and ratios panel changed.

