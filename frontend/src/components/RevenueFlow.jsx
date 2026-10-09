import { useEffect, useId, useRef, useState } from "react";
import Modal from "./Modal";
import Select from "./Select";
import { amount, day } from "./FinancialOverview";
import { flowLayout, matchingMix, shortLabel } from "../lib/incomeFlow";
import "./RevenueFlow.css";

const names = {
  trailing: "Trailing year",
  annual: "Annual",
  quarter: "Quarterly",
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
}) {
  const id = useId();
  const [kind, setKind] = useState("");
  const [selection, setSelection] = useState("");
  const [category, setCategory] = useState("");
  const [evidence, setEvidence] = useState(null);
  const timeline = useRef(null);
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
  const mixes = matchingMix(selected, segments?.groups);
  const mix = mixes.find((row) => row.axis === category) || mixes[0];
  const graph = flowLayout(selected, mix);
  const values =
    selected?.metrics.filter((row) => metricKeys.includes(row.key)) || [];
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
  if (!data) return null;
  function choose(value) {
    setSelection(value);
    setEvidence(null);
  }
  return (
    <section
      className="revenue-flow financial-chart-card"
      aria-labelledby={`${id}-heading`}
    >
      <div className="flow-heading">
        <div className={compactHeading ? "flow-heading-compact" : undefined}>
          <span className="section-label">FOLLOW THE REVENUE</span>
          <h2 id={`${id}-heading`}>Revenue &amp; expenses</h2>
          <p>
            See what remains after the company’s costs. Select a figure to
            inspect its evidence.
          </p>
        </div>
        {selected && (
          <div
            className="flow-kind"
            role="group"
            aria-label="Income statement period type"
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
        )}
      </div>
      {!selected ? (
        <p>{data.reason || "No saved income statement is available."}</p>
      ) : (
        <>
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
                onClick={() => choose(row.id)}
              >
                <span>
                  {row.kind === "quarter" ? day(row.end) : row.end.slice(0, 4)}
                </span>
                <small>
                  {amount(row.metrics.find((m) => m.key === "revenue")?.value)}{" "}
                  revenue
                </small>
              </button>
            ))}
          </div>
          <div className="flow-meta">
            <p>
              {names[selected.kind]} · {day(selected.start)} –{" "}
              {day(selected.end)}
              <br />
              <small>US dollars · reported income, not cash flow</small>
            </p>
            {mixes.length > 1 && (
              <label htmlFor={`${id}-mix`}>
                Revenue sources
                <Select
                  id={`${id}-mix`}
                  value={mix.axis}
                  onChange={(e) => setCategory(e.target.value)}
                >
                  {mixes.map((row) => (
                    <option key={row.axis} value={row.axis}>
                      {row.kind}
                    </option>
                  ))}
                </Select>
              </label>
            )}
            {mix && mixes.length === 1 && <span>{mix.kind}</span>}
          </div>
          {graph ? (
            <>
              <p className="flow-phone-hint">
                Swipe across to follow the flow. Figures also appear below.
              </p>
              <div
                className="flow-viewport"
                tabIndex={0}
                role="region"
                aria-label="Revenue and expense flow chart"
              >
                <svg
                  className="flow-svg"
                  viewBox={`0 0 ${graph.width} ${graph.height}`}
                  style={{ minWidth: Math.max(690, graph.width * 0.85) }}
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
                    const lines = shortLabel(row.label);
                    return (
                      <g
                        key={row.key}
                        className={`flow-node flow-${row.tone}`}
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
                          x={row.x - 8}
                          y={row.y - 80}
                          width="207"
                          height={Math.max(110, row.height + 84)}
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
                          x={row.x}
                          y={row.y - 28 - 17 * lines.length}
                        >
                          {lines.map((line, index) => (
                            <tspan key={index} x={row.x} dy={index ? 17 : 0}>
                              {line}
                            </tspan>
                          ))}
                        </text>
                        <text
                          className="flow-node-amount"
                          x={row.x}
                          y={row.y - 12}
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
                Band width shows the amount. * Calculated difference.{" "}
                {selected.kind === "trailing"
                  ? "Trailing figures use an annual/YTD bridge; a matching revenue-segment mix is not available."
                  : !mix
                    ? "No matching revenue-segment mix is available for this filing and period."
                    : mix.members.length > 5
                      ? "The complete category list is available in Where revenue comes from below."
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
              <p key={line}>{line}</p>
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
          <>
            <p className="flow-exact">
              {evidence.value == null ? "Unavailable" : `${evidence.value} USD`}
            </p>
            <p>
              {day(selected.start)} – {day(selected.end)}
            </p>
            {evidence.reason && <p>{evidence.reason}</p>}
            {evidence.formula && <p>{evidence.formula}</p>}
            {evidence.explanation && <p>{evidence.explanation}</p>}
            {evidence.group && (
              <p>
                Reported category: {evidence.member}. {evidence.group.kind}.
                Category names come from the filing; read its definitions.
              </p>
            )}
            {evidence.inputs.map((input, index) => (
              <p key={index}>
                {input.concept}: {input.value ?? "Unavailable"}{" "}
                {input.unit || "USD"}
                <br />
                {input.start && `${day(input.start)} – `}
                {input.end && day(input.end)}
                {input.context_id && `Context: ${input.context_id}`}
                <br />
                {(input.filing_url || evidence.group?.url) && (
                  <a
                    href={
                      input.filing_url ||
                      `${evidence.group.url}${input.fact_id ? `#${encodeURIComponent(input.fact_id)}` : ""}`
                    }
                    target="_blank"
                    rel="noreferrer"
                  >
                    Original {input.form || evidence.group.form} filing ↗
                  </a>
                )}
              </p>
            ))}
            <p>
              Method: {data.method} · saved source {data.payload_id}
            </p>
          </>
        )}
      </Modal>
    </section>
  );
}
