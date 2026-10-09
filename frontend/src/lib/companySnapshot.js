// The Overview summary is built only from figures the workspace already saved.
// A missing or mismatched input makes its sentence disappear and its check
// "unknown"; nothing is estimated or carried over from another date.

const num = (value) => {
  if (value == null || value === "") return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
};

export const day = (value) =>
  value
    ? new Date(value).toLocaleDateString("en-GB", {
        day: "numeric",
        month: "short",
        year: "numeric",
        timeZone: "UTC",
      })
    : "";

export const money = (value) => {
  const number = num(value);
  if (number == null) return null;
  const abs = Math.abs(number);
  const [divisor, suffix] =
    abs >= 1e12
      ? [1e12, "tn"]
      : abs >= 1e9
        ? [1e9, "bn"]
        : abs >= 1e6
          ? [1e6, "m"]
          : [1, ""];
  const scaled = (abs / divisor).toLocaleString("en-GB", {
    maximumFractionDigits: divisor === 1 ? 0 : 1,
  });
  return `${number < 0 ? "−" : ""}US$${scaled}${suffix}`;
};

export const percent = (value, digits = 1) => {
  const number = num(value);
  return number == null ? null : `${number.toFixed(digits)}%`;
};

export function trailing(depth, key) {
  const row = depth?.trailing?.find((item) => item.key === key);
  return row && num(row.value) != null ? row : null;
}

export function annualGrowth(depth) {
  const trend = (depth?.revenue_trend || [])
    .filter((row) => num(row.value) != null && row.period_end)
    .sort((a, b) => a.period_end.localeCompare(b.period_end));
  if (trend.length < 2) return null;
  const [previous, latest] = trend.slice(-2);
  const before = num(previous.value);
  const after = num(latest.value);
  if (!(before > 0)) return null;
  return {
    growth: ((after - before) / before) * 100,
    latest: after,
    previous: before,
    periodEnd: latest.period_end,
    previousEnd: previous.period_end,
  };
}

// Balances must come from one report; borrowing only counts when it shares
// that report's balance date.
export function balance(performance, depth) {
  const reports = Object.values(performance?.reports || {}).filter(
    (report) => report?.period_end && Array.isArray(report.metrics),
  );
  if (!reports.length) return null;
  const report = reports.sort((a, b) =>
    b.period_end.localeCompare(a.period_end),
  )[0];
  const metric = (key) => {
    const row = report.metrics.find((item) => item.key === key);
    return row && row.end === report.period_end ? num(row.value) : null;
  };
  const debt =
    depth?.debt?.end === report.period_end ? num(depth.debt.value) : null;
  return {
    periodEnd: report.period_end,
    form: report.form,
    assets: metric("assets"),
    liabilities: metric("liabilities"),
    cash: metric("cash"),
    debt,
  };
}

export function revenueOutlook(outlook) {
  for (const release of outlook?.releases || []) {
    for (const section of release.sections || []) {
      const forecast = (section.forecasts || []).find(
        (item) => item.metric === "revenue" && num(item.low) != null,
      );
      if (forecast)
        return {
          low: num(forecast.low),
          high: num(forecast.high ?? forecast.low),
          approximate: !!forecast.approximate,
          periodEnd: section.period_end,
          periodType: section.period_type,
          publishedAt: release.published_at,
          compared: forecast.comparison?.status === "compared",
        };
    }
  }
  return null;
}

const toneLabel = (tone) => {
  if (!tone || /thin|separate/.test(tone)) return null;
  const text = tone.replace(" / balanced", "").replace(" leaning", "-leaning");
  return text.charAt(0).toUpperCase() + text.slice(1);
};

export function newsTone(sentiment) {
  const news = sentiment?.summary?.news;
  if (!news) return null;
  const counts = news.counts || {};
  const total = ["positive", "neutral", "mixed", "negative"].reduce(
    (sum, key) => sum + (counts[key] || 0),
    0,
  );
  return {
    label: toneLabel(news.tone),
    counts,
    total,
    selected: news.selected || 0,
    savedAt: sentiment.created_at,
    stale: !!sentiment.stale,
    social: sentiment.summary.social_platforms || {},
  };
}

const check = (label, value) => ({
  label,
  state: value == null ? "unknown" : value ? "pass" : "fail",
});

export function snapshot(data) {
  const depth = data?.financial_depth;
  const growth = annualGrowth(depth);
  const revenue = trailing(depth, "revenue");
  const operating = trailing(depth, "operating_income");
  const margin = trailing(depth, "operating_margin");
  const freeCash = trailing(depth, "free_cash_flow");
  const position = balance(data?.performance, depth);
  const outlook = revenueOutlook(data?.management_outlook);
  const tone = newsTone(data?.sentiment);
  const quote = data?.market?.quote?.quote || null;

  const sentences = [];
  if (growth)
    sentences.push(
      `Revenue ${growth.growth >= 0 ? "grew" : "fell"} ${Math.abs(growth.growth).toFixed(1)}% in the fiscal year to ${day(growth.periodEnd)}.`,
    );
  if (outlook) {
    const range =
      outlook.low === outlook.high
        ? `${outlook.approximate ? "about " : ""}${money(outlook.low)}`
        : `${money(outlook.low)} to ${money(outlook.high)}`;
    sentences.push(
      `Management expects ${range} of revenue for the ${outlook.periodType || "period"} ending ${day(outlook.periodEnd)}.`,
    );
  }
  if (position?.cash > 0 && position?.debt != null) {
    const ratio = position.debt / position.cash;
    sentences.push(
      ratio >= 1.05
        ? `Its borrowing is about ${ratio.toFixed(1)}× the cash it holds.`
        : ratio <= 0.95
          ? "It holds more cash than it has borrowed."
          : "Its borrowing and cash are about the same.",
    );
  }

  const sections = [
    {
      tab: "fundamentals",
      number: 1,
      title: "Growth & profit",
      checks: [
        check(
          "Revenue grew last fiscal year",
          growth ? growth.growth > 0 : null,
        ),
        check(
          "Operating profit, past 12 months",
          operating ? Number(operating.value) > 0 : null,
        ),
      ],
      figures: [
        {
          value: revenue ? money(revenue.value) : null,
          label: "Revenue, past 12 months",
          tone: "info",
        },
        {
          value: margin ? percent(margin.value) : null,
          label: "Operating margin",
          tone: "positive",
        },
      ],
      note: revenue ? `${day(revenue.start)} – ${day(revenue.end)}` : null,
      action: "Open Financials",
    },
    {
      tab: "fundamentals",
      number: 2,
      title: "Financial health",
      checks: [
        check(
          "Owns more than it owes",
          position?.assets != null && position?.liabilities != null
            ? position.assets > position.liabilities
            : null,
        ),
        check(
          "Cash covers borrowing",
          position?.cash != null && position?.debt != null
            ? position.cash >= position.debt
            : null,
        ),
        check(
          "Positive free cash flow",
          freeCash ? Number(freeCash.value) > 0 : null,
        ),
      ],
      figures: [
        {
          value: freeCash ? money(freeCash.value) : null,
          label: "Free cash flow, past 12 months",
          tone: "positive",
        },
        {
          value: position?.debt != null ? money(position.debt) : null,
          label: "Borrowing",
          tone: "caution",
        },
      ],
      note: position ? `Balances at ${day(position.periodEnd)}` : null,
      action: "Open Financials",
    },
    {
      tab: "evidence",
      number: 3,
      title: "News & discussion",
      checks: [],
      tone,
      figures: [
        {
          value: tone?.label || null,
          label: "AI reading of recent news",
          tone: "neutral",
        },
        {
          value: tone ? String(tone.selected) : null,
          label: "Stories analysed",
          tone: "info",
        },
      ],
      note: tone?.savedAt
        ? `${tone.stale ? "Older reading" : "Saved"} ${day(tone.savedAt)}`
        : null,
      action: "Open News & discussion",
    },
    {
      tab: "expectations",
      number: 4,
      title: "Outlook",
      checks: [
        check("Management gave a revenue outlook", outlook ? true : null),
        ...(outlook
          ? [
              {
                label: outlook.compared
                  ? "Compared with results"
                  : "Not yet compared with results",
                state: outlook.compared ? "pass" : "unknown",
              },
            ]
          : []),
      ],
      figures: [
        {
          value: outlook
            ? `${outlook.approximate ? "≈ " : ""}${money(outlook.low)}`
            : null,
          label: outlook
            ? `Revenue expected, ${outlook.periodType || "period"} to ${day(outlook.periodEnd)}`
            : "Revenue outlook",
          tone: "info",
        },
      ],
      note: outlook?.publishedAt
        ? `From the release of ${day(outlook.publishedAt)}`
        : null,
      action: "Open Outlook",
    },
    {
      tab: "valuation",
      number: 5,
      title: "Compare & value",
      checks: [],
      figures: [
        {
          value:
            quote?.price != null
              ? `US$${Number(quote.price).toFixed(2)}`
              : null,
          label: "Share price",
          tone: "info",
        },
      ],
      note: "Compare with peers you choose, or test your own scenario.",
      action: "Open Compare & value",
    },
  ];
  return { sentences, sections, quote };
}
