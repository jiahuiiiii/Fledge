import Select from "./Select";
import { resultLabel } from "../lib/conditionRoles";
import { useState } from "react";
import CompanyAvatar from "./CompanyAvatar";
import { companyName } from "../lib/companyIdentity";
import "./IdeasAndChanges.css";
const metrics = {
  revenue_growth: "Revenue growth",
  operating_margin: "Operating margin",
};
const date = (value) =>
  value
    ? new Date(value).toLocaleDateString("en-GB", {
        day: "numeric",
        month: "short",
        year: "numeric",
        timeZone: "UTC",
      })
    : "Time unavailable";
export default function IdeasAndChanges({
  mode,
  catalogue,
  changes,
  onOpen,
  selectedCompany,
  onCreate,
}) {
  const [filter, setFilter] = useState("unreviewed");
  const ideas = catalogue
    .filter((c) => c.status)
    .sort((a, b) => b.unread - a.unread);
  const updates = changes.filter(
    (c) =>
      filter === "all" ||
      (filter === "unresolved"
        ? c.review_action === "unresolved"
        : !c.review_action),
  );
  return (
    <section
      className={`collection-page${mode === "ideas" ? " ideas-page" : ""}`}
      aria-label={mode === "ideas" ? "Saved ideas" : undefined}
    >
      {mode !== "ideas" && <span className="section-label">YOUR RESEARCH</span>}
      <div className="ideas-heading">
        <div>
          <h2>{mode === "ideas" ? "My ideas" : "What changed"}</h2>
          <p className="muted">
            {mode === "ideas"
              ? "The views you chose to save, in your own words."
              : "New evidence, age limits and coverage changes, linked to the reasoning you saved at the time."}
          </p>
        </div>
        {mode === "ideas" && (
          <span className="ideas-scope">
            {selectedCompany && <span>{selectedCompany.symbol}</span>}
            {ideas.length} saved {ideas.length === 1 ? "idea" : "ideas"}
          </span>
        )}
      </div>
      {mode === "ideas" ? (
        ideas.length ? (
          <div className="idea-collection">
            {ideas.map((c) => (
              <button
                key={c.id}
                className="idea-summary"
                onClick={() => onOpen(c.id, "idea")}
              >
                <div className="saved-idea-head">
                  <CompanyAvatar company={c} small />
                  <div className="saved-idea-company">
                    <strong title={c.name}>{companyName(c)}</strong>
                    <span>{c.symbol}</span>
                  </div>
                  <span className="status saved-idea-status">{c.status}</span>
                </div>
                <h3>{c.question || "Your saved idea"}</h3>
                <p className="saved-idea-reasoning">
                  {c.reasoning || "Draft with no reasoning yet."}
                </p>
                <div className="saved-idea-meta">
                  <span
                    className={
                      c.unread
                        ? "saved-idea-updates attention"
                        : "saved-idea-updates muted"
                    }
                  >
                    {c.unread
                      ? `${c.unread} update${c.unread === 1 ? "" : "s"} awaiting review`
                      : "No unreviewed updates"}
                  </span>
                  <span>
                    Evidence cutoff {date(c.cutoff)} · Revision {c.revision}
                  </span>
                </div>
                <div className="saved-idea-footer">
                  <span>Open idea</span>
                  <IdeaArrow />
                </div>
              </button>
            ))}
          </div>
        ) : (
          <div className="ideas-empty">
            <div className="ideas-empty-icon" aria-hidden="true">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M8 17h8M9 21h6M8 14a6 6 0 1 1 8 0c-1 1-1 2-1 3H9c0-1 0-2-1-3Z" />
                <path d="M10 8c.5-.8 1.2-1.2 2-1.2" />
              </svg>
            </div>
            <div className="ideas-empty-copy">
              <h3>
                {selectedCompany
                  ? `Save your view on ${selectedCompany.symbol}`
                  : "What do you think about the companies you follow?"}
              </h3>
              <p>
                Write what you think, why you think it, and what would change
                your mind. You can keep it as a draft and come back later.
              </p>
              <div className="ideas-empty-actions">
                {onCreate ? (
                  <>
                    <button className="primary" onClick={onCreate}>
                      Save my reasoning <IdeaArrow />
                    </button>
                    <button
                      className="ideas-research-link"
                      onClick={() => onOpen(selectedCompany.id, "workspace")}
                    >
                      Read company research
                    </button>
                  </>
                ) : (
                  <button
                    className="primary"
                    onClick={() => onOpen("", "workspace")}
                  >
                    Choose a company <IdeaArrow />
                  </button>
                )}
              </div>
            </div>
          </div>
        )
      ) : (
        <>
          <label className="field">
            Show updates
            <Select
              aria-label="Show updates"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
            >
              <option value="unreviewed">Awaiting review</option>
              <option value="unresolved">Left unresolved</option>
              <option value="all">All updates</option>
            </Select>
          </label>
          {updates.length ? (
            <div className="change-collection">
              {updates.map((c) => (
                <ConditionChange key={c.id} change={c} onOpen={onOpen} />
              ))}
            </div>
          ) : (
            <div className="empty-history">
              <h3>
                {filter === "unreviewed"
                  ? "Nothing awaiting review"
                  : "No updates in this view"}
              </h3>
              <p>
                A quiet update list does not establish that an investment is
                safe. Check source coverage within each company.
              </p>
            </div>
          )}
        </>
      )}
    </section>
  );
}

function IdeaArrow() {
  return (
    <svg
      className="idea-arrow"
      aria-hidden="true"
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M4 10h12m-5-5 5 5-5 5" />
    </svg>
  );
}

export function ConditionChange({ change: c, onOpen }) {
  return (
    <button
      className="change-summary"
      onClick={() => onOpen(c.instrument_id, "history", c.evaluation_id)}
    >
      <div className="row">
        <span className="ticker">{c.symbol}</span>
        <span className="muted">
          Recorded {date(c.created_at)} · revision {c.revision}
        </span>
      </div>
      <h3>{c.summary}</h3>
      <p>{c.question}</p>
      {c.withheld && (
        <p className="warning">
          Source access changed. Figures and interpretations are withheld.
        </p>
      )}
      {!c.withheld &&
        (c.details.affected_reports || []).map((a) => (
          <p key={a.condition_id}>
            {a.state === "conflicting"
              ? "Expected figures conflict"
              : a.state === "overdue"
                ? "Expected figures missing"
                : a.state === "available"
                  ? "Required reporting period available"
                  : "Waiting for expected figures"}
            : {a.period_type} period ending on or after {a.expected_period_end},
            expected by {a.expected_report_by}.{" "}
            {a.state === "conflicting"
              ? "Expected figures conflict"
              : a.state === "overdue"
                ? "This condition is unknown; missing evidence in this app does not prove a late company filing."
                : "Inspect the saved evidence and your condition."}
          </p>
        ))}
      {!c.withheld && c.kind === "expiry" && (
        <p>
          No new figure was received. Your saved age limit now makes the
          condition unknown.
        </p>
      )}
      {!c.withheld &&
        c.kind !== "expiry" &&
        c.details.affected_conditions.map((a) => (
          <span className="change-value" key={a.condition_id}>
            {metrics[a.metric] || "Condition"}:{" "}
            {a.before == null ? "Unknown" : a.before + "%"} (
            {c.details.previous_period}) →{" "}
            {a.after == null ? "Unknown" : a.after + "%"} ({c.details.period})
            {a.role === "risk" && <> · {resultLabel(a)}</>}
          </span>
        ))}
      {(!c.withheld ? c.details.affected_events || [] : []).map((e) => (
        <p key={e.condition_id}>
          {e.description}: {e.before?.replaceAll("_", " ") || "Unchecked"} →{" "}
          {e.after.replaceAll("_", " ")}
        </p>
      ))}
      <small>
        {c.withheld
          ? "Open the exact saved assessment to inspect its availability."
          : c.kind === "reporting"
            ? "Review the expected period, your chosen date and the available figure. The date transition makes no source or AI call."
            : c.kind === "event"
              ? "Review the event evidence and report deadline; an unknown outcome is not evidence of safety."
              : c.kind === "expiry"
                ? "Compare the last reported figure, its period end and your chosen limit."
                : c.kind === "coverage"
                  ? `Coverage: ${c.details.coverage_before} → ${c.details.coverage_after}`
                  : c.kind === "evidence"
                    ? "Review new source evidence; a numerical condition may still be met."
                    : "Compare each figure with your saved condition."}
      </small>
      <span className="text-button">
        {c.review_action === "reviewed"
          ? "Reviewed"
          : c.review_action === "unresolved"
            ? "Left unresolved"
            : "Review this change"}{" "}
        ↗
      </span>
    </button>
  );
}
