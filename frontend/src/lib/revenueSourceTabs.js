// Revenue views as tabs: Total revenue always, then only the breakdowns this
// company reports for the selected period (a company that folds its regions
// into business segments simply has no Countries & regions tab).
const TABS = [
  ["Total revenue", "Total revenue"],
  ["Operating segments", "Business segments"],
  ["Products and services", "Products and services"],
  ["Reported geographies", "Countries & regions"],
];

export function availableSourceTabs(mixes = []) {
  return TABS.filter(([key]) => key === "Total revenue" || mixes.some((row) => row.kind === key));
}

export function activeSourceTab(tabs, requested) {
  const keys = tabs.map(([key]) => key);
  if (keys.includes(requested)) return requested;
  return keys.includes("Operating segments") ? "Operating segments" : keys[0];
}
