// Adapted from Kestrel thesisDiff.js: preserve condition identities through edits.
// Replaces its multi-request mutation plan with one atomic revision document.
import { eventWindows } from "./eventWindows.js";
import { reportExpectationPayload } from "./reportExpectation.js";

export const validConditions = (rows) =>
  (rows || []).filter(
    (c) =>
      c.value !== "" &&
      c.value != null &&
      String(c.value).trim() !== "" &&
      Number.isFinite(Number(c.value)),
  );
export function revisionPayload(form, status) {
  const conditions = validConditions(form.conditions);
  if (conditions.length !== form.conditions.length)
    throw new Error(
      "Enter a finite number for each condition, or remove its row.",
    );
  for (const c of conditions) {
    if (
      c.max_report_age_days != null &&
      String(c.max_report_age_days).trim() !== "" &&
      (!Number.isInteger(Number(c.max_report_age_days)) ||
        Number(c.max_report_age_days) < 1 ||
        Number(c.max_report_age_days) > 3650)
    )
      throw new Error(
        "Use a whole number from 1 to 3650 days, or leave the age limit blank.",
      );
  }
  const events = form.events || [];
  for (const e of events) {
    if (
      e.description.trim().length < 5 ||
      e.evidence_requirement.trim().length < 5 ||
      !e.window_start ||
      !e.deadline ||
      e.deadline < e.window_start
    )
      throw new Error(
        "Describe each event and its evidence requirement (at least five characters each), then choose an ordered date window, or remove the event.",
      );
  }
  for (const event of events) {
    if (event.repeat_months) eventWindows(event);
  }
  return {
    events: events.map((e) => ({
      ...e,
      description: e.description.trim(),
      evidence_requirement: e.evidence_requirement.trim(),
    })),
    expected_revision: form.revision,
    question: form.question.trim(),
    reasoning: form.reasoning.trim(),
    status,
    conditions: conditions.map((c) => ({
      ...reportExpectationPayload(c),
      condition_id: c.id,
      metric: c.metric,
      role: c.role || "required",
      operator: c.operator,
      threshold: String(c.value),
      unit: "percent",
      basis: "reported",
      period_type: c.period_type || "quarter",
      max_report_age_days:
        c.max_report_age_days == null ||
        String(c.max_report_age_days).trim() === ""
          ? null
          : Number(c.max_report_age_days),
    })),
  };
}
