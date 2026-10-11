import { metric, number } from "./financialStory.js";

const definitions = [
  {
    key: "net_parent",
    label: "Parent company’s share",
    metricLabel: "Net income attributable to parent",
  },
  {
    key: "net_consolidated",
    label: "Whole group",
    metricLabel: "Net result including non-controlling interests",
  },
];
const conflict = (row) =>
  metric(row, "net_income")?.value == null &&
  /conflicting/i.test(metric(row, "net_income")?.reason || "");
const usable = (row, key) => {
  const m = metric(row, key);
  return (
    !conflict(row) &&
    m?.unit === "USD" &&
    typeof m.value !== "boolean" &&
    number(m.value) != null &&
    Math.abs(number(m.value)) <= 1e15
  );
};

export function profitOptions(story) {
  if (story?.status !== "available") return [];
  const rows = ["annual", "quarterly", "trailing"].flatMap(
    (kind) => story[kind] || [],
  );
  // One default for the company, shared by every period tab. Prefer the scope
  // with the most usable saved points; equal coverage prefers the parent's share.
  // Never splice another ownership scope into a missing date.
  return definitions
    .map((d) => ({
      ...d,
      count: rows.filter((row) => usable(row, d.key)).length,
    }))
    .filter((d) => d.count > 0)
    .sort((a, b) => b.count - a.count);
}

export function consistentProfitRows(rows, scope) {
  const definition = definitions.find((d) => d.key === scope);
  if (!definition) return rows; // Older responses without separate scopes.
  return rows.map((row) => {
    const selected = metric(row, scope),
      original = metric(row, "net_income");
    const blocked = conflict(row);
    const valid = usable(row, scope);
    const net = blocked
      ? { ...original }
      : {
          ...(selected || {}),
          key: "net_income",
          label: definition.metricLabel,
          unit: selected?.unit || "USD",
          value: valid ? selected.value : null,
          start: selected?.start || row.start || null,
          end: row.end,
          inputs: selected?.inputs || [],
          reason: valid
            ? null
            : selected?.reason ||
              `${definition.label} is not available for this date. The chart keeps the same profit definition across all dates.`,
        };
    return {
      ...row,
      metrics: [
        ...(row.metrics || []).filter((m) => m.key !== "net_income"),
        net,
      ],
    };
  });
}
