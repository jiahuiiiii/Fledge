export const number = (value) => {
  if (value == null || value === "") return null;
  const result = Number(value);
  return Number.isFinite(result) ? result : null;
};
export const metric = (period, key) =>
  period?.metrics?.find((row) => row.key === key);
export const money = (value) => {
  const n = number(value);
  if (n == null) return "Unavailable";
  const abs = Math.abs(n),
    divisor = abs >= 1e12 ? 1e12 : abs >= 1e9 ? 1e9 : abs >= 1e6 ? 1e6 : 1;
  return `${n < 0 ? "−" : ""}US$${(abs / divisor).toLocaleString("en-GB", { maximumFractionDigits: 2 })}${divisor === 1e12 ? "tn" : divisor === 1e9 ? "bn" : divisor === 1e6 ? "m" : ""}`;
};
export const percent = (value) =>
  number(value) == null ? "Unavailable" : `${number(value).toFixed(1)}%`;
export const day = (value) =>
  value
    ? new Date(value).toLocaleDateString("en-GB", {
        day: "numeric",
        month: "short",
        year: "numeric",
        timeZone: "UTC",
      })
    : "Unknown";
export const sameDates = (a, b) =>
  a && b && a.start && a.start === b.start && a.end === b.end;
const daysBetween = (a, b) => (Date.parse(a) - Date.parse(b)) / 86400000;
const basis = (row) =>
  [...new Set((row?.inputs || []).map((input) => input.concept))]
    .sort()
    .join("|");
export function previousYear(rows, active) {
  return (
    rows.find(
      (row) =>
        row.end !== active?.end &&
        daysBetween(active?.end, row.end) >= 357 &&
        daysBetween(active?.end, row.end) <= 373,
    ) || null
  );
}
export function incomeInsights(active, previous, mode) {
  const readings = [];
  const revenue = metric(active, "revenue"),
    before = metric(previous, "revenue");
  if (
    number(revenue?.value) != null &&
    number(before?.value) > 0 &&
    basis(revenue) &&
    basis(revenue) === basis(before) &&
    previousYear([previous], active) &&
    revenue.start &&
    before.start
  ) {
    const change = (number(revenue.value) / number(before.value) - 1) * 100;
    readings.push({
      tone: change >= 0 ? "positive" : "caution",
      basis:
        mode === "trailing"
          ? "Trailing 12 months"
          : mode === "annual"
            ? "Fiscal year"
            : "Selected period",
      period: `${day(revenue.start)} – ${day(revenue.end)} vs ${day(before.start)} – ${day(before.end)}`,
      title:
        change > 0
          ? "Sales grew"
          : change < 0
            ? "Sales fell"
            : "Sales were unchanged",
      text: `${money(revenue.value)} versus ${money(before.value)} a year earlier${change === 0 ? "." : ` — ${Math.abs(change).toFixed(1)}% ${change > 0 ? "higher" : "lower"}.`}`,
      rows: [revenue, before],
      detail:
        "Reported sales include acquisition, currency and accounting effects; this is not organic growth.",
    });
  } else
    readings.push({
      tone: "unknown",
      title: "Revenue comparison unavailable",
      text: "A compatible result from a year earlier is needed to describe growth.",
      rows: [revenue, before].filter(Boolean),
    });
  const margin = metric(active, "net_margin"),
    net = metric(active, "net_income");
  if (number(margin?.value) != null) {
    const n = number(margin.value);
    readings.push({
      tone: n >= 0 ? "positive" : "caution",
      title: n >= 0 ? "What remained from sales" : "The period ended in a loss",
      text: `For every US$100 of revenue, the company ${n >= 0 ? "reported" : "lost"} US$${Math.abs(n).toFixed(1)} ${n >= 0 ? "in net result" : "at the net-result level"}.`,
      detail: (net?.label || "Net result") + ". Profit is not cash generated.",
      rows: [margin, net],
    });
  } else {
    const operating = metric(active, "operating_margin");
    readings.push(
      number(operating?.value) != null
        ? {
            tone: number(operating.value) >= 0 ? "positive" : "caution",
            title: "Operating profit from each US$100 of sales",
            text: `${money(Math.abs(number(operating.value)))} ${number(operating.value) >= 0 ? "remained before non-operating items and tax" : "was lost from operations"}. The net-result comparison is unavailable.`,
            rows: [operating],
          }
        : {
            tone: "unknown",
            title: "Profit margin unavailable",
            text: "Matching revenue and profit figures are needed.",
            rows: [],
          },
    );
  }
  const cash = metric(active, "operating_cash"),
    fcf = metric(active, "free_cash_flow");
  if (number(fcf?.value) != null)
    readings.push({
      tone: number(fcf.value) >= 0 ? "positive" : "caution",
      title:
        number(fcf.value) >= 0
          ? "Cash left after capital spending"
          : "Capital spending exceeded operating cash",
      text: `${money(cash.value)} of operating cash flow ${number(fcf.value) >= 0 ? `left ${money(fcf.value)}` : `fell short by ${money(Math.abs(number(fcf.value)))}`} after cash spending on property, plant and equipment.`,
      detail:
        "This calculation excludes acquisitions, debt repayments and dividends; it is not all cash available to spend.",
      rows: [cash, metric(active, "capital_spending"), fcf],
    });
  else
    readings.push({
      tone: "unknown",
      title: "Cash remaining is unavailable",
      text: "Operating cash flow and capital spending must cover the same fiscal dates.",
      rows: [cash, fcf].filter(Boolean),
    });
  const beforeMargin = metric(previous, "net_margin"),
    beforeNet = metric(previous, "net_income");
  if (
    number(margin?.value) != null &&
    number(beforeMargin?.value) != null &&
    net?.label === beforeNet?.label &&
    basis(net) === basis(beforeNet) &&
    previousYear([previous], active)
  ) {
    const change = number(margin.value) - number(beforeMargin.value);
    readings.push({
      tone: change >= 0 ? "positive" : "caution",
      title:
        change > 0
          ? "Net margin expanded"
          : change < 0
            ? "Net margin narrowed"
            : "Net margin was unchanged",
      text: `${percent(margin.value)} versus ${percent(beforeMargin.value)} a year earlier${change === 0 ? "." : ` — a ${Math.abs(change).toFixed(1)} percentage-point ${change > 0 ? "increase" : "decrease"}.`}`,
      rows: [margin, beforeMargin],
    });
  }
  return readings;
}
export function balanceInsights(period) {
  const read = (key) => metric(period, key),
    readings = [];
  const ca = read("current_assets"),
    cl = read("current_liabilities");
  if (number(ca?.value) != null && number(cl?.value) != null) {
    const difference = number(ca.value) - number(cl.value);
    readings.push({
      tone: difference >= 0 ? "positive" : "caution",
      title:
        difference === 0
          ? "Current assets equal near-term obligations"
          : difference > 0
            ? "Current assets exceed near-term obligations"
            : "Near-term obligations exceed current assets",
      text: `${money(ca.value)} of current assets versus ${money(cl.value)} of current liabilities — a ${money(Math.abs(difference))} ${difference >= 0 ? "surplus" : "shortfall"}.`,
      detail:
        "Current assets include amounts that still need to be sold or collected. This comparison does not establish that every obligation can be paid on time.",
      rows: [ca, cl, read("working_capital")],
    });
  } else
    readings.push({
      tone: "unknown",
      title: "Near-term comparison unavailable",
      text: "Matching current assets and current liabilities are needed. Missing obligations are not zero.",
      rows: [ca, cl].filter(Boolean),
    });
  const debt = read("debt"),
    cash = read("cash"),
    net = read("net_debt");
  if (number(net?.value) != null)
    readings.push({
      tone: number(net.value) <= 0 ? "positive" : "neutral",
      title:
        number(net.value) > 0
          ? "Borrowing exceeds cash on hand"
          : "Cash equals or exceeds borrowing",
      text: `${money(debt.value)} of combined borrowing versus ${money(cash.value)} of cash and equivalents. ${number(net.value) > 0 ? `${money(net.value)} remains after subtracting cash.` : number(net.value) === 0 ? "Cash and borrowing are equal." : `Cash exceeds borrowing by ${money(Math.abs(number(net.value)))}.`}`,
      detail:
        "This arithmetic excludes leases and does not assume cash is unrestricted or available for repayment.",
      rows: [debt, cash, net],
    });
  else
    readings.push({
      tone: "unknown",
      title: "Cash versus borrowing is unavailable",
      text: "A complete borrowing measure and cash balance from this same filing are needed.",
      rows: [debt, cash].filter(Boolean),
    });
  const ratio = read("debt_equity");
  if (number(ratio?.value) != null)
    readings.push({
      tone: "neutral",
      title: "Borrowing relative to book equity",
      text: `${percent(ratio.value)}: US$${(number(ratio.value) / 100).toFixed(2)} of borrowing for each US$1 of book equity.`,
      detail:
        "Book equity is assets minus liabilities, including non-controlling interests; it is not market value. This is a relationship, not a credit rating.",
      rows: [ratio],
    });
  else
    readings.push({
      tone: "unknown",
      title: "Borrowing / equity ratio unavailable",
      text:
        ratio?.reason ||
        "A positive, matching book-equity denominator is required.",
      rows: [ratio].filter(Boolean),
    });
  return readings;
}
export function balanceBlocks(period, side) {
  const total = metric(period, side === "assets" ? "assets" : "liabilities"),
    equity = metric(period, "equity");
  const assetTotal = number(metric(period, "assets")?.value);
  if (!(assetTotal > 0)) return null;
  const keys =
    side === "assets"
      ? [
          "cash",
          "receivables",
          "inventory",
          "property",
          "goodwill",
          "intangibles",
        ]
      : ["equity", "debt", "payables"];
  const rows = keys
    .map((key) => metric(period, key))
    .filter((row) => number(row?.value) != null);
  if (
    side !== "assets" &&
    !(number(total?.value) >= 0 && number(equity?.value) >= 0)
  )
    return null;
  if (
    rows.some(
      (row) =>
        number(row.value) < 0 || row.end !== period.end || row.start != null,
    )
  )
    return null;
  const sum = rows.reduce((n, row) => n + number(row.value), 0);
  if (sum > assetTotal + Math.max(0.0001, assetTotal * 1e-12)) return null;
  const remainder = metric(
    period,
    side === "assets" ? "other_assets" : "other_liabilities",
  );
  if (
    number(remainder?.value) == null ||
    Math.abs(sum + number(remainder.value) - assetTotal) >
      Math.max(0.0001, assetTotal * 1e-12)
  )
    return null;
  return [...rows, ...(number(remainder.value) > 0 ? [remainder] : [])];
}

export function borrowingTrend(period, previous) {
  const current = metric(period, "debt_equity"),
    before = metric(previous, "debt_equity");
  if (
    number(current?.value) == null ||
    number(before?.value) == null ||
    !previousYear([previous], period) ||
    basis(current) !== basis(before)
  )
    return null;
  const change = number(current.value) - number(before.value);
  return {
    tone: "neutral",
    title:
      change < 0
        ? "Borrowing / equity fell"
        : change > 0
          ? "Borrowing / equity rose"
          : "Borrowing / equity was unchanged",
    text: `${percent(current.value)} at ${day(period.end)}, compared with ${percent(before.value)} a year earlier.`,
    detail:
      "The ratio can change because borrowing, book equity or both changed. It does not establish that the company repaid debt.",
    rows: [current, before],
  };
}

// Split the largest remaining rectangle near its midpoint. Every rectangle
// retains exactly its fraction of the total; labels never change the geometry.
export function blockLayout(rows, width = 100, height = 100) {
  const items = rows
    .filter((row) => number(row.value) > 0)
    .sort((a, b) => number(b.value) - number(a.value));
  const place = (group, x, y, w, h) => {
    if (!group.length) return [];
    if (group.length === 1) return [{ ...group[0], x, y, width: w, height: h }];
    const total = group.reduce((sum, row) => sum + number(row.value), 0);
    let count = 1,
      subtotal = number(group[0].value);
    while (
      count < group.length - 1 &&
      Math.abs(subtotal + number(group[count].value) - total / 2) <
        Math.abs(subtotal - total / 2)
    )
      subtotal += number(group[count++].value);
    const fraction = subtotal / total;
    return w >= h
      ? [
          ...place(group.slice(0, count), x, y, w * fraction, h),
          ...place(
            group.slice(count),
            x + w * fraction,
            y,
            w * (1 - fraction),
            h,
          ),
        ]
      : [
          ...place(group.slice(0, count), x, y, w, h * fraction),
          ...place(
            group.slice(count),
            x,
            y + h * fraction,
            w,
            h * (1 - fraction),
          ),
        ];
  };
  return place(items, 0, 0, width, height);
}

export function historyPath(rows, key, x, y) {
  let path = "",
    previous = null,
    definition = "";
  for (const row of rows) {
    const m = metric(row, key),
      value = number(m?.value);
    if (value == null || Math.abs(value) > 1e15) {
      previous = null;
      continue;
    }
    const nextDefinition = basis(m) + m.label;
    const gap = previous && daysBetween(row.end, previous.end);
    path += `${!previous || nextDefinition !== definition || gap > 420 ? "M" : "L"}${x(row)},${y(value)} `;
    previous = row;
    definition = nextDefinition;
  }
  return path;
}
