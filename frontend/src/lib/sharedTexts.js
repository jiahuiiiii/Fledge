// The company read sends a repeated source text once, in `source_texts`, and
// each place that had it carries `body_ref` instead (thesis/workspace_payload.py).
// Put the text back so every component sees `body` exactly as before.
const SOURCE_LISTS = [
  ["documents"],
  ["sentiment", "sources"],
  ["sentiment", "comparison_sources"],
  ["sentiment_inputs", "sources"],
  ["sentiment_inputs", "comparison_sources"],
];

export function expandSharedTexts(result) {
  const texts = result?.source_texts;
  if (!texts) return result;
  for (const path of SOURCE_LISTS) {
    const list = path.reduce((value, key) => value?.[key], result);
    if (!Array.isArray(list)) continue;
    for (const item of list) {
      if (!item || typeof item.body_ref !== "string") continue;
      if (Object.hasOwn(texts, item.body_ref)) item.body = texts[item.body_ref];
      delete item.body_ref;
    }
  }
  delete result.source_texts;
  return result;
}
