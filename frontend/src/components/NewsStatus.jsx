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
            ? `${status.checked.length} of ${status.feeds.length} news feeds checked successfully`
            : "No news feeds checked"}
          {status.failed.length > 0 &&
            ` · ${status.failed.length} ${status.failed.length === 1 ? "needs" : "need"} attention`}
          {status.waiting.length > 0 && ` · ${status.waiting.length} deferred`}
          {status.unchecked.length > 0 &&
            ` · ${status.unchecked.length} not checked`}
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
        {status.checked.length > 0 && (
          <p>
            <strong>Checked successfully:</strong>{" "}
            {status.checked.map((row) => row.label).join(", ")}. A successful
            check can return no matching company stories.
          </p>
        )}
        {status.waiting.length > 0 && (
          <details>
            <summary>
              {status.waiting.length} checks deferred by the refresh schedule
            </summary>
            <p>
              These checks made no new request. Saved news is retained; this
              does not establish whether each feed is currently reachable.
            </p>
            {status.waiting.map((row) => (
              <p key={row.provider}>
                <strong>{row.label}:</strong>{" "}
                {row.next_check_at
                  ? `Next check allowed ${stamp(row.next_check_at)}.`
                  : "Ready for a new source check."}
              </p>
            ))}
          </details>
        )}
        {status.unchecked.length > 0 && (
          <p>
            <strong>Not checked for this company:</strong>{" "}
            {status.unchecked.map((row) => row.label).join(", ")}.
          </p>
        )}
        {(data.provider_status || [])
          .filter(
            (row) =>
              row.channel === "social" &&
              ["blocked", "failed"].includes(row.status),
          )
          .map((row) => (
            <p key={row.provider}>
              <strong>{row.label}:</strong> {row.message}
            </p>
          ))}
        {status.failed.map((row) => (
          <p key={row.provider}>
            <strong>{row.label}:</strong> {row.message}
            {row.next_check_at &&
              ` Next check allowed ${stamp(row.next_check_at)}.`}
          </p>
        ))}
        {status.optional.length > 0 && (
          <p>
            <strong>Optional sources off:</strong>{" "}
            {status.optional.map((row) => row.label).join(", ")}.
          </p>
        )}
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
          Saved news remains available in News &amp; discussion. Open Data &amp;
          sources for individual checks; use Research updates to refresh sources
          when their wait has ended.
        </p>
      </div>
    </details>
  );
}
