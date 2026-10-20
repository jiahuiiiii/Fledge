import { useEffect, useState } from "react";
import { api } from "../api/client";
import { formatTimestamp } from "../lib/dateTime";
import { pctText, barWidth, toneLine } from "../lib/portfolioRead";
import "./BeginnerSummary.css";
import "./PortfolioRead.css";

// "Your list today": the whole watchlist read together, not one company.
// The lights and bars come from saved prices, news tone and the account's own
// world-news check. The written explanation is optional (one AI request) and
// every sentence cites the saved headline it relies on.
const SHAPE = { good: "▲", bad: "▼", mixed: "◆", none: "●" };

function Bars({ ids, byId, scale, onOpen }) {
  return (
    <ul className="pr-bars">
      {ids.map((id) => {
        const c = byId[id];
        if (!c) return null;
        const move = c.quote?.change_percent;
        return (
          <li key={id}>
            <button type="button" onClick={() => onOpen?.(id)}>
              <strong>{c.symbol}</strong>
              <span className="pr-track" aria-hidden="true">
                {move != null && (
                  <span
                    className={`pr-bar ${move < 0 ? "down" : "up"}`}
                    style={{ width: barWidth(move, scale) }}
                  />
                )}
              </span>
              <span className={`pr-pct ${move < 0 ? "down" : move > 0 ? "up" : ""}`}>
                {pctText(move)}
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}

export default function PortfolioRead({ onOpenCompany }) {
  const [page, setPage] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    const load = () =>
      api
        .portfolio()
        .then((value) => active && setPage(value))
        .catch(() => active && setPage(null));
    load();
    addEventListener("fledge:home-changed", load);
    // Prices on the cards refresh every minute; keep this summary in step.
    const timer = setInterval(() => {
      if (document.visibilityState === "visible") load();
    }, 60_000);
    return () => {
      active = false;
      clearInterval(timer);
      removeEventListener("fledge:home-changed", load);
    };
  }, []);
  // A "list" needs at least two companies; one company has its own Summary.
  if (!page || page.companies.length < 2) return null;

  const byId = Object.fromEntries(page.companies.map((c) => [c.id, c]));
  const scale = Math.max(
    1,
    ...page.companies.map((c) => Math.abs(c.quote?.change_percent || 0)),
  );
  const e = page.explanation;
  const lights = [
    ["TODAY", page.move],
    ["HOW SPREAD OUT", page.spread],
    ["WORLD", page.world],
  ];
  async function explain() {
    setBusy(true);
    setError("");
    try {
      setPage(await api.explainPortfolio());
    } catch (failure) {
      setError(failure.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="portfolio-read" aria-labelledby="pr-title">
      <span className="section-label">YOUR LIST TODAY</span>
      <h2 id="pr-title">How your {page.companies.length} companies moved</h2>
      <p className="pr-sub">
        {page.prices_from
          ? `Prices from ${formatTimestamp(page.prices_from)}`
          : "No share prices saved yet"}
        {page.prices_stale && " · these prices are a few days old"}
      </p>

      <ul className="bs-lights pr-lights">
        {lights.map(([title, light]) => (
          <li key={title}>
            <div className={`bs-light mood-${light.mood}`}>
              <span className="bs-shape" aria-hidden="true">
                {SHAPE[light.mood]}
              </span>
              <span className="bs-light-title">{title}</span>
              <strong>{light.text}</strong>
            </div>
          </li>
        ))}
      </ul>

      {e ? (
        <>
          {(e.headline || e.drivers.length > 0) && (
            <section className="bs-card">
              <h4>What happened</h4>
              {e.headline && <p className="bs-meaning">{e.headline}</p>}
              <ul className="pr-drivers">
                {e.drivers.map((d, i) => (
                  <li key={i}>
                    {d.text}
                    <small className="bs-meta">
                      {d.sources.map((s, j) => (
                        <span key={s.id}>
                          {j > 0 && " · "}
                          {s.url ? (
                            <a href={s.url} target="_blank" rel="noreferrer">
                              {s.publisher || "Source"}
                            </a>
                          ) : (
                            s.publisher || "Source"
                          )}
                        </span>
                      ))}
                    </small>
                  </li>
                ))}
              </ul>
            </section>
          )}
          {e.groups.length > 0 && (
            <section className="bs-card">
              <h4>Why some moved more</h4>
              {e.groups.map((g) => (
                <div className="pr-group" key={g.label}>
                  <span className="pr-group-label">{g.label}</span>
                  <p className="pr-note">{g.note}</p>
                  <Bars ids={g.company_ids} byId={byId} scale={scale} onOpen={onOpenCompany} />
                </div>
              ))}
            </section>
          )}
          {e.takeaway && (
            <section className="bs-card pr-takeaway">
              <h4>For your list</h4>
              <p>{e.takeaway}</p>
            </section>
          )}
          <p className="bs-note">
            Written by AI from your saved headlines on{" "}
            {formatTimestamp(e.created_at)}; tap a source to check it.
          </p>
        </>
      ) : (
        <>
          <section className="bs-card">
            <h4>How each moved</h4>
            <p className="bs-meaning">{toneLine(page.news_tone)}</p>
            {page.groups.map((g) => (
              <div className="pr-group" key={g.label}>
                <span className="pr-group-label">{g.label}</span>
                <Bars ids={g.company_ids} byId={byId} scale={scale} onOpen={onOpenCompany} />
              </div>
            ))}
          </section>
          {page.world.events?.length > 0 && (
            <section className="bs-card">
              <h4>World news touching your list</h4>
              <ul className="pr-drivers">
                {page.world.events.map((ev) => (
                  <li key={ev.article_id}>
                    <a href={ev.url} target="_blank" rel="noreferrer">
                      {ev.headline}
                    </a>
                    <small className="bs-meta">
                      {ev.publisher} · {ev.companies.length} of your companies
                    </small>
                  </li>
                ))}
              </ul>
            </section>
          )}
          <div className="pr-explain">
            {page.ai.available ? (
              <button
                type="button"
                className="primary"
                onClick={explain}
                disabled={busy}
              >
                {busy ? "Reading your list…" : "Explain my list"}
              </button>
            ) : (
              <p className="bs-note">
                A written explanation of your list needs AI, which isn’t switched
                on in this copy of Fledge.
              </p>
            )}
            {error && (
              <p className="error" role="alert">
                {error}
              </p>
            )}
          </div>
        </>
      )}
      <p className="bs-note">
        This shows what moved and what’s being said, not whether to buy or sell.
      </p>
    </section>
  );
}
