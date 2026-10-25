import { targetChange } from "../lib/targetRange";

const usd = (v) =>
  `US$${Number(v).toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const month = (value) =>
  new Date(value).toLocaleDateString("en-GB", { month: "short", year: "numeric", timeZone: "UTC" });
const dayMonth = (value) =>
  new Date(value).toLocaleDateString("en-GB", { day: "numeric", month: "short", timeZone: "UTC" });

// Saved daily closes (left of "Today") with the analysts' low, mean and high
// 12-month targets to the right, each labelled with its distance from the last
// price. The left axis is price; the bottom axis shows the dates of the closes.
// Targets are opinions; the chart shows them, it does not forecast.
export default function TargetChart({ bars = [], range }) {
  const closes = bars
    .slice(-130)
    .filter((b) => Number.isFinite(Number(b.close)) && b.date);
  const current = range.current ?? (closes.length ? Number(closes.at(-1).close) : null);
  const w = 680,
    h = 250,
    left = 52,
    top = 16,
    bottom = 30,
    split = 360,
    tx = 500,
    right = 672;
  const values = [range.low, range.mean, range.high, current, ...closes.map((b) => Number(b.close))].filter((v) => v != null);
  const lo = Math.min(...values),
    hi = Math.max(...values),
    pad = (hi - lo) * 0.08 || hi * 0.05,
    min = lo - pad,
    max = hi + pad;
  const y = (v) => top + ((max - v) / (max - min)) * (h - top - bottom);
  const x = (i) => (closes.length > 1 ? left + (i * (split - left)) / (closes.length - 1) : split);
  const path = closes.map((b, i) => `${i ? "L" : "M"}${x(i).toFixed(1)} ${y(Number(b.close)).toFixed(1)}`).join("");
  const ticks = [0, 1, 2, 3].map((i) => min + ((max - min) * i) / 3);
  const dates = closes.length > 1 ? [0, Math.floor((closes.length - 1) / 2)] : [];
  const targets = [
    ["High", range.high],
    ["Mean", range.mean],
    ["Low", range.low],
  ];
  // Keep the three labels apart when targets are close together.
  const labelY = [];
  targets.forEach(([, v], i) => {
    const wanted = y(v);
    labelY[i] = i && wanted - labelY[i - 1] < 26 ? labelY[i - 1] + 26 : wanted;
  });
  const from = closes.length
    ? { x: x(closes.length - 1), y: y(current ?? Number(closes.at(-1).close)) }
    : { x: split, y: y(current ?? range.mean) };
  const first = closes[0]?.date,
    last = closes.at(-1)?.date;
  return (
    <figure className="target-chart-figure">
      <svg
        className="target-chart"
        viewBox={`0 0 ${w} ${h}`}
        role="img"
        aria-label={`Analyst targets: low ${usd(range.low)}, mean ${usd(range.mean)}, high ${usd(range.high)}.${current ? ` Last price ${usd(current)}.` : ""}${first ? ` Price history ${dayMonth(first)} to ${dayMonth(last)}.` : ""}`}
      >
        {ticks.map((v) => (
          <g key={v} className="target-chart__grid">
            <line x1={left} x2={right} y1={y(v)} y2={y(v)} />
            <text x={left - 8} y={y(v) + 4} textAnchor="end">{Math.round(v)}</text>
          </g>
        ))}
        <line x1={split} x2={split} y1={top} y2={h - bottom} className="target-chart__today" />
        <text x={split} y={h - bottom + 22} textAnchor="middle" className="target-chart__axis">Today</text>
        <text x={tx} y={h - bottom + 22} textAnchor="middle" className="target-chart__axis">12-month targets</text>
        {path && <path d={path} className="target-chart__line" fill="none" />}
        {dates.map((i, n) => (
          <text key={i} x={x(i)} y={h - bottom + 22} textAnchor={n === 0 ? "start" : "middle"} className="target-chart__axis">
            {month(closes[i].date)}
          </text>
        ))}
        <rect x={tx - 3} y={y(range.high)} width={6} height={Math.max(2, y(range.low) - y(range.high))} rx="3" className="target-chart__band" />
        {targets.map(([name, v], i) => {
          const change = current ? (v / current - 1) * 100 : null;
          const tone = change == null ? "" : change < 0 ? "is-down" : "is-up";
          return (
            <g key={name} className={`target-chart__target ${tone}`}>
              <line x1={from.x} y1={from.y} x2={tx} y2={y(v)} />
              <circle cx={tx} cy={y(v)} r="4" />
              <text x={tx + 14} y={labelY[i] - 2}>{name} {usd(v)}</text>
              <text x={tx + 14} y={labelY[i] + 12} className="target-chart__delta">{change == null ? "" : targetChange(change)}</text>
            </g>
          );
        })}
        {current != null && <circle cx={from.x} cy={from.y} r="4" className="target-chart__dot" />}
      </svg>
      <figcaption className="fine">
        {first ? `Daily closes, ${dayMonth(first)} – ${dayMonth(last)} ${new Date(last).getUTCFullYear()}. ` : "No saved price history. "}
        Targets are 12-month analyst opinions, shown to the right of today.
      </figcaption>
    </figure>
  );
}
