# Current news independent of saved AI readings — 12 October 2026

The owner's NVIDIA screenshot showed 8–9 October reports under “Latest reported
developments from the saved reading · 9 Oct, 03:48 UTC.” The source cache was
newer: NVIDIA's news check completed on 12 October at 01:28 SGT, with reports
published on 11 October. When an exact current company briefing was absent,
`MarketResearch` took its preview from the last successful tone analysis. Newer
raw reports remained below the tone section, inside More headlines. An old or
unsuccessful AI reading therefore froze the most prominent news preview.

## Correction

What’s developing now displays the three latest saved company headlines from
the backend's current, permitted seven-day news IDs, independently of any AI
reading. It excludes superseded/undated/non-news records and exact supplied-text
duplicates, requires an explicit name/ticker mention, and orders by publication
date rather than the briefing's relevance-first ordering. Empty or unavailable
current IDs never fall back to an older analysis or the full source archive.
Cards retain original titles, snippets, publication dates and source dialogs.
This is a browsing filter, not an AI relevance classification.

The caption separates the newest article date from the latest source-check
time. A check can succeed without finding a new matching article; the existing
source-status display still distinguishes failures, waits and unchecked feeds.
Update data opens the existing source-only update dialog. The optional metered
AI summary starts collapsed, preserving its points, view filter, original
citations and limitations. The lower More headlines list contains additional
current unanalysed company mentions, excluding the three already previewed.
Tone labels, counts, saved readings, analysis selection and watches are unchanged.
Opening or switching companies still makes no provider or AI call.

Final actual-source inspection also exposed an existing browsing-filter gap:
Micron Technology and Marvell Technology did not match headlines containing only
Micron or Marvell. The frontend now accepts these bounded short brand names as
source collection already does. Micron requires a capital M to avoid the ordinary
measurement unit; longer words are excluded. One/two-letter tickers also accept
explicit “MU stock” and “NASDAQ: MU” context, while ordinary words remain excluded.

## Actual source checks

A read-only audit covered all ten saved real companies. Apple and Marvell had
news checks from 9 October; Intuit's last check was 11 October. The other seven
had successful checks on 12 October SGT. A recoverable full database backup was
saved before two normal source-only refreshes for Apple and Marvell. Both
Finnhub checks succeeded and returned 25 reports each (including existing
reports). The publisher feeds found zero additional matches; Apple retained one
actual failed feed, while Marvell had one scheduled deferral. These failures or
waits are not hidden or presented as new articles.

Apple's check completed at 01:44:00 SGT and its newest matching article is dated
11 October 17:45:07 SGT. Marvell's check completed at 01:44:04 SGT and its newest
matching article is dated 11 October 07:31:50 SGT. Do not rerun the collection as
verification. Other normal app activity continued: NVIDIA acquired a newer saved
AI reading during this work. That was not a task-initiated model request. No AI
request, automatic retry, watch enablement, or private-research action was made
by this task. No claim is made that all database tables or the ledger remained
unchanged across source collection and concurrent activity.

## Verification

158 frontend tests and the production build pass; scoped formatting and diff
checks pass. Four new tests exercise independence from old/withheld AI results,
current permission/window IDs, supersession, invalid dates, exact duplicates,
company switching, short brands and ambiguous ticker/unit negatives. Existing
saved-development and explicit-mention tests remain intact.

The candidate browser passes 23 cases: all ten real companies; NVIDIA, Apple
and AMD at 1440/390/320 pixels with original-source dialogs, Update data dialogs,
Escape and focus return; authored older-summary/withheld-tone, empty current
pool, new source-only arrival and company-switch cases. The actual Micron case
also requires the newest saved “SpaceX vs. Micron” article, preventing a test
that merely agrees with the helper's ordering. No page errors or horizontal
overflow. Browser writes and external requests are blocked; only existing
public FMP logo attempts are expected and explicitly allowed in the blocked
request inventory. Screenshots were inspected, including full-page phone
captures to distinguish fixed navigation from the earlier locator screenshot
capture overlay.

The first candidate browser reached the final guard but expected no external
attempts; existing company-logo requests caused that harness assertion. They
were blocked throughout. The corrected assertion allows only the exact public
image-stock logo path. Preserve the original failure capture, initial audit's
incorrect refresh-state column, guessed RSS-module path and the documentation
preparation's relative-working-directory failure. The first frontend install
passed its all-table audit before the final short-name improvement; its verified
bundle and audit are retained under initial-* evidence names.

The final frontend was installed atomically: index `02410f7a`, all 30 candidate
files verified through the running app, earlier hashed assets retained. PID
29025 remained running; neither backend nor PostgreSQL was restarted. All 116
table fingerprints, schema 49, the complete model ledger and private settings
remained exact across the final installation window (separate from collection).
The installed browser also passes all 23 cases, with exact latest source cards,
original evidence, accessible dialogs and 1440/390/320 layouts. Its screenshots
were inspected. No backend suite was needed for this frontend-only correction. Provider comprehensiveness and
semantic investment relevance are not established by these display tests.

Evidence: `.local/live-tests/news-freshness-20261012/`; recoverable database and
prior frontend source/index: `.local/backups/news-freshness-20261012/`.
