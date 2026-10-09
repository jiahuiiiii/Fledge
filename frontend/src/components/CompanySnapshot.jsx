import { day, snapshot } from "../lib/companySnapshot";
import "./CompanySnapshot.css";

const marks = {
  pass: ["✓", "Met"],
  fail: ["✗", "Not met"],
  unknown: ["–", "Unknown"],
};

function Checks({ checks }) {
  if (!checks.length) return null;
  const met = checks.filter((c) => c.state === "pass").length;
  return (
    <div className="glance-checks">
      <span className="glance-score">
        Checks {met}/{checks.length}
      </span>
      <ul>
        {checks.map((c) => (
          <li key={c.label} className={`glance-check ${c.state}`}>
            <span aria-hidden="true">{marks[c.state][0]}</span>
            <span className="sr-only">{marks[c.state][1]}: </span>
            {c.label}
          </li>
        ))}
      </ul>
    </div>
  );
}

function ToneBar({ tone }) {
  if (!tone?.total) return null;
  const { positive = 0, neutral = 0, mixed = 0, negative = 0 } = tone.counts;
  const parts = [
    ["positive", positive, "positive"],
    ["neutral", neutral + mixed, "neutral or mixed"],
    ["negative", negative, "negative"],
  ];
  return (
    <div className="glance-tone">
      <div
        className="glance-tone-bar"
        role="img"
        aria-label={parts.map(([, n, label]) => `${n} ${label}`).join(", ")}
      >
        {parts.map(([key, n]) =>
          n ? <span key={key} className={key} style={{ flexGrow: n }} /> : null,
        )}
      </div>
      <p>
        {parts.map(([key, n, label]) => (
          <span key={key} className={key}>
            <strong>{n}</strong> {label}
          </span>
        ))}
      </p>
    </div>
  );
}

function Activity({ data, instrumentId, onUpdates }) {
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
        {watch.error ? " · last check had a problem" : ""}
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
}) {
  const { sentences, sections } = snapshot(data);
  return (
    <section className="glance" aria-label="Company summary">
      {sentences.length ? (
        <p className="glance-summary">{sentences.join(" ")}</p>
      ) : (
        <p className="glance-summary muted">
          A short summary appears once filings and news are loaded. Use Refresh
          research to load them.
        </p>
      )}
      <Activity data={data} instrumentId={instrumentId} onUpdates={onUpdates} />
      {chart}
      <div className="glance-grid">
        {sections.map((section) => (
          <article
            key={section.title}
            className="glance-card"
            aria-labelledby={`glance-${section.number}`}
          >
            <div className="glance-card-head">
              <h4 id={`glance-${section.number}`}>{section.title}</h4>
              <button
                className="glance-open"
                onClick={() => onView(section.tab)}
              >
                {section.action} <span aria-hidden="true">→</span>
              </button>
            </div>
            <Checks checks={section.checks} />
            <div className="glance-figures">
              {section.figures.map((figure) => (
                <div
                  key={figure.label}
                  className={`glance-figure ${figure.tone}`}
                >
                  <strong className={figure.value ? "" : "missing"}>
                    {figure.value || "Not available"}
                  </strong>
                  <span>{figure.label}</span>
                </div>
              ))}
            </div>
            <ToneBar tone={section.tone} />
            {section.note && <p className="glance-note">{section.note}</p>}
          </article>
        ))}
      </div>
    </section>
  );
}
