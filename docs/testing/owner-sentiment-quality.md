# Blind owner review for the sentiment redesign

Prepared 17 October 2026 on `codex/redesign-phase-5`. This is the first phase 5
step, not a completed quality result. No prompt, live route or app data changed.

`experiments/soclaas_replay/owner_quality_set.py` exports 50 permitted saved
sources in a database-enforced read-only transaction. The fixed sample balances
company and news/discussion strata, chooses by a deterministic hash and never
uses a model's labels to choose examples. The initial private sample uses META
and AVGO, with 25 news and 25 discussion sources. This is a limited two-company
sample, not proof of general accuracy or market prediction.

The local HTML review page contains source evidence and saved discussion context,
with no model predictions or suggestions. Every relevance and tone choice starts
blank. Answers stay in browser storage until the owner downloads them; no source
or answer is sent over the network. Download requires all 50 answers and an explicit
confirmation that the owner labelled them without AI suggestions. The page uses
one evidence card and puts navigation beside the labels. All scripts and styles
are embedded; it requires no app server, dependency download or account change.

The source manifest is frozen and fingerprinted. Do not overwrite it after review
starts. Model comparison uses that same source text and context. Predictions are
separate files and must not be shown to the reviewer before annotation. The
scorer requires all 50 exact IDs, the manifest fingerprint and valid labels.
Missing answers never reduce the denominator. Its conservative primary check is
at least 40/50 exact relevance-and-tone matches (80%); it also reports separate
counts. The six hard cases still need their own check at 4/6 or better.

The owner must provide the actual annotations. Developer fixtures, labels filled
by browser tests and AI-generated labels cannot satisfy this gate.

Verification: 41 related offline tests pass (6 new), including read-only export,
fixed selection, blind projection, fingerprint/complete-label guards, exact80%
boundary and HTML escaping. Seven isolated authored browser groups pass at
1440/390/320 with zero HTTP requests: empty choices, disclosure controls, navigation,
local save/reload, completion/confirmation gates, download and layout. Test answers
are invented fixtures in a separate temporary browser and are not owner labels.

Private review: `.local/live-tests/redesign-phase-5-20261017/owner-quality-50/review.html`.
The raw sources, answers and identifiers stay outside Git. Cost: US$0; zero AI calls.
**Not verified:** owner labels (0/50 received), prompt quality and phase 5 acceptance.

## Smaller-task contracts prepared — 17 October 2026

`thesis/research/sentiment_tasks.py` is request construction and validation only;
it has no dispatch function and is not connected to the live pipeline. Tone,
news-event/importance and candidate-only duplicate instructions are3924,3379
and2497characters, all below6000. Shared schemas are1921,1537and924characters
in this version, avoiding per-item schema copies. Each request retains the
selected bulk model, existing finite ledger profile and48kB bound.

Code forces opinions, comparisons, analyst/market commentary, price recaps and
non-events low even when the model proposes high. High/medium require own-source
evidence. Unknown/duplicate labels and fabricated citations fail validation.
Duplicate calls cannot be constructed without bounded earlier headline candidates;
the existing citation, number/status and temporal guards still validate results.
New contract tests and related tone/reporting/coverage/batching suites:106pass.
These authored tests do not establish semantic quality or measured cost savings.

Still unimplemented here: pipeline integration/reuse across task versions,
rating/routing storage and UI, daily digest/cost alerts and the one-week replay.
No new migration or live setting accompanies this preparation.
