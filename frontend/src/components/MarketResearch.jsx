import { formatTimestamp } from "../lib/dateTime";
import { modelAvailability } from "../lib/modelAvailability";
import { currentCompanyHeadlines } from "../lib/companyHeadlines";
import { newsSourceStatus } from "../lib/newsPresentation";
import {
  Badge,
  Button,
  Card,
  Disclosure,
  FilterGroup,
  SourceChip,
  EmptyState,
  NewsIcon,
  MetaRow,
  SectionHeader,
  StoryCard,
} from "./ui";
import "./NewsDiscussion.css";
import { useId, useState } from "react";
import {
  extendedLine,
  latestPriceQuote,
  quoteMovement,
  sessionLabel,
} from "../lib/priceRefresh";
import PriceChange from "./PriceChange";
import ExtendedPrice from "./ExtendedPrice";
export const stamp = formatTimestamp;
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
  const extended = extendedLine(history);
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
              {extended ? (
                <span className="quote-session">At close · </span>
              ) : (
                sessionLabel(latest.session) && (
                  <span className="quote-session">
                    {sessionLabel(latest.session)} ·{" "}
                  </span>
                )
              )}
              Yahoo Finance
              {!extended &&
                !sessionLabel(latest.session) &&
                ` · ${latest.session}`}{" "}
              · {stamp(latest.quoted_at)}
            </small>
            {extended && <ExtendedPrice line={extended} />}
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
          <p>
            No share price saved yet. Prices load once the company’s data is
            updated.
          </p>
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
  const currentNews = currentCompanyHeadlines(data);
  const latestNews = currentNews.slice(0, 3);
  const previewIds = new Set(latestNews.map((d) => d.id));
  const sourceStatus = newsSourceStatus(data);
  // Stories in the saved tone reading are listed once, with their label, in
  // the tone section below; this list carries the rest.
  const analysed = new Set(
    data.sentiment && !data.sentiment.withheld
      ? (data.sentiment.sources || [])
          .filter((s) => s.kind === "news" && !s.comparison_only)
          .map((s) => s.id)
      : [],
  );
  const news = currentNews.filter(
    (d) => !analysed.has(d.id) && !previewIds.has(d.id),
  );
  const availability = modelAvailability(modelStatus, "briefing_enabled");
  const brief = data.market_brief;
  const kinds = {
    reported: "Reported developments",
    interpretation: "AI interpretation",
    uncertainty: "Uncertainty",
  };
  const points = brief?.points || [];
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
      <Disclosure
        className="market-research unanalysed-headlines"
        title="More headlines"
        description={`${news.length} company mentions · not analysed`}
      >
        <p className="fine">
          Only headlines or supplied snippets that name {data.instrument.symbol}{" "}
          or the company appear here. The latest three appear above. These
          additional headlines have no saved tone label.
        </p>
        {!news.length && (
          <p className="fine">
            No additional unanalysed company headlines. Saved readings and the
            complete source sample remain available above.
          </p>
        )}
        <div className="news-list">
          {(expanded ? news : news.slice(0, 5)).map((d) => (
            <StoryCard
              key={d.id}
              variant="flush"
              className="news-item"
              title={d.title}
              onOpen={() => onSource(d.id)}
              meta={
                <>
                  <span>{d.source}</span>
                  <time dateTime={d.published_at}>{stamp(d.published_at)}</time>
                </>
              }
              footer={
                <Button
                  variant="tertiary"
                  size="sm"
                  href={d.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={`Read original: ${d.title}`}
                >
                  Read original ↗
                </Button>
              }
            >
              {d.body && <p>{d.body}</p>}
            </StoryCard>
          ))}
        </div>
        {news.length > 5 && (
          <Button
            variant="plain"
            className="news-more"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded
              ? "Show fewer stories"
              : `Show all ${news.length} stories`}
          </Button>
        )}
      </Disclosure>
    );
  return (
    <section
      className="market-research news-developments"
      aria-label="Company developments"
    >
      <SectionHeader
        icon={<NewsIcon />}
        title="What’s developing"
        description="The latest company headlines, straight from saved sources."
        actions={<Badge>Past 7 days</Badge>}
      />
      <MetaRow>
        {latestNews.length > 0 && (
          <span>Latest headline {stamp(latestNews[0].published_at)}</span>
        )}
        {sourceStatus.latest && (
          <span>Latest source check {stamp(sourceStatus.latest)}</span>
        )}
      </MetaRow>
      {latestNews.length > 0 ? (
        <div className="development-headlines">
          {latestNews.map((story) => (
            <StoryCard
              key={story.id}
              className="development-card"
              title={story.title}
              onOpen={() => onSource(story.id)}
              meta={
                <>
                  <Badge>{story.source}</Badge>
                  <time dateTime={story.published_at}>
                    {stamp(story.published_at)}
                  </time>
                </>
              }
              footer={
                <Button
                  variant="tertiary"
                  size="sm"
                  onClick={() => onSource(story.id)}
                  aria-haspopup="dialog"
                >
                  Read story <span aria-hidden="true">↗</span>
                </Button>
              }
            >
              {story.body && <p>{story.body}</p>}
            </StoryCard>
          ))}
        </div>
      ) : (
        <EmptyState
          className="news-empty"
          title="No company headlines yet"
          description={`No saved headlines naming ${data.instrument.symbol} in the current seven-day sample. Use Update data to check for news.`}
        />
      )}
      <Disclosure
        className="current-news-summary"
        title={brief ? "Saved AI summary" : "Optional AI summary"}
      >
        {!brief && (
          <Button
            size="sm"
            disabled={
              busy ||
              !(data.market_news_ids || []).length ||
              availability.blocked
            }
            onClick={onGenerate}
            aria-describedby={
              availability.blocked && availability.state !== "running"
                ? "sentiment-disabled-reason"
                : undefined
            }
          >
            {busy ? "Reading sources…" : "Summarise sources"}
          </Button>
        )}
        {brief ? (
          <>
            <p className="fine">
              AI summary · {brief.included_news_count} supplied
              headlines/snippets · latest news {stamp(brief.latest_news_at)}.
              Interpretation may omit context.
            </p>
            <FilterGroup
              label="Briefing view"
              value={pointKind}
              controls={`${viewId}-points`}
              onValueChange={setPointKind}
              options={[
                { value: "all", label: "All", count: points.length },
                ...Object.entries(kinds).map(([kind, label]) => ({
                  value: kind,
                  label,
                  count: points.filter((p) => p.kind === kind).length,
                })),
              ]}
            />
            <p className="fine" role="status">
              {visiblePoints.length
                ? `Showing ${visiblePoints.length} of ${matchingPoints.length} developments. Labels describe the kind of statement, not whether it is favourable.`
                : `No points in this briefing are labelled ${kinds[pointKind]?.toLowerCase()}. This does not establish that no risks or uncertainty exist; inspect All points and the original sources.`}
            </p>
            <div className="brief-points" id={`${viewId}-points`}>
              {visiblePoints.map((p, i) => (
                <Card as="article" variant="inset" key={i} className={`brief-point ${p.kind}`}>
                  <Badge>
                    {p.kind === "reported"
                      ? "Reported"
                      : p.kind === "interpretation"
                        ? "AI interpretation"
                        : "Uncertainty"}
                  </Badge>
                  <h4>{p.title}</h4>
                  <p>{p.text}</p>
                  <div className="brief-citations">
                    {p.citations.map((c, j) => (
                      <SourceChip
                        key={j}
                        label={`${data.documents.find((d) => d.id === c.source_id)?.source || "Source"} ${j + 1}`}
                        onOpen={() => onSource(c.source_id)}
                        title={c.quote}
                        aria-label={`Inspect source ${j + 1}: ${data.documents.find((d) => d.id === c.source_id)?.title || "Source unavailable"}`}
                      />
                    ))}
                  </div>
                </Card>
              ))}
            </div>
            {matchingPoints.length > 3 && (
              <Button
                variant="tertiary"
                size="sm"
                type="button"
                className="news-more"
                onClick={() => setExpanded(!expanded)}
              >
                {expanded
                  ? "Show fewer developments"
                  : `Read all ${matchingPoints.length} developments`}
              </Button>
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
        ) : (
          <p className="fine">
            An AI summary is optional and uses the existing allowance. The
            headlines above update when sources are checked, even if an AI
            reading is older or could not finish.
          </p>
        )}
      </Disclosure>
    </section>
  );
}
