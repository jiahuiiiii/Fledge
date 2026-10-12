const options = {
  timeZone: "Asia/Singapore",
  day: "numeric",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
};
const minuteFormat = new Intl.DateTimeFormat("en-GB", options);
const secondFormat = new Intl.DateTimeFormat("en-GB", {
  ...options,
  second: "2-digit",
});

// Presentation only. Calendar/reporting dates are deliberately not instants.
// Reject ambiguous timestamps instead of interpreting them in the browser's zone.
export function formatTimestamp(
  value,
  { fallback = "Not checked", seconds = false } = {},
) {
  if (
    !value ||
    (typeof value === "string" &&
      !/T\d{2}:\d{2}.*(?:Z|[+-]\d{2}:?\d{2})$/i.test(value))
  )
    return fallback;
  const parsed = value instanceof Date ? value : new Date(value);
  if (!Number.isFinite(parsed.getTime())) return fallback;
  return `${(seconds ? secondFormat : minuteFormat).format(parsed)} SGT`;
}

export function formatReportingAgeExplanation(explanation, age) {
  const saved = `Too old to assess: the period ended ${age?.period_end}. Your ${age?.max_report_age_days}-day limit expired at ${age?.expires_at}. The last figure and source are retained.`;
  if (explanation !== saved) return explanation;
  const local = formatTimestamp(age.expires_at, { fallback: null });
  return local ? explanation.replace(age.expires_at, local) : explanation;
}
