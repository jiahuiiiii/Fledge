// Plain progress for a newly added company's first data collection, shown as
// three stages. The AI news rating is a separate, optional step and is not
// counted here.
const WAITING = new Set(["queued", "running"]);

export const SETUP_STAGES = [
  {
    id: "basics",
    label: "Price and company details",
    keys: ["market", "prices", "targets", "multiples"],
  },
  {
    id: "filings",
    label: "Filings and financials",
    keys: ["filings", "disclosures"],
  },
  {
    id: "news",
    label: "News and discussions",
    keys: ["rss", "alpha_vantage", "reddit", "hackernews", "x"],
  },
];

function stageOf(key) {
  return (
    SETUP_STAGES.find((stage) => stage.keys.includes(key))?.id ||
    SETUP_STAGES[0].id
  );
}

export function setupProgress(run, opening) {
  if (opening || !run) return { stage: "opening", stages: [] };
  const steps = (run.steps || []).filter((step) => step.key !== "analysis");
  const stages = SETUP_STAGES.map(({ id, label }) => {
    const own = steps.filter((step) => stageOf(step.key) === id);
    const done = own.filter((step) => !WAITING.has(step.status)).length;
    const state = !run.active
      ? "done"
      : done === own.length
        ? "done"
        : done > 0 || own.some((step) => step.status === "running")
          ? "working"
          : "waiting";
    return { id, label, done, total: own.length, state };
  }).filter((stage) => stage.total > 0);
  const ready = !run.active || stages.every((stage) => stage.state === "done");
  return { stage: ready ? "ready" : "collecting", stages };
}
