import { useState } from "react";
import { researchStep } from "../lib/researchProgress";
import "./ResearchLoading.css";
function checkDate(value) {
  const parsed = new Date(value);
  return Number.isFinite(parsed.getTime())
    ? parsed.toLocaleString("en-GB", {
        day: "numeric",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
        timeZoneName: "short",
      })
    : null;
}
export function ResearchProgressToggle({ run, error, onExpand }) {
  if (!run && !error) return null;
  const attention =
    error ||
    run?.steps.some((s) => researchStep(s, run.saved_coverage).attention);
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
export default function ResearchLoading({
  run,
  error,
  onCollapse,
  hidden = false,
}) {
  const [expanded, setExpanded] = useState(false);
  if (!run && !error) return null;
  const steps = run?.steps || [];
  const finished = steps.filter(
    (s) => !["running", "queued"].includes(s.status),
  ).length;
  const attention = steps.filter(
    (s) => researchStep(s, run.saved_coverage).attention,
  ).length;
  const deferred = steps.filter((s) => s.status === "cached").length;
  const hasSaved = ["news", "reddit", "hackernews"].some(
    (k) => run?.saved_coverage?.[k] > 0,
  );
  const active = run?.active;
  const working = steps
    .filter((s) => s.status === "running")
    .map((s) => (s.batches ? `${s.label} · ${s.message}` : s.label));
  return (
    <div
      className="research-loading-collapse"
      data-hidden={hidden}
      aria-hidden={hidden || undefined}
      inert={hidden ? "" : undefined}
    >
      <div className="research-loading-clip">
        <section
          className={`research-loading ${active ? "is-active" : ""}`}
          aria-label="Research loading progress"
        >
          <div className="loading-overview">
            <div>
              <strong>
                {active
                  ? "Updating your research"
                  : hasSaved
                    ? "Saved research available"
                    : attention
                      ? "Research check finished with gaps"
                      : "Research check complete"}
              </strong>
              <p role="status">
                {error ||
                  (active
                    ? working.length
                      ? working.join(" · ")
                      : steps.find((s) => s.status === "queued")?.message ||
                        "Waiting for the next step"
                    : `${finished} of ${steps.length} steps finished${deferred ? ` · ${deferred} repeat checks skipped` : ""}${attention ? ` · ${attention} need attention` : ""}`)}
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
          {run?.saved_coverage && (
            <p className="fine" aria-label="Saved source counts">
              Available saved sources now: {run.saved_coverage.news} news
              reports (7 days) · {run.saved_coverage.reddit} Reddit
              posts/comments · {run.saved_coverage.hackernews} Hacker News
              comments ({run.saved_coverage.discussion_days}-day discussion
              window). Source counts, not analysed developments.
            </p>
          )}
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
          <div
            className="loading-details"
            data-hidden={!expanded}
            aria-hidden={!expanded || undefined}
            inert={!expanded ? "" : undefined}
          >
            <div className="research-loading-clip">
              <p className="fine">
                Saved results remain readable when a repeat check is skipped.
                Expand refresh details for timing and connection information.
              </p>
              <ol className="loading-steps">
                {steps.map((step) => {
                  const view = researchStep(step, run.saved_coverage);
                  const date = view.date && checkDate(view.date);
                  return (
                    <li key={step.key} data-status={view.state}>
                      <span className="step-indicator" aria-hidden="true">
                        {view.state === "ready"
                          ? "✓"
                          : step.status === "queued"
                            ? "·"
                            : ""}
                      </span>
                      <div>
                        <strong>{step.label}</strong>
                        <span>{view.label}</span>
                        {view.summary && (
                          <p className="loading-source-count">{view.summary}</p>
                        )}
                        {date && (
                          <time
                            className="loading-check-date"
                            dateTime={view.date}
                          >
                            {view.prior ? "Previous result" : "Checked"} ·{" "}
                            {date}
                          </time>
                        )}
                        {view.attention && view.prior && (
                          <p className="loading-check-warning">
                            The previous check reported a gap; this attempt did
                            not recheck it.
                          </p>
                        )}
                        {view.details ? (
                          <details>
                            <summary>
                              Refresh details
                              <span className="sr-only"> · {step.label}</span>
                            </summary>
                            {view.prior && (
                              <p>Previous result: {view.prior.message}</p>
                            )}
                            {checkDate(step.finished_at || step.started_at) && (
                              <p>
                                Refresh attempt ·{" "}
                                <time
                                  dateTime={step.finished_at || step.started_at}
                                >
                                  {checkDate(
                                    step.finished_at || step.started_at,
                                  )}
                                </time>
                              </p>
                            )}
                            <p>{step.message}</p>
                          </details>
                        ) : (
                          <p>{view.message}</p>
                        )}
                      </div>
                    </li>
                  );
                })}
              </ol>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
