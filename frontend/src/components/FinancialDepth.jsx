const day = (value) =>
  value
    ? new Date(value).toLocaleDateString("en-GB", { timeZone: "UTC" })
    : "Unavailable";
const amount = (value, unit = "USD") =>
  value == null
    ? "Unavailable"
    : unit === "percent"
      ? `${Number(value).toLocaleString("en-GB", { maximumFractionDigits: 2 })}%`
      : `USD ${Number(value).toLocaleString("en-GB", { maximumFractionDigits: 2 })}`;

function Calculation({ row }) {
  return (
    <details className="financial-metric">
      <summary>
        <span>{row.label}</span>
        <strong>{amount(row.value, row.unit)}</strong>
        <small>
          {row.start
            ? `${day(row.start)} – `
            : row.key === "total_debt"
              ? "At "
              : "Period ending "}
          {day(row.end)}
        </small>
      </summary>
      {row.formula && <p>{row.formula}</p>}
      {row.reason && <p className="financial-note">{row.reason}</p>}
      {row.explanation && <p>{row.explanation}</p>}
      {row.inputs?.map((input, i) => (
        <p key={i}>
          {input.concept}: {amount(input.value)} ·{" "}
          {input.start ? `${day(input.start)} – ` : "At "}
          {day(input.end)} ·{" "}
          {input.filing_url && (
            <a href={input.filing_url} target="_blank" rel="noreferrer">
              Original {input.form} filing ↗
            </a>
          )}
        </p>
      ))}
    </details>
  );
}

export default function FinancialDepth({ data }) {
  if (!data || data.status !== "available")
    return (
      <section className="financial-performance">
        <h3>Trailing results & borrowing</h3>
        <p>
          {data?.reason || "Refresh filings to prepare these calculations."}
        </p>
      </section>
    );
  return (
    <section
      className="financial-performance"
      aria-label="Trailing results and borrowing"
    >
      <span className="section-label">A LONGER VIEW</span>
      <h3>Trailing results & borrowing</h3>
      <p>
        Code-calculated results from retained filing inputs. Expand a figure to
        inspect its dates, formula and original evidence.
      </p>
      <h4>Trailing fiscal year</h4>
      {data.trailing.map((row) => (
        <Calculation key={row.key} row={row} />
      ))}
      <h4>Borrowing at the reporting date</h4>
      <Calculation row={data.debt} />
      <h4>Reported annual revenue</h4>
      {data.revenue_trend.map((row) => (
        <Calculation
          key={row.period_end}
          row={{
            ...row,
            label: `Year ended ${day(row.period_end)}`,
            start: row.inputs?.[0]?.start,
            end: row.period_end,
            unit: "USD",
          }}
        />
      ))}
      <details className="financial-note">
        <summary>Definitions and limits</summary>
        {data.limitations.map((line) => (
          <p key={line}>{line}</p>
        ))}
      </details>
    </section>
  );
}
