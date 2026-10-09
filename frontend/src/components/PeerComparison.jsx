import { useId, useState } from "react";
import Select from "./Select";
import { amount, day } from "./FinancialOverview";
import { peerMetrics, peerRows, peerScale } from "../lib/peerComparison";
import TermHelp from "./TermHelp";
import "./PeerComparison.css";

const stamp = (date) =>
  date
    ? new Date(date).toLocaleString("en-GB", {
        timeZone: "UTC",
        timeZoneName: "short",
      })
    : "Not recorded";
function display(number, unit) {
  if (number == null) return "Unavailable";
  if (unit === "USD") return amount(number);
  return (
    number.toLocaleString("en-GB", { maximumFractionDigits: 2 }) +
    (unit === "percent" ? "%" : "×")
  );
}

export default function PeerComparison({ members, symbol }) {
  const [selected, setSelected] = useState("pe_finnhub");
  const id = useId();
  const metric = peerMetrics.find((item) => item.id === selected);
  const rows = peerRows(members, metric),
    scale = peerScale(rows);
  const peers = rows.length > 1;
  const hasValues = rows.some((row) => row.value != null);
  const periods = new Set(
    rows
      .filter((row) => row.value != null && row.end)
      .map((row) => [row.start, row.end].join("/")),
  );
  return (
    <section className="peer-chart" aria-labelledby={id + "-title"}>
      <div className="peer-chart-heading">
        <div>
          <span className="section-label">COMPARE YOUR CHOSEN COMPANIES</span>
          <h3 id={id + "-title"}>Peer comparison</h3>
        </div>
        <label htmlFor={id + "-measure"}>
          Figure &amp; source
          <Select
            id={id + "-measure"}
            value={selected}
            onChange={(event) => setSelected(event.target.value)}
          >
            {peerMetrics.map((item) => (
              <option key={item.id} value={item.id}>
                {item.label}
              </option>
            ))}
          </Select>
        </label>
      </div>
      <p className="peer-chart-intro">
        {metric.explanation}
        {selected.startsWith("pe_") && <TermHelp term="pe" />}
      </p>
      {!peers && (
        <p className="peer-chart-note">
          Choose and save a comparison company above to see its figures
          alongside {symbol}.
        </p>
      )}
      {periods.size > 1 && (
        <p className="peer-chart-note">
          These companies use different fiscal dates. Each period is shown
          below; the chart does not align their calendars.
        </p>
      )}
      {metric.source !== "SEC" && (
        <p className="peer-chart-note">
          Collection dates can differ and are not the underlying quote times.
          Each chart uses one provider; missing values stay unavailable.
        </p>
      )}
      <div className="peer-chart-reading" key={selected}>
        {hasValues && peers && (
          <div className="peer-chart-scale" aria-hidden="true">
            <span>{display(scale.low, metric.unit)}</span>
            <span>{display(scale.high, metric.unit)}</span>
          </div>
        )}
        <div className="peer-chart-rows">
          {rows.map((row) => (
            <article className="peer-chart-row" key={row.symbol}>
              <div className="peer-chart-value-row">
                <div>
                  <strong>{row.symbol}</strong>
                  <span>
                    {row.symbol === symbol
                      ? "Selected company"
                      : "Your comparison"}
                  </span>
                </div>
                <strong className="peer-chart-value">
                  {display(row.value, metric.unit)}
                </strong>
              </div>
              {row.value != null && peers ? (
                <div className="peer-chart-track" aria-hidden="true">
                  <i style={{ left: (-scale.low / scale.span) * 100 + "%" }} />
                  <span
                    style={{
                      left:
                        ((Math.min(0, row.value) - scale.low) / scale.span) *
                          100 +
                        "%",
                      width: (Math.abs(row.value) / scale.span) * 100 + "%",
                    }}
                  />
                </div>
              ) : (
                row.reason && <p className="peer-chart-missing">{row.reason}</p>
              )}
              <p className="peer-chart-date">
                {metric.source === "SEC"
                  ? !row.end
                    ? "Reporting dates unavailable"
                    : row.start
                      ? day(row.start) + " – " + day(row.end)
                      : "Balance at " + day(row.end)
                  : "Observed " + stamp(row.observed)}
              </p>
              {row.priorStart && row.priorEnd && (
                <p className="peer-chart-date">
                  Compared with {day(row.priorStart)} – {day(row.priorEnd)}
                </p>
              )}
              {metric.source !== "SEC" &&
                row.observed &&
                Date.now() - new Date(row.observed).getTime() > 86400000 && (
                  <p className="peer-chart-note">
                    Saved more than 24 hours ago; this is an older reference.
                  </p>
                )}
              <details>
                <summary>Source &amp; comparison context</summary>
                {row.rationale && <p>Your reason: {row.rationale}</p>}
                <p>
                  {row.name}
                  {row.industry && " · " + row.industry}.
                </p>
                {row.industry && (
                  <p>
                    FMP industry classification, first observed{" "}
                    {stamp(row.classificationDate)}. Classification alone does
                    not establish product competition.
                  </p>
                )}
                <p>{row.basis || metric.explanation}</p>
                {row.formula && <p>{row.formula}</p>}
                {row.exact != null && (
                  <p>
                    Exact value: {row.exact}{" "}
                    {metric.unit === "multiple"
                      ? "times"
                      : metric.unit === "percent"
                        ? "%"
                        : "USD"}
                    .
                  </p>
                )}
                <p>
                  {metric.source} · first observed {stamp(row.observed)}
                  {row.checked && " · checked " + stamp(row.checked)}.
                </p>
                {row.field && <p>Source field: {row.field}.</p>}
                {row.identity && (
                  <p className="peer-evidence-id">
                    Saved source: {row.identity}.
                  </p>
                )}
                {row.sourceError && <p>{row.sourceError}</p>}
                {row.payloadIdentity && (
                  <p className="peer-evidence-id">
                    Original source payload: {row.payloadIdentity}.
                  </p>
                )}
                {row.inputs.map((input, index) => (
                  <p key={index}>
                    {input.namespace}:{input.concept} · exact {input.value}{" "}
                    {input.unit} ·{" "}
                    {input.start ? day(input.start) + " – " : "at "}
                    {day(input.end)} · filing {input.accession}
                    {input.filing_url && (
                      <>
                        {" "}
                        ·{" "}
                        <a
                          href={input.filing_url}
                          target="_blank"
                          rel="noreferrer"
                        >
                          Original filing ↗
                        </a>
                      </>
                    )}
                  </p>
                ))}
              </details>
            </article>
          ))}
        </div>
      </div>
      <p className="peer-chart-note">
        {peers && hasValues ? "Bars share one scale including zero. " : ""}
        Companies stay in the same order when you switch figures. Business mix,
        growth, fiscal dates and accounting choices still need review; this is
        not an investment ranking.
      </p>
    </section>
  );
}
