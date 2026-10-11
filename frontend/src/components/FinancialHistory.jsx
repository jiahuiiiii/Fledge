import { useId, useLayoutEffect, useRef, useState } from "react";
import EvidenceButton from "./EvidenceButton";
import FinancialEvidence from "./FinancialEvidence";
import TermHelp from "./TermHelp";
import {
  number,
  metric,
  money,
  day,
  historyPath,
  historyNotes,
} from "../lib/financialStory";
import { forecastAmount, forecastPath } from "../lib/revenueForecasts";

function Evidence({ rows, title, label }) {
  return (
    <EvidenceButton
      title={title}
      label={label}
      className="financial-figure-link"
    >
      <FinancialEvidence rows={rows} />
    </EvidenceButton>
  );
}
export default function FinancialHistory({
  rows,
  series,
  active,
  onSelect,
  label,
  forecasts = [],
  periodKind,
  onForecast,
}) {
  const id = useId();
  const viewport = useRef(null);
  const [width, setWidth] = useState(870);
  useLayoutEffect(() => {
    const element = viewport.current;
    if (!element) return;
    const resize = () => setWidth(Math.max(640, element.clientWidth));
    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(element);
    return () => observer.disconnect();
  }, [rows.length]);
  const [enabled, setEnabled] = useState(() =>
    series.slice(0, 3).map((row) => row.key),
  );
  const future = enabled.includes("revenue") ? forecasts : [];
  const forecastIdentity = future.map((point) => point.id).join("|");
  useLayoutEffect(() => {
    if (forecastIdentity && viewport.current) {
      viewport.current.scrollLeft =
        viewport.current.scrollWidth - viewport.current.clientWidth;
    }
  }, [forecastIdentity, width]);
  const values = rows
    .flatMap((period) =>
      enabled.map((key) => number(metric(period, key)?.value)),
    )
    .filter((v) => v != null && Math.abs(v) <= 1e15)
    .concat(future.flatMap((p) => [p.low, p.high]));
  const min = Math.min(0, ...values),
    max = Math.max(0, ...values),
    span = max - min || 1;
  const first = Date.parse(rows[0]?.end),
    last = Math.max(
      Date.parse(rows.at(-1)?.end),
      ...future.map((p) => Date.parse(p.end)),
    );
  const right = width - 44;
  const x = (row) =>
    94 + ((Date.parse(row.end) - first) / (last - first || 1)) * (right - 94);
  const y = (value) => 42 + ((max - value) / span) * 230;
  const maxGapDays = periodKind === "annual" ? 420 : 110;
  const notes = series
    .filter((s) => enabled.includes(s.key))
    .flatMap((s) =>
      historyNotes(rows, s.key, maxGapDays).map((note) => ({
        ...note,
        label: s.label,
      })),
    );
  return (
    <div className="financial-history-chart">
      <div
        className="financial-chart-legend"
        role="group"
        aria-label={`${label} measures`}
      >
        {series.map((s) => (
          <button
            key={s.key}
            className={`story-series series-${s.tone}`}
            aria-pressed={enabled.includes(s.key)}
            onClick={() =>
              setEnabled((old) =>
                old.includes(s.key)
                  ? old.filter((key) => key !== s.key)
                  : [...old, s.key],
              )
            }
          >
            <i aria-hidden="true" />
            {s.label}
          </button>
        ))}
      </div>
      {future.length > 0 && (
        <div
          className="revenue-forecast-legend"
          aria-label="Revenue line styles"
        >
          <span>
            <i className="forecast-key reported" />
            Reported revenue
          </span>
          {future.some((p) => p.kind === "analyst") && (
            <span>
              <i className="forecast-key analyst" />
              Analyst forecast · dotted
            </span>
          )}
          {future.some((p) => p.kind === "management") && (
            <span>
              <i className="forecast-key management" />
              Management guidance · dotted
            </span>
          )}
          {future.some((point) => point.low !== point.high) && (
            <span className="forecast-range-key">
              Bars show low–high estimates
            </span>
          )}
        </div>
      )}
      {rows.length ? (
        <>
          <p className="story-swipe-hint">
            Swipe across the chart on a small screen. Choose a date below to
            inspect the figures.
          </p>
          <div
            ref={viewport}
            className="story-chart-viewport"
            tabIndex={0}
            role="region"
            aria-label={`${label} chart`}
          >
            <svg
              className="story-history-svg"
              viewBox={`0 0 ${width} 322`}
              width={width}
              height="322"
              style={{ width, minWidth: width }}
              role={future.length ? "group" : "img"}
              aria-labelledby={`${id}-chart-title`}
            >
              <title id={`${id}-chart-title`}>
                {label}. Reported values on one shared dollar scale,{" "}
                {day(rows[0].end)} to {day(rows.at(-1).end)}. Missing values and
                changes in measure definition break the lines. Revenue label
                changes are explained in chart notes.
                {future.length > 0 &&
                  " Dotted revenue lines show analyst forecasts and management guidance, not reported results. Vertical bars show estimate ranges."}
              </title>
              {future.length > 0 && (
                <g className="revenue-future-area">
                  <rect
                    x={x(rows.at(-1))}
                    y="10"
                    width={Math.max(0, right - x(rows.at(-1)))}
                    height="264"
                  />
                  <line
                    x1={x(rows.at(-1))}
                    x2={x(rows.at(-1))}
                    y1="12"
                    y2="274"
                  />
                  <text x={x(rows.at(-1)) + 10} y="26">
                    Forecast
                  </text>
                </g>
              )}
              {[0, 0.25, 0.5, 0.75, 1].map((f) => (
                <g key={f} className="story-grid">
                  <line
                    x1="94"
                    x2={right}
                    y1={y(min + span * f)}
                    y2={y(min + span * f)}
                  />
                  <text x="82" y={y(min + span * f) + 4} textAnchor="end">
                    {money(min + span * f)}
                  </text>
                </g>
              ))}
              <line
                className="story-zero"
                x1="94"
                x2={right}
                y1={y(0)}
                y2={y(0)}
              />
              {series
                .filter((s) => enabled.includes(s.key))
                .map((s) => (
                  <g key={s.key} className={`story-series series-${s.tone}`}>
                    <path d={historyPath(rows, s.key, x, y, maxGapDays)} />
                    {rows.map((row) => {
                      const value = number(metric(row, s.key)?.value);
                      return value != null && Math.abs(value) <= 1e15 ? (
                        <circle
                          key={row.id}
                          cx={x(row)}
                          cy={y(value)}
                          r={row.id === active?.id ? 5 : 3}
                        />
                      ) : null;
                    })}
                  </g>
                ))}
              {["analyst", "management"].map((kind) => {
                const points = future.filter((p) => p.kind === kind);
                return (
                  points.length > 0 && (
                    <g
                      key={kind}
                      className={`revenue-forecast-line forecast-${kind}`}
                    >
                      <path
                        d={forecastPath(points, rows.at(-1), periodKind, x, y)}
                      />
                      {points.map((point) => (
                        <g
                          key={point.id}
                          className="revenue-forecast-point"
                          role="button"
                          tabIndex={0}
                          aria-label={`${kind === "analyst" ? "Analyst forecast" : "Management guidance"}: ${forecastAmount(point.value, point.assumedCurrency ? "USD" : point.currency, point.approximate)}, period ending ${day(point.end)}${point.assumedCurrency ? ", USD assumed" : ""}. Open evidence.`}
                          onClick={() => onForecast?.(point)}
                          onKeyDown={(event) => {
                            if (event.key === "Enter" || event.key === " ") {
                              event.preventDefault();
                              onForecast?.(point);
                            }
                          }}
                        >
                          <rect
                            className="forecast-hit"
                            x={x(point) - 22}
                            y={y(point.value) - 22}
                            width="44"
                            height="44"
                            rx="6"
                          />
                          <line
                            className="forecast-range"
                            x1={x(point)}
                            x2={x(point)}
                            y1={y(point.high)}
                            y2={y(point.low)}
                          />
                          {[point.low, point.high].map((v, index) => (
                            <line
                              key={index}
                              className="forecast-range"
                              x1={x(point) - 6}
                              x2={x(point) + 6}
                              y1={y(v)}
                              y2={y(v)}
                            />
                          ))}
                          {kind === "analyst" ? (
                            <circle cx={x(point)} cy={y(point.value)} r="5" />
                          ) : (
                            <path
                              className="forecast-diamond"
                              d={`M${x(point)},${y(point.value) - 6} l6,6 l-6,6 l-6,-6 Z`}
                            />
                          )}
                          <title>
                            {forecastAmount(point.low, point.currency)} –{" "}
                            {forecastAmount(point.high, point.currency)} ·{" "}
                            {point.sourceLabel}
                            {point.assumedCurrency
                              ? " · USD assumed for this chart"
                              : ""}
                          </title>
                        </g>
                      ))}
                    </g>
                  )
                );
              })}
              {active && (
                <line
                  className="story-selection"
                  x1={x(active)}
                  x2={x(active)}
                  y1="16"
                  y2="276"
                />
              )}
              {rows.map((row, index) => (
                <g key={row.id}>
                  {(index === 0 ||
                    index === rows.length - 1 ||
                    (rows.length < 8 && index % 2 === 0 && !future.length)) && (
                    <text
                      className="story-date"
                      x={x(row)}
                      y={
                        future.length &&
                        index === rows.length - 1 &&
                        right - x(row) < 190
                          ? "292"
                          : "308"
                      }
                      textAnchor={
                        index === 0
                          ? "start"
                          : index === rows.length - 1
                            ? "end"
                            : "middle"
                      }
                    >
                      {day(row.end)}
                    </text>
                  )}
                  <rect
                    className="story-chart-hit"
                    x={x(row) - 12}
                    y="14"
                    width="24"
                    height="266"
                    onPointerEnter={() => onSelect(row.id)}
                    onClick={() => onSelect(row.id)}
                  >
                    <title>{day(row.end)}</title>
                  </rect>
                </g>
              ))}
              {future.length > 0 &&
                [...new Set(future.map((p) => p.end))]
                  .filter((_, i, all) => i === all.length - 1)
                  .map((end) => (
                    <text
                      key={end}
                      className="story-date forecast-date"
                      x={x({ end })}
                      y="308"
                      textAnchor="end"
                    >
                      {day(end)} · estimate
                    </text>
                  ))}
            </svg>
          </div>
          <label className="story-date-slider">
            Inspect reporting date{" "}
            <input
              aria-label={`${label} reporting date`}
              type="range"
              min="0"
              max={rows.length - 1}
              value={Math.max(
                0,
                rows.findIndex((row) => row.id === active?.id),
              )}
              aria-valuetext={day(active?.end)}
              onChange={(e) => onSelect(rows[Number(e.target.value)].id)}
            />
            <strong>{day(active?.end)}</strong>
          </label>
          <div className="story-selected-values" aria-live="polite">
            {series
              .filter((s) => enabled.includes(s.key))
              .map((s) => {
                const row = metric(active, s.key);
                const netScope =
                  s.key !== "net_income"
                    ? null
                    : row?.label ===
                        "Net result including non-controlling interests"
                      ? {
                          caption:
                            "Whole group, including other owners’ share.",
                          explanation:
                            "This figure includes the profit or loss belonging to other owners of subsidiaries, as well as the parent company. The filing calls those other owners’ share ‘non-controlling interests’.",
                        }
                      : row?.label === "Net income attributable to parent"
                        ? {
                            caption: "Parent company’s share.",
                            explanation:
                              "This figure is the profit or loss attributable to the parent company. It excludes the share belonging to other owners of subsidiaries.",
                          }
                        : null;
                return (
                  <article
                    className={`story-series series-${s.tone}`}
                    key={s.key}
                  >
                    <span className="story-stat-label">
                      {s.label}
                      <TermHelp term={s.key} context={netScope?.explanation} />
                    </span>
                    <Evidence
                      rows={[row]}
                      title={`${s.label} · ${day(active?.end)}`}
                      label={<strong>{money(row?.value)}</strong>}
                    />
                    <small>
                      {row?.start
                        ? `${day(row.start)} – ${day(row.end)}`
                        : row?.end
                          ? `At ${day(row.end)}`
                          : "No matching figure"}
                    </small>
                    {s.key === "net_income" && (
                      <>
                        <small>After expenses, interest and taxes.</small>
                        <small>{netScope?.caption || row?.label}</small>
                      </>
                    )}
                    {s.key === "free_cash_flow" &&
                      row?.spending_basis === "productive_assets" && (
                        <small>
                          Includes cash spending on software and intangible
                          assets
                        </small>
                      )}
                    {row?.value == null && row?.reason && (
                      <small>{row.reason}</small>
                    )}
                    {periodKind === "quarter" &&
                      row?.calculated &&
                      row?.value != null && (
                        <small>
                          Calculated from the fiscal year minus its first nine
                          months.
                        </small>
                      )}
                  </article>
                );
              })}
          </div>
        </>
      ) : (
        <p>No compatible saved history is available.</p>
      )}
      <p className="story-footnote">
        Shared scale · Fiscal reporting dates · Choose a figure to see its
        source.
      </p>
      {notes.length > 0 && (
        <details className="story-history-notes">
          <summary>Chart gaps &amp; reporting changes · {notes.length}</summary>
          {notes.map((note, index) => (
            <article key={index}>
              <strong>
                {note.label} · {day(note.start)}
                {note.end !== note.start && ` – ${day(note.end)}`}
              </strong>
              <p>{note.text}</p>
              <Evidence
                rows={note.metrics}
                title={`${note.label} · chart note`}
                label="Figures & sources"
              />
            </article>
          ))}
        </details>
      )}
    </div>
  );
}
