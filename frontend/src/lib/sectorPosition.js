// Compare retained figures within one source, measure and fiscal-period kind.
import { number, metric } from "./financialStory.js";
import { peerMetrics, peerRows } from "./peerComparison.js";
const numeric = (raw) =>
  typeof raw === "number" ||
  (typeof raw === "string" && /^-?\d+(?:\.\d+)?$/.test(raw))
    ? number(raw)
    : null;
const days = (a, b) => (Date.parse(a) - Date.parse(b)) / 86400000;
const revenueTags = [
  "RevenueFromContractWithCustomerExcludingAssessedTax",
  "Revenues",
  "SalesRevenueNet",
];
export const measures = [
  {
    key: "pe",
    label: "Price / earnings (P/E)",
    question: "How does its P/E compare with peers?",
    unit: "multiple",
    source: "Finnhub · trailing 12 months",
  },
  {
    key: "revenue_growth",
    label: "Revenue growth · fiscal year",
    question: "Who is growing faster?",
    unit: "percent",
  },
  {
    key: "operating_margin",
    label: "Operating margin",
    question: "Who keeps more of its sales as operating profit?",
    unit: "percent",
  },
  {
    key: "revenue",
    label: "Revenue",
    question: "How large is each business?",
    unit: "USD",
  },
];
export function peRows(members, references = []) {
  const metric = peerMetrics.find((item) => item.id === "pe_finnhub");
  return members.map((member) => {
    const entry = references.find((item) => item.symbol === member.symbol);
    const reference =
      entry?.available && entry.reference?.symbol === member.symbol
        ? entry.reference
        : null;
    const [row] = peerRows([{ ...member, saved_finnhub: reference }], metric);
    return { ...row, name: member.name, source: "Finnhub" };
  });
}
export function comparisonExclusion(row, own) {
  if (row === own) return null;
  if (row.value == null)
    return row.reason || "A usable saved figure is unavailable.";
  if (row.unit === "multiple")
    return row.source === "Finnhub" && row.value > 0
      ? null
      : "A usable saved Finnhub P/E is unavailable.";
  if (!own?.end || !Number.isFinite(Date.parse(own.end)))
    return "The researched company’s fiscal year end is unavailable.";
  if (!row.end || !Number.isFinite(Date.parse(row.end)))
    return "This company’s fiscal year end is unavailable.";
  const gap = Math.abs(days(row.end, own.end));
  return gap <= 120
    ? null
    : `Fiscal year ends are ${gap} days apart (120-day limit).`;
}
export function comparablePeers(rows, symbol) {
  const own = rows.find((row) => row.symbol === symbol);
  return rows.filter(
    (row) => row.symbol !== symbol && !comparisonExclusion(row, own),
  );
}
export function comparisonRows(rows, symbol) {
  const peers = comparablePeers(rows, symbol);
  return rows.filter((row) => row.symbol === symbol || peers.includes(row));
}
export function peerAverage(rows, symbol) {
  const peers = comparablePeers(rows, symbol);
  return {
    value: peers.length
      ? peers.reduce((sum, row) => sum + row.value, 0) / peers.length
      : null,
    peers,
    missing: rows.filter(
      (row) => row.symbol !== symbol && !peers.includes(row),
    ),
  };
}
export function reportedRow(member, key) {
  const source = member.performance,
    latest = source?.reports?.annual;
  const row = metric(latest, key),
    inputs = row?.inputs || [];
  const report = row?.source_report || latest;
  const value = numeric(row?.value),
    duration = days(row?.end, row?.start) + 1;
  const valid =
    source?.status === "available" &&
    source.method === "sec-performance-1" &&
    report?.period_type === "annual" &&
    /^10-K(?:\/A)?$/.test(report.form) &&
    row?.end === report.period_end &&
    duration >= 350 &&
    duration <= 380 &&
    row.unit === (key === "revenue" ? "USD" : "percent") &&
    value != null &&
    inputs.length === (key === "revenue" ? 1 : 2) &&
    inputs.every(
      (i) =>
        i.namespace === "us-gaap" &&
        i.unit === "USD" &&
        i.accession === report.accession &&
        numeric(i.value) != null,
    ) &&
    inputs[0].start === row.start &&
    inputs[0].end === row.end &&
    (key === "revenue_growth"
      ? revenueTags.includes(inputs[0].concept) &&
        revenueTags.includes(inputs[1].concept) &&
        inputs[1].end < inputs[0].start &&
        numeric(inputs[1].value) > 0
      : key === "operating_margin"
        ? inputs[0].concept === "OperatingIncomeLoss" &&
          revenueTags.includes(inputs[1].concept) &&
          inputs[1].start === row.start &&
          inputs[1].end === row.end &&
          numeric(inputs[1].value) > 0
        : revenueTags.includes(inputs[0].concept));
  return {
    symbol: member.symbol,
    name: member.name,
    value: valid ? value : null,
    exact: valid ? row.value : null,
    unit: key === "revenue" ? "USD" : "percent",
    start: row?.start,
    end: report?.period_end,
    row,
    inputs: valid ? inputs : [],
    report,
    filingResolution: row?.filing_resolution,
    reason: valid
      ? null
      : row?.reason ||
        source?.reason ||
        "A compatible saved annual filing is unavailable.",
    observed: source?.first_recorded_at,
  };
}
export function forecastRow(member, year, now) {
  const source = member.consensus;
  const forecasts =
    source?.status === "saved" && source.data?.method === "fmp-research-1"
      ? source.data.forecasts || []
      : [];
  const forecast = forecasts.find(
    (f) =>
      f.period_type === "annual" &&
      f.period_end?.slice(0, 4) === year &&
      f.period_end >= now,
  );
  const prior = forecasts.find(
    (f) =>
      f.period_type === "annual" &&
      days(forecast?.period_end, f.period_end) >= 350 &&
      days(forecast?.period_end, f.period_end) <= 380,
  );
  const current = forecast?.metrics?.find((m) => m.key === "revenue"),
    baseline = prior?.metrics?.find((m) => m.key === "revenue");
  const average = numeric(current?.average),
    previous = numeric(baseline?.average);
  const valid =
    forecast?.currency === "USD" &&
    prior?.currency === "USD" &&
    average != null &&
    average >= 0 &&
    previous != null &&
    previous > 0;
  return {
    symbol: member.symbol,
    name: member.name,
    unit: "percent",
    value: valid ? (average / previous - 1) * 100 : null,
    end: forecast?.period_end,
    start: null,
    priorEnd: prior?.period_end,
    observed: source?.first_observed_at,
    sourceId: source?.snapshot_id,
    forecast,
    prior,
    current,
    baseline,
    reason: valid
      ? null
      : source?.message ||
        (!forecast
          ? "No saved FMP annual revenue forecast for this year."
          : !prior
            ? "A preceding annual forecast is missing."
            : forecast.currency !== "USD" || prior.currency !== "USD"
              ? "Forecast currency is not explicitly USD in both years."
              : "Positive prior-year and nonnegative current-year revenue estimates are required."),
  };
}
export function yearsFor(members, now) {
  return [
    ...new Set(
      members.flatMap((m) =>
        m.consensus?.status === "saved"
          ? (m.consensus.data?.forecasts || [])
              .filter((f) => f.period_type === "annual" && f.period_end >= now)
              .map((f) => f.period_end.slice(0, 4))
          : [],
      ),
    ),
  ].sort();
}
export function position(rows, symbol) {
  const own = rows.find((r) => r.symbol === symbol);
  if (own?.value == null)
    return {
      text: "The company’s comparable figure is unavailable.",
      coverage: 0,
    };
  const peers = comparablePeers(rows, symbol);
  if (!peers.length)
    return {
      text:
        own.unit === "multiple"
          ? "No peer with a usable saved Finnhub P/E is available."
          : "No peer with a usable figure and fiscal end within 120 days is available.",
      coverage: 0,
    };
  const above = peers.filter((r) => own.value > r.value),
    below = peers.filter((r) => own.value < r.value),
    equal = peers.filter((r) => own.value === r.value);
  const clauses = [];
  const names = (items) =>
    new Intl.ListFormat("en-GB").format(items.map((r) => r.symbol));
  if (above.length) clauses.push(`above ${names(above)}`);
  if (below.length) clauses.push(`below ${names(below)}`);
  if (equal.length) clauses.push(`equal to ${names(equal)}`);
  const values = peers.map((r) => r.value).sort((a, b) => a - b),
    mid = Math.floor(values.length / 2);
  const median =
    values.length % 2 ? values[mid] : (values[mid - 1] + values[mid]) / 2;
  return {
    text: `${symbol} is ${clauses.join("; ")}.`,
    coverage: peers.length,
    median,
    difference: own.value - median,
    complete: peers.length === rows.length - 1,
  };
}
export function scale(rows) {
  const values = rows.map((r) => r.value).filter((v) => v != null);
  const low = Math.min(0, ...values),
    high = Math.max(0, ...values);
  return { low, high: high === low ? low + 1 : high, span: high - low || 1 };
}
export function managementRows(
  members,
  now = new Date().toISOString().slice(0, 10),
) {
  return members.map((member) => {
    const release =
      member.management?.status === "available"
        ? member.management.releases?.find((r) => r.current)
        : null;
    const section = release?.sections?.find(
      (s) =>
        s.period_type === "quarter" &&
        s.period_end >= now &&
        !s.review_status &&
        !s.truncated,
    );
    const margin = section?.forecasts?.find(
      (f) => f.metric === "operating_margin",
    );
    return { symbol: member.symbol, section, release, margin };
  });
}
