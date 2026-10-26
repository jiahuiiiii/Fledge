# Compact missing-figures panel — 25 October 2026

The owner asked to left-align the header and remove repeated cost emphasis and
wording. The disclosure and selection action now use shared Buttons, avoiding
legacy centered/full-width button styles. The title is “Fill missing figures”
with a short report count. Identical missing-figure labels appear once above the
checklist; differing reports retain their actual preview labels. Available rows
show their date without technical input counts or individual cost estimates.

There is one quiet combined maximum next to “Find figures with AI” after a
selection. The empty cost prompt, repeated AI-allowance reminder and free-reopen
reminder are removed. One short limited-sample note appears when relevant.
Review-before-use, unavailable-report reasons, errors and the distinction
between chart figures and monitoring inputs remain.

Verification: production build passed (existing large-bundle warning remains).
The authored offline browser journey passed with keyboard selection/collapse,
select-all/clear, sequential selected-report requests, disabled reports, retained
review, stop-on-failure, free preview reload and single-report cases. Added
checks cover left alignment, no per-report monetary text, common gaps shown once
and one combined total. Viewports 1440, 390 and 320 have no panel overflow;
desktop and phone screenshots were inspected in `recovery-screenshots/`.

Rerun with `node tests/browser_recovery_compact.cjs`, supplying an available
`PLAYWRIGHT_MODULE` and installed `CHROMIUM_PATH`. This builds an authored
static fixture in a temporary directory and intercepts all recovery API calls.
No real app/database process, paid call or saved setting was changed.
