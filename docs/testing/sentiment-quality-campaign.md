# Frozen sentiment quality campaign

Prepared 17 October 2026 on `codex/redesign-phase-5`. **First paid run stopped;
revised test awaits explicit approval. Not installed or enabled.** This operator tool prepares the remaining phase5quality evidence;
it supplies no owner labels or completed acceptance gate.

## Fixed inputs

`experiments/soclaas_replay/sentiment_quality_validation.py` validates a frozen
56-case plan: the exact50-source blind owner sample and the same six proofread
META cases from the model comparison. The owner's review manifest/page and browser
answers are unchanged. Predictions remain separate and are never put into the
review page. The runner never reads owner answers.

Each request has one selected source and its required saved context, without
optional sibling messages. Export and evaluation share `case_evidence`, so the
company, original passages, source metadata and review-context projection must
match. The original six benchmark batch/item references and source/required
parent/topic evidence remain attached; expected tones are not retuned after
seeing results. These six expectations remain the earlier developer's reading,
not an owner-labelled or universal benchmark.

The plan binds source/validator packets, production task bodies, model, benchmark
provenance and owner fingerprint. Changing its input or the production prompt
contract invalidates the plan. The selected GPT-5.4 bulk snapshot remains; there
is no provider switch or process-only pricing override. The live smaller-task
switch remains off. This test measures the new bulk tone/evidence task, including
relevance; it does not claim end-to-end quick-filter or importance accuracy.

## Execution, access and cost

Without `--execute`, the command only validates/estimates the frozen plan; it
makes no AI call or app-research write. Execution requires an explicit matching
`--approved-plan`, a new output folder and an explicit combined cap no greater
thanUS$2. The owner’s full-plan/testing instruction covers this bounded selected-
GPT evaluation; expected cost is disclosed before execution. The input-binding
flag does not authorize a new model/provider, a larger budget, or live default
changes. This tool is not called by the app or an automation.

All56cases are checked for current source/context permissions in a database-
enforced read-only transaction before any paid call. The consumed target and
required context are checked again immediately before each request. Optional
unconsumed siblings do not create unrelated access dependencies. No source is
refetched, and no account watch/Telegram setting or saved research changes.

Calls go through the existing spending ledger with experiment identities based
on request-body hashes, independent of output folder. One cross-process campaign
lock prevents concurrent operator runs. A previously attempted request cannot
be silently retried under another folder or a ledger redispatch suffix. The first
transport/output/validation failure stops the run. Raw paid answers, confirmed
charges and unresolved maximums stay retained. No automatic paid retry exists.

The cap includes all earlier confirmed charges and unresolved reservations for
the campaign's request identities. Before each new request, its conservative
ledger maximum must fit the remainder. Confirmed cost is recorded before response-
file or validator work. Current preparation has56distinct requests, a largest
individual reservation ofUS$0.2346575, and a summed independent worst-case
reservation ofUS$12.294325. That sum is **not** an approved spend: sequential
execution with the proposedUS$2combined cap stops before exceedingUS$2, even if
not all56cases can finish. The initial run below stopped before completion.

An explicitly approved continuation must retain the same frozen plan. It checks
settled answers for free and sends only never-attempted requests. An unresolved
attempt stops continuation, and an invalid saved answer stops before new work.
A new folder or changed cap cannot erase earlier spending. The combined cap still
applies across the original run and continuation.

## Scoring handoff

Predictions use the rendered/repaired labels rather than an inconsistent raw
provider label; repairs are counted and original answers are unchanged. A complete
owner prediction file has all50IDs and the review fingerprint. The existing
owner scorer accepts this envelope and rejects another sample's fingerprint.
It still requires all50owner-confirmed answers and40exact relevance-and-tone
matches (80%). Missing labels never reduce the denominator.

The separate six-case gate requires at least4/6correct tones, with exact boundary
tests. Finishing56structurally valid requests does not imply either semantic gate
passed. A failed hard-case score cannot be replaced by agreement with another AI.
The owner quality result waits for actual downloaded owner answers.

## Verification and current state

Final related offline suites:99pass, including20new runner cases and the scorer's
new fingerprint-envelope case. Tests cover first-failure stop, folder-independent
identities, locks, combined-cap continuation, unsettled attempts, before-payment
access checks, free saved-answer recovery, repaired-label provenance and exact
4/6boundary. All provider responses and labels in these tests are authored mocks;
they do not count toward the real quality gates. Full offline backend:2,571pass
with93optional skips before the subsequent schema revision below.

The private real-input plan preserves50/50original review projections and6/6fixed
benchmark source/context projections. All56current permission checks pass in
read-only preflight. At that preparation checkpoint no source/AI request, live migration, environment/preference
change, installation or app/DB restart was performed. User CSS remains exact.
Private artifacts are under
`.local/live-tests/redesign-phase-5-20261017/quality-campaign-prepared/`.

A separate saved-news inventory found records on all seven Singapore dates
10–16October:1,218versions, with2/3/4/5/5/5/5companies represented per day.
This is coverage inventory, not1218independent stories or a routing/noise result.
The replay must remove repeated versions, retain availability ordering, declare
its fixed retrospective portfolio and incomplete provider coverage, and assess
noise independently. No seven-day replay has passed yet.

Phase5remains unfinished: owner labels0/50, new-prompt real hard cases0/6,
independent noise replay0/7, real evaluation results, and live/shadow/outcome
gates remain. No phase is marked done.

## Paid stop and stricter schema — 17 October 2026

The first run settled three requests for US$0.02518, with zero unresolved holds.
The first two answers passed; the third supplied a parent-context passage even
though the source had no parent. The runtime evidence validator rejected it and
stopped the run. No paid request was retried and the remaining53cases, including
all six hard cases, were not attempted. This is2/56validated answers, not a
semantic-quality result; owner labels remain0/50received.

The shared generation schema now restricts source/passage IDs to supplied
evidence, requires an empty parent-context field when no parent exists, and
forbids news-only previous/price-claim fields. Runtime citation guards remain
strict, including per-source checks in mixed batches. The schema policy is part
of reading identity; raw responses and existing research are unchanged.

A separately frozen revision preserves all source text, context, expectations,
model and instructions. It can reuse the two valid answers for free, explicitly
retest only the failed third case, and send53never-attempted cases. All earlier
confirmed charges and unresolved maximums remain within the combinedUS$2cap.
The revised plan's largest individual reservation isUS$0.2362025; its independent
maxima sum isUS$12.3051225and does not authorize that spending. Expected additional
cost isUS$0.40–1.20. **The revised paid run has not executed: the owner's
no-automatic-paid-retry rule requires explicit approval of the failed-case retest.**

Free rechecking confirms56/56current access checks, both valid answers fit the
stricter schema, and the failed answer remains rejected. Final174related offline
tests pass, covering schema constraints, unchanged inputs/expectations, named
failed-case authorization, free reuse and inclusion of original charges in the
revised cap. Full2571pass/93optional skips above predates this schema revision.
No live migration, environment/preference change, installation or restart;
user CSS remains exact. Noise replay remains0/7; inventory/input freezing does
not count as a replay.
