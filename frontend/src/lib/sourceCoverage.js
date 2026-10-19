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
    // Saved totals that counted an unavailable source are withheld by the server.
    const withheld = analysis?.withheld_summaries?.[scope] ?? null;
    const analysed = summary?.selected ?? classified.length;
    const excluded = coverage.selection?.scopes?.[scope]?.excluded || {};
    const excludedCount = Object.values(excluded).reduce(
      (sum, n) => sum + n,
      0,
    );
    return {
      scope,
      tone: summary?.tone,
      sentimentSummary: summary,
      candidates: Number.isInteger(candidates) ? candidates : null,
      analysed,
      relevant:
        summary?.relevant ??
        (withheld == null
          ? 0
          : classified.filter((item) => item.relevance === "relevant").length),
      unrelated: classified.filter((item) => item.relevance === "unrelated")
        .length,
      unclear: classified.filter((item) => item.relevance === "unclear").length,
      quickSkipped: classified.filter((item) => item.prefilter).length,
      excluded,
      excludedCount,
      withheld,
      unanalysed: Number.isInteger(candidates)
        ? Math.max(0, candidates - analysed - excludedCount - (withheld || 0))
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
    quickSkipped: total("quickSkipped"),
    excluded: total("excludedCount"),
    unanalysed: total("unanalysed"),
  };
}

// Plain-language note for a reading shown without its unavailable sources.
export function withheldSourcesNote(analysis) {
  const count = analysis?.withheld_sources || 0;
  if (!count) return null;
  return `${count} saved ${count === 1 ? "source is" : "sources are"} no longer available, so ${count === 1 ? "its interpretation is" : "their interpretations are"} not shown. Tone totals that counted ${count === 1 ? "it" : "them"} are withheld; the remaining sources are unaffected.`;
}

export function sampleWithheld(analysis, scope) {
  return analysis?.withheld_summaries?.[scope] != null;
}

export function withheldAlertNote(alert) {
  const count = alert?.payload?.withheld_items || 0;
  if (!count) return null;
  return `${count} cited ${count === 1 ? "source is" : "sources are"} no longer available. That evidence and its interpretation are withheld; the rest of this alert is unaffected.`;
}
