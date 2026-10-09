import test from "node:test";
import assert from "node:assert/strict";
import {
  reportedRow,
  forecastRow,
  position,
  scale,
  yearsFor,
  managementRows,
} from "./sectorPosition.js";
const member = (symbol = "AVGO", value = "20", key = "revenue_growth") => {
  const revenue = {
    namespace: "us-gaap",
    concept: "Revenues",
    unit: "USD",
    accession: "annual",
    start: "2025-01-01",
    end: "2025-12-31",
    value: "120",
  };
  const prior = {
    ...revenue,
    start: "2024-01-01",
    end: "2024-12-31",
    value: "100",
  };
  const income = { ...revenue, concept: "OperatingIncomeLoss", value: "24" };
  return {
    symbol,
    name: symbol,
    performance: {
      status: "available",
      method: "sec-performance-1",
      reports: {
        annual: {
          form: "10-K",
          accession: "annual",
          period_type: "annual",
          period_end: "2025-12-31",
          metrics: [
            {
              key,
              value,
              unit: key === "revenue" ? "USD" : "percent",
              start: revenue.start,
              end: revenue.end,
              inputs:
                key === "revenue"
                  ? [revenue]
                  : key === "operating_margin"
                    ? [income, revenue]
                    : [revenue, prior],
            },
          ],
        },
      },
    },
  };
};
const forecast = (symbol = "AVGO") => ({
  symbol,
  name: symbol,
  consensus: {
    status: "saved",
    snapshot_id: "saved",
    data: {
      method: "fmp-research-1",
      forecasts: [
        {
          period_type: "annual",
          period_end: "2026-12-31",
          currency: "USD",
          metrics: [{ key: "revenue", average: "100" }],
        },
        {
          period_type: "annual",
          period_end: "2027-12-31",
          currency: "USD",
          metrics: [{ key: "revenue", average: "120" }],
        },
      ],
    },
  },
});
test("annual growth and margin reuse exact reported values and retain negative and zero", () => {
  for (const value of ["0", "-20", "20.012345"])
    assert.equal(
      reportedRow(member("AVGO", value), "revenue_growth").value,
      Number(value),
    );
  assert.equal(
    reportedRow(member("AVGO", "20", "operating_margin"), "operating_margin")
      .value,
    20,
  );
});
test("wrong fiscal kind, missing inputs, units, namespace and accession withhold", () => {
  for (const change of [
    (m) => (m.performance.status = "unavailable"),
    (m) => (m.performance.reports.annual.period_type = "quarter"),
    (m) => m.performance.reports.annual.metrics[0].inputs.pop(),
    (m) => (m.performance.reports.annual.metrics[0].inputs[0].unit = "EUR"),
    (m) =>
      (m.performance.reports.annual.metrics[0].inputs[0].accession = "other"),
    (m) =>
      (m.performance.reports.annual.metrics[0].inputs[0].namespace = "custom"),
    (m) => (m.performance.reports.annual.metrics[0].start = "2025-07-01"),
  ]) {
    const m = member();
    change(m);
    assert.equal(reportedRow(m, "revenue_growth").value, null);
  }
});
test("position gives direct peer relationships with coverage, ties and percentage-point difference", () => {
  const rows = [
    { symbol: "AVGO", value: 20, end: "2025-12-31" },
    { symbol: "NVDA", value: 60, end: "2026-01-31" },
    { symbol: "QCOM", value: 10, end: "2025-09-30" },
    { symbol: "AMD", value: null },
  ];
  const p = position(rows, "AVGO");
  assert.equal(p.text, "AVGO is above QCOM; below NVDA.");
  assert.equal(p.coverage, 2);
  assert.equal(p.median, 35);
  assert.equal(p.difference, -15);
  assert.equal(p.complete, false);
  assert.match(
    position([{ ...rows[0] }, { ...rows[1], value: 20 }], "AVGO").text,
    /equal to NVDA/,
  );
});
test("far-apart years never become a ranked cohort", () => {
  assert.equal(
    position(
      [
        { symbol: "AVGO", value: 20, end: "2025-12-31" },
        { symbol: "NVDA", value: 60, end: "2024-12-31" },
      ],
      "AVGO",
    ).coverage,
    0,
  );
  assert.equal(position([{ symbol: "AVGO", value: null }], "AVGO").coverage, 0);
});
test("expected growth compares two annual USD forecasts from one source, not actuals or public unknown units", () => {
  const m = forecast();
  assert.ok(Math.abs(forecastRow(m, "2027", "2026-10-09").value - 20) < 1e-10);
  assert.deepEqual(yearsFor([m], "2026-10-09"), ["2026", "2027"]);
  for (const change of [
    (m) => (m.consensus.status = "withheld"),
    (m) => (m.consensus.data.forecasts[1].currency = null),
    (m) => (m.consensus.data.forecasts[0].metrics[0].average = "0"),
    (m) => (m.consensus.data.forecasts[0].period_type = "quarter"),
    (m) => (m.consensus.data.forecasts[1].period_end = "2029-12-31"),
  ]) {
    const m = forecast();
    change(m);
    assert.equal(forecastRow(m, "2027", "2026-10-09").value, null);
  }
});
test("shared signed scale includes zero and remains usable for all-zero charts", () => {
  assert.deepEqual(scale([{ value: -20 }, { value: 60 }, { value: null }]), {
    low: -20,
    high: 60,
    span: 80,
  });
  assert.deepEqual(scale([{ value: 0 }]), { low: 0, high: 1, span: 1 });
});
test("withdrawn and historical management targets cannot become current targets", () => {
  const m = {
    symbol: "AVGO",
    management: {
      status: "available",
      releases: [
        {
          current: false,
          sections: [
            {
              period_type: "quarter",
              forecasts: [{ metric: "operating_margin", low: "66" }],
            },
          ],
        },
      ],
    },
  };
  assert.equal(managementRows([m])[0].margin, undefined);
  m.management.releases[0].current = true;
  m.management.releases[0].sections[0].review_status = "withdrawn";
  assert.equal(managementRows([m])[0].margin, undefined);
});
