export function countedTone(sample) {
  if (!sample) return null;
  const counts = sample.counts || {};
  const positive = counts.positive || 0,
    neutral = (counts.neutral || 0) + (counts.mixed || 0),
    negative = counts.negative || 0,
    unclear = counts.unclear || 0;
  const total = positive + neutral + negative + unclear;
  return {
    positive,
    neutral,
    negative,
    unclear,
    total,
    selected: sample.selected ?? 0,
    relevant: sample.relevant ?? null,
    reconciled:
      sample.counted_groups == null || sample.counted_groups === total,
  };
}
export function newsSourceStatus(data) {
  const providers = (data.provider_status || []).filter(
    (row) => row.channel === "news",
  );
  const market = data.market?.status;
  const feeds = [...providers];
  if (market && !providers.some((row) => row.provider === "finnhub"))
    feeds.push({
      provider: "finnhub",
      label: "Finnhub",
      status: market.news_error
        ? "failed"
        : market.completed_at
          ? "ready"
          : "not_checked",
      message: market.news_error,
      checked_at: market.completed_at || market.last_attempt_at,
    });
  const failed = feeds.filter((row) =>
    ["failed", "blocked"].includes(row.status),
  );
  const social = (data.social_status || []).filter(
    (row) => row.enabled && row.error,
  );
  const latest = feeds
    .map((row) => row.checked_at)
    .filter((value) => value && Number.isFinite(Date.parse(value)))
    .sort((a, b) => Date.parse(b) - Date.parse(a))[0];
  return { feeds, failed, social, latest };
}
