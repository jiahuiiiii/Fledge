import { useState } from "react";
import { targetRange, targetChange } from "../lib/targetRange";

const price = (v) =>
  `USD ${Number(v).toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const date = (v) =>
  new Date(v).toLocaleString("en-GB", {
    timeZone: "UTC",
    dateStyle: "medium",
    timeStyle: "short",
  }) + " UTC";

export default function AnalystTargets({ value, quote, onRefresh }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const record = value?.snapshot;
  const data = record?.data;
  const range = targetRange(data?.targets, quote);
  async function refresh() {
    setBusy(true);
    setError("");
    try {
      await onRefresh();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section
      className="analyst-targets"
      aria-label="Analyst price targets"
      aria-busy={busy}
    >
      <div className="market-section-head">
        <div>
          <span className="section-label">THE ANALYST VIEW</span>
          <h2>Analyst price targets</h2>
        </div>
        <button
          type="button"
          disabled={busy || !value?.available}
          onClick={refresh}
        >
          {busy ? "Checking targets…" : "Refresh analyst targets"}
        </button>
      </div>
      <p className="fine">
        Published 12-month targets, separate from the scenarios you build below.
      </p>
      {data ? (
        <>
          {range ? (
            <div className="target-range">
              <div className="target-range-summary">
                <div>
                  <span className="section-label">MEAN · 12 MONTHS</span>
                  <strong>{price(range.mean)}</strong>
                  <span
                    className={
                      range.change(range.mean) < 0 ? "negative" : "positive"
                    }
                  >
                    {targetChange(range.change(range.mean))}
                  </span>
                </div>
                <div className="target-quote">
                  <span>Last retrieved quote</span>
                  <strong>
                    {range.current ? price(range.current) : "Not available"}
                  </strong>
                  <small>
                    {range.current && quote?.quoted_at
                      ? date(quote.quoted_at)
                      : "Refresh research to compare potential returns."}
                  </small>
                </div>
              </div>
              <svg
                className="target-range-plot"
                viewBox="0 0 600 118"
                role="img"
                aria-label={`Analyst target range: low ${price(range.low)}, mean ${price(range.mean)}, median ${price(range.median)}, high ${price(range.high)}. ${range.current ? `Last quote ${price(range.current)}. ${targetChange(range.change(range.mean))} to mean.` : "No quote for return comparison."}`}
              >
                <line
                  x1="36"
                  x2="564"
                  y1="58"
                  y2="58"
                  className="target-axis"
                />
                <line
                  x1={range.position(range.low) * 6}
                  x2={range.position(range.high) * 6}
                  y1="58"
                  y2="58"
                  className="target-band"
                />
                {[range.low, range.high].map((v, i) => (
                  <line
                    key={i}
                    x1={range.position(v) * 6}
                    x2={range.position(v) * 6}
                    y1="47"
                    y2="69"
                    className="target-end"
                  />
                ))}
                <line
                  x1={range.position(range.median) * 6}
                  x2={range.position(range.median) * 6}
                  y1="51"
                  y2="65"
                  className="target-median"
                />
                <circle
                  cx={range.position(range.mean) * 6}
                  cy="58"
                  r="7"
                  className="target-mean-dot"
                />
                {range.current && (
                  <g className="target-current">
                    <line
                      x1={range.position(range.current) * 6}
                      x2={range.position(range.current) * 6}
                      y1="19"
                      y2="90"
                    />
                    <path
                      d={`M ${range.position(range.current) * 6 - 5} 19 L ${range.position(range.current) * 6 + 5} 19 L ${range.position(range.current) * 6} 26 Z`}
                    />
                  </g>
                )}
              </svg>
              <div className="target-legend">
                <span>
                  <i className="legend-mean" />
                  Mean
                </span>
                <span>
                  <i className="legend-median" />
                  Median {price(range.median)}
                </span>
                {range.current && (
                  <span>
                    <i className="legend-quote" />
                    Last quote
                  </span>
                )}
              </div>
              <dl className="target-range-values">
                {[
                  ["Lowest", range.low],
                  ["Mean", range.mean],
                  ["Highest", range.high],
                ].map(([label, value]) => (
                  <div key={label}>
                    <dt>{label} target</dt>
                    <dd>{price(value)}</dd>
                    <small
                      className={
                        range.change(value) < 0 ? "negative" : "positive"
                      }
                    >
                      {targetChange(range.change(value))}
                    </small>
                  </div>
                ))}
              </dl>
              <p className="fine">
                Potential price change from the retrieved quote, excluding
                dividends. The range shows analyst opinions, not a probability
                interval.
              </p>
            </div>
          ) : (
            <p className="financial-note">
              The saved target range is incomplete or inconsistent. Refresh to
              check the source.
            </p>
          )}
          <p className="target-source">
            <a href={data.url} target="_blank" rel="noreferrer">
              {data.publisher} ↗
            </a>{" "}
            · {data.provider} · {data.polled_analysts} analysts in the reported
            poll
          </p>
          <p className="fine">
            Fetched {date(record.retrieved_at)}.
            {data.page_updated_on && (
              <> Source page updated {data.page_updated_on}.</>
            )}{" "}
            The individual targets’ dates are not supplied with this range.
          </p>
          {record.stale && (
            <p className="financial-note">
              This saved snapshot was fetched more than 24 hours ago. Refresh
              before comparing it with today’s prices.
            </p>
          )}
          <details className="secondary-details">
            <summary>Source details and limits</summary>
            <p>
              The poll count is not a verified count of contributors to each
              target. Targets are opinions and may be wrong; the low target is
              not a suggested entry price. These figures do not set your
              assumptions or trigger alerts.
            </p>
            <p className="fine">
              Only the public forecast summary and table are read. Refresh is
              manual, once per company every 24 hours, and uses no AI credits.
            </p>
          </details>
        </>
      ) : (
        <p className="target-empty">
          {value?.available
            ? "Load the public analyst range for this company. Your scenario assumptions stay unchanged."
            : "This target source is unavailable. You can still build a scenario below."}
        </p>
      )}
      {(error || value?.refresh?.error) && (
        <p role="alert" className="form-error">
          {error || value.refresh.error}
        </p>
      )}
      {busy && (
        <p role="status" className="fine">
          Checking the public source. Your saved targets remain visible.
        </p>
      )}
    </section>
  );
}
