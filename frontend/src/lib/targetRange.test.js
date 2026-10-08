import test from "node:test";
import assert from "node:assert/strict";
import { targetRange, targetChange } from "./targetRange.js";
const targets = { low: 80, mean: 120, median: 115, high: 160 };
test("range includes quote outside consensus and computes each return from the same quote", () => {
  for (const price of [50, 100, 200]) {
    const r = targetRange(targets, { price });
    assert.ok(r.position(price) > 0 && r.position(price) < 100);
    assert.ok(r.position(r.low) < r.position(r.high));
    assert.equal(r.change(120), (120 / price - 1) * 100);
  }
  assert.equal(
    targetChange(targetRange(targets, { price: 100 }).change(80)),
    "−20.0% downside",
  );
  assert.equal(targetChange(20), "+20.0% upside");
});
test("missing/zero/invalid quotes never imply returns, identical targets remain plottable", () => {
  for (const price of [undefined, null, 0, -1, "", false, Infinity, "oops"])
    assert.equal(targetRange(targets, { price }).change(120), null);
  const r = targetRange({ low: 100, mean: 100, median: 100, high: 100 }, null);
  assert.equal(r.position(100), 50);
  assert.equal(targetChange(null), "Quote needed to compare");
});
test("invalid consensus is withheld instead of plotted", () => {
  for (const t of [
    null,
    { ...targets, low: null },
    { ...targets, mean: 999 },
    { ...targets, median: 0 },
    { ...targets, high: 40 },
  ])
    assert.equal(targetRange(t, null), null);
});
