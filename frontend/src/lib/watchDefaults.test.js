import test from "node:test";
import assert from "node:assert/strict";
import { withDefaultWindows, needsThreshold, suggestThreshold } from "./watchDefaults.js";

const today = new Date("2026-10-25T10:00:00Z");

test("events without dates get the default window; dated events are untouched", () => {
  const { form, applied } = withDefaultWindows(
    { events: [{ window_start: "", deadline: "" }, { window_start: "2026-01-01", deadline: "2026-02-01" }] },
    today,
  );
  assert.deepEqual(applied, { window_start: "2026-10-18", deadline: "2027-01-23" });
  assert.equal(form.events[0].window_start, "2026-10-18");
  assert.equal(form.events[1].window_start, "2026-01-01");
});

test("no event needing dates means nothing is applied", () => {
  assert.equal(withDefaultWindows({ events: [] }, today).applied, null);
});

test("a blank threshold needs the user", () => {
  assert.equal(needsThreshold({ conditions: [{ value: "" }] }), true);
  assert.equal(needsThreshold({ conditions: [{ value: "15" }] }), false);
});

test("the suggested threshold starts just below the latest reported figure", () => {
  assert.equal(suggestThreshold(14.2), "10");
  assert.equal(suggestThreshold(25), "20");
  assert.equal(suggestThreshold("31.9"), "30");
  assert.equal(suggestThreshold(-3), "-5");
  assert.equal(suggestThreshold(null), null);
  assert.equal(suggestThreshold("n/a"), null);
});
