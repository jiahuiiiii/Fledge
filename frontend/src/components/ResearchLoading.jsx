import { useState } from "react";
const states = {
  queued: "Queued",
  running: "Working",
  ready: "Complete",
  partial: "Partial coverage",
  cached: "Cooling down",
  failed: "Needs attention",
  blocked: "Blocked",
  interrupted: "Interrupted",
};
export function ResearchProgressToggle({ run, error, onExpand }) {
  if (!run && !error) return null;
  const attention =
    error ||
    run?.steps.some((s) =>
      ["failed", "blocked", "partial", "interrupted"].includes(s.status),
    );
  return (
    <button
      className="progress-restore"
      type="button"
      onClick={onExpand}
      aria-expanded={false}
      title="Show research progress"
    >
      <svg
        width="16"
        height="16"
        viewBox="0 0 20 20"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.7"
        aria-hidden="true"
      >
        <path d="m5 7 5 5 5-5" />
      </svg>
      <span role="status">
        Progress
        {run?.active ? " · working" : attention ? " · needs attention" : ""}
      </span>
    </button>
  );
}
export default function ResearchLoading({ run, error, onCollapse }) {
  const [expanded, setExpanded] = useState(false);
  if (!run && !error) return null;
  const steps = run?.steps || [];
  const finished = steps.filter(
    (s) => !["running", "queued"].includes(s.status),
  ).length;
  const attention = steps.filter((s) =>
    ["failed", "blocked", "partial", "interrupted"].includes(s.status),
  ).length;
  const active = run?.active;
  const working = steps
    .filter((s) => s.status === "running")
    .map((s) => s.label);
  return (
    <section
      className={`research-loading ${active ? "is-active" : ""}`}
      aria-label="Research loading progress"
    >
      <div className="loading-overview">
        <div>
          <strong>
            {active
              ? "Updating your research"
              : attention
                ? "Research updated with gaps"
                : "Research check complete"}
          </strong>
          <p role="status">
            {error ||
              (active
                ? working.length
                  ? working.join(" · ")
                  : steps.find((s) => s.status === "queued")?.message ||
                    "Waiting for the next step"
                : `${finished} of ${steps.length} steps finished${attention ? ` · ${attention} need attention` : ""}`)}
          </p>
        </div>
        <div className="loading-actions">
          <span>
            {finished}/{steps.length}
          </span>
          <button
            className="text-button"
            aria-expanded={expanded}
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? "Hide details" : "View progress"}
          </button>
          <button
            type="button"
            className="collapse-progress"
            onClick={onCollapse}
            aria-label="Hide research progress"
            title="Hide research progress"
            aria-expanded={true}
          >
            <svg
              width="18"
              height="18"
              viewBox="0 0 20 20"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.7"
              aria-hidden="true"
            >
              <path d="m5 12 5-5 5 5" />
            </svg>
          </button>
        </div>
      </div>
      <div
        className="research-progress"
        role="progressbar"
        aria-label="Research steps finished"
        aria-valuemin={0}
        aria-valuemax={steps.length || 1}
        aria-valuenow={finished}
      >
        <span
          style={{
            width: `${steps.length ? (finished / steps.length) * 100 : 0}%`,
          }}
        />
      </div>
      {expanded && (
        <ol className="loading-steps">
          {steps.map((step) => (
            <li key={step.key} data-status={step.status}>
              <span className="step-indicator" aria-hidden="true">
                {step.status === "ready"
                  ? "✓"
                  : step.status === "queued"
                    ? "·"
                    : ""}
              </span>
              <div>
                <strong>{step.label}</strong>
                <span>{states[step.status]}</span>
                <p>{step.message}</p>
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
