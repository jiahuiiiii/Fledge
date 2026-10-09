import { useId, useState } from "react";
import Select from "./Select";
import { Evidence, amount, day } from "./FinancialOverview";
import "./FinancialPosition.css";

// Charts only combine balances from the selected date and filing. Do not fill
// a missing debt total with one of the older statement's debt components.
function matching(row, report, label) {
  if (!row || row.value == null)
    return {
      key: label,
      label,
      value: null,
      inputs: [],
      reason: row?.reason || "A matching saved figure is unavailable.",
    };
  const inputs = row.inputs || [];
  if (
    row.unit !== "USD" ||
    row.start != null ||
    row.end !== report.period_end ||
    !inputs.length ||
    inputs.some(
      (input) =>
        input.unit !== "USD" ||
        input.start != null ||
        input.end !== report.period_end ||
        input.accession !== report.accession,
    )
  )
    return {
      key: label,
      label,
      value: null,
      inputs: [],
      reason:
        "A figure with the same currency, balance date and filing is unavailable.",
    };
  return {
    ...row,
    label,
    inputs: inputs.map((input) => ({
      ...input,
      filing_url: input.filing_url || report.filing_url,
    })),
  };
}

function Comparison({ title, explanation, rows, colour }) {
  const values = rows
    .map((row) => (row.value == null ? null : Number(row.value)))
    .filter((value) => value != null && Number.isFinite(value));
  const low = Math.min(0, ...values),
    high = Math.max(0, ...values),
    span = high - low || 1;
  return (
    <article className="financial-chart-card position-comparison">
      <h3>{title}</h3>
      <p>{explanation}</p>
      <div className="position-measures">
        {rows.map((row, index) => {
          const value = row.value == null ? null : Number(row.value);
          return (
            <div className="position-measure" key={row.key}>
              <div className="position-measure-label">
                <span>{row.label}</span>
                <strong>{amount(row.value)}</strong>
              </div>
              {value != null && Number.isFinite(value) ? (
                <div className="position-track" aria-hidden="true">
                  <i
                    className="position-zero"
                    style={{ left: `${(-low / span) * 100}%` }}
                  />
                  <span
                    style={{
                      left: `${((Math.min(0, value) - low) / span) * 100}%`,
                      width: `${(Math.abs(value) / span) * 100}%`,
                      background: colour[index],
                    }}
                  />
                </div>
              ) : (
                <p className="position-missing">No matching figure to plot</p>
              )}
              <Evidence row={row} />
            </div>
          );
        })}
      </div>
      <p className="position-scale">
        Bars share one scale in this chart, starting from zero. Each chart uses
        its own scale.
      </p>
    </article>
  );
}

export default function FinancialPosition({ performance, debt }) {
  const [kind, setKind] = useState("");
  const id = useId();
  if (!performance) return null;
  const reports =
    performance.status === "available" ? performance.reports || {} : {};
  const available = Object.entries(reports)
    .filter(([, report]) => report)
    .sort((a, b) => b[1].period_end.localeCompare(a[1].period_end));
  const active = available.find(([name]) => name === kind) || available[0];
  const [activeKind, report] = active || [];
  const read = (key, label) =>
    matching(
      report?.metrics.find((row) => row.key === key),
      report,
      label,
    );
  const borrowed = report ? matching(debt, report, "Borrowing") : null;
  const old =
    performance.checked_at &&
    Date.now() - new Date(performance.checked_at).getTime() > 86400000;
  return (
    <section className="financial-position" aria-labelledby={`${id}-title`}>
      <div className="position-heading">
        <div>
          <span className="section-label">BALANCE SHEET AT A GLANCE</span>
          <h2 id={`${id}-title`}>What it owns and owes</h2>
        </div>
        {report && (
          <label htmlFor={`${id}-period`}>
            Balance-sheet date
            <Select
              id={`${id}-period`}
              value={activeKind}
              onChange={(event) => setKind(event.target.value)}
            >
              {available.map(([name, item]) => (
                <option key={name} value={name}>
                  {name === "annual" ? "Annual report" : "Quarter report"} ·{" "}
                  {day(item.period_end)}
                </option>
              ))}
            </Select>
          </label>
        )}
      </div>
      {!report ? (
        <p>
          {performance.reason ||
            "No compatible balance sheet is available in the saved filing data."}
        </p>
      ) : (
        <>
          <p className="position-caption">
            Balances at {day(report.period_end)} · {report.form} filed{" "}
            {day(report.filed_on)} ·{" "}
            <a href={report.filing_url} target="_blank" rel="noreferrer">
              Original filing ↗
            </a>
          </p>
          <div
            className="position-reading"
            key={`${activeKind}/${report.accession}`}
          >
            <div className="position-grid">
              <Comparison
                title="Assets and liabilities"
                explanation="Assets are recorded resources, including cash, equipment and intangible assets. Liabilities include borrowing and other obligations."
                rows={[
                  read("assets", "Total assets"),
                  read("liabilities", "Total liabilities"),
                ]}
                colour={["#91bccc", "#b8a6ce"]}
              />
              <Comparison
                title="Cash and borrowing"
                explanation="Cash is part of assets; borrowing is part of liabilities. Repayment also depends on debt maturities, cash restrictions and future cash flow."
                rows={[read("cash", "Cash & equivalents"), borrowed]}
                colour={["#a6c9b2", "#d1bd91"]}
              />
            </div>
            <p className="position-caption">
              These pairs overlap; do not add the four figures together. Asset
              values follow accounting rules and may differ from resale values.
            </p>
            <p className="position-caption">
              Saved filing data checked {day(performance.checked_at)}.{" "}
              {performance.source_status?.last_error
                ? "The latest check failed; these are retained figures."
                : old
                  ? "The source check is over 24 hours old. Refresh research to check for newer reports."
                  : "Selecting a date uses saved figures."}
            </p>
          </div>
        </>
      )}
    </section>
  );
}
