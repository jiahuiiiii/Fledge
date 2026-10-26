# Saved filing figures — design for approval (would be migration 072)

Status: approved by the owner on 25 October 2026 and built as migration 072.

**Change from the approved design:** saved rows are per account as well as
per company (`owner_id`, row-level security like the recovery tables).
`apply_reviewed` folds in AI-assisted figures reviewed by an account, and
those reviews are private, so one company's figures can differ between
accounts. A per-company row could have shown one account's reviewed figures
to another. The basis also covers every saved disclosure document of the
company (any form), and figures read without an account are never saved.

## Problem

`financial_depth.present()` rebuilds a company's trailing figures from saved
SEC data on every request. Each call:

- hashes every saved original filing inside the database
  (`encode(sha256(raw_html),'hex')`), several MB per document;
- reloads every amendment's full HTML (`SELECT … raw_html … form IN
  ('10-K/A','10-Q/A')`), seen at up to 3.6 s per query on 25 Oct;
- re-parses the filings unless the in-memory overlay cache already holds them;
- applies reviewed recoveries and normalises the result.

Measured on the owner's data (15 companies): 20.7 s of work cold, 3.5–4.4 s
warm. The startup warm-up (built 25 Oct) hides the cold cost after about
25 s, but every restart repeats it, and the warm cost still includes the
hashing and amendment reads.

## Proposal

One additive table holding the finished result per company and per exact
set of inputs:

```sql
CREATE TABLE filing_figures(
  instrument_id uuid NOT NULL REFERENCES instruments(id),
  basis text NOT NULL,            -- sha256 of every input listed below
  depth jsonb NOT NULL,           -- the complete financial_depth.present() result
  computed_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY(instrument_id, basis)
);
-- Append-only, like other derived records.
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON filing_figures
  FOR EACH ROW EXECUTE FUNCTION immutable_record();
```

### The basis (when a saved result may be reused)

The basis is computed from cheap, already-indexed facts, never from the
filing bytes themselves:

1. the current SEC payload id and `checked_at`, and the company CIK;
2. source access for `sec-companyfacts` and `sec-disclosures`;
3. for each original filing used: id, url, form, `content_hash`;
4. for each amendment used: id, accession, `content_hash`;
5. the newest reviewed-recovery record that `apply_reviewed` reads for the
   company (id and time);
6. code versions: the extraction `METHOD`, the amendment resolver and the
   depth normaliser (a constant bumped whenever their logic changes).

If any of these change, the basis changes and the figures are rebuilt and
saved as a new row; old rows are never reused for a new basis. A saved row is
used only when its basis matches exactly.

`content_hash` is the hash recorded when each document was saved. The
current code also re-hashes the stored bytes on every call to detect damaged
or changed originals. To keep that protection without paying for it on every
page view, the bytes are verified once when a row is first saved; a changed
document always arrives as a new saved version with a new `content_hash`,
which changes the basis.

### When figures are built

- On demand: if no row matches, the first reader builds and saves it (same
  cost as today, once per change instead of once per restart).
- After the steps that change inputs (filing refresh, disclosure refresh,
  amendment resolution, recovery review), the figures are rebuilt in the
  background so readers rarely meet the cold path.

### What reads it

`financial_depth.present()` itself checks for a matching row first, so the
home cards, the Financials tab and the workspace all benefit without
separate code paths.

## Expected effect

Reading a saved row is one indexed lookup: a few milliseconds per company.
The 15 home cards' figures would cost well under a second in total, with or
without a restart. The basis lookup itself needs a handful of small indexed
queries per company; it no longer hashes or reloads MBs of filing HTML.

## Risks and how they are handled

- **Showing out-of-date figures.** Every input that can change the result is
  in the basis; unknown inputs fail towards rebuilding. Tests would change
  each input in turn and confirm a rebuild (the same style as the existing
  overlay-cache tests in `test_workspace_loading.py`).
- **Access changes.** Source access is in the basis, and the presenters still
  apply the current access rules on read.
- **Storage.** Results are about 10–40 KB per company; one row per change.
- **Migration risk.** Additive only; applies automatically at the next
  deliberate restart.

## Not included

Caching other heavy workspace parts (documents, income flow, segments).
Those belong to proposal 3 (staged company page).
