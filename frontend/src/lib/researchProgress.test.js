import test from "node:test";
import assert from "node:assert/strict";
import { researchStep } from "./researchProgress.js";

const coverage = { news: 33, reddit: 0, hackernews: 28, discussion_days: 7 };
const checked = {
  status: "ready",
  message: "28 verified comments.",
  finished_at: "2026-10-09T14:41:23Z",
};

test("cooldown shows currently readable comments, not an empty waiting state", () => {
  const value = researchStep(
    {
      key: "hackernews",
      status: "cached",
      message: "Wait 15 minutes.",
      previous_check: checked,
    },
    coverage,
  );
  assert.equal(value.label, "Available");
  assert.equal(value.summary, "28 saved comments in the 7-day window.");
  assert.equal(value.date, checked.finished_at);
  assert.equal(value.deferred, true);
  assert.equal(value.attention, false);
});

test("withdrawn or expired sources do not inherit historical availability", () => {
  const value = researchStep(
    { key: "hackernews", status: "cached", previous_check: checked },
    { ...coverage, hackernews: 0 },
  );
  assert.equal(value.summary, "No saved comments in the 7-day window.");
  assert.notEqual(value.label, "Available");
  assert.equal(value.prior.message, "28 verified comments.");
});

test("unknown coverage is never a zero or proof of saved results", () => {
  for (const hackernews of [undefined, null, -1, NaN, "28"]) {
    const value = researchStep(
      { key: "hackernews", status: "cached" },
      { ...coverage, hackernews },
    );
    assert.equal(value.summary, null);
    assert.equal(value.label, "Refresh skipped");
  }
});

test("a prior failure survives a later skipped attempt even with saved data", () => {
  const value = researchStep(
    {
      key: "market",
      status: "cached",
      previous_check: {
        ...checked,
        status: "failed",
        message: "Provider failed.",
      },
    },
    coverage,
  );
  assert.equal(value.attention, true);
  assert.equal(value.label, "Previous check needs attention");
  assert.match(value.summary, /33 saved news reports/);
});

test("optional X off is not counted as a broken connection; enabled failures still are", () => {
  const step = { key: "x", status: "blocked", message: "Configure X." };
  assert.equal(
    researchStep({ ...step, optional_source_off: true }, coverage).label,
    "Off",
  );
  assert.equal(
    researchStep({ ...step, optional_source_off: true }, coverage).attention,
    false,
  );
  assert.equal(researchStep(step, coverage).attention, true);
});

test("active work and current failures retain their status", () => {
  const running = researchStep(
    { key: "hackernews", status: "running", message: "Fetching." },
    coverage,
  );
  assert.equal(running.state, "running");
  assert.equal(running.summary, null);
  const failed = researchStep(
    { key: "hackernews", status: "failed", message: "Denied." },
    coverage,
  );
  assert.equal(failed.attention, true);
  assert.equal(failed.message, "Denied.");
});

test("a successful zero sample is not presented as a connection failure", () => {
  const value = researchStep(
    { key: "reddit", status: "ready", message: "No matches." },
    coverage,
  );
  assert.equal(value.label, "No saved matches");
  assert.equal(value.attention, false);
  assert.match(value.summary, /No saved posts\/comments/);
});
