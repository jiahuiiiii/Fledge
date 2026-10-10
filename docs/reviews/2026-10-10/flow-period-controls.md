# Clearer, smaller period controls — 10 October 2026

The owner found the revenue chart's period controls bulky and did not understand “Trailing year”. The shared Overview/Financials component now uses **Past 12 months** with a short definition, compact year/date buttons, and original exact reporting dates. Repeated revenue previews and the unnecessary single-period picker are removed. No backend, data, calculations, sources or saved settings change.

Contract: [revenue flow](../../features/revenue-expense-flow.md#compact-period-controls--10-october-2026). Evidence `.local/live-tests/flow-period-controls-20261010/`; backup `.local/backups/flow-period-controls-20261010/`.

116 existing frontend tests and the production build pass. Browser verification uses actual saved AVGO in both Overview and Financials at 1440/980/390/320, all three period types, latest/first date selection, keyboard activation, 44px controls and selected-date visibility. Original annual country evidence remains US$16.51bil with the same report link, Escape and focus return. Browser loading writes and external traffic are blocked. No backend suite is needed for this copy/layout change.

Preserve the initial guessed CSS path and overly broad search diagnostics. The first desktop capture placed the controls under the sticky header because the test scrolled during a transition; the capture was corrected to use instant scrolling. Final styling, installation and screenshot results are recorded below.

Final caption styling explicitly overrides the existing broad paragraph rule; the selected period underline and 44px targets are retained. Candidate desktop and 320px screenshots inspected. Atomic frontend index09ac8c21/all33assets verified with source/file-set/prior-index guards. Older assets retained; PID86392 unchanged and no restart. All114table fingerprints/schema47/.env/ledger exact across installation. No source collection, AI, private research/watch, email or Telegram action.

Installed browser verification passes the same24 viewport/tab/period combinations, correct dates, original evidence and keyboard/focus with no errors or overflow. Desktop and320px installed screenshots inspected.
