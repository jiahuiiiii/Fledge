# Clickable tone filters, reading order and All default — 10 October 2026

The owner asked to make the five tone-count tags filter the analysed sources, move **Read analysed sources** above the other reading disclosures, and default to **All** instead of **Company news**. The saved-analysis path had still initialized to news; it now starts at All, like the pre-analysis view.

The five tone tags are native toggle buttons with `aria-pressed`, a controlled source-list reference, visible selection/focus and 44px minimum targets. Clicking a tone opens the source list on page one and selects company-relevant items with that exact saved label. Clicking it again or **All tones** clears the tone restriction. Source type and tone remain independently combinable. Broader relevance selection clears tone; choosing a tone restores relevant-only selection. No saved labels, dates, source wording, ordering rules, grouped totals or model calculations change. Group totals need not equal matching source counts; the view explains that difference. All has tone filters but no invented pooled news/social counts.

The source list precedes **Sample details & method** in a platform view and **How sources are counted** in All, with discussion themes later. Existing summaries, source settings, coverage and evidence remain available. Filtering is temporary component state. There are no backend, migration, source, paid-request, watch or private-research changes.

## Verification

All112existing frontend checks, production build, touched product-source formatting, changed browser-script syntax and diff checks passed. Two existing browser scripts were adjusted to assert All first and explicitly select news for their news-only assertions; their full authored journeys were not rerun for this change. The focused guarded browser exercised the changed flow against actual saved Qualcomm analysis `a9ca166c-5de7-409b-8ffa-0a9a40d7a938` at1440/980/390/320px: All on first load/reload, all five filters, toggle/clear, source/relevance combinations, pagination reset, zero categories, source order, original evidence, Escape/focus, selected state, control reference and no overflow/page errors. Actual positive items are3in news and5across all source types.

Candidate-only simulations preserve the news3positive-group count when four positive source rows are supplied, and confirm a withheld analysis exposes neither tone filters nor its source list. These authored cases are separate from the actual saved reading. Browser loading writes and all external requests were blocked. Actual analysis, research revisions and watch values remained exact across the browser check. These are developer regression checks, not independent usability or sentiment-accuracy validation.

Evidence `.local/live-tests/tone-filters-20261010/`; backup `.local/backups/tone-filters-20261010/` includes prior product files and served frontend. Preserve `install-initial-import-failure.log`: the first installer invocation used an incorrect package path and exited before connecting or installing; using the repository package path corrected it. No failing candidate was installed.

## Installation

Full183-source hash/file-set and prior-index guards passed. Atomic index `9a962e1ab332c042de5a39768d893aa6ba87c2679a4df8d9edfc52ad6e966622`, all33candidate files and local-pitch session200 were verified. Older assets remain available; appPID28309was not restarted. All114table fingerprints, schema47, environment and original ledger were identical across installation. The separately approved Qualcomm reading and retained FN hold remain unchanged.

The installed browser separately passed the same four-width actual-data journey, recorded in `installed-browser.json`, with no page errors/overflow and unchanged saved reading, revisions and watch. Candidate and installed desktop/phone screenshots were inspected. No model/source request, private-research/watch write, email or Telegram action was performed by this interface change.
