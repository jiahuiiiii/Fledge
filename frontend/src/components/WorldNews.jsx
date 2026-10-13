import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import { formatTimestamp } from "../lib/dateTime";
import {
  EFFECT_LABELS,
  checkBlocker,
  filterArticles,
  themeCounts,
} from "../lib/worldNews";
import "./WorldNews.css";

// World view: major market headlines (central banks, conflicts, trade, energy)
// and which watchlist companies they might touch. Possibilities to read, not advice.
export default function WorldNews({ active, onOpenCompany }) {
  const [page, setPage] = useState(null);
  const [filter, setFilter] = useState("all");
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");
  const autoRefreshed = useRef(false);

  const load = useCallback(() => {
    return api
      .worldNews()
      .then((result) => {
        setPage(result);
        return result;
      })
      .catch((failure) => {
        setMessage(failure.message);
        return null;
      });
  }, []);

  const refresh = useCallback(async () => {
    setBusy("refresh");
    setMessage("");
    try {
      setPage(await api.refreshWorldNews());
    } catch (failure) {
      setMessage(failure.message);
    } finally {
      setBusy("");
    }
  }, []);

  useEffect(() => {
    if (!active) return;
    load().then((result) => {
      // Fetch fresh headlines once per visit when the saved ones are old.
      if (
        result?.configured &&
        result.stale &&
        result.can_refresh &&
        !autoRefreshed.current
      ) {
        autoRefreshed.current = true;
        refresh();
      }
    });
  }, [active, load, refresh]);

  async function check() {
    setBusy("check");
    setMessage("");
    try {
      setPage(await api.checkWorldNews());
    } catch (failure) {
      setMessage(failure.message);
    } finally {
      setBusy("");
    }
  }

  const companies = Object.fromEntries(
    (page?.companies || []).map((c) => [c.id, c]),
  );
  const themes = Object.fromEntries(
    (page?.themes || []).map((t) => [t.id, t.label]),
  );
  const articles = filterArticles(page?.articles, filter);
  const blocker = checkBlocker(page);
  const mineCount = filterArticles(page?.articles, "mine").length;

  return (
    <section className="world-news" aria-labelledby="world-news-title">
      <header className="world-news-head">
        <div>
          <span className="section-label">WORLD NEWS</span>
          <h2 id="world-news-title">What’s happening in the world</h2>
          <p>
            Rate decisions, conflicts, trade and oil: the big headlines, and
            which of your companies they might touch.
          </p>
        </div>
        <div className="world-news-actions">
          <button
            type="button"
            onClick={refresh}
            disabled={!!busy || !page?.configured || !page?.can_refresh}
            title={
              page && !page.can_refresh
                ? "World news refreshes are ten minutes apart."
                : undefined
            }
          >
            {busy === "refresh" ? "Refreshing…" : "Refresh"}
          </button>
          <button
            type="button"
            className="primary"
            onClick={check}
            disabled={!!busy || !!blocker}
            aria-describedby={blocker ? "world-check-blocker" : undefined}
          >
            {busy === "check" ? "Checking…" : "Check against my watchlist"}
          </button>
        </div>
      </header>
      <p className="world-news-status fine">
        {page?.checked_at
          ? `Headlines checked ${formatTimestamp(page.checked_at)} · Finnhub market news, last 3 days.`
          : "No world headlines saved yet."}
        {blocker && page && (
          <span id="world-check-blocker"> {blocker}</span>
        )}
        {page?.check && (
          <span>
            {" "}
            Last watchlist check {formatTimestamp(page.check.checked_at)}.
          </span>
        )}
      </p>
      {page && !page.configured && (
        <p className="warning" role="status">
          World news needs a Finnhub key. Add <code>FINNHUB_API_KEY</code> and{" "}
          <code>THESIS_LIVE_DATA_ENABLED=true</code> to your private .env file,
          then restart Fledge.
        </p>
      )}
      {page?.error && (
        <p className="warning" role="status">
          The last refresh failed: {page.error} Earlier headlines are kept.
        </p>
      )}
      {message && (
        <p className="warning" role="alert">
          {message}
        </p>
      )}

      {page && (
        <div
          className="world-news-filters"
          role="group"
          aria-label="Filter headlines"
        >
          {[
            { id: "all", label: "All", count: page.articles.length },
            { id: "mine", label: "My companies", count: mineCount },
            ...themeCounts(page.articles, page.themes),
          ].map((option) => (
            <button
              key={option.id}
              type="button"
              aria-pressed={filter === option.id}
              className={filter === option.id ? "active" : ""}
              onClick={() => setFilter(option.id)}
            >
              {option.label} <span>{option.count}</span>
            </button>
          ))}
        </div>
      )}

      {!page ? (
        <p className="fine">Loading world news…</p>
      ) : articles.length === 0 ? (
        <p className="world-news-empty">
          {filter === "all"
            ? "No headlines from the last three days yet."
            : filter === "mine"
              ? "No recent headline names your companies. Run the watchlist check to look for indirect effects, like rates or tariffs."
              : "No recent headlines on this theme."}
        </p>
      ) : (
        <ul className="world-news-list">
          {articles.map((article) => (
            <li key={article.id} className="world-news-item">
              <div className="world-news-meta">
                {article.themes.map((id) => (
                  <span key={id} className={`world-theme theme-${id}`}>
                    {themes[id] || id}
                  </span>
                ))}
                <span className="fine">
                  {article.publisher} ·{" "}
                  {formatTimestamp(article.published_at)}
                </span>
              </div>
              <h3>
                <a href={article.url} target="_blank" rel="noopener noreferrer">
                  {article.headline}
                  <span className="sr-only"> (opens the original article)</span>
                </a>
              </h3>
              {article.summary && (
                <p className="world-news-summary">{article.summary}</p>
              )}
              {article.mentions.length > 0 && (
                <p className="world-news-mentions">
                  Names{" "}
                  {article.mentions.map((id) => (
                    <button
                      key={id}
                      type="button"
                      className="text-button"
                      onClick={() => onOpenCompany?.(id)}
                    >
                      {companies[id]?.symbol || "a watchlist company"}
                    </button>
                  ))}
                </p>
              )}
              {article.links.length > 0 && (
                <ul className="world-news-links" aria-label="Possible effects">
                  {article.links.map((link) => (
                    <li key={link.company_id} className={`effect-${link.effect}`}>
                      <strong>
                        {link.symbol} · {EFFECT_LABELS[link.effect]}
                      </strong>{" "}
                      {link.reason}
                      <q>{link.quote}</q>
                    </li>
                  ))}
                </ul>
              )}
            </li>
          ))}
        </ul>
      )}
      <p className="fine world-news-note">
        Theme tags are keyword-based. AI-suggested effects are possibilities to
        read and check, quoted from the headline; they are not predictions or
        advice to buy or sell.
      </p>
    </section>
  );
}
