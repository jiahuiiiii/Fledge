import { targetChange } from "../lib/targetRange";

const usd = (v) =>
  `US$${Number(v).toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

// Saved daily closes with the analysts' low, mean and high targets drawn to the
// right, each labelled with its distance from the last price. Targets are
// opinions; the chart shows them, it does not forecast.
export default function TargetChart({ bars = [], range }) {
  const closes = bars.slice(-130).filter((b) => Number.isFinite(Number(b.close)));
  const current = range.current ?? (closes.length ? Number(closes.at(-1).close) : null);
  const w = 640,
    h = 220,
    left = 8,
    split = 440,
    right = 632;
  const values = [range.low, range.mean, range.high, current, ...closes.map((b) => Number(b.close))].filter((v) => v != null);
  const lo = Math.min(...values),
    hi = Math.max(...values),
    pad = (hi - lo) * 0.1 || hi * 0.05;
  const y = (v) => 14 + ((hi + pad - v) / (hi + pad - (lo - pad))) * (h - 28);
  const x = (i) => (closes.length > 1 ? left + (i * (split - left)) / (closes.length - 1) : split);
  const path = closes.map((b, i) => `${i ? "L" : "M"}${x(i).toFixed(1)} ${y(Number(b.close)).toFixed(1)}`).join("");
  const targets = [
    ["High", range.high],
    ["Mean", range.mean],
    ["Low", range.low],
  ];
  const from = closes.length ? { x: x(closes.length - 1), y: y(current ?? Number(closes.at(-1).close)) } : { x: split, y: y(current ?? range.mean) };
  return (
    <svg
      className="target-chart"
      viewBox={`0 0 ${w} ${h}`}
      role="img"
      aria-label={`Analyst targets: low ${usd(range.low)}, mean ${usd(range.mean)}, high ${usd(range.high)}.${current ? ` Last price ${usd(current)}.` : ""}`}
    >
      <rect x={split + 12} y={y(range.high)} width={right - split - 12} height={Math.max(2, y(range.low) - y(range.high))} className="target-chart__band" />
      {path && <path d={path} className="target-chart__line" fill="none" />}
      {current != null && <line x1={left} x2={right} y1={y(current)} y2={y(current)} className="target-chart__now" />}
      {targets.map(([name, v]) => {
        const change = current ? (v / current - 1) * 100 : null;
        const tone = change == null ? "" : change < 0 ? "is-down" : "is-up";
        return (
          <g key={name} className={`target-chart__target ${tone}`}>
            <line x1={from.x} y1={from.y} x2={split + 12} y2={y(v)} />
            <circle cx={split + 12} cy={y(v)} r="4" />
            <text x={split + 22} y={y(v) - 3}>{name} {usd(v)}</text>
            <text x={split + 22} y={y(v) + 10} className="target-chart__delta">{change == null ? "" : targetChange(change)}</text>
          </g>
        );
      })}
      {current != null && <circle cx={from.x} cy={from.y} r="4" className="target-chart__dot" />}
    </svg>
  );
}
