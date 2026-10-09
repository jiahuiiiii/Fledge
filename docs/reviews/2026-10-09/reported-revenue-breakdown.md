# Reported revenue breakdown — phase 89

9 October 2026. The original four-part request included original filings, business/financial depth, managed login, and consensus/reviewed peers once access and cost were clear. This phase advances the business/financial-depth item and the requested visual Fundamentals page. It does not close the complete four-part goal or the wider roadmap.

## Implemented and installed

Fundamentals now includes **Where revenue comes from**. Users select operating segments, products/services or reported geographies, then a separate quarter, fiscal-year-to-date or annual period. A proportional overview and individual bars show the mix only when all supported values reconcile exactly to the matching positive company total. Otherwise, the amounts remain a list with an explanation. Missing values never become zero. Every figure exposes its exact amount and original filing anchor.

The implementation reads current retained annual/quarter Inline XBRL in a read-only workspace transaction. It uses no external source request, paid model, new provider, migration or historical-document rewrite. Method `sec-segment-revenue-1` is separate from existing financial, business and monitoring methods. The [feature contract](../../features/original-company-research.md#reported-revenue-breakdown) records supported contexts, units, periods, reconciliation and limits.

## Actual retained Broadcom evidence

The current annual document is `avgo-20251102.htm`, and the current quarter is `avgo-20260802.htm`, both collected in the earlier original-document phase. Original immutable captures have no stored reporting-period field; this reader obtains the period from the filing's own DEI fact without updating those captures. Source bytes and initial/final parsed results remain under `.local/live-tests/segment-revenue-20261009/`.

| Operating segments | Semiconductor solutions | Infrastructure software | Consolidated revenue |
| --- | ---: | ---: | ---: |
| Quarter, 4 May–2 August 2026 | US$20.839bn | US$8.752bn | US$29.591bn |
| Fiscal YTD, 3 November 2025–2 August 2026 | US$48.363bn | US$22.726bn | US$71.089bn |
| Annual, 4 November 2024–2 November 2025 | US$36.858bn | US$27.029bn | US$63.887bn |

All three operating-segment groups and all three product/service groups reconcile exactly. The quarter and YTD geographic groups also reconcile. The annual geographic group contains eight country/region categories whose sum exceeds the total: it is deliberately **not charted**. The reader does not infer which categories contain others. Nine groups are retained, eight chartable.

The quarter semiconductor input retains fact anchor `f-1055`, displayed value `20,839`, USD unit and scale six. Controlled arithmetic checks separately assert the annual/quarter operating totals and annual-geography withholding. These are selected source/calculation checks, not independent universal validation of filing interpretation, economic exposure or peer comparability.

## Verification

- Initial guarded focused run: 57 passed, including the explicit retained Broadcom corpus. Two later controls add namespace-alias conflict handling and rejection of excess decimal precision.
- Final guarded full backend suite: **1,470 passed, 65 optional-corpus skips** in 203 seconds. Authored cases cover correct units/scales/signs, missing/zero/negative amounts, conflicting/equal duplicates, duplicate XML IDs, namespace aliases, wrong issuer, comparative periods, separate concepts/periods, nested/typed/unknown context qualifiers, excluded display text, XML limits, source permission and read-only preservation.
- Frontend: all **28 existing checks** and production build pass. No new dependency.
- Guarded isolated business browser journey passes twice. It covers period/category changes, keyboard selection, exact source anchors, overlapping geography without bars, missing categories, reduced motion and 1440/390/320px revenue layouts, alongside the existing business/original/private-peer/login and fundamentals checks. Final screenshots were visually inspected. Screenshot figures are authored software fixtures, not real Microsoft results.
- The restarted main app serves the installed index and every referenced bundle. Session route returns 200, unauthenticated private access 401, invalid-email login 422 without sending email. The real workspace calculation returns nine Broadcom groups. The owner's browser sessions were expired, so no final signed-in actual-browser visual claim is made.

The first screenshot pass captured desktop layout/reading transitions mid-animation. The final capture waits for finite animations and positions the heading relative to the correct scroll container. This was evidence-capture refinement, not a provider or arithmetic failure. Both browser logs and the final images are retained. There were no failing backend cases in this phase; earlier phases' failures remain untouched.

## Preservation and recovery

Before editing existing integration files, `.local/backups/phase89-revenue-view-20261008T191638Z/` preserved their prior contents and the installed frontend. This is a code/interface backup, not another database dump or a new paid installation. Earlier database backups and verified restore evidence remain available.

All **114 database tables have identical fingerprints** from the initial read-only main audit through installed verification. Schema remains 46. Owner ideas, identity mappings, source permissions/denials, watches, notification state and original cumulative allowance are unchanged during that measured interval. Three original-owner watches remain enabled and zero others. The restart confirmed zero active calls and no active `lease_until` in any public table, verified the listener command/cwd, then stopped the app gracefully while leaving PostgreSQL running. Backend checks preceded copying assets and atomic index replacement; old assets were retained for existing tabs.

At installed verification, the original US$30 ledger records **US$20.850354 confirmed + US$0.9156025 historical holds**, **US$8.2340435 available**, 369 calls, zero running/attention/unresolved calls. The two calls since phase88 occurred during ordinary running-app activity before this phase's initial audit; this read-only feature and its verification made no AI/Telegram call. Do not equate a running installation with globally zero external activity.

## Remaining work

General custom revenue concepts, multi-dimensional hierarchy, IFRS, non-USD measures, uniform peer segment definitions and broad independent user/semantic validation remain open. Full quarterly/multi-year analyst forecast coverage and the recorded FMP estimates/ratios access restrictions are separate unfinished work. Alpha Vantage's documented `EARNINGS_ESTIMATES` endpoint is a potential annual/quarterly source; live access has not been attempted or established. Its access must not be inferred from the separate NEWS_SENTIMENT restriction or tested by clearing existing provider pauses.

Primary references: [SEC companyfacts scope](https://www.sec.gov/search-filings/edgar-application-programming-interfaces), [Inline XBRL 1.1](https://www.xbrl.org/specification/inlinexbrl-part1/rec-2013-11-18/inlinexbrl-part1-rec-2013-11-18.html). Original [Broadcom annual filing](https://www.sec.gov/Archives/edgar/data/1730168/000173016825000121/avgo-20251102.htm) and [quarter filing](https://www.sec.gov/Archives/edgar/data/1730168/000173016826000080/avgo-20260802.htm) links refer to the previously retained evidence; this phase did not refetch them.
