import test from "node:test";
import assert from "node:assert/strict";
import { trendPoints } from "./financialTrends.js";

const row = (end, revenue, margin) => ({
  end,
  metrics: [
    { key: "revenue", value: revenue },
    { key: "operating_margin", value: margin },
  ],
});

test("missing figures are gaps, not zero", () => {
  const rows = [row("2025-06-30", 100, null), row("2026-06-30", 150, 20)];
  assert.deepEqual(trendPoints(rows, "operating_margin"), [null, 20]);
});

test("growth needs the same period a year earlier", () => {
  const rows = [row("2025-06-30", 100), row("2026-06-30", 150)];
  assert.deepEqual(trendPoints(rows, "revenue_growth"), [null, 50]);
});
