# Sentiment redesign phase 2 — 17 October 2026

Prepared on `codex/redesign-phase-2`, from the Haiku transport fix `e3be0da`.
The owner approved continuing phase 2 after that fix, and selected **GPT-5.4
bulk + GPT-5.4 mini quick checks**. These models are already configured; this
phase performs no switch and incurs **US$0 catch-up cost**. No environment,
schema, account preference, watch setting or saved research changed.

## Verification tool

[`phase2_readiness.py`](../../experiments/soclaas_replay/phase2_readiness.py)
reads aggregate watch history and the spending ledger in one consistent,
database-enforced read-only transaction. It never starts processes, collects
sources, sends messages or calls a model. Its output contains no account or
company identities. It is a local operator report, not an app endpoint.

After the phase 1 frontend and backend have actually been installed, use that
confirmed installation timestamp (with timezone) as `--since`:

```sh
.venv/bin/python experiments/soclaas_replay/phase2_readiness.py \
  --since '<confirmed installation timestamp>' --deployment-confirmed
```

Do not use the preparation timestamp as deployment evidence. Without the
deployment flag, the report cannot pass. A completed check under the new repair
policy must also be observed; old baseline checks cannot satisfy this proof.

- The window is the first 48 hours after installation, with two consecutive
  24-hour cost windows. Re-running later does not move the window.
- Failed, stopped and unfinished recorded attempts stay in the completion
  denominator. Results completed after the measurement cutoff count unfinished.
  No attempts means no completion percentage and cannot pass.
- App spending includes all models and purposes. Requests prefixed
  `experiment:` are excluded. Calls are assigned by their start time; unsettled
  calls retain their reserved maximum, rather than being counted as free.
  A late settlement stays a reservation when assessing an earlier cutoff.
- The selected configuration and observed app-call models must match the
  approved GPT pair. Partial observation windows, missing installation proof,
  old-policy-only results and unresolved charges cannot produce full acceptance.
- This reports recorded attempts, not missed schedule slots or continuous
  uptime. It does not replace phase 1's GPT-5.4 AVGO replay or three-day gate.

## Results

Offline report, watch-history, budget, bounded-experiment and transport suites:
**111 passed**, using disposable databases and mocked providers. Tests cover
the exact 97% and US$3 boundaries, unfinished checks, empty/partial windows,
missing deployment evidence, model mismatch, uncertainty and late settlement,
cutoffs, excluding experiment charges, read-only enforcement and identity-free
output. The preceding Haiku-related suites passed 171 tests; totals overlap.

Read-only preparation snapshot at **17 October 2026, 11:56 SGT** confirms the
approved GPT configuration. It records **0 hours / 0 checks** under a confirmed
deployment. Its overall result is **pending**, not successful. The US$0 shown
for the empty cost window does not establish a daily cost target.

| Phase 2 done-when item | Result | Measurement |
| --- | --- | --- |
| 48 hours at ≥97% completion | **Not verified** | 0/48 hours after confirmed installation; 0 checks |
| Switch catch-up below US$1 | **Passed** | No switch; US$0 |
| Daily AI cost ≤US$3 | **Not verified** | 0 complete 24-hour windows |

**Phase 2 is not done.** The models are already in use, but the phase 1
reliability changes need a matching frontend install and backend restart.
At the idle check at 11:56:36 SGT, no lease, AI call, data update, evaluation or
source action was active, but **4 watches were due within 90 seconds**. Restart
was deferred. Re-check idle immediately before any owner Terminal-panel restart;
this report never operates the app. No frontend installation or restart occurred.

Phase 2 itself made **0 paid calls / US$0**. The separately approved Haiku
investigation cost US$0.053381665 with US$0.011598500 additionally held for its
unresolved HTTP 400 attempt. Keep that hold and the failed/interrupted evidence.
The GPT-5.4 AVGO paid replay was not approved and was not run. No phase 3 work
has started. Private evidence: `.local/live-tests/redesign-phase-2-20261017/`.
