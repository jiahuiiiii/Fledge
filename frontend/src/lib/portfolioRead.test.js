import test from "node:test";
import assert from "node:assert/strict";
import { pctText, barWidth, toneLine } from "./portfolioRead.js";

test("moves read with a real minus sign and one decimal", () => {
  assert.equal(pctText(-15.46), "−15.5%");
  assert.equal(pctText(2), "+2.0%");
  assert.equal(pctText(0), "0.0%");
  assert.equal(pctText(null), "No price");
});

test("bars scale to the biggest move and stay visible", () => {
  assert.equal(barWidth(-15.46, 15.46), "100%");
  assert.equal(barWidth(-1.8, 15.46), "12%");
  assert.equal(barWidth(0.1, 15.46), "4%");
  assert.equal(barWidth(null, 15), "0%");
});

test("news tone across the list in plain words", () => {
  assert.equal(
    toneLine({ negative: 4, positive: 1, neutral: 1 }),
    "News across your list: 1 good, 4 bad, 1 neutral.",
  );
  assert.equal(toneLine({}), "No news reading saved for these companies yet.");
});
