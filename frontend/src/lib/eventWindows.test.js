import test from "node:test";
import assert from "node:assert/strict";
import { eventWindows } from "./eventWindows.js";
import { revisionPayload } from "./kestrelDiff.js";

test("monthly preview anchors month ends without drifting", () => {
  const e = {
    window_start: "2026-01-31",
    deadline: "2026-01-31",
    repeat_months: 1,
    repeat_count: 4,
  };
  assert.deepEqual(
    eventWindows(e).map((w) => w.window_start),
    ["2026-01-31", "2026-02-28", "2026-03-31", "2026-04-30"],
  );
  assert.deepEqual(
    eventWindows({
      ...e,
      window_start: "2024-02-29",
      deadline: "2024-02-29",
      repeat_months: 12,
      repeat_count: 5,
    }).map((w) => w.deadline),
    ["2024-02-29", "2025-02-28", "2026-02-28", "2027-02-28", "2028-02-29"],
  );
});
test("overlapping and unbounded windows cannot enter an approval payload", () => {
  const e = {
    condition_id: "event",
    description: "A recurring event",
    evidence_requirement: "An explicit completed event",
    role: "required",
    window_start: "2026-01-31",
    deadline: "2026-02-28",
    repeat_months: 1,
    repeat_count: 4,
  };
  const form = {
    revision: 1,
    question: "Is there another event?",
    reasoning: "Each quarter requires new evidence.",
    conditions: [],
    events: [e],
  };
  assert.throws(() => revisionPayload(form, "monitoring"), /overlap/);
  assert.throws(
    () => eventWindows({ ...e, deadline: "2026-01-31", repeat_count: 13 }),
    /2–12/,
  );
  const good = {
    ...e,
    window_start: "2026-01-01",
    deadline: "2026-03-31",
    repeat_months: 3,
  };
  assert.equal(
    revisionPayload({ ...form, events: [good] }, "monitoring").events[0]
      .repeat_count,
    4,
  );
  assert.deepEqual(
    eventWindows(good).map((w) => w.deadline),
    ["2026-03-31", "2026-06-30", "2026-09-30", "2026-12-31"],
  );
});
test("month-end quarterly dates and ordinary day anchors remain distinct", () => {
  assert.deepEqual(
    eventWindows({
      window_start: "2026-07-01",
      deadline: "2026-09-30",
      repeat_months: 3,
      repeat_count: 4,
    }).map((w) => w.deadline),
    ["2026-09-30", "2026-12-31", "2027-03-31", "2027-06-30"],
  );
  assert.deepEqual(
    eventWindows({
      window_start: "2026-01-30",
      deadline: "2026-01-30",
      repeat_months: 1,
      repeat_count: 3,
    }).map((w) => w.deadline),
    ["2026-01-30", "2026-02-28", "2026-03-30"],
  );
});

test("recurrence cannot overflow the calendar or its deadline boundary", () => {
  assert.throws(() =>
    eventWindows({
      window_start: "9999-10-01",
      deadline: "9999-10-31",
      repeat_months: 3,
      repeat_count: 2,
    }),
  );
  assert.throws(() =>
    eventWindows({
      window_start: "9999-12-01",
      deadline: "9999-12-31",
      repeat_months: 0,
      repeat_count: 1,
    }),
  );
});
