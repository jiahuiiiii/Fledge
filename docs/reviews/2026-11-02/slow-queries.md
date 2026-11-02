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
