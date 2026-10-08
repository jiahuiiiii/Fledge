import test from "node:test";
import assert from "node:assert/strict";
import { revisionPayload } from "./kestrelDiff.js";
test("editing preserves identity, expected revision and explicit numeric scope", () => {
  const body = revisionPayload(
    {
      revision: 3,
      question: " Q ",
      reasoning: " R ",
      conditions: [
        {
          id: "same-id",
          metric: "revenue_growth",
          operator: ">=",
          value: "15.25",
        },
      ],
    },
    "monitoring",
  );
  assert.equal(body.expected_revision, 3);
  assert.equal(body.conditions[0].condition_id, "same-id");
  assert.equal(body.conditions[0].threshold, "15.25");
  assert.equal(body.conditions[0].basis, "reported");
  assert.equal(body.conditions[0].period_type, "quarter");
  const annual = revisionPayload(
    {
      revision: 1,
      question: "Q",
      reasoning: "R",
      conditions: [
        {
          id: "stable",
          metric: "revenue_growth",
          operator: ">=",
          value: "15",
          period_type: "annual",
        },
      ],
    },
    "monitoring",
  );
  assert.equal(annual.conditions[0].period_type, "annual");
  assert.equal(annual.conditions[0].max_report_age_days, null);
});
test("age limits preserve blank versus explicit days and reject invalid values", () => {
  const form = {
    revision: 1,
    question: "Q",
    reasoning: "R",
    conditions: [
      {
        id: "stable",
        metric: "revenue_growth",
        operator: ">=",
        value: "15",
        max_report_age_days: "120",
      },
    ],
  };
  assert.equal(
    revisionPayload(form, "monitoring").conditions[0].max_report_age_days,
    120,
  );
  for (const invalid of ["0", "-1", "3651", "1.5", "x"]) {
    form.conditions[0].max_report_age_days = invalid;
    assert.throws(() => revisionPayload(form, "draft"));
  }
  form.conditions[0].max_report_age_days = " ";
  assert.equal(
    revisionPayload(form, "draft").conditions[0].max_report_age_days,
    null,
  );
});
test("draft can omit conditions; incomplete numeric rows cannot silently disappear", () => {
  assert.equal(
    revisionPayload(
      { revision: 0, question: "Q", reasoning: "", conditions: [] },
      "draft",
    ).conditions.length,
    0,
  );
  for (const value of ["", null, "Infinity", "  "])
    assert.throws(() =>
      revisionPayload(
        { revision: 0, question: "Q", reasoning: "", conditions: [{ value }] },
        "draft",
      ),
    );
});
test("event-only revision preserves definitions and rejects incomplete windows", () => {
  const event = {
    condition_id: "stable-event",
    description: "Product launch",
    evidence_requirement: "Report confirms general availability",
    role: "risk",
    window_start: "2026-10-01",
    deadline: "2026-10-31",
  };
  const form = {
    revision: 2,
    question: "Question",
    reasoning: "Reasoning",
    conditions: [],
    events: [event],
  };
  assert.deepEqual(revisionPayload(form, "monitoring").events, [event]);
  for (const change of [
    { deadline: "" },
    { window_start: "2026-11-01" },
    { description: "  " },
    { evidence_requirement: "" },
  ])
    assert.throws(() =>
      revisionPayload({ ...form, events: [{ ...event, ...change }] }, "draft"),
    );
});

test("numerical purpose preserves thresholds and defaults old definitions to required", () => {
  const form = {
    revision: 1,
    question: "Q",
    reasoning: "R",
    conditions: [
      {
        id: "stable",
        metric: "revenue_growth",
        operator: "<=",
        value: "15",
        role: "risk",
      },
    ],
  };
  assert.deepEqual(revisionPayload(form, "monitoring").conditions[0], {
    condition_id: "stable",
    metric: "revenue_growth",
    role: "risk",
    operator: "<=",
    threshold: "15",
    unit: "percent",
    basis: "reported",
    period_type: "quarter",
    max_report_age_days: null,
  });
  delete form.conditions[0].role;
  assert.equal(revisionPayload(form, "draft").conditions[0].role, "required");
});

test("event date meaning survives edits and approval payloads", () => {
  const event = {
    condition_id: "dated-event",
    description: "A completed launch",
    evidence_requirement: "A source explicitly dates the completed launch.",
    role: "required",
    date_basis: "event_occurrence",
    window_start: "2026-09-01",
    deadline: "2026-09-30",
  };
  const form = {
    revision: 1,
    question: "When was it launched?",
    reasoning: "Date matters to this criterion.",
    conditions: [],
    events: [event],
  };
  assert.equal(
    revisionPayload(form, "monitoring").events[0].date_basis,
    "event_occurrence",
  );
  assert.deepEqual(form.events, [event]);
});
