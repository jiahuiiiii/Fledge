import test from "node:test";
import assert from "node:assert/strict";
import { unfixableGaps } from "./financialGaps.js";

const row = (end, revenue, extra = []) => ({
  start: `${Number(end.slice(0, 4)) - 1}${end.slice(4)}`,
  end,
  metrics: [{ key: "revenue", label: "Revenue", value: revenue }, ...extra],
});

test("no saved year-earlier report explains revenue growth and points to Update data", () => {
  const active = row("2025-12-31", 100);
  const gaps = unfixableGaps({ rows: [active], active });
  assert.equal(gaps[0].key, "growth");
  assert.match(gaps[0].reason, /No saved report covers/);
  assert.match(gaps[0].help, /Update data/);
});

test("growth is not reported as a gap when both revenues exist", () => {
  const prior = row("2024-12-31", 80);
  const active = row("2025-12-31", 100);
  assert.deepEqual(unfixableGaps({ rows: [prior, active], active }), []);
});

test("facts the recovery tool can read are left to it; other reasons are shown exactly", () => {
  const active = row("2025-12-31", 100, [
    { key: "cash", label: "Cash", value: null, reason: "No compatible whole-company USD fact in the selected filing." },
    { key: "operating_margin", label: "Operating margin", value: null, reason: "A positive matching denominator is required; zero or negative values are not a usable ratio." },
  ]);
  const gaps = unfixableGaps({ rows: [row("2024-12-31", 80), active], active });
  assert.equal(gaps.length, 1);
  assert.match(gaps[0].reason, /positive matching denominator/);
});
