import test from "node:test";
import assert from "node:assert/strict";
import { describeVendorCheck } from "./vendorStatus.js";

test("never asked", () => {
  assert.match(describeVendorCheck({ last_attempt_at: null }), /not been asked/);
});
test("a refused check shows the earlier error and when to retry", () => {
  const text = describeVendorCheck(
    { last_attempt_at: "A", next_attempt_at: "B", error: "FMP endpoint requires a supported subscription or key", status: "empty", count: 0 },
    (v) => v,
  );
  assert.match(text, /supported subscription/);
  assert.match(text, /after B/);
});
test("a list with only unusable entries is explained", () => {
  assert.match(describeVendorCheck({ last_attempt_at: "A", status: "saved", count: 3 }), /none can be used/);
});
