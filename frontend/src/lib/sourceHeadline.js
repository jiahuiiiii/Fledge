// These are source-type placeholders, not headlines or the author's words.
const socialPlaceholders = new Set([
  "hacker news comment",
  "reddit comment",
  "reddit post",
  "x post",
]);

export function sourceHeadline(source) {
  if (typeof source?.title !== "string" || !source.title.trim()) return null;
  if (
    source.kind === "social" &&
    socialPlaceholders.has(source.title.trim().toLowerCase())
  )
    return null;
  return source.title;
}
