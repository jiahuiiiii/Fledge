# Forecast evidence dialog spacing and dates — 12 October 2026

The owner reported the analyst revenue forecast dialog and confirmed both the
cramped layout and apparent 2 October date were concerns. The shared dialog
frame sets padding to zero and expects a content wrapper to provide its own.
This wrapper had none. Its width rule also lost to the later shared modal rule,
leaving long metadata unnecessarily cramped against the frame.

The forecast dialog now uses a scoped 720px desktop width, padded content,
consistent spacing and smaller source/period text. At 600px and below it uses
16px viewport margins in total and 16px body padding, with metadata stacked.
The existing sticky header, scroll containment, original-source links, native
focus trap, Escape and focus return remain in place. Bottom padding keeps the
original-source link comfortably reachable after scrolling.

## Date verification

The exact saved Broadcom page was retrieved on 12 October at 08:00:16 SGT
(00:00:16 UTC). Its immutable source record is
`72f72236-e6a1-4350-98ec-41782f605f1c`, page hash
`58c7439fb63c214049b210d27d669018a8c39f282708e105c0ae394b73440e59`.
The visible original footer explicitly says “Last updated: Oct 2, 2026” after
its data-source attribution. The parser's 2 October value is correct. The
original also gives a 2 October publisher check date; this is distinct from the
app's retrieval. There is no new provider date to substitute.

The dialog now labels these separately as Publisher page updated and Page
checked & saved, with a short explanation when the publisher date predates the
saved-page check. Management shows Release date, while FMP preserves its
unknown forecast date and independently known latest check. Individual analysts'
forecast dates remain unknown. Known internal revenue-convention labels display
as Not specified by the source; GAAP and other original conventions retain their
meaning. No amount, range, currency assumption, source date, contributor count,
forecast vintage or saved record is changed.

The existing per-company 24-hour public-page interval remains in force. The
source had just been checked by normal app activity; this task made no repeat
provider request, AI call, retry, watch change or database write. An older
publisher date can remain in a newly retrieved page.

## Verification

158 frontend tests and production build pass, with scoped formatting, script
syntax and diff checks. Browser verification covers actual saved Broadcom
analyst and management dialogs at 1440/980/390/320, exact US$105.97bn average and
105.8–106.7bn range, explicit currency assumption, both dates, contributor
qualification, original links, padding, contained scrolling, sticky close,
Tab/Shift-Tab, Escape and return focus. Authored FMP, missing publisher date and
later failed-check cases exercise the distinct metadata and retained readings.
Writes and external requests are blocked during browser verification.

The first candidate passed all eight actual-source viewport/dialog cases, then
its FMP control incorrectly assumed every source had an original URL. FMP's
response does not provide one. The corrected harness checks the single-control
focus loop for that case without inventing a source link. Preserve this first
failure and the initial guessed stylesheet/component paths and sandbox process
inspection diagnostic. Candidate screenshots have been inspected.

The candidate passes all 11 browser cases. The frontend was installed
atomically with index `c6a4cf0c` and all 30 candidate files verified through the
running app. Older hashed assets were retained. PID 29025 remained unchanged;
no app or PostgreSQL restart. All 116 table fingerprints, schema 49, the entire
AI ledger and private settings remained exact across installation. The existing
news-freshness frontend remains included. The installed browser also passes all 11 cases with no page errors or
horizontal overflow; installed desktop and phone screenshots were inspected.

Evidence: `.local/live-tests/forecast-dialog-20261012/`; previous frontend
source and index: `.local/backups/forecast-dialog-20261012/`. The news-freshness
work and unrelated login/onboarding patch are preserved in the shared workspace.
