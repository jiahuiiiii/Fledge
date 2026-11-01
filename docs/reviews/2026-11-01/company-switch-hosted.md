# Company switching on the hosted copy — 1 November 2026

The owner reported that on the hosted website, adding a company and switching
back to one already opened both still take a long time, after the 25–27
October speed work.

## Why the earlier fixes did not cover it

The 25 October numbers (0.1–0.6 s per switch) were server time on the
owner's Mac, measured one request at a time. Three things differ on a hosted
server and were not measured:

1. **One process does everything.** `thesis/app.py` starts about 15
   background threads (four research-loading, four watch, filing, review,
   Telegram, warm-up …) in the same Python process as the web server. Python
   runs one thread's code at a time. Adding a company starts a research run
   that downloads and parses filings, news and discussions on those threads,
   so every page request from the same process waits for its turn. On a
   1–2 vCPU burstable server this is the most likely main cost.
   Not measured here: the server's logs were not available and the local
   database socket is blocked from this session.
2. **The browser kept nothing.** Every switch, including back to a company
   opened a minute earlier, read the full company again (several MB for
   news-heavy companies) behind a separate session check.
3. **Background polling from the open tab.** With a company open the page
   asked for update progress and AI status every 1.5 s indefinitely, re-read
   the whole company with financials every 30 s, and every 0.7 s while any
   evaluation job was pending.

## What changed (frontend only)

- `lib/companyCache.js`: the last read and price history of up to six
  companies opened in this tab, in memory only, keyed by account and cleared
  whenever the signed-in account changes or signs out. Switching back shows
  that page at once; a fresh read replaces it in the background (the figures
  on screen are kept until the next full read). A failed fresh read shows an
  error line instead of replacing the page.
- With a known account, the session check and company read go out together
  instead of one after the other.
- Update progress is checked every 15 s when no update is running (1.5 s
  while one runs; pressing Update checks quickly again).
- While an evaluation job is pending the company is re-read every 2 s
  without financials, instead of in full every 0.7 s.
- `readWithoutFinancials` now keeps figures from the latest state rather
  than a possibly stale closure.

## Verification

- `npm test`: 258 passed, including the new `companyCache.test.js`.
- Production build succeeds (built to a scratch folder; `dist` untouched).
- Not verified in a browser or on the hosted server. Nothing committed,
  installed or restarted.

## Not done

- Running background work in its own process (the main hosted cost above).
- Trimming the company read (every saved document body and the full latest
  sentiment reading are still sent on each read).
- Measuring on the hosted server: its `thesis.timing` log lines ("Slow
  request … ms total, … ms in database") would show whether time is spent in
  the database or waiting in Python.

## Adding a company: setup dialog with progress

The "Set up {company}" dialog after adding a company used to wait for the
page to load and then said the news had already been collected, while the
first collection had only just started. Now:

- It opens straight away and shows the Fledge fledgling (`FledgeLoader`, SVG
  and CSS only, still under reduced motion) with plain progress: "Opening…",
  then "Gathering sources… N of M checked · now: {source}" with a bar, then
  "All set!". Counts come from the research-loading run's steps; the
  optional AI rating step is not counted (`lib/setupProgress.js`).
- It explains that the first add usually takes a minute or two and that the
  dialog can be closed ("Keep browsing") while the page fills in.
- The Analyse / Watch choices are unchanged; choosing Analyse during
  collection adds the rating to the running collection (existing server
  behaviour).
- The three stages are in the UI gallery at `/?ui-preview`.

Checked: `npm test` 261 passed; build succeeds; the gallery renders all three
stages with their animations running and fits at 320 px, no console
errors. The dialog inside the real app was not opened (no app server was
started from this session).
