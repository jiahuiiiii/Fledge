import { sourceHeadline } from "./sourceHeadline.js";

const clip = (text, n = 280) =>
  text && text.length > n ? `${text.slice(0, n).trimEnd()}…` : text || "";

// The sources behind one saved update, as flat rows for EvidenceDialog. Only
// saved sources are used; nothing is inferred. A source with no link, or an
// update whose source access changed, gets no row link (the caller falls back
// to the in-app source dialog or the withheld notice).
export function alertEvidenceRows(record) {
  const d = record.detail;
  if (!d || d.withheld) return [];
  const sources = new Map((d.sources || []).map((s) => [s.id, s]));
  let items;
  if (record.kind === "company")
    items = (d.payload?.items || []).map((i) => ({
      id: i.source_id,
      quote: i.citations?.find((c) => c.source_id === i.source_id)?.quote,
    }));
  else if (record.kind === "idea")
    items = (d.items || []).map((i) => ({
      id: i.source_id,
      quote: i.answer_excerpt || null,
    }));
  else items = (d.sources || []).map((s) => ({ id: s.id }));
  const seen = new Set();
  return items
    .filter((i) => i.id && sources.has(i.id) && !seen.has(i.id) && seen.add(i.id))
    .map((i) => {
      const s = sources.get(i.id);
      return {
        id: s.id,
        label: sourceHeadline(s) || (s.body ? "Saved discussion" : "Saved source"),
        source: s.source || s.platform || "Source",
        publishedAt: s.published_at,
        url: s.url || null,
        quote: clip(i.quote || s.body),
        source_obj: s,
      };
    });
}

// Provenance kept for the audit trail, shown only in a closed "Details" line.
export function alertProvenance(record, format) {
  const d = record.detail || {};
  return [
    d.created_at || record.created_at
      ? `Saved ${format(d.created_at || record.created_at)}`
      : null,
    d.cutoff ? `Source cutoff ${format(d.cutoff)}` : null,
    d.model ? `Model ${d.model}` : null,
    d.prompt_version ? `Prompt ${d.prompt_version}` : null,
  ].filter(Boolean);
}
