import Select from "./Select";
import { roleLabel } from "../lib/conditionRoles";
import { useState } from "react";
import { ageLabel } from "./ReportingAge";
import { EventDefinitions } from "./EventConditions";
import ReviewDownload from "./ReviewDownload";
const labels = {
  met: "Condition met",
  not_met: "Condition not met",
  unknown: "Not enough evidence",
};
const names = {
  revenue_growth: "Revenue growth",
  operating_margin: "Operating margin",
};
const date = (value) =>
  new Date(value).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
const time = (value) =>
  new Date(value).toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
    timeZone: "UTC",
  });

export default function HistoryPanel({
  versions,
  renderEvaluation,
  renderComparison,
  renderEventReview,
  initialRecord,
}) {
  const [selected, setSelected] = useState(initialRecord || ""),
    [filter, setFilter] = useState("all");
  const records = versions.flatMap((version) => [
    { id: `revision:${version.id}`, version, evaluation: null },
    ...version.evaluations.map((evaluation, index) => ({
      id: evaluation.id,
      version,
      evaluation,
      assessmentNumber: version.evaluations.length - index,
    })),
    ...(version.event_reviews || []).map((eventReview, index, reviews) => ({
      id: `event:${eventReview.id}`,
      version,
      evaluation: null,
      eventReview,
      eventNumber: reviews.length - index,
    })),
    ...(version.evidence_reviews || []).map((comparison, index, reviews) => ({
      id: `comparison:${comparison.id}`,
      version,
      evaluation: null,
      comparison,
      comparisonNumber: reviews.length - index,
    })),
  ]);
  const filtered = records.filter(
    (r) =>
      filter === "all" ||
      (filter === "unreviewed"
        ? r.evaluation && !r.evaluation.review_action
        : r.evaluation?.review_action === "unresolved"),
  );
  const unavailable = selected && !records.some((r) => r.id === selected);
  const chosen = unavailable
    ? null
    : filtered.find((r) => r.id === selected) ||
      filtered.find((r) => r.evaluation) ||
      filtered[0];
  const unreviewed = records.filter(
    (r) => r.evaluation && !r.evaluation.review_action,
  ).length;
  return (
    <section className="history-page">
      <div className="row">
        <h2>Research history</h2>
        <span className="muted">{versions.length} revisions</span>
      </div>
      <p className="muted">
        Every saved definition, monitoring assessment, event check and AI
        comparison stays available. {unreviewed} assessments awaiting review.
      </p>
      <div className="field">
        <label htmlFor="history-filter">Show</label>
        <Select
          id="history-filter"
          value={filter}
          onChange={(e) => {
            setFilter(e.target.value);
            setSelected("");
          }}
        >
          <option value="all">
            All revisions, assessments and comparisons
          </option>
          <option value="unreviewed">Unreviewed assessments</option>
          <option value="unresolved">Left unresolved</option>
        </Select>
      </div>
      {!chosen ? (
        <div className="empty-history">
          <h3>
            {unavailable
              ? "This assessment is unavailable"
              : versions.length
                ? "No records in this view"
                : "No saved research yet"}
          </h3>
          <p>
            {unavailable
              ? "This link does not match a record in this company’s saved history. Choose All revisions, assessments and comparisons to browse available records."
              : versions.length
                ? "Other revisions, assessments and comparisons remain in All revisions, assessments and comparisons."
                : "Save a draft whenever you have reasoning worth revisiting."}
          </p>
        </div>
      ) : (
        <>
          <div className="field">
            <label htmlFor="historical-assessment">Record</label>
            <Select
              id="historical-assessment"
              value={chosen.id}
              onChange={(e) => {
                setSelected(e.target.value);
                const params = new URLSearchParams(location.search);
                params.set("evaluation", e.target.value);
                history.replaceState(null, "", `?${params}`);
              }}
            >
              {filtered.map((record) => (
                <option key={record.id} value={record.id}>
                  {record.eventReview
                    ? `Revision ${record.version.revision} · Event evidence check ${record.eventNumber} · ${date(record.eventReview.created_at)} · ${time(record.eventReview.created_at)} UTC`
                    : record.comparison
                      ? `Revision ${record.version.revision} · AI comparison ${record.comparisonNumber} · ${date(record.comparison.created_at)} · ${time(record.comparison.created_at)} UTC`
                      : record.evaluation
                        ? `Revision ${record.version.revision} · ${date(record.evaluation.manifest.assessed_at || record.evaluation.manifest.cutoff)} · ${labels[record.evaluation.outcome]} · Assessment ${record.assessmentNumber} · ${time(record.evaluation.manifest.assessed_at || record.evaluation.manifest.cutoff)} UTC`
                        : `Revision ${record.version.revision} · ${record.version.status} · saved definition`}
                </option>
              ))}
            </Select>
          </div>
          <div className="historical-note">
            <span className="section-label">
              SAVED REASONING · REVISION {chosen.version.revision} ·{" "}
              {chosen.version.status.toUpperCase()}
            </span>
            <h3>{chosen.version.question}</h3>
            <p>
              {chosen.version.reasoning ||
                "No reasoning was recorded in this draft."}
            </p>
          </div>
          <ReviewDownload
            version={chosen.version}
            evaluation={chosen.evaluation}
            comparison={chosen.comparison}
            eventReview={chosen.eventReview}
          />
          {chosen.eventReview ? (
            renderEventReview(chosen.eventReview, chosen.version)
          ) : chosen.comparison ? (
            <>
              {renderComparison(chosen.comparison, chosen.version)}
              {chosen.comparison.evaluation_id && (
                <button
                  className="text-button"
                  onClick={() => {
                    setSelected(chosen.comparison.evaluation_id);
                    const params = new URLSearchParams(location.search);
                    params.set("evaluation", chosen.comparison.evaluation_id);
                    history.replaceState(null, "", `?${params}`);
                  }}
                >
                  Open the linked numerical assessment ↗
                </button>
              )}
            </>
          ) : chosen.evaluation ? (
            renderEvaluation(chosen.evaluation, chosen.version, true)
          ) : (
            <div className="revision-definition">
              <h3>Saved conditions</h3>
              <EventDefinitions events={chosen.version.events} />
              {chosen.version.conditions.length ? (
                chosen.version.conditions.map((c) => (
                  <p key={c.condition_id}>
                    {roleLabel(c)} · {names[c.metric]}{" "}
                    {c.operator === ">=" ? "at least" : "at most"} {c.threshold}
                    % · reported{" "}
                    {c.period_type === "annual" ? "year" : "quarter"} ·{" "}
                    {ageLabel(c)}
                  </p>
                ))
              ) : (
                <p>No numerical conditions were defined.</p>
              )}
              <p className="fine">
                {chosen.version.evaluations.length
                  ? "This is the saved definition. Select an assessment to see the evidence checked against it."
                  : "Not evaluated. Saving or archiving a definition does not create an assessment."}
              </p>
            </div>
          )}
        </>
      )}
    </section>
  );
}
