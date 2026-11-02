# Lighter company reads — 2 November 2026

Brandon (friend review of the hosted copy) saw one open company page make 124
requests and transfer 14.3 MB in about four minutes, and a 25 s request.

## The 25 s request

`/companies/{id}/activity?wait=25` is the long poll added on 1 November. His
own Server-Timing line shows 36 ms of database work across 27 transactions in
25.3 s: the server waits for a change. Nothing on the page waits for it. No
change made.

## 1. Repeated texts sent once

One company read carried the same article or post text in up to three lists:
`documents`, `sentiment.sources` (the saved AI reading) and
`sentiment_inputs.sources` (the current selection). `thesis/workspace_payload.py`
`share_texts` moves texts of 200+ characters that occur more than once into
`source_texts`, keyed by a content hash, leaving `body_ref` where they were.
`frontend/src/lib/sharedTexts.js` puts them back inside `api.workspace` before
anything reads them, so components are unchanged. Only text already in the
answer moves; source access and withdrawals are unaffected.

Measured locally (disposable database, 150 news items with distinct text, no
saved AI reading): one read 671 KB → 285 KB. A saved AI reading adds a third
copy, so real companies should save more. Not measured on the hosted server.

## 2. Re-read only on change

- `/workspace` returns a `revision` (hash of the answer without
  `sentiment_inputs.as_of`, which changes on every read). A read with
  `known=<revision>` answers `{"unchanged": true, "revision": …}` when nothing
  changed. A field that changes per read but was missed only costs a full
  answer, never a stale page.
- The page sends the revision of the copy on screen on every re-read, and the
  cached copy's revision when switching back to a company.
- The activity token gained a middle part: newest document for the company,
  latest AI reading, newest alert for the account. The page re-reads when it
  changes. The background re-read went from every 30 s to every 120 s as a
  safety net; re-reads on window focus stay (they are now conditional).

Checked in a browser against a throwaway instance (network blocked):
idle for 150 s: 8 requests, about 1 KB (5 activity, 2 price history, 1
company read answered `unchanged` in 0.1 KB), against two full company reads
a minute before. Switching away and back: one 0.1 KB `unchanged` read, page
kept. A newly saved article appeared on the open page 2.6 s after it was
saved (including about 1.5 s to start the script that saved it). A story
whose text came through `source_texts` showed its full text when opened. No
page errors.

## Safeguards (same day, after a risk review)

- **Pages opened before the deploy.** Texts are shared only when the request
  says `shared=1`, which only the new page sends; an open old tab keeps
  getting every text in place.
- **Cost of the saved-data check.** No index serves "newest article for a
  company" (`documents` has none on `instrument_id`; adding one needs a
  migration and owner approval). The long poll now computes that part on
  every fifth check (about every 5 s); update progress and jobs stay at every
  check.
- **What wakes the page.** The saved-data part now also covers the newest
  Reddit or Hacker News post for the company, the number of withdrawn posts
  (`social_withdrawals` + `hn_withdrawals`, counted rather than by check time
  so re-checks do not wake the page) and which discussion feeds are on. A
  withdrawal now reaches an open page within about 5 s instead of waiting for
  the 120 s safety re-read.

Rechecked in the browser after these changes: shared text shown when a story
is opened; switching back answered `unchanged` (0.1 KB); a newly saved
article was on screen 2.3 s after saving; idle for 60 s: 3 requests, about
1 KB. Backend: 149 passed, 7 skipped (new tests for `shared=1`, the
every-fifth-check pattern and withdrawals moving the token).

## Tests

- New `tests/test_workspace_payload.py` (sharing, revision, unchanged reads
  over HTTP until a news item is saved) and an activity-token test in
  `tests/test_research_loading.py`; with the suites that call `/workspace`,
  market, loading and home cards: 117 passed, 7 skipped (disposable
  PostgreSQL 16).
- Frontend `npm test`: 264 passed, 1 failed. The failure,
  `companySnapshot.test.js` "summary sentences use only saved figures", is
  date-dependent and fails the same way without these changes: its fixture's
  guidance period ended on 1 November 2026, so from 2 November the sentence
  gains "This forecast period has ended."

## Not done

- Splitting the company read by tab (the larger fix for slow first opens).
- The 20 s Telegram-command poll (small answers) is unchanged.
