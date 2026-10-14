import { useEffect, useState } from "react";
import { api } from "../api/client";
import { useProfile } from "../lib/profile";
import { companyName } from "../lib/companyIdentity";
import { overviewNews } from "../lib/overviewSections";
import { sourceCoverage } from "../lib/sourceCoverage";
import {
  newsLight,
  platformName,
  priceLine,
  socialLight,
  socialTones,
  whatHappened,
  worldForCompany,
  worldLight,
} from "../lib/beginnerSummary";
import "./BeginnerSummary.css";

// Beginner summary, "Signals" layout: the price, three lights (News, People
// online, World) readable in seconds, one-line reasons, a merged list of what
// happened, and the user's own view. No charts. Everything rewords saved
// readings; Fledge never says buy or sell.
export default function BeginnerSummary({
  data,
  instrumentId,
  visible,
  savedView,
  onSaveView,
  onView,
  onSource,
  onWorld,
  onUpdate,
}) {
  const [world, setWorld] = useState(null);
  const { mode } = useProfile();
  useEffect(() => {
    if (!visible) return;
    let active = true;
    api
      .worldNews()
      .then((page) => active && setWorld(page))
      .catch(() => active && setWorld({ articles: [] }));
    return () => {
      active = false;
    };
  }, [visible, instrumentId]);

  const name = companyName(data.instrument);
  const price = priceLine(data.market?.quote?.quote);
  const reading = data.sentiment?.withheld ? null : data.sentiment;
  const scopes = sourceCoverage(reading).scopes;
  const newsTone = scopes.find((s) => s.scope === "news");
  const social = socialTones(scopes);
  const items = overviewNews(data);
  const analysedNews = items.filter((s) => s.kind === "news");
  // Without a news reading, show the saved company documents instead (newest
  // first, no tone), so the card is never empty when sources exist.
  const news = (
    analysedNews.length
      ? analysedNews
      : (data.documents || [])
          .filter((d) => d.title)
          .map((d) => ({ ...d, headline: d.title }))
          .sort((a, b) => Date.parse(b.published_at) - Date.parse(a.published_at))
  ).slice(0, 5);
  const posts = items.filter((s) => s.kind === "social").slice(0, 3);
  const { linked } = worldForCompany(world, instrumentId);
  const lights = [
    newsLight({
      tone: newsTone?.tone,
      counts: newsTone?.sentimentSummary?.counts,
      analysed: newsTone?.analysed || 0,
      newsCount: news.length,
      latest: news[0]?.headline,
    }),
    socialLight(social),
    worldLight(linked, name),
  ];
  const timeline = whatHappened({ news, posts, world: linked });
  const pointer = lights.some((l) => l.mood === "bad")
    ? "Something here could hurt. Worth reading the reasons before you decide anything."
    : null;

  return (
    <div className="beginner-summary signals">
      <section className="bs-price-row" aria-label="Share price">
        {price ? (
          <>
            <strong>{price.price}</strong>
            {price.move && (
              <span className={`mood-${price.mood}`}>
                <span aria-hidden="true">
                  {price.mood === "bad" ? "▼ " : price.mood === "good" ? "▲ " : ""}
                </span>
                {price.move}
              </span>
            )}
          </>
        ) : (
          <span className="bs-muted">No share price saved yet</span>
        )}
      </section>

      <section aria-labelledby="bs-lights-title">
        <h4 id="bs-lights-title" className="sr-only">
          {name} at a glance
        </h4>
        <ul className="bs-lights">
          {lights.map((light) => (
            <li key={light.key}>
              <a className={`bs-light mood-${light.mood}`} href={`#why-${light.key}`}>
                <span className="bs-dot" aria-hidden="true"></span>
                <span className="bs-light-title">{light.title}</span>
                <strong>{light.status}</strong>
              </a>
            </li>
          ))}
        </ul>
        {pointer && <p className="bs-pointer">{pointer}</p>}
      </section>

      <section className="bs-card" aria-labelledby="bs-why">
        <h4 id="bs-why">Why these lights?</h4>
        <ul className="bs-why">
          {lights.map((light) => (
            <li key={light.key} id={`why-${light.key}`} tabIndex={-1}>
              <span className={`bs-dot mood-${light.mood}`} aria-hidden="true"></span>
              <span>
                <strong>{light.title}:</strong> {light.reason}
              </span>
            </li>
          ))}
        </ul>
        {linked.some((x) => x.link) && (
          <p className="bs-caveat">
            World links are possibilities to think about, not predictions or tips.
          </p>
        )}
      </section>

      <section className="bs-card" aria-labelledby="bs-happened">
        <h4 id="bs-happened">What happened</h4>
        {timeline.length ? (
          <ul className="bs-timeline">
            {timeline.map((row) => (
              <li key={row.id}>
                <span className="bs-day">{row.day}</span>
                {row.kind === "world" ? (
                  <a href={row.url} target="_blank" rel="noopener noreferrer">
                    {row.text}
                    <small> · World</small>
                  </a>
                ) : (
                  <button type="button" className="bs-link" onClick={() => onSource?.(row.item)}>
                    {row.text}
                    <small> · {row.kind === "post" ? platformName(row.item.platform) : row.item.source || "News"}</small>
                  </button>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <p className="bs-muted">
            Nothing saved yet.{" "}
            {onUpdate && (
              <button type="button" className="bs-link inline" onClick={onUpdate}>
                Get the latest news
              </button>
            )}
          </p>
        )}
        <div className="bs-more-row">
          <button type="button" className="bs-more" onClick={() => onView?.("evidence")}>
            All news & posts →
          </button>
          <button type="button" className="bs-more" onClick={onWorld}>
            World news →
          </button>
        </div>
      </section>

      <section className="bs-card bs-view" aria-labelledby="bs-yourview">
        <h4 id="bs-yourview">Your view</h4>
        {savedView?.question ? (
          <>
            <p>{savedView.question}</p>
            {savedView.reasoning && <p className="bs-muted">{savedView.reasoning}</p>}
          </>
        ) : (
          <p className="bs-muted">
            Why are you interested in {name}? Write it down in a sentence. Later,
            you can turn on news alerts to hear when news backs it up or goes
            against it.
          </p>
        )}
        {onSaveView && (
          <button type="button" className="primary" onClick={onSaveView}>
            {savedView ? "Edit my view" : "Write my view"}
          </button>
        )}
      </section>

      <p className="bs-note">
        The lights describe what is being said, not whether to buy or sell.
        {mode === "explain"
          ? " Switch to Pro for financials, charts and comparisons."
          : " The other tabs have the financials, charts and comparisons."}
      </p>
    </div>
  );
}
