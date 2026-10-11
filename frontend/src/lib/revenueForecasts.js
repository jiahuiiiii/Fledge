import { day, metric, number } from "./financialStory.js";

const date = (value) =>
  typeof value === "string" &&
  /^\d{4}-\d{2}-\d{2}$/.test(value) &&
  Number.isFinite(Date.parse(value)) &&
  new Date(value).toISOString().slice(0, 10) === value
    ? Date.parse(value)
    : null;
const amount = (value) => {
  const n = typeof value === "boolean" ? null : number(value);
  return n != null && n >= 0 && n <= 1e15 ? n : null;
};
export const horizonLabel = (kind) =>
  kind === "annual"
    ? "Fiscal year"
    : kind === "quarter"
      ? "Quarter"
      : "Past 12 months";
export function forecastAmount(value, currency, approximate = false) {
  const n = amount(value);
  if (n == null) return "Unavailable";
  const divisor = n >= 1e12 ? 1e12 : n >= 1e9 ? 1e9 : n >= 1e6 ? 1e6 : 1;
  return `${approximate ? "≈ " : ""}${currency === "USD" ? "US$" : currency ? currency + " " : ""}${(n / divisor).toLocaleString("en-GB", { maximumFractionDigits: 2 })}${divisor === 1e12 ? "tn" : divisor === 1e9 ? "bn" : divisor === 1e6 ? "m" : ""}`;
}

function analystPoints(forecasts, metadata) {
  return (forecasts || []).flatMap((f) => {
    const revenue = f.metrics?.find((m) => m.key === "revenue");
    if (!revenue) return [];
    return [
      {
        ...metadata,
        id: `${metadata.source}:${f.period_type}:${f.period_end}`,
        kind: "analyst",
        periodKind: f.period_type,
        end: f.period_end,
        fiscalYear: f.fiscal_year,
        value: amount(revenue.average),
        low: amount(revenue.low),
        high: amount(revenue.high),
        currency: f.currency || null,
        basis: revenue.basis || "Source revenue definition",
        analysts: revenue.analysts,
        tableAnalysts: f.displayed_analyst_count,
        sourceDisplay: revenue.source_display,
        rangeAverage: revenue.range_average,
      },
    ];
  });
}
export function forecastSources(context, management) {
  const groups = [];
  const publicSource = context?.public_forecasts;
  const saved = publicSource?.available ? publicSource.snapshot : null;
  if (saved?.data)
    groups.push({
      key: "public",
      label: "Stock Analysis · S&P Global",
      points: analystPoints(saved.data.forecasts, {
        source: "public",
        sourceLabel: "Stock Analysis · S&P Global",
        url: saved.data.url,
        observedAt: saved.observed_at,
        updatedOn: saved.data.page_updated_on,
        stale: !!saved.stale,
        sourceError: publicSource.error,
        restrictedYears: saved.data.restricted_years || [],
      }),
    });
  const fmp = context?.consensus;
  if (fmp?.status === "saved" && fmp.data)
    groups.push({
      key: "fmp",
      label: "FMP",
      points: analystPoints(fmp.data.forecasts, {
        source: "fmp",
        sourceLabel: "FMP",
        observedAt: fmp.first_observed_at,
        checkedAt: fmp.checked_at,
        sourceError: fmp.message,
      }),
    });
  const guidance = [];
  // Only the current retained release may supply the forward outlook. Historical
  // releases stay accessible in Outlook and never replace withdrawn guidance.
  if (management?.status === "available")
    for (const release of management.releases || []) {
      if (!release.current) continue;
      for (const section of release.sections || []) {
        if (
          section.review_status ||
          section.truncated ||
          section.period_conflict
        )
          continue;
        for (const f of section.forecasts || []) {
          if (f.metric !== "revenue") continue;
          const low = amount(f.low),
            high = amount(f.high);
          guidance.push({
            id: `management:${release.id}:${section.id}:${f.id}`,
            kind: "management",
            source: "management",
            sourceLabel: "Management guidance",
            periodKind: section.period_type,
            end: section.period_end,
            value: low != null && high != null ? (low + high) / 2 : null,
            low,
            high,
            currency: f.unit || null,
            basis: f.basis || "Not specified in the guidance",
            approximate: !!f.approximate,
            quote: f.quote,
            context: [
              ...(section.context_evidence || []),
              ...(section.passages || []),
              ...(section.period_evidence || []).flatMap((e) => [
                e.heading,
                ...e.passages,
              ]),
            ],
            periodLabel: section.period_label,
            heading: section.heading,
            url: release.url,
            publishedAt:
              release.stated_release_date?.date || release.published_at,
            observedAt: release.available_at,
            sourceError: management.source_status?.last_error,
          });
        }
      }
    }
  return { groups, guidance };
}

export function quarterlyHistory(flow) {
  if (flow?.status !== "available") return [];
  const names = { net_result: "net_income", operating: "operating_income" };
  return (flow.periods || [])
    .filter((p) => p.kind === "quarter")
    .map((p) => ({
      ...p,
      metrics: (p.metrics || []).map((m) => ({
        ...m,
        key: names[m.key] || m.key,
      })),
    }))
    .sort((a, b) => Date.parse(a.end) - Date.parse(b.end));
}

// This is a visual comparison, not a guidance-versus-result verdict. A currency
// assumption is explicit, local to the chart and never written into source data.
export function chartForecasts(points, rows, kind, assumeUSD = false) {
  const last = rows.at(-1);
  const lastDate = date(last?.end);
  const plotted = [],
    excluded = [];
  const relevant = points.filter((p) => p.periodKind === kind);
  const counts = new Map();
  for (const p of relevant)
    counts.set(
      `${p.source}:${p.end}`,
      (counts.get(`${p.source}:${p.end}`) || 0) + 1,
    );
  for (const p of relevant) {
    let reason = "";
    if (kind === "trailing")
      reason =
        "Forecasts describe fiscal years or quarters, not a rolling year.";
    else if (date(p.end) == null) reason = "The forecast period is not clear.";
    else if (
      lastDate == null ||
      last.kind !== kind ||
      metric(last, "revenue")?.unit !== "USD"
    )
      reason = "Matching reported history is not available.";
    else if (date(p.end) <= lastDate) continue;
    else if (counts.get(`${p.source}:${p.end}`) > 1)
      reason = "This source has more than one estimate for this period.";
    else if (
      amount(p.value) == null ||
      amount(p.low) == null ||
      amount(p.high) == null ||
      p.low > p.value ||
      p.high < p.value
    )
      reason = "A complete, consistent revenue estimate is not available.";
    else if (p.currency && p.currency !== "USD")
      reason = `The forecast uses ${p.currency}; reported revenue uses USD.`;
    else if (!p.currency && !assumeUSD)
      reason = "The source does not state a currency.";
    const point = { ...p, assumedCurrency: !p.currency && assumeUSD };
    if (reason) excluded.push({ ...point, reason });
    else plotted.push(point);
  }
  return {
    plotted: plotted.sort((a, b) => date(a.end) - date(b.end)),
    excluded,
  };
}

export function forecastPath(points, lastReported, kind, x, y) {
  const limit = kind === "annual" ? [350, 380] : [70, 110];
  let previous =
    lastReported &&
    amount(metric(lastReported, "revenue")?.value) != null &&
    metric(lastReported, "revenue")?.unit === "USD"
      ? {
          ...lastReported,
          value: number(metric(lastReported, "revenue").value),
        }
      : null;
  let path = "";
  for (const point of points) {
    const gap = previous
      ? (date(point.end) - date(previous.end)) / 86400000
      : null;
    const adjacent = gap != null && gap >= limit[0] && gap <= limit[1];
    if (adjacent && !path) path += `M${x(previous)},${y(previous.value)} `;
    path += `${adjacent ? "L" : "M"}${x(point)},${y(point.value)} `;
    previous = point;
  }
  return path;
}

export function forecastTakeaway(point, rows) {
  const name =
    point.kind === "analyst" ? "Analysts estimate" : "Management guides to";
  const currency = point.assumedCurrency ? "USD" : point.currency;
  const value = forecastAmount(point.value, currency, point.approximate);
  const period = `${point.periodKind === "annual" ? "the fiscal year" : "the quarter"} ending ${day(point.end)}`;
  // Only an immediately preceding, complete period supports a growth sentence.
  const prior = rows.at(-1),
    revenue = metric(prior, "revenue"),
    gap = (date(point.end) - date(prior?.end)) / 86400000;
  const samePeriod =
    point.periodKind === "annual"
      ? gap >= 350 && gap <= 380
      : gap >= 70 && gap <= 110;
  if (
    point.currency === "USD" &&
    point.basis === "gaap" &&
    samePeriod &&
    number(revenue?.value) > 0
  ) {
    const change = (point.value / number(revenue.value) - 1) * 100;
    return `${name} ${value} for ${period}, ${Math.abs(change).toFixed(1)}% ${change >= 0 ? "above" : "below"} the last reported ${point.periodKind === "annual" ? "fiscal year" : "quarter"}.`;
  }
  return `${name} ${value} for ${period}${point.currency ? "." : point.assumedCurrency ? ", using your USD assumption." : "; currency is not stated."}`;
}
