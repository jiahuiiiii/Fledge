# Financial evidence and layout polish — 9 October 2026

The owner asked for readable financial evidence without long zero-heavy figures or SEC codes, aligned values below the financial history chart, and an Overview growth help icon beside its headline.

## Change

`FinancialEvidence` provides a shared visual treatment for Financials, the retained financial-overview/depth/performance views, revenue flow and breakdown, and peer/competitor evidence. Current and comparison periods appear in two desktop cards and a phone stack. Values use mil/bil/tril, percentages or multiples while retaining signs and small nonzero values. Dates remain explicit. Original reports are links; calculations expand into human-labelled inputs. Duplicate links to the same report are combined without combining different filing vintages or segment fact anchors.

Technical SEC concepts, accessions, snapshot/payload IDs and raw amendment-support tables are removed from the visible evidence. The short amendment status and links to both the figures' original report and amendments remain. Exact decimals, immutable source records, existing calculations, missing-value reasons, fiscal comparability and source permissions are unchanged. This is display formatting, not financial normalization or new data. Provider-only readings retain their provider, observation date and basis rather than inventing an external report URL.

History-card labels have the same height whether or not they include a help button; values have one type size and aligned baseline. Help controls keep their 44px hit area. The Overview growth headline and help icon share an inline layout. The history-chart footnote is shortened while the existing fiscal dates, negative values, unavailable gaps and chart definitions remain.

## Verification

- 95 frontend tests pass, including compact signs/zero/tiny/missing amounts, source-link identity and human calculation labels. Build, touched-file formatting and diff checks pass; entry bundle 371.87kB. No backend code changed and no backend suite was rerun for this UI phase.
- The disposable authored Financials journey passes at 1440/980/390/320px, covering fiscal/TTM selections, negative/missing data, shared scales, original source links, source withdrawal, keyboard and retained selections. Fixture values are not actual financial results.
- The candidate read-only browser uses actual saved AVGO/FN/AMD data at 1440/980/390/320px. It checks AVGO's 89.104bn/59.926bn trailing comparison displayed as US$89.1 bil/US$59.93 bil, correct original report URLs, calculation expansion, no codes or long raw values, aligned FN cards, inline Overview help, Escape/focus return and no horizontal overflow. It also checks revenue-flow evidence, a segment's original fact anchor, and AMD's 34.34% plus amendment link. All writes (including automatic loading) and external browser requests are blocked.
- Candidate screenshots were visually inspected on desktop and phone. The initial new calculation disclosure inherited a vertical-stick chevron; changing its summary to the existing flex convention fixed it, confirmed in the final screenshots. Initial exploratory path/glob reads and the first outside-root build warning are retained; no backend/source inference was made from them.

Evidence: `.local/live-tests/evidence-polish-20261009/`. Backup: `.local/backups/evidence-polish-20261009/` contains prior frontend and touched existing presentation files. Preserve all earlier source/financial work and independent feed-availability changes.

## Installation

Source-file hashes, file set and prior index were checked before atomic frontend index replacement. All 30 candidate assets/fonts are served and prior assets remain. Installed index: `d988f2c21a7cbed0c64ed23ca53ec9d46a289037c9d23109abde29b4d06e7c62`. App PID69431 remains running; no app or database restart. Session200/local-pitch verified. All114table fingerprints, schema47, `.env` and ledger are exact across install. No AI, provider, email, Telegram, private research or watch request was made by this task; the original unresolved paid hold remains untouched.

The installed-browser check passes at1440/980/390/320px with the same saved-data assertions, zero browser errors and only blocked loading attempts. The final installed desktop modal screenshot was visually inspected. These checks are separate from authored fixtures and are not independent financial-accuracy or usability validation.
