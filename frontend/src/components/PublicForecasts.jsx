import ForecastRange from "./ForecastRange";
import "./PublicForecasts.css";

const stamp = (value) => new Date(value).toLocaleString("en-GB");

export default function PublicForecasts({ source, busy, onRefresh }) {
  if (!source) return null;
  const record = source.available ? source.snapshot : null;
  const history = source.available ? source.history || [] : [];
  const paused =
    source.next_check_at && new Date(source.next_check_at) > new Date();
  return (
    <section
      className={`outlook-provider public-forecasts ${record ? "has-forecasts" : "empty-provider"}`}
      aria-label="Public annual financial forecasts"
    >
      <div className="outlook-provider-heading">
        <div>
          <span className="outlook-source-badge">
            Stock Analysis · S&amp;P Global
          </span>
          <h3>Public annual forecasts</h3>
        </div>
        <div className="outlook-check">
          <button
            onClick={onRefresh}
            disabled={busy || paused || !source.available}
          >
            {busy ? "Checking…" : "Check public forecasts"}
          </button>
          {paused && source.available && (
            <small>Next check {stamp(source.next_check_at)}</small>
          )}
        </div>
      </div>
      {!source.available && (
        <p className="outlook-source-notice" role="status">
          Access to this source is disabled.
        </p>
      )}
      {source.error && (
        <p className="outlook-source-notice" role="status">
          {source.error} Saved forecasts remain below when available.
        </p>
      )}
      {!record && (
        <p className="outlook-source-time">
          No public financial forecast has been saved yet.
        </p>
      )}
      {record && (
        <>
          <p className="outlook-source-time">
            Observed {stamp(record.observed_at)}
            {record.stale ? " · older than 24 hours" : ""} · source page updated{" "}
            {record.data.page_updated_on || "date unavailable"} · underlying
            forecast date unknown
          </p>
          {record.data.forecasts.map((forecast) => (
            <section
              className="outlook-estimate-period"
              key={forecast.period_end}
            >
              <div className="outlook-period-heading">
                <h4>
                  FY {forecast.fiscal_year} · period ending{" "}
                  {forecast.period_end}
                </h4>
                <span className="outlook-status">Adjusted EPS</span>
              </div>
              <p className="outlook-data-note">
                Forecast currency is not stated. Values use the source’s units.
              </p>
              <div className="forecast-ranges">
                {forecast.metrics.map((metric) => (
                  <ForecastRange key={metric.key} metric={metric} adjusted />
                ))}
              </div>
              <p className="outlook-source-time">
                {forecast.displayed_analyst_count
                  ? `${forecast.displayed_analyst_count} analysts in the annual table; contributors to each metric are not specified.`
                  : "Analyst count is unavailable."}
              </p>
            </section>
          ))}
          {!!record.data.restricted_years.length && (
            <p className="outlook-source-time">
              Restricted years ({record.data.restricted_years.join(", ")}) are
              not collected.
            </p>
          )}
          <a
            className="outlook-original-link"
            href={record.data.url}
            target="_blank"
            rel="noreferrer"
          >
            Inspect the public forecast tables ↗
          </a>
        </>
      )}
      <details className="outlook-source-details">
        <summary>Source &amp; coverage</summary>
        <p>
          Revenue and adjusted earnings are analyst forecasts, not reported
          results or management guidance.
        </p>
        {record && <p>{record.data.limitation}</p>}
        {paused && (
          <p>
            Next page check: {stamp(source.next_check_at)}. This shares the
            24-hour check limit with price targets.
          </p>
        )}
        {record && (
          <p>
            Observed {stamp(record.observed_at)}. Source page updated{" "}
            {record.data.page_updated_on || "date unavailable"}; the underlying
            forecast date is unknown.
          </p>
        )}
      </details>
      {record && (
        <details className="forecast-history outlook-source-details">
          <summary>
            Saved public forecast observations ({history.length})
          </summary>
          {history.map((item) => (
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
      )}
    </section>
  );
}
