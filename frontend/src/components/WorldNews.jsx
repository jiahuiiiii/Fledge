import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import { formatTimestamp } from "../lib/dateTime";
import {
  EFFECT_LABELS,
  checkBlocker,
  filterArticles,
  themeCounts,
} from "../lib/worldNews";
import { useProfile } from "../lib/profile";
import "./WorldNews.css";
import {
  Badge,
  Button,
  Card,
  Disclosure,
  EmptyState,
  FilterGroup,
  GlobeIcon,
  MetaRow,
  RefreshIcon,
  SectionHeader,
  StoryCard,
} from "./ui";

// World view: major market headlines (central banks, conflicts, trade, energy)
// and which watchlist companies they might touch. Possibilities to read, not advice.
export default function WorldNews({ active, onOpenCompany }) {
  // Beginners get the headlines, not the machinery: one short status line.
  const beginner = useProfile().mode === "explain";
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
    <section
      className="world-news reading-page"
      aria-labelledby="world-news-title"
    >
      {/* Everything above the headlines stays in view while they scroll
          (not on phones, where the screen is too short to spare). */}
      <div className="world-news-head">
        <SectionHeader
          level="page"
          as="h2"
          id="world-news-title"
          icon={<GlobeIcon />}
          title="World news"
          description="Rates, trade, energy and events that may affect your companies."
        />
        <div className="reading-page-actions">
          <Button
            icon={<RefreshIcon />}
            onClick={refresh}
            disabled={!!busy || !page?.configured || !page?.can_refresh}
            title={
              page && !page.can_refresh
                ? "World news refreshes are ten minutes apart."
                : undefined
            }
          >
            {busy === "refresh" ? "Refreshing…" : "Refresh"}
          </Button>
          {!(beginner && blocker) && (
            <Button
              variant="plain"
              onClick={check}
              disabled={!!busy || !!blocker}
              aria-describedby={blocker ? "world-check-blocker" : undefined}
            >
              {busy === "check" ? "Checking…" : "Check against my watchlist"}
            </Button>
          )}
        </div>
        {page && (
          <MetaRow className="world-news-status">
            {page.checked_at && (
              <span>
                Finnhub · past 3 days · updated{" "}
                {formatTimestamp(page.checked_at)}
              </span>
            )}
            {page.check && !beginner && (
              <span>
                Watchlist checked {formatTimestamp(page.check.checked_at)}
              </span>
            )}
          </MetaRow>
        )}
        {!beginner && blocker && page && (
          <p id="world-check-blocker" className="reading-page-note">
            {blocker.startsWith("needs AI")
              ? "Watchlist checks are unavailable while AI is off."
              : blocker}
          </p>
        )}
        {page && !page.configured && page.articles.length > 0 && (
          <Card variant="inset" role="status">
            Showing saved headlines. New headlines are unavailable.
          </Card>
        )}
        {page?.error && (
          <Card variant="inset" role="status">
            The last refresh failed: {page.error} Earlier headlines are kept.
          </Card>
        )}
        {message && (
          <Card variant="inset" role="alert">
            {message}
          </Card>
        )}
        {page?.articles.length > 0 && (
          <FilterGroup
            className="world-news-filters"
            label="Filter headlines"
            value={filter}
            onValueChange={setFilter}
            options={[
              { value: "all", label: "All", count: page.articles.length },
              { value: "mine", label: "About my companies", count: mineCount },
              ...themeCounts(page.articles, page.themes).map((option) => ({
                ...option,
                value: option.id,
              })),
            ]}
          />
        )}
      </div>
      {!page ? (
        message ? (
          <EmptyState
            title="World news unavailable"
            description="Try loading the saved headlines again."
            actions={<Button onClick={load}>Try again</Button>}
          />
        ) : (
          <p role="status" className="reading-page-note">
            Loading world news…
          </p>
        )
      ) : articles.length === 0 ? (
        <EmptyState
          icon={<GlobeIcon />}
          title={
            filter === "all"
              ? "No world headlines yet"
              : "No headlines in this view"
          }
          description={
            filter === "all"
              ? page.configured
                ? "No headlines from the last three days yet."
                : "World headlines aren’t connected yet."
              : filter === "mine"
                ? "No recent headline names your companies. A watchlist check can look for indirect effects."
                : "No recent headlines on this theme."
          }
          actions={
            filter !== "all" ? (
              <Button variant="tertiary" onClick={() => setFilter("all")}>
                Show all headlines
              </Button>
            ) : undefined
          }
        />
      ) : (
        <ul className="world-news-list">
          {articles.map((article) => (
            <li key={article.id}>
              <StoryCard
                className="world-news-item"
                title={article.headline}
                href={article.url}
                tags={
                  article.themes.length > 0 &&
                  article.themes.map((id) => (
                    <Badge key={id}>{themes[id] || id}</Badge>
                  ))
                }
                meta={
                  <>
                    <span>{article.publisher}</span>
                    <time dateTime={article.published_at}>
                      {formatTimestamp(article.published_at)}
                    </time>
                  </>
                }
              >
                {article.summary && (
                  <p className="world-news-summary">{article.summary}</p>
                )}
                {article.mentions.length > 0 && (
                  <div className="world-news-mentions">
                    <span>Mentions</span>
                    {article.mentions.map((id) => (
                      <Button
                        key={id}
                        variant="tertiary"
                        size="sm"
                        onClick={() => onOpenCompany?.(id)}
                      >
                        {companies[id]?.symbol || "a watchlist company"}
                      </Button>
                    ))}
                  </div>
                )}
                {article.links.length > 0 && (
                  <div className="world-news-effects">
                    <span className="reading-page-note">
                      Possible effects · AI interpretation
                    </span>
                    <ul
                      className="world-news-links"
                      aria-label="Possible effects"
                    >
                      {article.links.map((link) => (
                        <Card as="li" variant="inset" key={link.company_id}>
                          <MetaRow>
                            <strong>{link.symbol}</strong>
                            <Badge
                              shape={false}
                              tone={
                                {
                                  could_help: "positive",
                                  could_hurt: "negative",
                                  mixed_or_unclear: "mixed",
                                }[link.effect]
                              }
                            >
                              {EFFECT_LABELS[link.effect]}
                            </Badge>
                          </MetaRow>
                          <p>{link.reason}</p>
                        </Card>
                      ))}
                    </ul>
                  </div>
                )}
              </StoryCard>
            </li>
          ))}
        </ul>
      )}
      <Disclosure
        variant="flush"
        title="About these headlines"
        className="world-news-note"
      >
        <p>
          Topic tags use headline keywords. Possible effects are AI
          interpretations of the headline, not predictions or advice.
        </p>
      </Disclosure>
    </section>
  );
}
