# Partial withholding after a source withdrawal — 20 October 2026

## Problem

A withdrawn Reddit thread (`t3_1x77u1k`, r/investing, recorded 19 October 11:20
SGT) hid the whole saved NVDA readings that held its ~12 comments, and every
Updates alert built on those readings showed only "Source access changed", even
when the alert cited unrelated news. Cause: `sentiment.present()` withheld the
whole reading if any source was unavailable, and `news_watch.list_alerts()`
withheld an alert if either of its readings was withheld.

## Rule now

Presentation only. Stored readings and alerts are unchanged; no schema change.

- **Reading** (`present(conn, record, partial=True)`): leaves out unavailable
  sources, every item whose own or cited text (citations, earlier citations,
  reporting basis, Reddit thread context, parent context) depends on one, any
  comment read with a thread that has a withdrawn message, and coverage links
  touching any of those. Saved tone totals that counted a withheld selected
  source (news, social, or a social platform) are removed rather than shown as
  complete. A link removal also withholds the news total, because it grouped
  reports. The response gives `withheld_sources` and `withheld_summaries`
  (sample → withheld selected-source count). A price-history permission failure
  still withholds the whole reading.
- **Alert**: stays visible when the current reading still shows all its items
  and links. Linked-report claims are withheld whole if a link is no longer
  shown. A tone shift is kept only if its items and both saved before/after
  totals are still shown. Other affected items are dropped, and
  `payload.withheld_items` counts them. An alert with nothing left is withheld.
- **Exports and Telegram**: the Updates export renders the same filtered
  payload with a count note. Telegram immediate messages and daily recaps do
  not forward an alert with any withheld evidence, because its saved routing
  decision used evidence that is no longer available.
- **UI**: the sentiment panel says how many sources are withheld and labels
  withheld tone totals. Coverage counts withheld sources separately rather than
  as unanalysed. Alert cards show the withheld-evidence count. New discussion
  summaries and idea checks stay unavailable on a partial reading (those
  backends still require the whole sample) and the panel says to refresh.

## Still whole-reading (default `partial=False`)

These keep the earlier strict rule. Adapting them is a separate change:
discussion themes, saved-idea alert checks, sentiment history list/compare,
watch-check history counts, the saved-baseline check in `sentiment_inputs`, and
generation-side gating. The portfolio news read uses the company's latest
reading, so it now shows the remaining news. `news_watch.publish` still
refuses a current reading with an unavailable source, and it drops a withheld
baseline, so the next check sets a new baseline without alerts.

## Evidence

Offline synthetic fixtures with a disposable test database. No provider calls,
live-database reads, setting changes or app restart. The running app on port
8841 keeps the old rule until the owner's next deliberate restart. The NVDA
result was not checked against the live workspace.

- New `tests/test_partial_withdrawal.py` (5 tests) covers:
  - a reading with a withdrawn Reddit post keeps its news items and news total;
    the record is unchanged and the withdrawn text is absent;
  - a published news alert stays visible and exports without the Reddit text;
  - an alert citing the withdrawn source is withheld in Updates, the export and
    Telegram rendering;
  - a partly affected sentiment-shift alert and reporting alert keep only their
    news parts, with counts, and are not forwarded to Telegram;
  - a no-longer-shown coverage link withholds the linked claim.
- Eight existing tests that asserted whole withholding were updated to the new
  rule. Each still checks that the strict default withholds the stored reading
  and that no withdrawn social text is shown: `test_sentiment.py` (2),
  `test_alert_payload.py` (2), `test_deus_social.py`, `test_conversation.py` and
  `test_hackernews.py` (2). Two `present` test stubs accept the new keyword.
- Frontend: `sourceCoverage.test.js` adds the withheld-totals and note case;
  208/208 library tests pass. A Vite build to a scratch directory succeeds.
- Full Python suite before the last test updates: 2832 passed, 107 skipped and
  6 failed. Five failures were the old-rule tests and stubs above, now 70/70
  across those files. The sixth,
  `test_question_library.py::test_bundled_font_and_license_are_served_without_private_file_access`,
  needs a built `frontend/dist/fonts`. That directory is absent from this
  worktree, so the failure is unrelated to this change.
