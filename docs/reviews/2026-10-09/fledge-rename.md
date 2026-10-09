# Fledge rename — 9 October 2026

The owner requested renaming the product to **Fledge**. The existing text wordmark now reads **fledge ↗**, with its original visual styling. Normal, loading, empty and sign-in shells, browser title, starter guide, Telegram settings and future message templates use the new name. Newly generated research, answer, review, business, valuation, expectations, discussion-theme and reasoning-check downloads use `fledge-` filenames; branded HTML document titles and headings use Fledge. Current README/documentation headings and the private frontend package name are updated. `Start Fledge.command` is executable; the old launcher remains compatible.

The physical repository/Python package/database names, configuration, request headers, storage keys, model/prompt identities, source user agents and retained source/calculation provenance remain unchanged. This preserves the current installation and historical research. No migration, data rewrite, provider request, AI call, email or Telegram dispatch was part of this task. The existing pitch deck and historical documentation are not rewritten.

## Verification

- Production frontend build passed.
- Existing guarded offline backend suites:215passed/3optional skips for exports, Telegram, reviews, valuation, answers, expectations, themes, alert-quality and source diagnostics; five additional checks passed for business/reasoning exports and provider transport. These use disposable databases and blocked external networking. The existing Starlette/httpx deprecation warning remains.
- Changed Python syntax and executable launcher's shell syntax passed.
- Guarded candidate browser verified the actual saved workspace at1440/390/320px, no horizontal overflow, browser title/wordmark and starter guide. Empty/sign-in/loading shells use authored states. Application writes and external browser requests were blocked. Selected saved research fields stayed exact. Screenshots were inspected.
- The first browser run used an incorrect accessible-name selector for the loading text; its timeout is retained. The corrected run passed. Initial harmless guessed-file searches are retained in the conversation; no failing app build was installed.
- The same browser check passed against the installed app at1440/390/320px, including all four shells and guide copy, with no browser errors or saved-record changes. `git diff --check` passed.

## Installation

Evidence is in `.local/live-tests/fledge-20261009/`; original touched sources and full pre-install frontend are in `.local/backups/fledge-20261009/`. Source hashes/file-set and prior-index checks passed. The idle web process restarted from26956to36923, leaving PostgreSQL running. Backend session readiness preceded atomic frontend replacement;29candidate asset/font files verified, earlier hashed assets retained. Installed index SHA-256 is `ac7c12b409ddbb5c64fa4ed251e24c7bd8bc0f867e9d63de8c9dc862014959e1`.

All114table fingerprints, schema47 and `.env` were exact across the measured installation interval. Existing local-pitch mode and original ledger remain:US$24.3479945confirmed,US$1.1624375reserved,US$4.489568available,419calls,zero running and one unresolved review blocker. The rename did not retry or release that hold. These are installation checks, not new financial-data or independent usability validation.
