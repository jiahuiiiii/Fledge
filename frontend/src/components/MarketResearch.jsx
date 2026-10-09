import { modelAvailability } from "../lib/modelAvailability";
import Select from "./Select";
import { useId, useState } from "react";
import { latestPriceQuote, quoteMovement } from "../lib/priceRefresh";
import PriceChange from "./PriceChange";
export const stamp = (value) =>
  value
    ? new Date(value).toLocaleString("en-GB", {
        day: "numeric",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
        timeZone: "UTC",
      }) + " UTC"
    : "Not checked";
const money = (value) =>
  value == null
    ? "—"
    : Number(value).toLocaleString("en-US", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      });

export function MarketQuote({ market, history, compact = false }) {
  const record = market?.quote,
    q = record?.quote,
    status = market?.status;
  const latest = latestPriceQuote(market, history);
  const movement = quoteMovement(market, history);
  const interrupted =
    status?.lease_until && new Date(status.lease_until) < new Date();
  return (
    <section
      className={`market-quote${compact ? " compact" : ""}`}
      aria-label="Market quote"
    >
      <div className="quote-primary">
        {!compact && (
          <span className="section-label">PRICE CONTEXT · FINNHUB</span>
        )}
        {latest ? (
          <>
            <div className="quote-value">
              <strong>{money(latest.price)}</strong>
              <span>USD</span>
              {movement ? (
                <PriceChange movement={movement} />
              ) : (
                <span className="fine">Change unavailable</span>
              )}
            </div>
            <small>
              Yahoo Finance · {latest.session} · {stamp(latest.quoted_at)}
            </small>
          </>
        ) : q ? (
          <>
            <div className="quote-value">
              <strong>{money(q.price)}</strong>
              <span>USD</span>
              {movement ? (
                <PriceChange movement={movement} />
              ) : (
                <span className="fine">Change unavailable</span>
              )}
            </div>
            <small>
              {compact ? "Finnhub · " : "Quote as of "}
              {stamp(q.quoted_at)}
            </small>
          </>
        ) : (
          <p>No quote retrieved. Choose Refresh research to load it.</p>
        )}
        {!compact && status?.quote_error && (
          <p className="warning" role="status">
            Finnhub quote check unavailable. {status.quote_error}{" "}
            {q && !latest && "Showing the previous Finnhub quote."}
          </p>
        )}
        {!compact && interrupted && (
          <p className="warning">
            The previous refresh was interrupted. Displayed data may be older.
          </p>
        )}
      </div>
      {q && !compact && (
        <div className="quote-range">
          <div className="row">
            <span>DAY RANGE</span>
            <span>
              {money(q.low)} — {money(q.high)}
            </span>
          </div>
          <div className="range-track">
            {q.low != null && q.high > q.low && (
              <i
                style={{
                  left: `${(100 * (q.price - q.low)) / (q.high - q.low)}%`,
                }}
              />
            )}
          </div>
          <div className="row">
            <span>Open {money(q.open)}</span>
            <span>Previous close {money(q.previous_close)}</span>
          </div>
        </div>
      )}
      {!compact && (
        <details className="quote-foot secondary-details">
          <summary>Quote source details</summary>
          <p>
            Retrieved {stamp(record?.retrieved_at)} from Finnhub. Market data
            may be delayed.
          </p>
          <p>
            Price movement does not establish why a company’s outlook changed.
          </p>
        </details>
      )}
    </section>
  );
}

export default function MarketResearch({
  data,
  question,
  busy,
  modelStatus,
  onGenerate,
  onSource,
}) {
  const [expanded, setExpanded] = useState(false);
  const [pointKind, setPointKind] = useState("all");
  const viewId = useId();
  const superseded = new Set(data.documents.map((d) => d.supersedes_id));
  const seen = new Set();
  const order = new Map((data.market_news_ids || []).map((id, i) => [id, i]));
  const all = data.documents
    .filter((d) => d.kind === "news" && !superseded.has(d.id))
    .sort(
      (a, b) =>
        (order.get(a.id) ?? 9999) - (order.get(b.id) ?? 9999) ||
        new Date(b.published_at) - new Date(a.published_at),
    );
  const unique = all.filter((d) => {
    if (seen.has(d.content_hash)) return false;
    seen.add(d.content_hash);
    return true;
  });
  // Stories in the saved tone reading are listed once, with their label, in
  // the tone section below; this list carries the rest.
  const analysed = new Set(
    data.sentiment && !data.sentiment.withheld
      ? (data.sentiment.sources || [])
          .filter((s) => s.kind === "news" && !s.comparison_only)
          .map((s) => s.id)
      : [],
  );
  const news = unique.filter((d) => !analysed.has(d.id));
  const labelled = unique.length - news.length;
  const status = data.market?.status,
    brief = data.market_brief;
  const kinds = {
    reported: "Reported developments",
    interpretation: "AI interpretation",
    uncertainty: "Uncertainty",
  };
  const points = brief?.points || [];
  const visiblePoints = points.filter(
    (p) => pointKind === "all" || p.kind === pointKind,
  );
  const focus =
    question === "What could weaken the growth story?"
      ? "Look for developments that could challenge growth and what remains unconfirmed. Reported developments can contain risks even when they are not labelled uncertainty."
      : question === "Are expectations supported by reported performance?"
        ? "Check who made each expectation and when. Company guidance, a publisher’s forecast and reported results are different kinds of evidence; this brief does not supply independent consensus."
        : question === "Can growth hold up without sacrificing margins?"
          ? "Compare growth and margins across matching periods. A report about spending or demand does not by itself establish a change in reported margins."
          : "Compare each sourced development with your question and assumptions. A company-wide briefing does not automatically answer a custom research question.";
  return (
    <section className="market-research" aria-label="Company news and briefing">
      <div className="market-section-head news-heading">
        <h2>Recent company news</h2>
        <span className="fine">
          {labelled
            ? `${labelled} labelled ${labelled === 1 ? "story is" : "stories are"} under What’s the tone?`
            : "Company mentions first, newest within each group"}
        </span>
      </div>
      {status?.news_error && (
        <p className="warning" role="status">
          Finnhub news check unavailable. {status.news_error}{" "}
          {news.length > 0 && "Previously retrieved stories remain below."}
        </p>
      )}
      {!status?.news_error && status?.news_count === 0 && (
        <p className="fine">
          No articles returned for the seven-day window ending{" "}
          {status?.last_attempt_at?.slice(0, 10)}.{" "}
          {news.length > 0 &&
            "Showing previously retrieved stories and any saved briefing below."}
        </p>
      )}
      {!news.length && status?.news_count !== 0 && (
        <p className="fine">
          {status?.news_count === 0
            ? "The last successful check returned no company news."
            : "No news retrieved yet. Choose Refresh research."}
        </p>
      )}
      {all.length > unique.length && (
        <p className="fine">
          Duplicate supplied text is grouped. Multiple articles do not
          necessarily provide independent confirmation.
        </p>
      )}
      <div className="news-list">
        {(expanded ? news : news.slice(0, 5)).map((d) => (
          <article key={d.id} className="news-item">
            <div className="news-meta">
              <span>{d.source}</span>
              <time dateTime={d.published_at}>{stamp(d.published_at)}</time>
            </div>
            <button className="news-title" onClick={() => onSource(d.id)}>
              {d.title} <span>↗</span>
            </button>
            {d.body && <p>{d.body}</p>}
            <a
              href={d.url}
              target="_blank"
              rel="noopener noreferrer"
              className="source-link"
              aria-label={`Read original: ${d.title}`}
            >
              Read original ↗
            </a>
          </article>
        ))}
      </div>
      {news.length > 5 && (
        <button className="news-more" onClick={() => setExpanded(!expanded)}>
          {expanded ? "Show fewer stories" : `Show all ${news.length} stories`}
        </button>
      )}
      <details className="news-brief-details">
        <summary>AI company briefing · {brief ? "saved" : "optional"}</summary>
        <div className="market-section-head">
          <div>
            <span className="section-label">RESEARCH BRIEF</span>
            <h2>What’s developing</h2>
          </div>
          {!brief && (
            <button
              disabled={
                busy ||
                !news.length ||
                !modelStatus?.briefing_enabled ||
                modelStatus?.budget.unresolved > 0
              }
              onClick={onGenerate}
            >
              {busy ? "Reading sources…" : "Summarise sources"}
            </button>
          )}
        </div>
        {question && (
          <p className="fine">
            <strong>Reading focus:</strong> {focus} The shared company briefing
            stays the same when you change questions.
          </p>
        )}
        {!brief &&
          (!modelStatus?.briefing_enabled ||
            modelStatus?.budget.unresolved > 0) && (
            <p className="fine" role="status">
              {modelAvailability(modelStatus, "briefing_enabled").message}
            </p>
          )}
        {brief ? (
          <>
            <p className="fine">
              AI summary · {brief.included_news_count} supplied
              headlines/snippets · latest news {stamp(brief.latest_news_at)}.
              Interpretation may omit context.
            </p>
            <label className="field" htmlFor={viewId}>
              Briefing view
              <Select
                id={viewId}
                aria-label="Briefing view"
                value={pointKind}
                onChange={(e) => setPointKind(e.target.value)}
                aria-controls={`${viewId}-points`}
              >
                <option value="all">All points ({points.length})</option>
                {Object.entries(kinds).map(([kind, label]) => (
                  <option key={kind} value={kind}>
                    {label} ({points.filter((p) => p.kind === kind).length})
                  </option>
                ))}
              </Select>
            </label>
            <p className="fine" role="status">
              {visiblePoints.length
                ? `Showing ${visiblePoints.length} of ${points.length} briefing points. Labels describe the AI summary’s type, not whether a development is favourable.`
                : `No points in this briefing are labelled ${kinds[pointKind]?.toLowerCase()}. This does not establish that no risks or uncertainty exist; inspect All points and the original sources.`}
            </p>
            <div className="market-brief-points" id={`${viewId}-points`}>
              {visiblePoints.map((p, i) => (
                <article key={i} className={`market-point ${p.kind}`}>
                  <span className="section-label">
                    {p.kind === "reported"
                      ? "REPORTED"
                      : p.kind === "interpretation"
                        ? "AI INTERPRETATION"
                        : "UNCERTAINTY"}
                  </span>
                  <h3>{p.title}</h3>
                  <p>{p.text}</p>
                  <div className="brief-citations">
                    {p.citations.map((c, j) => (
                      <button
                        key={j}
                        className="source-link"
                        onClick={() => onSource(c.source_id)}
                        title={c.quote}
                        aria-label={`Inspect source ${j + 1}: ${data.documents.find((d) => d.id === c.source_id)?.title || "Source unavailable"}`}
                      >
                        {data.documents.find((d) => d.id === c.source_id)
                          ?.source || "Source"}{" "}
                        {j + 1} ↗
                      </button>
                    ))}
                  </div>
                </article>
              ))}
            </div>
            <details className="brief-unknowns">
              <summary>About this AI summary</summary>
              <p className="fine">{brief.limitation}</p>
            </details>
          </>
        ) : (
          <p className="fine">
            Read the news below, or request a concise AI briefing of the
            supplied headlines and snippets. Your saved reasoning stays
            separate. No AI call runs when you open or refresh this page.
          </p>
        )}
      </details>
    </section>
  );
}
