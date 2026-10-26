# Secondary pages and Updates speed — 25 October 2026

## Design unification

**My views**, **Updates** and **World** now share the same page shell:

- The shared `SectionHeader` page header, with an icon. My views previously used a
  hand-written heading and had no icon; it now uses `LightbulbIcon` like the
  other secondary pages use their own icon.
- Content edges and top spacing come from `.workspace-page` only. Removed the
  extra page-level padding from `.world-news` (which was doubling the gutter),
  `.update-inbox` (a leftover base 24px padding), `.ideas-page` and the leftover
  `.collection-page` block padding, which differed by 28px.
- On narrower windows, the mobile **Company** picker bar was shown on My views
  but hidden on Updates and World, making World appear to jump upward by about
  65px. It is now hidden on all collection pages, so the three pages start at the
  same offset.

No data, permissions, routes or paid actions changed.

## Updates load time

Measured through `review_digest.prepare` for the account with the most saved
records (156 records: 146 company alerts and 10 price moves):

| Change | Time |
| --- | --- |
| Before | **16.9 s** |
| After | **2.4 s** |

Causes and fixes:

1. `prepare` loaded every matching record (up to 1,000) a second time just to
   build the main-points summary, even though the page shows 20 records. It now
   builds main points from the visible page. The explicit export still covers the
   full retained window (up to 1,000).
2. `details` called `news_watch.list_alerts` once per company alert. Company
   alerts are now loaded in batches of 100 and mapped back to their events.
3. `daily-updates` itself was already fast (about 0.03 s for this account).

The remaining 2.4 s is mostly the per-alert sentiment/source access checks for
the 20 visible records and per-company coverage. The response is about 109 KB.

## Verification

- `pytest -q tests/test_review_digest.py tests/test_review_export.py`: 19 passed.
- Frontend `npm test`: 214 passed.
- `vite build`: succeeded; deployed to `frontend/dist`.
- The backend change needs the owner to restart the app before it takes effect.
  No restart was performed from the sandbox.
