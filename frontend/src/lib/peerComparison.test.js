import test from "node:test";
import assert from "node:assert/strict";
import { peerMetrics, peerRows, peerScale } from "./peerComparison.js";

const metric = (id) => peerMetrics.find((item) => item.id === id);
const member = (value = "30") => ({
  symbol: "EXMP",
  rationale: "Authored comparison reason",
  saved_finnhub: {
    id: "original-finnhub",
    retrieved_at: "2026-10-08T10:00:00Z",
    metrics: { earnings: { value, field: "peTTM" } },
  },
  ratios: {
    status: "saved",
    snapshot_id: "other-provider",
    first_observed_at: "2026-10-07T12:00:00Z",
    data: {
      period: "TTM",
      metrics: [{ key: "pe", value: "99", field: "priceToEarningsRatioTTM" }],
    },
  },
});
const financial = (value, unit = "USD") => ({
  symbol: "EXMP",
  financials: {
    status: "available",
    method: "sec-financial-depth-1",
    payload_id: "original-filing-payload",
    first_recorded_at: "2026-10-01T00:00:00Z",
    trailing: [
      {
        key: "free_cash_flow",
        value,
        unit,
        start: "2025-07-01",
        end: "2026-06-30",
        formula: "Cash flow less cash capital spending",
        inputs: [{ concept: "CapitalSpending", value: "3", unit: "USD" }],
      },
    ],
  },
});

test("peer sources keep their own value, identity and date without fallback", () => {
  const item = member(null);
  let [row] = peerRows([item], metric("pe_finnhub"));
  assert.equal(row.value, null);
  assert.equal(row.identity, "original-finnhub");
  [row] = peerRows([item], metric("pe_fmp"));
  assert.equal(row.exact, "99");
  assert.equal(row.identity, "other-provider");
  assert.equal(row.observed, "2026-10-07T12:00:00Z");
});

test("invalid or nonpositive multiples stay unavailable; decimals remain exact", () => {
  for (const value of [null, "", true, "NaN", "Infinity", "0", "-4"])
    assert.equal(
      peerRows([member(value)], metric("pe_finnhub"))[0].value,
      null,
    );
  assert.equal(
    peerRows([member("29.375")], metric("pe_finnhub"))[0].exact,
    "29.375",
  );
});

test("withheld FMP source and non-TTM payload do not leak a retained ratio", () => {
  const item = member();
  item.ratios.status = "withheld";
  assert.equal(peerRows([item], metric("pe_fmp"))[0].value, null);
  item.ratios.status = "saved";
  item.ratios.data.period = "forward";
  assert.equal(peerRows([item], metric("pe_fmp"))[0].value, null);
});

test("SEC figures require the existing method, matching unit, dates and evidence", () => {
  for (const change of [
    "method",
    "currency",
    "dates",
    "inputs",
    "permission",
  ]) {
    const item = financial("8");
    if (change === "method") item.financials.method = "unknown";
    if (change === "currency") item.financials.trailing[0].unit = "EUR";
    if (change === "dates") item.financials.trailing[0].start = null;
    if (change === "inputs") item.financials.trailing[0].inputs = [];
    if (change === "permission") item.financials.status = "unavailable";
    assert.equal(peerRows([item], metric("fcf_sec"))[0].value, null, change);
  }
});

test("zero and negative cash remain visible on a shared signed scale in original company order", () => {
  const rows = peerRows(
    [
      financial("-6"),
      { ...financial("0"), symbol: "ZERO" },
      { ...financial("40"), symbol: "LAST" },
    ],
    metric("fcf_sec"),
  );
  assert.deepEqual(
    rows.map((row) => row.value),
    [-6, 0, 40],
  );
  assert.deepEqual(
    rows.map((row) => row.symbol),
    ["EXMP", "ZERO", "LAST"],
  );
  assert.deepEqual(peerScale(rows), { low: -6, high: 40, span: 46 });
  assert.equal(rows[0].identity, "original-filing-payload");
});

test("an incomplete total borrowing figure is never substituted with other inputs", () => {
  const item = financial("20");
  item.financials.debt = {
    key: "total_debt",
    value: null,
    unit: "USD",
    end: "2026-06-30",
    start: null,
    inputs: [{ value: "8", concept: "LongTermDebt" }],
    reason: "A current component is missing.",
  };
  const [row] = peerRows([item], metric("debt_sec"));
  assert.equal(row.value, null);
  assert.equal(row.reason, "A current component is missing.");
});

const growth = (value = "-12.5000") => ({
  symbol: "GROWTH",
  annual_growth: {
    status: "available",
    method: "sec-performance-1",
    snapshot_id: "performance-original",
    payload_id: "payload-original",
    first_recorded_at: "2026-10-01T00:00:00Z",
    report: {
      period_type: "annual",
      form: "10-K",
      period_end: "2025-09-30",
      accession: "filing-original",
      filing_url: "https://www.sec.gov/Archives/example.htm",
    },
    metric: {
      key: "revenue_growth",
      value,
      unit: "percent",
      start: "2024-10-01",
      end: "2025-09-30",
      inputs: [
        {
          value: "70",
          unit: "USD",
          start: "2024-10-01",
          end: "2025-09-30",
          accession: "filing-original",
        },
        {
          value: "80",
          unit: "USD",
          start: "2023-10-01",
          end: "2024-09-30",
          accession: "filing-original",
        },
      ],
    },
  },
});

test("annual growth retains negative/zero values, exact decimals, both periods and original identities", () => {
  const rows = peerRows([growth(), growth("0")], metric("growth_sec"));
  assert.deepEqual(
    rows.map((row) => row.value),
    [-12.5, 0],
  );
  assert.equal(rows[0].exact, "-12.5000");
  assert.equal(rows[0].identity, "performance-original");
  assert.equal(rows[0].payloadIdentity, "payload-original");
  assert.equal(rows[0].priorStart, "2023-10-01");
  assert.equal(rows[0].priorEnd, "2024-09-30");
  assert.match(rows[0].inputs[1].filing_url, /sec.gov\/Archives/);
});

test("annual growth rejects quarterly, withdrawn, missing or mismatched evidence without fallback", () => {
  for (const mutate of [
    (item) => {
      item.annual_growth.status = "unavailable";
    },
    (item) => {
      item.annual_growth.method = "other-method";
    },
    (item) => {
      item.annual_growth.report.period_type = "quarter";
    },
    (item) => {
      item.annual_growth.report.form = "10-Q";
    },
    (item) => {
      item.annual_growth.metric.inputs.pop();
    },
    (item) => {
      item.annual_growth.metric.inputs[1].accession = "other-filing";
    },
    (item) => {
      item.annual_growth.metric.inputs[1].unit = "EUR";
    },
    (item) => {
      item.annual_growth.metric.end = "2025-12-31";
    },
    (item) => {
      item.annual_growth.metric.value = null;
    },
  ]) {
    const item = growth();
    mutate(item);
    assert.equal(peerRows([item], metric("growth_sec"))[0].value, null);
  }
});
