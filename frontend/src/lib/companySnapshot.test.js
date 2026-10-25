import test from "node:test";
import assert from "node:assert/strict";
import {
  annualGrowth,
  balance,
  money,
  newsTone,
  revenueOutlook,
  snapshot,
} from "./companySnapshot.js";

const metric = (key, value, end = "2026-08-02") => ({ key, value, end });

test("named fiscal guidance does not invent an ending date", () => {
  const data = {
    management_outlook: {
      releases: [
        {
          sections: [
            {
              period_type: "quarter",
              period_label: "Q3 FY2027",
              forecasts: [{ metric: "revenue", low: "1000000000" }],
            },
          ],
        },
      ],
    },
  };
  assert.equal(
    snapshot(data).sentences[0],
    "Saved management guidance is $1bn of revenue for Q3 FY2027. Currency is not specified by the source. Exact ending date is not stated.",
  );
});

const workspace = {
  financial_depth: {
    trailing: [
      {
        key: "revenue",
        value: 89104000000,
        start: "2025-08-04",
        end: "2026-08-02",
      },
      { key: "operating_income", value: 42814000000 },
      { key: "operating_margin", value: "48.0494" },
      { key: "free_cash_flow", value: 39403000000 },
      { key: "net_income", value: null },
    ],
    debt: { value: 61079000000, end: "2026-08-02" },
    revenue_trend: [
      { period_end: "2025-11-02", value: "63887000000" },
      { period_end: "2024-11-03", value: "51574000000" },
    ],
  },
  performance: {
    reports: {
      annual: { period_end: "2025-11-02", metrics: [] },
      quarter: {
        period_end: "2026-08-02",
        form: "10-Q",
        metrics: [
          metric("assets", "188148000000"),
          metric("liabilities", "88458000000"),
          metric("cash", "23975000000"),
        ],
      },
    },
  },
  management_outlook: {
    releases: [
      {
        published_at: "2026-09-03T04:26:04+08:00",
        sections: [
          {
            period_end: "2026-11-01",
            period_type: "quarter",
            forecasts: [
              { metric: "operating_margin", low: "66", high: "66" },
              {
                metric: "revenue",
                low: "34800000000",
                high: "34800000000",
                approximate: true,
                comparison: { status: "uncompared" },
              },
            ],
          },
        ],
      },
    ],
  },
  sentiment: {
    created_at: "2026-10-09T00:15:00+00:00",
    stale: false,
    summary: {
      news: {
        tone: "mixed / balanced",
        counts: { positive: 3, neutral: 1, negative: 2, mixed: 0 },
        selected: 8,
      },
    },
  },
  market: { quote: { quote: { price: 360.14 } } },
};

test("summary sentences use only saved figures", () => {
  const { sentences } = snapshot(workspace);
  assert.deepEqual(sentences, [
    "Revenue grew 23.9% in the fiscal year to 2 Nov 2025.",
    "Saved management guidance is about $34.8bn of revenue for the quarter ending 1 Nov 2026. Currency is not specified by the source.",
    "Its borrowing is about 2.5× the cash it holds.",
  ]);
});

test("historical guidance stays dated rather than sounding like a current forecast", () => {
  const data = structuredClone(workspace);
  data.management_outlook.releases[0].sections[0].period_end = "2001-11-01";
  const outlook = revenueOutlook(data.management_outlook);
  assert.match(snapshot(data).sentences[1], /This forecast period has ended\./);
  assert.equal(outlook.low, 34800000000);
  assert.equal(outlook.high, 34800000000);
  assert.equal(outlook.periodEnd, "2001-11-01");
  assert.equal(outlook.unit, undefined);
});

test("checks pass, fail or stay unknown from the data", () => {
  const { sections } = snapshot(workspace);
  const health = sections.find((s) => s.title === "Financial health");
  assert.deepEqual(
    health.checks.map((c) => c.state),
    ["pass", "fail", "pass"],
  );
  const outlook = sections.find((s) => s.title === "Guidance and forecasts");
  assert.equal(outlook.checks[1].label, "Not yet compared with results");
  assert.equal(outlook.checks[1].state, "unknown");
});

test("borrowing from another balance date is not used", () => {
  const moved = structuredClone(workspace);
  moved.financial_depth.debt.end = "2025-11-02";
  const position = balance(moved.performance, moved.financial_depth);
  assert.equal(position.debt, null);
  const { sentences, sections } = snapshot(moved);
  assert.equal(sentences.length, 2);
  const health = sections.find((s) => s.title === "Financial health");
  assert.equal(health.checks[1].state, "unknown");
});

test("missing data removes sentences and figures", () => {
  const { sentences, sections } = snapshot({});
  assert.deepEqual(sentences, []);
  for (const section of sections)
    for (const c of section.checks) assert.equal(c.state, "unknown");
  assert.equal(
    annualGrowth({ revenue_trend: [{ period_end: "2025-11-02", value: "1" }] }),
    null,
  );
  assert.equal(revenueOutlook({ releases: [] }), null);
  assert.equal(newsTone({}), null);
});

test("money formatting is compact", () => {
  assert.equal(money(89104000000), "US$89.1bn");
  assert.equal(money(-1500000000), "−US$1.5bn");
  assert.equal(money(null), null);
});

test("thin samples do not get a tone label", () => {
  const thin = newsTone({
    summary: { news: { tone: "thin sample", counts: {} } },
  });
  assert.equal(thin.label, null);
});
