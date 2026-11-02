# Slow queries on the owner's data — 2 November 2026

After the lighter-reads change, some pages still took 6–9 s on the owner's
Mac. A run with `THESIS_SQL_TIMING_MS=200` named the costliest queries per
request (load about 4 on 11 CPUs, so not CPU-bound):

| Request | Total | Costliest part |
| --- | --- | --- |
| `companies/{id}/alerts` | 19.8–25.0 s | `SELECT * FROM sentiment_analyses WHERE id=ANY(…)` 12.2–16.1 s; permitted articles and posts once per reading (15–42 times); conversation results ×323 |
| `workspace` | 2.5–9.9 s | latest reading ×2 (0.6–2.3 s), conversation lookups ×407–1,208, price snapshots ×45–113, evaluations ×11 |
| `financial-story` / `financial-recovery` | 4.4 / 6.8 s | raw 10-K/10-Q HTML (up to 5.4 s), the SEC payload (0.4–1.5 s) |

Trivial statements (`SELECT 1`, `set_config`) took 200–600 ms right after the
big reads: decoding megabytes of JSON held the Python interpreter, so every
other request waited too. On each restart the financial warm-up re-parsed
all ~21 companies back to back.

## Changes

**A. Saved AI readings decoded once** (`sentiment.readings`, `reading`,
`latest_record`). `sentiment_analyses` rows are immutable (trigger) and
shared, so a decoded row is kept in memory by id (pickled, 128 MB cap,
least recently used out first, a reading over a quarter of the cap is served
but not kept) and each caller gets its own copy. `present()` still applies
current access and withdrawals on every read. "Latest reading" reads only
the id from the index, then the cached row. Read paths switched: alert
lists, idea checks, watch history, discussion themes, reading history,
source selection, the news-watch worker. Writes are unchanged.

**B. One query instead of one per item.**
- Parent-context checks (`sentiment_context`): conversation results are
  immutable and shared, so found rows are kept (20,000-row cap); a reading's
  missing ones load in one query (`prefetch`); the current selection's
  latest checks load in one query instead of one per post.
- Permission checks per reading read ids only
  (`service.permitted_document_ids`, `social.document_ids`). Each shares its
  FROM/WHERE text with the full read it replaces, so the two cannot drift; a
  test compares them, including after a withdrawal.
- Price references (`sentiment_guards.attach`): the snapshot id per post
  from the index, each distinct snapshot's series read once.

**C. Filing data.**
- `sec/saved_payload.current`: the small "which payload is current"
  pointer is read every time (a refresh shows at once); the decoded payload
  is kept by id (immutable rows; 96 MB cap). Used by financial depth, income
  flow, financial story and financial recovery.
- The parsed-filing cache key uses the payload id instead of JSON-encoding
  and hashing the whole payload on every read.
- The startup warm-up pauses 1 s between companies.

Each cache is per process and only holds rows the database refuses to
change; tests clear them between cases.

## Not changed

- The company read still sends every idea version's evaluations
  (`evaluations` ×11, 1–2 s); reshaping that belongs with splitting the
  read by tab.
- Raw filing HTML is still read when the parsed-filing cache misses (first
  open after a restart, or when the filings change).
- Background workers still share the web process.
- No measurement on the owner's data yet: the same `THESIS_SQL_TIMING_MS=200`
  run after the warm-up settles will show the effect.

## Tests

Disposable PostgreSQL 16, offline:
- Full suite: 3,023 passed, 108 skipped, 7 failed. The 7 fail the same
  way on the previous commit: six HTTP-transport tests in
  `test_model_budget.py` and `test_provider_transport.py` (this sandbox's
  network proxy) and `test_question_library.py`'s font check (no
  `frontend/dist` built here).
- New `tests/test_reading_cache.py`: one load per reading, independent
  copies, other company's id refused, cached and uncached latest reading
  present identically, memory cap and oversize readings, ids-only
  permission checks equal to the full reads (also after a withdrawal).
- Two unit tests that faked `rows`/`one` now fake the batched paths
  (`test_alert_payload.py`, `test_sentiment_context.py`); what they assert
  is unchanged.

## Second round (owner's run after the first)

Owner's run after the first round: alerts 2.1 s and 9.9 s (first opens
after a restart), company read 1.8–4.3 s, financial story 2.6 s,
financial recovery 18.0 s. What was left, and what changed:

- **Background reuse lookup** (`sentiment_reuse.find`) loaded the 40 newest
  full readings on every scheduled check (3.6–9.7 s each). It now reads the
  ids from the index and the rows through the reading cache, a few at a time
  so an early stop skips the rest.
- **First opens.** After a restart, a background warm-up decodes (in
  batches of four, half a second apart) the readings the owner's newest idea
  checks and alerts point to and each company's latest reading
  (`sentiment.warm_ids`), then continues with the existing financial
  warm-up. (Round three reorders this list and stops it before the cache
  fills; see below.)
- **Ids-only permission checks** where only ids were used: proposal
  scoping (two places), event-review readability, evaluation input checks
  and the review digest. The company read ran 15 full article reads for
  these (1.1–1.5 s). `answers` and `expectations` also filter by source type
  and keep the full read.
- **Evaluation results**: one query per idea version for event results and
  one for condition results, instead of two per evaluation (80 + 80 on the
  owner's data); each evaluation's rows keep their previous order.
- **Financial recovery** read the raw HTML of every saved 10-K/10-Q (up to
  15 s) to open one. It now hashes them in the database, reads only the
  opened filing in full, and gets the parsed facts from the parsed-filing
  cache (same result as `attach`: the cache stores exactly the `_original_*`
  and `_recovery_*` keys `attach` adds).

`test_proposals.py::test_revoked_source_withholds_proposal_and_blocks_approval`
simulates a revoked source by replacing `service.permitted_documents`; it now
also replaces the ids-only twin, which proposals use. Its assertions are
unchanged. Two `test_sentiment_reliability.py` tests fed a reading to
`sentiment_reuse.find` by faking `rows`; they now fake `_recent_readings`.

Second-round tests (disposable PostgreSQL 16): full suite 3,024 passed,
108 skipped, the same 7 environment failures as before; new
`test_warm_up_list_ends_with_each_companys_latest_reading`. Not yet
measured on the owner's data.

## Third round

Owner's run after the second round: company read mostly 1.6–1.9 s (one
3.4 s), alerts 6.8 s, financial recovery 7.9 s, financial story up to
4.6 s; the owner reported the Financials tab still slow.

- **Financial story saved across restarts.** It was the one Financials
  view not stored in `filing_figures`, so every restart re-parsed the raw
  10-K/10-Q HTML to draw the charts (and the recovery checklist's gap check
  did too, through it). It now uses the same per-account, exact-input store
  (`cached(conn, iid, 'story', build)`); its access check still runs first on
  every read. `financial_story.METHOD` joined the store's version list, so
  every saved figure rebuilds once after this change. The saved-figure tests
  are parametrized over the story too (saved and reused, rebuilt on every
  input change including withdrawn access, one row per kind). Two tests
  that counted every saved row now count rows added by the read under test:
  their setup opens the recovery checklist, which saves the story.
- **Reading cache sized for real data.** Saved readings are several MB each
  on the owner's data, so 128 MB held about 30–40 and the warm-up (up to
  120) evicted its own work. Default now 256 MB, set with
  `THESIS_READING_CACHE_MB`; the warm-up loads the most important first
  (each company's latest reading, then the owner's alerts and idea checks)
  and stops at three quarters full.
- **Idea version history in about 7 queries** instead of 5 per version plus
  2 per version for results: events, event reviews, evidence reviews,
  conditions and evaluations each load for every version at once, ordered
  by version and then by the previous key, and are grouped back.

Not changed: the recovery checklist still parses its own filing set once per
process (in the background; it does not hold the charts). Alerts still check
social permissions once per reading (about 65 ms each).

Third-round tests (disposable PostgreSQL 16): full suite 3,031 passed, 108
skipped, the same 7 environment failures; frontend 264 passed, 1 failed
(the date-dependent `companySnapshot` test noted earlier). Not yet measured
on the owner's data.
