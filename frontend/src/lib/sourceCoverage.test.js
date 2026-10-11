import test from "node:test";
import assert from "node:assert/strict";
import { sourceCoverage } from "./sourceCoverage.js";

test("old limited readings disclose unanalysed candidates without declaring them unrelated", () => {
  const coverage = sourceCoverage({
    summary: { news: { selected: 8, relevant: 8 } },
    coverage: {
      available_news: 66,
      social_platforms: { reddit: 0, hackernews: 0, x: 0 },
    },
  });
  assert.equal(coverage.analysed, 8);
  assert.equal(coverage.candidates, 66);
  assert.equal(coverage.unanalysed, 58);
  assert.equal(coverage.unrelated, 0);
  assert.equal(coverage.complete, false);
});

test("full reading separates AI relevance from exclusions and preserves zero values", () => {
  const coverage = sourceCoverage({
    summary: { news: { selected: 64, relevant: 60 } },
    coverage: {
      available_news: 66,
      social_platforms: { reddit: 0, hackernews: 0, x: 0 },
      selection: {
        policy: "sentiment-all-eligible-1",
        scopes: { news: { excluded: { exact_duplicate: 2 } } },
      },
    },
    items: [
      { channel: "news", relevance: "unrelated" },
      { channel: "news", relevance: "unclear" },
    ],
  });
  assert.equal(coverage.complete, true);
  assert.equal(coverage.excluded, 2);
  assert.equal(coverage.unanalysed, 0);
  assert.equal(coverage.unrelated, 1);
  assert.equal(coverage.unclear, 1);
});

test("missing collection counts stay unknown", () => {
  const coverage = sourceCoverage({});
  assert.equal(coverage.candidates, null);
  assert.equal(coverage.unanalysed, null);
});

test("counts sources skipped by the quick relevance check", () => {
  const coverage = sourceCoverage({
    summary: { news: { selected: 3, relevant: 1 } },
    sources: [{ id: "a" }, { id: "b" }, { id: "c" }],
    items: [
      { source_id: "a", channel: "news", relevance: "relevant" },
      {
        source_id: "b",
        channel: "news",
        relevance: "unrelated",
        prefilter: true,
      },
      { source_id: "c", channel: "news", relevance: "unrelated" },
    ],
  });
  const news = coverage.scopes.find((scope) => scope.scope === "news");
  assert.equal(news.quickSkipped, 1);
  assert.equal(news.unrelated, 2);
  assert.equal(coverage.quickSkipped, 1);
});
