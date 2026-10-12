import test from "node:test";
import assert from "node:assert/strict";
import {
  reportedRow,
  peRows,
  peerAverage,
  comparisonRows,
  comparisonExclusion,
  chartRows,
  differentYearEnd,
  forecastRow,
  position,
  scale,
  yearsFor,
  managementRows,
  peerStatus,
} from "./sectorPosition.js";
test("peer status separates unsaved, pending, uncollected and failed data without invented periods", () => {
  assert.equal(peerStatus(null).label, "Not saved");
  for (const [status, label] of [
    ["loading", "Fetching…"],
    ["not_collected", "Not collected"],
    ["failed", "Fetch failed"],
    ["no_report", "No annual report"],
    ["unavailable", "Source unavailable"],
  ]) {
    const member = {
      symbol: "PEER",
      filing_status: { status, message: "Exact reason", can_fetch: false },
    };
    const row = reportedRow(member, "revenue_growth");
    assert.equal(row.value, null);
    assert.equal(row.reason, "Exact reason");
    assert.equal(peerStatus(member, row).label, label);
    assert.equal(peerStatus(member, row).message, "Exact reason");
  }
  const failed = {
    filing_status: {
      status: "failed",
      message: "SEC refresh failed; no new evidence committed.",
    },
  };
  assert.equal(
    peerStatus(failed, reportedRow(failed, "revenue_growth")).message,
    "The last filing check failed. Save & compare to retry.",
  );
  assert.equal(
    failed.filing_status.message,
    "SEC refresh failed; no new evidence committed.",
  );
});
test("different year-end peers retain their figures as context, and pending updates keep saved values", () => {
  const own = { symbol: "OWN", value: 12, end: "2025-12-31" },
    row = { symbol: "MSFT", value: 17.8, end: "2026-06-30" },
    member = { symbol: "MSFT", filing_status: { status: "ready" } };
  const state = peerStatus(member, row, own);
  assert.equal(state.label, "Different year-end");
  assert.equal(state.status, "reference");
  assert.match(state.message, /181 days/);
  assert.match(state.message, /outside the average and ranking/);
  assert.equal(row.value, 17.8);
  assert.equal(
    peerStatus(member, row, own, {
      status: "loading",
      message: "Fetching financial data…",
    }).label,
    "Fetching…",
  );
  assert.equal(
    peerStatus(member, { ...row, end: "2026-01-01" }, own).label,
    "Ready",
  );
  assert.equal(
    peerStatus(
      member,
      { ...row, value: null, reason: "Missing compatible USD total." },
      own,
    ).message,
    "Missing compatible USD total.",
  );
});
test("different fiscal years extend the chart scale while the comparable mean and ranking stay exact", () => {
  const rows = [
    { symbol: "AVGO", value: 23.874432853763524, end: "2025-11-02" },
    { symbol: "AMD", value: 34.33779329067287, end: "2025-12-27" },
    { symbol: "MRVL", value: 42.08728521145077, end: "2026-01-31" },
    {
      symbol: "MU",
      value: 256.3272513243084,
      exact: "256.3272513243084167157151265",
      end: "2026-09-03",
    },
    { symbol: "NVDA", value: 65.4735357900948, end: "2026-01-25" },
    { symbol: "QCOM", value: 13.65946306657769, end: "2025-09-28" },
  ];
  const before = structuredClone(rows),
    plotted = comparisonRows(rows, "AVGO"),
    average = peerAverage(rows, "AVGO");
  assert.deepEqual(
    plotted.map((r) => r.symbol),
    ["AVGO", "AMD", "MRVL", "NVDA", "QCOM"],
  );
  assert.equal(scale(plotted).high, rows[4].value);
  assert.deepEqual(plotted.slice(1), average.peers);
  assert.deepEqual(chartRows(rows, "AVGO"), rows);
  assert.equal(scale(chartRows(rows, "AVGO")).high, rows[3].value);
  assert.equal(differentYearEnd(rows[3], rows[0]), true);
  assert.equal(average.value.toFixed(1), "38.9");
  assert.deepEqual(average.missing, [rows[3]]);
  assert.equal(
    position(rows, "AVGO").text,
    "AVGO is above QCOM; below AMD, MRVL and NVDA.",
  );
  assert.equal(
    comparisonExclusion(rows[3], rows[0]),
    "Fiscal year ends are 305 days apart (120-day limit).",
  );
  assert.deepEqual(rows, before);
  assert.equal(
    average.missing[0],
    rows[3],
    "exact original evidence is retained",
  );
});
test("context rows retain both date directions, negative and zero values without admitting missing periods", () => {
  const own = {
      symbol: "OWN",
      value: 12.4,
      end: "2025-12-31",
      unit: "percent",
    },
    peer = (symbol, offset, value) => ({
      ...own,
      symbol,
      value,
      end: new Date(Date.parse(own.end) + offset * 86400000)
        .toISOString()
        .slice(0, 10),
    });
  const rows = [
      own,
      peer("BEFORE", -121, -5),
      peer("AFTER", 121, 0),
      peer("EDGE", 120, 3),
      { ...peer("GAP", 181, null), reason: "Not reported" },
      { ...peer("DATE", 181, 90), end: null },
    ],
    before = structuredClone(rows);
  assert.deepEqual(chartRows(rows, "OWN"), rows.slice(0, 4));
  assert.deepEqual(
    rows.map((r) => differentYearEnd(r, own)),
    [false, true, true, false, false, false],
  );
  assert.equal(peerAverage(rows, "OWN").value, 3);
  assert.equal(position(rows, "OWN").text, "OWN is above EDGE.");
  assert.deepEqual(scale(chartRows(rows, "OWN")), {
    low: -5,
    high: 12.4,
    span: 17.4,
  });
  assert.deepEqual(rows, before);
  const unknown = [{ ...own, end: null }, ...rows.slice(1)];
  assert.deepEqual(chartRows(unknown, "OWN"), [unknown[0]]);
});
test("annual date limit includes both 120-day boundaries, zero and negative figures", () => {
  const own = { symbol: "OWN", value: 10, end: "2025-07-01" };
  const peer = (symbol, offset, value) => ({
    symbol,
    value,
    end: new Date(Date.parse(own.end) + offset * 86400000)
      .toISOString()
      .slice(0, 10),
  });
  const rows = [
    own,
    peer("BEFORE", -120, -10),
    peer("AFTER", 120, 0),
    peer("OLD", -121, -999),
    peer("LATE", 121, 999),
    { symbol: "GAP", value: null },
    { symbol: "DATE", value: 100 },
    { symbol: "BAD_DATE", value: 100, end: "unknown" },
  ];
  assert.deepEqual(comparisonRows(rows, "OWN"), rows.slice(0, 3));
  assert.deepEqual(scale(comparisonRows(rows, "OWN")), {
    low: -10,
    high: 10,
    span: 20,
  });
  assert.equal(peerAverage(rows, "OWN").value, -5);
  assert.equal(position(rows, "OWN").coverage, 2);
  assert.match(comparisonExclusion(rows[3], own), /121 days/);
  assert.match(
    comparisonExclusion(rows[5], own),
    /saved figure is unavailable/,
  );
  assert.match(
    comparisonExclusion(rows[6], own),
    /fiscal year end is unavailable/,
  );
  assert.match(
    comparisonExclusion(rows[7], own),
    /fiscal year end is unavailable/,
  );
  for (const end of [null, "unknown"]) {
    const missingDate = [{ ...own, end }, ...rows.slice(1)];
    assert.deepEqual(comparisonRows(missingDate, "OWN"), [missingDate[0]]);
    assert.equal(peerAverage(missingDate, "OWN").value, null);
    assert.equal(position(missingDate, "OWN").coverage, 0);
  }
  const missing = [
    { ...own, value: null },
    { ...rows[1], value: null },
  ];
  assert.equal(comparisonRows(missing, "OWN").length, 1);
  assert.equal(position(missing, "OWN").coverage, 0);
  assert.equal(peerAverage(missing, "OWN").value, null);
});
test("P/E comparison keeps differing saved dates and only usable Finnhub peers", () => {
  const rows = [
    { symbol: "OWN", value: 40, unit: "multiple", source: "Finnhub" },
    {
      symbol: "PEER",
      value: 100,
      unit: "multiple",
      source: "Finnhub",
      end: "2000-01-01",
    },
    { symbol: "OTHER", value: 900, unit: "multiple", source: "FMP" },
    { symbol: "ZERO", value: 0, unit: "multiple", source: "Finnhub" },
  ];
  assert.deepEqual(comparisonRows(rows, "OWN"), rows.slice(0, 2));
  assert.deepEqual(chartRows(rows, "OWN"), rows.slice(0, 2));
  assert.equal(peerAverage(rows, "OWN").value, 100);
  assert.equal(position(rows, "OWN").text, "OWN is below PEER.");
});
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
test("20-F annual ratios plot in their original single currency and standard accounting basis", () => {
  for (const [namespace, currency] of [
    ["us-gaap", "CNY"],
    ["ifrs-full", "EUR"],
  ]) {
    for (const key of ["revenue_growth", "operating_margin"]) {
      const m = member("FOREIGN", "20", key),
        report = m.performance.reports.annual;
      report.form = "20-F";
      report.filed_on = "2026-02-01";
      report.financial_basis = {
        method: "sec-foreign-annual-1",
        namespace,
        currency,
        reason: null,
      };
      for (const input of report.metrics[0].inputs) {
        input.namespace = namespace;
        input.unit = currency;
        input.form = report.form;
        input.filed = report.filed_on;
        if (namespace === "ifrs-full")
          input.concept =
            input.concept === "OperatingIncomeLoss"
              ? "ProfitLossFromOperatingActivities"
              : "Revenue";
      }
      const original = structuredClone(m),
        row = reportedRow(m, key);
      assert.equal(row.value, 20);
      assert.match(row.basisLabel, new RegExp(currency));
      assert.equal(
        comparisonRows(
          [{ symbol: "AMZN", value: 12, end: "2026-03-01" }, row],
          "AMZN",
        ).length,
        2,
      );
      for (const mutate of [
        (r) => (r.metrics[0].inputs[0].unit = "USD"),
        (r) => (r.metrics[0].inputs[0].namespace = "custom"),
        (r) => (r.metrics[0].inputs[0].accession = "other"),
        (r) => (r.metrics[0].inputs[0].form = "6-K"),
        (r) => (r.metrics[0].inputs[0].filed = "2026-02-02"),
        (r) => (r.financial_basis.currency = "XYZ"),
        (r) => (r.financial_basis.reason = "Ambiguous currency"),
      ]) {
        const invalid = structuredClone(m);
        mutate(invalid.performance.reports.annual);
        assert.equal(reportedRow(invalid, key).value, null);
      }
      assert.deepEqual(m, original);
    }
  }
});
test("20-F native revenue is not relabelled USD for the revenue-size chart", () => {
  const m = member("FOREIGN", "120", "revenue"),
    report = m.performance.reports.annual;
  report.form = "20-F";
  report.metrics[0].unit = "CNY";
  report.metrics[0].inputs[0].unit = "CNY";
  assert.equal(reportedRow(m, "revenue").value, null);
  report.metrics[0].unit = "USD";
  report.metrics[0].inputs[0].unit = "USD";
  assert.equal(reportedRow(m, "revenue").value, 120);
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
test("retained figures validate against their original filing and keep amendment evidence", () => {
  const m = member();
  const annual = m.performance.reports.annual,
    row = annual.metrics[0];
  row.source_report = { ...annual, metrics: undefined };
  row.filing_resolution = {
    status: "retained",
    amendments: [{ document_id: "proof" }],
  };
  annual.accession = "amendment";
  annual.form = "10-K/A";
  assert.equal(reportedRow(m, "revenue_growth").value, 20);
  assert.equal(reportedRow(m, "revenue_growth").report.accession, "annual");
  assert.equal(
    reportedRow(m, "revenue_growth").filingResolution.amendments[0].document_id,
    "proof",
  );
  row.inputs[0].accession = "amendment";
  assert.equal(reportedRow(m, "revenue_growth").value, null);
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

test("peer average excludes the company, missing figures and incompatible fiscal periods; mean is not median", () => {
  const rows = [
    { symbol: "AVGO", value: 200, unit: "percent", end: "2025-12-31" },
    { symbol: "A", value: -10, unit: "percent", end: "2025-12-31" },
    { symbol: "B", value: 0, unit: "percent", end: "2026-01-31" },
    { symbol: "C", value: 100, unit: "percent", end: "2025-11-30" },
    { symbol: "OLD", value: 1000, unit: "percent", end: "2023-12-31" },
    { symbol: "GAP", value: null, unit: "percent", end: "2025-12-31" },
  ];
  const result = peerAverage(rows, "AVGO");
  assert.equal(result.value, 30);
  assert.deepEqual(
    result.peers.map((r) => r.symbol),
    ["A", "B", "C"],
  );
  assert.deepEqual(
    result.missing.map((r) => r.symbol),
    ["OLD", "GAP"],
  );
  assert.equal(peerAverage([rows[0]], "AVGO").value, null);
  assert.equal(
    peerAverage([{ ...rows[0], end: null }, rows[1]], "AVGO").value,
    null,
  );
});
test("P/E reuses only matching permitted Finnhub references and averages usable peers", () => {
  const members = [
    { symbol: "AVGO", name: "Broadcom" },
    { symbol: "A", name: "A" },
    { symbol: "B", name: "B" },
    { symbol: "GAP", name: "Gap" },
  ];
  const ref = (symbol, value) => ({
    symbol,
    available: true,
    reference: {
      symbol,
      id: "saved-" + symbol,
      retrieved_at: "2026-10-09T00:00:00Z",
      metrics: { earnings: { value, field: "peTTM" } },
    },
  });
  const refs = [ref("AVGO", "46.611"), ref("A", "20"), ref("B", "80")];
  const rows = peRows(members, refs);
  assert.equal(rows[0].exact, "46.611");
  assert.equal(rows[0].identity, "saved-AVGO");
  assert.equal(rows[0].name, "Broadcom");
  assert.equal(peerAverage(rows, "AVGO").value, 50);
  assert.equal(peerAverage(rows, "AVGO").peers.length, 2);
  assert.match(position(rows, "AVGO").text, /above A; below B/);
  for (const change of [
    (r) => (r.available = false),
    (r) => (r.reference.symbol = "OTHER"),
    (r) => (r.reference.metrics.earnings.value = "0"),
    (r) => (r.reference.metrics.earnings.value = "-5"),
    (r) => (r.reference.metrics.earnings.value = "NaN"),
  ]) {
    const altered = structuredClone(refs);
    change(altered[0]);
    assert.equal(peRows(members, altered)[0].value, null);
  }
  assert.equal(
    peRows(
      [
        {
          ...members[0],
          ratios: {
            status: "saved",
            data: { period: "TTM", metrics: [{ key: "pe", value: "99" }] },
          },
        },
      ],
      [],
    )[0].value,
    null,
  );
});
