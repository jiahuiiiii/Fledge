import test from "node:test";
import assert from "node:assert/strict";
import { groupByCompany, toneClass } from "./reviewGroups.js";

const record = (symbol, kind, tone, created_at) => ({
  kind,
  created_at,
  detail: { symbol, ...(tone ? { brief: { tone } } : {}) },
});

test("groups by company, busiest first, bad news and price moves on top", () => {
  const groups = groupByCompany([
    record("NVDA", "company", "Neutral news", "2026-10-20T03:00:00Z"),
    record("GOOGL", "company", "Good news", "2026-10-20T01:00:00Z"),
    record("GOOGL", "move", null, "2026-10-19T15:00:00Z"),
    record("GOOGL", "company", "Bad news", "2026-10-19T10:00:00Z"),
    record("GOOGL", "company", "Neutral news", "2026-10-20T02:00:00Z"),
  ]);
  assert.deepEqual(
    groups.map(([symbol, list]) => [symbol, list.length]),
    [
      ["GOOGL", 4],
      ["NVDA", 1],
    ],
  );
  assert.deepEqual(
    groups[0][1].map((r) => r.detail.brief?.tone || r.kind),
    ["Bad news", "move", "Good news", "Neutral news"],
  );
});

test("unknown or missing tones use the neutral colour", () => {
  assert.equal(toneClass("Bad news"), "tone-negative");
  assert.equal(toneClass("Unclear news"), "tone-neutral");
  assert.equal(toneClass(undefined), "tone-neutral");
});

test("main-point lines skip zero counts and pluralise", async () => {
  const { weekLine, countsLine } = await import("./reviewGroups.js");
  const points = [
    {
      symbol: "GOOGL",
      total: 8,
      bad: 1,
      mixed: 0,
      good: 2,
      other: 4,
      moves: 1,
    },
    { symbol: "NVDA", total: 1, bad: 0, mixed: 0, good: 0, other: 1, moves: 0 },
  ];
  assert.equal(
    weekLine(points),
    "9 updates across 2 companies · 1 price move · 1 bad-news item",
  );
  assert.equal(weekLine([points[1]]), "1 update across 1 company");
  assert.equal(
    countsLine(points[0]),
    "8 updates · 1 bad · 2 good · 4 neutral or unclear · 1 price move",
  );
});
