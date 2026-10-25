# Loading speed: compression, caching and light home cards — 25 October 2026

A friend reported more than five seconds before anything useful appeared. The
owner approved two of five proposals: compress and cache what the server
sends, and give the home company cards their own light reads.

## What changed

**Compression and caching** (`thesis/app.py`)

- Starlette `GZipMiddleware` (outermost, responses over 1 KB). Event streams
  stay uncompressed; the app has none today.
- `cache_policy()`: built files under `/assets/` (content-hashed names) are
  `public, max-age=31536000, immutable`; fonts `public, max-age=604800`; pages
  stay `no-cache`; `/api` and `/auth` stay `no-store`. Missing files (404) are
  never cached long.
- The 280 ms skeleton floor in `readableLoad` was left alone: it only applies
  on cold loads that finish faster than 280 ms, so it does not add to slow
  loads.

**Light home cards** (`thesis/home_cards.py`, `CompanyOverview.jsx`)

- `GET /api/v1/home-cards`: every catalogue company's saved quote in one read.
  Cards appear at once with prices.
- `GET /api/v1/companies/{id}/home-card?figures=`: the news-tone summary and,
  in Pro, only the trailing revenue and operating margin. Beginner asks for
  `figures=false` and skips the filing figures entirely, since it hides them.
- Readings go through the same presenters as the workspace (`sentiment.latest`,
  `financial_depth.present`), so withheld sources stay withheld; only fields
  the card reads are returned. Unknown companies are 404.
- The home no longer requests the full workspace per company. Cards show
  "Loading…" for tone and figures until their light read arrives; the grid
  stays `aria-busy` until then; a failed card read still shows "Saved data
  unavailable. Reload to try again."

## Measurements

Server timings were taken on this Mac against the owner's real data with a
read-only script (every transaction forced read-only, outside network
blocked), calling the same functions the endpoints use. 15 companies.
Asset sizes come from the production build.

### Code sent to the browser

| | Before | After |
| --- | --- | --- |
| JavaScript | 536,882 B, uncompressed | about 158.7 KB gzip |
| CSS | 254,660 B, uncompressed | about 41.4 KB gzip |
| Repeat visit | every built file revalidated (`no-cache`) | built files reused, no request; fonts for a week |

### Home page data (15 companies)

| | Before | After (Pro) | After (Beginner) |
| --- | --- | --- | --- |
| Requests | 15 full workspaces + 15 price histories | 1 quotes + 15 light cards + 15 price histories | same, without figures |
| Prices on every card | only as each full workspace finished | after one read of 11 ms | after one read of 11 ms |
| Server work, summed | 52.2 s | 23.8 s | 2.5 s |
| Slowest single read | 8.4 s (NVDA) | 3.8 s (TSLA) | 0.8 s (GOOGL) |
| Data sent | 30.6 MB (no compression) | about 131 KB gzip | about 122 KB gzip |

Before, the largest single answers were GOOGL 6.6 MB, META 6.1 MB and NVDA
5.7 MB, mostly saved news items and readings the card never showed. Price
histories are unchanged in content (639 KB raw, 114 KB gzip).

The page reads three companies at a time. Before, filling every card needed
at least about 17 s of server work (52.2 s ÷ 3), more where Python work could
not overlap. After, all prices show after one read; Beginner tone lines
finish in about 1 s (2.5 s ÷ 3); Pro figures still need about 8 s (23.8 s ÷ 3)
because each company's financial depth is rebuilt from its SEC payload
(0.7–3.6 s each).

**Estimate, not measured:** on a 20 Mbps connection the old home data alone
was about 12 s of transfer (30.6 MB) plus 0.3 s of code; the new home data
and first-visit code are about 0.3 MB together, roughly 0.1 s. On 5 Mbps the
difference is about 49 s versus 0.5 s. Whether the friend's route already
compresses responses is unknown.

## Verification

- `tests/test_home_cards.py`: 16 passed (quotes cover the catalogue, only two
  figures and the tone summary are returned, Beginner never computes figures,
  withheld readings stay withheld, 404 and cross-origin guards, gzip on large
  answers, cache policy per path and status, a real built file served gzip
  with the one-year header).
- All 30 Python files that call the app over HTTP: 576 passed, 18 skipped,
  1 failed. The failure,
  `test_alert_feedback.py::test_ratings_append_without_changing_research_and_same_app_vote_is_idempotent`,
  is date-dependent and unrelated: its fixture records an event at
  2026-10-15 and `review_digest.prepare()` looks back seven days from today.
- Frontend: 214 passed; production build succeeds.
- Isolated offline test server (disposable database, stopped afterwards):
  real responses carry gzip and the cache headers; the home page made one
  `home-cards` read, one `home-card` read per company and one price history
  per company, with no per-company workspace reads and no console errors;
  Beginner requested `figures=false`.
- `tests/browser_company_overview.cjs` now mocks the two new reads (with the
  same fail/hold cases). It was not run: Playwright is not installed here.

## Not done

- The app still reads one full workspace at startup before the home renders
  (proposal 3, staged company page).
- Pro figures remain slow because financial depth is recomputed per request
  (proposal 5, caching).
- No timing on the friend's device.

## Safe before a restart

The running app only gains `/api/v1/home-cards`, `/home-card`, compression and
the new cache headers when it restarts. So the frontend can be installed
first, `CompanyOverview` falls back when the quotes read fails or does not
return a list (404, not JSON, no answer): it reads each company's workspace
and price history as before, three at a time. In Beginner mode the fallback
asks for workspaces without financials, which is lighter than before.

Checked against the committed backend (`git archive HEAD` in a scratch folder,
offline, disposable database): `/api/v1/home-cards` answered 404, the page
fell back to one workspace read per company, cards showed their figures,
`aria-busy` cleared, and no script errors appeared (only the browser's own
404 log line for the probe).

## Deploying

1. Installing the new frontend before a restart is safe: home cards use the
   fallback and look as they do today.
2. Only the owner's deliberate restart of the app (after the usual idle
   check) turns on compression, the cache headers and the light home reads.
   Until then the measured gains do not apply.
3. No restart or install was performed by this work.

## Latest sentiment reading: migration 071

After the restart the home still felt slow. Profiling against the owner's
data (read-only) showed one lookup behind most of it: the latest sentiment
reading per company sorted on the cutoff inside each reading's packet. The
table is 1.5 GB (1,270 readings, up to 280 per company, packets of several
MB), so every lookup unpacked every packet: about 0.8 s per company. Five
places used it: the workspace (twice per company open), the home-card tone
line and portfolio summary (through `sentiment.latest`), sentiment history,
idea alerts and the background news watch.

The owner approved an additive migration on 25 October (requested as 069;
069 and 070 were already taken, so it is **071**):

- `sentiment_analyses.cutoff` (timestamptz), set from the packet by a
  `BEFORE INSERT` trigger, backfilled once inside the migration (the
  `immutable` trigger is disabled only around that `UPDATE` in the same
  transaction), and indexed on `(instrument_id, cutoff DESC, created_at DESC,
  id DESC)`. Packets and results are unchanged; readings stay immutable.
- The four "latest" lookups share `sentiment.LATEST_SQL`; sentiment history
  orders and pages by the column. Ordering is the same as before.

### Before and after (same data)

Measured on a disposable copy of the owner's database (made with `pg_dump`,
restored into a temporary cluster under `/private/tmp`, deleted afterwards),
before and after applying 071. Each read ran twice; the warm time is shown.

| Read | Before | After |
| --- | --- | --- |
| Latest reading, all 15 companies | 2.59 s | 0.33 s |
| `/portfolio` ("How each moved") | 2.29 s | 0.29 s |
| Home-card tone lines, all 15 (Beginner) | 2.47 s | 0.50 s |
| Open NVDA (workspace, no financials) | 5.76 s | 3.78 s |
| Open GOOGL (workspace, no financials) | 3.86 s | 2.90 s |

On the same copy the migration itself took 3.7 s; all 1,270 rows received
the same value as their packet (0 mismatches) and the `immutable` trigger was
enabled again.

Opening a news-heavy company is still several seconds: the workspace still
sends every saved document (proposal 3). Pro card figures are unchanged
(financial depth, proposal 5).

### Verification

- `tests/test_sentiment_cutoff.py` (new): the column mirrors the packet on
  insert; "latest" still means latest cutoff, not latest save; history order
  and paging are unchanged; updates are still refused; the latest and history
  lookups use the new index; no module sorts on the packet cutoff any more.
- All test files touching sentiment readings, alerts, news watch or
  migrations: 1,399 passed, 20 skipped, 1 failed (the same date-dependent
  `test_alert_feedback` case noted above).

### Deploying 071

071 applies automatically at the owner's next deliberate restart (after the
usual idle check), taking a few seconds on this data. The code that uses the
new column must only run against a database that has 071, so the backend
code and migration go live together at that restart. Nothing is committed,
installed or restarted.

## Figures after a restart: background warm-up

After the 071 restart the home still felt slow. The remaining cost was the
Pro card figures: `financial_depth.present()` parses the original SEC filings,
and the in-memory overlay cache is empty after every restart. Measured on
the owner's data, read-only: all 15 Pro cards 20.7 s of work cold, 3.5 s warm.

`home_cards.warm_figures()` builds every SEC company's figures once, and the
app starts it in a background thread 3 seconds after startup (`warm_loop` in
`lifespan`). It reads saved data only and stops with the app.

| Fresh process (like a restart) | Server work |
| --- | --- |
| Warm-up, 15 companies | 22.2 s, in the background |
| All 15 Pro cards after the warm-up | 4.4 s (slowest 1.0 s) |
| All 15 Pro cards with no warm-up (before) | 20.7 s (slowest 3.6 s) |

Someone opening the home page in the first ~25 s after a restart still meets
part of the cold cost. A permanent fix (saving figures per exact input) is
proposed in `saved-filing-figures-design.md` and awaits approval.

Tests: `test_home_cards.py` 18 passed, including that the warm-up visits each
SEC company once, stops when asked, and that the next card read reuses the
parsed filings instead of parsing again. Takes effect at the next restart.

## Saved filing figures: migration 072

Approved by the owner on 25 October (`saved-filing-figures-design.md`), built
with one stricter change: rows are per account (see the design note).

- `filing_figures(owner_id, instrument_id, basis, depth)`, append-only,
  row-level security per account.
- `financial_depth.present()` computes a `basis` hash from small indexed
  columns (source access, SEC payload id/check time/CIK, every saved
  disclosure document's id/url/form/source/accession/hash/dates, this
  account's recovery readings and newest reviews, and the calculation
  versions). A matching saved row is returned; otherwise it builds as before
  and saves the finished result in its own short transaction. Only
  `available` results are saved; reads without an account never save.
- Dates and decimals anywhere in the result are tagged so a saved result
  reads back equal. A first version only handled the two top-level dates;
  on the owner's data some results have nested dates, so their saves failed
  safely (rebuilt every time, nothing wrong shown). Fixed before release.
- The startup warm-up now runs per background account, so saved figures
  exist soon after a restart or an input change.

### Before and after (copy of the owner's data, fresh process each run)

Each run is a new process, like a restart. "Without saving" disables the
saved table, which is exactly the previous behaviour. The Financials tab is
timed first so the card loop cannot warm it.

| Fresh process | 15 Pro cards | Slowest card | Financials tab NVDA / GOOGL / MSFT |
| --- | --- | --- | --- |
| Without saving, run 1 | 18.05 s | 4.32 s | 2.06 / 1.59 / 4.86 s |
| Without saving, run 2 | 15.98 s | 3.53 s | 2.32 / 1.86 / 6.17 s |
| With saving, first run (builds, saves) | 14.31 s | 3.39 s | 1.95 / 1.62 / 4.66 s |
| With saving, run 2 | **0.43 s** | 0.12 s | 1.66 / 1.36 / 4.43 s |
| With saving, run 3 | **0.52 s** | 0.15 s | 1.74 / 1.38 / 5.52 s |

All 15 companies' saved-then-reloaded figures equal a fresh build exactly
(checked on the copy after the encoding fix). Migration 072 applied in
0.02 s. The Financials tab barely changes: most of its time is income flow
and segment revenue, which still parse the filings (not part of 072).

### Verification

- `tests/test_filing_figures.py` (new, 12 passed): saved equals a fresh build
  and is reused; each input change rebuilds — new SEC payload, new saved
  filing, source access change, new recovery reading, new review, version
  bump, calculation method change; another account never sees or reuses
  this account's row; reads without an account are never saved; unfinished
  results are not saved; rows are immutable; dates and decimals round-trip.
- All test files touching SEC figures, recovery, valuation, the workspace or
  migrations: see the final count in the session report.

### Deploying 072

Applies automatically at the next deliberate restart. After the restart the
warm-up builds and saves each company's figures once (about 20 s in the
background); from then on figures come from the saved table until an input
changes. Nothing committed, installed or restarted.
