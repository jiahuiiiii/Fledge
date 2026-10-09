import { useEffect, useId, useRef, useState } from "react";
import { api } from "../api/client";
import EvidenceButton from "./EvidenceButton";
import SectorPosition from "./SectorPosition";
import RevenueFlow from "./RevenueFlow";
import RevenueBreakdown from "./RevenueBreakdown";
import Select from "./Select";
import LoadingSkeleton from "./LoadingSkeleton";
import {
  number,
  metric,
  money,
  percent,
  day,
  previousYear,
  incomeInsights,
  balanceInsights,
  balanceBlocks,
  borrowingTrend,
  blockLayout,
  historyPath,
} from "../lib/financialStory";
import "./FinancialsPage.css";

function Evidence({ rows, title = "Financial reading · evidence" }) {
  return (
    <EvidenceButton title={title}>
      {(rows || []).filter(Boolean).map((row, index) => (
        <section className="story-evidence-row" key={`${row.key}-${index}`}>
          <h3>{row.label}</h3>
          <p>
            {row.start ? `${day(row.start)} – ` : "At "}
            {day(row.end)}
          </p>
          <p>
            {row.value == null
              ? "Unavailable"
              : `Exact value: ${row.value} ${row.unit || "USD"}`}
          </p>
          {row.formula && <p>Calculation: {row.formula}</p>}
          {row.reason && <p>{row.reason}</p>}
          {row.explanation && <p>{row.explanation}</p>}
          {row.inputs?.map((input, i) => (
            <p key={i}>
              {input.concept} · {input.value} {input.unit} ·{" "}
              {input.start ? `${day(input.start)} – ` : "At "}
              {day(input.end)} · {input.accession}
              {input.filing_url && (
                <>
                  {" "}
                  ·{" "}
                  <a href={input.filing_url} target="_blank" rel="noreferrer">
                    Original {input.form} filing ↗
                  </a>
                </>
              )}
            </p>
          ))}
        </section>
      ))}
    </EvidenceButton>
  );
}
function Insights({ readings }) {
  return (
    <div className="financial-insights">
      {readings.map((reading, index) => (
        <article
          className={`financial-insight insight-${reading.tone}`}
          key={index}
        >
          <span className="insight-mark" aria-hidden="true">
            {reading.tone === "unknown"
              ? "?"
              : reading.tone === "caution"
                ? "↘"
                : reading.tone === "positive"
                  ? "↗"
                  : "i"}
          </span>
          <div>
            <h3>{reading.title}</h3>
            <p>{reading.text}</p>
            {reading.detail && (
              <p className="insight-detail">{reading.detail}</p>
            )}
            {reading.rows?.length > 0 && (
              <Evidence
                rows={reading.rows}
                title={`${reading.title} · evidence`}
              />
            )}
          </div>
        </article>
      ))}
    </div>
  );
}
const incomeSeries = [
  { key: "revenue", label: "Revenue", tone: "revenue" },
  { key: "net_income", label: "Net result", tone: "earnings" },
  { key: "free_cash_flow", label: "Free cash flow", tone: "cashflow" },
  { key: "operating_cash", label: "Operating cash flow", tone: "operations" },
  { key: "operating_income", label: "Operating profit", tone: "operating" },
];
const balanceSeries = [
  { key: "debt", label: "Borrowing", tone: "debt" },
  { key: "equity", label: "Book equity", tone: "revenue" },
  { key: "cash", label: "Cash & equivalents", tone: "earnings" },
];
function HistoryChart({ rows, series, active, onSelect, label }) {
  const id = useId();
  const [enabled, setEnabled] = useState(() =>
    series.slice(0, 3).map((row) => row.key),
  );
  const values = rows
    .flatMap((period) =>
      enabled.map((key) => number(metric(period, key)?.value)),
    )
    .filter((v) => v != null && Math.abs(v) <= 1e15);
  const min = Math.min(0, ...values),
    max = Math.max(0, ...values),
    span = max - min || 1;
  const first = Date.parse(rows[0]?.end),
    last = Date.parse(rows.at(-1)?.end);
  const x = (row) =>
    94 + ((Date.parse(row.end) - first) / (last - first || 1)) * 738;
  const y = (value) => 22 + ((max - value) / span) * 252;
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
      {rows.length ? (
        <>
          <p className="story-swipe-hint">
            Swipe across the chart on a small screen. Choose a date below to
            inspect the figures.
          </p>
          <div
            className="story-chart-viewport"
            tabIndex={0}
            role="region"
            aria-label={`${label} chart`}
          >
            <svg
              className="story-history-svg"
              viewBox="0 0 870 322"
              role="img"
              aria-labelledby={`${id}-chart-title`}
            >
              <title id={`${id}-chart-title`}>
                {label}. Reported values on one shared dollar scale,{" "}
                {day(rows[0].end)} to {day(rows.at(-1).end)}. Missing values and
                changes in reporting basis break the lines.
              </title>
              {[0, 0.25, 0.5, 0.75, 1].map((f) => (
                <g key={f} className="story-grid">
                  <line
                    x1="94"
                    x2="832"
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
                x2="832"
                y1={y(0)}
                y2={y(0)}
              />
              {series
                .filter((s) => enabled.includes(s.key))
                .map((s) => (
                  <g key={s.key} className={`story-series series-${s.tone}`}>
                    <path d={historyPath(rows, s.key, x, y)} />
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
                    (rows.length < 8 && index % 2 === 0)) && (
                    <text
                      className="story-date"
                      x={x(row)}
                      y="308"
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
                return (
                  <article
                    className={`story-series series-${s.tone}`}
                    key={s.key}
                  >
                    <span>{s.label}</span>
                    <strong>{money(row?.value)}</strong>
                    <small>
                      {row?.start
                        ? `${day(row.start)} – ${day(row.end)}`
                        : row?.end
                          ? `At ${day(row.end)}`
                          : "No matching figure"}
                    </small>
                    {s.key === "net_income" && <small>{row?.label}</small>}
                    {row && (
                      <Evidence rows={[row]} title={`${s.label} · evidence`} />
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
        Every line uses the same scale, including zero and negative values. Gaps
        stay visible. Dates are fiscal report dates; a line between reports does
        not imply results were measured in between.
      </p>
    </div>
  );
}
function Heading({ number: n, title, children }) {
  return (
    <header className="financial-story-heading">
      <div>
        <span aria-hidden="true">{n}</span>
        <h2>{title}</h2>
      </div>
      <p>{children}</p>
    </header>
  );
}
function BalancePairs({ period }) {
  const pairs = [
    {
      title: "Short term",
      explanation:
        "Assets expected to be used or collected, and obligations due, within the normal operating cycle or about one year.",
      keys: ["current_assets", "current_liabilities"],
    },
    {
      title: "Long term",
      explanation:
        "Resources and obligations classified beyond the current period. These assets are not all available cash.",
      keys: ["noncurrent_assets", "noncurrent_liabilities"],
    },
  ];
  const values = pairs
    .flatMap((pair) =>
      pair.keys.map((key) => number(metric(period, key)?.value)),
    )
    .filter((v) => v != null && v >= 0);
  const maximum = Math.max(1, ...values);
  return (
    <div className="story-balance-pairs">
      {pairs.map((pair) => (
        <article key={pair.title}>
          <h3>{pair.title}</h3>
          <div className="story-pair-bars">
            {pair.keys.map((key, index) => {
              const row = metric(period, key),
                value = number(row?.value);
              return (
                <div className={`story-pair-column pair-${index}`} key={key}>
                  <strong>{money(row?.value)}</strong>
                  <div className="story-pair-track" aria-hidden="true">
                    {value != null && value >= 0 && (
                      <span style={{ height: `${(value / maximum) * 100}%` }} />
                    )}
                  </div>
                  <span>{index === 0 ? "Assets" : "Liabilities"}</span>
                  {row && (
                    <Evidence rows={[row]} title={`${row.label} · evidence`} />
                  )}
                </div>
              );
            })}
          </div>
          <p>{pair.explanation}</p>
        </article>
      ))}
    </div>
  );
}
function BalanceMap({ period, side }) {
  const rows = balanceBlocks(period, side);
  const total = number(metric(period, "assets")?.value);
  const rectangles = rows ? blockLayout(rows, 500, 320) : [];
  return (
    <article className="story-balance-map">
      <h3>{side === "assets" ? "Assets" : "Liabilities + book equity"}</h3>
      <p>
        {money(total)} · at {day(period?.end)}
      </p>
      {rows ? (
        <>
          <div
            className="story-map-blocks"
            role="img"
            aria-label={`${side === "assets" ? "Asset" : "Funding"} breakdown, area proportional to total assets`}
          >
            {rectangles.map((row) => (
              <div
                className={`story-map-block block-${row.key}`}
                key={row.key}
                style={{
                  left: `${row.x / 5}%`,
                  top: `${row.y / 3.2}%`,
                  width: `${row.width / 5}%`,
                  height: `${row.height / 3.2}%`,
                }}
                title={`${row.label}: ${money(row.value)}`}
              >
                {row.width > 90 && row.height > 75 && (
                  <>
                    <span>{row.label}</span>
                    <strong>{money(row.value)}</strong>
                  </>
                )}
              </div>
            ))}
          </div>
          <div className="story-map-legend">
            {rows.map((row) => (
              <div className={`block-${row.key}`} key={row.key}>
                <i aria-hidden="true" />
                <span>
                  {row.label}
                  <small>
                    {((number(row.value) / total) * 100).toFixed(1)}% of total
                    assets
                  </small>
                </span>
                <strong>{money(row.value)}</strong>
                <Evidence rows={[row]} title={`${row.label} · evidence`} />
              </div>
            ))}
          </div>
        </>
      ) : (
        <p className="story-gap">
          A nonnegative, reconciled breakdown is unavailable. Inspect the
          individual reported figures below.
        </p>
      )}
    </article>
  );
}
export default function FinancialsPage({ instrumentId, workspace, visible }) {
  const [attempt, setAttempt] = useState(0);
  const [story, setStory] = useState(null),
    [error, setError] = useState("");
  const [mode, setMode] = useState("trailing"),
    [incomeId, setIncomeId] = useState(""),
    [balanceId, setBalanceId] = useState("");
  const generation = useRef(0);
  useEffect(() => {
    if (!visible) return;
    const token = ++generation.current;
    api
      .financialStory(instrumentId)
      .then((data) => {
        if (token === generation.current) {
          setStory(data);
          setError("");
        }
      })
      .catch((failure) => {
        if (token === generation.current) setError(failure.message);
      });
    return () => {
      generation.current++;
    };
  }, [
    instrumentId,
    visible,
    workspace.financial_depth?.payload_id,
    workspace.financial_depth?.status,
    attempt,
  ]);
  const depth = workspace.financial_depth;
  const safe =
    depth?.status === "unavailable"
      ? { status: "unavailable", reason: depth.reason }
      : story?.status === "available" &&
          depth?.payload_id &&
          depth.payload_id !== story.payload_id
        ? null
        : story;
  const incomeRows = safe?.status === "available" ? safe[mode] || [] : [];
  const balances = safe?.status === "available" ? safe.balances || [] : [];
  const active =
    incomeRows.find((row) => row.id === incomeId) || incomeRows.at(-1);
  const balance =
    balances.find((row) => row.id === balanceId) || balances.at(-1);
  const past = previousYear(incomeRows, active);
  const readings = incomeInsights(active, past);
  const positionReadings = balanceInsights(balance);
  const debt = metric(balance, "debt");
  const ocf = metric(active, "operating_cash"),
    coverage = metric(active, "interest_coverage");
  const debtReadings = positionReadings.slice(1);
  const trend = borrowingTrend(balance, previousYear(balances, balance));
  if (trend) debtReadings.push(trend);
  if (
    balance?.end === active?.end &&
    number(debt?.value) > 0 &&
    number(ocf?.value) != null
  )
    debtReadings.push({
      tone: "neutral",
      title: "Operating cash flow relative to borrowing",
      text: `${money(ocf.value)} generated over ${day(ocf.start)} – ${day(ocf.end)}, compared with ${money(debt.value)} of borrowing at the end — ${((number(ocf.value) / number(debt.value)) * 100).toFixed(1)}%.`,
      detail:
        "This comparison is not a repayment schedule. Capital spending, other cash uses, restrictions and debt maturity dates still matter.",
      rows: [ocf, debt],
    });
  if (number(coverage?.value) != null)
    debtReadings.push({
      tone: number(coverage.value) >= 0 ? "neutral" : "caution",
      title: "Operating profit compared with interest expense",
      text: `${number(coverage.value).toFixed(1)} times the reported non-operating interest expense over ${day(coverage.start)} – ${day(coverage.end)}.`,
      detail:
        "Operating profit is not cash available for interest payments; this is not a credit assessment.",
      rows: [coverage],
    });
  else
    debtReadings.push({
      tone: "unknown",
      title: "Interest comparison unavailable",
      text: "Matching operating profit and non-operating interest expense are needed.",
      rows: [coverage].filter(Boolean),
    });
  return (
    <div className="financials-story">
      <SectorPosition
        instrumentId={instrumentId}
        visible={visible}
        financials
      />
      <div className="financials-intro">
        <h2>What the financials show</h2>
        <p>
          Follow the company’s sales, profit, cash generation and obligations.
          Each reading uses saved filing figures and shows what supports it.
        </p>
        {safe?.checked_at && (
          <p className="story-footnote">
            SEC filing data checked {day(safe.checked_at)}.{" "}
            {workspace.performance?.source_status?.last_error
              ? "The latest source check failed; these are retained figures."
              : "Selecting a date reads saved data."}
          </p>
        )}
      </div>
      {!safe && !error && (
        <LoadingSkeleton
          variant="chart"
          label="Reading saved financial history…"
        />
      )}
      {error && (
        <p className="warning" role="alert">
          {error}{" "}
          <button onClick={() => setAttempt((old) => old + 1)}>
            Read saved financials again
          </button>
        </p>
      )}
      {safe && safe.status !== "available" && (
        <p className="story-gap">{safe.reason}</p>
      )}
      {safe && (
        <>
          <section
            className="financial-story-section"
            aria-label="Revenue and expense story"
          >
            <Heading number="1" title="How sales become profit">
              Follow revenue through the company’s costs to the reported result.
              Choose a period and inspect any figure.
            </Heading>
            <RevenueFlow
              data={workspace.income_flow}
              segments={workspace.segment_revenue}
              compactHeading
            />
            <details className="story-secondary">
              <summary>Revenue by segment, product &amp; geography</summary>
              <RevenueBreakdown data={workspace.segment_revenue} />
            </details>
          </section>
          <section
            className="financial-story-section"
            aria-label="Earnings and cash-flow history"
          >
            <Heading number="2" title="Sales, earnings & cash over time">
              Growth matters alongside how much profit and cash the company
              generates. Select a date to read that period.
            </Heading>
            <div
              className="story-period-controls"
              role="group"
              aria-label="Financial history period basis"
            >
              {[
                ["trailing", "Trailing 12 months"],
                ["annual", "Annual reports"],
              ].map(([key, label]) => (
                <button
                  key={key}
                  aria-pressed={mode === key}
                  onClick={() => {
                    setMode(key);
                    setIncomeId("");
                  }}
                >
                  {label}
                </button>
              ))}
            </div>
            <HistoryChart
              key={mode}
              rows={incomeRows}
              series={incomeSeries}
              active={active}
              onSelect={setIncomeId}
              label="Sales, earnings and cash flow"
            />
            <Insights readings={readings} />
          </section>
          <section
            className="financial-story-section financial-position"
            aria-label="What it owns and owes"
          >
            <Heading
              number="3"
              title="Can current assets cover near-term obligations?"
            >
              Compare matching balances at one reporting date. Current and
              noncurrent amounts describe different timing.
            </Heading>
            {balance && (
              <label className="story-balance-select">
                Balance-sheet date
                <Select
                  value={balance.id}
                  onChange={(e) => setBalanceId(e.target.value)}
                >
                  {balances.map((row) => (
                    <option key={row.id} value={row.id}>
                      {day(row.end)} · {row.form}
                    </option>
                  ))}
                </Select>
              </label>
            )}
            <BalancePairs period={balance} />
            <Insights readings={positionReadings.slice(0, 1)} />
            <p className="story-footnote">
              Both short- and long-term charts use the same zero-based dollar
              scale. Liabilities include obligations beyond borrowing.
            </p>
          </section>
          <section
            className="financial-story-section"
            aria-label="Borrowing and equity history"
          >
            <Heading
              number="4"
              title="How borrowing compares with cash & equity"
            >
              See how the reported balances change together. Borrowing, cash and
              book equity are separate measures.
            </Heading>
            <HistoryChart
              rows={balances}
              series={balanceSeries}
              active={balance}
              onSelect={setBalanceId}
              label="Borrowing, cash and equity"
            />
            <Insights readings={debtReadings} />
          </section>
          <section
            className="financial-story-section"
            aria-label="Balance-sheet breakdown"
          >
            <Heading number="5" title="What makes up the balance sheet?">
              Assets show recorded resources. Liabilities and book equity show
              how those resources are accounted for.
            </Heading>
            <div className="story-balance-maps">
              <BalanceMap period={balance} side="assets" />
              <BalanceMap period={balance} side="funding" />
            </div>
            <p className="story-footnote">
              Each block’s size shows its share of total assets. Other &amp;
              unclassified includes missing categories. Book values may differ
              from resale values; goodwill and intangible assets are not cash.
            </p>
            <details className="story-secondary">
              <summary>All balance figures &amp; evidence</summary>
              <div className="story-balance-figures">
                {balance?.metrics.map((row) => (
                  <article key={row.key}>
                    <span>{row.label}</span>
                    <strong>
                      {row.unit === "percent"
                        ? percent(row.value)
                        : money(row.value)}
                    </strong>
                    <Evidence rows={[row]} title={`${row.label} · evidence`} />
                  </article>
                ))}
              </div>
            </details>
          </section>
        </>
      )}
      {safe?.limitations && (
        <details className="story-secondary">
          <summary>Financial definitions &amp; coverage</summary>
          {safe.limitations.map((line) => (
            <p key={line}>{line}</p>
          ))}
          <p>
            Learn how to read financial statements in the{" "}
            <a
              href="https://www.sec.gov/investor/pubs/begfinstmtguide.htm"
              target="_blank"
              rel="noreferrer"
            >
              SEC guide ↗
            </a>
            .
          </p>
          <p>
            First saved source observation: {day(safe.first_recorded_at)}.
            Method: {safe.method}. These readings do not create an AI assessment
            or change your monitoring.
          </p>
        </details>
      )}
    </div>
  );
}
