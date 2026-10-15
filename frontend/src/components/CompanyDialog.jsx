import { useEffect, useRef, useState } from "react";
import Modal from "./Modal";
import LoadingSkeleton from "./LoadingSkeleton";
import { api } from "../api/client";
import { companyName } from "../lib/companyIdentity";
import { needsListingUpdate } from "../lib/companyDirectory";

function ActionIcon({ restore = false }) {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      aria-hidden="true"
    >
      <path
        d={restore ? "M4 10a8 8 0 1 1 1 9M4 4v6h6" : "M6 6l12 12M18 6 6 18"}
      />
    </svg>
  );
}

export default function CompanyDialog({
  open,
  onClose,
  visible = [],
  hidden = [],
  onRemove,
  onRestore,
  onAdded,
}) {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  // "" | "updating" | "failed": the automatic or manual listing update.
  const [listing, setListing] = useState("");
  const refreshing = useRef(null);
  const tried = useRef(false);
  useEffect(() => {
    if (!open) tried.current = false;
  }, [open]);
  function refreshListings() {
    if (refreshing.current) return refreshing.current;
    setListing("updating");
    refreshing.current = api
      .refreshCompanyDirectory()
      .then(() => setListing(""))
      .catch(() => setListing("failed"))
      .finally(() => {
        refreshing.current = null;
        // Re-read even after a failure: another tab may have updated it.
        setRevision((r) => r + 1);
      });
    return refreshing.current;
  }
  // Update quietly once per opening when the saved copy is over a day old.
  useEffect(() => {
    if (!open || tried.current || !needsListingUpdate(result)) return;
    tried.current = true;
    refreshListings();
  }, [open, result]);
  useEffect(() => {
    if (!open) return;
    let active = true;
    setLoading(true);
    const timer = setTimeout(
      () => {
        api
          .companyDirectory(query)
          .then((data) => {
            if (active) {
              setResult(data);
              setError("");
            }
          })
          .catch((e) => active && setError(e.message))
          .finally(() => active && setLoading(false));
      },
      query ? 200 : 0,
    );
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [open, query, revision]);
  function update() {
    setError("");
    refreshListings();
  }
  async function add(company) {
    if (company.instrument_id) {
      onAdded(company.instrument_id);
      return;
    }
    setBusy(company.symbol);
    setError("");
    try {
      // A new listing needs current listings; wait for an update in progress.
      if (refreshing.current) await refreshing.current;
      const saved = await api.addSecCompany(company.symbol);
      onAdded(saved.instrument_id);
    } catch (e) {
      setError(
        e.message?.startsWith("Update the company directory")
          ? `US listings couldn’t be updated just now, so ${company.symbol} can’t be added yet. Try again in a few minutes.`
          : e.message,
      );
    } finally {
      setBusy("");
    }
  }
  // Companies already in this account's list (including the practice
  // companies) always match by name or ticker, even when they are not in the
  // US listings directory. Newcomers search for the company they were sent.
  const needle = query.trim().toLowerCase();
  const fromServer = result?.companies || [];
  const ownMatches = needle
    ? visible
        .filter(
          (c) =>
            (c.symbol || "").toLowerCase().includes(needle) ||
            (c.name || "").toLowerCase().includes(needle),
        )
        .filter((c) => !fromServer.some((r) => r.instrument_id === c.id))
        .map((c) => ({
          symbol: c.symbol,
          name: c.name,
          instrument_id: c.id,
          available: true,
          exchange: c.mode === "recorded" ? "Practice" : "",
        }))
    : [];
  const rows = [...ownMatches, ...fromServer];
  return (
    <Modal
      open={open}
      title="Add a company"
      className="company-modal"
      onClose={() => !busy && onClose()}
    >
      <div className="company-dialog">
        <label className="company-search-label" htmlFor="company-lookup">
          Find a company
        </label>
        <div className="company-search-field">
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.6"
            aria-hidden="true"
          >
            <circle cx="10.5" cy="10.5" r="6.5" />
            <path d="m16 16 5 5" />
          </svg>
          <input
            id="company-lookup"
            autoFocus
            type="search"
            maxLength={80}
            autoComplete="off"
            onKeyDown={(e) => {
              if (e.key === "Escape" && !busy) {
                e.preventDefault();
                e.stopPropagation();
                onClose();
              }
            }}
            placeholder="Company name or ticker, e.g. Tesla or TSLA"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <div className="company-result-heading">
          <span>{query ? "Search results" : "Explore companies"}</span>
          <span>US listings</span>
        </div>
        {error && (
          <p className="warning" role="alert">
            {error}
          </p>
        )}
        <div className="company-search-results" aria-busy={loading}>
          {loading ? (
            <LoadingSkeleton rows={3} label="Finding companies…" />
          ) : rows.length ? (
            <ul aria-label="Company search results">
              {rows.map((company) => {
                const saved = company.instrument_id;
                const isHidden = hidden.some((c) => c.id === saved);
                // "Open" only for companies already on this account's list.
                const listed = visible.some((c) => c.id === saved);
                return (
                  <li key={company.symbol}>
                    <button
                      type="button"
                      className="company-result"
                      disabled={!!busy || !company.available}
                      onClick={() => add(company)}
                      aria-label={`${saved && (isHidden || listed) ? (isHidden ? "Restore" : "Open") : "Add"} ${company.symbol} · ${company.name}`}
                    >
                      <span className="company-symbol-mark" aria-hidden="true">
                        {company.symbol.slice(0, 2)}
                      </span>
                      <span className="company-result-name">
                        <strong>
                          {company.symbol}
                          <small>{company.exchange}</small>
                        </strong>
                        <span title={company.name}>{companyName(company)}</span>
                        {company.limitation && <em>{company.limitation}</em>}
                      </span>
                      <span className="company-result-action">
                        {busy === company.symbol
                          ? listing === "updating"
                            ? "Updating listings…"
                            : "Adding…"
                          : !company.available
                            ? "Unavailable"
                            : isHidden
                              ? "Restore"
                              : saved && listed
                                ? "Open"
                                : "+ Add"}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          ) : (
            <div className="company-search-empty">
              <strong>No matching companies</strong>
              <p>
                Fledge covers US-listed companies for now, such as Apple
                (AAPL). Singapore (SGX) and other non-US shares aren’t covered
                yet.
              </p>
            </div>
          )}
        </div>
        <div className="company-directory-status">
          <span role="status">
            {listing === "updating"
              ? "Updating US listings from the SEC…"
              : listing === "failed"
                ? "Showing the companies we already have. The full US list couldn’t refresh just now."
                : !result?.retrieved_at
                  ? "Search more US companies by loading the full list."
                  : "Company identities from SEC · coverage varies by source"}
          </span>
          {(listing === "failed" || !result?.retrieved_at) && (
            <button
              type="button"
              className="text-button"
              onClick={update}
              disabled={!!busy || listing === "updating"}
            >
              {result?.retrieved_at ? "Try again" : "Load full list"}
            </button>
          )}
        </div>
        {(visible.length > 0 || hidden.length > 0) && (
          <details className="company-management">
            <summary>
              Manage my companies <span>{visible.length} companies</span>
            </summary>
            <p>
              Removing a company only hides it from your sidebar. Research and
              monitoring are kept.
            </p>
            <ul aria-label="Sidebar companies">
              {visible.map((company) => (
                <li key={company.id}>
                  <span>
                    <strong>{company.symbol}</strong> {companyName(company)}
                  </span>
                  <button
                    type="button"
                    className="company-row-action"
                    aria-label={`Remove ${company.symbol}`}
                    title="Remove from sidebar"
                    onClick={() => onRemove(company)}
                  >
                    <ActionIcon />
                  </button>
                </li>
              ))}
            </ul>
            {hidden.length > 0 && (
              <>
                <h3>Hidden companies</h3>
                <ul aria-label="Hidden companies">
                  {hidden.map((company) => (
                    <li key={company.id}>
                      <span>
                        <strong>{company.symbol}</strong> {companyName(company)}
                      </span>
                      <button
                        type="button"
                        className="company-row-action"
                        aria-label={`Restore ${company.symbol}`}
                        title="Restore to sidebar"
                        onClick={() => onRestore(company.id)}
                      >
                        <ActionIcon restore />
                      </button>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </details>
        )}
      </div>
    </Modal>
  );
}
