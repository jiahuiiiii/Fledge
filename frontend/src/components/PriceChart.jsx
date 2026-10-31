import { useEffect, useLayoutEffect, useRef, useState } from "react";
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
  const lastDate = prices.at(-1)?.date;
  useEffect(() => {
    setHover(null);
    setSelected(null);
  }, [lastDate]);
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
            USD ·{" "}
            {fictional
              ? "fictional prices"
              : chosen.provisional
                ? "latest session price · provisional"
                : "daily close"}{" "}
            · {chosen.date}
          </small>
        </div>
        <div className="chart-controls">
          <div className="segmented" role="group" aria-label="Date range">
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
          </div>
          <div className="segmented" role="group" aria-label="Chart type">
            <button
              className="icon-only"
              aria-pressed={mode === "Candles"}
              aria-label="Candlestick chart"
              title="Candlestick chart"
              onClick={() => setMode("Candles")}
            >
              <svg
                viewBox="0 0 16 16"
                width="16"
                height="16"
                aria-hidden="true"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.4"
                strokeLinecap="round"
              >
                <path d="M4.5 2v12M11.5 1.5v13" />
                <rect
                  x="2.5"
                  y="5"
                  width="4"
                  height="6"
                  rx=".5"
                  fill="currentColor"
                />
                <rect x="9.5" y="4" width="4" height="7" rx=".5" />
              </svg>
            </button>
            <button
              className="icon-only"
              aria-pressed={mode === "Line"}
              aria-label="Line chart"
              title="Line chart"
              onClick={() => setMode("Line")}
            >
              <svg
                viewBox="0 0 16 16"
                width="16"
                height="16"
                aria-hidden="true"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M1.5 11.5l4-4 3 2.5 6-7" />
              </svg>
            </button>
          </div>
        </div>
      </div>
      <svg
        ref={chartRef}
        className="price-chart"
        viewBox={`0 0 ${w} ${h}`}
        role="img"
        aria-label={`${label} ${mode.toLowerCase()} chart, ${first.date} to ${last.date}. ${last.provisional ? "Provisional latest price" : "Last close"} ${last.close}.`}
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
                stroke="#27272a"
                strokeDasharray="3 5"
              />
              <text
                x={w - 4}
                textAnchor="end"
                y={y(value) + 4}
                fill="#8f8f99"
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
          stroke="#80808a"
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
              {chosen.close.toFixed(2)}
              {chosen.provisional ? " (provisional)" : ""} · Vol{" "}
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
