export const sourceScopes = ["news", "reddit", "hackernews", "x"];

export const sourceExclusionLabels = {
  exact_duplicate: "Exact duplicate text",
  no_complete_passages: "No complete passage to read",
  no_complete_body_passages: "No complete comment body to read",
  required_context_unavailable: "Required reply context unavailable",
};

export function sourceCoverage(analysis) {
  const coverage = analysis?.coverage || {};
  const fullPolicy = coverage.selection?.policy === "sentiment-all-eligible-1";
  const scopes = sourceScopes.map((scope) => {
    const summary =
      scope === "news"
        ? analysis?.summary?.news
        : analysis?.summary?.social_platforms?.[scope] ||
          (scope === "reddit" ? analysis?.summary?.social : null);
    const candidates =
      coverage.selection?.scopes?.[scope]?.candidates ??
      (scope === "news"
        ? coverage.available_news
        : coverage.social_platforms?.[scope]);
    const classified = (analysis?.items || []).filter((item) => {
      const source = analysis.sources?.find(
        (source) => source.id === item.source_id,
      );
      return scope === "news"
        ? item.channel === "news"
        : item.channel === "social" && (source?.platform || "reddit") === scope;
    });
    const analysed = summary?.selected ?? classified.length;
    const excluded = coverage.selection?.scopes?.[scope]?.excluded || {};
    const excludedCount = Object.values(excluded).reduce(
      (sum, n) => sum + n,
      0,
    );
    return {
      scope,
      tone: summary?.tone,
      candidates: Number.isInteger(candidates) ? candidates : null,
      analysed,
      relevant: summary?.relevant ?? 0,
      unrelated: classified.filter((item) => item.relevance === "unrelated")
        .length,
      unclear: classified.filter((item) => item.relevance === "unclear").length,
      excluded,
      excludedCount,
      unanalysed: Number.isInteger(candidates)
        ? Math.max(0, candidates - analysed - excludedCount)
        : null,
    };
  });
  const total = (key) =>
    scopes.every((scope) => scope[key] != null)
      ? scopes.reduce((sum, scope) => sum + scope[key], 0)
      : null;
  return {
    complete: fullPolicy && scopes.every((scope) => scope.unanalysed === 0),
    scopes,
    candidates: total("candidates"),
    analysed: total("analysed"),
    relevant: total("relevant"),
    unrelated: total("unrelated"),
    unclear: total("unclear"),
    excluded: total("excludedCount"),
    unanalysed: total("unanalysed"),
  };
}
