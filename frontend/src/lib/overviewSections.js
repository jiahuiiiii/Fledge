import { originalSample } from "./originalSample.js";
import { sourceHeadline } from "./sourceHeadline.js";
import { day, money, newsTone } from "./companySnapshot.js";

export const number = (raw) => {
  if (raw == null || raw === "" || typeof raw === "boolean") return null;
  const value = Number(raw);
  return Number.isFinite(value) ? value : null;
};
export const ratio = (a, b) =>
  number(a) != null && number(b) > 0 ? number(a) / number(b) : null;
export const multiple = (value) =>
  value == null ? null : `${value.toFixed(2).replace(/0$/, "")}×`;

export function reportFigure(report, key) {
  const row = report?.metrics?.find((item) => item.key === key);
  if (
    !row ||
    row.end !== report.period_end ||
    row.unit !== (key === "revenue_growth" ? "percent" : "USD")
  )
    return null;
  const source = row.source_report || report;
  return {
    ...row,
    source_report: source,
    inputs: (row.inputs || []).map((input) => ({
      ...input,
      filing_url: input.filing_url || source.filing_url,
    })),
  };
}

export function businessMix(data) {
  const groups = data?.segment_revenue?.groups || [];
  const kind = ["Operating segments", "Products and services"].find((k) =>
    groups.some((g) => g.kind === k),
  );
  if (!kind) return [];
  // Compare two disclosed periods of the same axis, never add geographies or YTD to a quarter.
  return ["Quarter", "Annual"]
    .map(
      (period) =>
        groups
          .filter((g) => g.kind === kind && g.period === period)
          .sort((a, b) => b.end.localeCompare(a.end))[0],
    )
    .filter(Boolean);
}
export function segmentEvidence(group) {
  return (group?.members || []).map((row) => ({
    ...row,
    unit: "USD",
    start: group.start,
    end: group.end,
    inputs: (row.inputs || []).map((input) => ({
      ...input,
      start: group.start,
      end: group.end,
      form: group.form,
      filing_url: `${group.url}${input.fact_id ? `#${encodeURIComponent(input.fact_id)}` : ""}`,
    })),
  }));
}

export function currentGuidance(
  data,
  today = new Date().toISOString().slice(0, 10),
) {
  if (data?.status === "unavailable") return null;
  for (const release of data?.releases || []) {
    if (!release.current) continue;
    for (const section of release.sections || []) {
      if (
        section.review_status ||
        section.truncated ||
        !section.period_end ||
        section.period_end < today
      )
        continue;
      const forecast = section.forecasts?.find(
        (f) =>
          f.metric === "revenue" &&
          number(f.low) != null &&
          number(f.high ?? f.low) >= number(f.low),
      );
      if (forecast) return { ...forecast, release, section };
    }
  }
  return null;
}
export function guidanceAmount(guidance) {
  if (!guidance) return null;
  const format = (value) =>
    guidance.unit === "USD" ? money(value) : money(value)?.replace("US$", "$");
  const high = guidance.high ?? guidance.low;
  return `${guidance.approximate ? "≈ " : ""}${format(guidance.low)}${number(high) !== number(guidance.low) ? `–${format(high)}` : ""}`;
}

export function overviewNews(data) {
  // Current permitted sources remain readable even when an older complete AI packet is withheld.
  const sources = data.sentiment_inputs
    ? originalSample(data.sentiment_inputs, "all")
    : originalSample(data.sentiment, "all");
  const saved = data.sentiment?.withheld
    ? []
    : originalSample(data.sentiment, "all");
  const items = data.sentiment?.withheld ? [] : data.sentiment?.items || [];
  return sources.map((source) => {
    const exact = saved.find(
      (s) =>
        s.id === source.id &&
        s.body === source.body &&
        s.title === source.title &&
        s.published_at === source.published_at,
    );
    const item = exact && items.find((i) => i.source_id === source.id);
    return {
      ...source,
      headline:
        sourceHeadline(source) ||
        source.body?.trim().slice(0, 160) ||
        "Source text unavailable",
      tone: item?.relevance === "relevant" ? item.sentiment : null,
      analysisLabel: item
        ? item.relevance === "relevant"
          ? item.sentiment
          : "Outside company focus"
        : "Not analysed",
    };
  });
}

export function overviewModel(data, reads = {}) {
  const depth =
    data.financial_depth?.status === "available" ? data.financial_depth : null;
  const reports =
    data.performance?.status === "available"
      ? data.performance.reports || {}
      : {};
  const annual = reports.annual;
  const latest = Object.values(reports)
    .filter(Boolean)
    .sort((a, b) => b.period_end.localeCompare(a.period_end))[0];
  const revenue = reportFigure(annual, "revenue");
  const growth = reportFigure(annual, "revenue_growth");
  const trailing = (key) =>
    depth?.trailing?.find((row) => row.key === key) || null;
  const quarter = (data.income_flow?.periods || [])
    .filter((p) => p.kind === "quarter")
    .sort((a, b) => b.end.localeCompare(a.end))[0];
  const quarterMetric = quarter?.metrics.find((row) => row.key === "revenue");
  const quarterRevenue = quarterMetric
    ? { ...quarterMetric, unit: "USD", start: quarter.start, end: quarter.end }
    : null;
  const assets = reportFigure(latest, "assets"),
    liabilities = reportFigure(latest, "liabilities"),
    cash = reportFigure(latest, "cash");
  const debt = depth?.debt;
  const expectedAccession = debt?.source_report?.accession || latest?.accession;
  const borrowing =
    latest?.accession &&
    expectedAccession &&
    debt?.unit === "USD" &&
    debt.start == null &&
    debt.end === latest?.period_end &&
    debt.inputs?.length &&
    debt.inputs.every(
      (i) =>
        i.unit === "USD" &&
        i.start == null &&
        i.end === latest.period_end &&
        i.accession === expectedAccession,
    )
      ? debt
      : null;
  const briefCandidate = reads.business?.current || reads.business?.latest;
  const brief = !briefCandidate?.withheld ? briefCandidate : null;
  const referenceEntry = reads.valuation?.references?.find(
    (r) => r.symbol === data.instrument?.symbol,
  );
  const reference =
    referenceEntry?.available &&
    referenceEntry.reference?.symbol === data.instrument?.symbol
      ? referenceEntry.reference
      : null;
  const positiveMultiple = (key) =>
    number(reference?.metrics?.[key]?.value) > 0
      ? number(reference.metrics[key].value)
      : null;
  const consensus = reads.fmp?.consensus;
  const forecasts = !!(
    (consensus?.status === "saved" && consensus.data?.forecasts?.length) ||
    (reads.fmp?.public_forecasts?.available &&
      reads.fmp.public_forecasts.snapshot?.data?.forecasts?.length)
  );
  return {
    annual,
    quarterRevenue,
    latest,
    revenue,
    growth,
    trailingRevenue: trailing("revenue"),
    margin: trailing("operating_margin"),
    freeCash: trailing("free_cash_flow"),
    assets,
    liabilities,
    cash,
    borrowing,
    assetsRatio: ratio(assets?.value, liabilities?.value),
    cashRatio: ratio(cash?.value, borrowing?.value),
    mix: businessMix(data),
    guidance: currentGuidance(data.management_outlook),
    brief,
    olderBrief: !!reads.business?.sample_changed,
    tone: newsTone(data.sentiment),
    headlines: overviewNews(data),
    reference,
    pe: positiveMultiple("earnings"),
    ps: positiveMultiple("sales"),
    forecasts,
    peers: reads.fmp?.selected || [],
    scenarios: reads.valuation?.saved || [],
  };
}

export const yearLabel = (row) =>
  row?.end ? `Fiscal year ended ${day(row.end)}` : "Fiscal year unavailable";
