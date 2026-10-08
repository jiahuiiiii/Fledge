import { useEffect, useState } from "react";
import { api } from "../api/client";
import { readableLoad } from "../lib/loading";
import LoadingSkeleton from "./LoadingSkeleton";
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

export default function CompanyOverview({ catalogue, onOpen }) {
  return (
    <section className="collection-page" aria-label="All company workspaces">
      <span className="section-label">ALL COMPANIES</span>
      <h1>Your research workspace</h1>
      <p className="muted">
        Choose a company to explore its news, fundamentals and your saved
        reasoning.
      </p>
      <div className="idea-collection">
        {catalogue.map((company) => (
          <button
            className="idea-summary"
            key={company.id}
            onClick={() => onOpen(company.id, "workspace")}
          >
            <div className="row">
              <strong>
                {company.symbol} · {company.name}
              </strong>
              <span className="status">
                {company.mode === "recorded"
                  ? "Fictional sample"
                  : "Company research"}
              </span>
            </div>
            <p>{company.question || "Start with a research question."}</p>
            <span className="text-button">Open workspace ↗</span>
          </button>
        ))}
      </div>
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
