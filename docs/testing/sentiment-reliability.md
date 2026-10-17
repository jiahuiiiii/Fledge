# Sentiment redesign phase 1 — 17 October 2026

Implementation is on `codex/redesign-phase-1`, based on `3bbcf01`. **Acceptance
is pending; phase 1 is not marked done and phase 2 has not started.** No model,
provider, watch preference, Telegram preference, historical reading, applied
migration or environment file was changed. No paid test or source fetch ran.

## Implemented behavior

- `sentiment-item-repair-1` repairs consistency mistakes after checking the
  source citations. Tone/basis conflicts become unclear. Inconsistent event
  evidence becomes ineligible with no impact or citations. Misplaced social
  reporting, news price claims and earlier-attitude fields are removed.
- Unknown or duplicate evidence, missing/duplicate labels, invalid structure
  and incomplete JSON/output still fail. Each batch permits at most
  `max(1, floor(item_count / 4))` repaired items; several reasons on one item
  count once. The combined result retains each batch's decisions and provenance.
- Each repaired item records policy, reason codes and the original structured
  label. Reading totals include quick-check skips and reused items. Evidence
  shows the disagreement explanation. Raw responses and historical readings
  remain unchanged.
- Saved responses, including previously failed attempts, are checked again
  before dispatch. Compatible unchanged sources can retain labels from a
  different model; each item keeps its original model and call provenance.
  Prompt, summary, reporting, guard, parent and Reddit-thread policies still
  must match. Changed source or discussion context prevents reuse.
- Manual **Re-read everything · paid AI** uses a durable run identity, bypasses
  saved labels, paid-response caches and the quick filter, and reads saved
  sources without collecting new ones. Repeating that same run is idempotent.
  Later ordinary checks of the identical inputs reuse the explicit re-reading
  instead of returning the older cached reading.
- After one settled invalid retry, **Retry with smaller batches · paid AI**
  permits one split into two smaller requests. Child requests are terminal:
  no recursive split or paid child retry. A cancelled split retains completed
  work and requires explicit continuation before sending an unsent child.
  A stale recovery action cannot start a fresh full-pool or quick-check request
  when its saved inputs no longer match.
- Watches re-check saved answers for free but do not retry paid failures.
  Unsettled full-reading and quick-check requests are not redispatched, even
  though the general ledger supports redispatch. Explicit re-reading is a
  separate action; it does not settle an earlier uncertain charge.

No SQL migration is needed: the existing reading, call and loading-step JSON
fields hold these records. Existing prompt `thesis-source-sentiment-24`, summary
`sentiment-coverage-9`, batch policy and paid request schemas stay unchanged.
New analysis cache keys add the repair policy; paid-response keys stay reusable.

## Offline verification

All Python runs used `LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8` and
`.venv/bin/python -m pytest -q tests/<file>.py`. Tests used disposable databases
and mocked providers. The sandbox could not create the test database socket;
the test-only reruns allowed that socket, without operating the app database.

- Broad related run: **488 passed, 3 optional skips**, covering the new tests
  plus sentiment/basis/batching/history/context/inputs/limits/guards, Reddit
  context, coverage, relevance, loading, watches, events, ledger and Telegram.
- Later cache/provenance/loading/watch/sentiment suites: **150 passed** after
  verifying that regular checks adopt an explicit re-reading. Final recovery
  suites: **68 passed** (`test_sentiment_reliability.py`,
  `test_sentiment_batching.py`, `test_relevance_prefilter.py`,
  `test_parallel_batches.py`), including stale-action and uncertain-charge
  boundaries. These overlap the broad run; totals are not additive.
- Existing frontend suite: **198 passed**. Production build passed into a
  temporary output directory; the installed frontend was not replaced.
- `tests/frontend_sentiment_reliability.mjs`: **8 component behavior groups
  passed**, with layouts at **1440/390/320 px**, no overflow or browser errors,
  escaped source text, correct explicit-action payloads, disabled/active states,
  and withheld repair details. **0 network requests**. Final screenshots were
  inspected. The initial library fixture lacked production environment and
  design-token configuration; corrected fixtures and earlier failures remain
  in private evidence.

The standalone browser test expects Playwright installed or `PLAYWRIGHT_MODULE`
pointing to its entry module, and optionally `CHROMIUM_PATH` for the installed
browser. It starts a temporary browser fixture, never the Fledge server.

## Done-when results

`experiments/soclaas_replay/phase1_offline.py` replays frozen answers through the
production validator, without a database or network. META contains 119 item
instances in 16 batches per model; AVGO contains 64 in 15 Opus batches.

| Corpus / model | Batches passing | Repaired items | Repair rate | Required gate |
| --- | --- | --- | --- | --- |
| META / Opus | 16/16 | 1/119 | 0.84% | Passed |
| META / Sonnet | 16/16 | 0/119 | 0% | Passed |
| META / Haiku | 14/16 | 9/119 | 7.56% | **Failed** |
| META / GPT-5.5 | 16/16 | 0/119 | 0% | Passed |
| META / GPT-5.4 | 16/16 | 0/119 | 0% | Passed |
| AVGO / Opus | 15/15 | 0/64 | 0% | Passed |
| AVGO / Sonnet, Haiku, GPT-5.5, GPT-5.4 | 0/15 replayed for each | Unknown | Unknown | **Not verified: no saved responses** |
| Three days live on GPT-5.4 at ≥97% completion | 0 days observed with this implementation | — | — | **Not verified: not installed** |

Haiku's two failures exceed the per-batch repair limit. Its 9 repaired items
include those in rejected batches; rejected items are not hidden from the rate.
Neither the batch limit nor the 5% acceptance ceiling was relaxed.

The frozen requests preserve exact model-visible passages and parent evidence,
but not all storage metadata or historical price captures. Replay supplies only
neutral validator metadata and leaves absent price captures unknown; it never
borrows current sources. This verifies structural/consistency handling, not
semantic correctness or complete historical packet reconstruction.

**Paid test cost: US$0.** Missing model comparisons require separately scoped
paid testing. No automatic paid retry or fresh collection was used to fill gaps.

## Installation and rollback

Nothing from phase 1 is live yet. The backend needs an idle-window restart from
the owner's Terminal panel and a matching frontend installation. Before restart,
check all watch leases, AI calls, research updates, evaluations and active source
actions, plus no enabled watch due within 90 seconds. Never use the historical
sandbox restart script to operate the app.

`THESIS_SENTIMENT_RELIABILITY=false` disables new item repairs, cross-model reuse
and smaller-batch recovery. It does not rewrite saved repaired readings or permit
automatic paid retries. To roll back a deployed installation, back up `.env`
before changing it and use an idle Terminal-panel restart. This task did not
change the setting or `.env`. Retain the preceding frontend bundle for rollback.

Private evidence: `.local/live-tests/redesign-phase-1-20261017/`. It retains
replay results, test/build logs, initial diagnostics and final browser screenshots.
