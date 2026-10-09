import CompanyAvatar from "./CompanyAvatar";
import { companyName, companyMatches } from "../lib/companyIdentity";
import LoadingSkeleton from "./LoadingSkeleton";
import { WorkspaceSidebar } from "./WorkspaceControls";

export function CompanyAddButton({ className = "", ...props }) {
  return (
    <button
      type="button"
      className={`add-company ${className}`}
      aria-label="Add company"
      title="Add company"
      {...props}
    >
      <svg
        width="22"
        height="22"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        aria-hidden="true"
      >
        <path d="M12 5v14M5 12h14" />
      </svg>
    </button>
  );
}

export default function CompanySidebar({
  companies = [],
  selectedCompanyId,
  collapsed,
  onToggle,
  search = "",
  onSearch,
  onChoose,
  onRemove,
  onAdd,
  busy = false,
  loading = false,
}) {
  const shownCompanies = collapsed
    ? companies
    : companies.filter((company) => companyMatches(company, search));
  const toggleLabel = `${collapsed ? "Expand" : "Collapse"} company sidebar`;
  return (
    <WorkspaceSidebar
      id="companies-sidebar"
      className="watchlist"
      aria-label="Companies"
      data-collapsed={!!collapsed}
    >
      <div className="company-sidebar-content">
        {loading ? (
          <LoadingSkeleton rows={2} label="Loading companies…" />
        ) : (
          <>
            <div
              className="company-sidebar-browse"
              aria-hidden={collapsed || undefined}
              inert={collapsed ? "" : undefined}
            >
              <div className="company-sidebar-browse-clip">
                <div className="section-label">
                  COMPANIES <span>{companies.length}</span>
                </div>
                <label className="company-search">
                  <span>Find a company</span>
                  <input
                    value={search}
                    onChange={(event) => onSearch(event.target.value)}
                    placeholder="Name or symbol"
                  />
                </label>
              </div>
            </div>
            <div className="company-list">
              <button
                className={`watch-item all-companies-button ${!selectedCompanyId ? "selected" : ""}`}
                aria-label="All companies"
                title="All companies"
                aria-pressed={!selectedCompanyId}
                onClick={() => onChoose("")}
              >
                <svg
                  className="all-companies-icon"
                  width="22"
                  height="22"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  aria-hidden="true"
                >
                  <rect x="3" y="3" width="7" height="7" rx="1.5" />
                  <rect x="14" y="3" width="7" height="7" rx="1.5" />
                  <rect x="3" y="14" width="7" height="7" rx="1.5" />
                  <rect x="14" y="14" width="7" height="7" rx="1.5" />
                </svg>
                <strong className="all-companies-label">All companies</strong>
              </button>
              {shownCompanies.map((company) => (
                <div
                  className={`company-row ${company.id === selectedCompanyId ? "selected" : ""}`}
                  key={company.id}
                >
                  <button
                    className={`watch-item ${company.id === selectedCompanyId ? "selected" : ""}`}
                    aria-label={`${company.symbol} · ${companyName(company)}`}
                    title={`${company.symbol} · ${company.name}`}
                    aria-pressed={company.id === selectedCompanyId}
                    disabled={busy}
                    onClick={() => onChoose(company.id)}
                  >
                    <CompanyAvatar company={company} small />
                    <span className="company-row-label">
                      <strong title={company.symbol}>{company.symbol}</strong>
                      <small title={company.name}>{companyName(company)}</small>
                    </span>
                    {company.unread > 0 && <span className="watch-dot" />}
                  </button>
                  <button
                    type="button"
                    className="remove-company"
                    aria-label={`Remove ${company.symbol} from sidebar`}
                    title={`Remove ${company.symbol} from sidebar`}
                    onClick={() => onRemove(company)}
                  >
                    ×
                  </button>
                </div>
              ))}
              {!shownCompanies.length && !collapsed && (
                <p className="watch-caption">
                  {companies.length
                    ? "No matching company in your sidebar."
                    : "Your sidebar is empty. Add or restore a company."}
                </p>
              )}
            </div>
          </>
        )}
      </div>
      <div className="company-sidebar-actions">
        <CompanyAddButton onClick={onAdd} disabled={loading} />
        <button
          type="button"
          className="panel-toggle panel-toggle-left"
          aria-label={toggleLabel}
          title={toggleLabel}
          aria-expanded={!collapsed}
          aria-controls="companies-sidebar"
          onClick={onToggle}
        >
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.7"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d={collapsed ? "m9 5 7 7-7 7" : "m15 5-7 7 7 7"} />
          </svg>
        </button>
      </div>
    </WorkspaceSidebar>
  );
}
