import { useLayoutEffect, useRef, useState } from "react";
export default function PriceChart({ prices, fictional = true }) {
  const chartRef = useRef(null);
  const [width, setWidth] = useState(780);
  useLayoutEffect(() => {
    if (!chartRef.current) return;
    const measure = (value) => {
      // Hidden retained views have zero width. Keep their last measured geometry.
      if (value > 0) setWidth(Math.max(260, Math.round(value)));
    };
    measure(chartRef.current.getBoundingClientRect().width);
    const observer = new ResizeObserver(([entry]) =>
      measure(entry.contentRect.width),
    );
    observer.observe(chartRef.current);
    return () => observer.disconnect();
  }, [prices.length]);
  const [range, setRange] = useState(fictional ? 64 : 63),
    [mode, setMode] = useState("Candles"),
    [hover, setHover] = useState(null),
    [selected, setSelected] = useState(null);
  if (!prices.length)
    return (
      <section className="price-unavailable">
        <span className="section-label">PRICE CONTEXT</span>
        <p>No price history available for this company.</p>
        <small>
          Financials and source evidence are available in the company views.
        </small>
      </section>
    );
  const points = prices.slice(-range),
    last = points.at(-1),
    first = points[0];
  const lo = Math.min(...points.map((p) => p.low)),
    hi = Math.max(...points.map((p) => p.high)),
    pad = Math.max((hi - lo) * 0.08, hi * 0.005, 0.01),
    low = lo - pad,
    high = hi + pad;
  const w = width,
    h = 180,
    x = (i) => 12 + (i * (w - 74)) / Math.max(1, points.length - 1),
    y = (v) => 10 + ((high - v) / (high - low)) * 125;
  const index = hover ?? selected ?? points.length - 1,
    chosen = points[index] || last,
    change = last.close - first.close;
  const maxVolume = Math.max(1, ...points.map((p) => p.volume ?? 0)),
    volumeHeight = (v) => (v == null ? 0 : (v / maxVolume) * 28);
  const barWidth = Math.max(1, Math.min(5, ((w - 74) / points.length) * 0.65));
  const hitWidth = (w - 74) / Math.max(1, points.length - 1);
  const label = fictional ? "Fictional" : "Yahoo Finance daily";
  const ranges = fictional
    ? [
        [20, "1M"],
        [64, "3M"],
      ]
    : [
        [21, "1M"],
        [63, "3M"],
        [126, "6M"],
        [366, "1Y"],
      ];
  return (
    <section
      className="price-panel"
      aria-label={
        fictional ? "Illustrative price chart" : "Historical price chart"
      }
    >
      <div className="chart-head">
        <div>
          <span className="price">{chosen.close.toFixed(2)}</span>
          <span className={change >= 0 ? "positive" : "negative"}>
            {change >= 0 ? "+" : ""}
            {change.toFixed(2)}{" "}
            <span className="muted">over visible range</span>
          </span>
          <small>
            USD · {fictional ? "fictional prices" : "daily close"} ·{" "}
            {chosen.date}
          </small>
        </div>
        <div className="segmented">
          {ranges.map(([n, title]) => (
            <button
              key={n}
              aria-pressed={range === n}
              onClick={() => {
                setRange(n);
                setHover(null);
                setSelected(null);
              }}
            >
              {title}
            </button>
          ))}
          <button
            aria-pressed={mode === "Line"}
            onClick={() => setMode(mode === "Line" ? "Candles" : "Line")}
          >
            {mode}
          </button>
        </div>
      </div>
      <svg
        ref={chartRef}
        className="price-chart"
        viewBox={`0 0 ${w} ${h}`}
        role="img"
        aria-label={`${label} ${mode.toLowerCase()} chart, ${first.date} to ${last.date}. Last close ${last.close}.`}
        onPointerLeave={() => setHover(null)}
      >
        {[0, 1, 2, 3].map((i) => {
          const value = low + ((high - low) * (i + 0.5)) / 4;
          return (
            <g key={i}>
              <line
                x1="0"
                x2={w - 53}
                y1={y(value)}
                y2={y(value)}
                stroke="#242a2e"
                strokeDasharray="3 5"
              />
              <text
                x={w - 4}
                textAnchor="end"
                y={y(value) + 4}
                fill="#88959c"
                fontSize="12"
              >
                {value.toFixed(2)}
              </text>
            </g>
          );
        })}
        {points.map((p, i) => (
          <g key={p.date}>
            {p.volume != null && (
              <rect
                x={x(i) - barWidth / 2}
                y={176 - volumeHeight(p.volume)}
                width={barWidth}
                height={volumeHeight(p.volume)}
                fill={p.close >= p.open ? "#273a36" : "#382d31"}
              />
            )}
            {mode === "Candles" && (
              <>
                <line
                  x1={x(i)}
                  x2={x(i)}
                  y1={y(p.high)}
                  y2={y(p.low)}
                  stroke={p.close >= p.open ? "#8cd7b6" : "#d48b97"}
                />
                <rect
                  x={x(i) - barWidth / 2}
                  y={Math.min(y(p.close), y(p.open))}
                  width={barWidth}
                  height={Math.max(1, Math.abs(y(p.open) - y(p.close)))}
                  fill={p.close >= p.open ? "#8cd7b6" : "#d48b97"}
                />
              </>
            )}
            <rect
              x={x(i) - hitWidth / 2}
              width={hitWidth}
              height={h}
              fill="transparent"
              onPointerEnter={() => setHover(i)}
              onClick={() => setSelected(i)}
            />
          </g>
        ))}
        {mode === "Line" && (
          <polyline
            points={points.map((p, i) => `${x(i)},${y(p.close)}`).join(" ")}
            fill="none"
            stroke="#b7e776"
            strokeWidth="2"
            pointerEvents="none"
          />
        )}
        <line
          x1={x(index)}
          x2={x(index)}
          y1="0"
          y2={h}
          stroke="#78838a"
          strokeDasharray="3 3"
          pointerEvents="none"
        />
      </svg>
      {!fictional && (
        <details className="price-inspection secondary-details">
          <summary>Inspect a trading session</summary>
          <div className="price-session">
            <label>
              Inspect trading session{" "}
              <input
                aria-label="Trading session"
                type="range"
                min="0"
                max={points.length - 1}
                value={selected ?? points.length - 1}
                onChange={(e) => {
                  setSelected(Number(e.target.value));
                  setHover(null);
                }}
                aria-valuetext={
                  (points[selected ?? points.length - 1] || last).date
                }
              />
            </label>
            <output aria-live="polite">
              {chosen.date} · O {chosen.open.toFixed(2)} · H{" "}
              {chosen.high.toFixed(2)} · L {chosen.low.toFixed(2)} · C{" "}
              {chosen.close.toFixed(2)} · Vol{" "}
              {chosen.volume == null
                ? "unknown"
                : chosen.volume.toLocaleString("en-US")}
            </output>
          </div>
        </details>
      )}
      <div className="chart-foot">
        <span>{first.date}</span>
        <span>{last.date}</span>
      </div>
    </section>
  );
}
