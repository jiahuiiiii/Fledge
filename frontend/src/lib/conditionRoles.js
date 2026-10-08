export const roleLabel = (condition) =>
  condition.role === "risk" ? "Risk to watch" : "Requirement";
export const resultLabel = (result) =>
  result.role === "risk"
    ? {
        met: "Risk threshold not reached",
        not_met: "Risk threshold reached",
        unknown: "Not enough evidence",
      }[result.outcome]
    : {
        met: "Condition met",
        not_met: "Condition not met",
        unknown: "Not enough evidence",
      }[result.outcome];

export function comparisonMeaning(condition) {
  const comparison = condition.operator === "<=" ? "at most" : "at least";
  const threshold =
    condition.threshold == null
      ? "your chosen threshold"
      : `${condition.threshold}%`;
  return condition.role === "risk"
    ? `Flags a risk when the reported figure is ${comparison} ${threshold}, including equality.`
    : `The reported figure must be ${comparison} ${threshold}, including equality.`;
}
