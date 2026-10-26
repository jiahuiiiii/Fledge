// Plain-English readings for the Financials and Compare tabs.
// Pure functions so the wording can be tested without a browser.
import { number, metric, money } from "./financialStory.js";

const cents = (margin) => `${Math.round(Math.abs(margin))}¢`;

function nameList(names) {
  if (names.length <= 1) return names[0] || "";
  return `${names.slice(0, -1).join(", ")} and ${names.at(-1)}`;
}

export function plainSales(active, previous, name = "The company") {
  const now = number(metric(active, "revenue")?.value);
  if (now == null) return null;
  const before = number(metric(previous, "revenue")?.value);
  const change = before > 0 ? (now / before - 1) * 100 : null;
  let text = `All the money customers paid ${name} over this period.`;
  if (change != null && Math.abs(change) < 1)
    text += " About the same as a year earlier.";
  else if (change > 0)
    text += ` Up ${change.toFixed(0)}% on a year earlier, so the business is growing.`;
  else if (change < 0)
    text += ` Down ${Math.abs(change).toFixed(0)}% on a year earlier, so sales are shrinking.`;
  return { key: "sales", value: money(now), change, text };
}

export function plainMargin(active, name = "The company") {
  const margin = number(metric(active, "operating_margin")?.value);
  if (margin == null) return null;
  if (margin < 0)
    return {
      key: "margin",
      value: `−${cents(margin)}`,
      tone: "bad",
      text: `${name} spent more than it earned from sales: it lost about ${cents(margin)} on every $1. Young or fast-growing companies often do.`,
    };
  const compare =
    margin >= 25
      ? "That is high: most companies keep 10–20¢."
      : margin > 20
        ? "That is a bit above most companies (10–20¢)."
        : margin >= 10
          ? "That is typical: most companies keep 10–20¢."
          : "That is thin: most companies keep 10–20¢.";
  return {
    key: "margin",
    value: cents(margin),
    tone: margin >= 10 ? "good" : "neutral",
    text: `After everyday costs like staff and marketing, ${name} keeps about ${cents(margin)} of every $1 of sales. ${compare}`,
  };
}

export function plainCash(active, name = "The company") {
  const cash = number(metric(active, "free_cash_flow")?.value);
  if (cash == null) return null;
  return {
    key: "cash",
    value: money(cash),
    tone: cash >= 0 ? "good" : "bad",
    text:
      cash >= 0
        ? `Cash left after ${name} paid its bills and bought new equipment. Positive means it pays its own way.`
        : `${name} spent more cash than it brought in. Watch whether this turns around.`,
  };
}

function amount(value, unit) {
  const n = number(value);
  if (n == null) return null;
  if (unit === "percent") return `${n}%`;
  return money(n);
}

// The company's own forecast from its latest earnings release.
export function plainForecast(management, today = new Date()) {
  const releases = management?.releases || [];
  const release = releases.find((r) => r.current) || releases[0];
  if (!release?.current) return null;
  const date = today.toISOString().slice(0, 10);
  for (const section of release.sections || []) {
    if (section.review_status) continue;
    if (section.period_end && section.period_end < date) continue;
    const forecast = (section.forecasts || []).find(
      (f) => amount(f.low, f.unit) != null,
    );
    if (!forecast) continue;
    const low = amount(forecast.low, forecast.unit),
      high = amount(forecast.high, forecast.unit);
    const range = high && high !== low ? `${low} to ${high}` : low;
    return {
      key: "forecast",
      period: section.heading || section.period_label || "",
      value: `${forecast.label}: ${forecast.approximate ? "about " : ""}${range}`,
      text: "This is the company’s own forecast. Forecasts can be wrong.",
    };
  }
  return null;
}

// rows: [{ symbol, name, growth, margin, pe }]; own company first.
export function compareVerdicts(rows) {
  const [own, ...peers] = rows;
  if (!own) return [];
  const verdicts = [];
  const check = (key, more, less, toneMore, toneLess) => {
    if (own[key] == null) return;
    const others = peers.filter((p) => p[key] != null);
    if (!others.length) return;
    const above = others.filter((p) => own[key] > p[key]);
    const below = others.filter((p) => own[key] < p[key]);
    if (above.length === others.length)
      verdicts.push({
        key,
        tone: toneMore,
        text: more(others.length === 1 ? others[0].name : `all ${others.length} peers`),
      });
    else if (below.length === others.length)
      verdicts.push({
        key,
        tone: toneLess,
        text: less(others.length === 1 ? others[0].name : `all ${others.length} peers`),
      });
    else if (above.length >= below.length)
      verdicts.push({ key, tone: toneMore, text: more(nameList(above.map((p) => p.name))) });
    else
      verdicts.push({ key, tone: toneLess, text: less(nameList(below.map((p) => p.name))) });
  };
  check(
    "growth",
    (who) => `Sales are growing **faster** than ${who}.`,
    (who) => `Sales are growing **slower** than ${who}.`,
    "good",
    "neutral",
  );
  check(
    "margin",
    (who) => `Keeps **more profit** from each $1 of sales than ${who}.`,
    (who) => `Keeps **less profit** from each $1 of sales than ${who}.`,
    "good",
    "neutral",
  );
  check(
    "pe",
    (who) =>
      `Shares are **pricier** for each $1 of profit than ${who}. Investors expect a lot.`,
    (who) =>
      `Shares are **cheaper** for each $1 of profit than ${who}. Investors expect less, or see more risk.`,
    "neutral",
    "neutral",
  );
  return verdicts;
}

export const formatGrowth = (v) =>
  v == null ? "–" : `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v).toFixed(0)}%`;
export const formatMargin = (v) =>
  v == null ? "–" : `${v < 0 ? "−" : ""}${Math.round(Math.abs(v))}¢`;
export const formatPe = (v) => (v == null ? "–" : `${Math.round(v)}×`);
