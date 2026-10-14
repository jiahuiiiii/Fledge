import test from "node:test";
import assert from "node:assert/strict";
import { modelAvailability } from "./modelAvailability.js";
const base = {
  enabled: true,
  budget: { remaining_usd: 12, running: 0, needs_attention: 0, unresolved: 0 },
};
test("a running request queues new work; nothing else blocks", () => {
  assert.equal(
    modelAvailability({
      ...base,
      budget: { ...base.budget, running: 1, unresolved: 1 },
    }).state,
    "running",
  );
  assert.equal(modelAvailability(base).blocked, false);
});
test("off and unknown states are distinct", () => {
  assert.equal(modelAvailability(null).state, "unknown");
  assert.equal(
    modelAvailability({ ...base, enabled: false }).state,
    "disabled",
  );
});

test("spending review, unresolved charges and the allowance never block (owner decision, 13 Oct 2026)", () => {
  for (const budget of [
    { ...base.budget, needs_attention: 1, unresolved: 1 },
    { ...base.budget, remaining_usd: 0 },
    { ...base.budget, remaining_usd: -5 },
  ])
    assert.equal(modelAvailability({ ...base, budget }).blocked, false);
});
