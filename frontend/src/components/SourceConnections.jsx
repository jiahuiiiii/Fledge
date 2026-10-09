import { stamp } from "./MarketResearch";
export default function SourceConnections({ data, loadingRun }) {
  return (
    <>
      <div className="sentiment-collection-details">
        <div
          className="social-source-summary"
          aria-label="Social collection status"
        >
          {["reddit", "hackernews"].map((platform) => {
            const feeds = (data.social_status || []).filter(
              (s) => s.platform === platform,
            );
            const step = loadingRun?.steps.find((s) => s.key === platform);
            const count =
              data.sentiment_inputs?.scopes?.[platform]?.available || 0;
            const errors = feeds.filter((s) => s.enabled && s.error);
            return (
              <div key={platform}>
                <strong>
                  {platform === "reddit" ? "Reddit" : "Hacker News"}
                </strong>
                <span>
                  {step && ["queued", "running"].includes(step.status)
                    ? `${step.status === "queued" ? "Queued" : "Fetching discussions"}…`
                    : `${count} saved candidate ${count === 1 ? "discussion item" : "discussion items"} in the current analysis window`}
                </span>
                {errors.length > 0 ? (
                  <p>
                    {errors.length} source{" "}
                    {errors.length === 1 ? "check is" : "checks are"}{" "}
                    incomplete.{" "}
                    {errors.some((s) => s.error?.includes("429"))
                      ? "The provider is rate-limiting requests; retry after its cooldown."
                      : "See the connection details below."}
                  </p>
                ) : (
                  count === 0 &&
                  !["queued", "running"].includes(step?.status) && (
                    <p>
                      No matching discussion was returned in this window. Try a
                      longer window or another company. An empty sample does not
                      mean neutral sentiment.
                    </p>
                  )
                )}
              </div>
            );
          })}
        </div>
        <details className="secondary-details provider-coverage">
          <summary>Publisher feeds &amp; source connections</summary>
          <p>
            News feeds supply headlines and summaries. Social posts remain a
            separate sample. An unavailable source is not neutral sentiment.
          </p>
          <div className="provider-list">
            {(data.provider_status || []).map((source) => (
              <div className="provider-row" key={source.provider}>
                <div>
                  <strong>{source.label}</strong>
                  <span>
                    {source.channel === "news" ? "News" : "Social discussion"} ·{" "}
                    {source.checked_at
                      ? stamp(source.checked_at)
                      : "Not checked"}
                  </span>
                </div>
                <div>
                  <b className={`provider-state ${source.status}`}>
                    {source.status === "ready"
                      ? `${source.matched} matching ${source.matched === 1 ? "report" : "reports"}`
                      : source.status === "blocked"
                        ? "Connection needed"
                        : source.status === "failed"
                          ? "Unavailable"
                          : "Waiting"}
                  </b>
                  <p>{source.message}</p>
                </div>
              </div>
            ))}
          </div>
        </details>
      </div>
      <details className="social-coverage">
        <summary>Social source coverage</summary>
        {data.social_status?.map((s) => (
          <p className="fine" key={s.feed}>
            {s.label || `Reddit · r/${s.feed}`} ·{" "}
            {s.enabled ? "enabled" : "disabled"} · checked{" "}
            {stamp(s.completed_at)} ·{" "}
            {s.error ||
              (s.kind && s.notice) ||
              (s.post_count == null
                ? "Not checked"
                : `${s.post_count} candidates checked; ${s.matched_count} matching posts or comments retained; ${s.excluded_count} excluded.`)}
            {s.notice && !s.kind && <> {s.notice}</>}
            {s.sample_notice && <> {s.sample_notice}</>}
          </p>
        ))}
        <p className="fine">
          Repeated text is grouped for counts. Different posts are not
          necessarily independent opinions. Author identities and popularity do
          not determine the labels.
        </p>
      </details>
    </>
  );
}
