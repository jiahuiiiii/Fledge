import { test } from "node:test";
import assert from "node:assert/strict";
import { updateOutcome } from "./updateOutcome.js";

const step = (key, status) => ({ key, status });

test("says when nothing new was fetched instead of 'up to date'", () => {
  const all = [
    step("market", "cached"),
    step("rss", "cached"),
    step("alpha_vantage", "blocked"),
  ];
  assert.match(
    updateOutcome(all, "Amazon"),
    /^Nothing new to fetch for Amazon/,
  );
  assert.match(updateOutcome(all, "Amazon"), /doesn’t rate news/);
});

test("new data says updated; every source failing says so", () => {
  assert.match(
    updateOutcome([step("market", "ready"), step("rss", "cached")], "Visa"),
    /^Visa is updated/,
  );
  assert.match(
    updateOutcome([step("reddit", "partial")], "Visa"),
    /^Visa is updated/,
  );
  assert.match(
    updateOutcome([step("market", "failed"), step("rss", "failed")], "Visa"),
    /^Couldn’t update Visa/,
  );
  // The rating step is not a source: its status does not decide the message.
  assert.match(
    updateOutcome(
      [step("market", "cached"), step("analysis", "ready")],
      "Visa",
    ),
    /^Nothing new/,
  );
});
