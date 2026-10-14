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
        (!section.period_end && !section.period_label) ||
        (section.period_end && section.period_end < today)
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
export function guidanceReason(
  data,
  today = new Date().toISOString().slice(0, 10),
) {
  if (data?.status === "unavailable")
    return data.message || "Original earnings releases are unavailable.";
  const current = currentGuidance(data, today);
  if (current)
    return current.section.period_end
      ? null
      : "The release names the forecast period but does not state its exact ending date.";
  const dated = (data?.releases || [])
    .filter((r) => r.current)
    .flatMap((r) => r.sections || [])
    .filter(
      (s) =>
        !s.review_status &&
        !s.truncated &&
        s.forecasts?.some((f) => f.metric === "revenue"),
    );
  if (dated.length && dated.every((s) => s.period_end && s.period_end < today))
    return "The latest saved revenue guidance covers a period that has ended. Read it in Management outlook.";
  return (
    data?.availability?.message ||
    "No current earnings release is saved. Use Update data to collect it."
  );
}
export function guidanceStatusLabel(data) {
  return (
    {
      not_in_release: "No forecast in release",
      expired: "Period ended",
      release_missing: "Release missing",
      collection_failed: "Source check failed",
      source_unavailable: "Source unavailable",
      extraction_failed: "Could not read release",
      unsupported_format: "Format needs review",
      growth_only: "Growth rate only",
      needs_review: "Needs review",
    }[data?.availability?.code] || "See explanation"
  );
}
export function guidancePeriod(section) {
  if (section.period_end)
    return `the ${section.period_type === "annual" ? "fiscal year" : "quarter"} ending ${day(section.period_end)}`;
  return section.period_label || "a period whose date was not stated";
}

export function guidanceAmount(guidance) {
  if (!guidance) return null;
  const format = (value) =>
    guidance.unit === "USD" ? money(value) : money(value)?.replace("US$", "$");
  const high = guidance.high ?? guidance.low;
  return `${guidance.approximate ? "≈ " : ""}${format(guidance.low)}${number(high) !== number(guidance.low) ? `–${format(high)}` : ""}`;
}

export const guidanceScope = (section) =>
  section?.period_type === "annual"
    ? "full fiscal year"
    : section?.period_type === "quarter"
      ? "one quarter"
      : null;

const DAY = 86400000;
const daysBetween = (a, b) => (Date.parse(b) - Date.parse(a)) / DAY;
const nextDay = (value) =>
  new Date(Date.parse(value) + DAY).toISOString().slice(0, 10);
// Two reports cover the same period a year apart when their ends are about a
// year apart (52/53-week fiscal calendars move the end by a few days).
const yearApart = (earlier, later) => {
  const gap = daysBetween(earlier, later);
  return gap >= 354 && gap <= 375;
};
const growthRange = (low, high, base) =>
  number(base) > 0 && number(low) != null
    ? [
        (number(low) / number(base) - 1) * 100,
        (number(high ?? low) / number(base) - 1) * 100,
      ]
    : null;

// Fiscal quarter number from the company's own annual report boundaries; a
// quarter after the latest saved fiscal year counts from the day after it.
export function fiscalQuarter(period, annuals) {
  const containing = annuals.find(
    (a) => a.start && a.start <= period.start && period.end <= a.end,
  );
  const previous = annuals
    .filter((a) => a.end < period.start)
    .sort((a, b) => b.end.localeCompare(a.end))[0];
  const start = containing?.start || (previous && nextDay(previous.end));
  if (!start) return null;
  const elapsed = daysBetween(start, period.end) + 1;
  if (elapsed < 80 || elapsed > 375) return null;
  return Math.min(4, Math.max(1, Math.round(elapsed / 91.3)));
}

// Direct three-month quarters and fiscal years from the saved income
// statements, each compared only with a report covering the same period a year
// earlier. Outlook growth is code arithmetic on the release's own amounts.
export function revenueComparisons(data, guidance) {
  const periods = data?.income_flow?.periods || [];
  const revenueRows = (kind, minimum, maximum) =>
    periods
      .filter((p) => p.kind === kind && p.start && p.end)
      .map((p) => {
        const row = p.metrics?.find((r) => r.key === "revenue");
        const length = daysBetween(p.start, p.end) + 1;
        return row &&
          number(row.value) > 0 &&
          length >= minimum &&
          length <= maximum
          ? { ...row, unit: "USD", start: p.start, end: p.end }
          : null;
      })
      .filter(Boolean)
      .sort((a, b) => b.end.localeCompare(a.end));
  const quarters = revenueRows("quarter", 80, 100);
  const annuals = revenueRows("annual", 357, 375);
  const latest = quarters[0] || null;
  const latestYearAgo =
    latest && quarters.find((q) => yearApart(q.end, latest.end));
  const latestQuarter = latest &&
    latestYearAgo && {
      current: latest,
      previous: latestYearAgo,
      growth: growthRange(latest.value, latest.value, latestYearAgo.value)[0],
    };
  const section = guidance?.section;
  // A stated currency other than USD cannot be compared with USD results.
  const comparable = guidance && (!guidance.unit || guidance.unit === "USD");
  let outlook = null;
  if (comparable && section?.period_type === "quarter") {
    const target = Number(
      section.quarter || section.period_label?.match(/Q([1-4])/)?.[1],
    );
    const released = (
      guidance.release?.stated_release_date?.date ||
      guidance.release?.published_at ||
      ""
    ).slice(0, 10);
    const previous = section.period_end
      ? quarters.find((q) => yearApart(q.end, section.period_end))
      : target && released
        ? // The latest reported instance of this fiscal quarter before the
          // release, within the preceding fiscal year.
          quarters.find(
            (q) =>
              q.end < released &&
              daysBetween(q.end, released) <= 400 &&
              fiscalQuarter(q, annuals) === target,
          )
        : null;
    if (previous)
      outlook = {
        previous,
        growth: growthRange(guidance.low, guidance.high, previous.value),
      };
  } else if (
    comparable &&
    section?.period_type === "annual" &&
    section.period_end
  ) {
    const previous = annuals.find((a) => yearApart(a.end, section.period_end));
    if (previous)
      outlook = {
        previous,
        growth: growthRange(guidance.low, guidance.high, previous.value),
      };
  }
  return { latestQuarter, outlook };
}

export const signedPercent = (value) =>
  value == null
    ? null
    : `${value > 0 ? "+" : value < 0 ? "−" : ""}${Math.abs(value).toFixed(1)}%`;
export const growthText = (range) =>
  !range
    ? null
    : Math.abs(range[0] - range[1]) < 0.05
      ? signedPercent(range[0])
      : `${signedPercent(range[0])} to ${signedPercent(range[1])}`;

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

// Overview previews skip abusive and very short untitled social posts. The full
// source list on News & discussion still shows every saved original.
const ABUSIVE =
  /\b(bitch(es|y)?|fuck\w*|shit(s|ty|head)?|cunts?|retard(s|ed)?|dickheads?|assholes?|bastards?|whores?|sluts?)\b/i;
export function previewable(source) {
  const text = `${source?.title || ""} ${source?.body || ""}`;
  if (ABUSIVE.test(text)) return false;
  return (
    source.kind === "news" ||
    !!source.title ||
    (source.body || "").trim().length >= 40
  );
}

const published = (source) => Date.parse(source?.published_at || "");

// Company headlines from the last day, newest first, for the activity summary.
export function recentHeadlines(headlines, now = Date.now(), hours = 24) {
  return headlines
    .filter(
      (s) =>
        s.kind === "news" &&
        previewable(s) &&
        now - published(s) <= hours * 3600e3 &&
        published(s) <= now,
    )
    .sort((a, b) => published(b) - published(a));
}

// News published after the saved AI reading's source cutoff is not in its tone.
export function headlinesAfterReading(sentiment, headlines) {
  const cutoff = sentiment?.withheld
    ? null
    : Date.parse(sentiment?.cutoff || "");
  if (!cutoff) return [];
  return headlines.filter((s) => s.kind === "news" && published(s) > cutoff);
}

// The nearest saved annual analyst revenue forecast (public page). Its currency
// is often unstated, so it is shown with "$", never silently as US dollars.
export function analystRevenueForecast(fmp) {
  const page = fmp?.public_forecasts?.available
    ? fmp.public_forecasts.snapshot?.data
    : null;
  const forecast = (page?.forecasts || [])
    .filter((f) => f.period_type === "annual" && f.period_end)
    .sort((a, b) => a.period_end.localeCompare(b.period_end))
    .find((f) =>
      f.metrics?.some((m) => m.key === "revenue" && number(m.average) > 0),
    );
  if (!forecast) return null;
  const metric = forecast.metrics.find((m) => m.key === "revenue");
  const amount = money(metric.average);
  return {
    display: forecast.currency === "USD" ? amount : amount?.replace("US$", "$"),
    periodEnd: forecast.period_end,
    fiscalYear: forecast.fiscal_year,
    analysts: forecast.displayed_analyst_count ?? null,
    currencyStated: !!forecast.currency,
  };
}

// Borrowing measured in years of past-12-month free cash flow, only when both
// figures end on the same date and free cash flow is positive.
export function borrowingYears(borrowing, freeCash) {
  const debt = number(borrowing?.value);
  const cash = number(freeCash?.value);
  if (debt == null || !(cash > 0) || borrowing?.end !== freeCash?.end)
    return null;
  return debt / cash;
}

// The 7-day tone counts every development equally, so one major story can be
// outweighed. This separates relevant news stories from the last day before the
// reading's cutoff. Stories, not grouped developments, are counted here.
export function pastDayTone(sentiment, headlines, hours = 24) {
  const cutoff = sentiment?.withheld
    ? null
    : Date.parse(sentiment?.cutoff || "");
  if (!cutoff) return null;
  const counts = {};
  let total = 0;
  for (const s of headlines) {
    const age = cutoff - published(s);
    if (s.kind !== "news" || !s.tone || age < 0 || age > hours * 3600e3)
      continue;
    counts[s.tone] = (counts[s.tone] || 0) + 1;
    total += 1;
  }
  return total ? { total, counts } : null;
}
