/** The exact visible selected sample, not the comparison pool or a new retrieval. */
export function originalSample(analysis, channel, platform) {
  if (!analysis || analysis.withheld || !["news", "social"].includes(channel))
    return [];
  return (analysis.sources || [])
    .filter(
      (s) =>
        !s.comparison_only &&
        s.kind === channel &&
        (!platform || (s.platform || "reddit") === platform),
    )
    .slice()
    .sort(
      (a, b) =>
        Date.parse(b.published_at) - Date.parse(a.published_at) ||
        a.id.localeCompare(b.id),
    );
}
