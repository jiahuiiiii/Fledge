import { day, snapshot } from "../lib/companySnapshot";
import "./CompanySnapshot.css";
import TermHelp from "./TermHelp";
import OverviewSections from "./OverviewSections";

function Activity({ data, instrumentId, onUpdates, onView }) {
  const quote = data?.market?.quote?.quote;
  const watch = data?.news_watch;
  const unread = [
    ...(data?.research_alerts || []),
    ...(data?.idea_alerts || []),
  ].filter(
    (a) => a.instrument_id === instrumentId && !a.review_action && !a.withheld,
  ).length;
  const items = [];
  if (quote?.change_percent != null && quote?.quoted_at) {
    const down = quote.change_percent < 0;
    items.push(
      <li key="price" className={down ? "down" : "up"}>
        <span aria-hidden="true">{down ? "▼" : "▲"}</span>
        Share price {down ? "fell" : "rose"}{" "}
        {Math.abs(quote.change_percent).toFixed(1)}% in the session to{" "}
        {day(quote.quoted_at)}
      </li>,
    );
  }
  if (unread)
    items.push(
      <li key="alerts" className="alert">
        <span aria-hidden="true">●</span>
        {unread} update{unread === 1 ? "" : "s"} waiting for your review
        {onUpdates && (
          <button className="glance-link" onClick={onUpdates}>
            Review
          </button>
        )}
      </li>,
    );
  if (watch?.enabled && watch.last_check_at)
    items.push(
      <li key="watch" className="watch">
        <span aria-hidden="true">◎</span>
        Your news watch last checked{" "}
        {new Date(watch.last_check_at).toLocaleString("en-GB", {
          day: "numeric",
          month: "short",
          hour: "2-digit",
          minute: "2-digit",
        })}
        {watch.error && (
          <>
            {" "}
            · check incomplete{" "}
            <button className="glance-link" onClick={() => onView("evidence")}>
              Feed status →
            </button>
          </>
        )}
      </li>,
    );
  if (!items.length) return null;
  return (
    <div className="glance-activity">
      <h4>Latest activity</h4>
      <ul>{items}</ul>
    </div>
  );
}

export default function CompanySnapshot({
  data,
  instrumentId,
  onView,
  onUpdates,
  chart = null,
  visible,
  onSource,
  businessPanel,
  focusTopic,
}) {
  const { sentences, growth } = snapshot(data);
  return (
    <section className="glance" aria-label="Company summary">
      {sentences.length ? (
        <p className="glance-summary">
          {growth && (
            <span className="glance-growth">
              <span className="glance-growth-title">
                <strong>
                  Revenue {growth.growth >= 0 ? "grew" : "fell"}{" "}
                  {Math.abs(growth.growth).toFixed(1)}% · last fiscal year
                </strong>
                <TermHelp term="revenue_growth" />
              </span>
              <small>
                Year ended {day(growth.periodEnd)} vs year ended{" "}
                {day(growth.previousEnd)}
              </small>
            </span>
          )}
          {sentences.slice(growth ? 1 : 0).join(" ")}
        </p>
      ) : (
        <p className="glance-summary muted">
          A short summary appears once filings and news are loaded. Use Refresh
          research to load them.
        </p>
      )}
      <Activity
        data={data}
        instrumentId={instrumentId}
        onUpdates={onUpdates}
        onView={onView}
      />
      {chart}
      <OverviewSections
        data={data}
        instrumentId={instrumentId}
        visible={visible}
        onView={onView}
        onSource={onSource}
        businessPanel={businessPanel}
        focusTopic={focusTopic}
      />
    </section>
  );
}
