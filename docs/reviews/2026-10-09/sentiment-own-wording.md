# NVIDIA source-wording planning failure — 9 October 2026

The owner reported **Sentiment analysis · Blocked: A sentiment label needs its
own source wording** after **Refresh & analyse** for NVDA. This failure is
separate from the earlier output-limit and unrelated-coverage-link failures.

The immutable loading record `1de28db2-e1ee-4140-ad35-7e8d6abebb20` started its
analysis step at 13:08:01 SGT and failed at 13:08:06. Reconstructing that exact
cutoff reproduced the error before any dispatch. No model call was created
within that step; this NVIDIA analysis attempt incurred no AI charge.

## Cause and correction

The failed sample contained 276 candidates: 140 news, 93 Reddit texts and 43
Hacker News comments. Two HN comments had saved immediate parents but only the
generic `Hacker News comment` title remained among their eligible passages. The
existing conservative ellipsis filter had excluded their whole body passages.
These original comments were not physically empty; their stored text remains
unchanged. Ellipsis markers can be ordinary punctuation, but the existing filter
does not infer which uses are safe. That filter and source-passages policy remain.

`prepare` admitted these title-only comments. The schema builder correctly
requires a comment with parent context to cite its own body, excludes title `p0`,
then found no usable evidence and rejected the whole plan. It was a source
eligibility mismatch, not GPT-5.4 refusing the text or another token-limit failure.

The fix excludes comments with no complete body passage **before request planning**
and counts `no_complete_body_passages` by platform. It also applies to HN comments
without discovery metadata and known Reddit comments without a saved parent.
The same failed pool has one additional title-only Reddit comment; it is counted
under that rule rather than being classified from its generic title.

Corrected pool: **273 eligible originals**, comprising all 140 news, 92 Reddit and
41 HN comments, in 35 bounded batches. Every other eligible original remains.
Genuine news headlines and authored top-level post titles remain eligible without
a body; a comment with a complete body sentence survives other omitted fragments.
Parents are never used as substitutes for missing child wording. Existing schema,
exact-evidence/access/withdrawal checks and historical results remain unchanged.

The current-source preview now has **Excluded before analysis**, with human labels
for each platform/reason. The saved full-coverage view shares those labels. The
original source records remain accessible in Data & sources, and exclusions are
distinct from unrelated, unclear, neutral or unanalysed results. The screenshot's
16-source analysis is the earlier completed reading retained after the new failure;
it is not a completed result from this 276-source attempt.

## Separate paid-run blockers

Read-only preflight for the complete corrected sample requires a maximum new
allowance of **US$11.1198**, against **US$4.489568** currently available under the
original cumulative US$30. This is a conservative reservation for full input/output
bounds, not a claim the run would actually cost that amount. No batch was sent and
no maximum was reserved by this diagnostic.

A later app request for Fabrinet, `d1cb20a2-71e1-4d6a-b0d5-5de167e47b3e`, was
created at 13:42:26 SGT, purpose `thesis-source-sentiment-22`, one original. It is
unresolved, with no known actual charge and its **US$0.246835** maximum retained.
It is separate from the 13:08 NVIDIA planning failure and was not dispatched by
this task. Its unknown response/charge must not be invented, automatically retried,
released or administratively accounted without the original ledger's required
review/explicit owner authorization.

This task made **zero paid model requests** and did not change the US$30 cap.
GPT-5.4/low effort/12,000 total output, prompt v22, batching method4, eight-source
and 48,000-byte bounds, whole-plan preflight and retry rules remain. No live NVIDIA
sentiment completion or general semantic-accuracy claim is made by this fix.

## Verification and installation

Guarded focused backend **81 passed**. New cases cover empty/ellipsis-only HN and
Reddit comments, with/without parent context, legacy HN metadata, headline-only
news, genuine authored post titles and readable sentences beside omitted fragments.
Existing context, whole-source, preview, caching, profile and failure tests pass.
Frontend **71 checks**, candidate build, touched-file formatting and syntax pass.
Existing Starlette deprecation warning remains.

The guarded sentiment browser passed saved/current exclusion explanations,
platform-filter visibility, history/watch/evidence/failure behavior and
320/390/1440px layouts. Desktop/320px dialog screenshots were inspected; these are
authored fixtures, not a newly generated NVIDIA analysis. The body filter's actual
saved-source reconstruction and installed API selection were checked separately.

Idle app-only restart PID17776→65337 left PostgreSQL running. No active loading
or live source/model lease was present. The stopped unresolved Fabrinet request
and its exact hold were preserved; an unresolved charge does not need to be
reconciled to install a non-dispatching fix safely. Backend readiness/session
preceded atomic frontend index replacement, older assets retained, 22 assets served
and byte-verified. Installed index SHA-256
`005cb96b63babdd536a8d348e82367413c250e9c9bd8fc8c66bbbdc0cfa5fe62`;
immediately prior index `5be63c42` was preserved in backup. Other chats installed
presentation changes since the prior phase's `2eb63e79`; their current source tree
was retained and guarded during this candidate installation.

All **114 table fingerprints exact** across installation, schema47, `.env` and
local-pitch mode unchanged. Actual NVDA workspace API shows the three exclusions;
the older saved analysis and original blocked journal remain exact. Budget also
exact across install: **US$24.3479945 confirmed**, **US$1.1624375 reserved** (including
US$0.9156025 previously accounted holds and this new unknown maximum),
**US$4.489568 available**, 419 calls, zero running/one charge-review blocker.
No source/email/Telegram request, automatic retry, watch enrolment, ledger reset,
new allowance, cooldown or forecast-policy change was made by this task.

Preserve the original NVIDIA planning failure, the later independent Fabrinet
unknown charge and harmless guessed component/path diagnostics. The first focused
and browser candidate runs passed; no failing candidate was installed. Backend and
All-source originals were copied before edits; current-preview/shared-label rollback
copies were reconstructed by removing only this scoped patch, alongside the original
index and retained assets. Do not describe these as a new database dump.

Evidence: `.local/live-tests/sentiment-own-wording-20261009/`.
Backup: `.local/backups/sentiment-own-wording-20261009/`.
