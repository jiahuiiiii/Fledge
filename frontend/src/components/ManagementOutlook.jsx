import { useId, useState } from "react";
import Select from "./Select";
import { day, amount } from "./FinancialOverview";
import "./ManagementOutlook.css";

const stamp = (value) =>
  new Date(value).toLocaleString("en-GB", {
    timeZone: "UTC",
    timeZoneName: "short",
  });
function value(number, unit) {
  if (number == null) return "Read original wording";
  const n = Number(number);
  if (!Number.isFinite(n)) return "Read original wording";
  if (unit === "percent") return n + "%";
  const size = Math.abs(n) >= 1e9 ? 1e9 : Math.abs(n) >= 1e6 ? 1e6 : 1;
  return (
    (unit === "USD" ? "US$" : "$") +
    (n / size).toLocaleString("en-GB", { maximumFractionDigits: 6 }) +
    (size === 1e9 ? "bn" : size === 1e6 ? "m" : "")
  );
}

function Forecast({ forecast, release }) {
  const compared = forecast.comparison;
  const range = forecast.low !== forecast.high;
  return (
    <article className="outlook-forecast">
      <h4>{forecast.label}</h4>
      <p className="outlook-value">
        {forecast.approximate ? "≈ " : ""}
        {value(forecast.low, forecast.unit)}
        {range && " – " + value(forecast.high, forecast.unit)}
      </p>
      <p className="outlook-definition">
        {forecast.basis
          ? forecast.basis.toUpperCase()
          : "Accounting basis unspecified"}
        {forecast.metric === "revenue" &&
          !forecast.unit &&
          " · currency unspecified"}
        {forecast.approximate && " · approximate"}
      </p>
      <details>
        <summary>Original guidance &amp; evidence</summary>
        <blockquote>{forecast.quote}</blockquote>
        {forecast.low != null && (
          <p>
            Exact {range ? "range" : "point"}: {forecast.low}
            {range && " to " + forecast.high}{" "}
            {forecast.unit || "dollars; currency unspecified"}.
          </p>
        )}
        <p>
          Passage {forecast.id} · SEC filing accepted{" "}
          {stamp(release.published_at)}.
        </p>
        <a href={release.url} target="_blank" rel="noreferrer">
          Open original earnings release ↗
        </a>
      </details>
      <div className="outlook-comparison">
        {compared.status === "compared" ? (
          <>
            <strong>Filed revenue: {amount(compared.actual)}</strong>
            <p>
              {range
                ? { above: "Above", below: "Below", within: "Within" }[
                    compared.relation
                  ] + " the displayed guidance range."
                : "Difference from the " +
                  (compared.approximate ? "approximate " : "") +
                  "guidance point: " +
                  amount(compared.difference) +
                  "."}
            </p>
            <details>
              <summary>Inspect the result comparison</summary>
              <p>
                Original result period {day(compared.input.start)}–
                {day(compared.input.end)}. Exact revenue: {compared.actual} USD.
              </p>
              <p>
                {compared.input.namespace}:{compared.input.concept} · filing{" "}
                {compared.report.accession}. First saved{" "}
                {stamp(compared.first_recorded_at)}.
              </p>
              <p>
                This is the first retained matching original filing, which may
                follow the earnings announcement. An approximate point has no
                defined pass/fail tolerance.
              </p>
              <a
                href={compared.report.filing_url}
                target="_blank"
                rel="noreferrer"
              >
                Open reported result ↗
              </a>
            </details>
          </>
        ) : (
          <>
            <strong>Comparison unavailable</strong>
            <details>
              <summary>What is missing?</summary>
              <ul>
                {compared.reasons.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            </details>
          </>
        )}
      </div>
    </article>
  );
}

export default function ManagementOutlook({ data }) {
  const [selected, setSelected] = useState("");
  const id = useId();
  if (!data) return null;
  const releases = data.releases || [];
  const release =
    releases.find((item) => item.id === selected) ||
    releases.find((item) => item.current) ||
    releases[0];
  return (
    <section className="management-outlook" aria-labelledby={id + "-title"}>
      <div className="outlook-heading">
        <div>
          <span className="section-label">LOOKING AHEAD</span>
          <h2 id={id + "-title"}>Management outlook</h2>
          <p>
            The company’s own expectations, taken from its earnings release.
          </p>
        </div>
        {release && (
          <label htmlFor={id + "-release"}>
            Saved release
            <Select
              id={id + "-release"}
              value={release.id}
              onChange={(event) => setSelected(event.target.value)}
            >
              {releases.map((item) => (
                <option key={item.id} value={item.id}>
                  SEC accepted {day(item.published_at)} UTC ·{" "}
                  {item.current ? "current source" : "history"} · saved{" "}
                  {stamp(item.available_at)}
                </option>
              ))}
            </Select>
          </label>
        )}
      </div>
      {!release ? (
        <p>
          {data.status === "unavailable"
            ? data.message
            : "Collect original documents below to look for an earnings outlook."}
        </p>
      ) : (
        <div className="outlook-reading" key={release.id}>
          {!release.current && (
            <p className="financial-note">
              Historical source version. This is not the current earnings
              release.
            </p>
          )}
          <p className="outlook-meta">
            First saved {stamp(release.available_at)}. SEC filing accepted{" "}
            {stamp(release.published_at)}.
          </p>
          {data.source_status?.last_error && (
            <p className="financial-note">
              Latest document check: {data.source_status.last_error}
            </p>
          )}
          {!release.sections.length && (
            <p>
              No supported outlook section was identified in this release. Its
              full text remains available below.
            </p>
          )}
          {release.sections.map((section) => (
            <section className="outlook-period" key={section.id}>
              <h3>{section.heading}</h3>
              {section.review_status && (
                <p className="financial-note">
                  This section refers to earlier or withdrawn guidance. Read the
                  context before treating a figure as a current expectation.
                </p>
              )}
              <div className="outlook-dates">
                <div>
                  <span>Release’s stated date</span>
                  <strong>
                    {release.stated_release_date
                      ? day(release.stated_release_date.date)
                      : "Not established"}
                  </strong>
                </div>
                <div>
                  <span>Forecast period ends</span>
                  <strong>
                    {section.period_end
                      ? day(section.period_end)
                      : "Not established"}
                  </strong>
                </div>
              </div>
              <div className="outlook-forecasts">
                {section.forecasts.map((forecast) => (
                  <Forecast
                    key={forecast.id}
                    forecast={forecast}
                    release={release}
                  />
                ))}
              </div>
              <details className="outlook-context">
                <summary>Read the outlook in context</summary>
                {release.stated_release_date && (
                  <blockquote>{release.stated_release_date.quote}</blockquote>
                )}
                {section.passages.map((passage) => (
                  <p key={passage.id}>{passage.quote}</p>
                ))}
                {section.truncated && (
                  <p>
                    This saved excerpt is bounded. Open the full release for the
                    remaining context.
                  </p>
                )}
                <a href={release.url} target="_blank" rel="noreferrer">
                  Read the original release ↗
                </a>
              </details>
            </section>
          ))}
          <details className="outlook-limits">
            <summary>Coverage &amp; comparison rules</summary>
            {data.limitations.map((line) => (
              <p key={line}>{line}</p>
            ))}
            <p>
              At most 20 release versions and 100 reporting periods with their
              first retained original filing result are inspected. Earlier
              history may remain outside this view.
            </p>
          </details>
        </div>
      )}
    </section>
  );
}
