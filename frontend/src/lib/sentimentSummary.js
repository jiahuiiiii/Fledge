export function sentimentSummaryLabel(sample) {
  if (!sample) return "No analysed texts";
  const counts = sample.counts || {};
  const usable = ["positive", "negative", "mixed", "neutral"].reduce(
    (n, key) => n + (counts[key] || 0),
    0,
  );
  const unclear = counts.unclear || 0;
  const majority =
    sample.tone === "positive leaning"
      ? counts.positive
      : sample.tone === "negative leaning"
        ? counts.negative
        : null;
  const amount =
    majority == null
      ? `${usable} clear readings`
      : `${majority} of ${usable} clear readings`;
  return `${["mixed", "mixed / balanced"].includes(sample.tone) ? "Mixed tone" : sample.tone} · ${amount}${unclear ? ` · ${unclear} unclear` : ""}`;
}

export function priceComparisonText(value) {
  if (value.status !== "compared") return null;
  const amount = Number(value.amount).toLocaleString("en-US", {
    maximumFractionDigits: 4,
  });
  const close = Number(value.reference.close).toLocaleString("en-US", {
    maximumFractionDigits: 4,
  });
  const percent = Math.abs(Number(value.difference_percent)).toFixed(1);
  return `$${amount} target · ${percent}% ${value.relation === "equal" ? "difference from" : value.relation} the $${close} saved close (${value.reference.date})`;
}

export const priceUnavailableReasons = {
  unverified_post_time:
    "The recorded time is a feed update; the original post time is unverified.",
  no_saved_price_at_post_time:
    "No price capture was saved on or before the post time.",
  no_compatible_saved_price:
    "No compatible USD price capture is available from the post time.",
  price_access_unavailable: "Saved price access is unavailable.",
  no_completed_close: "The saved capture has no completed daily close.",
  saved_close_too_old: "The saved close is more than seven calendar days old.",
  not_comparable_target:
    "This amount is not a supported, directly attributed share-price target.",
};
