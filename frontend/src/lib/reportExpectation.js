export function reportExpectationPayload(condition) {
  const end = condition.expected_period_end || "",
    due = condition.expected_report_by || "";
  if (!end && !due) return {};
  if (!end || !due)
    throw new Error(
      "Choose both the required period end and expected-by date, or clear both.",
    );
  for (const value of [end, due]) {
    if (
      !/^\d{4}-\d{2}-\d{2}$/.test(value) ||
      !Number.isFinite(Date.parse(value)) ||
      new Date(value).toISOString().slice(0, 10) !== value
    )
      throw new Error(
        "Use valid calendar dates for the reporting expectation.",
      );
  }
  if (
    due < end ||
    due === "9999-12-31" ||
    (new Date(due) - new Date(end)) / 86400000 > 3650
  )
    throw new Error(
      "Use an expected-by date on or after the period end, within 3650 days.",
    );
  return { expected_period_end: end, expected_report_by: due };
}
export const reportStateLabels = {
  waiting: "Waiting for the expected figures",
  available: "Required reporting period available",
  conflicting: "Expected figures conflict",
  withheld: "Reporting evidence unavailable",
  overdue: "Expected figures missing",
};
