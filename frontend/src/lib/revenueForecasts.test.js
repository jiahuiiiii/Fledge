import test from "node:test";
import assert from "node:assert/strict";
import {
  chartForecasts,
  forecastSources,
  forecastPath,
  forecastTakeaway,
  quarterlyHistory,
} from "./revenueForecasts.js";

const year = (end = "2025-12-31", value = "1000000000") => ({
  id: end,
  kind: "annual",
  end,
  start: "2025-01-01",
  metrics: [{ key: "revenue", unit: "USD", value }],
});
const point = (overrides = {}) => ({
  id: "next",
  kind: "analyst",
  source: "public",
  periodKind: "annual",
  end: "2026-12-31",
  currency: "USD",
  value: 1200000000,
  low: 1100000000,
  high: 1400000000,
  basis: "source revenue convention",
  ...overrides,
});
const forecast = {
  period_type: "annual",
  period_end: "2026-12-31",
  currency: null,
  fiscal_year: 2026,
  metrics: [
    {
      key: "revenue",
      average: "1200000000",
      low: "1100000000",
      high: "1400000000",
    },
  ],
};
const context = () => ({
  public_forecasts: {
    available: true,
    snapshot: {
      observed_at: "2026-01-01",
      data: {
        forecasts: [structuredClone(forecast)],
        url: "https://example.com/original",
        restricted_years: [2027],
      },
    },
  },
  consensus: {
    status: "saved",
    data: { forecasts: [{ ...structuredClone(forecast), currency: "USD" }] },
  },
});
const management = () => ({
  status: "available",
  releases: [
    {
      id: "release",
      current: true,
      sections: [
        {
          id: "outlook",
          period_type: "quarter",
          period_end: "2026-03-31",
          review_status: false,
          forecasts: [
            {
              id: "guidance",
              metric: "revenue",
              low: "300000000",
              high: "340000000",
              unit: "USD",
              approximate: true,
              basis: "gaap",
              quote: "Original words",
            },
          ],
          passages: [],
        },
      ],
    },
  ],
});

test("annual forecast extends annual revenue with original average and range", () => {
  const result = chartForecasts([point()], [year()], "annual");
  assert.equal(result.plotted[0].value, 1200000000);
  assert.deepEqual(
    [result.plotted[0].low, result.plotted[0].high],
    [1100000000, 1400000000],
  );
  assert.equal(result.excluded.length, 0);
  assert.equal(
    forecastPath(
      result.plotted,
      year(),
      "annual",
      (r) => r.end,
      (v) => v,
    ),
    "M2025-12-31,1000000000 L2026-12-31,1200000000 ",
  );
});
test("quarterly guidance never becomes an annual or rolling-year estimate", () => {
  const p = point({
    periodKind: "quarter",
    end: "2026-03-31",
    kind: "management",
    value: 320000000,
    low: 300000000,
    high: 340000000,
  });
  assert.deepEqual(chartForecasts([p], [year()], "annual").plotted, []);
  assert.deepEqual(
    chartForecasts([p, point()], [year()], "trailing").plotted,
    [],
  );
  assert.equal(
    chartForecasts([p], [{ ...year(), kind: "quarter" }], "quarter").plotted
      .length,
    1,
  );
  assert.equal(chartForecasts([p], [year()], "quarter").plotted.length, 0);
});
test("unstated currency is not inferred; optional chart assumption never changes sources", () => {
  const original = point({ currency: null }),
    snapshot = structuredClone(original);
  assert.equal(
    chartForecasts([original], [year()], "annual").excluded[0].reason,
    "The source does not state a currency.",
  );
  const result = chartForecasts([original], [year()], "annual", true);
  assert.equal(result.plotted[0].assumedCurrency, true);
  assert.equal(result.plotted[0].currency, null);
  assert.deepEqual(original, snapshot);
  assert.match(
    forecastTakeaway(result.plotted[0], [year()]),
    /using your USD assumption/,
  );
});
test("a USD assumption cannot override an explicitly different currency", () => {
  const result = chartForecasts(
    [point({ currency: "EUR" })],
    [year()],
    "annual",
    true,
  );
  assert.equal(result.plotted.length, 0);
  assert.match(result.excluded[0].reason, /EUR/);
});
test("withdrawal hides public and FMP values even if stale data remains in the response", () => {
  const data = context();
  data.public_forecasts.available = false;
  data.consensus.status = "withheld";
  assert.equal(forecastSources(data, null).groups.length, 0);
});
test("analyst providers remain separate with their original currency, range, source and date", () => {
  const groups = forecastSources(context(), null).groups;
  assert.equal(groups.length, 2);
  assert.equal(groups[0].points[0].currency, null);
  assert.equal(groups[1].points[0].currency, "USD");
  assert.equal(groups[0].points[0].url, "https://example.com/original");
  assert.equal(groups[0].points[0].observedAt, "2026-01-01");
  assert.equal(groups[0].points[0].value, 1200000000);
});
test("guidance uses the current release only and preserves the range and quote", () => {
  const data = management();
  data.releases.push({
    ...structuredClone(data.releases[0]),
    current: false,
    id: "old",
  });
  const result = forecastSources(null, data).guidance;
  assert.equal(result.length, 1);
  assert.equal(result[0].value, 320000000);
  assert.equal(result[0].quote, "Original words");
  assert.equal(result[0].low, 300000000);
  assert.equal(result[0].high, 340000000);
});
test("withdrawn guidance is never replaced by historical guidance", () => {
  const data = management();
  data.releases[0].sections[0].review_status = true;
  data.releases.push({
    ...structuredClone(management().releases[0]),
    current: false,
  });
  assert.equal(forecastSources(null, data).guidance.length, 0);
  data.status = "unavailable";
  assert.equal(forecastSources(null, data).guidance.length, 0);
});
test("already-reported periods, invalid dates and duplicate source periods do not extend the line", () => {
  assert.equal(
    chartForecasts([point({ end: "2025-12-31" })], [year()], "annual").plotted
      .length,
    0,
  );
  assert.equal(
    chartForecasts([point({ end: "2026-02-30" })], [year()], "annual").plotted
      .length,
    0,
  );
  assert.equal(
    chartForecasts([point(), point({ id: "conflict" })], [year()], "annual")
      .plotted.length,
    0,
  );
});
test("missing, inverted, non-finite and oversized ranges stay off the graph; zero is valid", () => {
  for (const bad of [
    { value: null },
    { low: null },
    { high: Infinity },
    { low: 1300000000 },
    { high: 1e16 },
    { value: true },
  ])
    assert.equal(
      chartForecasts([point(bad)], [year()], "annual").plotted.length,
      0,
    );
  assert.equal(
    chartForecasts([point({ value: 0, low: 0, high: 0 })], [year()], "annual")
      .plotted.length,
    1,
  );
});
test("missing intermediate years and quarters break dotted paths instead of interpolating them", () => {
  assert.match(
    forecastPath(
      [point({ end: "2027-12-31" })],
      year(),
      "annual",
      (r) => r.end,
      (v) => v,
    ),
    /^M2027/,
  );
  assert.match(
    forecastPath(
      [point({ end: "2026-09-30" })],
      year(),
      "quarter",
      (r) => r.end,
      (v) => v,
    ),
    /^M2026/,
  );
  assert.match(
    forecastPath(
      [point()],
      year("2025-12-31", null),
      "annual",
      (r) => r.end,
      (v) => v,
    ),
    /^M2026/,
  );
});
test("quarterly history comes from actual quarter rows and keeps the chosen net-result definition", () => {
  const flow = {
    status: "available",
    periods: [
      { kind: "annual", end: "2025-12-31", metrics: [] },
      {
        kind: "quarter",
        end: "2026-03-31",
        metrics: [
          {
            key: "net_result",
            label: "Net income attributable to parent",
            value: "12",
          },
          { key: "operating", value: "20" },
        ],
      },
      { kind: "quarter", end: "2025-12-31", metrics: [] },
    ],
  };
  const result = quarterlyHistory(flow);
  assert.deepEqual(
    result.map((r) => r.end),
    ["2025-12-31", "2026-03-31"],
  );
  assert.equal(result[1].metrics[0].key, "net_income");
  assert.equal(result[1].metrics[0].label, "Net income attributable to parent");
  assert.equal(quarterlyHistory({ ...flow, status: "unavailable" }).length, 0);
});
test("only explicitly comparable guidance gets a growth sentence", () => {
  assert.match(
    forecastTakeaway(point({ kind: "management", basis: "gaap" }), [year()]),
    /20.0% above the last reported fiscal year/,
  );
  assert.doesNotMatch(forecastTakeaway(point(), [year()]), /%/);
  assert.doesNotMatch(
    forecastTakeaway(
      point({ kind: "management", basis: "gaap", end: "2028-12-31" }),
      [year()],
    ),
    /%/,
  );
});

test("quarterly reported lines preserve a missing quarter", async () => {
  const { historyPath } = await import("./financialStory.js");
  const rows = ["2025-03-31", "2025-06-30", "2025-12-31"].map((end) =>
    year(end),
  );
  const path = historyPath(
    rows,
    "revenue",
    (r) => r.end,
    (v) => v,
    110,
  );
  assert.equal((path.match(/M/g) || []).length, 2);
  assert.equal((path.match(/L/g) || []).length, 1);
});
