// A summary point can cite several quotes from the same article, or the same
// article saved under two source records. Show each article once.
const norm = (value) => String(value || "").trim().toLowerCase().replace(/\s+/g, " ");

export function uniqueCitations(citations = [], documents = []) {
  const seen = new Set();
  const out = [];
  for (const citation of citations) {
    const doc = documents.find((d) => d.id === citation.source_id);
    const key = norm(doc?.url) || norm(doc?.title) || citation.source_id;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push({ ...citation, doc });
  }
  return out;
}
