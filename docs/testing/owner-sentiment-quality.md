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

At this checkpoint pipeline integration/reuse, ratings, routing, daily digest/
cost alerts and the one-week replay were not implemented. The dated follow-up
below records subsequent preparation; no quality result is implied.

## Pipeline and ratings follow-up — 17 October 2026

The smaller contracts are now connected through an opt-in runner (default off),
with unchanged tone carry-over, separate importance backfill, durable ledger
results, bounded parallel stages and explicit retry/split recovery. Related
integration suites pass164offline tests. New migration061 prepares private
append-only alert ratings and a shared Telegram callback cursor; it is not live.
Updates places the same Useful / Not useful choices beside existing evidence.
[Implementation and limits](../features/sentiment-tasks-and-alert-ratings.md).

Neither switch is enabled. There has been no new-prompt paid evaluation, live
migration, saved-research change or restart. Owner annotations remain0/50, so
neither semantic quality nor phase5acceptance is verified. Subsequent preview
routing is recorded in the linked contract; live routing, daily digest, cost
alerts and the one-week replay remain to implement.

Daily-update follow-up17October: private recap/spending previews and the guarded
Telegram transport are now prepared, still off and unapplied live. Per-attempt
button mappings preserve original-alert ratings after a known rejected send is
re-rendered. [Current daily-update contract](../features/daily-updates.md).
This supplies no new owner annotations or prompt-quality result; actual routing,
independent replay and live gates remain pending.


## Exact evaluation inputs located — 17 October 2026

Read-only historical-packet checks found the exact original passages and matching
review context for all50frozen cases. A private input plan now prepares50separate
GPT-5.4 tone requests, each with one selected source, its required saved context
and no optional siblings. The owner's manifest/review page remains exact; the
plan contains no owner answers or AI predictions and dispatches nothing.

This is input preparation only, not a tested paid evaluation runner or a quality
result. Current access checks, the six fixed hard cases, approval/cost controls
and the actual evaluated answers remain outstanding. Owner annotations0/50
received; paid test costUS$0. Private evidence:
`.local/live-tests/redesign-phase-5-20261017/story-guard-prepared/quality-inputs-summary.json`.


## Bounded evaluation runner prepared — 17 October 2026

[The frozen campaign runner](sentiment-quality-campaign.md) now validates all50
review projections and the6original benchmark cases, with read-only current-access
checks, a combined spending cap, durable folder-independent request identities,
first-failure stop and explicit unattempted-only continuation. It never reads
owner answers or changes the review page. The scorer accepts its fingerprinted
prediction envelope and rejects another sample.99related offline tests pass;
no paid run or real new-prompt quality result exists. Owner labels0/50remain.

## First paid run stopped — 17 October 2026

Three requests costUS$0.02518with zero unresolved holds. Two answers passed;
the third failed the parent-context citation guard and stopped the run. No retry
occurred. A stricter generation schema and explicit revised-continuation guards
pass174related offline tests. The proposed run reuses the first two answers for
free, retests only the failed case and sends53untouched cases, subject to explicit
paid-retry approval and the original combinedUS$2cap. It has not executed.
[Current campaign record](sentiment-quality-campaign.md#paid-stop-and-stricter-schema--17-october-2026).
The review page and frozen evidence remain unchanged; no predictions are shown.
Actual owner annotations are still0/50received, so accuracy remains unmeasured.
