const attentionStates = new Set([
  "failed",
  "blocked",
  "partial",
  "interrupted",
]);

export function researchStep(step, coverage) {
  const prior = step.status === "cached" ? step.previous_check : null;
  const off =
    step.key === "x" &&
    step.status === "blocked" &&
    step.optional_source_off === true;
  const attention =
    !off &&
    (attentionStates.has(step.status) || attentionStates.has(prior?.status));
  const terminal = !["queued", "running"].includes(step.status);
  const saved =
    terminal && coverage
      ? {
          market: [coverage.news, "news reports", 7],
          reddit: [coverage.reddit, "posts/comments", coverage.discussion_days],
          hackernews: [
            coverage.hackernews,
            "comments",
            coverage.discussion_days,
          ],
        }[step.key]
      : null;
  const known =
    saved &&
    Number.isInteger(saved[0]) &&
    saved[0] >= 0 &&
    [1, 7, 30].includes(saved[2]);
  const available = known && saved[0] > 0;
  const summary = known
    ? `${saved[0] ? `${saved[0]} saved ${saved[1]}` : `No saved ${saved[1]}`} in the ${saved[2]}-day window.`
    : off
      ? "X is an optional source."
      : null;
  const labels = {
    queued: "Queued",
    running: "Working",
    ready: "Checked",
    partial: "Partial coverage",
    failed: "Needs attention",
    blocked: "Blocked",
    interrupted: "Interrupted",
  };
  const label = off
    ? "Off"
    : attention && step.status === "cached"
      ? "Previous check needs attention"
      : available && !attention
        ? "Available"
        : step.status === "cached"
          ? prior?.status === "ready"
            ? "Previous check completed"
            : "Refresh skipped"
          : known && !available && step.status === "ready"
            ? "No saved matches"
            : labels[step.status] || step.status;
  return {
    attention,
    summary,
    label,
    prior,
    state: off
      ? "off"
      : attention
        ? "partial"
        : available
          ? "ready"
          : step.status,
    deferred: step.status === "cached",
    date:
      prior?.finished_at || (step.status === "ready" ? step.finished_at : null),
    message:
      step.status === "cached"
        ? prior?.message || "No new check was made."
        : step.message,
    details: step.status === "cached" || off || !!summary,
  };
}
