import { newsSourceStatus } from "../lib/newsPresentation";
import { stamp } from "./MarketResearch";
export default function NewsStatus({ data, availability, onCoverage }) {
  const status = newsSourceStatus(data),
    analysis = data.sentiment;
  return (
    <details className="news-section-status">
      <summary>
        <span>
          {status.feeds.length
            ? `${status.failed.length} of ${status.feeds.length} news feeds unavailable`
            : "No news feeds checked"}
          {status.latest && ` · last check ${stamp(status.latest)}`}
          {status.social.length > 0 &&
            ` · ${status.social.length} discussion feeds unavailable`}
          {data.news_watch?.error && " · watch incomplete"}
          {analysis?.stale && " · older reading"}
          {analysis?.earlier_method &&
            !analysis.withheld &&
            " · earlier method"}
        </span>
        <span className="status-details-label">Details</span>
      </summary>
      <div className="news-status-details">
        {(data.provider_status || [])
          .filter((row) => row.channel === "social" && row.status !== "ready")
          .map((row) => (
            <p key={row.provider}>
              <strong>{row.label}:</strong> {row.message}
            </p>
          ))}
        {status.failed.map((row) => (
          <p key={row.provider}>
            <strong>{row.label}:</strong> {row.message}
          </p>
        ))}
        {status.social.map((row) => (
          <p key={row.feed}>
            <strong>{row.label || row.feed}:</strong> {row.error}
          </p>
        ))}
        {data.news_watch?.error && <p>{data.news_watch.error}</p>}
        {analysis?.stale && (
          <p>
            The saved reading uses a source sample captured over 24 hours ago.
            Read its dated sources before treating it as current.
          </p>
        )}
        {analysis?.earlier_method && !analysis.withheld && (
          <p>
            Saved with an earlier analysis method. A different label in a new
            reading alone is not a change in the news.
          </p>
        )}
        {availability.detail && (
          <details>
            <summary>AI request details</summary>
            <p>{availability.detail}</p>
          </details>
        )}
        <button className="source-link" onClick={onCoverage}>
          Open Data &amp; sources
        </button>
        <p>
          Inspect the affected connection and its next allowed check. Saved
          sources remain available; checks follow the existing schedule.
        </p>
      </div>
    </details>
  );
}
