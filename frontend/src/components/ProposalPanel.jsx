import { formatTimestamp } from "../lib/dateTime";
import { Button } from "./ui";
import { roleLabel, comparisonMeaning } from "../lib/conditionRoles";
import { useState } from "react";
import { splitSuggestions, addedConditionIds } from "../lib/proposals";
import { EventSchedule } from "./EventConditions";
import { ReportExpectationText } from "./ReportExpectation";
const stamp = (value) => formatTimestamp(value, { fallback: "Not recorded" });
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
const validNumber = (v) =>
  String(v ?? "").trim() !== "" && Number.isFinite(Number(v));
const kindLabel = (p) =>
  p.kind === "numeric"
    ? "Number to watch"
    : p.kind === "event"
      ? "Event to watch"
      : "Reword your question";

export default function ProposalPanel({
  embedded = false,
  proposals = [],
  current,
  busy,
  unavailableReason,
  onGenerate,
  onReview,
  onWatch,
  startingPoint = () => null,
  onReject,
  onSource,
  onOpen,
}) {
  const [thresholds, setThresholds] = useState({});
  const { open, past } = splitSuggestions(proposals);
  const usable = open.filter((p) => !p.source_unavailable);
  // A suggestion that only adds a check can start watching in one step.
  const watchable = (p) =>
    onWatch &&
    !p.source_unavailable &&
    p.operation === "add" &&
    p.kind !== "reasoning";
  const valueOf = (p) => thresholds[p.id] ?? startingPoint(p)?.threshold ?? "";
  const ready = (p) => p.kind !== "numeric" || validNumber(valueOf(p));
  const effective = (list) =>
    Object.fromEntries(list.map((p) => [p.id, valueOf(p)]));
  const addable = usable.filter(watchable);
  function card(p, { actions = false } = {}) {
    const field = p.kind === "numeric" ? "conditions" : "events";
    const before =
      p.kind === "reasoning"
        ? p.base
        : p.base[field]?.find((c) => c.condition_id === p.target_condition_id);
    const after = p.kind === "reasoning" ? p.proposed : p.proposed?.definition;
    const adding = p.operation === "add";
    const inputId = `threshold-${p.id}`;
    return (
      <article className="proposal-card" key={p.id}>
        <div className="row proposal-heading">
          <span className="section-label">
            {actions
              ? kindLabel(p).toUpperCase()
              : `${p.status.toUpperCase()} · ${kindLabel(p).toUpperCase()}`}
          </span>
        </div>
        <p className="proposal-rationale">{p.rationale}</p>
        {!p.source_unavailable && (
          <div className="proposal-diff">
            {!adding && (
              <div>
                <span className="section-label">Your current idea</span>
                <DefinitionText value={before} kind={p.kind} />
              </div>
            )}
            <div>
              <span className="section-label">
                {adding ? "What it would watch" : `Suggested ${p.operation}`}
              </span>
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
            ? "Your idea changed after this was made, so it can no longer be applied. Ask for fresh suggestions if you still want it."
            : ""}
        </p>
        {p.citations.map((c, i) => (
          <details className="proposal-source" key={i}>
            <summary>Supporting passage {i + 1}</summary>
            <blockquote>{c.quote}</blockquote>
            <Button variant="link" onClick={() => onSource(c.source_id)}>
              Inspect suggestion source ↗
            </Button>
          </details>
        ))}
        {actions && !p.source_unavailable && (
          <div className="proposal-watch">
            {watchable(p) && p.kind === "numeric" && (
              <label className="field" htmlFor={inputId}>
                Your threshold (%)
                <input
                  id={inputId}
                  type="number"
                  step="any"
                  inputMode="decimal"
                  placeholder="e.g. 10"
                  value={valueOf(p)}
                  onChange={(e) =>
                    setThresholds({ ...thresholds, [p.id]: e.target.value })
                  }
                />
              </label>
            )}
            {watchable(p) && p.kind === "numeric" && startingPoint(p) && (
              <small>
                Latest reported: {startingPoint(p).value}% (
                {startingPoint(p).period}). {startingPoint(p).threshold}% is a
                starting point just below it; change it to your own.
              </small>
            )}
            <div className="row">
              {watchable(p) ? (
                <Button
                  variant="primary"
                  size="sm"
                  disabled={busy || !ready(p)}
                  onClick={() => onWatch([p], effective([p]))}
                >
                  Watch this
                </Button>
              ) : (
                <Button
                  variant="primary"
                  size="sm"
                  disabled={busy || !p.candidate}
                  onClick={() => onReview([p])}
                >
                  {p.kind === "reasoning"
                    ? "Use this wording"
                    : "Review this change"}
                </Button>
              )}
              <Button
                variant="link"
                className="proposal-reject"
                disabled={busy}
                onClick={() => onReject(p.id)}
              >
                Not now
              </Button>
            </div>
            <small>
              {watchable(p)
                ? p.kind === "numeric"
                  ? "Saves this to your view and starts watching once you enter a threshold. You can change it later with Edit."
                  : "Saves it to your view and starts watching, using the standard dates (past week to 90 days ahead). Change anything later with Edit."
                : "Opens your question and reasoning with this filled in. Nothing is saved until you save."}
            </small>
          </div>
        )}
        {!actions && p.status === "stale" && (
          <Button
            variant="link"
            className="proposal-reject"
            disabled={busy}
            onClick={() => onReject(p.id)}
          >
            Dismiss
          </Button>
        )}
        {!actions && p.status === "approved" && p.accepted_version_id && (
          <Button variant="link" onClick={() => onOpen(p.accepted_version_id)}>
            Open the accepted revision ↗
          </Button>
        )}
      </article>
    );
  }
  return (
    <section
      className={embedded ? "proposal-panel embedded" : "proposal-panel"}
      aria-label="Reviewable suggestions"
    >
      {!embedded && (
        <>
          <h3>Make your idea testable</h3>
          <p className="fine">
            Compare suggested changes with your original idea. Nothing changes
            until you choose a suggestion and confirm it.
          </p>
        </>
      )}
      <button
        className={embedded ? "text-button" : "secondary"}
        onClick={onGenerate}
        disabled={busy || !!unavailableReason || current?.status === "archived"}
      >
        {busy
          ? "Working…"
          : current
            ? embedded
              ? "Suggest things to watch (AI)"
              : "Suggest checks for my idea"
            : "Suggest a starting idea"}
      </button>
      {unavailableReason && <p className="fine">{unavailableReason}</p>}
      {!embedded && (
        <details className="proposal-method">
          <summary>How suggestions work</summary>
          <p className="fine">
            Suggestions use AI and the available sources. Thresholds and dates
            are assumptions for you to choose or edit. Checks can describe a
            requirement or a risk. A request uses the shared AI budget; the
            selected sources cannot establish that every important risk has been
            detected.
          </p>
        </details>
      )}
      {open.length > 0 && (
        <p className="fine">
          {open.length} suggestion{open.length === 1 ? "" : "s"}. Using one
          saves a new version of your idea, so use the ones you want together
          {addable.length > 1 ? " with “Watch all”" : ""}; the rest then need a
          fresh request.
        </p>
      )}
      {addable.length > 1 && (
        <Button
          variant="primary"
          disabled={busy || !addable.every(ready)}
          onClick={() => onWatch(addable, effective(addable))}
        >
          Watch all {addable.length} checks
        </Button>
      )}
      {open.map((p) => card(p, { actions: true }))}
      {past.length > 0 && (
        <details className="past-proposals">
          <summary>Earlier suggestions ({past.length})</summary>
          {past.map((p) => card(p))}
        </details>
      )}
    </section>
  );
}
