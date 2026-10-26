// The idea page in one glance: is anything being watched, and what (owner
// feedback 20 Oct 2026: the page never said whether it was doing anything).
import { resultLabel } from "./conditionRoles.js";

const METRICS = {
  revenue_growth: "Revenue growth",
  operating_margin: "Operating margin",
};

const EVENT_STATES = {
  confirmed: "Happened",
  risk_reported: "Risk reported",
  denied_report: "A report denies it",
  conflicting: "Reports conflict",
  deadline_unconfirmed: "Deadline passed, not confirmed",
  not_started: "Not started yet",
};

export function watchItems(version, evaluation) {
  if (!version) return [];
  const watching = version.status === "monitoring";
  const points = evaluation?.event_results || [];
  const results = evaluation?.results || [];
  const idle = watching ? "Not checked yet" : "Not watching";
  return [
    ...(version.events || []).map((e) => {
      const point = points.find((p) => p.condition_id === e.condition_id);
      return {
        key: e.condition_id,
        type: e.role === "risk" ? "Risk" : "Event",
        label: e.description,
        state: point
          ? EVENT_STATES[point.state || point.status] || "Not confirmed yet"
          : idle,
      };
    }),
    ...(version.conditions || []).map((c) => {
      const result = results.find((r) => r.condition_id === c.condition_id);
      const comparison = c.operator === "<=" ? "at most" : "at least";
      return {
        key: c.condition_id,
        type: c.role === "risk" ? "Risk" : "Number",
        label: `${METRICS[c.metric] || c.metric} ${comparison} ${c.threshold}%`,
        state: result ? resultLabel({ ...result, role: c.role }) : idle,
      };
    }),
  ];
}

export function statusLine(version, evaluation) {
  if (!version) return "No idea saved yet.";
  const count =
    (version.events?.length || 0) + (version.conditions?.length || 0);
  const things = `${count} thing${count === 1 ? "" : "s"}`;
  if (version.status === "archived") return "Archived. Not watching.";
  if (version.status !== "monitoring")
    return count
      ? `Not watching yet. Approve the ${things} below in Edit to start alerts.`
      : "Not watching yet. Add something to watch in Edit, then approve it.";
  return evaluation
    ? `Watching ${things}. Last checked ${new Date(evaluation.created_at).toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "Asia/Singapore" })} SGT.`
    : `Watching ${things}. Waiting for the first check.`;
}
