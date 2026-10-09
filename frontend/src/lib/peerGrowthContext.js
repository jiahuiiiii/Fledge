import { reportedRow } from "./sectorPosition.js";
export function peerGrowthContext(data) {
  if (!data) return "See reported growth alongside your chosen peers.";
  const rows = (data.members || []).map((member) =>
    reportedRow(member, "revenue_growth"),
  );
  const own = rows.find((row) => row.symbol === data.symbol);
  const peers = rows.filter(
    (row) =>
      row.symbol !== data.symbol &&
      row.value != null &&
      own?.value != null &&
      row.end &&
      own.end &&
      Math.abs(Date.parse(row.end) - Date.parse(own.end)) <= 120 * 86400000,
  );
  if (!peers.length)
    return `${data.symbol}: a fiscal-year growth comparison is unavailable.`;
  const faster = peers.filter((row) => row.value > own.value).length;
  const slower = peers.filter((row) => row.value < own.value).length;
  return `${data.symbol} fiscal-year revenue growth was ${faster ? `slower than ${faster}` : slower ? `faster than ${slower}` : `equal to all ${peers.length}`} of ${peers.length} comparable peers. Fiscal years may differ.`;
}
