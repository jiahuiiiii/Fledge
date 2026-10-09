import { sourceHeadline } from "./sourceHeadline.js";

const relations = {
  supports: "May support your reasoning",
  challenges: "May challenge your reasoning",
  risk: "Risk to investigate",
  answers: "Evidence toward your question",
};

export function inboxSummary(record) {
  const d = record.detail;
  if (d.withheld)
    return {
      title: "Source access changed",
      text: "Evidence and interpretation are withheld. Your review history is preserved.",
    };
  if (record.kind === "company") {
    const item = d.payload.items?.[0];
    // Preview only this alert's retained source, never a current workspace
    // version, unrelated source, comparison-only article or parent comment.
    const source = d.sources?.find(
      (source) => source.id === item?.source_id && !source.comparison_only,
    );
    const headline = sourceHeadline(source);
    const excerpt = item?.citations?.find(
      (citation) =>
        citation.source_id === source?.id &&
        citation.quote !== headline &&
        source?.body?.includes(citation.quote),
    )?.quote;
    return {
      title:
        headline || (source?.body ? "From the saved discussion" : record.title),
      text:
        excerpt ||
        source?.body ||
        "Open this update to inspect the saved change and its evidence.",
      source: source?.source || source?.platform,
      publishedAt: source?.published_at,
      alert: record.title,
      more: Math.max(0, (d.payload.items?.length || 0) - 1),
    };
  }
  if (record.kind === "condition")
    return { title: record.title, text: d.question };
  const noteworthy = d.items.filter((i) => relations[i.relation]);
  const kinds = [...new Set(noteworthy.map((i) => i.relation))];
  return {
    title:
      kinds.length === 1
        ? relations[kinds[0]]
        : "Connections to your saved reasoning",
    text: noteworthy[0]?.explanation || d.question,
    question: d.question,
  };
}

export function recordKey(record) {
  return `${record.kind}:${record.id}`;
}
