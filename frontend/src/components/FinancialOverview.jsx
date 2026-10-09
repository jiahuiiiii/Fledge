import { useState } from "react";
import EvidenceButton from "./EvidenceButton";
import "../financial-overview.css";

export { Evidence, amount, day };

const valueOf = (value) => {
  if (value == null || value === "") return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
};
const day = (value) =>
  value
    ? new Date(value).toLocaleDateString("en-GB", {
        day: "numeric",
        month: "short",
        year: "numeric",
        timeZone: "UTC",
      })
    : "unavailable";
const amount = (value, exact = false) => {
  const number = valueOf(value);
  if (number == null) return "Unavailable";
  if (exact)
    return `US$${number.toLocaleString("en-GB", { maximumFractionDigits: 2 })}`;
  const divisor =
    Math.abs(number) >= 1e9 ? 1e9 : Math.abs(number) >= 1e6 ? 1e6 : 1;
  return `US$${(number / divisor).toLocaleString("en-GB", { maximumFractionDigits: 2 })}${divisor === 1e9 ? "bn" : divisor === 1e6 ? "m" : ""}`;
};
const period = (row) =>
  row?.start
    ? `${day(row.start)} – ${day(row.end)}`
    : row?.key && row.key !== "total_debt"
      ? `Period ending ${day(row.end)} · start unavailable`
      : `At ${day(row?.end)}`;
const extent = (values) => {
  const known = values.map(valueOf).filter((v) => v != null);
  const low = Math.min(0, ...known);
  const high = Math.max(0, ...known);
  return { low, high, span: high - low || 1 };
};

function Evidence({ row }) {
  return (
    <EvidenceButton
      title={`${row.label || "Figure"} · evidence`}
      className="overview-evidence"
    >
      {row.reason && <p>{row.reason}</p>}
      {row.formula && <p>{row.formula}</p>}
      {row.explanation && <p>{row.explanation}</p>}
      {row.value != null && (
        <p>
          Exact value: {row.value} {row.unit === "percent" ? "%" : "USD"}
        </p>
      )}
      {row.inputs?.map((input, index) => (
        <p key={index}>
          {input.concept}: {amount(input.value, true)} · {period(input)}
          {input.filing_url && (
            <>
              {" · "}
              <a href={input.filing_url} target="_blank" rel="noreferrer">
                Original {input.form} filing ↗
              </a>
            </>
          )}
        </p>
      ))}
    </EvidenceButton>
  );
}

function RevenueHistory({ rows }) {
  const [selected, setSelected] = useState("");
  const ordered = [...rows].sort((a, b) =>
    a.period_end.localeCompare(b.period_end),
  );
  const active =
    ordered.find((row) => row.period_end === selected) || ordered.at(-1);
  const scale = extent(ordered.map((row) => row.value));
  if (!active)
    return (
      <article className="financial-chart-card">
        <h3>Has revenue changed?</h3>
        <p>No compatible annual revenue history is available.</p>
      </article>
    );
  return (
    <article className="financial-chart-card">
      <span className="section-label">REPORTED ANNUAL REVENUE</span>
      <h3>Has revenue changed?</h3>
      <p>Choose a fiscal year to inspect the exact dates and filing.</p>
      <div className="revenue-chart" aria-label="Annual revenue chart">
        <div className="revenue-scale" aria-hidden="true">
          <span>{amount(scale.high)}</span>
          <span>{amount(scale.low)}</span>
        </div>
        <div className="revenue-columns">
          {ordered.map((row) => {
            const number = valueOf(row.value);
            const current = row.period_end === active.period_end;
            return (
              <button
                className="revenue-column"
                key={row.period_end}
                aria-pressed={current}
                aria-label={`Revenue, fiscal year ended ${day(row.period_end)}: ${amount(row.value, true)}`}
                onClick={() => setSelected(row.period_end)}
              >
                <span className="revenue-value">
                  {number == null
                    ? "No data"
                    : amount(row.value).replace(/^US\$/, "")}
                </span>
                <span className="revenue-track" aria-hidden="true">
                  <span
                    className="revenue-zero"
                    style={{ top: `${(scale.high / scale.span) * 100}%` }}
                  />
                  {number != null ? (
                    <span
                      className="revenue-bar"
                      style={{
                        top: `${((scale.high - Math.max(0, number)) / scale.span) * 100}%`,
                        height: `${(Math.abs(number) / scale.span) * 100}%`,
                      }}
                    />
                  ) : (
                    <span className="revenue-missing">—</span>
                  )}
                </span>
                <span className="revenue-year">
                  FY {row.period_end.slice(0, 4)}
                </span>
              </button>
            );
          })}
        </div>
      </div>
      <div className="revenue-reading" key={active.period_end}>
        <p aria-live="polite">
          <strong>{amount(active.value)}</strong>
          <span>Fiscal year ended {day(active.period_end)}</span>
        </p>
        <Evidence row={{ ...active, end: active.period_end }} />
      </div>
      <p className="overview-footnote">
        Whole-company reported revenue. Missing years stay visible. Acquisitions
        and accounting changes can affect comparisons.
      </p>
    </article>
  );
}

function CashGeneration({ rows }) {
  const keys = ["operating_cash", "capital_spending", "free_cash_flow"];
  const cash = keys.map((key) => rows.find((row) => row.key === key));
  const anchor = cash.find((row) => row?.value != null);
  const compatible = cash.map((row) => {
    if (!row) return null;
    if (anchor && (row.start !== anchor.start || row.end !== anchor.end))
      return {
        ...row,
        value: null,
        reason:
          "This figure covers a different period and is excluded from this comparison.",
      };
    return row;
  });
  const scale = extent(compatible.map((row) => row?.value));
  const zero = (-scale.low / scale.span) * 100;
  return (
    <article className="financial-chart-card">
      <span className="section-label">CASH GENERATION</span>
      <h3>What cash is left after capital spending?</h3>
      <p>
        {anchor?.start
          ? period(anchor)
          : "Compatible trailing cash-flow figures are unavailable."}
      </p>
      <div className="cash-comparison">
        {compatible.map((row, index) => {
          if (!row) return null;
          const number = valueOf(row.value);
          return (
            <section className="cash-measure" key={row.key}>
              <div>
                <span>
                  {
                    [
                      "Cash from operations",
                      "Cash capital spending",
                      "Free cash flow",
                    ][index]
                  }
                </span>
                <strong>{amount(row.value)}</strong>
              </div>
              <div className="cash-track" aria-hidden="true">
                <span className="cash-zero" style={{ left: `${zero}%` }} />
                {number != null && (
                  <span
                    className={`cash-bar cash-bar-${index}`}
                    style={{
                      left: `${((Math.min(0, number) - scale.low) / scale.span) * 100}%`,
                      width: `${(Math.abs(number) / scale.span) * 100}%`,
                    }}
                  />
                )}
              </div>
              <Evidence row={row} />
            </section>
          );
        })}
      </div>
      <p className="overview-footnote">
        Free cash flow = operating cash flow − cash capital spending. It
        excludes other uses of cash, including acquisitions, debt repayments and
        dividends. All bars use the same dollar scale; spending is shown as an
        amount paid.
      </p>
    </article>
  );
}

export default function FinancialOverview({ data, compact = false }) {
  if (data?.status !== "available") return null;
  const keys = ["revenue", "operating_margin", "free_cash_flow"];
  const metrics = keys.map((key) =>
    data.trailing.find((row) => row.key === key),
  );
  return (
    <section className="financial-overview" aria-label="Financial overview">
      <div className="overview-intro">
        <span className="section-label">THE BUSINESS IN NUMBERS</span>
        <h2>Revenue, profitability & cash</h2>
        <p>
          Trailing fiscal results and reporting-date borrowing from company
          filings. Open a figure to inspect its evidence.
        </p>
      </div>
      <div className="financial-snapshot">
        {[...metrics, data.debt].filter(Boolean).map((row) => (
          <article className="snapshot-card" key={row.key}>
            <span>
              {{
                total_debt: "Borrowing",
                operating_margin: "Operating margin",
                free_cash_flow: "Free cash flow",
              }[row.key] || row.label}
            </span>
            <strong>
              {row.unit === "percent" && valueOf(row.value) != null
                ? `${Number(row.value).toLocaleString("en-GB", { maximumFractionDigits: 2 })}%`
                : amount(row.value)}
            </strong>
            <small>{period(row)}</small>
            <Evidence row={row} />
          </article>
        ))}
      </div>
      {!compact && (
        <div className="financial-chart-grid">
          <RevenueHistory rows={data.revenue_trend} />
          <CashGeneration rows={data.trailing} />
        </div>
      )}
    </section>
  );
}
