import { useEffect, useState } from "react";
import { api } from "../api/client";
import { useProfile } from "../lib/profile";
import { companyName } from "../lib/companyIdentity";
import { overviewNews } from "../lib/overviewSections";
import { sourceCoverage } from "../lib/sourceCoverage";
import {
  countLabel,
  countMood,
  dayLabel,
  groupByTone,
  newsMeaning,
  peopleMeaning,
  plainTone,
  platformName,
  priceLine,
  socialTones,
  worldForCompany,
  worldLight,
} from "../lib/beginnerSummary";

const EFFECT_WORDS = {
  could_help: "Could help",
  could_hurt: "Could hurt",
  mixed_or_unclear: "Could go either way",
};
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
  onRate,
  rating = false,
  practice = false,
}) {
  const [world, setWorld] = useState(null);
  const { mode, setDetailMode } = useProfile();
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
  const { linked } = worldForCompany(world, instrumentId);
  const allPosts = items.filter((s) => s.kind === "social");
  const newsGroups = groupByTone(news.length ? (analysedNews.length ? analysedNews : news) : []);
  const postGroups = groupByTone(allPosts);
  const links = linked.filter((x) => x.link);
  const worldState = worldLight(linked, name);
  const lights = [
    { key: "news", title: "News", mood: countMood(newsGroups), status: countLabel(newsGroups) },
    {
      key: "people",
      title: "People online",
      mood: countMood(postGroups),
      status: countLabel(postGroups, { good: "upbeat", bad: "worried", neutral: "neutral" }),
    },
    { key: "world", title: "World", mood: worldState.mood, status: worldState.status },
  ];
  const pointer = worldState.hurt
    ? worldState.reason
    : newsGroups.bad.length > newsGroups.good.length
      ? "There has been more bad news than good recently. Read both sides below."
      : null;
  const rated =
    newsGroups.good.length + newsGroups.bad.length + newsGroups.mixed.length +
      newsGroups.neutral.length + postGroups.good.length + postGroups.bad.length +
      postGroups.mixed.length > 0;
  const SHAPE = { good: "▲", bad: "▼", mixed: "◆", none: "●" };
  const MOOD_WORD = { good: "mostly good", bad: "mostly bad", mixed: "mixed", none: "no clear lean" };
  const headline = (item) => (
    <li key={item.id}>
      <button type="button" className="bs-link" onClick={() => onSource?.(item)}>
        {item.headline}
      </button>
      <small>
        {item.kind === "social"
          ? platformName(item.platform)
          : item.source || item.publisher || "News"}{" "}
        · {dayLabel(item.published_at)}
      </small>
    </li>
  );
  const group = (label, mood, list, limit = 3) =>
    list.length > 0 && (
      <div className="bs-group">
        <h5>
          <span className={`bs-dot mood-${mood}`} aria-hidden="true"></span>
          {label} <span className="bs-count">{list.length}</span>
        </h5>
        <ul className="bs-headlines">{list.slice(0, limit).map(headline)}</ul>
      </div>
    );

  return (
    <div className="beginner-summary signals">
      {practice && (
        <p className="bs-practice">
          <strong>Practice company, not real.</strong> Sample news and posts
          that show how Fledge works.
        </p>
      )}
      <section className="bs-price-row" aria-label="Share price">
        {price ? (
          <>
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
        {price?.move && (
          <p className="bs-price-note">
            Prices move for many reasons. The news below may not explain
            today’s move.
          </p>
        )}
      </section>

      <section aria-labelledby="bs-lights-title">
        <h4 id="bs-lights-title" className="sr-only">
          {name} at a glance
        </h4>
        <ul className="bs-lights">
          {lights.map((light) => (
            <li key={light.key}>
              <a
                className={`bs-light mood-${light.mood}`}
                href={`#bs-${light.key}`}
                aria-label={`${light.title}: ${light.status} (${MOOD_WORD[light.mood]}). Show details.`}
              >
                <span className="bs-shape" aria-hidden="true">
                  {SHAPE[light.mood]}
                </span>
                <span className="bs-light-title">{light.title}</span>
                <strong>{light.status}</strong>
              </a>
            </li>
          ))}
        </ul>
        <p className="bs-key">
          {rated && "Sorted by AI from saved headlines and posts; tap any item to check it. "}
          ▲ mostly good · ▼ mostly bad · ◆ mixed. This shows the tone of what’s
          being said, not whether to buy or sell.
        </p>
        {pointer && <p className="bs-pointer">{pointer}</p>}
      </section>

      <section className="bs-card" id="bs-news" tabIndex={-1} aria-labelledby="bs-news-title">
        <h4 id="bs-news-title">News: what happened</h4>
        <p className="bs-meaning">{newsMeaning(newsGroups)}</p>
        {onRate && !reading && (newsGroups.unrated.length > 0 || postGroups.unrated.length > 0) && (
          <div className="bs-rate">
            <button type="button" className="primary" onClick={onRate} disabled={rating}>
              {rating ? "Rating… this takes a minute or two" : "Rate with AI"}
            </button>
            <small>Fledge reads the news and posts and marks each good, bad or mixed.</small>
          </div>
        )}
        {group("Good news", "good", newsGroups.good)}
        {group("Bad news", "bad", newsGroups.bad)}
        {group("Mixed: good and bad in one story", "mixed", newsGroups.mixed)}
        {newsGroups.neutral.length > 0 && (
          <details className="bs-group">
            <summary>
              Neutral, neither good nor bad{" "}
              <span className="bs-count">{newsGroups.neutral.length}</span>
            </summary>
            <ul className="bs-headlines">{newsGroups.neutral.slice(0, 5).map(headline)}</ul>
          </details>
        )}
        {!reading && group("Not rated yet", "none", newsGroups.unrated, 5)}
        {!news.length && onUpdate && (
          <button type="button" className="bs-link inline" onClick={onUpdate}>
            Get the latest news
          </button>
        )}
        <button type="button" className="bs-more" onClick={() => onView?.("evidence")}>
          All news & posts →
        </button>
      </section>

      <section className="bs-card" id="bs-people" tabIndex={-1} aria-labelledby="bs-people-title">
        <h4 id="bs-people-title">What people online are saying</h4>
        <p className="bs-meaning">{peopleMeaning(postGroups)}</p>
        {social.length > 0 && (
          <p className="bs-muted bs-platforms">
            {social
              .map((s) => `${s.platform}: ${plainTone(s.tone).toLowerCase()}`)
              .join(" · ")}
          </p>
        )}
        {group("Upbeat posts (opinions)", "none", postGroups.good)}
        {group("Worried posts (opinions)", "none", postGroups.bad)}
        {group("Mixed posts: good and bad", "none", postGroups.mixed)}
        {!reading && group("Not rated yet", "none", postGroups.unrated)}
      </section>

      <section className="bs-card" id="bs-world" tabIndex={-1} aria-labelledby="bs-world-title">
        <h4 id="bs-world-title">World news that may matter</h4>
        {links.length ? (
          <ul className="bs-world">
            {links.map(({ article, link }) => (
              <li key={article.id}>
                <span className={`bs-effect-tag effect-${link.effect}`}>
                  {EFFECT_WORDS[link.effect]}
                </span>
                <a href={article.url} target="_blank" rel="noopener noreferrer">
                  {article.headline}
                </a>
                <small className="bs-meta">
                  {article.publisher} · {dayLabel(article.published_at)}
                </small>
                <p>{link.reason}</p>
              </li>
            ))}
          </ul>
        ) : (
          <p className="bs-muted">{worldState.reason}</p>
        )}
        {links.length > 0 && (
          <p className="bs-caveat">
            These are possibilities to think about, not predictions or tips.
          </p>
        )}
        <button type="button" className="bs-more" onClick={onWorld}>
          World news →
        </button>
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

      {mode === "explain" ? (
        <p className="bs-note">
          Want financials, charts and comparisons?{" "}
          <button
            type="button"
            className="bs-link inline"
            onClick={() => setDetailMode?.("data")}
          >
            Turn on Pro tools
          </button>{" "}
          (you can switch back in Account).
        </p>
      ) : (
        <p className="bs-note">
          The other tabs have the financials, charts and comparisons.
        </p>
      )}
    </div>
  );
}
