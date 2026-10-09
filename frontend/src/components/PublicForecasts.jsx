import "./PublicForecasts.css";

const stamp = (value) => new Date(value).toLocaleString("en-GB");
const number = (value) => {
  const [whole, fraction] = String(value).split(".");
  return (
    whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",") +
    (fraction ? `.${fraction}` : "")
  );
};

export default function PublicForecasts({ source, busy, onRefresh }) {
  if (!source) return null;
  const record = source.snapshot;
  const paused =
    source.next_check_at && new Date(source.next_check_at) > new Date();
  return (
    <section
      className="business-topic public-forecasts"
      aria-label="Public annual financial forecasts"
    >
      <div className="financial-heading">
        <div>
          <h3>Public annual forecasts</h3>
          <p className="public-forecast-meta">
            Stock Analysis · S&amp;P Global
          </p>
        </div>
        <button
          onClick={onRefresh}
          disabled={busy || paused || !source.available}
        >
          {busy ? "Checking…" : "Check public forecasts"}
        </button>
      </div>
      <p>
        Analysts’ expectations for revenue and adjusted earnings. These are
        separate from the company’s reported results.
      </p>
      {paused && (
        <p className="public-forecast-meta">
          Next page check: {stamp(source.next_check_at)}. This shares the
          24-hour check limit with price targets.
        </p>
      )}
      {!source.available && <p>Access to this source is disabled.</p>}
      {source.error && (
        <p role="status">
          {source.error} Saved forecasts remain below when available.
        </p>
      )}
      {!record && <p>No public financial forecast has been saved yet.</p>}
      {record && (
        <>
          <p className="public-forecast-meta">
            Observed {stamp(record.observed_at)}
            {record.stale ? " · older than 24 hours" : ""}. Source page updated{" "}
            {record.data.page_updated_on || "date unavailable"}; the underlying
            forecast date is unknown.
          </p>
          {record.data.forecasts.map((forecast) => (
            <section key={forecast.period_end}>
              <h4>
                FY {forecast.fiscal_year} · period ending {forecast.period_end}
              </h4>
              <p className="financial-note">
                Forecast currency is not stated in the public table. Values
                below use the source’s units.{" "}
                {forecast.displayed_analyst_count
                  ? `The annual table lists ${forecast.displayed_analyst_count} analysts; contributors to each metric are not specified.`
                  : "Analyst count is unavailable."}
              </p>
              <div className="forecast-ranges">
                {forecast.metrics.map((metric) => {
                  const low = Number(metric.low),
                    high = Number(metric.high),
                    average = Number(metric.average);
                  const position =
                    high === low ? 50 : ((average - low) / (high - low)) * 100;
                  return (
                    <article className="forecast-range" key={metric.key}>
                      <h5>
                        {metric.key === "eps"
                          ? "Adjusted earnings per share"
                          : "Revenue"}
                      </h5>
                      <p className="forecast-average">
                        {metric.source_display.average}
                        <span>average estimate</span>
                      </p>
                      <div className="forecast-track" aria-hidden="true">
                        <span style={{ left: `${position}%` }} />
                      </div>
                      <div className="forecast-endpoints">
                        <span>Low {metric.source_display.low}</span>
                        <span>High {metric.source_display.high}</span>
                      </div>
                      <details>
                        <summary>Exact values &amp; definition</summary>
                        <p>
                          Low {number(metric.low)} · average{" "}
                          {number(metric.average)} · high {number(metric.high)}.{" "}
                          {metric.basis}. The marker shows the average within
                          this forecast range; each metric uses its own scale.
                        </p>
                        <p>
                          The source’s range table rounds its average to{" "}
                          {number(metric.range_average)}. This view retains the
                          more precise annual-table average.
                        </p>
                      </details>
                    </article>
                  );
                })}
              </div>
            </section>
          ))}
          <p className="financial-note">
            {record.data.limitation}{" "}
            {record.data.restricted_years.length > 0 &&
              `Restricted years (${record.data.restricted_years.join(", ")}) are not collected.`}
          </p>
          <a href={record.data.url} target="_blank" rel="noreferrer">
            Inspect the public forecast tables ↗
          </a>
          <details className="forecast-history">
            <summary>
              Saved public forecast observations ({source.history.length})
            </summary>
            {source.history.map((item) => (
              <section key={item.id}>
                <p>Observed {stamp(item.observed_at)}</p>
                {item.data.forecasts.map((f) => (
                  <p key={f.period_end}>
                    FY {f.fiscal_year}, ending {f.period_end}:{" "}
                    {f.metrics
                      .map(
                        (m) =>
                          `${m.key === "eps" ? "adjusted EPS" : "revenue"} average ${m.source_display.average}`,
                      )
                      .join(" · ")}
                    . Currency unspecified.
                  </p>
                ))}
              </section>
            ))}
          </details>
        </>
      )}
    </section>
  );
}
