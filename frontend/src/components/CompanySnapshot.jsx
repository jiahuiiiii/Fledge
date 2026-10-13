import { formatTimestamp } from "../lib/dateTime";
import { day, snapshot } from "../lib/companySnapshot";
import "./CompanySnapshot.css";
import TermHelp from "./TermHelp";
import OverviewSections from "./OverviewSections";
import { companyName } from "../lib/companyIdentity";
import {
  currentGuidance,
  headlinesAfterReading,
  overviewNews,
  recentHeadlines,
  revenueComparisons,
} from "../lib/overviewSections";

const when = (value) => formatTimestamp(value, { fallback: "Not checked" });

// Collection status is separate from the dates and limits of each conclusion.
function Freshness({ data }) {
  const checks = (data?.source_checks || []).filter((c) => c.checked_at);
  if (!checks.length) return null;
  const latest = checks
    .map((c) => c.checked_at)
    .sort((a, b) => Date.parse(b) - Date.parse(a))[0];
  const states = (data.source_checks || []).map((c) => c.state);
  return (
    <p className="glance-freshness">
      <span>
        Data freshness · latest source check {when(latest)}
        {states.includes("stale") && " · some coverage is over 24 hours old"}
        {states.some(
          (state) => !["fresh", "stale", "unknown"].includes(state),
        ) && " · some source checks did not finish successfully"}
        {states.includes("unknown") && " · some coverage is unknown"}
      </span>
    </p>
  );
}

// The product's core loop: save a view, then get told what supports or challenges it.
function YourView({ data, savedView, onSaveView }) {
  if (!onSaveView) return null;
  const name = companyName(data.instrument);
  if (!savedView)
    return (
      <section className="glance-view" aria-labelledby="glance-view-title">
        <div>
          <h4 id="glance-view-title">What do you think of {name}?</h4>
          <p>
            Write your view in a sentence or two. Fledge then watches news,
            filings and results for evidence that supports or challenges it.
          </p>
        </div>
        <div className="glance-view-actions">
          <button className="primary" onClick={onSaveView}>
            Save my view
          </button>
        </div>
      </section>
    );
  return (
    <section className="glance-view saved" aria-labelledby="glance-view-title">
      <div>
        <h4 id="glance-view-title">
          Your view{" "}
          <span
            className={`status ${savedView.status === "monitoring" ? "met" : ""}`}
          >
            {savedView.status === "monitoring" ? "Watching" : "Draft"}
          </span>
        </h4>
        {savedView.question && <p>{savedView.question}</p>}
        {savedView.reasoning && (
          <p className="glance-view-reasoning">{savedView.reasoning}</p>
        )}
      </div>
      <div className="glance-view-actions">
        <button onClick={onSaveView}>Edit my view</button>
      </div>
    </section>
  );
}

function Activity({ data, instrumentId, onUpdates, onView, onSource }) {
  const quote = data?.market?.quote?.quote;
  const watch = data?.news_watch;
  const headlines = overviewNews(data);
  const today = recentHeadlines(headlines).slice(0, 3);
  const notInTone = headlinesAfterReading(data?.sentiment, headlines);
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
        {when(quote.quoted_at)}
      </li>,
    );
  }
  // Shown beside the price, not as its cause: a headline is not proof of why
  // the price moved.
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
        The AI tone reading was saved {when(data.sentiment.created_at)} and does
        not include {notInTone.length} newer news{" "}
        {notInTone.length === 1 ? "headline" : "headlines"}
        <button className="glance-link" onClick={() => onView("evidence")}>
          News & discussion →
        </button>
      </li>,
    );
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
        Your news watch last {watch.error
          ? "attempted an update"
          : "checked"}{" "}
        {when(watch.last_check_at)}
        {watch.error && (
          <>
            {" "}
            · {watch.error}{" "}
            <button className="glance-link" onClick={() => onView("evidence")}>
              Source details →
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
  savedView,
  onSaveView,
  financialError,
  onRetryFinancials,
}) {
  const { sentences, growth } = snapshot(data);
  const { latestQuarter } = revenueComparisons(
    data,
    currentGuidance(data?.management_outlook),
  );
  return (
    <section className="glance" aria-label="Company summary">
      {data.financials_pending ? (
        <p className="glance-summary muted" role="status">
          {financialError || "Loading saved financials…"}
          {financialError && (
            <button onClick={onRetryFinancials}>Try again</button>
          )}
        </p>
      ) : sentences.length ? (
        <p className="glance-summary">
          {latestQuarter ? (
            <span className="glance-growth">
              <span className="glance-growth-title">
                <strong>
                  Revenue {latestQuarter.growth >= 0 ? "up" : "down"}{" "}
                  {Math.abs(latestQuarter.growth).toFixed(1)}% · latest quarter
                  vs a year earlier
                </strong>
                <TermHelp term="revenue_growth" />
              </span>
              <small>
                Quarter to {day(latestQuarter.current.end)} vs quarter to{" "}
                {day(latestQuarter.previous.end)}
                {growth &&
                  ` · fiscal year to ${day(growth.periodEnd)}: ${growth.growth >= 0 ? "+" : "−"}${Math.abs(growth.growth).toFixed(1)}%`}
              </small>
            </span>
          ) : (
            growth && (
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
            )
          )}
          {sentences.slice(growth ? 1 : 0).join(" ")}
        </p>
      ) : (
        <p className="glance-summary muted">
          A short summary appears once filings and news are loaded. Use Update
          to load them.
        </p>
      )}
      <Freshness data={data} />
      <YourView data={data} savedView={savedView} onSaveView={onSaveView} />
      <Activity
        data={data}
        instrumentId={instrumentId}
        onUpdates={onUpdates}
        onView={onView}
        onSource={onSource}
      />
      {chart}
      {!data.financials_pending && (
        <OverviewSections
          data={data}
          instrumentId={instrumentId}
          visible={visible}
          onView={onView}
          onSource={onSource}
          businessPanel={businessPanel}
          focusTopic={focusTopic}
        />
      )}
    </section>
  );
}
