import test from "node:test";
import assert from "node:assert/strict";
import { modelAvailability } from "./modelAvailability.js";
const base = {
  enabled: true,
  budget: { remaining_usd: 12, running: 0, needs_attention: 0, unresolved: 0 },
};
test("running is not unresolved billing; actual billing uncertainty needs attention", () => {
  assert.equal(
    modelAvailability({
      ...base,
      budget: { ...base.budget, running: 1, unresolved: 1 },
    }).state,
    "running",
  );
  assert.equal(
    modelAvailability({
      ...base,
      budget: { ...base.budget, needs_attention: 1, unresolved: 1 },
    }).state,
    "attention",
  );
  assert.equal(modelAvailability(base).blocked, false);
});
test("off, disconnected and exhausted states are distinct", () => {
  assert.equal(modelAvailability(null).state, "unknown");
  assert.equal(
    modelAvailability({ ...base, enabled: false }).state,
    "disabled",
  );
  assert.equal(
    modelAvailability({ ...base, budget: { ...base.budget, remaining_usd: 0 } })
      .state,
    "budget",
  );
});

test("review blockers stay enforced while billing detail is separate from action guidance", () => {
  const status = modelAvailability({
    ...base,
    budget: { ...base.budget, needs_attention: 1 },
  });
  assert.equal(status.blocked, true);
  assert.match(status.message, /New AI analysis is paused/);
  assert.doesNotMatch(status.message, /charge|paid|automatic confirmation/);
  assert.match(status.detail, /without a confirmed charge/);
});
