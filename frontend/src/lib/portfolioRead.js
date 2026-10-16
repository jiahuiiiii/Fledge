// Small helpers for "Your list today" (tested in portfolioRead.test.js).
export function pctText(value) {
  if (value == null || Number.isNaN(value)) return "No price";
  const sign = value > 0 ? "+" : value < 0 ? "−" : "";
  return `${sign}${Math.abs(value).toFixed(1)}%`;
}

// Bar length relative to the biggest move on the list, never invisible.
export function barWidth(value, scale) {
  if (value == null || !scale) return "0%";
  return `${Math.max(4, Math.round((Math.abs(value) / scale) * 100))}%`;
}

export function toneLine(tone = {}) {
  const parts = [
    [tone.positive, "good"],
    [tone.negative, "bad"],
    [tone.mixed, "mixed"],
    [tone.neutral, "neutral"],
  ]
    .filter(([n]) => n)
    .map(([n, word]) => `${n} ${word}`);
  return parts.length
    ? `News across your list: ${parts.join(", ")}.`
    : "No news reading saved for these companies yet.";
}
