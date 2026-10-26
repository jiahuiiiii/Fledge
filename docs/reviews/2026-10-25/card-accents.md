# Card accents — 25 October 2026

At the owner's request, ornamental left borders were removed from content
boxes and callouts across Summary, Overview, Financials, Outlook, comparisons
and research notices. The rounded “What do you think…” card no longer has the
inset green edge. Ordinary neutral card outlines and fills remain. Straight
quotation rules, metric markers, chart references and layout separators retain
their roles.

Summary's News and People online tone-group headings no longer render dots.
Their labels, counts, heading colours, original source text and source actions
remain. The top overview indicators are separate from these group headings.

Verification: production build passed, with the existing large-bundle warning.
An ephemeral, authored offline Chrome preview checked the actual Summary
component and representative card styles at 1440, 390 and 320 px. All six
news/discussion groups retained headings, with no heading dots; representative
cards have matching left/right outline widths and no inset shadow. No page
overflow, browser errors, API or external requests. Desktop and phone captures
were visually inspected and saved under `surface-screenshots/`. Temporary
preview sources were removed. `git diff --check` passed. No backend, saved
research, live settings or running processes were changed.

Owner follow-up: added a small gold lightbulb to the left of the Overview
“What do you think…” heading, using a reusable line icon. It is decorative for
screen readers, keeps a fixed 20 px width while the company name wraps, and
does not add a left-edge highlight. Production rebuild and diff checks passed.
