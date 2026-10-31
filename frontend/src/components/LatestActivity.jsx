import { formatTimestamp } from "../lib/dateTime";
import {
  headlinesAfterReading,
  overviewNews,
  recentHeadlines,
} from "../lib/overviewSections";
import { Button, Card, SectionHeader } from "./ui";

const when = (value) => formatTimestamp(value, { fallback: "Not checked" });

// What happened lately, one line each: price move, headlines from the past
// day, a tone reading that is out of date, updates waiting and watch status.
// A headline is shown beside the price, never as proof of why it moved.
export default function LatestActivity({
  data,
  instrumentId,
  onUpdates,
  onView,
  onSource,
}) {
  const quote = data?.market?.quote?.quote;
  const watch = data?.news_watch;
  const headlines = overviewNews(data);
  const today = recentHeadlines(headlines).slice(0, 3);
  const notInTone = headlinesAfterReading(data?.sentiment, headlines);
  const unread = [
    ...(data?.research_alerts || []),
    ...(data?.idea_alerts || []),
  ].filter(
    (a) =>
      a.instrument_id === instrumentId &&
      !a.review_action &&
      !a.status_only &&
      !a.withheld,
  ).length;
  const items = [];
  if (quote?.change_percent != null && quote?.quoted_at) {
    const down = quote.change_percent < 0;
    items.push(
      <li key="price" className={down ? "down" : "up"}>
        <span aria-hidden="true">{down ? "▼" : "▲"}</span>
        <span>
          Share price {down ? "fell" : "rose"}{" "}
          {Math.abs(quote.change_percent).toFixed(1)}% in the session to{" "}
          {when(quote.quoted_at)}
        </span>
      </li>,
    );
  }
  if (today.length)
    items.push(
      <li key="headlines" className="headlines">
        <span aria-hidden="true">≡</span>
        <div>
          <span>Company headlines in the past day</span>
          <ul>
            {today.map((source) => (
              <li key={source.id}>
                <button
                  className="glance-headline"
                  onClick={() => onSource?.(source)}
                >
                  {source.headline}
                </button>
                <small>
                  {source.source || "News"} · {when(source.published_at)}
                </small>
              </li>
            ))}
          </ul>
        </div>
      </li>,
    );
  if (notInTone.length && data?.sentiment?.created_at)
    items.push(
      <li key="tone" className="watch">
        <span aria-hidden="true">◎</span>
        <span>
          The AI tone reading was saved {when(data.sentiment.created_at)} and
          does not include {notInTone.length} newer news{" "}
          {notInTone.length === 1 ? "headline" : "headlines"}{" "}
          <Button
            variant="tertiary"
            size="inline"
            onClick={() => onView("evidence")}
          >
            News & discussion →
          </Button>
        </span>
      </li>,
    );
  if (unread)
    items.push(
      <li key="alerts" className="alert">
        <span aria-hidden="true">●</span>
        <span>
          {unread} update{unread === 1 ? "" : "s"} waiting for your review{" "}
          {onUpdates && (
            <Button variant="tertiary" size="inline" onClick={onUpdates}>
              Review
            </Button>
          )}
        </span>
      </li>,
    );
  if (watch?.enabled && watch.last_check_at)
    items.push(
      <li key="watch" className="watch">
        <span aria-hidden="true">◎</span>
        <span>
          Your news watch last {watch.error ? "attempted an update" : "checked"}{" "}
          {when(watch.last_check_at)}
          {watch.error && <> · {watch.error}</>}
        </span>
      </li>,
    );
  if (!items.length) return null;
  return (
    <Card className="glance-activity" aria-labelledby="latest-activity-title">
      <SectionHeader
        level="card"
        as="h3"
        id="latest-activity-title"
        title="Latest activity"
      />
      <ul>{items}</ul>
    </Card>
  );
}
