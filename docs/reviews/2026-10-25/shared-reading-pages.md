# Shared News, World news and Updates UI — 25 October 2026

The owner asked to redesign these three pages around the existing reusable UI
and create reusable parts where needed. The pages now share the Overview's
neutral surfaces, compact headings, small corners, accent actions and metadata.
Actions stay left-aligned; ornamental left borders are not reintroduced.

## Reusable parts

Added `Disclosure`, `FilterGroup`, `EmptyState`, `MetaRow`, `Pagination` and
`StoryCard` under `frontend/src/components/ui/`, plus globe and refresh icons.
They are exported from the existing UI entry point, documented in its README,
and demonstrated in the authored `/?ui-preview` gallery. Callers own data,
permissions, timestamps, cursors and actions. No dependency was added.

- Disclosures retain native details/summary keyboard behaviour. Controlled
  source-list and lazy recap state still belong to their existing components.
- Filters use labelled pressed buttons, including optional counts and icons.
  Missing counts are not invented. Pagination adapts the existing cursor and
  one-based display without changing the server's page semantics.
- Story cards receive exact supplied headlines and text. Original-article links
  and source-inspection dialogs keep their existing destinations.
- Empty states keep loading, failures, unavailable connections, withdrawn
  evidence and actual empty results distinct.

## Pages

**News & discussion:** shared story cards for current headlines and additional
headlines; shared summary/source-status disclosures; common source/tone filters,
metadata and pagination. Removed duplicate reading-date wording and moved the
explicit full re-read option below the reading. Dates, counts, source windows,
stale/method/partial-coverage warnings, exact evidence and original paid/watch
controls remain. The default source and retained filters/paging are unchanged.

**World news:** the page heading, actions, filters, article cards and possible
company effects now use shared parts. Theme tags remain code-owned; supplied
headlines, summaries, publishers and dates remain exact. AI effects are labelled
as interpretations. Unavailable checks have concise reasons. Source refresh,
watchlist checks, saved results and the existing automatic stale-headline refresh
policy are unchanged.

**Updates:** matching page heading and left-aligned actions, shared filter and
coverage disclosures, compact record metadata, review badges, evidence cards,
empty states and pagination. Daily recap containers and review/rating controls
use the same parts. Weekly review stays a single heading action. Exact source
previews, original record order/cutoff, company/status filters, withheld evidence,
explicit review/rating writes and lazy read-only recap access remain intact.
Cost details stay inside the recap disclosure rather than being repeated in its
closed heading. Removed obsolete filter/source-status rules from ReadingFlow.css
that conflicted with the new shared components on phones.

## Verification

All browser checks below use authored data and mocked API actions. None accessed
the real app or database, fetched providers, sent a message or called a model.

- Frontend library suite: **214 passed**.
- `browser_news_redesign.cjs`: passed at 1440, 1024, 768, 390 and 320 px;
  keyboard/focus, retained source filters/paging, exact evidence and
  empty/withheld/stale readings. Zero API/external requests and browser errors.
- `frontend_reading_pages.mjs`: passed at 1440, 768, 390 and 320 px; World filters,
  saved/empty/failed readings, disabled and explicitly requested mocked actions;
  inbox keyboard disclosures, exact source inspection, review/rating, filters,
  cutoff pagination, lazy read-only recaps, withheld evidence, late-response
  fencing and standalone shared-component gallery controls. Zero HTTP requests
  and browser errors.
- `frontend_daily_updates.mjs`: **10 browser groups passed**, including exact and
  unresolved spending, recap paging, ratings, withdrawal, errors and late-result
  rejection; zero HTTP requests.
- `frontend_price_moves.mjs`: **13 browser groups passed**, including price and
  company evidence, routing, review/rating and all-company versus company scope;
  zero network requests.
- Production build passed with the existing main-chunk size warning. Scoped
  formatting and diff checks passed.

Desktop and phone screenshots were visually inspected in
`reading-pages-screenshots/` and `news-screenshots/`. An initial fixture syntax
error and test action-log collision were corrected before the final passing
runs. The initial daily-test invocation used a directory as an ES module; the
successful invocation uses Playwright's module file.

These are presentation and authored-interaction checks, not independent user
validation or evidence of live provider/AI quality. No server/database restart,
schema, private settings, stored research, ledger, paid call or delivery change
was performed. Existing unrelated work was preserved. Nothing was committed,
pushed or opened as a pull request.
