export const ageLabel = (c) =>
  c.max_report_age_days == null || String(c.max_report_age_days).trim() === ""
    ? "No age limit"
    : `Maximum reporting age: ${c.max_report_age_days} ${Number(c.max_report_age_days) === 1 ? "day" : "days"}`;

export default function ReportingAge({
  condition,
  fundamentals,
  cutoff,
  recorded,
}) {
  const fact = fundamentals?.find(
    (f) =>
      f.metric === condition.metric &&
      f.period_type === (condition.period_type || "quarter"),
  );
  if (!fact?.period_end)
    return (
      <small className="age-preview">
        No compatible period end available to preview this age limit.
      </small>
    );
  const end = new Date(fact.period_end).getTime();
  const clock = recorded ? new Date(cutoff).getTime() : Date.now();
  const days = Math.floor(clock / 86400000) - Math.floor(end / 86400000);
  const limit = Number(condition.max_report_age_days);
  const valid =
    String(condition.max_report_age_days ?? "").trim() &&
    Number.isInteger(limit) &&
    limit >= 1 &&
    limit <= 3650;
  const deadline = valid
    ? new Date(end + (limit + 1) * 86400000).toISOString().slice(0, 10)
    : null;
  return (
    <small className="age-preview">
      Period ended {fact.period_end} · {days} days ago
      {recorded ? " at the sample date" : " (UTC)"}.
      {valid
        ? ` ${days > limit ? "Already too old under this limit." : "Within your limit."} ${days > limit ? "Became" : "Becomes"} too old on ${deadline} at 00:00 UTC.`
        : String(condition.max_report_age_days ?? "").trim()
          ? " Enter a whole number from 1 to 3650 days."
          : " No age limit selected."}
    </small>
  );
}
