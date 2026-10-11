// One-line peer comparisons for Overview, using the same eligibility rules as
// the Compare & value chart so both pages show the same numbers.
import {
  comparablePeers,
  peRows,
  peerAverage,
  reportedRow,
} from "./sectorPosition.js";

const percent = (value) => `${value.toFixed(1)}%`;
const multiple = (value) => `${value.toFixed(1)}×`;

function compare(rows, symbol) {
  const own = rows.find((row) => row.symbol === symbol);
  if (own?.value == null) return null;
  const peers = comparablePeers(rows, symbol);
  if (!peers.length) return null;
  return {
    own: own.value,
    count: peers.length,
    higher: peers.filter((row) => row.value > own.value).length,
    lower: peers.filter((row) => row.value < own.value).length,
    average: peerAverage(rows, symbol).value,
  };
}

// Revenue growth: "slower than 3 of 4 comparable peers (peer average 38.9%)".
export function growthTakeaway(sector, lead = "That is") {
  if (!sector?.members?.length) return null;
  const rows = sector.members.map((m) => reportedRow(m, "revenue_growth"));
  const c = compare(rows, sector.symbol);
  if (!c) return null;
  const relation = c.higher
    ? `slower than ${c.higher} of ${c.count}`
    : c.lower
      ? `faster than all ${c.count}`
      : `level with all ${c.count}`;
  return `${lead} ${relation} comparable peers (peer average ${percent(c.average)}).`;
}

// P/E: "below the 62.4× average of 5 peers". Not a valuation verdict.
export function peTakeaway(sector, references, lead = "That is") {
  if (!sector?.members?.length) return null;
  const rows = peRows(sector.members, references || []);
  const c = compare(rows, sector.symbol);
  if (!c || c.average == null) return null;
  const side =
    c.own < c.average ? "below" : c.own > c.average ? "above" : "level with";
  return `${lead} ${side} the ${multiple(c.average)} average of ${c.count} ${c.count === 1 ? "peer" : "peers"} on the same measure.`;
}
