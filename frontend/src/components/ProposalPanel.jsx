import Checkbox from "./Checkbox";
import { roleLabel, comparisonMeaning } from "../lib/conditionRoles";
import { useState } from "react";
import { EventSchedule } from "./EventConditions";
import { ReportExpectationText } from "./ReportExpectation";
const stamp = (value) =>
  new Date(value).toLocaleString("en-GB", {
    timeZone: "UTC",
    dateStyle: "medium",
    timeStyle: "short",
  }) + " UTC";
const metrics = {
  revenue_growth: "Revenue growth",
  operating_margin: "Operating margin",
};
export function DefinitionText({ value, kind }) {
  if (!value) return <p className="fine">Not defined</p>;
  if (kind === "reasoning")
    return (
      <>
        <strong>{value.question}</strong>
        <p>{value.reasoning || "No reasoning yet"}</p>
      </>
    );
  if (kind === "numeric")
    return (
      <>
        <p>
          {roleLabel(value)} · {metrics[value.metric]} {value.operator}{" "}
          {value.threshold == null
            ? "Choose your threshold"
            : `${value.threshold}%`}{" "}
          · {value.period_type} ·{" "}
          {value.max_report_age_days == null
            ? "No reporting-age limit"
            : `Maximum ${value.max_report_age_days} days since period end`}
        </p>
        <p className="fine">{comparisonMeaning(value)}</p>
        <ReportExpectationText condition={value} />
      </>
    );
  return (
    <>
      <strong>
        {value.role === "risk" ? "Risk to watch" : "Required event"} ·{" "}
        {value.description}
      </strong>
      <p>{value.evidence_requirement}</p>
      <EventSchedule event={value} />
      <p className="fine">
        {value.date_basis === "event_occurrence"
          ? "Event happened"
          : "Reports published"}{" "}
        {value.window_start || "Choose start"} through{" "}
        {value.deadline || "Choose deadline"}.{" "}
        {value.date_basis === "event_occurrence"
          ? "An explicit source-stated calendar date is required; later reports may qualify."
          : "Inclusive UTC publication dates; they do not establish when the event happened."}
      </p>
    </>
  );
}
export default function ProposalPanel({
  proposals = [],
  current,
  busy,
  unavailableReason,
  onGenerate,
  onReview,
  onReject,
  onSource,
  onOpen,
}) {
  const [selected, setSelected] = useState([]);
  const pending = proposals.filter((p) => p.status === "pending"),
    old = proposals.filter((p) => p.status !== "pending");
  function card(p, index) {
    const field = p.kind === "numeric" ? "conditions" : "events";
    const before =
      p.kind === "reasoning"
        ? p.base
        : p.base[field]?.find((c) => c.condition_id === p.target_condition_id);
    const after = p.kind === "reasoning" ? p.proposed : p.proposed?.definition;
    return (
      <article className="proposal-card" key={p.id}>
        <div className="row proposal-heading">
          <span className="section-label">
            {p.status.toUpperCase()} ·{" "}
            {p.kind === "numeric"
              ? "NUMERICAL CHECK"
              : p.kind === "event"
                ? "EVENT CHECK"
                : "REASONING"}
          </span>
          {p.status === "pending" && (
            <label className="proposal-choice">
              <Checkbox
                aria-label={`Select suggestion ${index + 1}`}
                checked={selected.includes(p.id)}
                disabled={busy || p.source_unavailable}
                onChange={(e) =>
                  setSelected(
                    e.target.checked
                      ? [...selected, p.id]
                      : selected.filter((id) => id !== p.id),
                  )
                }
              />{" "}
              Select
            </label>
          )}
        </div>
        <p className="proposal-rationale">{p.rationale}</p>
        {!p.source_unavailable && (
          <div className="proposal-diff">
            <div>
              <span className="section-label">Your current idea</span>
              <DefinitionText value={before} kind={p.kind} />
            </div>
            <div>
              <span className="section-label">Suggested {p.operation}</span>
              <DefinitionText
                value={p.operation === "remove" ? null : after}
                kind={p.kind}
              />
              {p.operation === "remove" && (
                <p>This condition would be removed.</p>
              )}
            </div>
          </div>
        )}
        <p className="fine">
          {p.base_version_id
            ? `Based on revision ${p.base.expected_revision}`
            : "Starting idea · nothing saved yet"}{" "}
          · Sources through {stamp(p.cutoff)}.{" "}
          {p.status === "stale"
            ? "The idea or source snapshot changed. Request fresh suggestions before applying this change."
            : ""}
        </p>
        {p.citations.map((c, i) => (
          <details className="proposal-source" key={i}>
            <summary>Supporting passage {i + 1}</summary>
            <blockquote>{c.quote}</blockquote>
            <button
              className="text-button"
              onClick={() => onSource(c.source_id)}
            >
              Inspect suggestion source ↗
            </button>
          </details>
        ))}
        {p.status === "pending" || p.status === "stale" ? (
          <button
            className="text-button proposal-reject"
            disabled={busy}
            onClick={() => onReject(p.id)}
          >
            Reject suggestion
          </button>
        ) : (
          p.accepted_version_id && (
            <button
              className="text-button"
              onClick={() => onOpen(p.accepted_version_id)}
            >
              Open the accepted revision ↗
            </button>
          )
        )}
      </article>
    );
  }
  const chosen = pending.filter(
    (p) => selected.includes(p.id) && !p.source_unavailable,
  );
  return (
    <section className="proposal-panel" aria-label="Reviewable suggestions">
      <h3>Make your idea testable</h3>
      <p className="fine">
        Compare suggested changes with your original idea. Nothing changes until
        you choose a suggestion, review it and save.
      </p>
      <button
        className="secondary"
        onClick={onGenerate}
        disabled={busy || !!unavailableReason || current?.status === "archived"}
      >
        {busy
          ? "Working…"
          : current
            ? "Suggest checks for my idea"
            : "Suggest a starting idea"}
      </button>
      {unavailableReason && <p className="fine">{unavailableReason}</p>}
      <details className="proposal-method">
        <summary>How suggestions work</summary>
        <p className="fine">
          Suggestions use AI and the available sources. Thresholds and dates are
          assumptions for you to choose or edit. Checks can describe a
          requirement or a risk. A request uses the shared AI budget; the
          selected sources cannot establish that every important risk has been
          detected.
        </p>
      </details>
      {pending.map(card)}
      {chosen.length > 0 && (
        <button
          className="primary"
          disabled={busy}
          onClick={() => onReview(chosen)}
        >
          Review {chosen.length} selected suggestion
          {chosen.length === 1 ? "" : "s"}
        </button>
      )}
      {old.length > 0 && (
        <details className="past-proposals">
          <summary>Previous suggestions ({old.length})</summary>
          {old.map(card)}
        </details>
      )}
    </section>
  );
}
