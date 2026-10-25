import { formatTimestamp } from "../lib/dateTime";
import { guidanceReason } from "../lib/overviewSections";
import { readableNote } from "../lib/readingNotes";
import { useId, useState } from "react";
import TermHelp from "./TermHelp";
import Select from "./Select";
import EvidenceButton from "./EvidenceButton";
import { Disclosure, SourceChip } from "./ui";
import { day, amount } from "./FinancialOverview";
import "./ManagementOutlook.css";

const stamp = (value) => formatTimestamp(value, { fallback: "Not recorded" });
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

function Forecast({ forecast, release, section }) {
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
      <EvidenceButton
        title={`${forecast.label} · original guidance`}
        label="Evidence"
        className="guidance-evidence"
      >
        <blockquote>{forecast.quote}</blockquote>
        {forecast.low != null && (
          <p>
            Exact {range ? "range" : "point"}: {forecast.low}
            {range && " to " + forecast.high}{" "}
            {forecast.unit || "dollars; currency unspecified"}.
          </p>
        )}
        {forecast.calculation && (
          <p>
            Range calculated from the stated guidance: {forecast.calculation}.
          </p>
        )}
        {section.period_evidence?.map((e, i) => (
          <div key={i}>
            <p>Forecast date is stated in the same release’s reconciliation:</p>
            <blockquote>{e.heading.quote}</blockquote>
            {e.passages
              .filter((p) => /revenue|ending|ended|20\d{2}/i.test(p.quote))
              .map((p) => (
                <blockquote key={p.id}>{p.quote}</blockquote>
              ))}
          </div>
        ))}
        <p>
          Passage {forecast.id} · SEC filing accepted{" "}
          {stamp(release.published_at)}.
        </p>
        <p>First saved {stamp(release.available_at)}.</p>
        <a href={release.url} target="_blank" rel="noreferrer">
          Open original earnings release ↗
        </a>
      </EvidenceButton>
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
        ) : null}
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
          <span className="outlook-source-badge">Company guidance</span>
          <TermHelp term="guidance" />
          <h2 id={id + "-title"}>Management outlook</h2>
          <p>What the company expects, from its original earnings release.</p>
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
                  SEC {stamp(item.published_at)} ·{" "}
                  {item.current ? "latest saved release" : "history"}
                </option>
              ))}
            </Select>
          </label>
        )}
      </div>
      {guidanceReason(data) && (
        <p className="outlook-data-note" role="status">
          {guidanceReason(data)}
        </p>
      )}
      {!release ? (
        <div className="outlook-empty">
          <h3>No saved company guidance</h3>
          <p>
            {data.status === "unavailable"
              ? data.message
              : "Use Update data at the top of the page to collect original earnings releases."}
          </p>
        </div>
      ) : (
        <div className="outlook-reading" key={release.id}>
          {!release.current && (
            <p className="outlook-data-note">
              Historical source version. This is not the current earnings
              release.
            </p>
          )}
          {data.source_status?.last_error && (
            <p className="outlook-data-note" role="status">
              Latest document check: {data.source_status.last_error}
            </p>
          )}
          {release.sections.map((section) => (
            <section className="outlook-period" key={section.id}>
              <div className="outlook-period-heading">
                <h3>{section.heading}</h3>
                <span className="outlook-status">
                  {!release.current ||
                  (section.period_end &&
                    section.period_end < new Date().toISOString().slice(0, 10))
                    ? "Historical guidance"
                    : section.period_end
                      ? "Latest saved guidance"
                      : "Latest release · exact date not stated"}
                </span>
              </div>
              {section.review_status && (
                <p className="outlook-data-note">
                  {section.review_message ||
                    "This section refers to earlier or withdrawn guidance. Read the context before treating it as a current expectation."}
                </p>
              )}
              <p className="outlook-meta fine">
                Release dated{" "}
                {release.stated_release_date
                  ? day(release.stated_release_date.date)
                  : "not established"}{" "}
                · forecast period ends{" "}
                {section.period_end
                  ? day(section.period_end)
                  : section.period_label
                    ? `${section.period_label} (exact date not stated)`
                    : "not identified"}
              </p>
              <div className="outlook-forecasts">
                {section.forecasts.map((forecast) => (
                  <Forecast
                    key={forecast.id}
                    forecast={forecast}
                    release={release}
                    section={section}
                  />
                ))}
              </div>
              {section.forecasts.some(
                (forecast) => forecast.comparison.status !== "compared",
              ) && (
                <details className="outlook-comparison-gaps">
                  <summary>
                    Why guidance isn’t compared with results yet
                  </summary>
                  {section.forecasts
                    .filter(
                      (forecast) => forecast.comparison.status !== "compared",
                    )
                    .map((forecast) => (
                      <div key={forecast.id}>
                        <strong>{forecast.label}</strong>
                        <ul>
                          {forecast.comparison.reasons.map((reason) => (
                            <li key={reason}>{reason}</li>
                          ))}
                        </ul>
                      </div>
                    ))}
                </details>
              )}
              <Disclosure variant="flush" className="outlook-context" title="Read the outlook in context">
                {release.stated_release_date && (
                  <blockquote>{release.stated_release_date.quote}</blockquote>
                )}
                {(section.context_evidence || []).map((passage) => (
                  <p key={passage.id}>{passage.quote}</p>
                ))}
                {section.passages.map((passage) => (
                  <p key={passage.id}>{passage.quote}</p>
                ))}
                {section.truncated && (
                  <p>
                    Only part of this section is saved. Open the full release to
                    read the rest.
                  </p>
                )}
                <SourceChip label="Original release" href={release.url} />
              </Disclosure>
            </section>
          ))}
          <Disclosure variant="flush" className="outlook-limits" title="Release details and limits">
            <p className="fine">
              First saved {stamp(release.available_at)}. SEC filing accepted {stamp(release.published_at)}. The stated release date comes from the release’s own dateline; SEC acceptance and first-saved time are separate dates.
            </p>
            {data.limitations.map((line) => (
              <p className="fine" key={line}>{readableNote(line)}</p>
            ))}
            <p className="fine">
              This covers a limited set of saved releases and reports. Earlier forecasts and results may be missing.
            </p>
            <SourceChip label="Open original earnings release" href={release.url} />
          </Disclosure>
        </div>
      )}
    </section>
  );
}
