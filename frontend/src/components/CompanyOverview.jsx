import { formatTimestamp } from "../lib/dateTime";
import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import { readableLoad } from "../lib/loading";
import LoadingSkeleton from "./LoadingSkeleton";
import CompanyAvatar from "./CompanyAvatar";
import PriceChange from "./PriceChange";
import { companyName, companyMatches } from "../lib/companyIdentity";
import {
  day,
  money,
  percent,
  trailing,
  newsTone,
} from "../lib/companySnapshot";
import {
  extendedLine,
  latestPriceQuote,
  quoteMovement,
  sessionLabel,
} from "../lib/priceRefresh";
import ExtendedPrice from "./ExtendedPrice";
import { freshPrice, LIVE_PRICE_MS } from "../lib/livePrice";
import {
  Badge,
  Button,
  Card,
  ChevronRightIcon,
  GridIcon,
  SectionHeader,
} from "./ui";
import "./CompanyOverview.css";
const stamp = (value) =>
  formatTimestamp(value, { fallback: "Date unavailable" });

import { useProfile } from "../lib/profile";

// Newcomers were puzzled by companies they never added. Say what they are.
function practiceNote(catalogue) {
  const practice = catalogue.filter((c) => c.mode === "recorded");
  const lead = "Choose a company to see what’s happening with it.";
  if (!practice.length) return lead;
  const names = practice.map((c) => c.name || c.symbol);
  const list =
    names.length > 1
      ? `${names.slice(0, -1).join(", ")} and ${names.at(-1)} are practice companies`
      : `${names[0]} is a practice company`;
  return `${lead} ${list} (not real) so you can see how Fledge works.`;
}

export default function CompanyOverview({ catalogue, onOpen }) {
  const [readings, setReadings] = useState({});
  // Beginner mode keeps each card to the price and a plain news line.
  const beginner = useProfile().mode === "explain";
  const [refresh, setRefresh] = useState(0);
  const [query, setQuery] = useState("");
  const current = useRef({ catalogue });
  current.current = { catalogue };
  const membership = catalogue.map((company) => company.id).join(",");
  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    const { catalogue: companies } = current.current;
    const { signal } = controller;
    setReadings({});
    // Staged, local, account-scoped reads; browsing does not refresh suppliers.
    // 1. One light read gives every card its saved quote, so cards appear at once.
    // 2. Then each card's news tone, filing figures (Pro only) and price history,
    //    three companies at a time.
    // A server that predates the light reads (404, no JSON, no answer) gets the
    // earlier full workspace read per card, so a new page works before a restart.
    const load = async () => {
      const quotes = await api.homeCards({ signal }).catch(() => null);
      if (!active) return;
      const light = Array.isArray(quotes);
      if (light) {
        const quoteFor = new Map(quotes.map((row) => [row.id, row]));
        setReadings(
          Object.fromEntries(
            companies.map((company) => [
              company.id,
              {
                data: {
                  instrument: { id: company.id },
                  ...quoteFor.get(company.id),
                },
                history: null,
                pending: true,
                error: false,
              },
            ]),
          ),
        );
      }
      const read = light
        ? (company) =>
            api
              .homeCard(company.id, { figures: !beginner, signal })
              .then((card) => (card?.id === company.id ? card : null))
        : (company) =>
            api
              .workspace(company.id, { includeFinancials: !beginner, signal })
              .then((data) =>
                data?.instrument?.id === company.id ? data : null,
              );
      let index = 0;
      const worker = async () => {
        while (active && index < companies.length) {
          const company = companies[index++];
          const [card, prices] = await Promise.allSettled([
            read(company),
            company.mode === "sec"
              ? api.priceHistory(company.id, { signal })
              : Promise.resolve(null),
          ]);
          if (!active) return;
          const detail = card.status === "fulfilled" ? card.value : null;
          const history =
            prices.status === "fulfilled" &&
            prices.value?.symbol === company.symbol
              ? prices.value
              : null;
          setReadings((previous) => ({
            ...previous,
            [company.id]: {
              data: { ...previous[company.id]?.data, ...detail },
              history,
              pending: false,
              error: !detail,
              priceError: prices.status === "rejected",
            },
          }));
        }
      };
      await Promise.all(
        Array.from({ length: Math.min(3, companies.length) }, worker),
      );
    };
    void load();
    return () => {
      active = false;
      controller.abort();
    };
  }, [membership, refresh, beginner]);
  // Home prices refresh on their own while the page is visible.
  useEffect(() => {
    let stopped = false;
    const tick = async () => {
      if (document.visibilityState !== "visible") return;
      for (const company of current.current.catalogue) {
        if (stopped) return;
        if (company.mode !== "sec") continue;
        try {
          const history = await freshPrice(company.id);
          if (stopped || history?.symbol !== company.symbol) continue;
          setReadings((previous) =>
            previous[company.id]
              ? {
                  ...previous,
                  [company.id]: { ...previous[company.id], history },
                }
              : previous,
          );
        } catch {
          /* Keep the saved price on screen. */
        }
      }
      if (!stopped) dispatchEvent(new Event("fledge:prices-updated"));
    };
    const timer = setInterval(tick, LIVE_PRICE_MS);
    return () => {
      stopped = true;
      clearInterval(timer);
    };
  }, [membership]);
  const loading = catalogue.some(
    (company) => !readings[company.id] || readings[company.id].pending,
  );
  // Your own companies first, then practice companies (the worked example,
  // Northstar, before the others), so newcomers see one that has data.
  const rank = (c) =>
    c.mode !== "recorded"
      ? 0
      : c.id === "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
        ? 1
        : 2;
  const companies = catalogue
    .filter((company) => companyMatches(company, query))
    .map((company, index) => [company, index])
    .sort((a, b) => rank(a[0]) - rank(b[0]) || a[1] - b[1])
    .map(([company]) => company);
  return (
    <section
      className="collection-page company-overview"
      aria-label="All company workspaces"
    >
      <SectionHeader
        level="page"
        className="company-overview-heading"
        icon={<GridIcon />}
        eyebrow={beginner ? "Your companies" : "Your research"}
        title={
          <>
            {beginner ? "My companies" : "All companies"}{" "}
            <Badge>{catalogue.length}</Badge>
          </>
        }
        description={
          beginner
            ? practiceNote(catalogue)
            : "Saved prices and financials, together. Open a company to explore its evidence."
        }
        actions={
          // Beginner mode keeps the home to the cards themselves.
          !beginner && (
            <Button
              size="sm"
              onClick={() => setRefresh((value) => value + 1)}
              disabled={loading}
            >
              Reload saved data
            </Button>
          )
        }
      />
      <label className="company-overview-search">
        <span>Find a company</span>
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Name or ticker"
        />
      </label>
      <div className="company-overview-grid" aria-busy={loading}>
        {companies.map((company) => {
          const reading = readings[company.id],
            data = reading?.data;
          const quote =
            latestPriceQuote(data?.market, reading?.history) ||
            data?.market?.quote?.quote;
          const yahoo = !!latestPriceQuote(data?.market, reading?.history);
          const price =
            quote?.price != null && Number.isFinite(Number(quote.price))
              ? Number(quote.price).toFixed(2)
              : null;
          const revenue = trailing(data?.financial_depth, "revenue");
          const margin = trailing(data?.financial_depth, "operating_margin");
          const tone = newsTone(data?.sentiment);
          // The quote is shown first; tone and figures follow per card.
          const waiting = !!reading?.pending;
          return (
            <Card
              as="button"
              interactive
              className="company-overview-card"
              key={company.id}
              data-company={company.id}
              aria-label={`Open ${company.symbol} · ${companyName(company)}`}
              onClick={() => onOpen(company.id, "workspace")}
            >
              <span className="company-overview-identity">
                <CompanyAvatar company={company} />
                <span>
                  <strong title={company.name}>{companyName(company)}</strong>
                  <span className="company-overview-symbol">
                    {company.symbol}
                    {company.mode === "recorded" && (
                      <Badge>Fictional sample</Badge>
                    )}
                  </span>
                </span>
                <span className="company-overview-arrow" aria-hidden="true">
                  <ChevronRightIcon />
                </span>
              </span>
              {!reading ? (
                <span className="company-overview-loading" role="status">
                  Loading saved figures…
                </span>
              ) : reading.error ? (
                <span className="company-overview-loading">
                  Saved data unavailable. Reload to try again.
                </span>
              ) : (
                <>
                  <span className="company-overview-quote">
                    <strong>
                      {price ? (
                        <>
                          {price} <small>USD</small>
                        </>
                      ) : (
                        "Price unavailable"
                      )}
                    </strong>
                    {quote && (
                      <PriceChange
                        movement={quoteMovement(data.market, reading.history)}
                      />
                    )}
                    <span className="company-overview-date">
                      {quote
                        ? `${yahoo && extendedLine(reading.history) ? "At close · " : yahoo && sessionLabel(quote.session) ? `${sessionLabel(quote.session)} · ` : ""}${yahoo ? "Yahoo Finance" : "Finnhub"} · ${stamp(quote.quoted_at)}`
                        : "No saved quote"}
                      {reading.priceError && " · Latest-price read unavailable"}
                    </span>
                    {yahoo && extendedLine(reading.history) && (
                      <ExtendedPrice line={extendedLine(reading.history)} />
                    )}
                  </span>
                  <span className="company-overview-tone">
                    <span>
                      {beginner ? "News · " : "News tone · "}
                      {waiting
                        ? "Loading…"
                        : tone?.label ||
                          (tone
                            ? beginner
                              ? "Not enough to tell yet"
                              : "Too few interpretable developments"
                            : beginner
                              ? "Not read yet"
                              : "No saved reading")}
                    </span>
                    <small>
                      {beginner
                        ? "Open the company for the headlines"
                        : waiting
                          ? "Reading saved news"
                          : tone
                            ? `${tone.selected} ${tone.selected === 1 ? "story" : "stories"} · ${tone.total} counted groups · ${tone.stale ? "older reading" : "saved"} ${stamp(tone.savedAt)}`
                            : "Analyse news in the company workspace"}
                    </small>
                  </span>
                  <Card
                    as="span"
                    variant="inset"
                    className="company-overview-figures"
                    hidden={beginner}
                  >
                    <span>
                      <span>Revenue · 12 months</span>
                      <strong>
                        {waiting
                          ? "…"
                          : revenue
                            ? money(revenue.value)
                            : "Unavailable"}
                      </strong>
                      <small>
                        {waiting
                          ? "Loading saved figure"
                          : revenue
                            ? `SEC · to ${day(revenue.end)}`
                            : "No compatible saved figure"}
                      </small>
                    </span>
                    <span>
                      <span>Operating margin</span>
                      <strong>
                        {waiting
                          ? "…"
                          : margin
                            ? percent(margin.value)
                            : "Unavailable"}
                      </strong>
                      <small>
                        {waiting
                          ? "Loading saved figure"
                          : margin
                            ? `SEC · to ${day(margin.end)}`
                            : "No compatible saved figure"}
                      </small>
                    </span>
                  </Card>
                </>
              )}
              <span className="company-overview-footer">
                <span>
                  {company.status
                    ? beginner
                      ? "View saved"
                      : "Idea saved"
                    : beginner
                      ? "No view saved yet"
                      : "No saved idea"}
                  {company.unread > 0 && (
                    <Badge status="info">{company.unread} to review</Badge>
                  )}
                </span>
                <span>{beginner ? "See summary" : "Open workspace"}</span>
              </span>
            </Card>
          );
        })}
      </div>
      {!companies.length && (
        <p className="company-overview-empty">
          {query.trim()
            ? `No companies match “${query}”.`
            : "Your watchlist is empty. Add a company to follow it here."}
        </p>
      )}
    </section>
  );
}

function recordsFor(company, versions) {
  return versions.flatMap((version) => {
    const record = (id, kind, created_at) => ({
      id,
      kind,
      created_at,
      company,
      revision: version.revision,
      question: version.question,
    });
    return [
      record(`revision:${version.id}`, "Saved definition", version.created_at),
      ...version.evaluations.map((evaluation) =>
        record(
          evaluation.id,
          "Monitoring assessment",
          evaluation.created_at ||
            evaluation.manifest.assessed_at ||
            evaluation.manifest.cutoff,
        ),
      ),
      ...(version.event_reviews || []).map((review) =>
        record(`event:${review.id}`, "Event evidence check", review.created_at),
      ),
      ...(version.evidence_reviews || []).map((review) =>
        record(`comparison:${review.id}`, "AI comparison", review.created_at),
      ),
    ];
  });
}

export function AllHistory({
  catalogue,
  onOpen,
  visible = true,
  hasChecks = false,
}) {
  const [state, setState] = useState({
    records: [],
    errors: [],
    loading: true,
    membership: null,
  });
  const [refresh, setRefresh] = useState(0);
  // This bounded local catalogue reuses the existing account/source-scoped reads.
  const membership = catalogue
    .filter((company) => company.status)
    .map((company) => `${company.id}:${company.revision}`)
    .join(",");
  useEffect(() => {
    if (!visible) return;
    let active = true;
    const controller = new AbortController();
    const existing = state.membership === membership;
    if (!existing)
      setState({ records: [], errors: [], loading: true, membership: null });
    const companies = catalogue.filter((company) => company.status);
    readableLoad(
      Promise.allSettled(
        companies.map((company) =>
          api.workspace(company.id, {
            includeFinancials: false,
            signal: controller.signal,
          }),
        ),
      ),
      existing ? 0 : 280,
    ).then((results) => {
      if (!active) return;
      const records = [],
        errors = [];
      results.forEach((result, index) => {
        if (result.status === "fulfilled")
          records.push(...recordsFor(companies[index], result.value.versions));
        else errors.push(companies[index].symbol);
      });
      records.sort(
        (a, b) =>
          (Date.parse(b.created_at) || 0) - (Date.parse(a.created_at) || 0) ||
          a.id.localeCompare(b.id),
      );
      setState({ records, errors, loading: false, membership });
    });
    return () => {
      active = false;
      controller.abort();
    };
  }, [membership, refresh, visible]);
  return (
    <section
      className="collection-page all-history"
      aria-label="All company history"
    >
      <span className="section-label">ALL COMPANIES</span>
      <div className="row">
        <h2>History</h2>
        <button
          onClick={() => setRefresh((value) => value + 1)}
          disabled={state.loading}
        >
          Refresh history
        </button>
      </div>
      <p className="muted">
        Past versions of your ideas and completed checks, newest first.
      </p>
      {state.loading ? (
        <LoadingSkeleton label="Loading saved company histories…" />
      ) : (
        <>
          {!!state.errors.length && (
            <p className="warning" role="alert">
              History could not be loaded for {state.errors.join(", ")}. Refresh
              to retry.
            </p>
          )}
          {!state.records.length && !state.errors.length && !hasChecks && (
            <div className="history-empty">
              <span className="history-empty-mark" aria-hidden="true">
                <svg
                  width="24"
                  height="24"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                >
                  <circle cx="12" cy="12" r="8" />
                  <path d="M12 7v5l3 2" />
                </svg>
              </span>
              <h3>No saved history yet</h3>
              <p>
                Save an idea first. Its revisions and completed checks will
                appear here, so you can see how your thinking changed.
              </p>
              <button onClick={() => onOpen("", "ideas")}>
                Go to My views
              </button>
            </div>
          )}
          <div className="idea-collection">
            {state.records.map((record) => (
              <button
                key={`${record.company.id}:${record.id}`}
                className="idea-summary"
                data-company={record.company.id}
                onClick={() => onOpen(record.company.id, "history", record.id)}
              >
                <div className="row">
                  <strong>
                    {record.company.symbol} · {record.kind}
                  </strong>
                  <span className="muted">{stamp(record.created_at)}</span>
                </div>
                <h3>{record.question}</h3>
                <span className="text-button">
                  Revision {record.revision} · Open saved record ↗
                </span>
              </button>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
