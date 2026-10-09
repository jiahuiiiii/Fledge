import test from "node:test";
import assert from "node:assert/strict";
import { originalSample } from "./originalSample.js";
const sources = [
  { id: "older", kind: "news", published_at: "2026-10-01T00:00:00Z" },
  {
    id: "context",
    kind: "news",
    comparison_only: true,
    published_at: "2026-10-02T02:00:00Z",
  },
  { id: "social", kind: "social", published_at: "2026-10-02T02:00:00Z" },
  { id: "unrelated", kind: "news", published_at: "2026-10-02T00:00:00Z" },
];
test("original reading retains an unrelated selected item and excludes comparison-only and other-channel sources", () => {
  assert.deepEqual(
    originalSample(
      { sources, items: [{ source_id: "unrelated", relevance: "unrelated" }] },
      "news",
    ).map((s) => s.id),
    ["unrelated", "older"],
  );
  assert.deepEqual(
    originalSample({ sources }, "social").map((s) => s.id),
    ["social"],
  );
  assert.equal(sources[0].id, "older");
});
test("withdrawn sample never exposes retained source text", () => {
  assert.deepEqual(originalSample({ sources, withheld: true }, "news"), []);
  assert.deepEqual(originalSample(null, "news"), []);
  assert.deepEqual(originalSample({ sources, withheld: true }, "all"), []);
  assert.deepEqual(originalSample({ sources }, "unsupported"), []);
});

test("all selected sources retain news, legacy Reddit and newer platforms in date order without comparison context", () => {
  const analysis = {
    sources: [
      ...sources,
      {
        id: "hn",
        kind: "social",
        platform: "hackernews",
        published_at: "2026-10-02T03:00:00Z",
      },
      {
        id: "x",
        kind: "social",
        platform: "x",
        published_at: "2026-10-02T03:00:00Z",
      },
      { id: "filing", kind: "sec", published_at: "2026-10-02T04:00:00Z" },
    ],
    items: [{ source_id: "unrelated", relevance: "unrelated" }],
  };
  assert.deepEqual(
    originalSample(analysis, "all").map((source) => source.id),
    ["hn", "x", "social", "unrelated", "older"],
  );
  assert.equal(analysis.sources[0].id, "older");
});

test("platform filtering does not blend HN comments with historic Reddit posts", () => {
  const analysis = {
    sources: [
      ...sources,
      {
        id: "hn",
        kind: "social",
        platform: "hackernews",
        published_at: "2026-10-02T03:00:00Z",
      },
    ],
  };
  assert.deepEqual(
    originalSample(analysis, "social", "hackernews").map((s) => s.id),
    ["hn"],
  );
  assert.deepEqual(
    originalSample(analysis, "social", "reddit").map((s) => s.id),
    ["social"],
  );
});
