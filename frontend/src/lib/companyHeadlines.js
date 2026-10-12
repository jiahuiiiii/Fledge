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
  // The same bounded public names used by source collection. Capital M keeps
  // Micron's brand distinct from an ordinary lowercase measurement unit.
  const short = {
    MU: ["Micron Technology", "Micron"],
    MRVL: ["Marvell Technology", "Marvell"],
  }[symbol];
  if (
    short &&
    name === short[0] &&
    new RegExp(
      `(^|[^\\p{L}\\p{N}])${short[1]}(?=$|[^\\p{L}\\p{N}])`,
      symbol === "MU" ? "u" : "iu",
    ).test(text)
  )
    return true;
  return symbol.length > 2
    ? new RegExp(`(^|[^A-Za-z0-9])${escape(symbol)}(?=$|[^A-Za-z0-9])`).test(
        text,
      )
    : new RegExp(
        `(?:\\$|\\(|:\\s*)${escape(symbol)}(?=$|[^A-Za-z0-9])|\\b${escape(symbol)}\\s+(?:stock|shares|earnings)\\b`,
      ).test(text);
}

// The backend supplies permitted news IDs for the current seven-day window.
// A saved AI reading must never supply or order this current browsing preview.
export function currentCompanyHeadlines(data) {
  const allowed = new Set(data.market_news_ids || []);
  const documents = data.documents || [];
  const superseded = new Set(
    documents.map((d) => d.supersedes_id).filter(Boolean),
  );
  const seen = new Set();
  return documents
    .filter(
      (d) =>
        d.kind === "news" &&
        allowed.has(d.id) &&
        !superseded.has(d.id) &&
        Number.isFinite(Date.parse(d.published_at)) &&
        mentionsCompany(d, data.instrument),
    )
    .slice()
    .sort(
      (a, b) =>
        Date.parse(b.published_at) - Date.parse(a.published_at) ||
        a.id.localeCompare(b.id),
    )
    .filter((d) => {
      const identity = d.content_hash || d.id;
      if (seen.has(identity)) return false;
      seen.add(identity);
      return true;
    });
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
