import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import { readableLoad } from "../lib/loading";
import LoadingSkeleton from "./LoadingSkeleton";
import CompanyAvatar from "./CompanyAvatar";
import PriceChange from "./PriceChange";
import { companyName, companyMatches } from "../lib/companyIdentity";
import { day, money, percent, trailing } from "../lib/companySnapshot";
import { latestPriceQuote, quoteMovement } from "../lib/priceRefresh";
import "./CompanyOverview.css";
const stamp = (value) =>
  value
    ? new Date(value).toLocaleString("en-GB", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        timeZone: "UTC",
      }) + " UTC"
    : "Date unavailable";

export default function CompanyOverview({
  catalogue,
  initialWorkspace,
  onOpen,
}) {
  const [readings, setReadings] = useState({});
  const [refresh, setRefresh] = useState(0);
  const [query, setQuery] = useState("");
  const current = useRef({ catalogue, initialWorkspace });
  current.current = { catalogue, initialWorkspace };
  const membership = catalogue.map((company) => company.id).join(",");
  useEffect(() => {
    let active = true;
    const { catalogue: companies, initialWorkspace: initial } = current.current;
    setReadings({});
    let index = 0;
    // Local, account-scoped reads only. Browsing does not refresh suppliers.
    const worker = async () => {
      while (active && index < companies.length) {
        const company = companies[index++];
        const [workspace, prices] = await Promise.allSettled([
          !refresh && initial?.instrument?.id === company.id
            ? Promise.resolve(initial)
            : api.workspace(company.id),
          company.mode === "sec"
            ? api.priceHistory(company.id)
            : Promise.resolve(null),
        ]);
        if (!active) return;
        const data =
          workspace.status === "fulfilled" &&
          workspace.value?.instrument?.id === company.id
            ? workspace.value
            : null;
        const history =
          prices.status === "fulfilled" &&
          prices.value?.symbol === company.symbol
            ? prices.value
            : null;
        setReadings((previous) => ({
          ...previous,
          [company.id]: {
            data,
            history,
            error: !data,
            priceError: prices.status === "rejected",
          },
        }));
      }
    };
    void Promise.all(
      Array.from({ length: Math.min(3, companies.length) }, worker),
    );
    return () => {
      active = false;
    };
  }, [membership, refresh]);
  const loading = catalogue.some((company) => !readings[company.id]);
  const companies = catalogue.filter((company) =>
    companyMatches(company, query),
  );
  return (
    <section
      className="collection-page company-overview"
      aria-label="All company workspaces"
    >
      <div className="company-overview-heading">
        <div>
          <span className="section-label">YOUR RESEARCH</span>
          <h1>
            All companies <span>{catalogue.length}</span>
          </h1>
          <p className="muted">
            Saved prices and financials, together. Open a company to explore its
            evidence.
          </p>
        </div>
        <button
          onClick={() => setRefresh((value) => value + 1)}
          disabled={loading}
        >
          Reload saved data
        </button>
      </div>
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
          return (
            <button
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
                    {company.mode === "recorded" && " · Fictional sample"}
                  </span>
                </span>
                <span className="company-overview-arrow" aria-hidden="true">
                  ↗
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
                        ? `${yahoo ? "Yahoo Finance" : "Finnhub"} · ${stamp(quote.quoted_at)}`
                        : "No saved quote"}
                      {reading.priceError && " · Latest-price read unavailable"}
                    </span>
                  </span>
                  <span className="company-overview-figures">
                    <span>
                      <span>Revenue · 12 months</span>
                      <strong>
                        {revenue ? money(revenue.value) : "Unavailable"}
                      </strong>
                      <small>
                        {revenue
                          ? `SEC · to ${day(revenue.end)}`
                          : "No compatible saved figure"}
                      </small>
                    </span>
                    <span>
                      <span>Operating margin</span>
                      <strong>
                        {margin ? percent(margin.value) : "Unavailable"}
                      </strong>
                      <small>
                        {margin
                          ? `SEC · to ${day(margin.end)}`
                          : "No compatible saved figure"}
                      </small>
                    </span>
                  </span>
                </>
              )}
              <span className="company-overview-footer">
                <span>
                  {company.status ? "Idea saved" : "No saved idea"}
                  {company.unread > 0 && ` · ${company.unread} to review`}
                </span>
                <span>Open workspace →</span>
              </span>
            </button>
          );
        })}
      </div>
      {!companies.length && (
        <p className="company-overview-empty">No companies match “{query}”.</p>
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

export function AllHistory({ catalogue, onOpen, visible = true }) {
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
    const existing = state.membership === membership;
    if (!existing)
      setState({ records: [], errors: [], loading: true, membership: null });
    const companies = catalogue.filter((company) => company.status);
    readableLoad(
      Promise.allSettled(companies.map((company) => api.workspace(company.id))),
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
    };
  }, [membership, refresh, visible]);
  return (
    <section
      className="collection-page all-history"
      aria-label="All company history"
    >
      <span className="section-label">ALL COMPANIES</span>
      <div className="row">
        <h2>Research history</h2>
        <button
          onClick={() => setRefresh((value) => value + 1)}
          disabled={state.loading}
        >
          Refresh history
        </button>
      </div>
      <p className="muted">
        Saved definitions and checks, newest first. Open a record to inspect its
        original evidence.
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
          {!state.records.length && !state.errors.length && (
            <h3>No saved research yet</h3>
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
