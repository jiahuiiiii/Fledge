import { useState } from "react";

const day = (value) =>
  value
    ? new Date(value).toLocaleDateString("en-GB", {
        day: "numeric",
        month: "short",
        year: "numeric",
        timeZone: "UTC",
      })
    : "Unavailable";
const scope = (row) =>
  row.start ? `${day(row.start)} – ${day(row.end)}` : `At ${day(row.end)}`;
const amount = (value, unit = "USD") => {
  if (value == null) return "Unavailable";
  const n = Number(value);
  if (unit === "percent")
    return `${n.toLocaleString("en-GB", { maximumFractionDigits: 2 })}%`;
  const divisor = Math.abs(n) >= 1e9 ? 1e9 : Math.abs(n) >= 1e6 ? 1e6 : 1;
  return `USD ${(n / divisor).toLocaleString("en-GB", { maximumFractionDigits: 2 })}${divisor === 1e9 ? "bn" : divisor === 1e6 ? "m" : ""}`;
};
const groups = ["Business performance", "Cash generation", "Balance sheet"];

export default function FinancialPerformance({ data }) {
  const reports = data?.reports || {};
  const defaultKind =
    reports.annual &&
    (!reports.quarter ||
      reports.annual.period_end >= reports.quarter.period_end)
      ? "annual"
      : "quarter";
  const [kind, setKind] = useState("");
  const activeKind = kind || defaultKind;
  const chosen = reports[activeKind];
  const stale =
    data?.checked_at &&
    Date.now() - new Date(data.checked_at).getTime() > 24 * 60 * 60 * 1000;
  if (!data || data.status !== "available")
    return (
      <section
        className="financial-performance"
        aria-label="Financial performance"
      >
        <h3>Business performance</h3>
        <p>{data?.reason || "Financial statements are unavailable."}</p>
      </section>
    );
  return (
    <section
      className="financial-performance"
      aria-label="Financial performance"
    >
      <div className="financial-heading">
        <div>
          <span className="section-label">PERFORMANCE BEHIND THE STORY</span>
          <h3>How is the business doing?</h3>
        </div>
        <div
          className="financial-periods"
          role="group"
          aria-label="Financial reporting view"
        >
          <button
            aria-pressed={activeKind === "annual"}
            onClick={() => setKind("annual")}
          >
            Annual financials
          </button>
          <button
            aria-pressed={activeKind === "quarter"}
            onClick={() => setKind("quarter")}
          >
            Latest quarter
          </button>
        </div>
      </div>
      <p className="financial-coverage">
        Filing data checked {day(data.checked_at)}.{" "}
        {data.source_status?.last_error
          ? "The latest filing check failed; these are retained figures."
          : stale
            ? "The source check is over 24 hours old. Refresh research to check for newer reports."
            : "Opening this view uses saved filing data."}
      </p>
      {!chosen ? (
        <p className="unknown-row">
          No compatible {activeKind === "annual" ? "annual" : "quarterly"}{" "}
          filing is available in the saved response.
        </p>
      ) : (
        <>
          <div className="financial-filing">
            <div>
              <strong>
                {activeKind === "annual"
                  ? "Annual report"
                  : "Direct-quarter report"}{" "}
                · period ended {day(chosen.period_end)}
              </strong>
              <p>
                {chosen.form} · filed {day(chosen.filed_on)}
              </p>
            </div>
            <a href={chosen.filing_url} target="_blank" rel="noreferrer">
              Open this SEC filing ↗
            </a>
          </div>
          {activeKind === "quarter" &&
            reports.annual?.period_end > chosen.period_end && (
              <p className="financial-note">
                The annual report is newer than this 10-Q. This view preserves
                the latest directly reported quarter; it does not estimate a
                fourth quarter.
              </p>
            )}
          {groups.map((group) => (
            <section className="financial-group" key={group} aria-label={group}>
              <h4>{group}</h4>
              {group === "Cash generation" && (
                <p>
                  Cash flow covers the dates shown below. A quarterly filing can
                  report fiscal year-to-date cash flow.
                </p>
              )}
              {group === "Balance sheet" && (
                <p>
                  Balances at the reporting date. Debt components are shown
                  separately; they do not form a complete total.
                </p>
              )}
              {chosen.metrics
                .filter((m) => m.group === group)
                .map((m) => (
                  <details className="financial-metric" key={m.key}>
                    <summary>
                      <span>
                        {m.label}
                        <small>{scope(m)}</small>
                      </span>
                      <strong>{amount(m.value, m.unit)}</strong>
                    </summary>
                    <div className="financial-evidence">
                      <p>{m.explanation}</p>
                      {m.reason && <p className="financial-note">{m.reason}</p>}
                      {m.formula && (
                        <p>
                          <strong>Calculation:</strong> {m.formula}
                        </p>
                      )}
                      {m.value != null && (
                        <p>
                          Exact {m.calculated ? "calculated" : "reported"}{" "}
                          value:{" "}
                          <strong>
                            {m.value} {m.unit === "percent" ? "%" : "USD"}
                          </strong>
                        </p>
                      )}
                      {m.prior && (
                        <p>
                          Comparison reported in this filing:{" "}
                          <strong>{amount(m.prior.value)}</strong> ·{" "}
                          {scope(m.prior)}.{" "}
                          {m.prior.start
                            ? "Comparable prior-year period."
                            : "Previous reported balance date; not necessarily one year earlier."}
                        </p>
                      )}
                      {m.inputs.length > 0 && (
                        <>
                          <h5>Reported inputs</h5>
                          <ul>
                            {m.inputs.map((f, i) => (
                              <li key={i}>
                                <strong>{f.concept}</strong>: USD {f.value}
                                <br />
                                {scope(f)} · accession {f.accession}
                              </li>
                            ))}
                          </ul>
                        </>
                      )}
                      <a
                        href={chosen.filing_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Inspect original filing ↗
                      </a>
                    </div>
                  </details>
                ))}
            </section>
          ))}
          <details className="financial-method">
            <summary>Definitions and source limitations</summary>
            <ul>
              {data.limitations.map((text) => (
                <li key={text}>{text}</li>
              ))}
            </ul>
            <p>
              Calculated values use decimal arithmetic before display rounding.
              The selected view does not change saved monitoring conditions.
              Automatic numerical monitoring currently supports revenue growth
              and operating margin using the active filing.
            </p>
          </details>
        </>
      )}
    </section>
  );
}
