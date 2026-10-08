const positive = (value) => {
  if (value == null || value === "" || typeof value === "boolean") return null;
  const n = Number(value);
  return Number.isFinite(n) && n > 0 ? n : null;
};
export function targetRange(targets, quote) {
  if (!targets) return null;
  const [low, mean, median, high] = ["low", "mean", "median", "high"].map((k) =>
    positive(targets[k]),
  );
  if (
    [low, mean, median, high].some((v) => v == null) ||
    low > high ||
    mean < low ||
    mean > high ||
    median < low ||
    median > high
  )
    return null;
  const current = positive(quote?.price);
  const bottom = Math.min(low, current ?? low),
    top = Math.max(high, current ?? high);
  const span = Math.max(top - bottom, top * 0.08);
  const min = bottom - span * 0.12,
    max = top + span * 0.12;
  return {
    low,
    mean,
    median,
    high,
    current,
    position: (value) => 6 + ((value - min) / (max - min)) * 88,
    change: (value) => (current == null ? null : (value / current - 1) * 100),
  };
}
export function targetChange(value) {
  if (value == null) return "Quote needed to compare";
  if (Math.abs(value) < 0.05) return "0.0% vs quote";
  return `${value > 0 ? "+" : "−"}${Math.abs(value).toFixed(1)}% ${value > 0 ? "upside" : "downside"}`;
}
