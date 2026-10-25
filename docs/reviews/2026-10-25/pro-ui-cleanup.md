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

See the end of this file (filled in when the checks finished).
