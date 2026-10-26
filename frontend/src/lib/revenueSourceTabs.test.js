import test from "node:test";
import assert from "node:assert/strict";
import { availableSourceTabs, activeSourceTab } from "./revenueSourceTabs.js";

test("only reported breakdowns get a tab", () => {
  const tabs = availableSourceTabs([{ kind: "Operating segments" }]);
  assert.deepEqual(tabs.map(([key]) => key), ["Total revenue", "Operating segments"]);
});

test("a company with everything shows every tab", () => {
  const all = ["Operating segments", "Products and services", "Reported geographies"].map((kind) => ({ kind }));
  assert.equal(availableSourceTabs(all).length, 4);
});

test("a missing tab falls back to segments, then to total revenue", () => {
  const withSegments = availableSourceTabs([{ kind: "Operating segments" }]);
  assert.equal(activeSourceTab(withSegments, "Reported geographies"), "Operating segments");
  assert.equal(activeSourceTab(availableSourceTabs([]), "Operating segments"), "Total revenue");
});
