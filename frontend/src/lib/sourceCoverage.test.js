import test from "node:test";
import assert from "node:assert/strict";
import {
  sampleWithheld,
  sourceCoverage,
  withheldAlertNote,
  withheldSourcesNote,
} from "./sourceCoverage.js";

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

test("withheld tone totals are labelled, not shown as complete or unanalysed", () => {
  const analysis = {
    summary: { news: { selected: 3, relevant: 3 }, social_platforms: {} },
    withheld_sources: 2,
    withheld_summaries: { reddit: 2, social: 2 },
    items: [
      { source_id: "r1", channel: "social", relevance: "relevant" },
      { source_id: "n1", channel: "news", relevance: "relevant" },
    ],
    sources: [
      { id: "r1", platform: "reddit" },
      { id: "n1", kind: "news" },
    ],
    coverage: {
      available_news: 3,
      social_platforms: { reddit: 3, hackernews: 0, x: 0 },
    },
  };
  const reddit = sourceCoverage(analysis).scopes.find((s) => s.scope === "reddit");
  assert.equal(reddit.withheld, 2);
  assert.equal(reddit.analysed, 1);
  assert.equal(reddit.relevant, 1);
  assert.equal(reddit.unanalysed, 0);
  assert.equal(sampleWithheld(analysis, "reddit"), true);
  assert.equal(sampleWithheld(analysis, "news"), false);
  assert.match(withheldSourcesNote(analysis), /^2 saved sources are no longer available/);
  assert.equal(withheldSourcesNote({ withheld_sources: 0 }), null);
  assert.match(
    withheldAlertNote({ payload: { withheld_items: 1 } }),
    /^1 cited source is no longer available/,
  );
  assert.equal(withheldAlertNote({ payload: {} }), null);
});
