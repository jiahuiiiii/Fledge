// Presentation of existing source-scoped figures only. No provider fallback,
// cross-vendor blending, new financial calculation or investment ranking.
export const peerMetrics = [
  {
    id: "pe_finnhub",
    label: "P/E · Finnhub",
    source: "Finnhub",
    key: "earnings",
    unit: "multiple",
    explanation:
      "Price relative to the last twelve months of earnings, as reported by Finnhub. A lower multiple can reflect weaker expected growth or greater risk; it does not establish a bargain.",
  },
  {
    id: "ps_finnhub",
    label: "P/S · Finnhub",
    source: "Finnhub",
    key: "sales",
    unit: "multiple",
    explanation:
      "Price relative to the last twelve months of sales, as reported by Finnhub. Sales do not measure profit, and businesses with different margins can deserve different multiples.",
  },
  {
    id: "pe_fmp",
    label: "P/E · FMP",
    source: "FMP",
    key: "pe",
    unit: "multiple",
    explanation:
      "FMP’s trailing price-to-earnings multiple. Its response does not establish a GAAP or adjusted-earnings convention. Keep this separate from Finnhub and forward estimates.",
  },
  {
    id: "ps_fmp",
    label: "P/S · FMP",
    source: "FMP",
    key: "ps",
    unit: "multiple",
    explanation:
      "FMP’s trailing price-to-sales multiple. Revenue recognition, growth and profitability can differ between companies. Keep this separate from Finnhub references.",
  },
  {
    id: "revenue_sec",
    label: "Trailing revenue · SEC",
    source: "SEC",
    key: "revenue",
    unit: "USD",
    explanation:
      "Whole-company revenue over each company’s explicit trailing fiscal dates. Different fiscal year ends and business mix can limit comparison.",
  },
  {
    id: "growth_sec",
    label: "Annual revenue growth · SEC",
    source: "SEC",
    key: "revenue_growth",
    unit: "percent",
    explanation:
      "How much whole-company annual revenue changed from the prior fiscal year, using compatible reported USD inputs from the same filing. This is reported growth, including acquisitions and currency effects; it is not organic growth or a forecast.",
  },
  {
    id: "margin_sec",
    label: "Trailing operating margin · SEC",
    source: "SEC",
    key: "operating_margin",
    unit: "percent",
    explanation:
      "Operating income divided by revenue for the displayed trailing dates, calculated from compatible reported SEC inputs. This is not an adjusted margin.",
  },
  {
    id: "fcf_sec",
    label: "Trailing free cash flow · SEC",
    source: "SEC",
    key: "free_cash_flow",
    unit: "USD",
    explanation:
      "Operating cash flow less cash capital spending over the displayed trailing dates. Reported spending may include software and intangible assets; inspect each company’s definition. Noncash additions are excluded and company-defined free cash flow can differ.",
  },
  {
    id: "debt_sec",
    label: "Borrowing at period end · SEC",
    source: "SEC",
    key: "total_debt",
    unit: "USD",
    explanation:
      "The complete borrowing figure supported by saved SEC inputs, at each company’s balance date. It is separate from total liabilities and is not a debt-to-cash-flow ratio.",
  },
];

const numeric = (raw) => {
  if (typeof raw !== "string" && typeof raw !== "number") return null;
  if (typeof raw === "string" && !/^-?\d+(?:\.\d+)?$/.test(raw)) return null;
  const value = Number(raw);
  return Number.isFinite(value) ? value : null;
};

export function peerRows(members, metric) {
  return members.map((member) => {
    const common = {
      symbol: member.symbol,
      rationale: member.rationale,
      name: member.profile?.data?.name || member.symbol,
      industry: member.profile?.data?.industry || null,
      classificationDate: member.profile?.first_observed_at || null,
      value: null,
      exact: null,
      unit: metric.unit,
      reason: null,
      inputs: [],
      start: null,
      end: null,
      observed: null,
      checked: null,
      identity: null,
    };
    if (metric.source === "Finnhub") {
      const reference = member.saved_finnhub,
        row = reference?.metrics?.[metric.key];
      const value = numeric(row?.value);
      return {
        ...common,
        value: value != null && value > 0 ? value : null,
        exact: value != null && value > 0 ? String(row.value) : null,
        reason:
          value != null && value > 0
            ? null
            : row?.reason || "No usable saved Finnhub multiple is available.",
        observed: reference?.retrieved_at,
        identity: reference?.id,
        field: row?.field,
        basis:
          "Finnhub vendor TTM definition. The underlying earnings convention, quote time and fiscal dates are not established by this saved response.",
      };
    }
    if (metric.source === "FMP") {
      const source = member.ratios;
      const data =
        source?.status === "saved" && source.data?.period === "TTM"
          ? source.data
          : null;
      const row = data?.metrics?.find((item) => item.key === metric.key);
      const value = numeric(row?.value);
      return {
        ...common,
        value: value != null && value > 0 ? value : null,
        exact: value != null && value > 0 ? String(row.value) : null,
        reason:
          value != null && value > 0
            ? null
            : row?.reason ||
              source?.message ||
              "No usable saved FMP multiple is available.",
        observed: source?.first_observed_at,
        checked: source?.checked_at,
        identity: source?.snapshot_id,
        field: row?.field,
        sourceError: source?.message,
        basis:
          data?.basis ||
          "FMP vendor TTM definition. Underlying quote and fiscal dates are not established.",
      };
    }
    if (metric.key === "revenue_growth") {
      const source = member.annual_growth;
      const projected =
        ["sec-amendment-resolution-1", "sec-amendment-resolution-2"].includes(
          source?.projection_method,
        ) && source.based_on_snapshot_id;
      const identity = projected ? source.projection_id : source?.snapshot_id;
      const report = source?.report;
      const row = source?.metric;
      const inputs = row?.inputs || [];
      const value = numeric(row?.value);
      const valid =
        source?.status === "available" &&
        source.method === "sec-performance-1" &&
        identity &&
        report?.period_type === "annual" &&
        /^10-K(?:\/A)?$/.test(report.form) &&
        row?.key === "revenue_growth" &&
        row.unit === "percent" &&
        row.start &&
        row.end === report.period_end &&
        inputs.length === 2 &&
        inputs.every(
          (input) =>
            input.unit === "USD" &&
            input.start &&
            input.end &&
            input.accession === report.accession,
        ) &&
        inputs[0].start === row.start &&
        inputs[0].end === row.end &&
        inputs[1].end < inputs[0].start &&
        value != null;
      return {
        ...common,
        value: valid ? value : null,
        exact: valid ? String(row.value) : null,
        reason: valid
          ? null
          : row?.reason ||
            source?.reason ||
            "Compatible annual revenue and prior-year inputs are unavailable. Quarterly or trailing growth is not substituted.",
        start: row?.start,
        end: row?.end,
        priorStart: valid ? inputs[1].start : null,
        priorEnd: valid ? inputs[1].end : null,
        observed: source?.first_recorded_at,
        checked: source?.checked_at,
        identity,
        projected: !!projected,
        baseIdentity: source?.based_on_snapshot_id,
        payloadIdentity: source?.payload_id,
        filingResolution: row?.filing_resolution,
        inputs: inputs.map((input) => ({
          ...input,
          filing_url: input.filing_url || report?.filing_url,
        })),
        formula: row?.formula,
        basis: metric.explanation,
      };
    }
    const source = member.financials;
    const data =
      source?.status === "available" &&
      ["sec-financial-depth-1", "sec-financial-depth-2"].includes(source.method)
        ? source
        : null;
    const row =
      metric.key === "total_debt"
        ? data?.debt
        : data?.trailing?.find((item) => item.key === metric.key);
    const value = numeric(row?.value);
    const dated =
      row?.end && (metric.key === "total_debt" ? row.start == null : row.start);
    const valid =
      value != null &&
      row.unit === metric.unit &&
      dated &&
      row.inputs?.length > 0;
    return {
      ...common,
      value: valid ? value : null,
      exact: valid ? String(row.value) : null,
      reason: valid
        ? null
        : row?.reason ||
          source?.reason ||
          "Compatible saved financial inputs and fiscal dates are unavailable. Collect this company’s filings to add them.",
      start: row?.start,
      end: row?.end,
      observed: source?.first_recorded_at,
      checked: source?.checked_at,
      identity: source?.payload_id,
      inputs: row?.inputs || [],
      formula: row?.formula,
      basis: row?.explanation,
      filingResolution: row?.filing_resolution,
      sourceError: source?.reason,
    };
  });
}

export function peerScale(rows) {
  const values = rows
    .map((row) => row.value)
    .filter((value) => value != null && Number.isFinite(value));
  const low = Math.min(0, ...values),
    high = Math.max(0, ...values);
  return { low, high, span: high - low || 1 };
}
