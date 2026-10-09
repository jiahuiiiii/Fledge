import PublicForecasts from "./PublicForecasts";
import ForecastRange from "./ForecastRange";
import LoadingSkeleton from "./LoadingSkeleton";
import TermHelp from "./TermHelp";

const stamp = (value) =>
  value ? new Date(value).toLocaleString("en-GB") : "Not established";
const exact = (value) => (value == null ? "Unavailable" : String(value));

export default function AnalystForecasts({
  data,
  busy,
  error,
  onCheck,
  onCheckPublic,
}) {
  const source = data?.consensus;
  const forecasts = source?.data?.forecasts || [];
  const hasPublic = !!(
    data?.public_forecasts?.available && data.public_forecasts.snapshot
  );
  return (
    <section
      className="fmp-panel outlook-analysts"
      aria-label="Analyst forecasts"
    >
      <header className="outlook-section-heading">
        <div>
          <h2>Analyst forecasts</h2>
          <p>
            Revenue and earnings estimates, kept separate by source.{" "}
            <TermHelp term="consensus" />
          </p>
        </div>
      </header>
      {error && (
        <p className="warning" role="alert">
          {error}
        </p>
      )}
      {!data && !error && (
        <LoadingSkeleton
          variant="panel"
          rows={2}
          label="Loading saved forecasts…"
        />
      )}
      {data && (
        <>
          <section
            className={`outlook-provider ${forecasts.length ? "has-forecasts" : "empty-provider"}`}
            aria-label="FMP financial expectations"
          >
            <div className="outlook-provider-heading">
              <div>
                <span className="outlook-source-badge">FMP</span>
                <h3>
                  {forecasts.length
                    ? "Financial expectations"
                    : "No saved FMP forecasts"}
                </h3>
              </div>
              <button disabled={busy} onClick={onCheck}>
                {busy ? "Checking…" : "Check FMP data"}
              </button>
            </div>
            {forecasts.length > 0 && (
              <p className="outlook-source-time">
                First observed {stamp(source.first_observed_at)} · checked{" "}
                {stamp(source.checked_at)}
              </p>
            )}
            {source?.message && (
              <p className="outlook-source-notice" role="status">
                {source.message}
              </p>
            )}
            {forecasts.map((forecast) => (
              <section
                className="outlook-estimate-period"
                key={forecast.period_end}
              >
                <div className="outlook-period-heading">
                  <h4>Annual period ending {forecast.period_end}</h4>
                  <span className="outlook-status">Analyst estimates</span>
                </div>
                <p className="outlook-data-note">
                  Currency: {forecast.currency || "not supplied by provider"} ·
                  Earnings accounting convention unspecified
                </p>
                <div className="forecast-ranges">
                  {forecast.metrics.map((metric) => (
                    <ForecastRange
                      key={metric.key}
                      metric={metric}
                      currency={forecast.currency}
                    />
                  ))}
                </div>
              </section>
            ))}
            {!forecasts.length && !hasPublic && data.symbol && (
              <p className="outlook-reading-link">
                <a
                  href={`https://stockanalysis.com/stocks/${encodeURIComponent(data.symbol.toLowerCase())}/forecast/`}
                  target="_blank"
                  rel="noreferrer"
                >
                  Inspect public financial forecasts on Stock Analysis ↗
                </a>
                <span>
                  Use the public forecast check below to save the available
                  annual table. Some years require membership; EPS is adjusted.
                </span>
              </p>
            )}
            <details className="outlook-source-details">
              <summary>Data source details</summary>
              {!forecasts.length && (
                <p>
                  First observed {stamp(source?.first_observed_at)} · last
                  checked {stamp(source?.checked_at)}
                </p>
              )}
              <p>
                {source?.data?.limitation ||
                  "Consensus is separate from management guidance and price targets. Missing forecasts remain unknown."}
              </p>
              <p>
                Data access depends on your FMP subscription. Checking data
                makes no AI request.
              </p>
              {data.profile?.data && (
                <p>
                  FMP classification: {data.profile.data.sector} ·{" "}
                  {data.profile.data.industry}. {data.profile.data.limitation}
                </p>
              )}
            </details>
            {data.consensus_history?.length > 0 && (
              <details className="outlook-source-details forecast-history">
                <summary>
                  Saved forecast vintages ({data.consensus_history.length})
                </summary>
                {data.consensus_history.map((vintage) => (
                  <section key={vintage.id}>
                    <p>First observed {stamp(vintage.available_at)}</p>
                    {vintage.data.forecasts.map((forecast) => (
                      <p key={forecast.period_end}>
                        Period ending {forecast.period_end} · revenue average{" "}
                        {exact(
                          forecast.metrics.find((m) => m.key === "revenue")
                            ?.average,
                        )}{" "}
                        · EPS average{" "}
                        {exact(
                          forecast.metrics.find((m) => m.key === "eps")
                            ?.average,
                        )}{" "}
                        · currency {forecast.currency || "unspecified"}
                      </p>
                    ))}
                  </section>
                ))}
              </details>
            )}
          </section>
          <PublicForecasts
            source={data.public_forecasts}
            busy={busy}
            onRefresh={onCheckPublic}
          />
        </>
      )}
    </section>
  );
}
