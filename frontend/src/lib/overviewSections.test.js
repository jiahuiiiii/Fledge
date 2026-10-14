import test from "node:test";
import assert from "node:assert/strict";
import {
  businessMix,
  currentGuidance,
  guidanceAmount,
  overviewNews,
  overviewModel,
  ratio,
  previewable,
  recentHeadlines,
  headlinesAfterReading,
  analystRevenueForecast,
  borrowingYears,
  pastDayTone,
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

test("named fiscal guidance remains readable without inventing an ending date", async () => {
  const { guidanceReason, guidancePeriod } = await import(
    "./overviewSections.js"
  );
  const source = {
    releases: [
      {
        current: true,
        sections: [
          {
            period_type: "quarter",
            period_label: "Q3 FY2027",
            period_end: null,
            forecasts: [
              {
                metric: "revenue",
                low: "1000000",
                high: "2000000",
                unit: null,
              },
            ],
          },
        ],
      },
    ],
  };
  const g = currentGuidance(source, "2026-10-12");
  assert.equal(guidancePeriod(g.section), "Q3 FY2027");
  assert.equal(guidanceAmount(g), "$1m–$2m");
  assert.match(guidanceReason(source), /does not state its exact ending date/);
  source.releases[0].sections[0].period_end = "2025-10-31";
  assert.equal(currentGuidance(source, "2026-10-12"), null);
  assert.match(guidanceReason(source, "2026-10-12"), /period that has ended/);
  assert.equal(
    guidanceReason({
      availability: { message: "The linked release is missing." },
    }),
    "The linked release is missing.",
  );
  assert.equal(
    guidanceReason({
      status: "unavailable",
      message: "Access withdrawn",
      ...source,
    }),
    "Access withdrawn",
  );
});
test("quarterly outlook compares only with the same fiscal quarter a year earlier", async () => {
  const { revenueComparisons, fiscalQuarter, growthText, guidanceScope } =
    await import("./overviewSections.js");
  const period = (kind, start, end, value) => ({
    kind,
    start,
    end,
    metrics: [{ key: "revenue", value }],
  });
  const flow = {
    income_flow: {
      periods: [
        period("trailing", "2025-07-01", "2026-06-30", "775680000000"),
        period("quarter", "2026-04-01", "2026-06-30", "200606000000"),
        period("quarter", "2026-01-01", "2026-03-31", "181519000000"),
        period("annual", "2025-01-01", "2025-12-31", "716924000000"),
        period("quarter", "2025-07-01", "2025-09-30", "180169000000"),
        period("quarter", "2025-04-01", "2025-06-30", "167702000000"),
        period("quarter", "2025-01-01", "2025-03-31", "155667000000"),
        period("annual", "2024-01-01", "2024-12-31", "637959000000"),
      ],
    },
  };
  const guidance = {
    low: "197000000000",
    high: "202000000000",
    unit: null,
    section: { period_type: "quarter", period_label: "Q3 2026", quarter: 3 },
    release: { published_at: "2026-07-31T08:06:23+08:00" },
  };
  const { latestQuarter, outlook } = revenueComparisons(flow, guidance);
  assert.equal(latestQuarter.current.end, "2026-06-30");
  assert.equal(latestQuarter.previous.end, "2025-06-30");
  assert.equal(latestQuarter.growth.toFixed(2), "19.62");
  assert.equal(outlook.previous.end, "2025-09-30");
  assert.equal(growthText(outlook.growth), "+9.3% to +12.1%");
  assert.equal(guidanceScope(guidance.section), "one quarter");
  // Quarters after the latest saved fiscal year count from its end.
  const annuals = [{ start: "2025-01-01", end: "2025-12-31" }];
  assert.equal(
    fiscalQuarter({ start: "2026-04-01", end: "2026-06-30" }, annuals),
    2,
  );
  // A non-USD outlook, a missing year-earlier quarter or an annual outlook
  // without an ending date gets no implied growth.
  assert.equal(
    revenueComparisons(flow, { ...guidance, unit: "EUR" }).outlook,
    null,
  );
  const missing = structuredClone(flow);
  missing.income_flow.periods.splice(4, 1);
  assert.equal(revenueComparisons(missing, guidance).outlook, null);
  assert.equal(
    revenueComparisons(flow, {
      ...guidance,
      section: { period_type: "annual", period_label: "FY2026" },
    }).outlook,
    null,
  );
  const annual = revenueComparisons(flow, {
    ...guidance,
    low: "800000000000",
    high: "800000000000",
    section: { period_type: "annual", period_end: "2026-12-31" },
  });
  assert.equal(annual.outlook.previous.end, "2025-12-31");
  assert.equal(growthText(annual.outlook.growth), "+11.6%");
  // No quarters: nothing to compare, nothing invented.
  assert.deepEqual(revenueComparisons({}, guidance), {
    latestQuarter: null,
    outlook: null,
  });
});

test("Overview preview skips abusive and very short untitled posts but keeps news", () => {
  assert.equal(
    previewable({
      kind: "social",
      body: "Worked there before. Foul mouth bitch.",
    }),
    false,
  );
  assert.equal(previewable({ kind: "social", body: "Avgo." }), false);
  assert.equal(
    previewable({ kind: "social", title: "AVGO earnings", body: "" }),
    true,
  );
  assert.equal(previewable({ kind: "news", title: "Chip stocks fall" }), true);
  assert.equal(
    previewable({
      kind: "social",
      body: "Broadcom's AI networking demand still looks strong to me.",
    }),
    true,
  );
});

test("Past-day headlines are company news only, newest first, and never future-dated", () => {
  const now = Date.parse("2026-10-13T10:00:00Z");
  const items = [
    { id: 1, kind: "news", title: "Old", published_at: "2026-10-11T09:00:00Z" },
    {
      id: 2,
      kind: "news",
      title: "Earlier today",
      published_at: "2026-10-13T06:00:00Z",
    },
    {
      id: 3,
      kind: "social",
      title: "Post",
      published_at: "2026-10-13T08:00:00Z",
    },
    {
      id: 4,
      kind: "news",
      title: "Latest",
      published_at: "2026-10-13T08:30:00Z",
    },
    {
      id: 5,
      kind: "news",
      title: "Future",
      published_at: "2026-10-13T12:00:00Z",
    },
  ];
  assert.deepEqual(
    recentHeadlines(items, now).map((s) => s.id),
    [4, 2],
  );
});

test("Headlines after the AI reading's cutoff are counted; withheld readings count none", () => {
  const items = [
    { kind: "news", published_at: "2026-10-12T00:00:00Z" },
    { kind: "news", published_at: "2026-10-13T08:00:00Z" },
    { kind: "social", published_at: "2026-10-13T08:00:00Z" },
  ];
  const sentiment = { cutoff: "2026-10-11T17:28:27Z" };
  assert.equal(headlinesAfterReading(sentiment, items).length, 2);
  assert.equal(
    headlinesAfterReading({ ...sentiment, withheld: true }, items).length,
    0,
  );
  assert.equal(headlinesAfterReading(null, items).length, 0);
});

test("Analyst revenue forecast keeps an unstated currency as $ and picks the nearest year", () => {
  const fmp = {
    public_forecasts: {
      available: true,
      snapshot: {
        data: {
          forecasts: [
            {
              period_type: "annual",
              period_end: "2027-10-31",
              fiscal_year: 2027,
              currency: null,
              metrics: [{ key: "revenue", average: "130000000000" }],
            },
            {
              period_type: "annual",
              period_end: "2026-10-31",
              fiscal_year: 2026,
              currency: null,
              displayed_analyst_count: 40,
              metrics: [{ key: "revenue", average: "105970000000" }],
            },
          ],
        },
      },
    },
  };
  const result = analystRevenueForecast(fmp);
  assert.equal(result.display, "$106bn");
  assert.equal(result.periodEnd, "2026-10-31");
  assert.equal(result.currencyStated, false);
  assert.equal(
    analystRevenueForecast({ public_forecasts: { available: false } }),
    null,
  );
});

test("Borrowing in years of free cash flow needs the same end date and positive cash flow", () => {
  const debt = { value: "61079000000", end: "2026-08-02" };
  assert.equal(
    borrowingYears(debt, { value: "39403000000", end: "2026-08-02" }).toFixed(
      2,
    ),
    "1.55",
  );
  assert.equal(
    borrowingYears(debt, { value: "39403000000", end: "2026-05-03" }),
    null,
  );
  assert.equal(borrowingYears(debt, { value: "-5", end: "2026-08-02" }), null);
});

test("Past-day tone counts only relevant news stories in the day before the cutoff", () => {
  const sentiment = { cutoff: "2026-10-13T09:20:00Z" };
  const items = [
    { kind: "news", tone: "negative", published_at: "2026-10-13T08:29:00Z" },
    { kind: "news", tone: "negative", published_at: "2026-10-13T07:00:00Z" },
    { kind: "news", tone: "positive", published_at: "2026-10-11T07:00:00Z" },
    { kind: "news", tone: null, published_at: "2026-10-13T07:00:00Z" },
    { kind: "social", tone: "positive", published_at: "2026-10-13T07:00:00Z" },
    { kind: "news", tone: "positive", published_at: "2026-10-13T10:00:00Z" },
  ];
  assert.deepEqual(pastDayTone(sentiment, items), {
    total: 2,
    counts: { negative: 2 },
  });
  assert.equal(pastDayTone({ ...sentiment, withheld: true }, items), null);
});
