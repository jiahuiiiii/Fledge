import test from "node:test";
import assert from "node:assert/strict";
import { reportExpectationPayload } from "./reportExpectation.js";
import { revisionPayload } from "./kestrelDiff.js";

test("optional expectations preserve an unchanged legacy payload", () => {
  assert.deepEqual(reportExpectationPayload({}), {});
  assert.deepEqual(
    reportExpectationPayload({
      expected_period_end: "",
      expected_report_by: "",
    }),
    {},
  );
});
test("both dates are required and must be ordered real days", () => {
  for (const [end, due] of [
    ["2026-09-30", ""],
    ["", "2026-10-31"],
    ["2026-02-30", "2026-10-31"],
    ["2026-10-31", "2026-10-30"],
    ["2026-09-30", "2037-10-31"],
    ["9999-12-31", "9999-12-31"],
  ])
    assert.throws(() =>
      reportExpectationPayload({
        expected_period_end: end,
        expected_report_by: due,
      }),
    );
});
test("full revision keeps expected dates through approval and clearing", () => {
  const c = {
    id: "chosen-condition",
    metric: "revenue_growth",
    value: "15",
    operator: ">=",
    expected_period_end: "2024-02-29",
    expected_report_by: "2024-03-31",
  };
  const form = {
    revision: 2,
    question: "Can growth hold?",
    reasoning: "Authored test",
    conditions: [c],
  };
  const saved = revisionPayload(form, "monitoring");
  assert.equal(saved.conditions[0].expected_period_end, "2024-02-29");
  assert.equal(saved.conditions[0].expected_report_by, "2024-03-31");
  assert.equal(saved.expected_revision, 2);
  c.expected_period_end = "";
  c.expected_report_by = "";
  assert.ok(
    !(
      "expected_period_end" in revisionPayload(form, "monitoring").conditions[0]
    ),
  );
});
