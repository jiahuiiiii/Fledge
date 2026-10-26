// One mapping from every tone vocabulary in the app to the five display tones.
export function toneOf(value) {
  const text = String(value || "").toLowerCase();
  if (/(^|\W)(positive|good|upbeat|could_help|help)/.test(text)) return "positive";
  if (/(^|\W)(negative|bad|worried|could_hurt|hurt)/.test(text)) return "negative";
  if (/mixed/.test(text)) return "mixed";
  if (/neutral/.test(text)) return "neutral";
  return "unknown";
}
