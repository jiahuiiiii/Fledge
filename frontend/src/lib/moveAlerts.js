export const causeName = {
  market: "Possible market connection",
  sector: "Possible sector connection",
  company: "Possible company connection",
  no_clear: "No clear cause found",
};

export function movePercent(value, points = false) {
  if (value == null || value === "" || typeof value === "boolean")
    return "Unknown";
  const number = Number(value);
  if (!Number.isFinite(number)) return "Unknown";
  const rounded = Math.abs(number) < 0.05 ? 0 : number;
  return `${rounded > 0 ? "+" : rounded < 0 ? "−" : ""}${Math.abs(rounded).toFixed(1)}${points ? " points" : "%"}`;
}

export function moveSummary(detail) {
  return {
    title: detail.title,
    text:
      detail.explanation?.text ||
      "The price move crossed a rule. No verified explanation is saved yet.",
    alert: detail.preview
      ? "Preview · not sent to Telegram"
      : "Price-move alert",
  };
}
