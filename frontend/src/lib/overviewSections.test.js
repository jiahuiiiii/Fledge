import test from "node:test";
import assert from "node:assert/strict";
import {
  businessMix,
  currentGuidance,
  guidanceAmount,
  overviewNews,
  overviewModel,
  ratio,
} from "./overviewSections.js";
const row = (key, value, end = "2026-08-02") => ({
  key,
  value,
  unit: "USD",
  end,
  inputs: [{ unit: "USD", end, start: null, accession: "quarter" }],
});
const data = {
  instrument: { symbol: "TEST" },
  performance: {
    status: "available",
    reports: {
      quarter: {
        accession: "quarter",
        period_end: "2026-08-02",
        metrics: [
          row("assets", "100"),
          row("liabilities", "40"),
          row("cash", "12"),
        ],
      },
    },
  },
  financial_depth: {
    status: "available",
    debt: row("total_debt", "30"),
    trailing: [],
  },
};
test("Overview position uses the same date and filing, keeps zero, and never fills missing borrowing", () => {
  const model = overviewModel(data);
  assert.equal(model.assetsRatio, 2.5);
  assert.equal(model.cashRatio, 0.4);
  for (const change of [
    { end: "2025-08-02" },
    { unit: "EUR" },
    { inputs: [] },
    { inputs: [{ unit: "USD", end: "2026-08-02", accession: "other" }] },
  ]) {
    const changed = structuredClone(data);
    Object.assign(changed.financial_depth.debt, change);
    assert.equal(overviewModel(changed).borrowing, null);
  }
  assert.equal(ratio(0, 20), 0);
  assert.equal(ratio(20, 0), null);
  assert.equal(ratio(null, 20), null);
});
test("business mix compares quarter and annual of one business axis, excluding YTD and geography", () => {
  const group = (kind, period, end) => ({ kind, period, end });
  const result = businessMix({
    segment_revenue: {
      groups: [
        group("Operating segments", "Quarter", "2026-08-02"),
        group("Operating segments", "Quarter", "2026-05-03"),
        group("Operating segments", "Annual", "2025-11-02"),
        group("Operating segments", "Fiscal year to date", "2026-08-02"),
        group("Reported geographies", "Quarter", "2026-08-02"),
      ],
    },
  });
  assert.deepEqual(
    result.map((r) => [r.period, r.end]),
    [
      ["Quarter", "2026-08-02"],
      ["Annual", "2025-11-02"],
    ],
  );
});
test("current guidance excludes withdrawn, historical, expired and truncated sections; no implied USD", () => {
  const section = {
    period_end: "2026-11-01",
    forecasts: [
      {
        metric: "revenue",
        low: "34800000000",
        high: "34800000000",
        approximate: true,
        unit: null,
      },
    ],
  };
  const source = { releases: [{ current: true, sections: [section] }] };
  assert.equal(
    guidanceAmount(currentGuidance(source, "2026-10-09")),
    "≈ $34.8bn",
  );
  for (const changed of [
    { review_status: true },
    { truncated: true },
    { period_end: "2026-09-01" },
  ])
    assert.equal(
      currentGuidance(
        {
          releases: [{ current: true, sections: [{ ...section, ...changed }] }],
        },
        "2026-10-09",
      ),
      null,
    );
  assert.equal(
    currentGuidance(
      { releases: [{ current: false, sections: [section] }] },
      "2026-10-09",
    ),
    null,
  );
});
test("current headlines carry AI labels only for identical permitted source versions", () => {
  const source = {
    id: "one",
    kind: "social",
    platform: "hackernews",
    title: "Hacker News comment",
    body: "Actual author's words about the chip market.",
    published_at: "2026-10-09T00:00:00Z",
  };
  const sample = {
    sentiment_inputs: { sources: [source] },
    sentiment: {
      sources: [{ ...source }],
      items: [
        { source_id: "one", relevance: "relevant", sentiment: "negative" },
      ],
    },
  };
  const news = overviewNews(sample)[0];
  assert.equal(news.headline, source.body);
  assert.equal(news.tone, "negative");
  const changed = structuredClone(sample);
  changed.sentiment_inputs.sources[0].body = "Edited comment";
  assert.equal(overviewNews(changed)[0].tone, null);
  const withheld = structuredClone(sample);
  withheld.sentiment.withheld = true;
  assert.equal(overviewNews(withheld)[0].tone, null);
  assert.equal(
    overviewNews({ sentiment: { withheld: true, sources: [source] } }).length,
    0,
  );
  assert.equal(
    overviewNews({
      sentiment_inputs: { sources: [{ ...source, comparison_only: true }] },
    }).length,
    0,
  );
});
test("saved multiples remain symbol and access scoped; public forecast access is explicit", () => {
  const reads = {
    valuation: {
      references: [
        {
          available: true,
          symbol: "TEST",
          reference: {
            symbol: "TEST",
            metrics: {
              earnings: { value: "46.611" },
              sales: { value: "20.0167" },
            },
          },
        },
      ],
    },
    fmp: {
      public_forecasts: {
        available: false,
        snapshot: { data: { forecasts: [{}] } },
      },
    },
  };
  assert.equal(overviewModel(data, reads).pe, 46.611);
  assert.equal(overviewModel(data, reads).forecasts, false);
  reads.valuation.references[0].reference.symbol = "OTHER";
  assert.equal(overviewModel(data, reads).pe, null);
  reads.fmp.public_forecasts.available = true;
  assert.equal(overviewModel(data, reads).forecasts, true);
});
test("empty and withdrawn datasets remain missing", () => {
  const model = overviewModel({});
  assert.equal(model.revenue, null);
  assert.equal(model.borrowing, null);
  assert.equal(model.assetsRatio, null);
  assert.equal(model.pe, null);
  assert.deepEqual(model.headlines, []);
  const withdrawn = structuredClone(data);
  withdrawn.performance.status = "unavailable";
  withdrawn.financial_depth.status = "unavailable";
  assert.equal(overviewModel(withdrawn).cashRatio, null);
});
