import test from "node:test";
import assert from "node:assert/strict";
import { toneOf } from "./tone.js";

test("maps the app's tone words", () => {
  assert.equal(toneOf("positive leaning"), "positive");
  assert.equal(toneOf("bad"), "negative");
  assert.equal(toneOf("negative leaning"), "negative");
  assert.equal(toneOf("mixed"), "mixed");
  assert.equal(toneOf("neutral"), "neutral");
  assert.equal(toneOf("thin sample"), "unknown");
  assert.equal(toneOf(undefined), "unknown");
});
