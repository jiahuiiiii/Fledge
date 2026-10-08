# Repeatable alert-continuity replay

The phase60 helper loads retained Apple/Alphabet public-source records and completed model responses into a disposable database, then runs the production watch/publication/review services. Original source wording and labels stay unchanged. Partial-arrival sets, gaps, forced-due scheduling, errors and saved reasoning are authored; this is not a historical reconstruction or a prospective watch trial.

Set `THESIS_WATCH_REPLAY_CORPUS` to `.local/live-tests/watch-continuity-20261004T004158Z/`. For the actual private-question response replay, set `THESIS_WATCH_PRIVATE_RESPONSE` to that folder's `private-replay.json`. These artifacts remain local and are not committed. Without a configured corpus, the optional tests skip rather than fetch data. Without the private response, its relation is explicitly mocked.

Run `.venv/bin/python -m pytest -q tests/test_retained_watch_continuity.py` for company repeat/gap/failure/stop/recovery, exact review history, owner/source access and separate private-baseline recovery. Run `.venv/bin/python tests/run_browser.py --watch-continuity` with the same corpus for the phone/desktop inbox, source dialog, independent acknowledgement and export.

The helper enforces disposable data-directory naming and never installs sources into the main database. Provider transports replay saved responses; the browser blocks external and analysis/refresh requests. Reading the actual-source corpus is distinct from fetching new source data. A separate explicitly metered live evaluation supplied the retained private answer; ordinary tests do not repeat it.

[Evidence, costs, limitations and five-perspective review](../reviews/2026-10-04/watch-continuity-phase-review.md).
