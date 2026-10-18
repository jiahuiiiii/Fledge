# Owner tone clarifications — 18 October 2026

The owner answered three follow-up questions after reviewing the failed rubric-2
comparison. These are explicit product/rubric judgments on exposed examples,
not blind test labels or adjudicated objective truth:

1. An adverse short reply is negative when its supplied topic clearly establishes
   the target and question being answered. Context resolves meaning; the reply's
   own wording supplies the attitude. A short reply is not automatically unclear.
2. Explicit happiness about a possible future share-price gain expresses positive
   attitude, without establishing that the gain is likely. Mere price conditions
   and unanswered questions remain separate.
3. Reporting a past share-price gain while asking an open buy/hold question is
   neutral in the reviewed excerpt. The candidate applies this narrowly where
   there is no separate explicit evaluation or stated business benefit/harm.

The answers reaffirm the original reference tones for two owner cases and one
fixed hard case. They are saved separately in private
`.local/live-tests/redesign-phase-5-20261018/rubric-owner-followup-v1/answers.json`.
No original label, hard-case reference, prediction, denominator or score changes.
The record notes that the owner saw answer choices after evaluation; it cannot
be presented as independent blind validation.

## Prepared candidate and checks

Prompt `thesis-source-sentiment-tasks-3` implements these boundaries with eight
fictional teaching snippets. Seven additional authored development cases cover
the three rules and their limits: the same adverse wording without a supplied
target, a future-gain question without an expressed wish, genuine favourable
business results and explicit praise beside an open question. There are now
23 separate development cases; their references/rationales never enter source
payloads. [Current rubric](../../testing/sentiment-tone-rubric.md).

Both earlier smaller-task prompt versions remain explicitly reusable through
the existing reliability bridge, retaining each label's actual original prompt,
model and call. Integration checks cover both versions without dispatching a
reread or changing the historical database result.

| Check | Result |
| --- | --- |
| Owner follow-up recorded | **3/3**, separate from original labels |
| Task instruction bounds | **3/3 pass**: tone 5,796, event 4,350, duplicate 2,497 characters, each ≤6,000 |
| Development input/reference contracts | **23/23** retain supplied text/context and accept authored reference shapes without repair; fabricated citations reject |
| Related offline suites | **192 passed**, including 15 additional checks since candidate 2 |
| Candidate-3 model quality | **Unmeasured**; no model call or paid retry |
| Original owner quality | **Failed: 24/50 (48%)**; original hard cases remain 4/6 |
| Candidate-2 development result | **Failed: 24/50 (48%)**, hard cases 3/6 |
| News-noise gate | **Failed: 2/18 (11.11%)**, unchanged |

The same nine related suites listed in the
[candidate-2 verification](sentiment-rubric-candidate.md) ran with the required
locale and `.venv/bin/python -m pytest -q tests/<file>.py` invocation. All checks
use the disposable database/invented responses, without network. Passing these
checks verifies request/evidence/reuse contracts, not AI interpretation. The
original owner export, blind page, old predictions and protected CSS remain
hash-identical.

Actual incremental cost **US$0**. The completed earlier candidate-2 paid test
remains US$0.47429 with zero unresolved amount; its approval is exhausted.
No new paid evaluation is authorized or performed. No schema, live settings,
saved research/preferences, UI installation, Telegram delivery or real app/DB
restart changes. The legacy live prompt is unchanged. Candidate 3 remains
prepared and off; phase 5 is unfinished and any later release-quality evaluation
still needs a stable rubric and separately held-out owner labels.
