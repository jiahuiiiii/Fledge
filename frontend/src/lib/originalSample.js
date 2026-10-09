/** The exact visible selected sample, not the comparison pool or a new retrieval. */
export function originalSample(analysis, channel, platform) {
  if (
    !analysis ||
    analysis.withheld ||
    !["all", "news", "social"].includes(channel)
  )
    return [];
  return (analysis.sources || [])
    .filter(
      (s) =>
        !s.comparison_only &&
        ["news", "social"].includes(s.kind) &&
        (channel === "all" || s.kind === channel) &&
        (channel === "all" ||
          !platform ||
          (s.platform || "reddit") === platform),
    )
    .slice()
    .sort(
      (a, b) =>
        Date.parse(b.published_at) - Date.parse(a.published_at) ||
        a.id.localeCompare(b.id),
    );
}
