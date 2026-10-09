import { modelAvailability } from "../lib/modelAvailability";
import { mentionsCompany, savedDevelopments } from "../lib/companyHeadlines";
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
  headlinesOnly = false,
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
  const unanalysed = unique.filter((d) => !analysed.has(d.id));
  const news = unanalysed.filter((d) => mentionsCompany(d, data.instrument));
  const availability = modelAvailability(modelStatus, "briefing_enabled");
  const brief = data.market_brief;
  const kinds = {
    reported: "Reported developments",
    interpretation: "AI interpretation",
    uncertainty: "Uncertainty",
  };
  const points = brief?.points || [];
  const developments = savedDevelopments(data.sentiment).slice(0, 3);
  const matchingPoints = points.filter(
    (p) => pointKind === "all" || p.kind === pointKind,
  );
  const visiblePoints = expanded ? matchingPoints : matchingPoints.slice(0, 3);
  const focus =
    question === "What could weaken the growth story?"
      ? "Look for developments that could challenge growth and what remains unconfirmed. Reported developments can contain risks even when they are not labelled uncertainty."
      : question === "Are expectations supported by reported performance?"
        ? "Check who made each expectation and when. Company guidance, a publisher’s forecast and reported results are different kinds of evidence; this brief does not supply independent consensus."
        : question === "Can growth hold up without sacrificing margins?"
          ? "Compare growth and margins across matching periods. A report about spending or demand does not by itself establish a change in reported margins."
          : "Compare each sourced development with your question and assumptions. A company-wide briefing does not automatically answer a custom research question.";
  if (headlinesOnly)
    return (
      <details className="market-research unanalysed-headlines">
        <summary>
          More headlines{" "}
          <span>{news.length} company mentions · not analysed</span>
        </summary>
        <p className="fine">
          Only headlines or supplied snippets that name {data.instrument.symbol}{" "}
          or the company appear here.{" "}
          {unanalysed.length - news.length > 0
            ? `${unanalysed.length - news.length} without an explicit mention are hidden from this list. `
            : ""}
          These have no saved tone label.
        </p>
        {!news.length && (
          <p className="fine">
            No additional unanalysed company headlines. Saved readings and the
            complete source sample remain available above.
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
            {expanded
              ? "Show fewer stories"
              : `Show all ${news.length} stories`}
          </button>
        )}
      </details>
    );
  return (
    <section
      className="market-research news-developments"
      aria-label="Company developments"
    >
      <div className="market-section-head">
        <div>
          <h2>What’s developing</h2>
        </div>
        {!brief && (
          <button
            disabled={busy || !unique.length || availability.blocked}
            onClick={onGenerate}
            aria-describedby={
              availability.blocked && availability.state !== "running"
                ? "sentiment-disabled-reason"
                : undefined
            }
          >
            {busy ? "Reading sources…" : "Summarise sources"}
          </button>
        )}
      </div>
      {brief ? (
        <>
          <p className="fine">
            AI summary · {brief.included_news_count} supplied headlines/snippets
            · latest news {stamp(brief.latest_news_at)}. Interpretation may omit
            context.
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
              ? `Showing ${visiblePoints.length} of ${matchingPoints.length} developments. Labels describe the kind of statement, not whether it is favourable.`
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
          {matchingPoints.length > 3 && (
            <button
              type="button"
              className="news-more"
              onClick={() => setExpanded(!expanded)}
            >
              {expanded
                ? "Show fewer developments"
                : `Read all ${matchingPoints.length} developments`}
            </button>
          )}
          <details className="brief-unknowns">
            <summary>About this AI summary</summary>
            <p className="fine">{brief.limitation}</p>
            {question && (
              <p className="fine">
                <strong>Reading focus:</strong> {focus}
              </p>
            )}
          </details>
        </>
      ) : developments.length ? (
        <>
          <p className="fine">
            Latest reported developments from the saved reading ·{" "}
            {stamp(data.sentiment.created_at)}. Headlines and snippets from the
            original publishers.
          </p>
          <div className="development-headlines">
            {developments.map((story) => (
              <article key={story.id}>
                <span className="fine">
                  {story.source} · {stamp(story.published_at)}
                </span>
                <button
                  className="news-title"
                  onClick={() => onSource(story.id)}
                >
                  {story.title} <span>↗</span>
                </button>
                {story.body && <p>{story.body}</p>}
              </article>
            ))}
          </div>
        </>
      ) : (
        <p className="fine">
          No reported developments in the saved reading yet. Read the tone and
          original sources below, or summarise sources when AI is available.
        </p>
      )}
    </section>
  );
}
