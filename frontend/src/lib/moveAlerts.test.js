import test from "node:test";
import assert from "node:assert/strict";
import { movePercent, moveSummary } from "./moveAlerts.js";
import { inboxSummary, recordKey } from "./inbox.js";

test("saved move numbers preserve direction and percentage-point units", () => {
  assert.equal(movePercent("-3.159012"), "−3.2%");
  assert.equal(movePercent("2.005"), "+2.0%");
  assert.equal(movePercent("-0.001"), "0.0%");
  assert.equal(movePercent("-2", true), "−2.0 points");
  for (const value of [null, undefined, "", "NaN", Infinity, true]) {
    assert.equal(movePercent(value), "Unknown");
  }
});

test("price previews use their own kind, exact saved title and verified explanation", () => {
  const detail = {
    title: "NVDA −3.2% today · Nasdaq −2.1%",
    preview: true,
    explanation: { text: "The headline reports a rotation out of AI." },
  };
  const summary = inboxSummary({ kind: "move", detail });
  assert.equal(summary.title, detail.title);
  assert.equal(summary.text, detail.explanation.text);
  assert.match(summary.alert, /not sent to Telegram/);
  assert.notEqual(
    recordKey({ kind: "move", id: "one" }),
    recordKey({ kind: "company", id: "one" }),
  );
});

test("unverified cause stays unknown and withdrawn move evidence cannot leak", () => {
  assert.match(
    moveSummary({ title: "Saved move", preview: true }).text,
    /No verified explanation/,
  );
  const result = inboxSummary({
    kind: "move",
    detail: {
      withheld: true,
      title: "Sensitive old price",
      explanation: { text: "Sensitive old claim" },
    },
  });
  assert.doesNotMatch(JSON.stringify(result), /Sensitive/);
});
