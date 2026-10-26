import { metric, number, previousYear } from "./financialStory.js";

// Reasons the "Fill missing figures" tool can act on (a fact missing from one
// saved filing). Everything else it cannot fix, so we explain it instead.
const FIXABLE = [
  "No compatible whole-company USD fact in the selected filing.",
  "A complete reported borrowing total",
];
const fixable = (reason) => FIXABLE.some((text) => (reason || "").startsWith(text));

// Figures the charts lack for the latest period, with the exact reason and what
// would help. Pure: pass `day` to format dates.
export function unfixableGaps({ rows = [], active, balance, mode = "trailing", day = (v) => v }) {
  const out = [];
  const basis = mode === "annual" ? "fiscal year" : "past 12 months";
  if (active) {
    const revenue = metric(active, "revenue");
    const prior = previousYear(rows, active);
    const priorRevenue = metric(prior, "revenue");
    const grows = number(revenue?.value) != null && number(priorRevenue?.value) != null;
    if (!grows) {
      const period = `${day(active.start)} – ${day(active.end)}`;
      if (!prior)
        out.push({
          key: "growth",
          title: "Revenue growth",
          period: `${basis} to ${day(active.end)}`,
          reason: `No saved report covers the same ${basis} a year earlier (the period ending about ${day(
            new Date(Date.parse(active.end) - 365 * 86400000).toISOString(),
          )}), so there is nothing to compare ${period} with. Fill missing figures only reads reports that are already saved.`,
          help: "Use Update data to collect earlier filings. If they are already saved, the earlier period was reported on a different basis and cannot be matched.",
        });
      else if (number(revenue?.value) == null && !fixable(revenue?.reason))
        out.push({ key: "growth", title: "Revenue growth", period: period, reason: `Revenue for this period is unavailable: ${revenue?.reason || "no reason was saved"}`, help: "The source data, not a missing line, is the limit." });
      else if (number(priorRevenue?.value) == null && !fixable(priorRevenue?.reason))
        out.push({ key: "growth", title: "Revenue growth", period: `${day(prior.start)} – ${day(prior.end)}`, reason: `Revenue a year earlier is unavailable: ${priorRevenue?.reason || "no reason was saved"}`, help: "The source data, not a missing line, is the limit." });
    }
    for (const row of active.metrics || []) {
      if (row.key === "revenue" || number(row.value) != null || fixable(row.reason)) continue;
      out.push({
        key: `${active.id || active.end}:${row.key}`,
        title: row.label || row.key,
        period: row.start ? `${day(row.start)} – ${day(row.end)}` : `At ${day(row.end)}`,
        reason: row.reason || "No reason was saved.",
        help: null,
      });
    }
  }
  for (const row of balance?.metrics || []) {
    if (number(row.value) != null || fixable(row.reason)) continue;
    out.push({
      key: `balance:${row.key}`,
      title: row.label || row.key,
      period: `At ${day(balance.end)}`,
      reason: row.reason || "No reason was saved.",
      help: null,
    });
  }
  return out;
}
