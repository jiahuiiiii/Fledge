# Visual peer comparison and draft preservation — phase 92

9 October 2026. This continues the original business-research/expanded-peer work and requested visual UX. It adds no provider connection or new financial calculation.

## Installed experience

**Peer comparison** in Business brings the selected company and up to three saved peers into one chart. Its eight figure/source choices are Finnhub P/E/P/S, separate FMP P/E/P/S, and existing SEC trailing revenue, operating margin, free cash flow and period-end borrowing. Values retain exact source strings and evidence; chart geometry alone uses display numbers. Each chart has a single provider/measure, a shared zero-inclusive scale, stable company order and accessible textual values. Negative cash flow stays negative; zero is not missing. A missing ratio never takes another provider's value. Incomplete borrowing is not replaced by a component.

Observation dates and fiscal dates are shown separately from source definitions. Old vendor observations are labelled after 24 hours without asserting an underlying quote time. Different fiscal calendars remain explicit. Source details retain original filing inputs, dates, identities, private comparison rationale and dated vendor industry classifications. Classification alone does not establish product competition or valuation comparability. Explanations follow the [SEC financial-statement guide](https://www.sec.gov/about/reports-publications/investorpubsbegfinstmtguide) and [FINRA's discussion of valuation context](https://syndication.finra.org/content/defining-value-investment); no automatic investment ranking is added.

Unsaved peer edits now survive leaving/returning to the Business tab and checking data. A delayed read started before Save cannot overwrite the saved response. Save remains explicit; Discard restores saved choices without another write. Source and measure controls never save a peer or request data. The panel is scoped to its company and unmounts on sign-out. Existing private-account isolation, provider controls and database schemas are unchanged.

The forecast/peer panel and chart load when needed. The initial JS bundle is 488.03 kB, below the initial 500.06 kB build warning. The chart supports keyboard measure selection, 320px layout and reduced motion.

## Checks and actual saved sources

All **34 frontend checks** pass, including six new source-separation, missing-value, permission, unit/date/evidence, signed-scale and incomplete-debt controls. Formatting and production build pass. Both guarded isolated business browser runs pass. Final coverage includes **1440/980/390/320px** charts, original evidence, separate FMP/Finnhub values, negative cash flow, borrowing, keyboard/reduced motion, missing references without fallback, draft persistence, Discard, and a deliberately delayed read after Save. Exactly two explicit peer writes occur in that authored journey; navigation/chart controls/discard create none. Desktop and 320px screenshots were visually inspected.

Screenshots use authored Microsoft/NVIDIA-shaped fixtures, not their actual results. Controlled FMP refresh uses the existing local context response, without an external request. The disposable runtime retains its external-network guard. No backend suite was repeated for this frontend-only change; phase91's full run remains separate. There was no new failing app test. An initial log-tail command used the frontend working directory with a root-relative evidence path and found no file; the corrected read recovered the existing log. The initial bundle-size warning and final builds are retained.

A read-only projection of the actual retained Broadcom context has **zero privately selected peers**, preserved. It shows Finnhub P/E **46.611** and P/S **20.0167** from their existing saved reference. FMP ratios remain unavailable with the original 402 diagnostic; no new subscription request or retry occurs. Existing SEC projections retain revenue **US$89.104bn**, operating margin **48.04947028191775902316394326%**, free cash flow **US$39.403bn**, and borrowing **US$61.079bn**, with exact dates/payload/input identities. These are checks of existing source values and presentation, not a new financial-condition assessment or a signed-in main-browser claim.

## Installation and remaining scope

Backup `.local/backups/phase92-peer-comparison/` contains prior touched files and installed frontend; evidence is `.local/live-tests/peer-comparison-20261009/`. Atomic index installation retained previous assets. The managed-session endpoint and all entry/lazy assets were checked. **No server or database restart.** Installed index hash: `1cca8ff7e47f7236b0b4d786f72d4a951b33c8bfa295c2b97c4015efe04f2a3f`.

All **114 table fingerprints are identical** between the initial audit and post-install check. Schema46, three owner watches/zero others, private research/peers/auth records, notifications, source denials and provider clocks remain unchanged. One ordinary app call settled between phase91's audit and this phase's initial audit; this feature made no AI/Telegram call. Initial/final ledger: **US$20.9395215 confirmed + US$0.9156025 historical holds**, **US$8.144876 available** of the original US$30, 370 calls and zero blockers.

Alpha Vantage forecast access remains unverified behind the original shared pause until 9 October **13:00:28 SGT**. Restricted FMP ratios/estimates are not unlocked by these charts. Full forecast coverage, cross-company economic comparability and independent beginner usefulness still need evidence. The four-part goal remains incomplete. Codex's last read showed 20% remaining and the reset card untouched, consistent with the owner's critical-only reset instruction.
