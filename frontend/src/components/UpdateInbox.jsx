import LoadingSkeleton from "./LoadingSkeleton";
import { readableLoad } from "../lib/loading";
import Select from "./Select";
import { useEffect, useState } from "react";
import { api } from "../api/client";
import { stamp } from "./MarketResearch";
import IdeaAlertChecks from "./IdeaAlertChecks";
import { ResearchAlerts } from "./SentimentPanel";
import { ConditionChange } from "./IdeasAndChanges";
import { inboxSummary, recordKey } from "../lib/inbox";
import "./UpdateInbox.css";

const kindName = {
  idea: "Your saved idea",
  company: "Company news",
  condition: "Monitored condition",
};
const reviewName = (action) =>
  ({ reviewed: "Reviewed", unresolved: "Left unresolved" })[action] ||
  "Awaiting review";

export default function UpdateInbox({
  active = true,
  filters,
  onFiltersChange,
  catalogue,
  onOpen,
  onSource,
  onReviewed,
  onWeeklyReview,
  unseenReviews = 0,
}) {
  const { company, review, page, cutoff } = filters;
  const [refresh, setRefresh] = useState(0);
  const [data, setData] = useState(null);
  const [fetching, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [emptyCompany, setEmptyCompany] = useState("");
  const isEmptyCompany = !!company && emptyCompany === company;
  // A sidebar filter changes outside this component. Withhold the earlier
  // result immediately, including before the new request effect starts.
  const loading =
    fetching ||
    (!error &&
      !isEmptyCompany &&
      (!data ||
        (data.instrument_id || "") !== company ||
        data.review !== review ||
        data.page !== page));
  const companies = [
    ...new Map(
      [...(catalogue || []), ...(data?.companies || [])].map((c) => [c.id, c]),
    ).values(),
  ];
  useEffect(() => {
    if (!active) return;
    let current = true;
    const existing =
      data &&
      (data.instrument_id || "") === company &&
      data.review === review &&
      data.page === page;
    setLoading(!existing);
    setError("");
    setEmptyCompany("");
    readableLoad(
      api.researchReview({
        days: 0,
        instrument_id: company,
        review,
        page,
        cutoff,
      }),
      existing ? 0 : 280,
    )
      .then((result) => {
        if (current) setData(result);
      })
      .catch((e) => {
        if (!current) return;
        if (
          company &&
          e.status === 404 &&
          e.message ===
            "No saved idea or watch exists for this company in your account."
        ) {
          setEmptyCompany(company);
        } else {
          setError(e.message);
        }
      })
      .finally(() => {
        if (current) setLoading(false);
      });
    return () => {
      current = false;
    };
  }, [company, review, page, cutoff, refresh, active]);
  function reset(changes = {}) {
    setLoading(true);
    onFiltersChange((current) => ({
      ...current,
      ...changes,
      page: 0,
      cutoff: "",
    }));
  }
  function turnPage(delta) {
    setLoading(true);
    onFiltersChange((current) => ({
      ...current,
      cutoff: data.cutoff,
      page: current.page + delta,
    }));
  }
  function reload() {
    reset();
    setRefresh((n) => n + 1);
  }
  async function acknowledge(kind, id, action) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await (kind === "idea"
        ? api.reviewIdeaAlert(id, action)
        : api.reviewAlert(id, action));
      setNotice(
        action === "reviewed"
          ? "Review recorded. Your idea is unchanged."
          : "Left unresolved. Your idea is unchanged.",
      );
      reload();
      // The write succeeded even if the separate navigation-badge refresh fails.
      await onReviewed().catch(() => {});
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  const scoped = (data?.companies || []).filter(
    (c) => !company || c.id === company,
  );
  const gaps = scoped.filter((c) => c.coverage.concerns.length);
  const off = scoped.filter(
    (c) => c.mode !== "recorded" && !c.coverage.watch?.enabled,
  );
  return (
    <section className="update-inbox" aria-label="Research update inbox">
      <div className="market-section-head">
        <div>
          <h2>Updates</h2>
          <p className="inbox-intro">
            Changes to your ideas, company reporting and monitored conditions.
          </p>
        </div>
        <div className="inbox-heading-actions">
          {onWeeklyReview && (
            <button onClick={onWeeklyReview}>
              Weekly review{unseenReviews > 0 ? ` · ${unseenReviews} new` : ""}
            </button>
          )}
          <button onClick={reload} disabled={loading || busy}>
            Refresh inbox
          </button>
        </div>
      </div>
      <details className="inbox-filter-disclosure">
        <summary>
          Filter updates{" "}
          <span>
            {companies.find((c) => c.id === company)?.symbol || "All companies"}{" "}
            ·{" "}
            {review === "all"
              ? "All updates"
              : reviewName(review === "pending" ? null : review)}
          </span>
        </summary>
        <div className="inbox-filters">
          <label>
            Company
            <Select
              aria-label="Inbox company"
              value={company}
              disabled={busy}
              onChange={(e) => {
                reset({ company: e.target.value });
              }}
            >
              <option value="">All my ideas and watches</option>
              {companies.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.symbol} · {c.name}
                </option>
              ))}
            </Select>
          </label>
          <label>
            Show updates
            <Select
              aria-label="Show updates"
              value={review}
              disabled={busy}
              onChange={(e) => {
                reset({ review: e.target.value });
              }}
            >
              <option value="pending">Awaiting review</option>
              <option value="unresolved">Left unresolved</option>
              <option value="reviewed">Reviewed</option>
              <option value="all">All updates</option>
            </Select>
          </label>
        </div>
      </details>
      {notice && (
        <p role="status" className="notice">
          {notice}
        </p>
      )}
      {error && (
        <div role="alert" className="warning">
          <p>{error}</p>
          <button onClick={reload} disabled={busy}>
            Retry inbox
          </button>
        </div>
      )}
      {loading && <LoadingSkeleton label="Loading saved updates…" />}
      {!loading && isEmptyCompany && (
        <div className="empty-history">
          <h3>No updates in this view</h3>
          <p>No saved idea or watch exists for this company yet.</p>
          <button onClick={() => onOpen(company, "workspace")}>
            Open company research ↗
          </button>
        </div>
      )}
      {!loading && !error && !isEmptyCompany && data && (
        <>
          <div className="inbox-counts" aria-label="Update counts">
            <strong>{data.totals.pending_count} awaiting review</strong>
            {data.totals.unresolved_count > 0 && (
              <span>{data.totals.unresolved_count} left unresolved</span>
            )}
          </div>
          <details className="inbox-list-meta">
            <summary>
              {data.total} matching {data.total === 1 ? "update" : "updates"} ·
              newest first
            </summary>
            <p>
              Showing {data.records.length ? page * data.page_size + 1 : 0}–
              {page * data.page_size + data.records.length} · recorded through{" "}
              {stamp(data.cutoff)}. Review status is current; source event dates
              may be earlier.
            </p>
          </details>
          {!data.records.length && (
            <div className="empty-history">
              <h3>
                {review === "pending"
                  ? "Nothing awaiting review"
                  : "No updates in this view"}
              </h3>
              <p>
                Check source coverage below, or choose another company or review
                status. Quiet checks remain in History.
              </p>
            </div>
          )}
          <div className="inbox-records change-collection">
            {data.records.map((record) => {
              const d = record.detail,
                summary = inboxSummary(record);
              if (record.kind === "condition")
                return (
                  <article
                    className="inbox-record"
                    data-kind={record.kind}
                    data-record-id={record.id}
                    key={recordKey(record)}
                  >
                    <div className="inbox-kind">{kindName[record.kind]}</div>
                    <ConditionChange change={d} onOpen={onOpen} />
                  </article>
                );
              return (
                <details
                  className="inbox-record"
                  data-kind={record.kind}
                  data-record-id={record.id}
                  key={recordKey(record)}
                >
                  <summary>
                    <div className="inbox-record-head">
                      <strong>{d.symbol}</strong>
                      <span className="inbox-kind">
                        {kindName[record.kind]}
                      </span>
                      <time>{stamp(record.created_at)}</time>
                    </div>
                    <h3>{summary.title}</h3>
                    <p className="inbox-preview">{summary.text}</p>
                    {summary.source && (
                      <p className="inbox-source-caption">
                        {summary.source}
                        {summary.publishedAt
                          ? ` · Source dated ${stamp(summary.publishedAt)}`
                          : ""}
                        {summary.more > 0
                          ? ` · +${summary.more} more saved sources`
                          : ""}
                      </p>
                    )}
                    {summary.alert && (
                      <p className="inbox-alert-caption">
                        Flagged for review: {summary.alert}
                      </p>
                    )}
                    {summary.question && (
                      <p className="fine inbox-preview">
                        Your question: {summary.question}
                      </p>
                    )}
                    <div className="inbox-record-footer">
                      <span
                        className={`inbox-review-status${record.review_action ? "" : " pending"}`}
                      >
                        {reviewName(record.review_action)}
                      </span>
                      <span className="inbox-evidence-control">
                        <span className="inbox-inspect-label">
                          Inspect evidence
                        </span>
                        <span className="inbox-hide-label">Hide evidence</span>
                        <svg
                          width="16"
                          height="16"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="1.7"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          aria-hidden="true"
                        >
                          <path d="m9 5 7 7-7 7" />
                        </svg>
                      </span>
                    </div>
                  </summary>
                  <div className="inbox-detail">
                    {record.kind === "idea" ? (
                      <IdeaAlertChecks
                        checks={[d]}
                        embedded
                        busy={busy}
                        onSource={onSource}
                        onOpen={onOpen}
                        onReview={(id, action) =>
                          acknowledge("idea", id, action)
                        }
                      />
                    ) : (
                      <ResearchAlerts
                        alerts={[d]}
                        embedded
                        busy={busy}
                        onSource={onSource}
                        onOpen={onOpen}
                        onReview={(id, action) =>
                          acknowledge("company", id, action)
                        }
                      />
                    )}
                  </div>
                </details>
              );
            })}
          </div>
          {data.total > data.page_size && (
            <div className="review-pagination">
              <button
                disabled={busy || page === 0}
                onClick={() => turnPage(-1)}
              >
                Previous updates
              </button>
              <span>
                Page {page + 1} of {Math.ceil(data.total / data.page_size)}
              </span>
              <button
                disabled={busy || (page + 1) * data.page_size >= data.total}
                onClick={() => turnPage(1)}
              >
                Next updates
              </button>
            </div>
          )}
          <details
            className={`inbox-coverage${gaps.length ? " has-concerns" : ""}`}
          >
            <summary>
              Source coverage ·{" "}
              {gaps.length
                ? `${gaps.length} ${gaps.length === 1 ? "company needs" : "companies need"} attention`
                : "inspect latest checks"}
              {off.length
                ? ` · ${off.length} ${off.length === 1 ? "watch" : "watches"} off`
                : ""}
            </summary>
            <p className="fine">
              A quiet inbox does not mean nothing important happened. These are
              the latest recorded checks; opening this inbox does not refresh
              sources.
            </p>
            {!scoped.length && (
              <p>
                No saved ideas or watches yet. Open a company to begin your
                research.
              </p>
            )}
            {scoped.map((c) => (
              <div key={c.id}>
                <strong>
                  {c.symbol} · {c.name}
                </strong>
                <p className="fine">
                  {c.mode === "recorded"
                    ? "Recorded fictional example"
                    : c.coverage.watch?.enabled
                      ? `Local watch on · every ${c.coverage.watch.interval_minutes === 60 ? "hour" : "four hours"} while the app runs`
                      : "Local watch off"}
                </p>
                {c.coverage.concerns.map((message) => (
                  <p className="fine" key={message}>
                    {message}
                  </p>
                ))}
                <button onClick={() => onOpen(c.id, "workspace")}>
                  Open {c.symbol} research ↗
                </button>
              </div>
            ))}
          </details>
          <p className="fine">
            Marking an alert reviewed records your attention. It does not
            approve the investment, resolve a risk or change your saved idea.
          </p>
        </>
      )}
    </section>
  );
}
