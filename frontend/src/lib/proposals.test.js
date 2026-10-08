import test from "node:test";
import assert from "node:assert/strict";
import { combineSuggestions } from "./proposals.js";
const base = {
  expected_revision: 1,
  question: "Question",
  reasoning: "Reasoning",
  conditions: [],
  events: [],
};
const common = {
  status: "pending",
  base_version_id: "v1",
  instrument_id: "one",
  snapshot_id: 1,
  base,
};
test("merges selected changes once without replacing other fields or mutating base", () => {
  const first = {
    ...common,
    id: "a",
    kind: "reasoning",
    candidate: {
      ...base,
      reasoning: "Suggested belief",
      question: "Suggested question",
    },
  };
  const event = { condition_id: "stable", description: "Completed event" };
  const second = {
    ...common,
    id: "b",
    kind: "event",
    operation: "add",
    candidate: { ...base, events: [event] },
  };
  const merged = combineSuggestions([first, second]);
  assert.equal(merged.reasoning, "Suggested belief");
  assert.deepEqual(merged.events, [event]);
  assert.deepEqual(base.events, []);
  assert.throws(() =>
    combineSuggestions([first, { ...second, status: "stale" }]),
  );
  assert.throws(() =>
    combineSuggestions([first, { ...first, id: "different" }]),
  );
  assert.throws(() =>
    combineSuggestions([first, { ...second, instrument_id: "other" }]),
  );
});

test("numeric risk update and addition preserve roles and untouched rules", () => {
  const existing = {
    condition_id: "risk-1",
    role: "risk",
    metric: "revenue_growth",
    operator: "<=",
    threshold: "15",
  };
  const kept = {
    condition_id: "required-1",
    role: "required",
    metric: "operating_margin",
    operator: ">=",
    threshold: "20",
  };
  const current = { ...base, conditions: [existing, kept] };
  const updated = { ...existing, threshold: "12" };
  const added = {
    condition_id: "risk-2",
    role: "risk",
    metric: "operating_margin",
    operator: "<=",
    threshold: null,
  };
  const first = {
    ...common,
    base: current,
    id: "change-risk",
    kind: "numeric",
    operation: "update",
    target_condition_id: "risk-1",
    candidate: { ...current, conditions: [updated, kept] },
  };
  const second = {
    ...common,
    base: current,
    id: "add-risk",
    kind: "numeric",
    operation: "add",
    target_condition_id: null,
    candidate: { ...current, conditions: [existing, kept, added] },
  };
  assert.deepEqual(combineSuggestions([first, second]).conditions, [
    updated,
    kept,
    added,
  ]);
  assert.deepEqual(current.conditions, [existing, kept]);
});
