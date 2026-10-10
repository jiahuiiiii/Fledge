import { readableNote } from "../lib/readingNotes";
import { useEffect, useId, useRef, useState } from "react";
import Modal from "./Modal";
import FinancialEvidence from "./FinancialEvidence";
import Select from "./Select";
import { amount, day } from "./FinancialOverview";
import { flowLayout, matchingBreakdowns, shortLabel } from "../lib/incomeFlow";
import "./RevenueFlow.css";

const names = {
  trailing: "Past 12 months",
  annual: "Annual",
  quarter: "Quarterly",
};
const periodHelp = {
  trailing: "12 months ending at the latest report.",
  annual: "The company’s full financial year.",
  quarter: "One quarter, labelled by its ending date.",
};
const metricKeys = [
  "revenue",
  "cost",
  "gross",
  "expenses",
  "operating",
  "net_result",
  "net_items",
];

export default function RevenueFlow({
  data,
  segments,
  compactHeading = false,
  compactOverview = false,
}) {
  const id = useId();
  const [kind, setKind] = useState("");
  const [selection, setSelection] = useState("");
  const [category, setCategory] = useState("");
  const [geographyView, setGeographyView] = useState("");
  const [evidence, setEvidence] = useState(null);
  const timeline = useRef(null);
  const viewport = useRef(null);
  const [chartWidth, setChartWidth] = useState(0);
  const periods = data?.periods || [];
  const kinds = ["trailing", "annual", "quarter"].filter((name) =>
    periods.some((row) => row.kind === name),
  );
  const activeKind = kinds.includes(kind) ? kind : kinds[0];
  const choices = periods
    .filter((row) => row.kind === activeKind)
    .sort((a, b) => a.end.localeCompare(b.end));
  const selected =
    choices.find((row) => row.id === selection) || choices.at(-1);
  const mixes = matchingBreakdowns(selected, [
    ...(segments?.groups || []),
    ...(segments?.trailing_groups || []),
  ]);
  const activeCategory =
    category ||
    mixes.find((row) => row.kind === "Operating segments")?.kind ||
    mixes[0]?.kind ||
    "Total revenue";
  const revenueInputs =
    selected?.metrics.find((row) => row.key === "revenue")?.inputs || [];
  const hasFiling =
    revenueInputs.length > 0 &&
    revenueInputs.every((input) =>
      segments?.filing_urls?.includes(input.filing_url),
    );
  const categoryMixes = mixes.filter((row) => row.kind === activeCategory);
  const mix =
    categoryMixes.find((row) => row.view_label === geographyView) ||
    categoryMixes[0];
  const graph = flowLayout(selected, mix?.chartable ? mix : null, chartWidth);
  const connectedSources = graph?.nodes.some((row) => row.group);
  const values =
    selected?.metrics.filter((row) => metricKeys.includes(row.key)) || [];
  useEffect(() => setEvidence(null), [data, segments]);
  useEffect(() => {
    const element = timeline.current;
    if (!element) return;
    const reveal = () => {
      const active = element.querySelector('[aria-pressed="true"]');
      if (!active) return;
      const parent = element.getBoundingClientRect(),
        child = active.getBoundingClientRect();
      if (child.left < parent.left || child.right > parent.right)
        element.scrollLeft += child.left - parent.left - 6;
    };
    const observer = new ResizeObserver(reveal);
    observer.observe(element);
    reveal();
    return () => observer.disconnect();
  }, [selected?.id]);
  useEffect(() => {
    const element = viewport.current;
    if (!element) return;
    const observer = new ResizeObserver(([entry]) =>
      setChartWidth(entry.contentRect.width),
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, [selected?.id, Boolean(graph)]);
  if (!data) return null;
  function choose(value) {
    setSelection(value);
    setEvidence(null);
  }
  const sourceFigures = mix && (
    <div className="flow-source-figures" aria-label="Reported revenue sources">
      {mix.members.map((row) => (
        <button
          key={row.member}
          aria-haspopup="dialog"
          onClick={() => setEvidence({ ...row, group: mix })}
        >
          <span>{row.label}</span>
          <strong>{amount(row.value)}</strong>
          {mix.chartable && (
            <small>{Number(row.percentage).toFixed(1)}% of revenue</small>
          )}
        </button>
      ))}
    </div>
  );
  return (
    <section
      className="revenue-flow financial-chart-card"
      data-period={selected?.id}
      aria-labelledby={`${id}-heading`}
    >
      <div className="flow-heading">
        <div className={compactHeading ? "flow-heading-compact" : undefined}>
          <span className="section-label">FOLLOW THE REVENUE</span>
          <h2 id={`${id}-heading`}>
            {compactOverview ? "Follow the revenue" : "Revenue & expenses"}
          </h2>
          <p>
            See what remains after the company’s costs. Select a figure to
            inspect its evidence.
          </p>
        </div>
        {selected && (
          <div className="flow-period-types">
            <div
              className="flow-kind"
              role="group"
              aria-label="Income statement period type"
              aria-describedby={`${id}-period-help`}
            >
              {kinds.map((name) => (
                <button
                  key={name}
                  aria-pressed={name === activeKind}
                  onClick={() => {
                    setKind(name);
                    setSelection("");
                    setEvidence(null);
                  }}
                >
                  {names[name]}
                </button>
              ))}
            </div>
            <p className="flow-period-help" id={`${id}-period-help`}>
              {periodHelp[activeKind]}
            </p>
          </div>
        )}
      </div>
      {!selected ? (
        <p>{data.reason || "No saved income statement is available."}</p>
      ) : (
        <>
          {choices.length > 1 && (
            <div
              className="flow-timeline"
              ref={timeline}
              role="group"
              aria-label="Income statement reporting periods"
            >
              {choices.map((row) => (
                <button
                  key={row.id}
                  aria-pressed={row.id === selected.id}
                  aria-label={`${row.kind === "annual" ? "Fiscal year" : names[row.kind]} ending ${day(row.end)}`}
                  onClick={() => choose(row.id)}
                >
                  {row.kind === "quarter" ? day(row.end) : row.end.slice(0, 4)}
                </button>
              ))}
            </div>
          )}
          <div className="flow-meta">
            <p>
              {selected.kind === "annual"
                ? "Fiscal year"
                : names[selected.kind]}{" "}
              · {day(selected.start)} – {day(selected.end)}
              <br />
              <small>US dollars · reported income, not cash flow</small>
            </p>
            <div className="flow-source-controls">
              <label htmlFor={`${id}-mix`}>
                Revenue sources
                <Select
                  id={`${id}-mix`}
                  value={activeCategory}
                  onChange={(e) => {
                    setCategory(e.target.value);
                    setEvidence(null);
                  }}
                >
                  {[
                    "Total revenue",
                    "Operating segments",
                    "Products and services",
                    "Reported geographies",
                  ].map((name) => (
                    <option key={name} value={name}>
                      {name === "Reported geographies"
                        ? "Countries & regions"
                        : name === "Operating segments"
                          ? "Business segments"
                          : name}
                    </option>
                  ))}
                </Select>
              </label>
              {categoryMixes.length > 1 && (
                <label htmlFor={`${id}-geography`}>
                  Geographic view
                  <Select
                    id={`${id}-geography`}
                    value={mix.view_label}
                    onChange={(e) => {
                      setGeographyView(e.target.value);
                      setEvidence(null);
                    }}
                  >
                    {categoryMixes.map((row) => (
                      <option key={row.view_id} value={row.view_label}>
                        {row.view_label}
                      </option>
                    ))}
                  </Select>
                </label>
              )}
            </div>
          </div>
          {activeCategory !== "Total revenue" && (
            <div
              className="flow-source-detail"
              aria-live="polite"
              data-category={activeCategory}
            >
              {mix ? (
                <>
                  {mix.calculated && (
                    <p className="flow-footnote">
                      Calculated from the same annual and year-to-date reports
                      as total revenue.
                    </p>
                  )}
                  {mix.kind === "Reported geographies" && (
                    <p className="flow-footnote">
                      Countries and regions use the company’s reporting basis
                      {!mix.chartable
                        ? " and may overlap. Amounts are shown separately, without a percentage split"
                        : ""}
                      .
                    </p>
                  )}
                  {!mix.chartable && (
                    <p className="flow-footnote">{mix.reason}</p>
                  )}
                  {!connectedSources && sourceFigures}
                </>
              ) : (
                <p className="flow-footnote">
                  {selected.kind === "trailing"
                    ? "The past 12 months combines several reports. A matching breakdown is not available; choose Annual or Quarterly to see reported revenue sources."
                    : segments?.status === "unavailable"
                      ? segments.message ||
                        "Original-filing source access is unavailable."
                      : hasFiling
                        ? "This breakdown is not available for these dates in the reported figures. Other revenue views may be available."
                        : "This breakdown is not available in the saved filing for this period. Check reported data in Data & sources to collect missing historical reports."}
                </p>
              )}
            </div>
          )}
          {graph ? (
            <>
              <p className="flow-phone-hint">
                Swipe across to follow the flow. Figures also appear below.
              </p>
              <div
                className="flow-viewport"
                ref={viewport}
                tabIndex={0}
                role="region"
                aria-label="Revenue and expense flow chart"
              >
                <svg
                  className="flow-svg"
                  viewBox={`0 0 ${graph.width} ${graph.height}`}
                  style={{ width: graph.width, height: graph.height }}
                  aria-labelledby={`${id}-chart-title`}
                >
                  <title id={`${id}-chart-title`}>
                    Revenue flowing into costs and profit, {day(selected.start)}{" "}
                    to {day(selected.end)}. Band widths share a scale.
                  </title>
                  <g aria-hidden="true">
                    {graph.links.map((link) => (
                      <path
                        key={`${link.source}-${link.target}`}
                        className={`flow-link flow-${link.tone}`}
                        d={link.path}
                      />
                    ))}
                  </g>
                  {graph.nodes.map((row) => {
                    const allLines = shortLabel(row.label, row.group ? 22 : 25);
                    const lines =
                      row.group && allLines.length > 2
                        ? [allLines[0], allLines[1] + "…"]
                        : allLines;
                    const labelX = row.labelX ?? row.x;
                    return (
                      <g
                        key={row.key}
                        className={`flow-node flow-${row.tone}${row.group ? " flow-source-node" : ""}`}
                        role="button"
                        tabIndex={0}
                        aria-label={`${row.label}: ${amount(row.value)}. Inspect evidence`}
                        aria-haspopup="dialog"
                        onClick={() => setEvidence(row)}
                        onKeyDown={(e) => {
                          if (["Enter", " "].includes(e.key)) {
                            e.preventDefault();
                            setEvidence(row);
                          }
                        }}
                      >
                        <title>
                          {row.label}: {amount(row.value)}
                          {row.calculated ? " · calculated" : ""}
                        </title>
                        <rect
                          className="flow-hit"
                          x={labelX - 8}
                          y={row.hitY ?? row.y - 80}
                          width="207"
                          height={
                            row.hitHeight ?? Math.max(110, row.height + 84)
                          }
                          rx="8"
                        />
                        <rect
                          className="flow-bar"
                          x={row.x}
                          y={row.y}
                          width={row.width}
                          height={Math.max(0.7, row.height)}
                        />
                        <text
                          className="flow-node-label"
                          x={labelX}
                          y={
                            row.group
                              ? row.labelY - 8 - 17 * (lines.length - 1)
                              : row.y - 28 - 17 * lines.length
                          }
                        >
                          {lines.map((line, index) => (
                            <tspan key={index} x={labelX} dy={index ? 17 : 0}>
                              {line}
                            </tspan>
                          ))}
                        </text>
                        <text
                          className="flow-node-amount"
                          x={labelX}
                          y={row.group ? row.labelY + 16 : row.y - 12}
                        >
                          {amount(row.value)}
                          <tspan className="flow-calculated">
                            {row.calculated ? " *" : ""}
                          </tspan>
                        </text>
                      </g>
                    );
                  })}
                </svg>
              </div>
              <p className="flow-footnote">
                Band width shows the amount. * Calculated from reported figures.{" "}
                {mix?.chartable && !connectedSources
                  ? "Revenue sources are listed above to keep the flow compact."
                  : ""}
              </p>
            </>
          ) : (
            <p className="flow-gap">
              {selected.reason ||
                "These figures exceed the chart’s supported range. Inspect the exact values below."}
            </p>
          )}
          {selected.notes.map((note) => (
            <p key={note} className="flow-footnote">
              {note}
            </p>
          ))}
          <details
            key={selected.id}
            className="flow-all-figures"
            open={!graph || undefined}
          >
            <summary>View all figures &amp; evidence</summary>
            {connectedSources && sourceFigures}
            <div className="flow-figures" aria-label="Income statement figures">
              {values.map((row) => (
                <button
                  key={row.key}
                  className="flow-figure"
                  onClick={() => setEvidence(row)}
                  aria-haspopup="dialog"
                >
                  <span>{row.label}</span>
                  <strong>{amount(row.value)}</strong>
                  <small>
                    {row.value == null
                      ? "Inspect missing figure"
                      : row.calculated
                        ? "Calculated · evidence ↗"
                        : "Reported · evidence ↗"}
                  </small>
                </button>
              ))}
            </div>
          </details>
          {selected.expense_parts.length > 0 && (
            <details className="flow-expenses">
              <summary>What makes up operating expenses?</summary>
              <p>
                Reported research and selling/administrative costs, plus the
                calculated remainder. Cost of revenue is separate.
              </p>
              <div className="flow-expense-list">
                {selected.expense_parts.map((row) => (
                  <button
                    key={row.key}
                    onClick={() => setEvidence(row)}
                    aria-haspopup="dialog"
                  >
                    <span>
                      {row.label}
                      {row.calculated ? " *" : ""}
                    </span>
                    <strong>{amount(row.value)}</strong>
                  </button>
                ))}
              </div>
            </details>
          )}
          <details className="flow-definitions">
            <summary>How to read this chart</summary>
            {data.limitations.map((line) => (
              <p key={line}>{readableNote(line)}</p>
            ))}
            <p>
              Gross profit is revenue after costs directly associated with
              providing goods and services. Operating profit subtracts other
              operating expenses. Net result also reflects tax and other items;
              the label specifies whether it includes non-controlling interests.
            </p>
          </details>
        </>
      )}
      <Modal
        open={Boolean(evidence)}
        onClose={() => setEvidence(null)}
        title={`${evidence?.label || "Figure"} · evidence`}
        className="evidence-dialog flow-evidence"
      >
        {evidence && (
          <FinancialEvidence
            rows={[
              {
                ...evidence,
                unit: "USD",
                start: selected.start,
                end: selected.end,
                inputs: (evidence.inputs || []).map((input) => ({
                  ...input,
                  form: input.form || evidence.group?.form,
                  start: input.start || evidence.group?.start,
                  end: input.end || evidence.group?.end,
                  filing_url:
                    input.filing_url ||
                    (evidence.group?.url
                      ? `${evidence.group.url}${input.fact_id ? `#${encodeURIComponent(input.fact_id)}` : ""}`
                      : null),
                })),
              },
            ]}
          />
        )}
      </Modal>
    </section>
  );
}
