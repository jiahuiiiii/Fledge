import { useEffect, useState } from "react";
import Modal from "./Modal";
import LoadingSkeleton from "./LoadingSkeleton";
import { api } from "../api/client";

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
  async function update() {
    setBusy("directory");
    setError("");
    try {
      await api.refreshCompanyDirectory();
      setRevision((r) => r + 1);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy("");
    }
  }
  async function add(company) {
    if (company.instrument_id) {
      onAdded(company.instrument_id);
      return;
    }
    setBusy(company.symbol);
    setError("");
    try {
      const saved = await api.addSecCompany(company.symbol);
      onAdded(saved.instrument_id);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy("");
    }
  }
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
          ) : result?.companies?.length ? (
            <ul aria-label="Company search results">
              {result.companies.map((company) => {
                const saved = company.instrument_id;
                const isHidden = hidden.some((c) => c.id === saved);
                return (
                  <li key={company.symbol}>
                    <button
                      type="button"
                      className="company-result"
                      disabled={!!busy || !company.available}
                      onClick={() => add(company)}
                      aria-label={`${saved ? (isHidden ? "Restore" : "Open") : "Add"} ${company.symbol} · ${company.name}`}
                    >
                      <span className="company-symbol-mark" aria-hidden="true">
                        {company.symbol.slice(0, 2)}
                      </span>
                      <span className="company-result-name">
                        <strong>
                          {company.symbol}
                          <small>{company.exchange}</small>
                        </strong>
                        <span>{company.name}</span>
                        {company.limitation && <em>{company.limitation}</em>}
                      </span>
                      <span className="company-result-action">
                        {busy === company.symbol
                          ? "Adding…"
                          : !company.available
                            ? "Unavailable"
                            : saved
                              ? isHidden
                                ? "Restore"
                                : "Open"
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
                Try the ticker or a shorter name. Coverage is limited to
                supported US exchange listings.
              </p>
            </div>
          )}
        </div>
        <div className="company-directory-status">
          <span>
            {!result?.retrieved_at
              ? "Load the directory to search beyond the starter companies."
              : result.stale
                ? "Listings need updating before adding a new company."
                : "Company identities from SEC · coverage varies by source"}
          </span>
          <button
            type="button"
            className="text-button"
            onClick={update}
            disabled={!!busy}
          >
            {busy === "directory"
              ? "Updating…"
              : result?.retrieved_at
                ? "Update listings"
                : "Load directory"}
          </button>
        </div>
        {(visible.length > 0 || hidden.length > 0) && (
          <details className="company-management">
            <summary>
              Manage sidebar <span>{visible.length} companies</span>
            </summary>
            <p>
              Removing a company only hides it from your sidebar. Research and
              monitoring are kept.
            </p>
            <ul aria-label="Sidebar companies">
              {visible.map((company) => (
                <li key={company.id}>
                  <span>
                    <strong>{company.symbol}</strong> {company.name}
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
                        <strong>{company.symbol}</strong> {company.name}
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
