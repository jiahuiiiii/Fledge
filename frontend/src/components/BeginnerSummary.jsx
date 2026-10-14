import { useEffect, useState } from "react";
import { api } from "../api/client";
import { useProfile } from "../lib/profile";
import { formatTimestamp } from "../lib/dateTime";
import { companyName } from "../lib/companyIdentity";
import { snapshot } from "../lib/companySnapshot";
import { overviewNews } from "../lib/overviewSections";
import { sourceCoverage } from "../lib/sourceCoverage";
import {
  itemTone,
  oneLine,
  plainTone,
  platformName,
  priceLine,
  socialTones,
  toneMood,
  worldForCompany,
} from "../lib/beginnerSummary";
import "./BeginnerSummary.css";

const EFFECT_WORDS = {
  could_help: "Could help",
  could_hurt: "Could hurt",
  mixed_or_unclear: "Could go either way",
};
const when = (value) => formatTimestamp(value, { fallback: "date unknown" });

// One page for beginners: the price, what the news and people online are
// saying, world events that may matter, and the user's own view. No charts.
// Everything is a saved reading reworded; Fledge never says buy or sell.
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
  const { sentences } = snapshot(data);
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
  const { linked, bigPicture } = worldForCompany(world, instrumentId);
  const summaryLine = oneLine({
    newsTone: newsTone?.analysed ? newsTone.tone : null,
    newsCount: news.length,
    social,
    links: linked.map((x) => x.link).filter(Boolean),
  });

  return (
    <div className="beginner-summary">
      <section className="bs-card bs-hero" aria-label="Share price">
        <div>
          <span className="section-label">SHARE PRICE</span>
          <p className="bs-muted">
            {name}
            {data.instrument.sector ? ` · ${data.instrument.sector}` : ""}
          </p>
        </div>
        {price ? (
          <div className={`bs-price mood-${price.mood}`}>
            <strong>{price.price}</strong>
            {price.move && <span>{price.move}</span>}
          </div>
        ) : (
          <p className="bs-muted">No share price saved yet.</p>
        )}
        <p className="bs-oneline">
          <span className="section-label">IN SHORT</span>
          {summaryLine}
        </p>
      </section>

      {sentences.length > 0 && (
        <section className="bs-card" aria-labelledby="bs-basics">
          <h4 id="bs-basics">The basics</h4>
          <ul className="bs-list">
            {sentences.map((sentence) => (
              <li key={sentence}>{sentence}</li>
            ))}
          </ul>
        </section>
      )}

      <section className="bs-card" aria-labelledby="bs-news">
        <div className="bs-head">
          <h4 id="bs-news">What the news says</h4>
          <span className={`bs-tone mood-${toneMood(newsTone?.tone)}`}>
            {newsTone?.analysed ? plainTone(newsTone.tone) : "Not read yet"}
          </span>
        </div>
        {news.length ? (
          <ul className="bs-headlines">
            {news.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  className="bs-link"
                  onClick={() => onSource?.(item)}
                >
                  {item.headline}
                </button>
                <small>
                  {item.source || item.publisher || "News"} ·{" "}
                  {when(item.published_at)}
                  {itemTone(item.tone) && (
                    <span className={`bs-chip tone-${item.tone}`}>
                      {itemTone(item.tone)}
                    </span>
                  )}
                </small>
              </li>
            ))}
          </ul>
        ) : (
          <p className="bs-muted">
            No company news saved yet.{" "}
            {onUpdate && (
              <button type="button" className="bs-link" onClick={onUpdate}>
                Get the latest news
              </button>
            )}
          </p>
        )}
      </section>

      <section className="bs-card" aria-labelledby="bs-social">
        <div className="bs-head">
          <h4 id="bs-social">What people are saying online</h4>
        </div>
        {social.length ? (
          <ul className="bs-tones">
            {social.map((s) => (
              <li key={s.platform}>
                <span>{s.platform}</span>
                <span className={`bs-tone mood-${toneMood(s.tone)}`}>
                  {plainTone(s.tone)}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="bs-muted">
            No reading of Reddit, Hacker News or X yet.
          </p>
        )}
        {posts.length > 0 && (
          <ul className="bs-headlines">
            {posts.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  className="bs-link"
                  onClick={() => onSource?.(item)}
                >
                  {item.headline}
                </button>
                <small>
                  {platformName(item.platform)} · {when(item.published_at)}
                  {itemTone(item.tone) && (
                    <span className={`bs-chip tone-${item.tone}`}>
                      {itemTone(item.tone)}
                    </span>
                  )}
                </small>
              </li>
            ))}
          </ul>
        )}
        <button type="button" className="bs-more" onClick={() => onView?.("evidence")}>
          Read all news & posts →
        </button>
      </section>

      <section className="bs-card" aria-labelledby="bs-world">
        <div className="bs-head">
          <h4 id="bs-world">World news that may matter</h4>
        </div>
        {!world ? (
          <p className="bs-muted">Loading world news…</p>
        ) : linked.length ? (
          <ul className="bs-headlines">
            {linked.map(({ article, link }) => (
              <li key={article.id}>
                <a href={article.url} target="_blank" rel="noopener noreferrer">
                  {article.headline}
                </a>
                {link ? (
                  <p className={`bs-effect effect-${link.effect}`}>
                    <strong>{EFFECT_WORDS[link.effect] || "Possible effect"}:</strong>{" "}
                    {link.reason}
                  </p>
                ) : (
                  <p className="bs-muted">This headline names {name}.</p>
                )}
              </li>
            ))}
          </ul>
        ) : bigPicture.length ? (
          <>
            <p className="bs-muted">
              Nothing yet ties world news to {name}. The big picture:
            </p>
            <ul className="bs-headlines">
              {bigPicture.map((article) => (
                <li key={article.id}>
                  <a href={article.url} target="_blank" rel="noopener noreferrer">
                    {article.headline}
                  </a>
                  <small>
                    {article.publisher} · {when(article.published_at)}
                  </small>
                </li>
              ))}
            </ul>
          </>
        ) : (
          <p className="bs-muted">No recent world headlines saved yet.</p>
        )}
        {linked.some((x) => x.link) && (
          <p className="bs-caveat">A possibility to think about, not a prediction or a tip.</p>
        )}
        <button type="button" className="bs-more" onClick={onWorld}>
          Open World news →
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

      <p className="bs-note">
        This page rewords saved news and posts; it is not advice to buy or
        sell.
        {mode === "explain"
          ? " Switch to Pro for financials, charts and comparisons."
          : " The other tabs have the financials, charts and comparisons."}
      </p>
    </div>
  );
}
