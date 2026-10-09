import { companyName } from "./companyIdentity.js";

const escape = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

// A browsing filter only: an explicit mention is not an AI relevance verdict.
// Saved readings, tone totals and the complete source catalogue stay unchanged.
export function mentionsCompany(story, company) {
  const text = `${story.title || ""} ${story.body || ""}`;
  const name = companyName(company)
    .replace(
      /(?:,?\s+(?:incorporated|inc\.?|corporation|corp\.?|limited|ltd\.?|plc))(?:\s*\/.*)?$/i,
      "",
    )
    .trim();
  if (
    name &&
    name !== company?.symbol &&
    new RegExp(
      `(^|[^\\p{L}\\p{N}])${escape(name)}(?=$|[^\\p{L}\\p{N}])`,
      "iu",
    ).test(text)
  )
    return true;
  const symbol = company?.symbol;
  if (!symbol) return false;
  return symbol.length > 2
    ? new RegExp(`(^|[^A-Za-z0-9])${escape(symbol)}(?=$|[^A-Za-z0-9])`).test(
        text,
      )
    : new RegExp(`(?:\\$|\\(|:)${escape(symbol)}(?=$|[^A-Za-z0-9])`).test(text);
}

export function savedDevelopments(analysis) {
  if (!analysis || analysis.withheld) return [];
  const reported = new Set(
    (analysis.items || [])
      .filter(
        (item) =>
          item.channel === "news" &&
          item.relevance === "relevant" &&
          item.reporting_basis?.eligible,
      )
      .map((item) => item.source_id),
  );
  const repeated = new Set(
    (analysis.coverage_links || [])
      .filter(
        (link) =>
          link.relation === "repeats" && link.repeat_suppression_allowed,
      )
      .map((link) => link.source_id),
  );
  return (analysis.sources || [])
    .filter(
      (source) =>
        source.kind === "news" &&
        !source.comparison_only &&
        reported.has(source.id) &&
        !repeated.has(source.id),
    )
    .slice()
    .sort((a, b) => Date.parse(b.published_at) - Date.parse(a.published_at));
}
